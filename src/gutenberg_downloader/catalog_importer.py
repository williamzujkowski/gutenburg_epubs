"""Import Project Gutenberg catalogs from offline sources."""

import csv
import gzip
import logging
import os
import shutil
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from tqdm import tqdm

from .constants import REQUEST_TIMEOUT, DEFAULT_USER_AGENT
from .database import BookDatabase

logger = logging.getLogger(__name__)


class CatalogImporter:
    """Import book metadata from Project Gutenberg offline catalogs."""
    
    # Catalog URLs
    RDF_CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.zip"
    CSV_CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
    
    def __init__(self, db_path: str = "gutenberg_books.db"):
        """Initialize catalog importer.
        
        Args:
            db_path: Path to the database file
        """
        self.db = BookDatabase(db_path)
        self.client = httpx.Client(
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=REQUEST_TIMEOUT
        )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()
    
    def download_with_progress(self, url: str, output_path: Path) -> bool:
        """Download a file with progress bar.
        
        Args:
            url: URL to download from
            output_path: Path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if file already exists and get size for resume
            resume_pos = 0
            if output_path.exists():
                resume_pos = output_path.stat().st_size
                logger.info(f"Resuming download from {resume_pos} bytes")
            
            # Get file size and download with proper streaming
            headers = {"Range": f"bytes={resume_pos}-"} if resume_pos > 0 else {}
            
            # Use stream context manager properly (httpx API)
            with self.client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                if resume_pos > 0:
                    total_size += resume_pos
                
                # Download with progress
                mode = "ab" if resume_pos > 0 else "wb"
                with open(output_path, mode) as f:
                    with tqdm(
                        total=total_size,
                        initial=resume_pos,
                        unit="B",
                        unit_scale=True,
                        desc=f"Downloading {output_path.name}"
                    ) as pbar:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            return True
            
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False
    
    def import_csv_catalog(self, csv_path: Optional[Path] = None) -> int:
        """Import books from CSV catalog.
        
        Args:
            csv_path: Path to CSV file, or None to download
            
        Returns:
            Number of books imported
        """
        logger.info("Importing from CSV catalog...")
        
        # Download if needed
        if csv_path is None:
            csv_path = Path("pg_catalog.csv")
            if not csv_path.exists():
                print("📥 Downloading CSV catalog...")
                if not self.download_with_progress(self.CSV_CATALOG_URL, csv_path):
                    return 0
        
        # Load genre extraction helper
        from .api_discovery import APIBookDiscovery
        api_discovery = APIBookDiscovery()
        
        # Parse CSV
        books_data = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in tqdm(reader, desc="Parsing CSV catalog"):
                # Skip non-English books without EPUB
                if row.get('Language') != 'en':
                    continue
                
                # Extract subjects and bookshelves
                subjects = row.get('Subjects', '').split('; ') if row.get('Subjects') else []
                bookshelves = row.get('Bookshelves', '').split('; ') if row.get('Bookshelves') else []
                
                # Extract genre classifications from subjects and bookshelves
                genres = api_discovery._extract_genres_from_metadata(subjects, bookshelves)
                    
                # Create book data structure similar to API
                book_data = {
                    'id': int(row.get('Text#', 0)),
                    'title': row.get('Title', 'Unknown'),
                    'authors': [{'name': row.get('Authors', 'Unknown')}],
                    'subjects': subjects,
                    'bookshelves': bookshelves,
                    'genres': genres,
                    'languages': ['en'],
                    'formats': {},
                    'download_count': 0,  # CSV doesn't have download counts
                    'media_type': 'Text',
                    'raw_data': dict(row)  # Store the original row
                }
                
                # Add Library of Congress Classification if available
                if row.get('LoCC'):
                    book_data['locc'] = row.get('LoCC')
                
                # Add format URLs if available
                if row.get('Text#'):
                    book_id = row.get('Text#')
                    # Direct URL to the potential EPUB file
                    book_data['formats']['application/epub+zip'] = f"https://www.gutenberg.org/ebooks/{book_id}.epub.images"
                
                books_data.append(book_data)
        
        # Store in database
        print(f"\n💾 Storing {len(books_data)} books in database...")
        stored = self.db.bulk_insert_books(books_data)
        
        return stored
    
    def parse_rdf_file(self, rdf_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a single RDF file.
        
        Args:
            rdf_path: Path to RDF file
            
        Returns:
            Book data dictionary or None
        """
        try:
            tree = ET.parse(rdf_path)
            root = tree.getroot()
            
            # Define namespaces
            ns = {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dc': 'http://purl.org/dc/terms/',
                'dcam': 'http://purl.org/dc/dcam/',
                'pgterms': 'http://www.gutenberg.org/2009/pgterms/',
                'cc': 'http://web.resource.org/cc/'
            }
            
            # Get book ID from filename
            book_id = int(rdf_path.stem)
            
            # Extract metadata
            ebook = root.find('.//pgterms:ebook', ns)
            if ebook is None:
                return None
            
            # Title
            title = ebook.find('.//dc:title', ns)
            title_text = title.text if title is not None else f"Book {book_id}"
            
            # Authors
            authors = []
            for creator in ebook.findall('.//dc:creator', ns):
                agent = creator.find('.//pgterms:agent', ns)
                if agent is not None:
                    name = agent.find('.//pgterms:name', ns)
                    birth_year = agent.find('.//pgterms:birthdate', ns)
                    death_year = agent.find('.//pgterms:deathdate', ns)
                    
                    if name is not None:
                        author_data = {'name': name.text}
                        if birth_year is not None:
                            try:
                                author_data['birth_year'] = int(birth_year.text)
                            except (ValueError, TypeError):
                                pass
                                
                        if death_year is not None:
                            try:
                                author_data['death_year'] = int(death_year.text)
                            except (ValueError, TypeError):
                                pass
                                
                        authors.append(author_data)
            
            # Language
            language = ebook.find('.//dc:language', ns)
            lang_code = 'en'
            if language is not None:
                value = language.find('.//rdf:value', ns)
                if value is not None:
                    lang_code = value.text
            
            # Subjects
            subjects = []
            for subject in ebook.findall('.//dc:subject', ns):
                value = subject.find('.//rdf:value', ns)
                if value is not None:
                    subjects.append(value.text)
            
            # LCC (Library of Congress Classification)
            lcc = None
            for subject in ebook.findall('.//dc:subject', ns):
                memberOf = subject.find('./dcam:memberOf', ns)
                if memberOf is not None and '{http://purl.org/dc/terms/LCC}' in memberOf.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', ''):
                    value = subject.find('.//rdf:value', ns)
                    if value is not None:
                        lcc = value.text
                        break
            
            # Publisher
            publisher = ebook.find('.//dc:publisher', ns)
            publisher_text = publisher.text if publisher is not None else None
            
            # Publication date
            pub_date = ebook.find('.//dc:issued', ns)
            pub_date_text = pub_date.text if pub_date is not None else None
            
            # Rights (license)
            rights = ebook.find('.//dc:rights', ns)
            rights_text = rights.text if rights is not None else None
            
            # Formats
            formats = {}
            for file_elem in ebook.findall('.//pgterms:file', ns):
                about = file_elem.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
                if about:
                    format_elem = file_elem.find('.//dc:format/rdf:value', ns)
                    if format_elem is not None:
                        format_type = format_elem.text
                        formats[format_type] = about
                        
                        # Special case for EPUB
                        if 'epub' in format_type.lower():
                            formats['application/epub+zip'] = about
            
            # Download count
            downloads = ebook.find('.//pgterms:downloads', ns)
            download_count = 0
            if downloads is not None:
                try:
                    download_count = int(downloads.text)
                except ValueError:
                    pass
            
            # Media type
            media_type = "Text"  # Default for most Gutenberg books
            
            # Capture raw XML as a string for reference
            raw_xml = ET.tostring(ebook, encoding='unicode')
            
            # Extract bookshelves (not directly in RDF, but can be inferred from certain subject types)
            bookshelves = []
            
            # Load genre extraction helper
            from .api_discovery import APIBookDiscovery
            api_discovery = APIBookDiscovery()
            
            # Extract genre classifications
            genres = api_discovery._extract_genres_from_metadata(subjects, bookshelves)
            
            return {
                'id': book_id,
                'title': title_text,
                'authors': authors,
                'subjects': subjects,
                'bookshelves': bookshelves,
                'genres': genres,
                'languages': [lang_code],
                'formats': formats,
                'download_count': download_count,
                'media_type': media_type,
                'publisher': publisher_text,
                'publication_date': pub_date_text,
                'rights': rights_text,
                'lcc': lcc,
                'raw_data': {
                    'xml': raw_xml[:10000],  # Limit size for storage
                    'source': 'rdf'
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing {rdf_path}: {e}")
            return None
    
    def import_rdf_catalog(self, rdf_archive_path: Optional[Path] = None) -> int:
        """Import books from RDF catalog archive.
        
        Args:
            rdf_archive_path: Path to RDF archive, or None to download
            
        Returns:
            Number of books imported
        """
        logger.info("Importing from RDF catalog...")
        
        # Download if needed
        if rdf_archive_path is None:
            rdf_archive_path = Path("rdf-files.tar.zip")
            if not rdf_archive_path.exists():
                print("📥 Downloading RDF catalog (this may take a while)...")
                if not self.download_with_progress(self.RDF_CATALOG_URL, rdf_archive_path):
                    return 0
        
        # Extract and process
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Extract zip
            print("📦 Extracting catalog archive...")
            shutil.unpack_archive(rdf_archive_path, tmpdir_path)
            
            # Find the tar file inside
            tar_files = list(tmpdir_path.glob("*.tar"))
            if not tar_files:
                logger.error("No tar file found in archive")
                return 0
            
            # Extract tar
            print("📂 Extracting RDF files...")
            with tarfile.open(tar_files[0], 'r') as tar:
                tar.extractall(tmpdir_path)
            
            # Process RDF files
            rdf_files = list(tmpdir_path.glob("**/*.rdf"))
            logger.info(f"Found {len(rdf_files)} RDF files")
            
            books_data = []
            for rdf_file in tqdm(rdf_files, desc="Parsing RDF files"):
                book_data = self.parse_rdf_file(rdf_file)
                if book_data and book_data['languages'] == ['en'] and book_data['formats']:
                    books_data.append(book_data)
            
            # Store in database
            print(f"\n💾 Storing {len(books_data)} English EPUB books in database...")
            stored = self.db.bulk_insert_books(books_data)
            
            return stored
    
    def import_catalog(self, format: str = "csv") -> int:
        """Import catalog in specified format.
        
        Args:
            format: Catalog format ('csv' or 'rdf')
            
        Returns:
            Number of books imported
        """
        if format.lower() == "csv":
            return self.import_csv_catalog()
        elif format.lower() == "rdf":
            return self.import_rdf_catalog()
        else:
            logger.error(f"Unknown catalog format: {format}")
            return 0
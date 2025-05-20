# Bulk Download Instructions

This document explains how to download a large number of books (like 300) from Project Gutenberg using this software.

## Current Status

The bulk download attempt only found **7 books** in the database. To download 300 books, you need to first populate the database with more book metadata.

## Step 1: Populate the Database

Before you can download books, you need to discover and index them. Run the discovery script:

```bash
python run_discovery_first.py
```

This script will:
1. Connect to the Project Gutenberg API
2. Request metadata for books with IDs from 1 to 10,000
3. Store book information in the database, focusing on English books
4. Process approximately 10 books per second, so indexing 10,000 books takes ~15-20 minutes

When the script completes, your database should contain hundreds of English books with EPUB formats.

## Step 2: Run the Bulk Download

After populating the database, run the bulk download script:

```bash
python bulk_download.py
```

This will:
1. Query the database for the 300 most popular English books with EPUB format
2. Download them to the `./bulk_downloads` directory
3. Automatically handle any download errors or interruptions

## Additional Options

### Process More Books

If you want to discover even more books, modify the discovery script to process a larger range:

```python
# In run_discovery_first.py, change:
for start_id in range(1, 10001, batch_size):  # Original
for start_id in range(1, 30001, batch_size):  # Process 30,000 books
```

### Change Output Directory

To change where books are saved, edit the `OUTPUT_DIR` in `bulk_download.py`:

```python
# Change this line in bulk_download.py:
OUTPUT_DIR = Path("./my_custom_directory")
```

### Resume Interrupted Downloads

If the download process is interrupted, you can resume it by running:

```bash
python bulk_download.py
```

The script automatically detects and resumes any pending or failed downloads.

## Troubleshooting

- **Empty Database**: If no books are found, make sure the discovery script runs successfully
- **Few Books**: The number of books available depends on the Project Gutenberg API and what's been indexed
- **Download Errors**: Some books might have incorrect or missing EPUB URLs; the script will try to handle these cases

## Current Catalog

The current download contains these 7 books:
1. Pride and Prejudice (561 KB)
2. Emma (483 KB)
3. Sense and Sensibility (413 KB)
4. The War of the Worlds (245 KB)
5. A Princess of Mars (252 KB)
6. The Time Machine (164 KB)
7. The Strange Case of Dr. Jekyll and Mr. Hyde (144 KB)
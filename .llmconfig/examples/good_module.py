"""Example module demonstrating project coding standards.

This module provides a reference implementation that follows all the project's
coding standards, including proper docstrings, type hints, error handling,
and testing patterns.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

from src.avip_pipeline.exceptions import DataValidationError

# Configure structured logging
logger = logging.getLogger(__name__)

# Constants follow UPPER_SNAKE_CASE
DEFAULT_THRESHOLD = 9.0
MAX_ENTRIES = 1000


class ExampleProcessor:
    """Processes vulnerability data according to defined criteria.

    This class demonstrates proper class structure, documentation,
    type hints, and error handling patterns.

    Attributes:
        threshold: The CVSS score threshold for filtering.
        source_name: The name of the data source being processed.
    """

    def __init__(self, threshold: float = DEFAULT_THRESHOLD, source_name: str = "default"):
        """Initialize the processor with filtering criteria.

        Args:
            threshold: CVSS score threshold for filtering vulnerabilities.
                Defaults to DEFAULT_THRESHOLD.
            source_name: Name of the data source. Defaults to "default".
        """
        self.threshold = threshold
        self.source_name = source_name
        self._processed_count = 0  # Private attribute with leading underscore

        logger.info(
            "Initialized processor",
            extra={"threshold": threshold, "source": source_name}
        )

    def process_entries(self, entries: List[Dict[str, Union[str, float, None]]]) -> List[Dict[str, Union[str, float, None]]]:
        """Process vulnerability entries and filter based on threshold.

        Takes a list of vulnerability entries and returns only those
        that meet the defined threshold criteria.

        Args:
            entries: List of vulnerability entries as dictionaries.
                Each entry must contain at least an 'id' and 'cvss_score' field.

        Returns:
            List of filtered vulnerability entries meeting threshold criteria.

        Raises:
            DataValidationError: If entries are missing required fields.
        """
        if not entries:
            logger.warning("No entries provided for processing")
            return []

        filtered_entries = []

        for entry in entries:
            # Validate required fields
            if 'id' not in entry:
                logger.error("Missing required field", extra={"field": "id", "entry": entry})
                raise DataValidationError("Entry missing required 'id' field")

            # Handle optional fields with safe access
            cvss_score = entry.get('cvss_score')

            # Type checking with proper null handling
            if cvss_score is not None and not isinstance(cvss_score, (int, float)):
                logger.error(
                    "Invalid CVSS score type",
                    extra={"id": entry['id'], "type": type(cvss_score).__name__}
                )
                continue

            # Apply filtering logic
            if cvss_score is not None and cvss_score >= self.threshold:
                # Enrich data when including in results
                entry['processed_date'] = datetime.now().isoformat()
                entry['source'] = self.source_name
                filtered_entries.append(entry)

        # Update internal state
        self._processed_count += len(entries)

        # Log results
        logger.info(
            "Processed vulnerability entries",
            extra={
                "total": len(entries),
                "filtered": len(filtered_entries),
                "threshold": self.threshold
            }
        )

        return filtered_entries

    @property
    def processed_count(self) -> int:
        """Total number of entries processed since initialization.

        Returns:
            The count of processed entries.
        """
        return self._processed_count

# Example usage in doctest format
"""
>>> processor = ExampleProcessor(threshold=7.0, source_name="NVD")
>>> entries = [
...     {"id": "CVE-2023-1234", "cvss_score": 8.5, "description": "Critical vulnerability"},
...     {"id": "CVE-2023-5678", "cvss_score": 6.5, "description": "Moderate vulnerability"}
... ]
>>> filtered = processor.process_entries(entries)
>>> len(filtered)
1
>>> filtered[0]["id"]
'CVE-2023-1234'
"""
EOF < /dev/null

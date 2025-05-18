"""Test module demonstrating project testing standards.

This module shows how to implement comprehensive tests following
the project's testing manifesto, including hypothesis tests,
regression tests, and proper test organization.
"""

from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.avip_pipeline.example_module import ExampleProcessor
from src.avip_pipeline.exceptions import DataValidationError


class TestExampleProcessor:
    """Tests for the ExampleProcessor class."""

    def test_initialization_with_defaults(self):
        """HYPOTHESIS: Processor should initialize with default values if none provided."""
        # Arrange/Act
        processor = ExampleProcessor()

        # Assert
        assert processor.threshold == 9.0
        assert processor.source_name == "default"
        assert processor.processed_count == 0

    def test_initialization_with_custom_values(self):
        """HYPOTHESIS: Processor should use provided values for initialization."""
        # Arrange/Act
        threshold = 7.5
        source = "test_source"
        processor = ExampleProcessor(threshold=threshold, source_name=source)

        # Assert
        assert processor.threshold == threshold
        assert processor.source_name == source

    @given(threshold=st.floats(min_value=0, max_value=10))
    def test_initialization_with_various_thresholds(self, threshold):
        """HYPOTHESIS: Processor should accept any valid threshold in the CVSS range."""
        # Arrange/Act
        processor = ExampleProcessor(threshold=threshold)

        # Assert
        assert processor.threshold == threshold

    def test_process_entries_empty_list(self):
        """HYPOTHESIS: Processing an empty list should return an empty list."""
        # Arrange
        processor = ExampleProcessor()
        entries = []

        # Act
        result = processor.process_entries(entries)

        # Assert
        assert result == []
        assert processor.processed_count == 0

    def test_process_entries_missing_id_field(self):
        """HYPOTHESIS: Entries missing the required 'id' field should raise DataValidationError."""
        # Arrange
        processor = ExampleProcessor()
        entries = [{"cvss_score": 9.5}]  # Missing 'id' field

        # Act/Assert
        with pytest.raises(DataValidationError) as excinfo:
            processor.process_entries(entries)

        assert "missing required 'id' field" in str(excinfo.value).lower()

    def test_process_entries_with_invalid_cvss_type(self):
        """HYPOTHESIS: Entries with non-numeric CVSS scores should be skipped."""
        # Arrange
        processor = ExampleProcessor(threshold=7.0)
        entries = [
            {"id": "CVE-2023-1234", "cvss_score": "high"},  # String instead of number
            {"id": "CVE-2023-5678", "cvss_score": 8.0}      # Valid entry
        ]

        # Act
        result = processor.process_entries(entries)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "CVE-2023-5678"
        assert processor.processed_count == 2  # Both entries were processed

    def test_process_entries_filtering(self):
        """HYPOTHESIS: Only entries meeting threshold criteria should be returned."""
        # Arrange
        threshold = 7.0
        processor = ExampleProcessor(threshold=threshold)
        entries = [
            {"id": "CVE-2023-1234", "cvss_score": 8.0},  # Above threshold
            {"id": "CVE-2023-5678", "cvss_score": 7.0},  # At threshold
            {"id": "CVE-2023-9012", "cvss_score": 6.5}   # Below threshold
        ]

        # Act
        result = processor.process_entries(entries)

        # Assert
        assert len(result) == 2
        assert {entry["id"] for entry in result} == {"CVE-2023-1234", "CVE-2023-5678"}
        assert processor.processed_count == 3

    def test_process_entries_enrichment(self):
        """HYPOTHESIS: Filtered entries should be enriched with additional data."""
        # Arrange
        source_name = "test_source"
        processor = ExampleProcessor(threshold=7.0, source_name=source_name)
        entries = [{"id": "CVE-2023-1234", "cvss_score": 8.0}]

        # Act
        result = processor.process_entries(entries)

        # Assert
        assert len(result) == 1
        assert result[0]["source"] == source_name
        assert "processed_date" in result[0]

    @patch('src.avip_pipeline.example_module.logger')
    def test_process_entries_logging(self, mock_logger):
        """HYPOTHESIS: Processing should log information about the operation."""
        # Arrange
        processor = ExampleProcessor()
        entries = [{"id": "CVE-2023-1234", "cvss_score": 9.5}]

        # Act
        processor.process_entries(entries)

        # Assert
        # Verify logger was called with the right information
        mock_logger.info.assert_called_with(
            "Processed vulnerability entries",
            extra={
                "total": 1,
                "filtered": 1,
                "threshold": 9.0
            }
        )

    @given(
        entries=st.lists(
            st.fixed_dictionaries({
                "id": st.text(min_size=1),
                "cvss_score": st.one_of(
                    st.none(),
                    st.floats(min_value=0, max_value=10)
                )
            }),
            min_size=0,
            max_size=10
        ),
        threshold=st.floats(min_value=0, max_value=10)
    )
    def test_property_filtering_behavior(self, entries, threshold):
        """PROPERTY: Only entries with CVSS at or above threshold should be included."""
        # Arrange
        processor = ExampleProcessor(threshold=threshold)

        # Skip if entries contain invalid IDs that would cause validation errors
        for entry in entries:
            if not entry["id"]:
                pytest.skip("Test data includes empty ID")

        # Act
        result = processor.process_entries(entries)

        # Assert
        # All results should have CVSS scores at or above threshold
        for entry in result:
            assert entry["cvss_score"] is not None
            assert entry["cvss_score"] >= threshold

        # All original entries with valid scores above threshold should be included
        expected_count = sum(
            1 for entry in entries
            if entry["cvss_score"] is not None and entry["cvss_score"] >= threshold
        )
        assert len(result) == expected_count

    def test_regression_null_cvss_handling(self):
        """REGRESSION: Bug #123 - Null CVSS scores should be handled gracefully."""
        # Arrange
        processor = ExampleProcessor()
        entries = [
            {"id": "CVE-2023-1234", "cvss_score": None},
            {"id": "CVE-2023-5678", "cvss_score": 9.5}
        ]

        # Act
        result = processor.process_entries(entries)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "CVE-2023-5678"
EOF < /dev/null

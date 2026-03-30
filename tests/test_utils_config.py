"""
Unit tests for utils and config modules
"""

from unittest.mock import MagicMock, patch

import pytest

from probable_train import config
from probable_train.utils import allowed_file, require_query_parameters


class TestUtils:
    """Test cases for utility functions"""

    @pytest.mark.parametrize(
        "request_args,required_params,strict,expected_missing",
        [
            # All parameters present, strict=False
            (
                {"param1": "value1", "param2": "value2"},
                ["param1", "param2"],
                False,
                set(),
            ),
            # Missing parameters, strict=False
            ({"param1": "value1"}, ["param1", "param2"], False, {"param2"}),
            # All parameters present, strict=True
            (
                {"param1": "value1", "param2": "value2"},
                ["param1", "param2"],
                True,
                set(),
            ),
            # Empty required list
            ({"param1": "value1"}, [], True, set()),
            # No request args
            ({}, ["param1", "param2"], False, {"param1", "param2"}),
        ],
    )
    def test_require_query_parameters(
        self, request_args, required_params, strict, expected_missing
    ):
        """Test require_query_parameters with various scenarios"""
        mock_request = MagicMock()
        mock_request.args = request_args

        result = require_query_parameters(mock_request, required_params, strict=strict)

        assert result == expected_missing

    @patch("probable_train.utils.abort")
    def test_require_query_parameters_missing_strict_true(self, mock_abort):
        """Test require_query_parameters when some parameters are missing,
        strict=True"""
        mock_request = MagicMock()
        mock_request.args = {"param1": "value1"}

        require_query_parameters(mock_request, ["param1", "param2"], strict=True)

        # Should call abort with 400 and missing parameters
        mock_abort.assert_called_once_with(
            400, description="Missing required parameters: {'param2'}"
        )

    @pytest.mark.parametrize(
        "filename,expected_result",
        [
            # Valid extensions
            ("test.csv", True),
            ("TEST.CSV", True),  # Case insensitive
            ("my.test.file.csv", True),  # Multiple dots
            # Invalid extensions
            ("test.exe", False),
            ("testfile", False),  # No extension
        ],
    )
    def test_allowed_file(self, filename, expected_result):
        """Test allowed_file with various filenames"""
        result = allowed_file(filename)
        assert result == expected_result

    def test_allowed_file_empty_config(self):
        """Test allowed_file with empty ALLOWED_EXTENSIONS"""
        from probable_train.utils import current_app

        original_config = current_app.config.copy()
        current_app.config = {"ALLOWED_EXTENSIONS": set()}

        try:
            result = allowed_file("test.csv")
            assert result is False
        finally:
            current_app.config = original_config


class TestConfig:
    """Test cases for configuration module"""

    def test_config_values(self):
        """Test that expected configuration values are present"""
        # Test that config has expected attributes
        assert hasattr(config, "DEBUG")
        assert hasattr(config, "ALLOWED_EXTENSIONS")
        assert hasattr(config, "INGEST_TYPES")
        assert hasattr(config, "UPLOAD_FOLDER")
        assert hasattr(config, "DATABASE_URI")

        # Test specific values
        assert isinstance(config.DEBUG, bool)
        assert isinstance(config.ALLOWED_EXTENSIONS, set)
        assert isinstance(config.INGEST_TYPES, set)
        assert isinstance(config.UPLOAD_FOLDER, str)
        assert isinstance(config.DATABASE_URI, str)

    def test_allowed_extensions_content(self):
        """Test ALLOWED_EXTENSIONS contains expected file types"""
        expected_extensions = {"csv", "psv", "txt", "yaml", "yml"}
        assert config.ALLOWED_EXTENSIONS == expected_extensions

    def test_ingest_types_content(self):
        """Test INGEST_TYPES contains expected ingest types"""
        expected_types = {"trade1", "trade2", "position"}
        assert config.INGEST_TYPES == expected_types

    def test_database_uri_format(self):
        """Test DATABASE_URI is in expected format"""
        assert config.DATABASE_URI.startswith("sqlite:///")
        assert config.DATABASE_URI.endswith(".db")

    def test_upload_folder_path(self):
        """Test UPLOAD_FOLDER is a valid path"""
        assert config.UPLOAD_FOLDER == "./uploads"

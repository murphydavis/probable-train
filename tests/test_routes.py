"""
Integration tests for API routes - focused ONLY on route behavior.

Tests verify HTTP request handling, parameter validation, and response formatting.
Controller logic is mocked and NOT validated - that's covered in other test files.
"""

from datetime import datetime
import os
from unittest.mock import MagicMock, patch

import pytest

from probable_train import app


class TestRoutes:
    """Route tests - one test per route, focused on HTTP behavior only"""

    def test_index_route(self):
        """Test GET / returns server status"""
        with app.test_client() as client:
            response = client.get("/")
            assert response.status_code == 200
            assert response.get_json() == "server online"

    @pytest.mark.parametrize(
        "file_data,ftype,expected_status",
        [
            # Success cases - use actual static files
            ("trade1_sample.csv", "trade1", 200),
            ("trade2_sample.psv", "trade2", 200),
            ("position_sample.yaml", "position", 200),
            # Error cases
            (None, "trade1", 400),  # No file
            ("trade1_sample.csv", None, 400),  # No file type
            ("trade1_sample.csv", "invalid", 400),  # Invalid file type
            ("invalid.xyz", "trade1", 400),  # Invalid file extension
        ],
    )
    def test_ingest_route(self, file_data, ftype, expected_status):
        """Test ingest route - only verify HTTP handling and controller calls"""
        # Get static file path before any mocking
        static_path = None
        if file_data is not None:
            static_path = os.path.join(os.path.dirname(__file__), "static", file_data)

        with patch("probable_train.controllers.ingest.ingest_file") as mock_ingest:
            with patch("probable_train.routes.datetime") as mock_datetime:
                with patch("probable_train.routes.os.path.join") as mock_join:
                    with patch("probable_train.routes.logger") as mock_logger:
                        # Mock infrastructure
                        mock_datetime.utcnow.return_value = datetime(
                            2023, 1, 1, 12, 0, 0
                        )
                        mock_join.return_value = "/mocked/path"

                        with app.test_client() as client:
                            # Prepare request data
                            data = {}
                            if file_data is not None:
                                with open(static_path, "rb") as test_file:
                                    data["file"] = (test_file, file_data)
                                    if ftype is not None:
                                        data["ftype"] = ftype

                                    # Mock file save to avoid filesystem issues
                                    with patch(
                                        "werkzeug.datastructures.FileStorage.save"
                                    ):
                                        response = client.post(
                                            "/ingest",
                                            data=data,
                                            content_type="multipart/form-data",
                                        )
                            else:
                                # No file case
                                if ftype is not None:
                                    data["ftype"] = ftype
                                response = client.post(
                                    "/ingest",
                                    data=data,
                                    content_type="multipart/form-data",
                                )

                            assert response.status_code == expected_status

                            # Only verify controller was called for success cases
                            if expected_status == 200:
                                mock_ingest.assert_called_once()
                                mock_logger.info.assert_called_once()
                            else:
                                mock_ingest.assert_not_called()

    @pytest.mark.parametrize(
        "account,date,expected_status,expected_response",
        [
            # Success case
            ("ACC001", "20230101", 200, "success"),
            # Error cases
            (None, "20230101", 400, "Missing required parameter"),
            ("ACC001", None, 400, "Missing required parameter"),
            (None, None, 400, "Missing required parameter"),
        ],
    )
    def test_positions_route(self, account, date, expected_status, expected_response):
        """Test positions route with all scenarios"""
        # Mock database and date parsing
        with patch("probable_train.routes.db_session.scalars") as mock_scalars:
            with patch("probable_train.routes.dateparser.parse") as mock_parse:
                # Setup mocks for success case
                if expected_status == 200:
                    mock_date = datetime(2023, 1, 1).date()
                    mock_parse.return_value.date.return_value = mock_date

                    # Mock position with proper dict-like behavior for line 111 coverage
                    mock_position = MagicMock()
                    mock_position.__dict__.update(
                        {
                            "account_id": "ACC001",
                            "custodian": "BANK1",
                            "id": 1,
                            "report_date": mock_date,
                            "share_qty": 100,
                            "ticker": "AAPL",
                            "other_field": "should_be_excluded",
                        }
                    )
                    mock_scalars.return_value.all.return_value = [mock_position]

                with app.test_client() as client:
                    # Build query parameters
                    query_params = {}
                    if account is not None:
                        query_params["account"] = account
                    if date is not None:
                        query_params["date"] = date

                    response = client.get("/positions", query_string=query_params)
                    assert response.status_code == expected_status

                    if expected_status == 200:
                        # Verify database was queried
                        mock_scalars.assert_called_once()
                        mock_parse.assert_called_once()
                    else:
                        # Verify database was not queried for error cases
                        mock_scalars.assert_not_called()
                        mock_parse.assert_not_called()

    @pytest.mark.parametrize(
        "date,threshold,expected_status",
        [
            # Success cases
            ("20230101", None, 200),
            ("20230101", 0.15, 200),
            # Error case
            (None, None, 400),  # Missing date
        ],
    )
    def test_compliance_route(self, date, threshold, expected_status):
        """Test compliance route - only verify HTTP handling and controller calls"""
        with patch("probable_train.routes.get_concentration_breaches") as mock_breaches:
            with patch("probable_train.routes.dateparser.parse") as mock_parse:
                # Mock infrastructure for success case
                if expected_status == 200:
                    mock_breaches.return_value = {"breaches": []}

                with app.test_client() as client:
                    # Build query parameters
                    query_params = {}
                    if date is not None:
                        query_params["date"] = date
                    if threshold is not None:
                        query_params["threshold"] = threshold

                    response = client.get(
                        "/compliance/concentration", query_string=query_params
                    )
                    assert response.status_code == expected_status

                    # Only verify controller was called for success cases
                    if expected_status == 200:
                        mock_breaches.assert_called_once()
                        mock_parse.assert_called_once()
                    else:
                        mock_breaches.assert_not_called()
                        mock_parse.assert_not_called()

    @pytest.mark.parametrize(
        "date,expected_status",
        [
            # Success case
            ("20230101", 200),
            # Error case
            (None, 400),  # Missing date
        ],
    )
    def test_reconciliation_route(self, date, expected_status):
        """Test reconciliation route - only verify HTTP handling and controller calls"""
        with patch(
            "probable_train.routes.get_reconciliation_report"
        ) as mock_reconciliation:
            with patch("probable_train.routes.dateparser.parse") as mock_parse:
                # Mock infrastructure for success case
                if expected_status == 200:
                    mock_reconciliation.return_value = {}

                with app.test_client() as client:
                    # Build query parameters
                    query_params = {}
                    if date is not None:
                        query_params["date"] = date

                    response = client.get("/reconciliation", query_string=query_params)
                    assert response.status_code == expected_status

                    # Only verify controller was called for success cases
                    if expected_status == 200:
                        mock_reconciliation.assert_called_once()
                        mock_parse.assert_called_once()
                    else:
                        mock_reconciliation.assert_not_called()
                        mock_parse.assert_not_called()

"""
Unit tests for controllers module
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, mock_open, patch

import pytest

from probable_train import app
from probable_train.controllers.ingest import (
    ingest_file,
    ingest_position,
    ingest_trade1,
    ingest_trade2,
)
from probable_train.controllers.reconciliation import get_reconciliation_report


class TestIngestTrade1:
    """Test cases for ingest_trade1 function"""

    @patch("probable_train.controllers.ingest.dateparser.parse")
    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    def test_ingest_trade1_success(self, mock_session, mock_get_account, mock_parse):
        """Test successful ingestion of trade1 CSV file"""
        # Mock date parsing - need 4 calls for 2 rows
        # (trade_date + settlement_date each)
        mock_parse.side_effect = [
            MagicMock(date=lambda: "2023-01-01"),  # TradeDate for row 1
            MagicMock(date=lambda: "2023-01-03"),  # SettlementDate for row 1
            MagicMock(date=lambda: "2023-01-02"),  # TradeDate for row 2
            MagicMock(date=lambda: "2023-01-04"),  # SettlementDate for row 2
        ]

        # Mock account - return different accounts for different calls
        def mock_get_account_side_effect(session, account_id):
            mock_account = MagicMock()
            mock_account.id = account_id
            return mock_account

        mock_get_account.side_effect = mock_get_account_side_effect

        # Mock CSV data
        csv_data = """AccountID,Ticker,Quantity,Price,TradeType,TradeDate,SettlementDate
ACC001,AAPL,100,150.25,BUY,2023-01-01,2023-01-03
ACC002,GOOGL,50,2500.50,SELL,2023-01-02,2023-01-04"""

        with patch("builtins.open", mock_open(read_data=csv_data)):
            ingest_trade1("dummy_path.csv")

        # Verify account creation was called
        assert mock_get_account.call_count == 2

        # Verify trades were added to session
        mock_session.add_all.assert_called_once()
        trades_added = mock_session.add_all.call_args[0][0]
        assert len(trades_added) == 2

        # Verify first trade
        first_trade = trades_added[0]
        assert first_trade.account_id == "ACC001"
        assert first_trade.ticker == "AAPL"
        assert first_trade.share_qty == 100
        assert first_trade.market_value == Decimal("15025.00")

        # Verify second trade (SELL should be negative)
        second_trade = trades_added[1]
        assert second_trade.account_id == "ACC002"
        assert second_trade.ticker == "GOOGL"
        assert second_trade.share_qty == -50  # Negative for SELL

    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    def test_ingest_trade1_malformed_row(self, mock_session, mock_get_account):
        """Test handling of malformed rows in trade1 CSV"""
        # Mock logger
        from probable_train.controllers.ingest import current_app

        current_app.logger.exception = MagicMock()

        # CSV with malformed row
        csv_data = """AccountID,Ticker,Quantity,Price,TradeType,TradeDate,SettlementDate
ACC001,AAPL,invalid,150.25,BUY,2023-01-01,2023-01-03
ACC002,GOOGL,50,2500.50,SELL,2023-01-02,2023-01-04"""

        with patch("builtins.open", mock_open(read_data=csv_data)):
            with patch(
                "probable_train.controllers.ingest.dateparser.parse"
            ) as mock_parse:
                mock_parse.side_effect = [
                    MagicMock(date=lambda: "2023-01-02"),  # TradeDate for valid row
                    MagicMock(
                        date=lambda: "2023-01-04"
                    ),  # SettlementDate for valid row
                ]
                ingest_trade1("dummy_path.csv")

        # Should only process the valid row
        mock_get_account.assert_called_once()
        mock_session.add_all.assert_called_once()
        trades_added = mock_session.add_all.call_args[0][0]
        assert len(trades_added) == 1

        # Should log exception for malformed row
        from probable_train.controllers.ingest import current_app

        current_app.logger.exception.assert_called_once()


class TestIngestTrade2:
    """Test cases for ingest_trade2 function"""

    @pytest.mark.parametrize(
        "psv_data,expected_trades",
        [
            # Success case
            (
                """ACCOUNT_ID|SHARES|MARKET_VALUE|REPORT_DATE|SOURCE_SYSTEM|SECURITY_TICKER
ACC001|100|15025.00|20230102|BROKER1|AAPL
ACC002|50|125025.00|20230102|BROKER2|GOOGL""",
                2,
            ),
            # Mixed case - one valid, one malformed
            (
                """ACCOUNT_ID|SHARES|MARKET_VALUE|REPORT_DATE|SOURCE_SYSTEM|SECURITY_TICKER
ACC001|100|15025.00|20230102|BROKER1|AAPL
ACC002|invalid|125025.00|20230102|BROKER2|GOOGL""",
                1,
            ),
        ],
    )
    @patch("probable_train.controllers.ingest.dateparser.parse")
    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    def test_ingest_trade2_scenarios(
        self, mock_session, mock_get_account, mock_parse, psv_data, expected_trades
    ):
        """Test trade2 ingestion with valid data scenarios"""
        # Mock date parsing for valid rows
        mock_parse.return_value = MagicMock(date=lambda: "2023-01-01")

        # Mock account creation
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_get_account.return_value = mock_account

        with patch("builtins.open", mock_open(read_data=psv_data)):
            ingest_trade2("dummy_path.psv")

        # Verify trades were added correctly
        mock_session.add_all.assert_called_once()
        trades_added = mock_session.add_all.call_args[0][0]
        assert len(trades_added) == expected_trades

    @pytest.mark.xfail(reason="Expected to fail due to malformed data")
    @pytest.mark.parametrize(
        "psv_data",
        [
            # Malformed data cases
            (
                """ACCOUNT_ID|SHARES|MARKET_VALUE|REPORT_DATE|SOURCE_SYSTEM|SECURITY_TICKER
ACC001|invalid|100.50|20230101|BROKER1|AAPL
ACC001|100|invalid|20230101|BROKER1|AAPL"""
            ),
        ],
    )
    @patch("probable_train.controllers.ingest.dateparser.parse")
    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    @patch("probable_train.controllers.ingest.current_app")
    def test_ingest_trade2_malformed_data(
        self, mock_app, mock_session, mock_get_account, mock_parse, psv_data
    ):
        """Test trade2 ingestion with malformed data (expected to fail)"""
        # Mock logger
        mock_logger = MagicMock()
        mock_app.logger = mock_logger

        # Mock date parsing for valid rows
        mock_parse.return_value = MagicMock(date=lambda: "2023-01-01")

        # Mock account creation
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_get_account.return_value = mock_account

        with patch("builtins.open", mock_open(read_data=psv_data)):
            ingest_trade2("dummy_path.psv")

        # Verify logger was called for malformed rows
        assert mock_logger.exception.call_count >= 1


class TestIngestPosition:
    """Test cases for ingest_position function"""

    @pytest.mark.parametrize(
        "yaml_data,expected_positions",
        [
            # Success case
            (
                {
                    "report_date": "20230101",
                    "positions": [
                        {
                            "account_id": "ACC001",
                            "ticker": "AAPL",
                            "shares": 100,
                            "market_value": "15025.00",
                            "custodian_ref": "BANK1",
                        },
                        {
                            "account_id": "ACC002",
                            "ticker": "GOOGL",
                            "shares": 50,
                            "market_value": "125025.00",
                            "custodian_ref": "BANK2",
                        },
                    ],
                },
                2,
            ),
            # Mixed case - one valid, one malformed
            (
                {
                    "report_date": "20230101",
                    "positions": [
                        {
                            "account_id": "ACC001",
                            "ticker": "AAPL",
                            "shares": 100,
                            "market_value": "15025.00",
                            "custodian_ref": "BANK1",
                        },
                        {
                            "account_id": "ACC002",
                            "ticker": "GOOGL",
                            "shares": "invalid",  # This will cause ValueError
                            "market_value": "125025.00",
                        },
                    ],
                },
                1,
            ),
        ],
    )
    @patch("probable_train.controllers.ingest.dateparser.parse")
    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    def test_ingest_position_scenarios(
        self, mock_session, mock_get_account, mock_parse, yaml_data, expected_positions
    ):
        """Test position ingestion with valid data scenarios"""
        # Mock date parsing
        mock_parse.return_value = MagicMock(date=lambda: "2023-01-01")

        # Mock account creation
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_get_account.return_value = mock_account

        with patch("builtins.open", mock_open()):
            with patch("yaml.safe_load", return_value=yaml_data):
                ingest_position("dummy_path.yaml")

        # Verify positions were added correctly
        mock_session.add_all.assert_called_once()
        positions_added = mock_session.add_all.call_args[0][0]
        assert len(positions_added) == expected_positions

    @pytest.mark.xfail(reason="Expected to fail due to malformed data")
    @pytest.mark.parametrize(
        "yaml_data",
        [
            # Malformed data cases
            (
                {
                    "report_date": "20230101",
                    "positions": [
                        {
                            "account_id": "ACC001",
                            "ticker": "AAPL",
                            "shares": "invalid",
                            "market_value": "100.50",
                        },
                        {
                            "account_id": "ACC001",
                            "ticker": "GOOGL",
                            "shares": "100",
                            "market_value": "not_a_decimal",
                        },
                    ],
                }
            ),
        ],
    )
    @patch("probable_train.controllers.ingest.dateparser.parse")
    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    @patch("probable_train.controllers.ingest.current_app")
    def test_ingest_position_malformed_data(
        self, mock_app, mock_session, mock_get_account, mock_parse, yaml_data
    ):
        """Test position ingestion with malformed data (expected to fail)"""
        # Mock logger
        mock_logger = MagicMock()
        mock_app.logger = mock_logger

        # Mock date parsing
        mock_parse.return_value = MagicMock(date=lambda: "2023-01-01")

        # Mock account creation
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_get_account.return_value = mock_account

        with patch("builtins.open", mock_open()):
            with patch("yaml.safe_load", return_value=yaml_data):
                ingest_position("dummy_path.yaml")

        # Verify logger was called for malformed positions
        assert mock_logger.exception.call_count >= 1


class TestIngestFile:
    """Test cases for ingest_file function"""

    @pytest.mark.parametrize(
        "ingest_type,expected_file",
        [
            ("trade1", "tests/static/trade1_sample.csv"),
            ("trade2", "tests/static/trade2_sample.psv"),
            ("position", "tests/static/position_sample.yaml"),
        ],
    )
    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    def test_ingest_file_formats(
        self,
        mock_session,
        mock_get_account,
        ingest_type,
        expected_file,
    ):
        """Test ingest_file with different file formats"""
        # Mock dependencies
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_get_account.return_value = mock_account

        # Use static test file
        ingest_file(expected_file, ingest_type)
        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()


class TestReconciliation:
    """Test cases for reconciliation controller"""

    @patch("probable_train.controllers.reconciliation.jsonify")
    @patch("probable_train.controllers.reconciliation.db_session")
    def test_get_reconciliation_report_empty(self, mock_session, mock_jsonify):
        """Test reconciliation report with no accounts"""
        mock_session.query.return_value.all.return_value = []

        result = get_reconciliation_report("2023-01-01")

        # Should return mocked jsonify response
        assert result is not None
        mock_jsonify.assert_called_once_with({})

    @patch("probable_train.controllers.reconciliation.jsonify")
    @patch("probable_train.controllers.reconciliation.db_session")
    @pytest.mark.parametrize(
        "mock_row_data,expected_report",
        [
            (
                {
                    "account_id": "ACC001",
                    "ticker": "AAPL",
                    "position_shares": 100,
                    "position_market_value": "15025.00",
                    "position_custodian": "BANK1",
                    "trade_shares": 95,
                    "trade_market_value": "14273.75",
                    "trade_custodian": "BROKER1",
                    "trade_date": date(2023, 1, 1),
                    "position_report_date": date(2023, 1, 1),
                    "trade_settlement_date": date(2023, 1, 1),
                },
                {
                    "ticker": "AAPL",
                    "has_position": True,
                    "has_trade": True,
                    "position_shares": 100,
                    "position_market_value": "15025.00",
                    "position_custodian": "BANK1",
                    "trade_shares": 95,
                    "trade_market_value": "14273.75",
                    "trade_custodian": "BROKER1",
                    "reconciliation_status": "both_exist",
                    "trade_date": "2023-01-01",
                },
            ),
            (
                {
                    "account_id": "ACC001",
                    "ticker": "AAPL",
                    "position_shares": 100,
                    "position_market_value": "15025.00",
                    "position_custodian": "BANK1",
                    "trade_shares": None,
                    "trade_market_value": None,
                    "trade_custodian": None,
                    "trade_date": None,
                    "position_report_date": date(2023, 1, 1),
                    "trade_settlement_date": None,
                },
                {
                    "ticker": "AAPL",
                    "has_position": True,
                    "has_trade": False,
                    "position_shares": 100,
                    "position_market_value": "15025.00",
                    "position_custodian": "BANK1",
                    "trade_shares": None,
                    "trade_market_value": None,
                    "trade_custodian": None,
                    "reconciliation_status": "position_only",
                    "trade_date": None,
                },
            ),
            (
                {
                    "account_id": "ACC001",
                    "ticker": "AAPL",
                    "position_shares": None,
                    "position_market_value": None,
                    "position_custodian": None,
                    "trade_shares": 95,
                    "trade_market_value": "14273.75",
                    "trade_custodian": "BROKER1",
                    "trade_date": date(2023, 1, 1),
                    "position_report_date": None,
                    "trade_settlement_date": date(2023, 1, 1),
                },
                {
                    "ticker": "AAPL",
                    "has_position": False,
                    "has_trade": True,
                    "position_shares": None,
                    "position_market_value": None,
                    "position_custodian": None,
                    "trade_shares": 95,
                    "trade_market_value": "14273.75",
                    "trade_custodian": "BROKER1",
                    "reconciliation_status": "trade_only",
                    "trade_date": "2023-01-01",
                },
            ),
        ],
    )
    def test_get_reconciliation_report_scenarios(
        self, mock_session, mock_jsonify, mock_row_data, expected_report
    ):
        """Test reconciliation report with various data scenarios"""
        # Create a mock result row with the test data
        mock_row = MagicMock()
        for key, value in mock_row_data.items():
            setattr(mock_row, key, value)

        # Mock the single query execution to return the mock row
        mock_session.execute.return_value.all.return_value = [mock_row]

        result = get_reconciliation_report("2023-01-01")

        # Should return mocked jsonify response
        assert result is not None
        mock_jsonify.assert_called_once()
        call_args = mock_jsonify.call_args[0][0]

        account_id = mock_row_data["account_id"]
        ticker = mock_row_data["ticker"]
        assert call_args[account_id][ticker] == expected_report

        # Verify single query was called
        mock_session.execute.assert_called_once()


class TestComplianceConcentration:
    """Test cases for compliance concentration endpoint"""

    @pytest.mark.parametrize(
        "test_name,query_params,position_shares,position_value,trade_shares,trade_value,expected_breaches,expected_total_breaches,expected_breach_types",
        [
            (
                "success_with_breaches",
                {"date": "20230101", "threshold": "0.15"},
                100,
                Decimal("15025.00"),
                80,  # 20% difference from position
                Decimal("12020.00"),  # 20% difference from position
                1,
                1,
                ["share_quantity", "market_value"],
            ),
            (
                "no_breaches",
                {"date": "20230101"},
                100,
                Decimal("15025.00"),
                105,  # 5% difference from position
                Decimal("15776.25"),  # 5% difference from position
                0,
                0,
                [],
            ),
            (
                "no_trades",
                {"date": "20230101"},
                100,
                Decimal("15025.00"),
                None,  # No trades
                None,  # No trades
                1,
                1,
                ["share_quantity", "market_value"],
            ),
        ],
    )
    @patch("probable_train.routes.dateparser.parse")
    def test_compliance_concentration_scenarios(
        self,
        mock_parse,
        test_name,
        query_params,
        position_shares,
        position_value,
        trade_shares,
        trade_value,
        expected_breaches,
        expected_total_breaches,
        expected_breach_types,
    ):
        """Test compliance concentration endpoint with various scenarios"""
        # Mock date parsing
        mock_datetime = MagicMock()
        mock_datetime.date.return_value = datetime(2023, 1, 1).date()
        mock_parse.return_value = mock_datetime

        # Mock database data
        with app.test_client() as client:
            with patch("probable_train.db_session.query") as mock_query:
                with patch("probable_train.db_session.execute") as mock_execute:
                    # Mock account
                    mock_account = MagicMock()
                    mock_account.id = "ACC001"
                    mock_query.return_value.all.return_value = [mock_account]

                    # Mock position
                    mock_position = MagicMock()
                    mock_position.ticker = "AAPL"
                    mock_position.share_qty = position_shares
                    mock_position.market_value = position_value
                    mock_position.custodian = "BANK1"
                    mock_position.report_date = datetime(2023, 1, 1).date()

                    # Setup trades list
                    trades = []
                    if trade_shares is not None:
                        mock_trade = MagicMock()
                        mock_trade.ticker = "AAPL"
                        mock_trade.share_qty = trade_shares
                        mock_trade.market_value = trade_value
                        mock_trade.custodian = "BROKER1"
                        trades = [mock_trade]

                    # Setup mock execute to return positions and trades
                    mock_execute.return_value.scalars.return_value.all.side_effect = [
                        [mock_position],  # Positions
                        trades,  # Trades (may be empty)
                    ]

                    # Build query string
                    query_string = "&".join(
                        [f"{k}={v}" for k, v in query_params.items()]
                    )
                    response = client.get(f"/compliance/concentration?{query_string}")

                    assert response.status_code == 200
                    response_data = response.get_json()

                    # Build expected response data
                    expected_threshold = float(query_params.get("threshold", 0.2))
                    expected_response = {
                        "date": "2023-01-01",
                        "threshold": expected_threshold,
                        "breaches": [],
                        "total_breaches": expected_total_breaches,
                    }

                    # Add breach data if expected
                    if expected_breaches > 0:
                        # Calculate expected differences
                        share_diff = (
                            (trade_shares - position_shares)
                            if trade_shares is not None
                            else -position_shares
                        )
                        share_diff_pct = (
                            abs(share_diff / position_shares)
                            if position_shares != 0
                            else 1.0
                        )

                        trade_value_for_calc = (
                            trade_value if trade_value is not None else 0
                        )
                        value_diff = trade_value_for_calc - position_value
                        value_diff_pct = (
                            abs(value_diff / position_value)
                            if position_value != 0
                            else 1.0
                        )

                        expected_custodians = (
                            ["BROKER1"] if trade_shares is not None else []
                        )

                        expected_response["breaches"] = [
                            {
                                "account_id": "ACC001",
                                "ticker": "AAPL",
                                "breach_type": expected_breach_types,
                                "differences": {
                                    "share_qty_difference": share_diff,
                                    "share_qty_difference_percentage": share_diff_pct,
                                    "market_value_difference": float(value_diff),
                                    "market_value_difference_percentage": str(
                                        value_diff_pct
                                    ),
                                },
                                "position_data": {
                                    "custodian": "BANK1",
                                    "market_value": float(position_value),
                                    "report_date": "2023-01-01",
                                    "share_qty": position_shares,
                                },
                                "trade_data": {
                                    "custodians": expected_custodians,
                                    "market_value": float(trade_value_for_calc),
                                    "share_qty": (
                                        trade_shares if trade_shares is not None else 0
                                    ),
                                },
                                "threshold": expected_threshold,
                            }
                        ]

                    assert response_data == expected_response

    def test_compliance_concentration_missing_date(self):
        """Test compliance concentration endpoint without date parameter"""
        with app.test_client() as client:
            response = client.get("/compliance/concentration")
            assert response.status_code == 400

"""
Unit tests for controllers module
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, mock_open, patch

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

    @patch("probable_train.controllers.ingest.dateparser.parse")
    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    def test_ingest_trade2_success(self, mock_session, mock_get_account, mock_parse):
        """Test successful ingestion of trade2 PSV file"""
        # Mock date parsing
        mock_parse.return_value = MagicMock(date=lambda: "2023-01-01")

        # Mock account
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_get_account.return_value = mock_account

        # Mock PSV data (pipe-separated)
        psv_data = (
            "ACCOUNT_ID|SECURITY_TICKER|SHARES|MARKET_VALUE|"
            "SOURCE_SYSTEM|REPORT_DATE\n"
            "ACC001|AAPL|100|15025.00|BROKER1|20230101\n"
            "ACC002|GOOGL|50|125025.00|BROKER2|20230102"
        )

        with patch("builtins.open", mock_open(read_data=psv_data)):
            ingest_trade2("dummy_path.psv")

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
        assert first_trade.custodian == "BROKER1"

        # Verify date parsing was called with correct format (check last call)
        mock_parse.assert_called_with("20230102", date_formats=["%Y%m%d"])


class TestIngestPosition:
    """Test cases for ingest_position function"""

    @patch("probable_train.controllers.ingest.dateparser.parse")
    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    def test_ingest_position_success(self, mock_session, mock_get_account, mock_parse):
        """Test successful ingestion of position YAML file"""
        # Mock date parsing
        mock_parse.return_value = MagicMock(date=lambda: "2023-01-01")

        # Mock account
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_get_account.return_value = mock_account

        # Mock YAML data
        yaml_data = {
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
        }

        with patch("builtins.open", mock_open()):
            with patch("yaml.safe_load", return_value=yaml_data):
                ingest_position("dummy_path.yaml")

        # Verify account creation was called
        assert mock_get_account.call_count == 2

        # Verify positions were added to session
        mock_session.add_all.assert_called_once()
        positions_added = mock_session.add_all.call_args[0][0]
        assert len(positions_added) == 2

        # Verify first position
        first_position = positions_added[0]
        assert first_position.account_id == "ACC001"
        assert first_position.ticker == "AAPL"
        assert first_position.share_qty == 100
        assert first_position.market_value == Decimal("15025.00")
        assert first_position.custodian == "BANK1"


class TestIngestFile:
    """Test cases for ingest_file function"""

    @pytest.mark.parametrize(
        "ingest_type,file_extension,content_template",
        [
            (
                "trade1",
                "csv",
                lambda today: (
                    f"AccountID,Ticker,Quantity,Price,TradeType,TradeDate,SettlementDate\n"
                    f"ACC001,AAPL,100,150.25,BUY,{today},{today}"
                ),
            ),
            (
                "trade2",
                "psv",
                lambda today: (
                    f"ACCOUNT_ID|SECURITY_TICKER|SHARES|MARKET_VALUE|"
                    f"SOURCE_SYSTEM|REPORT_DATE\n"
                    f"ACC001|AAPL|100|15025.00|BROKER1|{today}"
                ),
            ),
            (
                "position",
                "yaml",
                lambda today: (
                    f"report_date: '{today}'\n"
                    f"positions:\n"
                    f"  - account_id: ACC001\n"
                    f"    ticker: AAPL\n"
                    f"    shares: 100\n"
                    f"    market_value: '15025.00'\n"
                    f"    custodian_ref: BANK1"
                ),
            ),
        ],
    )
    @patch("probable_train.controllers.ingest.get_or_create_account")
    @patch("probable_train.controllers.ingest.db_session")
    def test_ingest_file_formats(
        self,
        mock_session,
        mock_get_account,
        tmp_path,
        ingest_type,
        file_extension,
        content_template,
    ):
        """Test ingest_file with different file formats"""
        from datetime import date

        today = (
            date.today().strftime("%Y-%m-%d")
            if ingest_type == "trade1"
            else date.today().strftime("%Y%m%d")
        )

        # Mock dependencies
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_get_account.return_value = mock_account

        # Create test file
        content = content_template(today)
        test_file = tmp_path / f"test.{file_extension}"
        test_file.write_text(content)

        ingest_file(str(test_file), ingest_type)
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
    def test_get_reconciliation_report_with_data(self, mock_session, mock_jsonify):
        """Test reconciliation report with mock data"""
        # Mock accounts
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_session.query.return_value.all.return_value = [mock_account]

        # Mock positions query
        mock_position = MagicMock()
        mock_position.ticker = "AAPL"
        mock_position.share_qty = 100
        mock_position.market_value = Decimal("15025.00")
        mock_position.custodian = "BANK1"

        mock_session.execute.return_value.scalars.return_value.all.side_effect = [
            [mock_position],  # First call for positions
            [],  # Second call for trades
        ]

        result = get_reconciliation_report("2023-01-01")

        # Should return mocked jsonify response
        assert result is not None
        mock_jsonify.assert_called_once_with({})

        # Verify queries were called
        assert mock_session.execute.call_count == 2

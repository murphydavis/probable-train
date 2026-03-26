"""
Pytest configuration and fixtures
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_current_app():
    """Mock Flask current_app for all tests"""
    mock_app = MagicMock()
    mock_app.config = {
        "ALLOWED_EXTENSIONS": {"csv", "psv", "txt", "yaml", "yml"},
        "UPLOAD_FOLDER": "./uploads",
        "DATABASE_URI": "sqlite:///./test.db",
    }
    mock_app.logger = MagicMock()
    return mock_app


@pytest.fixture(autouse=True)
def setup_flask_mocks(mock_current_app, monkeypatch):
    """Setup Flask mocks for all tests"""
    # Patch current_app only in modules that use it
    monkeypatch.setattr(
        "probable_train.controllers.ingest.current_app", mock_current_app
    )
    monkeypatch.setattr("probable_train.utils.current_app", mock_current_app)


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    return session


@pytest.fixture
def sample_trade1_csv():
    """Sample trade1 CSV data"""
    return """AccountID,Ticker,Quantity,Price,TradeType,TradeDate,SettlementDate
ACC001,AAPL,100,150.25,BUY,2023-01-01,2023-01-03
ACC002,GOOGL,50,2500.50,SELL,2023-01-02,2023-01-04"""


@pytest.fixture
def sample_trade2_psv():
    """Sample trade2 PSV data"""
    return """ACCOUNT_ID|SECURITY_TICKER|SHARES|MARKET_VALUE|SOURCE_SYSTEM|REPORT_DATE
ACC001|AAPL|100|15025.00|BROKER1|20230101
ACC002|GOOGL|50|125025.00|BROKER2|20230102"""


@pytest.fixture
def sample_position_yaml():
    """Sample position YAML data"""
    return {
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

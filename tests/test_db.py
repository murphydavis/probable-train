"""
Unit tests for database module
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import NoResultFound

from probable_train.db.helper import get_or_create_account
from probable_train.db.models.reconciliation import Account


class TestDbHelper:
    """Test cases for database helper functions"""

    @patch("probable_train.db.helper.Account")
    def test_get_or_create_account_existing(self, mock_account_class):
        """Test get_or_create_account when account exists"""
        # Setup
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = "ACC001"
        mock_session.get_one.return_value = mock_account

        # Execute
        result = get_or_create_account(mock_session, "ACC001")

        # Verify
        assert result == mock_account
        mock_session.get_one.assert_called_once_with(mock_account_class, "ACC001")
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    @patch("probable_train.db.helper.Account")
    def test_get_or_create_account_new(self, mock_account_class):
        """Test get_or_create_account when account doesn't exist"""
        # Setup
        mock_session = MagicMock()
        mock_session.get_one.side_effect = NoResultFound()

        mock_new_account = MagicMock()
        mock_new_account.id = "ACC001"
        mock_account_class.return_value = mock_new_account

        # Execute
        result = get_or_create_account(mock_session, "ACC001")

        # Verify
        assert result == mock_new_account
        mock_session.get_one.assert_called_once_with(mock_account_class, "ACC001")
        mock_account_class.assert_called_once_with(id="ACC001")
        mock_session.add.assert_called_once_with(mock_new_account)
        mock_session.commit.assert_called_once()


class TestDbModels:
    """Test cases for database models"""

    @pytest.mark.parametrize(
        "model_class,init_args,expected_attributes",
        [
            (
                "Account",
                {"id": "ACC001"},
                {"id": "ACC001"},
            ),
            (
                "Position",
                {
                    "account_id": "ACC001",
                    "custodian": "BANK1",
                    "market_value": Decimal("15025.00"),
                    "report_date": date(2023, 1, 1),
                    "share_qty": 100,
                    "ticker": "AAPL",
                },
                {
                    "account_id": "ACC001",
                    "custodian": "BANK1",
                    "market_value": Decimal("15025.00"),
                    "report_date": date(2023, 1, 1),
                    "share_qty": 100,
                    "ticker": "AAPL",
                    "id": None,
                },
            ),
            (
                "Trade",
                {
                    "account_id": "ACC001",
                    "custodian": "BROKER1",
                    "market_value": Decimal("15025.00"),
                    "settlement_date": date(2023, 1, 3),
                    "share_qty": 100,
                    "ticker": "AAPL",
                    "trade_date": date(2023, 1, 1),
                },
                {
                    "account_id": "ACC001",
                    "custodian": "BROKER1",
                    "market_value": Decimal("15025.00"),
                    "settlement_date": date(2023, 1, 3),
                    "share_qty": 100,
                    "ticker": "AAPL",
                    "trade_date": date(2023, 1, 1),
                    "id": None,
                },
            ),
            (
                "Trade",
                {
                    "account_id": "ACC001",
                    "custodian": "BROKER1",
                    "market_value": Decimal("15025.00"),
                    "settlement_date": date(2023, 1, 3),
                    "share_qty": 100,
                    "ticker": "AAPL",
                    # trade_date omitted
                },
                {
                    "account_id": "ACC001",
                    "custodian": "BROKER1",
                    "market_value": Decimal("15025.00"),
                    "settlement_date": date(2023, 1, 3),
                    "share_qty": 100,
                    "ticker": "AAPL",
                    "trade_date": None,
                    "id": None,
                },
            ),
        ],
    )
    def test_model_creation(self, model_class, init_args, expected_attributes):
        """Test database model creation"""
        from datetime import date
        from decimal import Decimal
        from probable_train.db.models.reconciliation import Account, Position, Trade

        model_classes = {"Account": Account, "Position": Position, "Trade": Trade}
        model_class_obj = model_classes[model_class](**init_args)

        for attr, expected_value in expected_attributes.items():
            assert getattr(model_class_obj, attr) == expected_value

        # Test create_ts attribute exists for Account
        if model_class == "Account":
            assert hasattr(model_class_obj, "create_ts")

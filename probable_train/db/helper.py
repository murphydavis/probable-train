#!/usr/bin/env python3
"""
Database-specific helper functions
This is probably overkill here but establishes a basic pattern
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from probable_train.db.models.reconciliation import Account


def get_or_create_account(session, account_id):
    account = None
    try:
        account = session.get_one(Account, account_id)
    except NoResultFound:
        account = Account(id=account_id)

    return account

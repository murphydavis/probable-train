"""
Database-specific helper functions
This is probably overkill here but establishes a basic pattern
"""

from sqlalchemy.exc import NoResultFound

from probable_train.db.models.reconciliation import Account


def get_or_create_account(session, account_id):
    account = None
    try:
        account = session.get_one(Account, account_id)
    except NoResultFound:
        account = Account(id=account_id)
        # It's not the most efficient approach to commit every time
        # but is a limitation of sqlite
        session.add(account)
        session.commit()

    return account

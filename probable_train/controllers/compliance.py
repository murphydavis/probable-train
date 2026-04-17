"""
Controller for compliance logic and associated helpers
"""


from probable_train.db import db_session
from probable_train.db.models.reconciliation import Account, Position


def get_concentration_breaches(report_date, threshold=0.2):
    """
    Get accounts and tickers where the concentration of any single ticker
    exceeds the specified threshold percentage of the total portfolio value.

    Args:
        report_date: Date to check for breaches
        threshold: Threshold percentage (default 0.2 for 20%)

    Returns:
        dict: Contains date, threshold, breaches list, and total breaches count
    """
    from sqlalchemy import func

    # Single ORM query with HAVING clause to only return breached accounts and tickers
    breach_results = (
        db_session.query(
            Account.id.label('account_id'),
            Position.ticker.label('ticker'),
            Position.share_qty.label('share_qty'),
            Position.market_value.label('market_value'),
            Position.custodian.label('custodian'),
            Position.report_date.label('report_date'),
            func.sum(Position.market_value).over(
                partition_by=Account.id
            ).label('total_portfolio_value'),
            (Position.market_value / func.sum(Position.market_value).over(
                partition_by=Account.id
            )).label('concentration_percentage')
        )
        .join(Position, Account.id == Position.account_id)
        .filter(Position.report_date <= report_date)
        .filter(
            func.row_number().over(
                partition_by=(Account.id, Position.ticker),
                order_by=Position.report_date.desc()
            ) == 1
        )
        .having(
            (Position.market_value / func.sum(Position.market_value).over(
                partition_by=Account.id
            )) > threshold
        )
        .all()
    )

    # Format breach results
    breaches = []
    for result in breach_results:
        breaches.append({
            "account_id": result.account_id,
            "ticker": result.ticker,
            "position_data": {
                "share_qty": result.share_qty,
                "market_value": float(result.market_value),
                "custodian": result.custodian,
                "report_date": result.report_date.isoformat(),
            },
            "portfolio_data": {
                "total_portfolio_value": float(result.total_portfolio_value),
                "concentration_percentage": float(result.concentration_percentage),
            },
            "threshold": threshold,
            "breach_type": "concentration",
        })

    return {
        "date": report_date.isoformat(),
        "threshold": threshold,
        "breaches": breaches,
    }

"""
Controller for file ingest logic and associated helpers
"""

# TODO: get proper logic for this report
from flask import jsonify
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import outerjoin

from probable_train.db import db_session
from probable_train.db.models.reconciliation import Account, Position, Trade


def get_reconciliation_report(report_date):
    """
    Reconciliation report comparing cumulative trades up to report date
    against current positions for the same date.

    Args:
        report_date: Date to check reconciliation for

    Returns:
        JSON response with reconciliation data by account and ticker
    """

    # Get cumulative trades up to report date for each account/ticker
    cumulative_trades = (
        select(
            Trade.account_id,
            Trade.ticker,
            func.sum(Trade.share_qty).label('total_trade_shares'),
            func.sum(Trade.market_value).label('total_trade_market_value'),
            func.array_agg(Trade.custodian.distinct()).label('trade_custodians'),
            func.min(Trade.trade_date).label('first_trade_date'),
            func.max(Trade.trade_date).label('last_trade_date')
        )
        .filter(Trade.settlement_date <= report_date)
        .group_by(Trade.account_id, Trade.ticker)
        .subquery()
    )

    # Get latest positions for report date
    latest_positions = (
        select(
            Position.account_id,
            Position.ticker,
            Position.share_qty.label('position_shares'),
            Position.market_value.label('position_market_value'),
            Position.custodian.label('position_custodian'),
            Position.report_date,
            func.row_number().over(
                partition_by=(Position.account_id, Position.ticker),
                order_by=Position.report_date.desc()
            ).label('rn')
        )
        .filter(Position.report_date <= report_date)
        .subquery()
    )

    # Join trades and positions to get reconciliation data
    reconciliation_query = (
        select(
            Account.id.label('account_id'),
            func.coalesce(
                latest_positions.c.ticker, cumulative_trades.c.ticker
            ).label('ticker'),
            latest_positions.c.position_shares,
            latest_positions.c.position_market_value,
            latest_positions.c.position_custodian,
            latest_positions.c.report_date,
            cumulative_trades.c.total_trade_shares,
            cumulative_trades.c.total_trade_market_value,
            cumulative_trades.c.trade_custodians,
            cumulative_trades.c.first_trade_date,
            cumulative_trades.c.last_trade_date
        )
        .select_from(
            outerjoin(
                Account,
                latest_positions,
                and_(
                    Account.id == latest_positions.c.account_id,
                    latest_positions.c.rn == 1
                )
            )
        )
        .outerjoin(
            cumulative_trades,
            and_(
                Account.id == cumulative_trades.c.account_id,
                latest_positions.c.ticker == cumulative_trades.c.ticker
            )
        )
        .where(
            or_(
                latest_positions.c.account_id.isnot(None),
                cumulative_trades.c.account_id.isnot(None)
            )
        )
    )

    results = db_session.execute(reconciliation_query).all()

    # Build reconciliation report
    reconciliation_report = {}

    for row in results:
        account_id = row.account_id
        ticker = row.ticker

        if account_id not in reconciliation_report:
            reconciliation_report[account_id] = {}

        # Calculate differences
        position_shares = row.position_shares or 0
        trade_shares = row.total_trade_shares or 0
        shares_difference = position_shares - trade_shares

        position_value = (
            float(row.position_market_value) if row.position_market_value else 0
        )
        trade_value = (
            float(row.total_trade_market_value) if row.total_trade_market_value else 0
        )
        value_difference = position_value - trade_value

        # Determine reconciliation status
        has_position = row.position_shares is not None
        has_trades = row.total_trade_shares is not None

        if has_position and has_trades:
            # Check if values match (allowing for small floating point differences)
            shares_match = abs(shares_difference) < 0.01  # Allow 0.01 share tolerance
            value_match = abs(value_difference) < 0.01  # Allow $0.01 tolerance

            if shares_match and value_match:
                status = "reconciled"
            else:
                status = "discrepancy"
        elif has_position and not has_trades:
            status = "position_only"
        elif not has_position and has_trades:
            status = "trades_only"
        else:
            continue  # This should never happen based on our WHERE clause  # pragma: no cover

        ticker_report = {
            "ticker": ticker,
            "reconciliation_status": status,
            "position_data": {
                "shares": row.position_shares,
                "market_value": (
                    float(row.position_market_value)
                    if row.position_market_value else None
                ),
                "custodian": row.position_custodian,
                "report_date": row.report_date.isoformat() if row.report_date else None
            } if has_position else None,
            "cumulative_trades_data": {
                "total_shares": row.total_trade_shares,
                "total_market_value": (
                    float(row.total_trade_market_value)
                    if row.total_trade_market_value else None
                ),
                "custodians": row.trade_custodians or [],
                "first_trade_date": (
                    row.first_trade_date.isoformat() if row.first_trade_date else None
                ),
                "last_trade_date": (
                    row.last_trade_date.isoformat() if row.last_trade_date else None
                )
            } if has_trades else None,
            "differences": {
                "shares_difference": shares_difference,
                "market_value_difference": value_difference
            } if (has_position and has_trades) else None
        }

        reconciliation_report[account_id][ticker] = ticker_report

    return jsonify(reconciliation_report)

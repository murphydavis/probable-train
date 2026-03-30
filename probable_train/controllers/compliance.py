"""
Controller for compliance logic and associated helpers
"""

from sqlalchemy import and_, select

from probable_train.db import db_session
from probable_train.db.models.reconciliation import Account, Position, Trade


def get_concentration_breaches(report_date, threshold=0.2):
    """
    Get accounts and tickers where the difference between position and trade data
    exceeds the specified threshold percentage.

    Args:
        report_date: Date to check for breaches
        threshold: Threshold percentage (default 0.2 for 20%)

    Returns:
        dict: Contains date, threshold, breaches list, and total breaches count
    """
    # Get all accounts
    accounts = db_session.query(Account).all()
    breaches = []

    for account in accounts:
        # Get latest position for each ticker up to the specified date
        position_stmt = (
            select(Position)
            .where(
                and_(
                    Position.account_id == account.id,
                    Position.report_date <= report_date,
                )
            )
            .order_by(Position.report_date.desc())
        )
        positions = db_session.execute(position_stmt).scalars().all()

        # Get sum of all trades for each ticker up to the specified date
        trade_stmt = select(Trade).where(
            and_(
                Trade.account_id == account.id,
                Trade.settlement_date <= report_date,
            )
        )
        trades = db_session.execute(trade_stmt).scalars().all()

        # Aggregate trades by ticker and sum them, collecting custodians
        trade_sums = {}
        for trade in trades:
            if trade.ticker not in trade_sums:
                trade_sums[trade.ticker] = {
                    "share_qty": 0,
                    "market_value": 0,
                    "custodians": set(),
                }
            trade_sums[trade.ticker]["share_qty"] += trade.share_qty
            trade_sums[trade.ticker]["market_value"] += trade.market_value
            trade_sums[trade.ticker]["custodians"].add(trade.custodian)

        # Get latest position for each ticker (handle multiple positions per ticker)
        latest_positions = {}
        for position in positions:
            if (
                position.ticker not in latest_positions
                or position.report_date > latest_positions[position.ticker].report_date
            ):
                latest_positions[position.ticker] = position

        # Check for breaches
        for ticker, position in latest_positions.items():
            trade_data = trade_sums.get(
                ticker, {"share_qty": 0, "market_value": 0, "custodians": set()}
            )

            # Calculate percentage differences
            share_diff_pct = (
                abs(trade_data["share_qty"] - position.share_qty)
                / abs(position.share_qty)
                if position.share_qty != 0
                else 0
            )
            market_value_diff_pct = (
                abs(trade_data["market_value"] - position.market_value)
                / abs(position.market_value)
                if position.market_value != 0
                else 0
            )

            # Check if either difference exceeds threshold
            if share_diff_pct > threshold or market_value_diff_pct > threshold:
                breaches.append(
                    {
                        "account_id": account.id,
                        "ticker": ticker,
                        "position_data": {
                            "share_qty": position.share_qty,
                            "market_value": float(position.market_value),
                            "custodian": position.custodian,
                            "report_date": position.report_date.isoformat(),
                        },
                        "trade_data": {
                            "share_qty": trade_data["share_qty"],
                            "market_value": float(trade_data["market_value"]),
                            "custodians": list(trade_data["custodians"]),
                        },
                        "differences": {
                            "share_qty_difference": trade_data["share_qty"]
                            - position.share_qty,
                            "share_qty_difference_percentage": share_diff_pct,
                            "market_value_difference": float(
                                trade_data["market_value"] - position.market_value
                            ),
                            "market_value_difference_percentage": market_value_diff_pct,
                        },
                        "threshold": threshold,
                        "breach_type": [],
                    }
                )

                # Determine which thresholds were breached
                if share_diff_pct > threshold:
                    breaches[-1]["breach_type"].append("share_quantity")
                if market_value_diff_pct > threshold:
                    breaches[-1]["breach_type"].append("market_value")

    return {
        "date": report_date.isoformat(),
        "threshold": threshold,
        "breaches": breaches,
        "total_breaches": len(breaches),
    }

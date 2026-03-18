#!/usr/bin/env python3
"""
Controller for file ingest logic and associated helpers
"""

import csv
from decimal import Decimal

import dateparser
from flask import current_app
import yaml

from probable_train.db import db_session
from probable_train.db.helper import get_or_create_account
from probable_train.db.models.reconciliation import Position, Trade


def ingest_trade1(filepath):
    with open(filepath) as file:
        reader = csv.DictReader(file, delimiter=",")
        trade_data = []
        for row in reader:
            try:
                share_qty = int(row["Quantity"])
                if row["TradeType"] == "SELL":
                    share_qty *= -1
                share_price = Decimal(row["Price"])
                trade_date = dateparser.parse(row["TradeDate"]).date()
                settlement_date = dateparser.parse(row["SettlementDate"]).date()
            except ValueError:
                current_app.logger.exception("Malformed row data: {row}")
                continue
            # get or create account at the end so it's only done on valid rows
            account = get_or_create_account(db_session, row["AccountID"])

            trade_data.append(
                Trade(
                    trade_date=trade_date,
                    account_id=account.id,
                    custodian="",  # not present in format
                    market_value=share_qty * share_price,
                    settlement_date=settlement_date,
                    share_qty=share_qty,
                    ticker=row["Ticker"],
                )
            )
        db_session.add_all(trade_data)


def ingest_trade2(filepath):
    with open(filepath) as file:
        reader = csv.DictReader(file, delimiter="|")
        trade_data = []
        for row in reader:
            try:
                share_qty = int(row["SHARES"])
                market_value = Decimal(row["MARKET_VALUE"])
                report_date = dateparser.parse(
                    row["REPORT_DATE"], date_formats=["%Y%m%d"]
                ).date()
            except ValueError:
                current_app.logger.exception("Malformed row data: {row}")
                continue
            # get or create account at the end so it's only done on valid rows
            account = get_or_create_account(db_session, row["ACCOUNT_ID"])

            trade_data.append(
                Trade(
                    # trade_date = None # omitted bc not present in file
                    account_id=account.id,
                    custodian=row["SOURCE_SYSTEM"],
                    market_value=market_value,
                    settlement_date=report_date,
                    share_qty=share_qty,
                    ticker=row["SECURITY_TICKER"],
                )
            )
        db_session.add_all(trade_data)


def ingest_position(filepath):
    with open(filepath) as file:
        bank_positions = yaml.safe_load(file)
    position_data = []
    report_date = dateparser.parse(
        bank_positions["report_date"], date_formats=["%Y%m%d"]
    ).date()
    for position in bank_positions["positions"]:
        try:
            share_qty = int(position["shares"])
            market_value = Decimal(position["market_value"])
        except ValueError:
            current_app.logger.exception("Malformed row data: {row}")
            continue
        # get or create account at the end so it's only done on valid rows
        account = get_or_create_account(db_session, position["account_id"])

        position_data.append(
            Position(
                account_id=account.id,
                custodian=position["custodian_ref"],
                market_value=market_value,
                report_date=report_date,
                share_qty=share_qty,
                ticker=position["ticker"],
            )
        )
    db_session.add_all(position_data)


INGEST_FUNCTIONS = {
    "trade1": ingest_trade1,
    "trade2": ingest_trade2,
    "position": ingest_position,
}


def ingest_file(filepath, format):
    # read file contents

    # breakpoint()
    INGEST_FUNCTIONS[format](filepath)

    db_session.commit()
    return

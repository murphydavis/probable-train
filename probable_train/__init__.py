import logging
import sys

import dateparser
from flask import jsonify, Flask, request
from sqlalchemy import select
from sqlalchemy.orm import Session

from probable_train.db import db_session
from probable_train.db.models.reconciliation import Account, Position, Trade
from probable_train.utils import require_query_parameters

# some additional setup to get logging to stdout too
logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(levelname)s] - %(message)s", level=logging.INFO
)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

app = Flask(__name__)  # define the Flask app
app.config.from_pyfile("config.py")

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

# -------- API ENDPOINTS --------
# because there is a pretty limited number of endpoints, define them here
# if the number grew, factor routes out into blueprints
@app.route("/", methods=["GET"])
def index():
    """Default route"""
    app.logger.debug("this is a DEBUG message")
    # app.logger.info("this is an INFO message")
    # app.logger.warning("this is a WARNING message")
    # app.logger.error("this is an ERROR message")
    # app.logger.critical("this is a CRITICAL message")
    return jsonify("server online")


@app.route("/ingest", methods=["POST"])
def ingest():
    """
    load files and return data quality report
    """
    ingest_file = request.files
    pass


@app.route("/positions", methods=["GET"])
def positions():
    """
    retrieve positions with cost basis and market value

    parameters:
        - name: account
          in: query
          type: string
          required: true
          description: account ID
        - name: date
          in: query
          type: string
          required: true
          description: the date to check
    """
    require_query_parameters(request, ["account", "date"], strict=True)

    account = request.args.get("account")
    date = dateparser.parse(request.args.get("date"))

    query = select(Position).filter_by(account_id=account, report_date=date)
    # query=select(Position).where(Position.__table__.c.account_id == account)
    positions = db_session.scalars(query).all()

    acc = Account(id="TEST")
    pos = Position(id=1234, account_id="TEST")
    from sqlalchemy.dialects import sqlite
    qry = query.compile(dialect=sqlite.dialect())
    breakpoint()
    return positions


@app.route("/compliance/concentration", methods=["GET"])
def compliance_concentration():
    """
    retrieve accounts exceeding the threshold (default 20%) with breach details
    """
    require_query_parameters(request, ["date"], strict=True)
    pass


@app.route("/reconciliation", methods=["GET"])
def reconciliation():
    """
    retrieve trade vs position file discrepancies, optionally specifying date
    """
    require_query_parameters(request, ["date"], strict=True)
    pass


# start the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

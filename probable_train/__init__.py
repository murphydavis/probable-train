#!/usr/bin/env python3
from datetime import datetime
import logging
import os

import dateparser
from flask import abort, jsonify, Flask, request
from sqlalchemy import and_, select
# from sqlalchemy.orm import Session
# from werkzeug.utils import secure_filename

from probable_train.controllers.ingest import ingest_file
from probable_train.controllers.reconciliation import get_reconciliation_report
from probable_train.db import db_session
from probable_train.db.models.reconciliation import Position
from probable_train.utils import allowed_file, require_query_parameters

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

    form-data
      - name: file
        in: files
        type: file
        required: true
        description: the file to ingest
      - name: ftype
        in: form
        type: string
        required: true
        description: the ingest data type, selected from trade1, trade2, or position
    """
    # check and save file in uploads
    file = request.files.get("file")
    ftype = request.form.get("ftype")
    if file is None:
        abort(400, description="No file part found")
    ext = file.filename.rsplit(".", 1)[1]
    if not allowed_file(file.filename):
        abort(400, description=f"Invalid file extension: '{ext}'")
    if ftype is None:
        abort(400, description="No file type specified")
    if ftype not in app.config["INGEST_TYPES"]:
        abort(400, description=f"Invalid ingest type: '{ftype}'")

    # filename = secure_filename(file.filename)
    # save ingest file with unique name to prevent overwriting existing files
    # should OG filename be preserved? Could append a UUID or put in unique folder
    filename = f"{datetime.utcnow()}.{ext}"
    full_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(full_path)
    logger.info(f"New upload file {file.filename} saved at {full_path}")

    # ingest file into database
    ingest_file(full_path, ftype)

    return jsonify("File ingestion successful")


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
    date = dateparser.parse(request.args.get("date"), date_formats=["%Y%m%d"]).date()
    query = select(Position).where(
        and_(Position.account_id == account, Position.report_date <= date)
    )
    raw_positions = db_session.scalars(query).all()
    keys = {
        "account_id",
        "custodian",
        "id",
        "report_date",
        "share_qty",
        "ticker",
    }
    positions = []
    for position in raw_positions:
        positions.append(
            {key: val for key, val in position.__dict__.items() if key in keys}
        )
    # TODO: This is admittedly *way* too rushed, clunky, and "clever" for its own good
    # At this point I believe this should be factored out into a separate controller

    return jsonify(positions)


# TODO: this is just a stub
@app.route("/compliance/concentration", methods=["GET"])
def compliance_concentration():
    """
    retrieve accounts exceeding the threshold (default 20%) with breach details

    parameters:
      - name: date
        in: query
        type: string
        required: true
        description: the date to check
    """
    require_query_parameters(request, ["date"], strict=True)
    return jsonify("")


@app.route("/reconciliation", methods=["GET"])
def reconciliation():
    """
    retrieve trade vs position file discrepancies, optionally specifying date

    parameters:
      - name: date
        in: query
        type: string
        required: true
        description: the date to check
    """
    require_query_parameters(request, ["date"], strict=True)

    date = dateparser.parse(request.args.get("date"), date_formats=["%Y%m%d"]).date()
    return get_reconciliation_report(date)


# start the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

"""
API route definitions for the probable_train application
"""

from datetime import datetime
import os

import dateparser
from flask import abort, jsonify, request
from sqlalchemy import and_, select

from probable_train.controllers.compliance import get_concentration_breaches
from probable_train.controllers.reconciliation import get_reconciliation_report
from probable_train.db.models.reconciliation import Position
from probable_train.utils import allowed_file, require_query_parameters

from . import app, db_session, logger


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
    from probable_train.controllers.ingest import ingest_file

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
      - name: threshold
        in: query
        type: float
        required: false
        description: threshold percentage (default 0.2 for 20%)
    """
    require_query_parameters(request, ["date"], strict=True)

    date = dateparser.parse(request.args.get("date"), date_formats=["%Y%m%d"]).date()
    threshold = float(request.args.get("threshold", 0.2))

    breaches_data = get_concentration_breaches(date, threshold)
    return jsonify(breaches_data)


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

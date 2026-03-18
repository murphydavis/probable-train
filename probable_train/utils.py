#!/usr/bin/env python3
"""
This file contains miscellaneous utilities.
If you write the same code or pattern 3+ times, consider making it a function here!
"""

import logging

from flask import current_app, abort


logger = logging.getLogger(__name__)


def require_query_parameters(request, parameters, strict=False):
    """
    identify which required query parameters are missing, abort if strict
    """
    parameters = set(parameters)
    keys = set(request.args.keys())
    missing = parameters.difference(keys)

    if missing and strict:
        abort(400, description=f"Missing required parameters: {missing}")

    return missing


def allowed_file(filename):
    filename = filename.lower()
    config = current_app.config
    return (
        "." in filename and filename.rsplit(".", 1)[1] in config["ALLOWED_EXTENSIONS"]
    )

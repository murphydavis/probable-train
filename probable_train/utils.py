#!/usr/bin/env python3
"""
This file contains miscellaneous utilities.
If you write the same code or pattern 3+ times, consider making it a function here!
"""

from flask import abort


def require_query_parameters(request, parameters, strict=False):
    """
    identify which required query parameters are missing, abort if strict
    """
    keys = set(request.args.keys)
    missing = keys.difference(parameters)

    if missing and strict:
        abort(400, message=f"Missing required parameters: {missing}")

    return missing


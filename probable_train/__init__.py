#!/usr/bin/env python3
import logging

from flask import Flask

from probable_train.db import db_session

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


# Import routes to register them with the app
# This import is intentionally placed after app creation to avoid circular imports
import probable_train.routes as routes  # noqa: E402, F401

# start the app
if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=8000, debug=True)

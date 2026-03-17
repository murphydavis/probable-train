from flask import Flask, request

from probable_train.utils import require_query_parameters


app = Flask(__name__)  # define the Flask app


# because there is a pretty limited number of endpoints, define them here
# if the number grew, factor routes out into blueprints
@app.route("/", methods=["GET"])
def index():
    import pprint; pprint.pprint(request.__dict__)
    return "A certain train is probably better than a probable one"


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
    require_query_parameters(request, ['account', 'date'], strict=True)
    account = request.args.get('account')
    pass


@app.route("/compliance/concentration", methods=["GET"])
def compliance_concentration():
    """
    retrieve accounts exceeding the threshold (default 20%) with breach details
    """
    require_query_parameters(request, ['date'], strict=True)
    pass


@app.route("/reconciliation", methods=["GET"])
def reconciliation():
    """
    retrieve trade vs position file discrepancies, optionally specifying date
    """
    require_query_parameters(request, ['date'], strict=True)
    pass


# start the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

# probable-train
Vest Financial take home project

## Installation and use
All you should need to have installed is `uv` in order to get things working. Before
running the first time, we need to install and initialize the database, like so:
```bash
$ uv sync
$ uv run python -c "from probable_train.db import init_db; init_db()"
```
In the case that you ever want to start fresh, you may either
1. delete the `probabletrain.db` file and run the above python command again
2. use sqlite to access the database and delete all records from the account, position,
and trade tables

Then, to run the server, you can use either
```bash
# This runs the built in Flask HTTP server on port 5000, 
$ ./run_debug.sh

# This runs the application with gunicorn on port 8000, which is more production suited
$ ./run.sh
```
With this, you should be up and running and good to go! To demonstrate that the server
is running, just hit the base endpoint, either in a browser or like so:
```bash
$ curl "localhost:5000/"
```
Once this endpoint returns 200 with "server online" then you can hit the other
endpoints. For `/positions` you must specify `account` with account ID and `date`
in the url query parameters, and any missing parameters will result in a 400 
with a specific message as to the issue at hand:
```bash
$ curl "localhost:5000/positions?date=2026-03-16"
```
will give you
```html
<!doctype html>
<html lang=en>
<title>400 Bad Request</title>
<h1>Bad Request</h1>
<p>Missing required parameters: {&#39;date&#39;}</p>
```
And correct use will look more like the following:
```bash
$ curl "localhost:5000/positions?date=2026-03-18&account=ACC001"
```
yielding results like:
```json
[
  {
    "account_id": "ACC001",
    "custodian": "CUST_A_12345",
    "id": 1,
    "report_date": "Wed, 15 Jan 2025 00:00:00 GMT",
    "share_qty": 100,
    "ticker": "AAPL"
  }
]
```
Note that currently, a 400 will return an HTML document, while all successful queries
return as JSON objects. Similarly to `/positions`, for the reconciliation and 
compliance endpoints, you must specify `date`:
```bash
$ curl "localhost:5000/reconciliation?date=2025-01-14"
$ curl "localhost:5000/reconciliation?date=20250127"
$ curl "localhost:5000/compliance/concentration?date=20250127"
```
Note that you may use either YYYY-MM-DD or YYYYMMDD format, which I will use
interchangeably in these examples. If you are doing these in order, you will also note
that the results are empty, because you have not ingested any data. I have included
the sample documents provided in the top level `static` directory,
which you can ingest with the aptly named `/ingest` endpoint. From the top level of the
repository, you can ingest files in the following manner:
```bash
curl -F file=@static/trade1.csv -F ftype=trade1 "localhost:5000/ingest"
curl -F file=@static/trade2.psv -F ftype=trade2 "localhost:5000/ingest"
curl -F file=@static/position.yml -F ftype=position "localhost:5000/ingest"
```
You must use a properly formatted file with a valid permitted file extension, as well
as a valid ftype. If either part is missing or invalid, you will get a 400 error
detailing the issue.
Each of these can be repeated multiple times at this point, which *WILL* result in
duplicate records at the moment: I need a better understanding of the domain logic
to more clearly flesh this out - ideally each file can only be ingested once.

Also note that there is no file ingest or other endpoint to create accounts, which do
still exist in the database with a foreign key relation to trade and position records.
Account records are automatically created upon ingestion of other files if no matching
account exists, and they will not be duplicated.

## Top level dependencies

* `flask`
    REST API framework
* `sqlalchemy`
    Database driver and ORM
* `dateparser`
    Used for simple date parsing from URL query parameters
* `PyYAML`
    Basic YAML parsing library for loading bank position report
* `gunicorn`
    This is the WSGI server, used to run the server in a more robust manner than the
    built-in Flask server, which is intended for testing purposes

### Dev dependencies
* `ipython`
    This is a personal favorite, just a few more interactive niceties for the CLI

## Configuration
Right now there's not much to configure, but there are a few you may tweak.
- `gunicorn.conf.py` gunicorn configuration
  - Here, if you really wanted, you can configure the IP or port the application is
    served on, the number of workers to use, log level, and where logs are stored.
- `probable_train/config.py` flask application config
  - `DEBUG`: whether flask runs in debug mode, left `True` for development
    (we're not quite prod ready yet)
  - `ALLOWED_EXTENSIONS`: the set of all file extensions permitted by the ingestion
    endpoint. does not determine how a file is handled.
  - `INGEST_TYPES`: this is the set of possible options for ingest type, which
    determines how ingest is routed right now. may be obsoleted if file type detection
    is added or different ingests are split into separate endpoints.
  - `UPLOAD_FOLDER`: when files are uploaded, they are stored here for record keeping.
    for a production release I would hope to have this use a S3 location or similar.
  - `DATABASE_URI`: the URI of the database, crazy enough. In the future of course this
    would likely be hosted on a separate server using Postgres or another more robust
    database.


## Basic design concepts and directory structure
The base directory contains several files and folders:
- `LICENSE`/`README.md`/`pyproject.toml`/`uv.lock`
  * These files are the same as they would be in any other Python project.
- `static/`
  * This directory contains various static files, at this point test files for the
  ingest process.
- `uploads/`
  * This directory is used by the application to store all uploaded files. The original
  filenames and extensions are discarded, and the files renamed with a timestamp.
- `tests/`
  * This file contains tests, which includes unit tests and integration tests.
  **not yet implemented**
- `probabletrain.db`
  * If you have initialized the database, by default it will be stored as a file in this
  top level directory.
- `debug.log`
  * Another application default, once the application has been run logs will be stored
  in this text file.
- `run.sh`/`run_debug.sh`
  * These scripts are used to run the server with gunicorn and the flask development
  server, respectively.
- `probable_train/`
  * This directory contains the actual application code, and I will explain the
  highlights.
  - `__init__.py`: This file contains the app definition, and at this stage all route
  definitions. Ideally the routes would be factored out into a separate routes file or
  multiple blueprints if there are multiple logical groupings.
  - `config.py`: This file contains the flask app configuration.
  - `utils.py`: This file is for basic helper functions that don't have another logical
  home and serve a general purpose.
  - `controllers/`: This directory contains files that contain definitions of business
  logic, the heart of the application's functionality.
  - `db/` and `db/models/`: This directory and subdirectory contain all the code for
  initializing and connecting to the database, as well as all ORM models, which are the
  basic operating units of the application.

```
├── LICENSE
├── README.md
├── gunicorn.conf.py
├── probable_train/
│   ├── __init__.py
│   ├── config.py/
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── ingest.py
│   │   └── reconciliation.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── helper.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── reconciliation.py
│   │   └── tree.md
│   └── utils.py
├── probabletrain.db
├── pyproject.toml
├── run.sh
├── run_debug.sh
├── static/
│   ├── position.txt
│   ├── position.yml
│   ├── trade1.csv
│   ├── trade2.psv
│   └── trade3.tsv
├── tests/
├── uploads/
└── uv.lock
```

## Future Improvements
Get CORRECT logic for reconciliation/compliance calculations. This is probably far and
away priority #1 and the biggest mistake here.

Implement proper unit tests! Right now I basically just have integration tests, but I
have tried to keep my own logic largely factored into testable units. I am apprehensive
about test driven development because wrinkles are always revealed in the course of
implementation.

Register a custom error handler so that 400s and other errors *also* return JSON so
that this application can more smoothly be integrated as a microservice

I think I would like to use some sort of marshalling for the url parameters, such as
Marshmallow - I almost did but needed to reel my ambition back in some

I would like to add OpenAPI docs, potentially with a Flask extension, but left fully
to my own devices I would use FastAPI

I would like to keep the configuration stored locally as minimal as possible, or only
use that for local development purposes. For a proper deployment, keep as much
configuration as possible out of the code, in a place such as AWS Secrets Manager.
This is both secure *and* allows the flexibility of configuration changes without the
need for any code deployment.

Unit tests should have a required coverage percentage - probably not as a commit hook
though, so I guess that's a bit more DevOps

Use a more "proper" database - probably PostgreSQL, potentially via Amazon RDS.
If I fully committed to AWS I would also like to store upload files in S3.

Clean up the db initialization, I have the db file specified twice because I was
fighting app context but I'm probably being silly there.

Minor, but probably migrate to using a .env file for configs, another personal
preference but it's always seemed the "cleanest"

Using Celery or similar, make file upload an async task, so that potential long running
ingest processes don't cause requests to be slow, and expose an endpoint to inspect the
state of ingest jobs. Overall better experience to keep endpoints snappy when practical.
Right now this isn't necessary as files are small and ingestion is fast.

For file ingestion, could add the ability to automatically determine file type, but
arguably I could split trade and position ingestion to separate endpoints too, to keep
each API endpoint single-purpose

Use a ticketing system to track this wishlist (joke) (or is it?)

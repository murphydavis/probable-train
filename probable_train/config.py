# General configuration
DEBUG = True

# Ingest configuration
ALLOWED_EXTENSIONS = {
    "csv",
    "psv",
    "txt",
    "yaml",
    "yml",
}
INGEST_TYPES = {
    "trade1",
    "trade2",
    "position",
}
UPLOAD_FOLDER = "./uploads"

# Database configuration
DATABASE_URI = "sqlite:///./probabletrain.db"

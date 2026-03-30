from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine, Numeric, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

engine = create_engine("sqlite:///./probabletrain.db")
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)


# for any potential global changes
# ProbableTrainBase = declarative_base()
class ProbableTrainBase(DeclarativeBase):
    type_annotation_map = {
        datetime: TIMESTAMP(timezone=True),
        Decimal: Numeric(12, 2),
    }


ProbableTrainBase.query = db_session.query_property()


def init_db():  # pragma: no cover
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import probable_train.db.models  # noqa: F401

    ProbableTrainBase.metadata.create_all(bind=engine)

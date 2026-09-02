import os
from typing import Generator

from sqlmodel import Session, create_engine

# Neon pooled connection. Set in .env:
#   DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, echo=False)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


# This module — and everything under database/ — is the ONLY place allowed
# to import SQLModel/SQLAlchemy per database/README.md rule 5:
#   "อย่าให้ Core service import ORM หรือ storage client โดยตรง"
# core/* modules must only ever see a Protocol + a plain dataclass.
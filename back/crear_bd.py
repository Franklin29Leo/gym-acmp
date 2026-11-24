"""Crea la base de datos (si no existe) y las tablas. Uso: python crear_bd.py"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import settings
from app.db import Base, engine
from app import models  # noqa: F401

url = make_url(settings.database_url)
admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
with admin.connect() as c:
    if not c.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}):
        c.execute(text(f'CREATE DATABASE "{url.database}" ENCODING \'UTF8\' TEMPLATE template0'))
        print(f"Base de datos '{url.database}' creada.")
    else:
        print(f"La base de datos '{url.database}' ya existe.")
Base.metadata.create_all(engine)
print("Tablas listas.")

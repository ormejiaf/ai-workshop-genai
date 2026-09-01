"""Compatibilidad para Oracle Linux 9, cuya SQLite de sistema es anterior a Chroma."""

import sys


def enable_modern_sqlite() -> None:
    import sqlite3

    if sqlite3.sqlite_version_info >= (3, 35, 0):
        return

    import pysqlite3

    sys.modules["sqlite3"] = pysqlite3

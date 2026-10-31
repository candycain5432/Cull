# SQLite cache of photo results, so a second run doesn't have to open any photos
import os
import sqlite3
from pathlib import Path

VERSION = 3 # Bump this when a score changes, old results get thrown out on the next run

FIELDS = ("long_edge", "sharpness", "blown", "crushed", "brightness", "taken", "camera", "phash", "error")


# Lives in the home folder by default, a file inside the shoot would get moved by <sort>
def connect(settings, warn):
    if not settings.enabled:
        return open_db(":memory:")

    path = Path(settings.folder).expanduser() / "cache.db"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return open_db(path)
        except sqlite3.OperationalError: # Locked or read only, the file is fine so leave it alone
            raise
        except sqlite3.DatabaseError: # Damaged, but it's only a cache so start again
            path.unlink()
            return open_db(path)
    except (OSError, sqlite3.Error) as e: # Scores still work without it, they just aren't saved
        warn(f"Can't use the cache in {path.parent}, nothing will be saved this run: {e}")
        return open_db(":memory:")


def open_db(path):
    db = sqlite3.connect(path)

    if db.execute("PRAGMA user_version").fetchone()[0] != VERSION:
        db.execute("DROP TABLE IF EXISTS photos")
    db.execute(f"PRAGMA user_version = {VERSION}") # Always written, so a read only cache shows up here

    db.execute(f"""CREATE TABLE IF NOT EXISTS photos (
        path TEXT PRIMARY KEY, size INTEGER, mtime INTEGER, scoring TEXT, {", ".join(FIELDS)})""")
    return db


# Paths are stored as bytes, a file name doesn't have to be valid text
def path_key(path):
    return os.fsencode(path)


# Returns the saved result, or None if the file or the scoring settings have changed since
def lookup(db, path, size, mtime, scoring):
    row = db.execute(f"SELECT {', '.join(FIELDS)} FROM photos WHERE path = ? AND size = ? AND mtime = ? AND scoring = ?",
                     (path_key(path), size, mtime, scoring)).fetchone()
    return dict(zip(FIELDS, row)) if row else None


# Saves after every photo, so stopping a big scan halfway doesn't lose the work
def store(db, path, size, mtime, scoring, result):
    values = [path_key(path), size, mtime, scoring] + [result.get(field) for field in FIELDS]
    db.execute(f"INSERT OR REPLACE INTO photos VALUES ({', '.join('?' * len(values))})", values)
    db.commit()

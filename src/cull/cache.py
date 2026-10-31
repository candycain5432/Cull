# SQLite cache of photo results, so a second run doesn't have to open any photos
import sqlite3
from pathlib import Path

VERSION = 1 # Bump this when a score changes, old results get thrown out on the next run

FIELDS = ("long_edge", "sharpness", "blown", "crushed", "brightness", "taken", "camera", "phash", "error")


# Lives in the home folder, a file inside the shoot would get moved by <sort>
def connect():
    path = Path.home() / ".cache" / "cull" / "cache.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)

    if db.execute("PRAGMA user_version").fetchone()[0] != VERSION:
        db.execute("DROP TABLE IF EXISTS photos")
        db.execute(f"PRAGMA user_version = {VERSION}")

    db.execute(f"""CREATE TABLE IF NOT EXISTS photos (
        path TEXT PRIMARY KEY, size INTEGER, mtime INTEGER, {", ".join(FIELDS)})""")
    return db


# Returns the saved result, or None if the file is new or has changed since
def lookup(db, path, size, mtime):
    row = db.execute(f"SELECT {', '.join(FIELDS)} FROM photos WHERE path = ? AND size = ? AND mtime = ?",
                     (path, size, mtime)).fetchone()
    return dict(zip(FIELDS, row)) if row else None


# Saves after every photo, so stopping a big scan halfway doesn't lose the work
def store(db, path, size, mtime, result):
    values = [path, size, mtime] + [result.get(field) for field in FIELDS]
    db.execute(f"INSERT OR REPLACE INTO photos VALUES ({', '.join('?' * len(values))})", values)
    db.commit()

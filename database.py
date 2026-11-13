"""
Esmiringhoy Hotel - Database (SQLite)
-------------------------------------
Holds the hotel settings and ALL the SQL for the reservation system.
Nothing else in the project talks to sqlite3 directly.

Files created next to this script:
    hotel.db   -> the SQLite database (tables: rooms, bookings)

Run this file by itself to create the database (it also imports the old
bookings.json if you still have one):
    python database.py
"""
import os
import json
import sqlite3

# ----------------------------------------------------------------------------
# Data / settings
# ----------------------------------------------------------------------------
FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(FOLDER, "hotel.db")
OLD_JSON_FILE = os.path.join(FOLDER, "bookings.json")   # only used by import_json()

HOTEL_NAME = "Esmiringhoy Hotel"
VAT_RATE = 0.12
EXTRA_GUEST_FEE = 500          # per extra guest, per night (beyond included guests)
MAX_NIGHTS = 30
MAX_DAYS_AHEAD = 365
PAYMENT_METHODS = ["ONLINE", "CASH", "BANKING"]

ROOMS = {
    "Masters bedroom": {
        "rate": 8500, "included": 4, "max": 6, "total": 3,
        "specs": "65 sqm | 2 King beds | Living area | Jacuzzi | Balcony | Smart TV | Free Wi-Fi",
    },
    "Class A": {
        "rate": 5500, "included": 3, "max": 4, "total": 5,
        "specs": "42 sqm | 1 King + 1 Single bed | Air-con | Smart TV | Mini fridge | Free Wi-Fi",
    },
    "Class B": {
        "rate": 3500, "included": 2, "max": 3, "total": 8,
        "specs": "30 sqm | 1 Queen bed | Air-con | Cable TV | Private bathroom | Free Wi-Fi",
    },
    "Regular": {
        "rate": 2000, "included": 2, "max": 2, "total": 10,
        "specs": "22 sqm | 1 Double bed | Electric fan | Cable TV | Private bathroom",
    },
}
ROOM_NAMES = list(ROOMS.keys())

# Column order of the bookings table (same keys the main program uses)
COLUMNS = ("ref", "room", "checkin", "checkout", "time", "nights", "guests",
           "name", "contact", "payment", "requests", "total", "created")

SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
    room_type   TEXT PRIMARY KEY,
    rate        INTEGER NOT NULL,
    included    INTEGER NOT NULL,
    max_guests  INTEGER NOT NULL,
    total       INTEGER NOT NULL,
    specs       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    ref        TEXT PRIMARY KEY,
    room       TEXT NOT NULL REFERENCES rooms (room_type),
    checkin    TEXT NOT NULL,                       -- YYYY-MM-DD
    checkout   TEXT NOT NULL,                       -- YYYY-MM-DD
    time       TEXT NOT NULL,                       -- e.g. 2:00PM
    nights     INTEGER NOT NULL CHECK (nights BETWEEN 1 AND 30),
    guests     INTEGER NOT NULL CHECK (guests >= 1),
    name       TEXT NOT NULL,
    contact    TEXT NOT NULL,
    payment    TEXT NOT NULL CHECK (payment IN ('ONLINE', 'CASH', 'BANKING')),
    requests   TEXT NOT NULL DEFAULT '',
    total      REAL NOT NULL,
    created    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookings_room_dates ON bookings (room, checkin, checkout);
"""


# ----------------------------------------------------------------------------
# Storage helpers
# ----------------------------------------------------------------------------
def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, params=()):
    """Run a SELECT and return the rows as a list of dictionaries."""
    conn = connect()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def execute(sql, params=()):
    """Run an INSERT / UPDATE / DELETE. Returns how many rows changed."""
    conn = connect()
    try:
        with conn:      # commits when it works, rolls back when it fails
            return conn.execute(sql, params).rowcount
    finally:
        conn.close()


def init_db():
    """Create the tables (if missing) and copy the ROOMS settings into 'rooms'."""
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        with conn:
            for name, r in ROOMS.items():
                conn.execute(
                    """INSERT INTO rooms (room_type, rate, included, max_guests, total, specs)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT (room_type) DO UPDATE SET
                           rate = excluded.rate, included = excluded.included,
                           max_guests = excluded.max_guests, total = excluded.total,
                           specs = excluded.specs""",
                    (name, r["rate"], r["included"], r["max"], r["total"], r["specs"]))
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# Bookings: add / find / cancel / list
# ----------------------------------------------------------------------------
def add_booking(rec):
    marks = ", ".join("?" * len(COLUMNS))
    execute(f"INSERT INTO bookings ({', '.join(COLUMNS)}) VALUES ({marks})",
            [rec[c] for c in COLUMNS])


def get_booking(ref):
    rows = query("SELECT * FROM bookings WHERE ref = ?", (ref,))
    return rows[0] if rows else None


def delete_booking(ref):
    """Cancel a reservation. Returns True if something was deleted."""
    return execute("DELETE FROM bookings WHERE ref = ?", (ref,)) > 0


def all_bookings():
    return query("SELECT * FROM bookings ORDER BY checkin, ref")


def ref_exists(ref):
    return get_booking(ref) is not None


def count_booked(room, start, end, ignore_ref=None):
    """How many reservations of this room type overlap the nights [start, end)."""
    rows = query(
        """SELECT COUNT(*) AS used FROM bookings
           WHERE room = ? AND checkin < ? AND checkout > ? AND ref != ?""",
        (room, end.isoformat(), start.isoformat(), ignore_ref or ""))
    return rows[0]["used"]


# ----------------------------------------------------------------------------
# Move the old bookings.json into the database (runs once)
# ----------------------------------------------------------------------------
def import_json():
    """Copy reservations from bookings.json into SQLite. Returns how many were added."""
    if not os.path.exists(OLD_JSON_FILE):
        return 0
    try:
        with open(OLD_JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(data, list):
        return 0

    added = 0
    for rec in data:
        try:
            if not ref_exists(rec["ref"]):
                add_booking(rec)
                added += 1
        except (KeyError, TypeError, sqlite3.Error):
            continue    # skip a bad row and keep going

    try:    # rename it so a cancelled booking is never imported again
        os.replace(OLD_JSON_FILE, OLD_JSON_FILE + ".imported")
    except OSError:
        pass
    return added


# ----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print(f"Database ready: {DB_FILE}")
    n = import_json()
    if n:
        print(f"Imported {n} reservation(s) from bookings.json")

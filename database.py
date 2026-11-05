"""database.py - SQLite connection, table creation, and all SQL operations
for the Room Booking Management System.

Every query that includes a user-supplied value is parameterized (``?`` or
``:name`` placeholders). User input is never concatenated into SQL text.

Tables
------
rooms         one row per room
guests        one row per guest
reservations  one row per booking; links a room and a guest (foreign keys)
"""

import os
import sqlite3
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "room_booking.db")

# Allowed values (also enforced by CHECK constraints in the schema below).
ROOM_TYPES = ("Single", "Double", "Family", "Suite")
PAYMENT_STATUSES = ("Unpaid", "Partial", "Paid")
BOOKING_STATUSES = ("Booked", "Checked-in", "Checked-out", "Cancelled")

SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
    room_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number    TEXT    NOT NULL UNIQUE,
    room_type      TEXT    NOT NULL
                   CHECK (room_type IN ('Single', 'Double', 'Family', 'Suite')),
    capacity       INTEGER NOT NULL CHECK (capacity > 0),
    rate_per_night REAL    NOT NULL CHECK (rate_per_night > 0),
    is_simulated   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS guests (
    guest_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT    NOT NULL,
    contact_number TEXT    NOT NULL DEFAULT '',
    is_simulated   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id        INTEGER NOT NULL,
    guest_id       INTEGER NOT NULL,
    check_in       TEXT    NOT NULL,   -- ISO date: YYYY-MM-DD
    check_out      TEXT    NOT NULL,   -- ISO date: YYYY-MM-DD
    total_cost     REAL    NOT NULL CHECK (total_cost >= 0),
    amount_paid    REAL    NOT NULL DEFAULT 0 CHECK (amount_paid >= 0),
    payment_status TEXT    NOT NULL DEFAULT 'Unpaid'
                   CHECK (payment_status IN ('Unpaid', 'Partial', 'Paid')),
    booking_status TEXT    NOT NULL DEFAULT 'Booked'
                   CHECK (booking_status IN
                          ('Booked', 'Checked-in', 'Checked-out', 'Cancelled')),
    is_simulated   INTEGER NOT NULL DEFAULT 0,
    CHECK (check_out > check_in),
    FOREIGN KEY (room_id)  REFERENCES rooms (room_id),
    FOREIGN KEY (guest_id) REFERENCES guests (guest_id)
);
"""

# Base query used wherever reservations are shown (joins all three tables).
RESERVATION_SELECT = """
    SELECT res.reservation_id, res.room_id, res.guest_id,
           r.room_number, r.room_type, g.full_name,
           res.check_in, res.check_out, res.total_cost, res.amount_paid,
           res.payment_status, res.booking_status, res.is_simulated
    FROM reservations AS res
    JOIN rooms  AS r ON r.room_id  = res.room_id
    JOIN guests AS g ON g.guest_id = res.guest_id
"""


# ---------------------------------------------------------------------------
# Connection and generic helpers
# ---------------------------------------------------------------------------

def get_connection():
    """Open a connection to the SQLite file and return it.

    Foreign key enforcement is switched on for every connection because
    SQLite leaves it off by default. Rows can be read like dictionaries.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    """Create all tables if they do not exist yet (safe to call every run)."""
    conn = get_connection()
    try:
        with conn:
            conn.executescript(SCHEMA)
    finally:
        conn.close()


def fetch_all(sql, params=()):
    """Run a SELECT and return every row as a list."""
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def fetch_one(sql, params=()):
    """Run a SELECT and return the first row, or None if nothing matched."""
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def execute_write(sql, params=()):
    """Run an INSERT, UPDATE, or DELETE and commit it.

    Returns:
        (lastrowid, rowcount) - lastrowid is the new id after an INSERT;
        rowcount is how many rows an UPDATE or DELETE changed (0 means the
        record was not found).

    Raises:
        sqlite3.IntegrityError: for duplicates, bad foreign keys, or CHECK
        failures. Callers decide how to explain it to the user.
    """
    conn = get_connection()
    try:
        with conn:  # commits on success, rolls back on error
            cursor = conn.execute(sql, params)
            return cursor.lastrowid, cursor.rowcount
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

def add_room(room_number, room_type, capacity, rate_per_night, is_simulated=0):
    """Insert a room and return its new room_id."""
    sql = ("INSERT INTO rooms (room_number, room_type, capacity, rate_per_night, "
           "is_simulated) VALUES (?, ?, ?, ?, ?)")
    return execute_write(sql, (room_number, room_type, capacity,
                               rate_per_night, is_simulated))[0]


def get_all_rooms():
    """Return all rooms ordered by room number."""
    return fetch_all("SELECT * FROM rooms ORDER BY room_number")


def get_room_by_id(room_id):
    """Return one room row by id, or None."""
    return fetch_one("SELECT * FROM rooms WHERE room_id = ?", (room_id,))


def get_room_by_number(room_number):
    """Return one room row by its room number, or None."""
    return fetch_one("SELECT * FROM rooms WHERE room_number = ?", (room_number,))


def search_rooms(keyword):
    """Return rooms whose number or type contains the keyword."""
    pattern = f"%{keyword}%"  # the wildcard goes in the parameter, not the SQL
    sql = ("SELECT * FROM rooms WHERE room_number LIKE ? OR room_type LIKE ? "
           "ORDER BY room_number")
    return fetch_all(sql, (pattern, pattern))


def update_room(room_id, room_type, capacity, rate_per_night):
    """Update a room. Returns the number of rows changed (0 = not found)."""
    sql = ("UPDATE rooms SET room_type = ?, capacity = ?, rate_per_night = ? "
           "WHERE room_id = ?")
    return execute_write(sql, (room_type, capacity, rate_per_night, room_id))[1]


def delete_room(room_id):
    """Delete a room. Raises IntegrityError if it still has reservations."""
    return execute_write("DELETE FROM rooms WHERE room_id = ?", (room_id,))[1]


# ---------------------------------------------------------------------------
# Guests
# ---------------------------------------------------------------------------

def add_guest(full_name, contact_number="", is_simulated=0):
    """Insert a guest and return the new guest_id."""
    sql = ("INSERT INTO guests (full_name, contact_number, is_simulated) "
           "VALUES (?, ?, ?)")
    return execute_write(sql, (full_name, contact_number, is_simulated))[0]


def get_all_guests():
    """Return all guests ordered by name."""
    return fetch_all("SELECT * FROM guests ORDER BY full_name")


def get_guest_by_id(guest_id):
    """Return one guest row by id, or None."""
    return fetch_one("SELECT * FROM guests WHERE guest_id = ?", (guest_id,))


def search_guests(keyword):
    """Return guests whose name or contact number contains the keyword."""
    pattern = f"%{keyword}%"
    sql = ("SELECT * FROM guests WHERE full_name LIKE ? OR contact_number LIKE ? "
           "ORDER BY full_name")
    return fetch_all(sql, (pattern, pattern))


def update_guest(guest_id, full_name, contact_number):
    """Update a guest. Returns rows changed (0 = not found)."""
    sql = "UPDATE guests SET full_name = ?, contact_number = ? WHERE guest_id = ?"
    return execute_write(sql, (full_name, contact_number, guest_id))[1]


def delete_guest(guest_id):
    """Delete a guest. Raises IntegrityError if they still have reservations."""
    return execute_write("DELETE FROM guests WHERE guest_id = ?", (guest_id,))[1]


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------

def add_reservation(room_id, guest_id, check_in, check_out, total_cost,
                    amount_paid, payment_status, booking_status="Booked",
                    is_simulated=0):
    """Insert a reservation and return its new reservation_id."""
    sql = ("INSERT INTO reservations (room_id, guest_id, check_in, check_out, "
           "total_cost, amount_paid, payment_status, booking_status, is_simulated) "
           "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    params = (room_id, guest_id, check_in, check_out, total_cost, amount_paid,
              payment_status, booking_status, is_simulated)
    return execute_write(sql, params)[0]


def get_all_reservations():
    """Return every reservation (joined with room and guest), oldest first."""
    return fetch_all(RESERVATION_SELECT + " ORDER BY res.check_in, r.room_number")


def get_reservation_by_id(reservation_id):
    """Return one joined reservation row by id, or None."""
    sql = RESERVATION_SELECT + " WHERE res.reservation_id = ?"
    return fetch_one(sql, (reservation_id,))


def get_room_stays(room_id, exclude_reservation_id=None):
    """Return check-in/check-out dates of a room's non-cancelled reservations.

    Used for the double-booking check. Pass exclude_reservation_id when
    editing a reservation so it does not conflict with itself.
    """
    sql = ("SELECT check_in, check_out FROM reservations "
           "WHERE room_id = ? AND booking_status != 'Cancelled' "
           "AND reservation_id != ?")
    # Ids start at 1, so 0 safely means "exclude nothing".
    return fetch_all(sql, (room_id, exclude_reservation_id or 0))


def search_reservations(field, value):
    """Search reservations by one field.

    field is one of: 'guest' (name contains), 'room' (exact room number),
    'date' (a night the guest is staying), 'payment' (payment status),
    'booking' (booking status).

    The SQL conditions below are fixed text chosen by the program; the
    user's value is always passed as a parameter.
    """
    if field == "guest":
        condition, params = "g.full_name LIKE ?", (f"%{value}%",)
    elif field == "room":
        condition, params = "r.room_number = ?", (value,)
    elif field == "date":
        condition, params = "res.check_in <= ? AND res.check_out > ?", (value, value)
    elif field == "payment":
        condition, params = "res.payment_status = ?", (value,)
    elif field == "booking":
        condition, params = "res.booking_status = ?", (value,)
    else:
        raise ValueError(f"Unknown search field: {field}")
    sql = (RESERVATION_SELECT + " WHERE " + condition +
           " ORDER BY res.check_in, r.room_number")
    return fetch_all(sql, params)


def update_reservation_dates(reservation_id, check_in, check_out, total_cost,
                             payment_status):
    """Change a stay's dates (and the recalculated cost/payment status)."""
    sql = ("UPDATE reservations SET check_in = ?, check_out = ?, total_cost = ?, "
           "payment_status = ? WHERE reservation_id = ?")
    params = (check_in, check_out, total_cost, payment_status, reservation_id)
    return execute_write(sql, params)[1]


def update_payment(reservation_id, amount_paid, payment_status):
    """Record the new total paid and the matching payment status."""
    sql = ("UPDATE reservations SET amount_paid = ?, payment_status = ? "
           "WHERE reservation_id = ?")
    return execute_write(sql, (amount_paid, payment_status, reservation_id))[1]


def update_booking_status(reservation_id, booking_status):
    """Change a reservation's booking status (check-in, check-out, cancel)."""
    sql = "UPDATE reservations SET booking_status = ? WHERE reservation_id = ?"
    return execute_write(sql, (booking_status, reservation_id))[1]


def delete_reservation(reservation_id):
    """Delete a reservation. Returns rows deleted (0 = not found)."""
    sql = "DELETE FROM reservations WHERE reservation_id = ?"
    return execute_write(sql, (reservation_id,))[1]


# ---------------------------------------------------------------------------
# Simulated sample data (clearly flagged with is_simulated = 1)
# ---------------------------------------------------------------------------

# (room number, type, capacity, rate per night in PHP)
SAMPLE_ROOMS = [
    ("101", "Single", 1, 1200.0), ("102", "Single", 1, 1200.0),
    ("201", "Double", 2, 1800.0), ("202", "Double", 2, 1800.0),
    ("203", "Double", 2, 1800.0), ("301", "Family", 4, 2800.0),
    ("302", "Family", 4, 2800.0), ("401", "Suite", 2, 4500.0),
]

# Fictional guests. The phone numbers are obviously fake placeholders.
SAMPLE_GUESTS = [
    ("Maria Santos", "0917-000-0001"), ("Juan Dela Cruz", "0917-000-0002"),
    ("Ana Reyes", "0917-000-0003"), ("Pedro Garcia", "0917-000-0004"),
    ("Liza Mendoza", "0917-000-0005"), ("Carlo Ramos", "0917-000-0006"),
    ("Grace Bautista", "0917-000-0007"), ("Miguel Torres", "0917-000-0008"),
    ("Ella Navarro", "0917-000-0009"), ("Rico Villanueva", "0917-000-0010"),
]

# (room, guest number 1-10, check-in, check-out, share of cost paid, status)
SAMPLE_RESERVATIONS = [
    ("101", 1, "2026-07-03", "2026-07-05", 1.0, "Checked-out"),
    ("101", 6, "2026-07-20", "2026-07-23", 1.0, "Checked-out"),
    ("101", 3, "2026-09-10", "2026-09-12", 1.0, "Checked-out"),
    ("101", 2, "2026-11-03", "2026-11-07", 0.5, "Checked-in"),
    ("101", 4, "2026-12-20", "2026-12-23", 0.0, "Booked"),
    ("102", 5, "2026-08-01", "2026-08-04", 1.0, "Checked-out"),
    ("102", 7, "2026-09-25", "2026-09-27", 0.5, "Checked-out"),
    ("102", 10, "2026-11-10", "2026-11-12", 0.0, "Booked"),
    ("201", 8, "2026-07-10", "2026-07-14", 1.0, "Checked-out"),
    ("201", 9, "2026-08-15", "2026-08-18", 1.0, "Checked-out"),
    ("201", 1, "2026-10-05", "2026-10-08", 1.0, "Checked-out"),
    ("201", 3, "2026-11-01", "2026-11-06", 1.0, "Checked-in"),
    ("202", 4, "2026-08-22", "2026-08-25", 1.0, "Checked-out"),
    ("202", 6, "2026-10-12", "2026-10-15", 0.5, "Checked-out"),
    ("202", 5, "2026-12-01", "2026-12-05", 0.0, "Booked"),
    ("203", 2, "2026-09-01", "2026-09-04", 1.0, "Checked-out"),
    ("203", 7, "2026-10-20", "2026-10-22", 0.0, "Cancelled"),
    ("203", 9, "2026-11-15", "2026-11-18", 0.5, "Booked"),
    ("301", 10, "2026-07-25", "2026-07-28", 1.0, "Checked-out"),
    ("301", 8, "2026-09-18", "2026-09-21", 1.0, "Checked-out"),
    ("301", 1, "2026-12-24", "2026-12-28", 0.5, "Booked"),
    ("302", 3, "2026-08-08", "2026-08-12", 1.0, "Checked-out"),
    ("302", 4, "2026-10-28", "2026-10-31", 1.0, "Checked-out"),
    ("302", 5, "2026-11-20", "2026-11-23", 0.0, "Booked"),
    ("401", 7, "2026-07-15", "2026-07-17", 1.0, "Checked-out"),
    ("401", 6, "2026-09-05", "2026-09-08", 1.0, "Checked-out"),
    ("401", 2, "2026-10-30", "2026-11-02", 0.5, "Checked-out"),
    ("401", 1, "2026-12-30", "2027-01-02", 0.5, "Booked"),
]

_STATUS_BY_SHARE = {0.0: "Unpaid", 0.5: "Partial", 1.0: "Paid"}


def load_sample_data():
    """Insert simulated rooms, guests, and reservations for testing/demo.

    Every inserted record has is_simulated = 1 so it can be recognised as
    invented data. Returns the number of reservations added (0 if the sample
    data was already loaded).
    """
    already = fetch_one("SELECT COUNT(*) AS n FROM reservations WHERE is_simulated = 1")
    if already["n"] > 0:
        return 0

    rooms = {}  # room number -> (room_id, rate)
    for number, room_type, capacity, rate in SAMPLE_ROOMS:
        existing = get_room_by_number(number)
        if existing:
            rooms[number] = (existing["room_id"], existing["rate_per_night"])
        else:
            rooms[number] = (add_room(number, room_type, capacity, rate, 1), rate)

    guest_ids = [add_guest(name, contact, 1) for name, contact in SAMPLE_GUESTS]

    added = 0
    for number, guest_no, check_in, check_out, share, status in SAMPLE_RESERVATIONS:
        room_id, rate = rooms[number]
        nights = (date.fromisoformat(check_out) - date.fromisoformat(check_in)).days
        total = round(nights * rate, 2)
        paid = round(total * share, 2)
        add_reservation(room_id, guest_ids[guest_no - 1], check_in, check_out,
                        total, paid, _STATUS_BY_SHARE[share], status, 1)
        added += 1
    return added

# Room Booking Management System

**DSA 214 - Programming for Data Science | Final Laboratory Activity**
Isabela State University, College of Computing Studies, ICT
Assigned scenario: **12. Room Booking Management**

A command-line application that manages rooms, guests, and reservations
(check-in/check-out dates and payment statuses) in a SQLite database, and
produces summaries and charts from the stored records.

## Group

| Member | Primary responsibility |
| --- | --- |
| Member 1: _name_ | Database design, table relationships, SQL/CRUD (`database.py`) |
| Member 2: _name_ | Functions, validation, control structures, menus (`functions.py`, `main.py`) |
| Member 3: _name_ | Data analysis and charts (`analytics.py`) |
| Member 4: _name_ | Testing, GitHub, README, documentation (`tests/`, `README.md`) |

## Requirements

- Python 3.8 or newer
- `sqlite3` (included with Python)
- `matplotlib` (only needed for charts)

## Setup and run

```bash
git clone <your-repository-url>
cd room-booking-system
pip install -r requirements.txt
python main.py
```

The database file (`database/room_booking.db`) is created automatically on the
first run, and records are kept between runs.

To try the program with example data, choose **5. Load simulated sample data**
from the main menu. Sample records are invented for testing and demos. They are
marked with `*` in lists and noted on charts and the report, and must never be
presented as real observations.

## Features

| Menu | What you can do |
| --- | --- |
| Rooms | Add, view, search, update, delete rooms |
| Guests | Add, view, search, update, delete guests |
| Reservations | Create a booking (double-booking is blocked), view, search by guest / room / date / payment / status, check availability, change dates, record payments, check in / check out / cancel, delete |
| Analytics and charts | Summary report (5 measures), occupancy for any period, 3 charts saved to `charts/` |

Deleting a room, guest, or reservation always asks for confirmation. A room or
guest that still has reservations cannot be deleted.

## Analytical measures

1. Occupancy rate per room and overall, for a chosen period
2. Revenue per month: billed, collected, and outstanding
3. Average length of stay
4. Most-booked rooms
5. Outstanding balances per guest

## Charts

| File | Shows |
| --- | --- |
| `charts/monthly_revenue.png` | Collected vs outstanding money for each month |
| `charts/bookings_by_room_type.png` | Number of reservations per room type |
| `charts/payment_status.png` | Share of reservations that are Paid, Partial, or Unpaid |

## Database design

```
rooms (room_id PK, room_number UNIQUE, room_type, capacity, rate_per_night, is_simulated)
guests (guest_id PK, full_name, contact_number, is_simulated)
reservations (reservation_id PK, room_id FK -> rooms, guest_id FK -> guests,
              check_in, check_out, total_cost, amount_paid,
              payment_status, booking_status, is_simulated)
```

One room has many reservations and one guest has many reservations. Foreign
keys are enforced, and CHECK constraints keep statuses and amounts valid.
All SQL that uses user input is parameterized.

## Project structure

```
main.py          menu and program flow
database.py      connection, tables, all SQL operations, sample data
functions.py     validation, date/cost calculations, availability checks, tables
analytics.py     measures, summary report, charts
tests/           test_cases.md (manual test sheet), test_core.py (automated checks)
charts/          generated chart images
database/        SQLite database file (created on first run)
documentation/   final PDF
```

## Rules and assumptions

- A stay occupies the nights from check-in up to (not including) check-out, so a
  guest may arrive on the day another guest leaves.
- Dates use the format `YYYY-MM-DD`. Check-out must be after check-in.
- Total cost = nights x the room's rate at the time of booking. Changing a
  room's rate later does not change existing reservations.
- Payment status is calculated: Unpaid (nothing paid), Partial, or Paid.
- Booking status changes follow: Booked -> Checked-in or Cancelled;
  Checked-in -> Checked-out. Checked-out and Cancelled are final.
- Cancelled reservations are left out of availability checks and analytics.
- Monthly revenue is grouped by the month of the check-in date.
- Currency is Philippine pesos (PHP). Guest contact numbers are optional.

## Testing

Automated checks (they use a temporary database, not your real data):

```bash
python -m unittest discover -s tests -v
```

Manual test cases and results are recorded in `tests/test_cases.md`.

## References and AI disclosure

- Python `sqlite3` documentation: https://docs.python.org/3/library/sqlite3.html
- Matplotlib documentation: https://matplotlib.org/stable/

AI assistance: _describe how AI was used, according to your instructor's
directions and university policy._

# Esmiringhoy Hotel – Room Reservation Management System

A desktop room reservation system for **Esmiringhoy Hotel**, built with **Python**, **Tkinter** (GUI) and **SQLite** (database).
Guests can check room availability, make a reservation, get a printable receipt, look up or cancel a booking by reference number, and the hotel can view an analytics report of all saved reservations.

> DSA 214 (Programming for Data Science) – Final Laboratory Activity, Scenario 12: **Room Booking Management**

---

## Group Members

| # | Name |
|---|------|
| 1 | Reagan Recto |
| 2 | Elaiza Aquino |
| 3 | John Rainier Varilla |
| 4 | John Ace Donato |

---

## Features

- **Room selection** – 4 room types with live availability for the chosen dates (shows rooms left or `FULL`).
- **Reservation flow** – Room & dates → Guest information & payment → Confirmation → Receipt.
- **Automatic pricing** – room rate, extra-guest fee, length-of-stay discount and 12% VAT computed for you.
- **Input validation** – dates, time, nights, guests, name, contact number, payment method and special requests are all checked with clear error messages.
- **Double-booking protection** – availability is re-checked right before a reservation is saved.
- **Receipts** – every reservation gets a unique reference number (`ESM-XXXXXX`) and a `.txt` receipt saved in the `receipts/` folder (can also be saved elsewhere with *Save Receipt As...*).
- **Find / Cancel booking** – look up a reservation by reference number and cancel it (past stays cannot be cancelled).
- **Analytics report** – totals, revenue by room type, payment methods, occupancy, reservations per month and top guests.

---

## Rooms and Rates

| Room | Rate / night | Guests included | Max guests | Rooms available |
|------|-------------:|:---------------:|:----------:|:---------------:|
| Masters bedroom | PHP 8,500 | 4 | 6 | 3 |
| Class A | PHP 5,500 | 3 | 4 | 5 |
| Class B | PHP 3,500 | 2 | 3 | 8 |
| Regular | PHP 2,000 | 2 | 2 | 10 |

### How the price is computed

1. **Base** = room rate × number of nights
2. **Extra guests** = PHP 500 × guests beyond the included number × nights
3. **Discount** on the subtotal: **5%** for 3–4 nights, **10%** for 5 or more nights
4. **VAT** = 12% of the discounted subtotal
5. **Total** = discounted subtotal + VAT

*Example:* Class B, 4 nights, 3 guests → base 14,000 + extra guest 2,000 = 16,000 → 5% discount (−800) = 15,200 → VAT 1,824 → **Total PHP 17,024.00**

### Booking rules

- Check-in date cannot be in the past and can be at most **365 days** ahead
- Stay is **1 to 30 nights**
- Number of guests cannot go over the room's maximum
- Contact number format: `09XXXXXXXXX` or `+639XXXXXXXXX`
- Payment method: `ONLINE`, `CASH` or `BANKING`
- Special requests: optional, up to 80 characters

---

## Project Structure

```
.
├── mainsirbenn.py   # Main program – the Tkinter windows/screens
├── database.py      # Hotel settings + ALL the SQLite code
├── functions.py     # Input checking, prices, availability, references, receipts
├── analytics.py     # Summary numbers and the analytics report
├── hotel.db         # SQLite database (rooms and bookings tables)
├── hotelbg.jpg      # Optional background image
└── receipts/        # Auto-generated .txt receipts
```

Each file has its own job:

| File | What it does |
|------|--------------|
| `mainsirbenn.py` | Draws the screens (booking, guest info, receipt, analytics) and connects the buttons to the other files. |
| `database.py` | Stores the hotel settings (rooms, VAT, limits) and is the only file that talks to SQLite. |
| `functions.py` | Business logic with no windows and no SQL: validation, pricing, availability, reference numbers and receipt text. |
| `analytics.py` | SQL summaries and the text report shown on the Analytics screen. |

### Database

`hotel.db` has two tables:

- **`rooms`** – `room_type` (primary key), `rate`, `included`, `max_guests`, `total`, `specs`
- **`bookings`** – `ref` (primary key), `room` (foreign key to `rooms`), `checkin`, `checkout`, `time`, `nights`, `guests`, `name`, `contact`, `payment`, `requests`, `total`, `created`

The tables are created automatically the first time the program runs. If an old `bookings.json` file exists, its reservations are imported into the database once.

---

## Requirements

- **Python 3.8 or newer**
- **Tkinter** (included with the standard Python installer; on some Linux systems install it with `sudo apt install python3-tk`)
- **Pillow** *(optional)* – only needed for the background image. Without it, a blue gradient is used.

```bash
pip install pillow
```

---

## How to Run

1. Put all the files in the **same folder**.
2. Open a terminal in that folder and run:

```bash
python mainsirbenn.py
```

Other files can also be run by themselves:

```bash
python database.py    # create the database (and import old bookings.json if present)
python analytics.py   # print the analytics report in the terminal
```

---

## How to Use

1. **Choose a room** – pick the room type, check-in date (`MONTH/DAY/YEAR`, e.g. `12/25/2026`), check-in time (e.g. `2:00PM`), number of nights and number of guests. Press **Check Availability** to see how many rooms are left, then **Next**.
2. **Enter guest details** – full name, contact number, payment method and any special requests, then press **Confirm Reservation**.
3. **Get your receipt** – note the reference number. The receipt is saved automatically in `receipts/`.
4. **Find / Cancel Booking** – enter your reference number (e.g. `ESM-AB12CD`) to view or cancel a reservation.
5. **Analytics** – open the Analytics screen to see the hotel report.

---

## Tech Stack

- Python 3
- Tkinter (GUI)
- SQLite3 (database)
- Pillow (optional, background image)

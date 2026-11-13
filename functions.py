"""
Esmiringhoy Hotel - Functions (business logic)
----------------------------------------------
Input checking, prices, availability, reference numbers and receipts.
No windows and no SQL in here, so the same functions work for the GUI
version and for a command-line version.
"""
import re
import random
import string
from datetime import datetime, date

from database import (HOTEL_NAME, VAT_RATE, EXTRA_GUEST_FEE, PAYMENT_METHODS,
                      ROOMS, count_booked, ref_exists)


# ----------------------------------------------------------------------------
# Input checking (each one raises ValueError with a message the user can read)
# ----------------------------------------------------------------------------
def parse_date(s):
    s = s.strip()
    if not s:
        raise ValueError("Date of reservation is required (MONTH/DAY/YEAR, e.g. 12/25/2026).")
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        raise ValueError("Invalid date. Use MONTH/DAY/YEAR, e.g. 12/25/2026 (must be a real date).")


def parse_time(s):
    s = s.strip().upper().replace(" ", "")
    if not s:
        raise ValueError("Time of reservation is required (e.g. 7:00AM).")
    for fmt in ("%I:%M%p", "%I%p"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    raise ValueError("Invalid time. Use a format like 7:00AM or 2:30PM.")


def parse_int(s, label, lo, hi):
    s = s.strip()
    if not s:
        raise ValueError(f"{label} is required.")
    if not s.isdigit():
        raise ValueError(f"{label} must be a whole number.")
    n = int(s)
    if not lo <= n <= hi:
        raise ValueError(f"{label} must be between {lo} and {hi}.")
    return n


def check_name(s):
    name = " ".join(s.split())
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'\-]+", name):
        raise ValueError("Please enter a valid full name (letters only, at least 2 characters).")
    return name


def check_contact(s):
    cp = re.sub(r"[\s\-]", "", s)
    if not cp:
        raise ValueError("Contact number is required.")
    if not re.fullmatch(r"(09\d{9}|\+639\d{9})", cp):
        raise ValueError("Invalid contact number. Use 09XXXXXXXXX or +639XXXXXXXXX.")
    return cp


def check_payment(s):
    if s not in PAYMENT_METHODS:
        raise ValueError("Please choose a payment method.")
    return s


def check_requests(s):
    req = s.strip()
    if len(req) > 80:
        raise ValueError("Special requests must be 80 characters or fewer.")
    return req


# ----------------------------------------------------------------------------
# Business logic
# ----------------------------------------------------------------------------
def rooms_left(room, start, end, ignore_ref=None):
    """How many rooms of this type are free for [start, end)."""
    return ROOMS[room]["total"] - count_booked(room, start, end, ignore_ref)


def compute_price(room, nights, guests):
    r = ROOMS[room]
    base = r["rate"] * nights
    extra_guests = max(0, guests - r["included"])
    extra = extra_guests * EXTRA_GUEST_FEE * nights
    subtotal = base + extra
    disc_pct = 0.10 if nights >= 5 else 0.05 if nights >= 3 else 0.0
    discount = subtotal * disc_pct
    taxable = subtotal - discount
    vat = taxable * VAT_RATE
    return {
        "rate": r["rate"], "base": base, "extra_guests": extra_guests, "extra": extra,
        "subtotal": subtotal, "disc_pct": disc_pct, "discount": discount,
        "vat": vat, "total": taxable + vat,
    }


def new_reference():
    while True:
        ref = "ESM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not ref_exists(ref):
            return ref


def make_record(booking, name, contact, payment, requests):
    """Turn the screen data + guest details into one reservation record."""
    total = compute_price(booking["room"], booking["nights"], booking["guests"])["total"]
    return {
        "ref": new_reference(), "room": booking["room"],
        "checkin": booking["checkin"], "checkout": booking["checkout"],
        "time": booking["time"], "nights": booking["nights"],
        "guests": booking["guests"], "name": name, "contact": contact,
        "payment": payment, "requests": requests, "total": round(total, 2),
        "created": datetime.now().strftime("%b %d, %Y %I:%M %p"),
    }


def peso(x):
    return f"PHP {x:,.2f}"


def build_receipt(b):
    p = compute_price(b["room"], b["nights"], b["guests"])
    ci = date.fromisoformat(b["checkin"])
    co = date.fromisoformat(b["checkout"])
    w = 50
    line = "=" * w
    dash = "-" * w

    def row(label, value):
        return f"{label:<26}{value:>{w - 26}}"

    out = [
        line,
        HOTEL_NAME.upper().center(w),
        "OFFICIAL RESERVATION RECEIPT".center(w),
        line,
        f"Reference No : {b['ref']}",
        f"Issued       : {b['created']}",
        dash,
        f"Guest        : {b['name']}",
        f"Contact No.  : {b['contact']}",
        f"Payment      : {b['payment']}",
        dash,
        f"Room         : {b['room']}",
        f"Specs        : {ROOMS[b['room']]['specs'][:36]}",
        f"Check-in     : {ci.strftime('%b %d, %Y')} at {b['time']}",
        f"Check-out    : {co.strftime('%b %d, %Y')}",
        f"Length of stay: {b['nights']} night(s)",
        f"No. of guests: {b['guests']}",
    ]
    if b.get("requests"):
        out.append(f"Requests     : {b['requests'][:36]}")
    out.append(dash)
    out.append(row(f"Room rate x {b['nights']} night(s)", peso(p["base"])))
    if p["extra_guests"]:
        out.append(row(f"Extra guest x{p['extra_guests']}", peso(p["extra"])))
    if p["discount"]:
        out.append(row(f"Discount ({int(p['disc_pct'] * 100)}%)", "-" + peso(p["discount"])))
    out.append(row("VAT (12%)", peso(p["vat"])))
    out.append(dash)
    out.append(row("TOTAL AMOUNT DUE", peso(p["total"])))
    out.append(line)
    out.append("Thank you for choosing Esmiringhoy Hotel!".center(w))
    out.append("Please present this receipt upon check-in.".center(w))
    out.append(line)
    return "\n".join(out)

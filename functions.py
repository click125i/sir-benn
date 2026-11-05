"""functions.py - reusable helpers: input validation, date/cost calculations,
availability checking, and table display for the Room Booking system.

Input helpers keep asking until the user gives a valid value, so the program
never crashes on bad input. A blank answer returns ``default`` when one is
given (used by the update menus: press Enter to keep the current value).
"""

import math
from datetime import date, datetime

import database

DATE_FORMAT = "%Y-%m-%d"

# Which booking-status changes are allowed from each current status.
ALLOWED_STATUS_CHANGES = {
    "Booked": ("Checked-in", "Cancelled"),
    "Checked-in": ("Checked-out",),
    "Checked-out": (),
    "Cancelled": (),
}


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def get_valid_choice(prompt, valid_options):
    """Ask until the user types one of valid_options (case-insensitive).

    Args:
        prompt: text shown to the user.
        valid_options: list of acceptable strings, e.g. ["1", "2", "0"].

    Returns:
        The matching option exactly as written in valid_options.
    """
    lookup = {str(option).lower(): str(option) for option in valid_options}
    while True:
        answer = input(prompt).strip().lower()
        if answer in lookup:
            return lookup[answer]
        print("  Invalid choice. Please pick one of: " + ", ".join(lookup.values()))


def get_non_empty_string(prompt, default=None):
    """Ask for required text. Blank returns default if given, else re-asks."""
    while True:
        text = input(prompt).strip()
        if text:
            return text
        if default is not None:
            return default
        print("  This field is required and cannot be blank.")


def get_int(prompt, min_value=None, max_value=None, default=None):
    """Ask for a whole number within optional limits."""
    while True:
        text = input(prompt).strip()
        if text == "" and default is not None:
            return default
        try:
            number = int(text)
        except ValueError:
            print("  Invalid input. Please enter a whole number.")
            continue
        if min_value is not None and number < min_value:
            print(f"  The value must be at least {min_value}.")
        elif max_value is not None and number > max_value:
            print(f"  The value must be at most {max_value}.")
        else:
            return number


def get_float(prompt, min_value=None, max_value=None, default=None):
    """Ask for a decimal number within optional limits."""
    while True:
        text = input(prompt).strip().replace(",", "")
        if text == "" and default is not None:
            return default
        try:
            number = float(text)
        except ValueError:
            print("  Invalid input. Please enter a number (for example 1500.50).")
            continue
        if not math.isfinite(number):
            print("  Invalid input. Please enter a normal number.")
        elif min_value is not None and number < min_value:
            print(f"  The value must be at least {min_value:,.2f}.")
        elif max_value is not None and number > max_value:
            print(f"  The value must be at most {max_value:,.2f}.")
        else:
            return number


def choose_from_list(title, options, default=None):
    """Show a numbered list and return the option the user picks.

    A blank answer returns default when one is given.
    """
    print(title)
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option}")
    suffix = f" [Enter = {default}]" if default is not None else ""
    index = get_int(f"Choose 1-{len(options)}{suffix}: ", 1, len(options),
                    default=0 if default is not None else None)
    return default if index == 0 else options[index - 1]


def confirm_action(prompt):
    """Ask a yes/no question. Returns True only for 'y' or 'yes'."""
    answer = get_valid_choice(prompt + " (y/n): ", ["y", "yes", "n", "no"])
    return answer in ("y", "yes")


def validate_contact(text):
    """Return True if text looks like a phone number (7-15 digits).

    Only digits, spaces, +, -, and parentheses are allowed.
    """
    allowed = set("0123456789+-() ")
    digit_count = sum(1 for char in text if char.isdigit())
    return all(char in allowed for char in text) and 7 <= digit_count <= 15


def get_contact(prompt, default=""):
    """Ask for an optional contact number. Blank returns default."""
    while True:
        text = input(prompt).strip()
        if text == "":
            return default
        if validate_contact(text):
            return text
        print("  Invalid number. Use 7-15 digits (spaces, +, -, ( ) allowed).")


# ---------------------------------------------------------------------------
# Dates, costs, and payment status
# ---------------------------------------------------------------------------

def parse_date(text):
    """Convert 'YYYY-MM-DD' text to a date object, or None if invalid."""
    try:
        return datetime.strptime(text.strip(), DATE_FORMAT).date()
    except ValueError:
        return None


def get_date(prompt, default=None):
    """Ask for a date and return it as an ISO 'YYYY-MM-DD' string."""
    while True:
        text = input(prompt).strip()
        if text == "" and default is not None:
            return default
        parsed = parse_date(text)
        if parsed is not None:
            return parsed.isoformat()
        print("  Invalid date. Use the format YYYY-MM-DD (for example 2026-12-25).")


def get_stay_dates(default_in=None, default_out=None):
    """Ask for check-in and check-out dates until check-out is after check-in.

    Returns:
        (check_in, check_out) as ISO date strings.
    """
    while True:
        check_in = get_date("Check-in date (YYYY-MM-DD): " if default_in is None
                            else f"Check-in date [{default_in}]: ", default_in)
        check_out = get_date("Check-out date (YYYY-MM-DD): " if default_out is None
                             else f"Check-out date [{default_out}]: ", default_out)
        if check_out > check_in:  # ISO dates compare correctly as text
            return check_in, check_out
        print("  Check-out must be after check-in. Please enter both dates again.")


def calculate_nights(check_in, check_out):
    """Return the number of nights between two ISO date strings."""
    return (date.fromisoformat(check_out) - date.fromisoformat(check_in)).days


def calculate_total_cost(nights, rate_per_night):
    """Return the total cost of a stay, rounded to centavos."""
    return round(nights * rate_per_night, 2)


def determine_payment_status(amount_paid, total_cost):
    """Return 'Unpaid', 'Partial', or 'Paid' from the amounts."""
    if amount_paid <= 0:
        return "Unpaid"
    if amount_paid < total_cost:
        return "Partial"
    return "Paid"


def can_change_status(current_status, new_status):
    """Return True if a booking may move from current_status to new_status."""
    return new_status in ALLOWED_STATUS_CHANGES.get(current_status, ())


# ---------------------------------------------------------------------------
# Availability (double-booking prevention)
# ---------------------------------------------------------------------------

def dates_overlap(start_a, end_a, start_b, end_b):
    """Return True if two stays share at least one night.

    A stay occupies the nights from check-in up to (not including) check-out,
    so one guest leaving on the same day another arrives is NOT an overlap.
    ISO date strings compare correctly in alphabetical order.
    """
    return start_a < end_b and end_a > start_b


def is_room_available(room_id, check_in, check_out, exclude_reservation_id=None):
    """Return True if the room has no active reservation overlapping the dates.

    Args:
        exclude_reservation_id: ignore this reservation (used when editing it).
    """
    for stay in database.get_room_stays(room_id, exclude_reservation_id):
        if dates_overlap(check_in, check_out, stay["check_in"], stay["check_out"]):
            return False
    return True


def get_available_rooms(check_in, check_out):
    """Return the list of room rows that are free for the whole stay."""
    available = []
    for room in database.get_all_rooms():
        if is_room_available(room["room_id"], check_in, check_out):
            available.append(room)
    return available


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_money(amount):
    """Format a number as Philippine pesos, e.g. 'PHP 1,200.00'."""
    return f"PHP {amount:,.2f}"


def mark_simulated(record_id, is_simulated):
    """Return the id as text, with '*' added if it is a simulated record."""
    return f"{record_id}*" if is_simulated else str(record_id)


def print_table(headers, rows):
    """Print rows under headers in aligned columns."""
    if not rows:
        print("  (no records found)")
        return
    text_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(str(header)) for header in headers]
    for row in text_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    print("  ".join(str(h).ljust(w) for h, w in zip(headers, widths)))
    print("  ".join("-" * w for w in widths))
    for row in text_rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)))

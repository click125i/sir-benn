"""main.py - menu-driven command-line interface for the Room Booking
Management System.

Run with:  python main.py
"""

import sqlite3

import analytics
import database
import functions as fn


# ---------------------------------------------------------------------------
# Menu engine
# ---------------------------------------------------------------------------

def run_menu(title, options, actions, exit_label="Back"):
    """Show a menu repeatedly and run the chosen action until option 0.

    Args:
        title: heading text.
        options: list of (key, label) pairs shown to the user.
        actions: dict mapping each key to a function to call.
        exit_label: label for option 0 ("Back" or "Exit").
    """
    keys = [key for key, _ in options] + ["0"]
    while True:
        print(f"\n=== {title} ===")
        for key, label in options:
            print(f"  {key}. {label}")
        print(f"  0. {exit_label}")
        choice = fn.get_valid_choice("Choose an option: ", keys)
        if choice == "0":
            return
        try:
            actions[choice]()
        except sqlite3.Error as error:
            print(f"  Database error: {error}")


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

def show_rooms(rooms):
    """Print a list of room rows as a table."""
    rows = [[fn.mark_simulated(r["room_id"], r["is_simulated"]), r["room_number"],
             r["room_type"], r["capacity"], fn.format_money(r["rate_per_night"])]
            for r in rooms]
    fn.print_table(["ID", "Room", "Type", "Capacity", "Rate/night"], rows)
    if any(r["is_simulated"] for r in rooms):
        print("  * = simulated sample record")


def add_room():
    """Add a new room after validating every field."""
    print("\n-- Add Room --")
    room_number = fn.get_non_empty_string("Room number (e.g. 101): ").upper()
    if database.get_room_by_number(room_number):
        print(f"  Room {room_number} already exists. Room numbers must be unique.")
        return
    room_type = fn.choose_from_list("Room type:", database.ROOM_TYPES)
    capacity = fn.get_int("Capacity (number of guests): ", 1, 20)
    rate = fn.get_float("Rate per night (PHP): ", 1)
    try:
        room_id = database.add_room(room_number, room_type, capacity, rate)
        print(f"  Room {room_number} added (ID {room_id}).")
    except sqlite3.IntegrityError:
        print(f"  Could not add room: {room_number} already exists.")


def view_rooms():
    """Show all rooms."""
    print("\n-- All Rooms --")
    show_rooms(database.get_all_rooms())


def search_rooms():
    """Search rooms by number or type."""
    keyword = fn.get_non_empty_string("Search rooms (number or type): ")
    show_rooms(database.search_rooms(keyword))


def update_room():
    """Update a room's type, capacity, or rate (Enter keeps the current value)."""
    room_number = fn.get_non_empty_string("Room number to update: ").upper()
    room = database.get_room_by_number(room_number)
    if room is None:
        print(f"  Room {room_number} was not found.")
        return
    print("Press Enter to keep the current value.")
    room_type = fn.choose_from_list("Room type:", database.ROOM_TYPES,
                                    default=room["room_type"])
    capacity = fn.get_int(f"Capacity [{room['capacity']}]: ", 1, 20,
                          default=room["capacity"])
    rate = fn.get_float(f"Rate per night [{room['rate_per_night']:,.2f}]: ", 1,
                        default=room["rate_per_night"])
    database.update_room(room["room_id"], room_type, capacity, rate)
    print(f"  Room {room_number} updated. Existing reservations keep their "
          f"original total cost.")


def delete_room():
    """Delete a room after confirmation."""
    room_number = fn.get_non_empty_string("Room number to delete: ").upper()
    room = database.get_room_by_number(room_number)
    if room is None:
        print(f"  Room {room_number} was not found.")
        return
    if not fn.confirm_action(f"Delete room {room_number} permanently?"):
        print("  Deletion cancelled.")
        return
    try:
        database.delete_room(room["room_id"])
        print(f"  Room {room_number} deleted.")
    except sqlite3.IntegrityError:
        print(f"  Cannot delete room {room_number}: it still has reservations. "
              f"Delete those reservations first.")


# ---------------------------------------------------------------------------
# Guests
# ---------------------------------------------------------------------------

def show_guests(guests):
    """Print a list of guest rows as a table."""
    rows = [[fn.mark_simulated(g["guest_id"], g["is_simulated"]), g["full_name"],
             g["contact_number"] or "-"] for g in guests]
    fn.print_table(["ID", "Name", "Contact"], rows)
    if any(g["is_simulated"] for g in guests):
        print("  * = simulated sample record")


def add_guest():
    """Add a guest. Returns the new guest_id (used when booking), or None."""
    print("\n-- Add Guest --")
    name = fn.get_non_empty_string("Full name: ")
    contact = fn.get_contact("Contact number (optional): ")
    try:
        guest_id = database.add_guest(name, contact)
    except sqlite3.IntegrityError as error:
        print(f"  Could not add guest: {error}")
        return None
    print(f"  Guest added (ID {guest_id}).")
    return guest_id


def view_guests():
    """Show all guests."""
    print("\n-- All Guests --")
    show_guests(database.get_all_guests())


def search_guests():
    """Search guests by name or contact number."""
    keyword = fn.get_non_empty_string("Search guests (name or contact): ")
    show_guests(database.search_guests(keyword))


def update_guest():
    """Update a guest (Enter keeps the current value)."""
    guest_id = fn.get_int("Guest ID to update: ", 1)
    guest = database.get_guest_by_id(guest_id)
    if guest is None:
        print(f"  No guest with ID {guest_id}.")
        return
    print("Press Enter to keep the current value.")
    name = fn.get_non_empty_string(f"Full name [{guest['full_name']}]: ",
                                   default=guest["full_name"])
    contact = fn.get_contact(f"Contact number [{guest['contact_number'] or '-'}]: ",
                             default=guest["contact_number"])
    database.update_guest(guest_id, name, contact)
    print("  Guest updated.")


def delete_guest():
    """Delete a guest after confirmation."""
    guest_id = fn.get_int("Guest ID to delete: ", 1)
    guest = database.get_guest_by_id(guest_id)
    if guest is None:
        print(f"  No guest with ID {guest_id}.")
        return
    if not fn.confirm_action(f"Delete guest '{guest['full_name']}' permanently?"):
        print("  Deletion cancelled.")
        return
    try:
        database.delete_guest(guest_id)
        print("  Guest deleted.")
    except sqlite3.IntegrityError:
        print("  Cannot delete this guest: they still have reservations. "
              "Delete those reservations first.")


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------

def show_reservations(reservations):
    """Print a list of joined reservation rows as a table."""
    rows = []
    for r in reservations:
        nights = fn.calculate_nights(r["check_in"], r["check_out"])
        rows.append([
            fn.mark_simulated(r["reservation_id"], r["is_simulated"]),
            r["room_number"], r["full_name"], r["check_in"], r["check_out"],
            nights, fn.format_money(r["total_cost"]),
            fn.format_money(r["amount_paid"]), r["payment_status"],
            r["booking_status"],
        ])
    fn.print_table(["ID", "Room", "Guest", "Check-in", "Check-out", "Nights",
                    "Total", "Paid", "Payment", "Status"], rows)
    if any(r["is_simulated"] for r in reservations):
        print("  * = simulated sample record")


def show_available_rooms(check_in, check_out, rooms):
    """Print the free rooms with the estimated total for the stay."""
    nights = fn.calculate_nights(check_in, check_out)
    rows = [[r["room_number"], r["room_type"], r["capacity"],
             fn.format_money(r["rate_per_night"]),
             fn.format_money(fn.calculate_total_cost(nights, r["rate_per_night"]))]
            for r in rooms]
    fn.print_table(["Room", "Type", "Capacity", "Rate/night",
                    f"Total ({nights} nights)"], rows)


def make_reservation():
    """Create a reservation: pick guest, dates, an available room, payment."""
    print("\n-- New Reservation --")
    guest_id = fn.get_int("Guest ID (enter 0 to register a new guest): ", 0)
    if guest_id == 0:
        guest_id = add_guest()
        if guest_id is None:
            return
    guest = database.get_guest_by_id(guest_id)
    if guest is None:
        print(f"  No guest with ID {guest_id}. Add the guest first.")
        return
    print(f"  Guest: {guest['full_name']}")

    check_in, check_out = fn.get_stay_dates()
    available = fn.get_available_rooms(check_in, check_out)
    if not available:
        print("  Sorry, no rooms are available for those dates.")
        return
    print("\nAvailable rooms:")
    show_available_rooms(check_in, check_out, available)

    numbers = [room["room_number"] for room in available]
    choice = fn.get_valid_choice("Room number to book (0 to cancel): ",
                                 numbers + ["0"])
    if choice == "0":
        print("  Reservation cancelled.")
        return
    room = next(r for r in available if r["room_number"] == choice)

    nights = fn.calculate_nights(check_in, check_out)
    total = fn.calculate_total_cost(nights, room["rate_per_night"])
    print(f"  {nights} night(s) x {fn.format_money(room['rate_per_night'])} "
          f"= {fn.format_money(total)}")
    paid = fn.get_float("Payment received now (PHP, 0 if none): ", 0, total)
    payment_status = fn.determine_payment_status(paid, total)

    reservation_id = database.add_reservation(
        room["room_id"], guest_id, check_in, check_out, total, paid,
        payment_status, "Booked")
    print(f"  Reservation #{reservation_id} saved: room {room['room_number']}, "
          f"{check_in} to {check_out}, payment: {payment_status}.")


def view_reservations():
    """Show all reservations."""
    print("\n-- All Reservations --")
    show_reservations(database.get_all_reservations())


def search_reservations():
    """Search reservations by guest, room, date, payment, or booking status."""
    print("\n-- Search Reservations --")
    field = fn.get_valid_choice(
        "Search by: 1) guest name  2) room number  3) date  "
        "4) payment status  5) booking status: ", ["1", "2", "3", "4", "5"])
    if field == "1":
        results = database.search_reservations(
            "guest", fn.get_non_empty_string("Guest name contains: "))
    elif field == "2":
        results = database.search_reservations(
            "room", fn.get_non_empty_string("Room number: ").upper())
    elif field == "3":
        results = database.search_reservations(
            "date", fn.get_date("Date (YYYY-MM-DD) - who is staying that night: "))
    elif field == "4":
        results = database.search_reservations(
            "payment", fn.choose_from_list("Payment status:", database.PAYMENT_STATUSES))
    else:
        results = database.search_reservations(
            "booking", fn.choose_from_list("Booking status:", database.BOOKING_STATUSES))
    show_reservations(results)


def _find_reservation():
    """Ask for a reservation ID and return the row, or None (with a message)."""
    reservation_id = fn.get_int("Reservation ID: ", 1)
    reservation = database.get_reservation_by_id(reservation_id)
    if reservation is None:
        print(f"  Reservation #{reservation_id} was not found.")
    return reservation


def update_reservation_dates():
    """Change the dates of a reservation, re-checking availability and cost."""
    reservation = _find_reservation()
    if reservation is None:
        return
    if reservation["booking_status"] in ("Checked-out", "Cancelled"):
        print(f"  Dates cannot be changed for a {reservation['booking_status']} "
              f"reservation.")
        return
    print(f"  Current stay: {reservation['check_in']} to {reservation['check_out']} "
          f"(room {reservation['room_number']}). Press Enter to keep a date.")
    check_in, check_out = fn.get_stay_dates(reservation["check_in"],
                                            reservation["check_out"])
    if not fn.is_room_available(reservation["room_id"], check_in, check_out,
                                exclude_reservation_id=reservation["reservation_id"]):
        print(f"  Room {reservation['room_number']} is already booked for part "
              f"of those dates. Nothing was changed.")
        return
    room = database.get_room_by_id(reservation["room_id"])
    nights = fn.calculate_nights(check_in, check_out)
    total = fn.calculate_total_cost(nights, room["rate_per_night"])
    status = fn.determine_payment_status(reservation["amount_paid"], total)
    database.update_reservation_dates(reservation["reservation_id"], check_in,
                                      check_out, total, status)
    print(f"  Dates updated. New total: {fn.format_money(total)} "
          f"(payment status: {status}).")
    if reservation["amount_paid"] > total:
        print("  Note: the guest has paid more than the new total. "
              "Arrange a refund or credit.")


def record_payment():
    """Add a payment to a reservation and update its payment status."""
    reservation = _find_reservation()
    if reservation is None:
        return
    if reservation["booking_status"] == "Cancelled":
        print("  This reservation is cancelled; payments cannot be recorded.")
        return
    balance = round(reservation["total_cost"] - reservation["amount_paid"], 2)
    if balance <= 0:
        print("  This reservation is already fully paid.")
        return
    print(f"  Balance due: {fn.format_money(balance)}")
    payment = fn.get_float("Payment amount (PHP): ", 0.01, balance)
    new_paid = round(reservation["amount_paid"] + payment, 2)
    status = fn.determine_payment_status(new_paid, reservation["total_cost"])
    database.update_payment(reservation["reservation_id"], new_paid, status)
    print(f"  Payment recorded. Payment status is now: {status}.")


def change_booking_status():
    """Check a guest in or out, or cancel a booking (only valid changes)."""
    reservation = _find_reservation()
    if reservation is None:
        return
    current = reservation["booking_status"]
    options = fn.ALLOWED_STATUS_CHANGES[current]
    if not options:
        print(f"  A {current} reservation cannot be changed any further.")
        return
    new_status = fn.choose_from_list(f"Current status: {current}. Change to:", options)
    if new_status == "Cancelled" and not fn.confirm_action(
            "Cancel this reservation?"):
        print("  Cancellation aborted.")
        return
    database.update_booking_status(reservation["reservation_id"], new_status)
    print(f"  Reservation #{reservation['reservation_id']} is now {new_status}.")


def delete_reservation():
    """Delete a reservation after confirmation."""
    reservation = _find_reservation()
    if reservation is None:
        return
    show_reservations([reservation])
    if not fn.confirm_action("Delete this reservation permanently?"):
        print("  Deletion cancelled.")
        return
    database.delete_reservation(reservation["reservation_id"])
    print("  Reservation deleted.")


def check_available_rooms():
    """List rooms that are free for a date range."""
    print("\n-- Room Availability --")
    check_in, check_out = fn.get_stay_dates()
    available = fn.get_available_rooms(check_in, check_out)
    if not available:
        print("  No rooms are available for those dates.")
        return
    show_available_rooms(check_in, check_out, available)


# ---------------------------------------------------------------------------
# Analytics and sample data
# ---------------------------------------------------------------------------

def occupancy_for_period():
    """Show occupancy for a period the user chooses."""
    print("\n-- Occupancy for a Period --")
    start, end = fn.get_stay_dates()
    analytics.print_occupancy_report(start, end)


def make_charts():
    """Generate all charts and list the saved files."""
    print("\n-- Generating Charts --")
    saved = analytics.generate_all_charts()
    if saved:
        print("  Charts saved:")
        for path in saved:
            print(f"    {path}")


def load_sample_data():
    """Load the simulated sample records after confirmation."""
    print("\nThis adds SIMULATED rooms, guests, and reservations for testing "
          "and demos.")
    print("They are marked with * and are not real observations.")
    if not fn.confirm_action("Load sample data?"):
        print("  Cancelled.")
        return
    added = database.load_sample_data()
    if added == 0:
        print("  Sample data is already loaded.")
    else:
        print(f"  Loaded sample data ({added} simulated reservations).")


# ---------------------------------------------------------------------------
# Menu wiring
# ---------------------------------------------------------------------------

def rooms_menu():
    """Rooms submenu."""
    run_menu("Manage Rooms",
             [("1", "Add room"), ("2", "View all rooms"), ("3", "Search rooms"),
              ("4", "Update room"), ("5", "Delete room")],
             {"1": add_room, "2": view_rooms, "3": search_rooms,
              "4": update_room, "5": delete_room})


def guests_menu():
    """Guests submenu."""
    run_menu("Manage Guests",
             [("1", "Add guest"), ("2", "View all guests"), ("3", "Search guests"),
              ("4", "Update guest"), ("5", "Delete guest")],
             {"1": add_guest, "2": view_guests, "3": search_guests,
              "4": update_guest, "5": delete_guest})


def reservations_menu():
    """Reservations submenu."""
    run_menu("Manage Reservations",
             [("1", "New reservation"), ("2", "View all reservations"),
              ("3", "Search reservations"), ("4", "Check room availability"),
              ("5", "Change reservation dates"), ("6", "Record a payment"),
              ("7", "Check in / check out / cancel"),
              ("8", "Delete reservation")],
             {"1": make_reservation, "2": view_reservations,
              "3": search_reservations, "4": check_available_rooms,
              "5": update_reservation_dates, "6": record_payment,
              "7": change_booking_status, "8": delete_reservation})


def analytics_menu():
    """Analytics submenu."""
    run_menu("Analytics and Charts",
             [("1", "Full summary report"), ("2", "Occupancy for a chosen period"),
              ("3", "Generate charts (saved to charts/)")],
             {"1": analytics.print_summary_report, "2": occupancy_for_period,
              "3": make_charts})


def main():
    """Create the database if needed, then run the main menu."""
    database.create_tables()
    print("=" * 50)
    print(" ROOM BOOKING MANAGEMENT SYSTEM")
    print(" DSA 214 - Programming for Data Science")
    print("=" * 50)
    try:
        run_menu("Main Menu",
                 [("1", "Rooms"), ("2", "Guests"), ("3", "Reservations"),
                  ("4", "Analytics and charts"),
                  ("5", "Load simulated sample data")],
                 {"1": rooms_menu, "2": guests_menu, "3": reservations_menu,
                  "4": analytics_menu, "5": load_sample_data},
                 exit_label="Exit")
    except (KeyboardInterrupt, EOFError):
        print("\n  Input interrupted.")
    print("Goodbye! All records are saved.")


if __name__ == "__main__":
    main()

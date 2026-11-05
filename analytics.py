"""analytics.py - calculations, summary report, and chart generation.

All measures read from the SQLite database. Cancelled reservations are
excluded because they do not produce stays or revenue. Revenue for a
reservation is counted in the month of its check-in date.

Measures
--------
1. Occupancy rate per room and overall, for a chosen period
2. Revenue per month (billed, collected, outstanding)
3. Average length of stay
4. Most-booked rooms
5. Outstanding balances per guest
"""

import os

import database
import functions

CHARTS_DIR = os.path.join(database.BASE_DIR, "charts")
ACTIVE = "booking_status != 'Cancelled'"  # fixed SQL text, no user input


# ---------------------------------------------------------------------------
# Measures (return data; printing happens in print_summary_report)
# ---------------------------------------------------------------------------

def get_data_period():
    """Return (first check-in, last check-out) of active reservations, or None."""
    row = database.fetch_one(
        f"SELECT MIN(check_in) AS first_day, MAX(check_out) AS last_day "
        f"FROM reservations WHERE {ACTIVE}")
    if row is None or row["first_day"] is None:
        return None
    return row["first_day"], row["last_day"]


def occupancy_by_room(start, end):
    """Return occupancy per room between two ISO dates (start inclusive).

    Each reservation counts only the nights that fall inside the period.
    Occupancy % = booked nights / nights in period * 100.

    Returns:
        list of dicts with room_number, room_type, booked_nights,
        period_nights, occupancy_pct. Empty if the period is not valid.
    """
    period_nights = functions.calculate_nights(start, end)
    if period_nights <= 0:
        return []
    sql = """
        SELECT r.room_number, r.room_type,
               COALESCE(SUM(MAX(0, julianday(MIN(res.check_out, :end))
                                 - julianday(MAX(res.check_in, :start)))), 0)
                   AS booked_nights
        FROM rooms AS r
        LEFT JOIN reservations AS res
               ON res.room_id = r.room_id AND res.booking_status != 'Cancelled'
        GROUP BY r.room_id
        ORDER BY r.room_number
    """
    results = []
    for row in database.fetch_all(sql, {"start": start, "end": end}):
        booked = int(round(row["booked_nights"]))
        results.append({
            "room_number": row["room_number"],
            "room_type": row["room_type"],
            "booked_nights": booked,
            "period_nights": period_nights,
            "occupancy_pct": round(booked / period_nights * 100, 1),
        })
    return results


def overall_occupancy(room_results):
    """Return overall occupancy % (all rooms) from occupancy_by_room() output."""
    if not room_results:
        return 0.0
    booked = sum(item["booked_nights"] for item in room_results)
    available = sum(item["period_nights"] for item in room_results)
    return round(booked / available * 100, 1)


def revenue_by_month():
    """Return per-month totals: reservations, billed, collected, outstanding."""
    sql = f"""
        SELECT strftime('%Y-%m', check_in) AS month,
               COUNT(*)                       AS reservations,
               SUM(total_cost)                AS billed,
               SUM(amount_paid)               AS collected,
               SUM(total_cost - amount_paid)  AS outstanding
        FROM reservations
        WHERE {ACTIVE}
        GROUP BY month
        ORDER BY month
    """
    return database.fetch_all(sql)


def average_length_of_stay():
    """Return the average number of nights per active reservation (0 if none)."""
    row = database.fetch_one(
        f"SELECT AVG(julianday(check_out) - julianday(check_in)) AS avg_nights "
        f"FROM reservations WHERE {ACTIVE}")
    if row is None or row["avg_nights"] is None:
        return 0.0
    return round(row["avg_nights"], 2)


def most_booked_rooms(limit=5):
    """Return the rooms with the most reservations (ties broken by room number)."""
    sql = f"""
        SELECT r.room_number, r.room_type,
               COUNT(*) AS reservations,
               SUM(julianday(res.check_out) - julianday(res.check_in)) AS nights
        FROM reservations AS res
        JOIN rooms AS r ON r.room_id = res.room_id
        WHERE res.{ACTIVE}
        GROUP BY r.room_id
        ORDER BY reservations DESC, r.room_number
        LIMIT ?
    """
    return database.fetch_all(sql, (limit,))


def outstanding_balances():
    """Return guests who still owe money, largest balance first."""
    sql = f"""
        SELECT g.full_name,
               COUNT(*)                                  AS reservations,
               SUM(res.total_cost - res.amount_paid)     AS balance
        FROM reservations AS res
        JOIN guests AS g ON g.guest_id = res.guest_id
        WHERE res.{ACTIVE}
        GROUP BY g.guest_id
        HAVING SUM(res.total_cost - res.amount_paid) > 0
        ORDER BY balance DESC, g.full_name
    """
    return database.fetch_all(sql)


def bookings_by_room_type():
    """Return the number of active reservations per room type."""
    sql = f"""
        SELECT r.room_type, COUNT(*) AS reservations
        FROM reservations AS res
        JOIN rooms AS r ON r.room_id = res.room_id
        WHERE res.{ACTIVE}
        GROUP BY r.room_type
        ORDER BY reservations DESC, r.room_type
    """
    return database.fetch_all(sql)


def payment_status_counts():
    """Return the number of active reservations per payment status."""
    sql = f"""
        SELECT payment_status, COUNT(*) AS reservations
        FROM reservations
        WHERE {ACTIVE}
        GROUP BY payment_status
        ORDER BY payment_status
    """
    return database.fetch_all(sql)


def has_simulated_data():
    """Return True if any simulated (sample) reservation exists."""
    row = database.fetch_one(
        "SELECT COUNT(*) AS n FROM reservations WHERE is_simulated = 1")
    return row["n"] > 0


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_occupancy_report(start, end):
    """Print occupancy per room and overall for the period start..end."""
    results = occupancy_by_room(start, end)
    print(f"\n1. OCCUPANCY RATE  ({start} to {end}, "
          f"{functions.calculate_nights(start, end)} nights)")
    if not results:
        print("  The period is not valid (end date must be after start date).")
        return
    rows = [[i["room_number"], i["room_type"], i["booked_nights"],
             i["period_nights"], f"{i['occupancy_pct']}%"] for i in results]
    functions.print_table(["Room", "Type", "Booked nights", "Period nights",
                           "Occupancy"], rows)
    print(f"  Overall occupancy: {overall_occupancy(results)}%")


def print_summary_report(start=None, end=None):
    """Print all five measures. Defaults to the period covered by the data."""
    period = get_data_period()
    if period is None:
        print("\n  No reservation data yet. Add reservations or load the "
              "sample data first.")
        return
    start = start or period[0]
    end = end or period[1]

    print("\n" + "=" * 60)
    print("ROOM BOOKING SUMMARY REPORT")
    if has_simulated_data():
        print("Note: includes simulated sample records (marked * in lists).")
    print("=" * 60)

    print_occupancy_report(start, end)

    print("\n2. REVENUE BY MONTH (by check-in month, cancelled excluded)")
    rows = [[r["month"], r["reservations"], functions.format_money(r["billed"]),
             functions.format_money(r["collected"]),
             functions.format_money(r["outstanding"])] for r in revenue_by_month()]
    functions.print_table(["Month", "Bookings", "Billed", "Collected",
                           "Outstanding"], rows)

    print(f"\n3. AVERAGE LENGTH OF STAY: {average_length_of_stay()} nights")

    print("\n4. MOST-BOOKED ROOMS")
    rows = [[r["room_number"], r["room_type"], r["reservations"],
             int(r["nights"])] for r in most_booked_rooms()]
    functions.print_table(["Room", "Type", "Bookings", "Nights"], rows)

    print("\n5. OUTSTANDING BALANCES BY GUEST")
    rows = [[r["full_name"], r["reservations"],
             functions.format_money(r["balance"])] for r in outstanding_balances()]
    functions.print_table(["Guest", "Bookings", "Balance due"], rows)


# ---------------------------------------------------------------------------
# Charts (matplotlib)
# ---------------------------------------------------------------------------

def _get_pyplot():
    """Import matplotlib lazily; return pyplot or None if not installed."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # draw to files, no window needed
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        print("  matplotlib is not installed. Run: pip install -r requirements.txt")
        return None


def _finish_chart(plt, figure, filename):
    """Add the simulated-data note if needed, save the figure, return its path."""
    if has_simulated_data():
        figure.text(0.99, 0.01, "Includes simulated sample data",
                    ha="right", va="bottom", fontsize=8, color="gray")
    os.makedirs(CHARTS_DIR, exist_ok=True)
    path = os.path.join(CHARTS_DIR, filename)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def chart_monthly_revenue():
    """Bar chart of collected vs outstanding money per month. Returns the path."""
    data = revenue_by_month()
    if not data:
        print("  No data for the monthly revenue chart.")
        return None
    plt = _get_pyplot()
    if plt is None:
        return None
    months = [row["month"] for row in data]
    collected = [row["collected"] for row in data]
    outstanding = [row["outstanding"] for row in data]
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.bar(months, collected, label="Collected", color="#2a9d8f")
    axis.bar(months, outstanding, bottom=collected, label="Outstanding",
             color="#e76f51")
    axis.set_title("Monthly Revenue: Collected vs Outstanding")
    axis.set_xlabel("Month (by check-in date)")
    axis.set_ylabel("Amount (PHP)")
    axis.legend()
    return _finish_chart(plt, figure, "monthly_revenue.png")


def chart_bookings_by_room_type():
    """Bar chart of reservation counts per room type. Returns the path."""
    data = bookings_by_room_type()
    if not data:
        print("  No data for the room type chart.")
        return None
    plt = _get_pyplot()
    if plt is None:
        return None
    figure, axis = plt.subplots(figsize=(7, 5))
    types = [row["room_type"] for row in data]
    counts = [row["reservations"] for row in data]
    bars = axis.bar(types, counts, color="#264653")
    axis.bar_label(bars)
    axis.set_title("Reservations by Room Type")
    axis.set_xlabel("Room type")
    axis.set_ylabel("Number of reservations")
    return _finish_chart(plt, figure, "bookings_by_room_type.png")


def chart_payment_status():
    """Pie chart of reservations by payment status. Returns the path."""
    data = payment_status_counts()
    if not data:
        print("  No data for the payment status chart.")
        return None
    plt = _get_pyplot()
    if plt is None:
        return None
    colors = {"Paid": "#2a9d8f", "Partial": "#e9c46a", "Unpaid": "#e76f51"}
    labels = [row["payment_status"] for row in data]
    counts = [row["reservations"] for row in data]
    figure, axis = plt.subplots(figsize=(6, 6))
    axis.pie(counts, labels=labels, autopct="%1.1f%%", startangle=90,
             colors=[colors.get(label, "#999999") for label in labels])
    axis.set_title("Payment Status of Reservations")
    return _finish_chart(plt, figure, "payment_status.png")


def generate_all_charts():
    """Create every chart and return the list of files that were saved."""
    saved = []
    for make_chart in (chart_monthly_revenue, chart_bookings_by_room_type,
                       chart_payment_status):
        path = make_chart()
        if path:
            saved.append(path)
    return saved

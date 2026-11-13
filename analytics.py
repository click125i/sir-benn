"""
Esmiringhoy Hotel - Analytics
-----------------------------
Summary numbers about the reservations saved in hotel.db, plus a text
report laid out like the receipt (the main program shows it on the
Analytics screen).

Run this file by itself to print the report in the terminal:
    python analytics.py
"""
from datetime import date, timedelta

from database import HOTEL_NAME, PAYMENT_METHODS, ROOMS, ROOM_NAMES, init_db, query
from functions import peso


# ----------------------------------------------------------------------------
# Numbers
# ----------------------------------------------------------------------------
def summary():
    """Totals and averages over every reservation."""
    return query("""SELECT COUNT(*)                  AS bookings,
                           COALESCE(SUM(total), 0)   AS revenue,
                           COALESCE(AVG(total), 0)   AS avg_value,
                           COALESCE(AVG(nights), 0)  AS avg_nights,
                           COALESCE(AVG(guests), 0)  AS avg_guests
                    FROM bookings""")[0]


def revenue_by_room():
    """One row per room type (rooms with no bookings show 0)."""
    return query("""SELECT r.room_type AS room,
                           COUNT(b.ref) AS bookings,
                           COALESCE(SUM(b.nights), 0) AS nights,
                           COALESCE(SUM(b.total), 0)  AS revenue
                    FROM rooms r LEFT JOIN bookings b ON b.room = r.room_type
                    GROUP BY r.room_type
                    ORDER BY revenue DESC, r.rate DESC""")


def bookings_by_payment():
    """One row per payment method (methods nobody used show 0)."""
    found = {r["payment"]: r for r in query(
        """SELECT payment, COUNT(*) AS bookings, SUM(total) AS revenue
           FROM bookings GROUP BY payment""")}
    return [found.get(p, {"payment": p, "bookings": 0, "revenue": 0}) for p in PAYMENT_METHODS]


def bookings_by_month():
    """Reservations grouped by the month of check-in (YYYY-MM), oldest first."""
    return query("""SELECT substr(checkin, 1, 7) AS month,
                           COUNT(*) AS bookings, SUM(total) AS revenue
                    FROM bookings GROUP BY month ORDER BY month""")


def top_guests(limit=5):
    """Guests with the most reservations."""
    return query("""SELECT MIN(name) AS name, COUNT(*) AS stays, SUM(total) AS spent
                    FROM bookings GROUP BY LOWER(name)
                    ORDER BY stays DESC, spent DESC LIMIT ?""", (limit,))


def upcoming_checkins(days=7):
    """Reservations that check in from today up to `days` days ahead."""
    today = date.today()
    return query("""SELECT ref, name, room, checkin, time FROM bookings
                    WHERE checkin >= ? AND checkin <= ?
                    ORDER BY checkin, ref""",
                 (today.isoformat(), (today + timedelta(days=days)).isoformat()))


def occupancy(start, end):
    """Room-nights used vs. available for every room type, for the nights [start, end)."""
    days = (end - start).days
    if days < 1:
        raise ValueError("The end date must be after the start date.")
    result = []
    for room in ROOM_NAMES:
        rows = query("""SELECT checkin, checkout FROM bookings
                        WHERE room = ? AND checkin < ? AND checkout > ?""",
                     (room, end.isoformat(), start.isoformat()))
        used = 0
        for r in rows:      # count only the nights that fall inside the window
            s = max(start, date.fromisoformat(r["checkin"]))
            e = min(end, date.fromisoformat(r["checkout"]))
            used += (e - s).days
        available = ROOMS[room]["total"] * days
        result.append({"room": room, "used": used, "available": available,
                       "percent": used / available * 100})
    return result


# ----------------------------------------------------------------------------
# Text report
# ----------------------------------------------------------------------------
def analytics_report(start=None, end=None):
    start = start or date.today()
    end = end or start + timedelta(days=30)
    w = 60
    line = "=" * w
    dash = "-" * w

    def row(label, value, split=34):
        return f"{label:<{split}}{value:>{w - split}}"

    s = summary()
    out = [
        line,
        HOTEL_NAME.upper().center(w),
        "ANALYTICS REPORT".center(w),
        line,
        "SUMMARY",
        row("Total reservations", s["bookings"]),
        row("Total revenue (incl. VAT)", peso(s["revenue"])),
        row("Average booking value", peso(s["avg_value"])),
        row("Average stay", f"{s['avg_nights']:.1f} night(s)"),
        row("Average guests per booking", f"{s['avg_guests']:.1f}"),
        row("Check-ins in the next 7 days", len(upcoming_checkins(7))),
        dash,
        "REVENUE BY ROOM TYPE",
        f"{'Room':<18}{'Bookings':>9}{'Nights':>8}{'Revenue':>25}",
    ]
    for r in revenue_by_room():
        out.append(f"{r['room']:<18}{r['bookings']:>9}{r['nights']:>8}{peso(r['revenue']):>25}")

    out += [dash, "PAYMENT METHODS"]
    for p in bookings_by_payment():
        out.append(row(f"{p['payment']} ({p['bookings']})", peso(p["revenue"] or 0)))

    occ = occupancy(start, end)
    days = (end - start).days
    out += [dash, f"OCCUPANCY {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')} ({days} nights)"]
    for o in occ:
        out.append(row(o["room"], f"{o['percent']:.1f}%  ({o['used']}/{o['available']})"))
    used = sum(o["used"] for o in occ)
    available = sum(o["available"] for o in occ)
    out.append(row("All rooms", f"{used / available * 100:.1f}%  ({used}/{available})"))

    months = bookings_by_month()[-4:]
    out += [dash, "RESERVATIONS BY CHECK-IN MONTH (latest 4)"]
    if months:
        for m in months:
            out.append(row(f"{m['month']}  ({m['bookings']})", peso(m["revenue"])))
    else:
        out.append("No reservations yet.")

    guests = top_guests(3)
    out += [dash, "TOP GUESTS"]
    if guests:
        for g in guests:
            out.append(row(f"{g['name']} ({g['stays']})", peso(g["spent"])))
    else:
        out.append("No reservations yet.")
    out.append(line)
    return "\n".join(out)


# ----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print(analytics_report())

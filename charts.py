"""
Esmiringhoy Hotel - Charts (matplotlib)
---------------------------------------
Draws charts from the numbers in analytics.py. The main program shows them
in a window (Analytics screen -> "Show Charts").

Needs matplotlib (install it once):
    pip install matplotlib

Run this file by itself to save every chart as a PNG in the "charts" folder
and open the dashboard window:
    python charts.py
"""
import os
from datetime import date, datetime, timedelta

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator

from database import HOTEL_NAME, init_db
from analytics import (summary, revenue_by_room, bookings_by_payment, bookings_by_month,
                       top_guests, upcoming_checkins, occupancy)
from functions import peso

# ----------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------
FOLDER = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(FOLDER, "charts")      # where "Save all as PNG" puts the images

BLUE, LIGHT_BLUE, GOLD, GREEN = "#1f4e79", "#5dade2", "#f5b041", "#58d68d"
PAY_COLORS = {"ONLINE": LIGHT_BLUE, "CASH": GOLD, "BANKING": GREEN}


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def tidy(ax):
    """Remove the top and right lines so the chart looks cleaner."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def no_data(ax, message="No reservations yet"):
    """Show a message instead of an empty chart."""
    ax.text(0.5, 0.5, message, ha="center", va="center", color="gray",
            fontsize=12, transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)


def thousands(value, _position=None):
    """Axis label like 12,500 (the second argument is required by matplotlib)."""
    return f"{value:,.0f}"


# ----------------------------------------------------------------------------
# One function per chart. Each one draws on the `ax` it is given.
# ----------------------------------------------------------------------------
def chart_summary(ax):
    """Text panel with the main numbers (used on the dashboard)."""
    ax.set_title("Summary", fontweight="bold")
    ax.axis("off")
    s = summary()
    items = [
        ("Total reservations", f"{s['bookings']}"),
        ("Total revenue (incl. VAT)", peso(s["revenue"])),
        ("Average booking value", peso(s["avg_value"])),
        ("Average stay", f"{s['avg_nights']:.1f} night(s)"),
        ("Average guests per booking", f"{s['avg_guests']:.1f}"),
        ("Check-ins in the next 7 days", f"{len(upcoming_checkins(7))}"),
    ]
    for i, (label, value) in enumerate(items):
        y = 0.88 - i * 0.16
        ax.text(0.02, y, label, ha="left", va="center", fontsize=10, transform=ax.transAxes)
        ax.text(0.98, y, value, ha="right", va="center", fontsize=10,
                fontweight="bold", transform=ax.transAxes)


def chart_revenue_by_room(ax):
    """Horizontal bars: total revenue of each room type (number of bookings under the name)."""
    ax.set_title("Revenue by room type", fontweight="bold")
    rows = revenue_by_room()
    if sum(r["revenue"] for r in rows) == 0:
        return no_data(ax)

    names = [f"{r['room']}\n({r['bookings']} booking(s))" for r in rows]
    money = [r["revenue"] for r in rows]
    bars = ax.barh(names, money, color=BLUE)
    ax.bar_label(bars, labels=[f"{m:,.0f}" for m in money], padding=4, fontsize=9)
    ax.invert_yaxis()                       # biggest room type on top
    ax.set_xlim(0, max(money) * 1.3)        # leave space for the number at the end of the bar
    ax.xaxis.set_major_locator(MaxNLocator(nbins=4))      # fewer ticks so the numbers don't touch
    ax.xaxis.set_major_formatter(FuncFormatter(thousands))
    ax.set_xlabel("Revenue incl. VAT (PHP)")
    tidy(ax)


def chart_payment(ax):
    """Pie: how guests pay (only the methods that were used)."""
    ax.set_title("Bookings by payment method", fontweight="bold")
    rows = [p for p in bookings_by_payment() if p["bookings"] > 0]
    if not rows:
        return no_data(ax)

    ax.pie([p["bookings"] for p in rows],
           labels=[f"{p['payment']} ({p['bookings']})" for p in rows],
           colors=[PAY_COLORS[p["payment"]] for p in rows],
           autopct="%1.0f%%", startangle=90,
           wedgeprops={"edgecolor": "white"})


def chart_by_month(ax):
    """Bars: how many reservations check in each month (latest 12 months)."""
    ax.set_title("Reservations by check-in month", fontweight="bold")
    rows = bookings_by_month()[-12:]
    if not rows:
        return no_data(ax)

    months = [datetime.strptime(r["month"], "%Y-%m").strftime("%b %Y") for r in rows]
    counts = [r["bookings"] for r in rows]
    bars = ax.bar(months, counts, color=LIGHT_BLUE)
    ax.bar_label(bars, padding=2)
    ax.set_ylim(0, max(counts) * 1.2)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))     # no 0.5 reservations
    ax.set_ylabel("Reservations")
    ax.tick_params(axis="x", rotation=30)
    tidy(ax)


def chart_occupancy(ax, days=30):
    """Bars: % of room-nights used for each room type, from today for `days` nights."""
    start = date.today()
    end = start + timedelta(days=days)
    ax.set_title(f"Room occupancy, next {days} nights", fontweight="bold")

    rows = occupancy(start, end)
    used = sum(r["used"] for r in rows)
    available = sum(r["available"] for r in rows)
    names = [r["room"] for r in rows] + ["All rooms"]
    percents = [r["percent"] for r in rows] + [used / available * 100]
    colors = [LIGHT_BLUE] * len(rows) + [BLUE]

    bars = ax.barh(names, percents, color=colors)
    ax.bar_label(bars, labels=[f"{p:.1f}%" for p in percents], padding=4, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 125)                     # a full bar (100%) still has room for its label
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("% of room-nights booked")
    tidy(ax)


def chart_top_guests(ax):
    """Bars: guests with the most reservations."""
    ax.set_title("Top guests (most stays)", fontweight="bold")
    rows = top_guests(5)
    if not rows:
        return no_data(ax)

    names = [r["name"].title()[:20] for r in rows]
    stays = [r["stays"] for r in rows]
    bars = ax.barh(names, stays, color=GREEN)
    ax.bar_label(bars, labels=[f"{r['stays']} stay(s) | PHP {r['spent']:,.0f}" for r in rows],
                 padding=4, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, max(stays) * 2.2)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel("Number of stays")
    tidy(ax)


# Name shown in the picker -> function that draws it
CHARTS = {
    "Revenue by room type": chart_revenue_by_room,
    "Bookings by payment method": chart_payment,
    "Reservations by month": chart_by_month,
    "Room occupancy": chart_occupancy,
    "Top guests": chart_top_guests,
}
DASHBOARD = "Dashboard (all charts)"
CHOICES = [DASHBOARD] + list(CHARTS)


# ----------------------------------------------------------------------------
# Put the charts on a figure
# ----------------------------------------------------------------------------
def draw_dashboard(fig):
    """All charts on one figure (2 rows x 3 columns)."""
    fig.clear()
    fig.suptitle(f"{HOTEL_NAME} - Analytics Dashboard", fontsize=16, fontweight="bold")
    axes = fig.subplots(2, 3).flatten()
    chart_summary(axes[0])
    for ax, draw in zip(axes[1:], CHARTS.values()):
        draw(ax)


def draw_chart(fig, name=DASHBOARD):
    """Draw the dashboard, or just one chart, on `fig` (replaces what was there)."""
    if name == DASHBOARD:
        draw_dashboard(fig)
        return
    fig.clear()
    CHARTS[name](fig.add_subplot(111))


def save_all(folder=CHART_DIR):
    """Save the dashboard and every chart as a PNG. Returns the list of file paths."""
    os.makedirs(folder, exist_ok=True)
    paths = []
    for name in CHOICES:
        size = (13, 7.5) if name == DASHBOARD else (9, 5.5)
        fig = Figure(figsize=size, layout="constrained")
        draw_chart(fig, name)
        # "Revenue by room type" -> revenue_by_room_type.png, "Dashboard (all charts)" -> dashboard.png
        file_name = name.split(" (")[0].lower().replace(" ", "_") + ".png"
        path = os.path.join(folder, file_name)
        fig.savefig(path, dpi=150)
        paths.append(path)
    return paths


# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import matplotlib.pyplot as plt     # only needed here, to open a window

    init_db()
    for p in save_all():
        print("Saved", p)
    fig = plt.figure(figsize=(13, 7.5), layout="constrained")
    draw_dashboard(fig)
    plt.show()

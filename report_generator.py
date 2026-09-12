import json
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from fpdf import FPDF

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def week_dates(monday: date) -> Dict[str, date]:
    if monday.weekday() != 0:
        raise ValueError("Week start must be a Monday.")
    return {day: monday + timedelta(days=i) for i, day in enumerate(DAYS)}


def blank_week(monday: date) -> Dict[str, Dict]:
    dates = week_dates(monday)
    return {day: {"date": dates[day].isoformat(), "machines": {}} for day in DAYS}


def normalise_machine_data(data: Dict) -> Dict:
    completed = int(data.get("Completed Quantity", 0) or 0)
    rejected = int(data.get("Rejected Quantity", 0) or 0)
    return {
        "Product Name": str(data.get("Product Name", "")).strip(),
        "Manufacturing Order": str(data.get("Manufacturing Order", "")).strip(),
        "Operation Number": str(data.get("Operation Number", "")).strip(),
        "Completed Quantity": completed,
        "Rejected Quantity": rejected,
        "Accepted Quantity": completed - rejected,
    }


def save_payload(monday: date, day_data: Dict, machines: List[str], products: List[str]) -> str:
    payload = {
        "week_start": monday.isoformat(),
        "machines": sorted(set(machines), key=str.lower),
        "products": sorted(set(products), key=str.lower),
        "day_data": day_data,
    }
    return json.dumps(payload, indent=2)


def load_payload(raw: bytes | str) -> Tuple[date, Dict, List[str], List[str]]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")
    data = json.loads(raw)
    monday = datetime.strptime(data["week_start"], "%Y-%m-%d").date()
    day_data = data.get("day_data") or blank_week(monday)
    machines = list(data.get("machines", []))
    products = list(data.get("products", []))
    return monday, day_data, machines, products


def weekly_summary(day_data: Dict) -> Dict[str, int]:
    completed = rejected = accepted = 0
    for day in DAYS:
        for machine_data in day_data.get(day, {}).get("machines", {}).values():
            item = normalise_machine_data(machine_data)
            completed += item["Completed Quantity"]
            rejected += item["Rejected Quantity"]
            accepted += item["Accepted Quantity"]
    return {
        "Completed Total": completed,
        "Rejected Total": rejected,
        "Accepted Total": accepted,
    }


def _chart_bytes(labels: List[str], values: List[int], title: str, ylabel: str) -> BytesIO:
    fig, ax = plt.subplots(figsize=(10, 5.2))
    bars = ax.bar(labels, values)
    ceiling = max(values) if values else 0
    ax.set_ylim(0, max(ceiling * 1.25, 1))
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(value), ha="center", va="bottom")
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    buf.seek(0)
    return buf


def _summary_chart(summary: Dict[str, int]) -> BytesIO:
    labels = ["Completed", "Rejected", "Accepted"]
    values = [summary["Completed Total"], summary["Rejected Total"], summary["Accepted Total"]]
    return _chart_bytes(labels, values, "Weekly Production Summary", "Quantity")


def _daily_chart(machines: Dict[str, Dict]) -> BytesIO:
    names = list(machines.keys())
    values = [normalise_machine_data(machines[name])["Completed Quantity"] for name in names]
    return _chart_bytes(names, values, "Completed Quantity by Machine", "Completed Quantity")


def generate_pdf(monday: date, day_data: Dict) -> bytes:
    dates = week_dates(monday)
    summary = weekly_summary(day_data)
    pdf = FPDF(orientation="L", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 18, "Weekly Production Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=14)
    pdf.cell(0, 10, f"{dates['Monday'].strftime('%d/%m/%Y')} to {dates['Saturday'].strftime('%d/%m/%Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
    chart = _summary_chart(summary)
    pdf.image(chart, x=25, y=48, w=247)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Weekly Summary", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=13)
    pdf.ln(8)
    col_w = 90
    for label in ["Completed Total", "Rejected Total", "Accepted Total"]:
        pdf.cell(col_w, 12, f"{label}: {summary[label]}", border=1, align="C")
    pdf.ln(18)
    pdf.image(_summary_chart(summary), x=25, y=62, w=247)

    for day in DAYS:
        machines = day_data.get(day, {}).get("machines", {})
        if not machines:
            continue
        pdf.add_page()
        day_date = day_data[day].get("date") or dates[day].isoformat()
        try:
            pretty_date = datetime.strptime(day_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pretty_date = day_date
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 10, day, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 8, f"Date: {pretty_date}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.image(_daily_chart(machines), x=30, y=38, w=237)
        pdf.set_y(142)
        headers = ["Machine", "Product", "MO", "Op", "Completed", "Rejected", "Accepted"]
        widths = [42, 60, 42, 28, 36, 36, 36]
        pdf.set_font("Helvetica", "B", 8)
        for h, w in zip(headers, widths):
            pdf.cell(w, 8, h, border=1, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", size=8)
        for machine, raw in machines.items():
            item = normalise_machine_data(raw)
            row = [
                machine,
                item["Product Name"],
                item["Manufacturing Order"],
                item["Operation Number"],
                str(item["Completed Quantity"]),
                str(item["Rejected Quantity"]),
                str(item["Accepted Quantity"]),
            ]
            for value, w in zip(row, widths):
                text = str(value)
                if len(text) > 24:
                    text = text[:21] + "..."
                pdf.cell(w, 8, text, border=1)
            pdf.ln()

    return bytes(pdf.output())

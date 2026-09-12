import json
from collections import defaultdict
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
    if monday.weekday() != 0:
        raise ValueError("Saved week_start is not a Monday.")
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


def load_weekly_report(raw: bytes | str, filename: str = "") -> Dict:
    monday, day_data, machines, products = load_payload(raw)
    return {
        "filename": filename,
        "week_start": monday,
        "week_end": monday + timedelta(days=5),
        "day_data": day_data,
        "machines": machines,
        "products": products,
        "summary": weekly_summary(day_data),
    }


def _month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def _month_label(key: str) -> str:
    return datetime.strptime(key, "%Y-%m").strftime("%b %Y")


def aggregate_weekly_reports(reports: List[Dict]) -> Dict:
    if not reports:
        raise ValueError("At least one weekly report is required.")

    sorted_reports = sorted(reports, key=lambda r: r["week_start"])
    week_starts = [r["week_start"] for r in sorted_reports]
    if len(week_starts) != len(set(week_starts)):
        raise ValueError("Duplicate weekly reports detected. Each week can only be included once.")

    completed = rejected = accepted = 0
    machine_totals = defaultdict(lambda: {"Completed": 0, "Rejected": 0, "Accepted": 0})
    product_totals = defaultdict(lambda: {"Completed": 0, "Rejected": 0, "Accepted": 0})
    monthly_totals = defaultdict(lambda: {"Completed": 0, "Rejected": 0, "Accepted": 0, "Weeks": set()})
    machine_monthly = defaultdict(lambda: defaultdict(lambda: {"Completed": 0, "Rejected": 0, "Accepted": 0}))
    weekly_rows = []

    for report in sorted_reports:
        summary = report["summary"]
        completed += summary["Completed Total"]
        rejected += summary["Rejected Total"]
        accepted += summary["Accepted Total"]
        weekly_rows.append({
            "Week Starting": report["week_start"].isoformat(),
            "Week Ending": report["week_end"].isoformat(),
            "Completed": summary["Completed Total"],
            "Rejected": summary["Rejected Total"],
            "Accepted": summary["Accepted Total"],
        })

        for day in DAYS:
            day_block = report["day_data"].get(day, {})
            machines = day_block.get("machines", {})
            raw_date = day_block.get("date")
            try:
                production_day = datetime.strptime(raw_date, "%Y-%m-%d").date() if raw_date else report["week_start"]
            except ValueError:
                production_day = report["week_start"]
            month = _month_key(production_day)
            monthly_totals[month]["Weeks"].add(report["week_start"].isoformat())

            for machine, raw in machines.items():
                item = normalise_machine_data(raw)
                mt = machine_totals[machine]
                mt["Completed"] += item["Completed Quantity"]
                mt["Rejected"] += item["Rejected Quantity"]
                mt["Accepted"] += item["Accepted Quantity"]

                pt = product_totals[item["Product Name"] or "Unspecified"]
                pt["Completed"] += item["Completed Quantity"]
                pt["Rejected"] += item["Rejected Quantity"]
                pt["Accepted"] += item["Accepted Quantity"]

                mon = monthly_totals[month]
                mon["Completed"] += item["Completed Quantity"]
                mon["Rejected"] += item["Rejected Quantity"]
                mon["Accepted"] += item["Accepted Quantity"]

                mm = machine_monthly[machine][month]
                mm["Completed"] += item["Completed Quantity"]
                mm["Rejected"] += item["Rejected Quantity"]
                mm["Accepted"] += item["Accepted Quantity"]

    machine_rows = []
    for name, values in sorted(machine_totals.items(), key=lambda x: x[0].lower()):
        rate = values["Rejected"] / values["Completed"] * 100 if values["Completed"] else 0.0
        machine_rows.append({"Machine": name, **values, "Rejection Rate %": rate})

    product_rows = []
    for name, values in sorted(product_totals.items(), key=lambda x: x[0].lower()):
        rate = values["Rejected"] / values["Completed"] * 100 if values["Completed"] else 0.0
        product_rows.append({"Product": name, **values, "Rejection Rate %": rate})

    monthly_rows = []
    for month, values in sorted(monthly_totals.items()):
        rate = values["Rejected"] / values["Completed"] * 100 if values["Completed"] else 0.0
        monthly_rows.append({
            "Month Key": month,
            "Month": _month_label(month),
            "Weeks Included": len(values["Weeks"]),
            "Completed": values["Completed"],
            "Rejected": values["Rejected"],
            "Accepted": values["Accepted"],
            "Rejection Rate %": rate,
        })

    machine_trend_rows = []
    months = [row["Month Key"] for row in monthly_rows]
    for machine in sorted(machine_monthly, key=str.lower):
        for month in months:
            values = machine_monthly[machine].get(month, {"Completed": 0, "Rejected": 0, "Accepted": 0})
            rate = values["Rejected"] / values["Completed"] * 100 if values["Completed"] else 0.0
            machine_trend_rows.append({
                "Machine": machine,
                "Month Key": month,
                "Month": _month_label(month),
                "Completed": values["Completed"],
                "Rejected": values["Rejected"],
                "Accepted": values["Accepted"],
                "Rejection Rate %": rate,
            })

    rejection_rate = (rejected / completed * 100) if completed else 0.0
    return {
        "reports": sorted_reports,
        "start_date": sorted_reports[0]["week_start"],
        "end_date": sorted_reports[-1]["week_end"],
        "weeks_included": len(sorted_reports),
        "Completed Total": completed,
        "Rejected Total": rejected,
        "Accepted Total": accepted,
        "Rejection Rate": rejection_rate,
        "weekly_rows": weekly_rows,
        "machine_rows": machine_rows,
        "product_rows": product_rows,
        "monthly_rows": monthly_rows,
        "machine_trend_rows": machine_trend_rows,
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
    return _chart_bytes(
        ["Completed", "Rejected", "Accepted"],
        [summary["Completed Total"], summary["Rejected Total"], summary["Accepted Total"]],
        "Weekly Production Summary",
        "Quantity",
    )


def _daily_chart(machines: Dict[str, Dict]) -> BytesIO:
    names = list(machines.keys())
    values = [normalise_machine_data(machines[name])["Completed Quantity"] for name in names]
    return _chart_bytes(names, values, "Completed Quantity by Machine", "Completed Quantity")


def _weekly_trend_chart(aggregate: Dict) -> BytesIO:
    labels = [datetime.strptime(r["Week Starting"], "%Y-%m-%d").strftime("%d/%m") for r in aggregate["weekly_rows"]]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.plot(labels, [r["Completed"] for r in aggregate["weekly_rows"]], marker="o", label="Completed")
    ax.plot(labels, [r["Accepted"] for r in aggregate["weekly_rows"]], marker="o", label="Accepted")
    ax.plot(labels, [r["Rejected"] for r in aggregate["weekly_rows"]], marker="o", label="Rejected")
    ax.set_title("Weekly Production Trend")
    ax.set_xlabel("Week Starting")
    ax.set_ylabel("Quantity")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    buf.seek(0)
    return buf


def _monthly_comparison_chart(aggregate: Dict) -> BytesIO:
    rows = aggregate.get("monthly_rows", [])
    labels = [r["Month"] for r in rows]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.plot(labels, [r["Completed"] for r in rows], marker="o", label="Completed")
    ax.plot(labels, [r["Accepted"] for r in rows], marker="o", label="Accepted")
    ax.plot(labels, [r["Rejected"] for r in rows], marker="o", label="Rejected")
    ax.set_title("Month-to-Month Production Comparison")
    ax.set_xlabel("Month")
    ax.set_ylabel("Quantity")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    buf.seek(0)
    return buf


def _machine_trend_chart(aggregate: Dict) -> BytesIO:
    rows = aggregate.get("machine_trend_rows", [])
    fig, ax = plt.subplots(figsize=(11, 5.4))
    machines = sorted({r["Machine"] for r in rows}, key=str.lower)
    months = [r["Month"] for r in aggregate.get("monthly_rows", [])]
    for machine in machines:
        machine_rows = [r for r in rows if r["Machine"] == machine]
        values_by_month = {r["Month"]: r["Accepted"] for r in machine_rows}
        ax.plot(months, [values_by_month.get(month, 0) for month in months], marker="o", label=machine)
    ax.set_title("Machine Accepted Production Trend by Month")
    ax.set_xlabel("Month")
    ax.set_ylabel("Accepted Quantity")
    ax.tick_params(axis="x", rotation=45)
    if machines:
        ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    buf.seek(0)
    return buf


def _safe_cell_text(value, max_len: int = 28) -> str:
    text = str(value)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def _add_aggregate_table(pdf: FPDF, title: str, rows: List[Dict], first_col: str):
    if not rows:
        return
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, title, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    headers = [first_col, "Completed", "Rejected", "Accepted"]
    widths = [120, 50, 50, 50]
    pdf.set_font("Helvetica", "B", 9)
    for header, width in zip(headers, widths):
        pdf.cell(width, 8, header, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", size=9)
    for row in rows:
        values = [row[first_col], row["Completed"], row["Rejected"], row["Accepted"]]
        for value, width in zip(values, widths):
            pdf.cell(width, 8, _safe_cell_text(value), border=1)
        pdf.ln()


def _add_monthly_table(pdf: FPDF, rows: List[Dict]):
    if not rows:
        return
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Month-by-Month Comparison", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.image(_monthly_comparison_chart({"monthly_rows": rows}), x=25, y=28, w=247)
    pdf.set_y(130)
    headers = ["Month", "Weeks", "Completed", "Rejected", "Accepted", "Reject %"]
    widths = [60, 35, 45, 45, 45, 42]
    pdf.set_font("Helvetica", "B", 8)
    for header, width in zip(headers, widths):
        pdf.cell(width, 8, header, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", size=8)
    for row in rows:
        values = [row["Month"], row["Weeks Included"], row["Completed"], row["Rejected"], row["Accepted"], f"{row['Rejection Rate %']:.2f}%"]
        for value, width in zip(values, widths):
            pdf.cell(width, 8, str(value), border=1, align="C")
        pdf.ln()


def generate_period_pdf(aggregate: Dict, report_type: str) -> bytes:
    title = f"{report_type} Production Report"
    pdf = FPDF(orientation="L", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 18, title, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=14)
    pdf.cell(0, 10, f"{aggregate['start_date'].strftime('%d/%m/%Y')} to {aggregate['end_date'].strftime('%d/%m/%Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 9, f"Weekly reports included: {aggregate['weeks_included']}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.image(_weekly_trend_chart(aggregate), x=25, y=58, w=247)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Overall Summary", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(7)
    metrics = [
        ("Completed Total", aggregate["Completed Total"]),
        ("Rejected Total", aggregate["Rejected Total"]),
        ("Accepted Total", aggregate["Accepted Total"]),
        ("Rejection Rate", f"{aggregate['Rejection Rate']:.2f}%"),
    ]
    for label, value in metrics:
        pdf.cell(68, 12, f"{label}: {value}", border=1, align="C")
    pdf.ln(18)
    pdf.image(_weekly_trend_chart(aggregate), x=25, y=65, w=247)

    if report_type.lower().startswith("annual") or len(aggregate.get("monthly_rows", [])) > 1:
        _add_monthly_table(pdf, aggregate.get("monthly_rows", []))
        if aggregate.get("machine_trend_rows"):
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 18)
            pdf.cell(0, 12, "Machine Performance Trends", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.image(_machine_trend_chart(aggregate), x=20, y=30, w=257)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Week-by-Week Summary", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    headers = ["Week Starting", "Week Ending", "Completed", "Rejected", "Accepted"]
    widths = [58, 58, 52, 52, 52]
    pdf.set_font("Helvetica", "B", 9)
    for header, width in zip(headers, widths):
        pdf.cell(width, 8, header, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", size=9)
    for row in aggregate["weekly_rows"]:
        for value, width in zip([row[h] for h in headers], widths):
            pdf.cell(width, 8, str(value), border=1, align="C")
        pdf.ln()

    _add_aggregate_table(pdf, "Production by Machine", aggregate["machine_rows"], "Machine")
    _add_aggregate_table(pdf, "Production by Product", aggregate["product_rows"], "Product")
    return bytes(pdf.output())


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
    pdf.image(_summary_chart(summary), x=25, y=48, w=247)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Weekly Summary", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    for label in ["Completed Total", "Rejected Total", "Accepted Total"]:
        pdf.cell(90, 12, f"{label}: {summary[label]}", border=1, align="C")
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
            row = [machine, item["Product Name"], item["Manufacturing Order"], item["Operation Number"], str(item["Completed Quantity"]), str(item["Rejected Quantity"]), str(item["Accepted Quantity"])]
            for value, w in zip(row, widths):
                pdf.cell(w, 8, _safe_cell_text(value, 24), border=1)
            pdf.ln()

    return bytes(pdf.output())

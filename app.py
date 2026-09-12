from datetime import date, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from report_generator import (
    DAYS,
    aggregate_weekly_reports,
    blank_week,
    generate_pdf,
    generate_period_pdf,
    load_payload,
    load_weekly_report,
    normalise_machine_data,
    save_payload,
    week_dates,
    weekly_summary,
)

st.set_page_config(page_title="Weekly Production Report Generator", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    .block-container {max-width: 1500px; padding-top: 1.2rem;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def most_recent_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def reset_week(monday: date):
    st.session_state.week_start = monday
    st.session_state.day_data = blank_week(monday)


if "week_start" not in st.session_state:
    st.session_state.week_start = most_recent_monday()
if "day_data" not in st.session_state:
    st.session_state.day_data = blank_week(st.session_state.week_start)
if "machines" not in st.session_state:
    st.session_state.machines = []
if "products" not in st.session_state:
    st.session_state.products = []

st.title("Weekly Production Report Generator")
st.caption("Enter production data by day and machine, review the week, generate a weekly PDF, or combine saved weeks into monthly and annual management reports.")

with st.sidebar:
    st.header("Saved data")
    uploaded = st.file_uploader("Load saved weekly JSON", type=["json"], key="single_week_upload")
    if uploaded is not None and st.button("Load saved week", use_container_width=True):
        try:
            monday, day_data, machines, products = load_payload(uploaded.getvalue())
            st.session_state.week_start = monday
            st.session_state.day_data = day_data
            st.session_state.machines = machines
            st.session_state.products = products
            st.success("Saved week loaded.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not load file: {exc}")

    payload = save_payload(st.session_state.week_start, st.session_state.day_data, st.session_state.machines, st.session_state.products)
    st.download_button(
        "Download weekly data (JSON)",
        data=payload,
        file_name=f"production_week_{st.session_state.week_start.isoformat()}.json",
        mime="application/json",
        use_container_width=True,
    )

    if st.button("Clear current week", use_container_width=True):
        reset_week(most_recent_monday())
        st.rerun()

with st.container(border=True):
    st.subheader("Week selection")
    selected_monday = st.date_input("Week starting Monday", value=st.session_state.week_start)
    if selected_monday.weekday() != 0:
        st.error("Please select a Monday.")
    elif selected_monday != st.session_state.week_start:
        if st.button("Change week"):
            reset_week(selected_monday)
            st.rerun()

    dates = week_dates(st.session_state.week_start)
    st.caption(f"Reporting period: {dates['Monday'].strftime('%d/%m/%Y')} - {dates['Saturday'].strftime('%d/%m/%Y')}")

manager_tab, entry_tab, review_tab, report_tab, history_tab = st.tabs(
    ["Machines & Products", "Enter Production", "Final Review", "Generate Weekly Report", "Monthly / Annual Reports"]
)

with manager_tab:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Machine names")
        new_machine = st.text_input("Add machine", key="new_machine")
        if st.button("Save machine", use_container_width=True):
            value = new_machine.strip()
            if not value:
                st.warning("Enter a machine name.")
            elif value.lower() in {x.lower() for x in st.session_state.machines}:
                st.warning("That machine is already saved.")
            else:
                st.session_state.machines.append(value)
                st.session_state.machines = sorted(st.session_state.machines, key=str.lower)
                st.rerun()
        if st.session_state.machines:
            st.dataframe(pd.DataFrame({"Machine": st.session_state.machines}), hide_index=True, use_container_width=True)

    with c2:
        st.subheader("Product names")
        new_product = st.text_input("Add product", key="new_product")
        if st.button("Save product", use_container_width=True):
            value = new_product.strip()
            if not value:
                st.warning("Enter a product name.")
            elif value.lower() in {x.lower() for x in st.session_state.products}:
                st.warning("That product is already saved.")
            else:
                st.session_state.products.append(value)
                st.session_state.products = sorted(st.session_state.products, key=str.lower)
                st.rerun()
        if st.session_state.products:
            st.dataframe(pd.DataFrame({"Product": st.session_state.products}), hide_index=True, use_container_width=True)

with entry_tab:
    st.subheader("Production data entry")
    day = st.selectbox("Day", DAYS)
    day_date = dates[day]
    st.caption(day_date.strftime("%A %d/%m/%Y"))

    machine_choices = ["<Enter new machine>"] + st.session_state.machines
    product_choices = ["<Enter new product>"] + st.session_state.products

    with st.form("production_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            machine_choice = st.selectbox("Machine Name", machine_choices)
            machine_custom = st.text_input("New Machine Name", disabled=machine_choice != "<Enter new machine>")
            product_choice = st.selectbox("Product Name", product_choices)
            product_custom = st.text_input("New Product Name", disabled=product_choice != "<Enter new product>")
            manufacturing_order = st.text_input("Manufacturing Order")
        with c2:
            operation_number = st.text_input("Operation Number")
            completed_quantity = st.number_input("Completed Quantity", min_value=0, step=1)
            rejected_quantity = st.number_input("Rejected Quantity", min_value=0, step=1)
            accepted = int(completed_quantity) - int(rejected_quantity)
            st.metric("Accepted Quantity", accepted)

        if st.form_submit_button("Save Data for This Machine", use_container_width=True):
            machine = machine_custom.strip() if machine_choice == "<Enter new machine>" else machine_choice
            product = product_custom.strip() if product_choice == "<Enter new product>" else product_choice
            if not machine or not product or not manufacturing_order.strip() or not operation_number.strip():
                st.error("Machine, product, manufacturing order and operation number are required.")
            elif rejected_quantity > completed_quantity:
                st.error("Rejected quantity cannot exceed completed quantity.")
            else:
                if machine not in st.session_state.machines:
                    st.session_state.machines.append(machine)
                    st.session_state.machines = sorted(st.session_state.machines, key=str.lower)
                if product not in st.session_state.products:
                    st.session_state.products.append(product)
                    st.session_state.products = sorted(st.session_state.products, key=str.lower)
                st.session_state.day_data[day]["date"] = day_date.isoformat()
                st.session_state.day_data[day]["machines"][machine] = {
                    "Product Name": product,
                    "Manufacturing Order": manufacturing_order.strip(),
                    "Operation Number": operation_number.strip(),
                    "Completed Quantity": int(completed_quantity),
                    "Rejected Quantity": int(rejected_quantity),
                    "Accepted Quantity": accepted,
                }
                st.success(f"Data saved for {machine} on {day}.")
                st.rerun()

    existing = st.session_state.day_data[day]["machines"]
    if existing:
        rows = []
        for machine, raw in existing.items():
            rows.append({"Machine": machine, **normalise_machine_data(raw)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

with review_tab:
    st.subheader("Final Check")
    all_rows = []
    for day in DAYS:
        machines = st.session_state.day_data[day]["machines"]
        if not machines:
            st.info(f"{day}: No production data entered / skipped")
            continue
        for machine, raw in machines.items():
            all_rows.append({"Day": day, "Date": st.session_state.day_data[day]["date"], "Machine": machine, **normalise_machine_data(raw)})

    if all_rows:
        st.dataframe(pd.DataFrame(all_rows), hide_index=True, use_container_width=True)
        st.markdown("### Edit an entry")
        labels = [f"{r['Day']} - {r['Machine']} - {r['Manufacturing Order']}" for r in all_rows]
        selected = st.selectbox("Select entry", range(len(labels)), format_func=lambda i: labels[i])
        row = all_rows[selected]
        with st.form("edit_entry"):
            ec1, ec2 = st.columns(2)
            with ec1:
                e_product = st.text_input("Product Name", value=row["Product Name"])
                e_mo = st.text_input("Manufacturing Order", value=row["Manufacturing Order"])
                e_op = st.text_input("Operation Number", value=row["Operation Number"])
            with ec2:
                e_completed = st.number_input("Completed Quantity", min_value=0, step=1, value=int(row["Completed Quantity"]))
                e_rejected = st.number_input("Rejected Quantity", min_value=0, step=1, value=int(row["Rejected Quantity"]))
                st.metric("Accepted Quantity", int(e_completed) - int(e_rejected))
            if st.form_submit_button("Update Entry", use_container_width=True):
                if e_rejected > e_completed:
                    st.error("Rejected quantity cannot exceed completed quantity.")
                else:
                    st.session_state.day_data[row["Day"]]["machines"][row["Machine"]] = {
                        "Product Name": e_product.strip(),
                        "Manufacturing Order": e_mo.strip(),
                        "Operation Number": e_op.strip(),
                        "Completed Quantity": int(e_completed),
                        "Rejected Quantity": int(e_rejected),
                        "Accepted Quantity": int(e_completed) - int(e_rejected),
                    }
                    st.success("Entry updated.")
                    st.rerun()

        if st.button("Remove selected entry"):
            del st.session_state.day_data[row["Day"]]["machines"][row["Machine"]]
            st.rerun()
    else:
        st.info("No production data has been entered yet.")

with report_tab:
    st.subheader("Weekly Summary")
    summary = weekly_summary(st.session_state.day_data)
    m1, m2, m3 = st.columns(3)
    m1.metric("Completed Total", f"{summary['Completed Total']:,}")
    m2.metric("Rejected Total", f"{summary['Rejected Total']:,}")
    m3.metric("Accepted Total", f"{summary['Accepted Total']:,}")

    if summary["Completed Total"] == 0:
        st.info("Enter production data before generating a report.")
    else:
        try:
            pdf_bytes = generate_pdf(st.session_state.week_start, st.session_state.day_data)
            end_date = dates["Saturday"]
            st.download_button(
                "Generate / Download Weekly Production Report PDF",
                data=pdf_bytes,
                file_name=f"Production_Report_{st.session_state.week_start.strftime('%d%m%Y')}_to_{end_date.strftime('%d%m%Y')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.success("Report is ready to download.")
        except Exception as exc:
            st.error(f"Could not generate the PDF: {exc}")

with history_tab:
    st.subheader("Build a Monthly or One-Year Report")
    st.write("Upload weekly JSON files previously downloaded from this app. They are combined without altering the original weekly files.")

    report_type = st.radio(
        "Report type",
        ["Monthly", "One Year / Overall"],
        horizontal=True,
        help="Monthly accepts up to 5 weekly files. One Year / Overall accepts up to 52 weekly files.",
    )
    max_files = 5 if report_type == "Monthly" else 52
    period_label = "Monthly" if report_type == "Monthly" else "Annual"

    uploaded_weeks = st.file_uploader(
        f"Upload weekly JSON files (maximum {max_files})",
        type=["json"],
        accept_multiple_files=True,
        key=f"aggregate_upload_{max_files}",
    )

    if uploaded_weeks:
        if len(uploaded_weeks) > max_files:
            st.error(f"Too many files selected. {report_type} reports accept a maximum of {max_files} weekly JSON files.")
        else:
            reports, errors = [], []
            for uploaded_week in uploaded_weeks:
                try:
                    reports.append(load_weekly_report(uploaded_week.getvalue(), uploaded_week.name))
                except Exception as exc:
                    errors.append(f"{uploaded_week.name}: {exc}")

            if errors:
                st.error("One or more files could not be loaded:\n\n" + "\n".join(f"- {item}" for item in errors))
            elif reports:
                try:
                    aggregate = aggregate_weekly_reports(reports)
                    st.success(
                        f"Loaded {aggregate['weeks_included']} unique weekly report(s), covering "
                        f"{aggregate['start_date'].strftime('%d/%m/%Y')} to {aggregate['end_date'].strftime('%d/%m/%Y')}."
                    )

                    a1, a2, a3, a4, a5 = st.columns(5)
                    a1.metric("Weeks Included", aggregate["weeks_included"])
                    a2.metric("Completed", f"{aggregate['Completed Total']:,}")
                    a3.metric("Rejected", f"{aggregate['Rejected Total']:,}")
                    a4.metric("Accepted", f"{aggregate['Accepted Total']:,}")
                    a5.metric("Rejection Rate", f"{aggregate['Rejection Rate']:.2f}%")

                    st.markdown("### Week-by-week summary")
                    st.dataframe(pd.DataFrame(aggregate["weekly_rows"]), hide_index=True, use_container_width=True)

                    if report_type == "One Year / Overall":
                        st.markdown("## Annual Management Review")
                        st.markdown("### Month-to-month comparison")
                        monthly_df = pd.DataFrame(aggregate["monthly_rows"])
                        st.dataframe(monthly_df.drop(columns=["Month Key"], errors="ignore"), hide_index=True, use_container_width=True)

                        if not monthly_df.empty:
                            chart_df = monthly_df.set_index("Month")[["Completed", "Accepted", "Rejected"]]
                            st.line_chart(chart_df, use_container_width=True)

                            best = monthly_df.loc[monthly_df["Accepted"].idxmax()]
                            lowest_reject = monthly_df.loc[monthly_df["Rejection Rate %"].idxmin()]
                            c1, c2 = st.columns(2)
                            c1.metric("Highest Accepted Month", best["Month"], f"{int(best['Accepted']):,} accepted")
                            c2.metric("Lowest Rejection Month", lowest_reject["Month"], f"{lowest_reject['Rejection Rate %']:.2f}%")

                        st.markdown("### Machine performance trends")
                        machine_trends = pd.DataFrame(aggregate["machine_trend_rows"])
                        if machine_trends.empty:
                            st.info("No machine trend data found.")
                        else:
                            machine_names = sorted(machine_trends["Machine"].unique(), key=str.lower)
                            selected_machines = st.multiselect("Machines to compare", machine_names, default=machine_names[: min(5, len(machine_names))])
                            filtered = machine_trends[machine_trends["Machine"].isin(selected_machines)]
                            if not filtered.empty:
                                pivot = filtered.pivot_table(index="Month", columns="Machine", values="Accepted", aggfunc="sum", fill_value=0)
                                st.line_chart(pivot, use_container_width=True)
                            st.dataframe(machine_trends.drop(columns=["Month Key"], errors="ignore"), hide_index=True, use_container_width=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("### Production by machine")
                        machine_df = pd.DataFrame(aggregate["machine_rows"])
                        st.dataframe(machine_df, hide_index=True, use_container_width=True) if not machine_df.empty else st.info("No machine data found.")
                    with c2:
                        st.markdown("### Production by product")
                        product_df = pd.DataFrame(aggregate["product_rows"])
                        st.dataframe(product_df, hide_index=True, use_container_width=True) if not product_df.empty else st.info("No product data found.")

                    pdf_bytes = generate_period_pdf(aggregate, period_label)
                    st.download_button(
                        f"Generate / Download {report_type} Production Report PDF",
                        data=pdf_bytes,
                        file_name=f"{period_label}_Production_Report_{aggregate['start_date'].strftime('%d%m%Y')}_to_{aggregate['end_date'].strftime('%d%m%Y')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                except Exception as exc:
                    st.error(f"Could not build the combined report: {exc}")
    else:
        st.info(f"Upload between 1 and {max_files} saved weekly JSON files to create this report.")

st.divider()
st.caption("Weekly data is kept in the current browser session. Download the JSON file to retain or transfer a week, then use those files later for monthly and annual reporting.")

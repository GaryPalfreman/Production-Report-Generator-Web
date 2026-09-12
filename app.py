from datetime import date, timedelta

import pandas as pd
import streamlit as st

from report_generator import (
    DAYS,
    blank_week,
    generate_pdf,
    load_payload,
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
st.caption("Enter production data by day and machine, review the week, then generate a downloadable PDF report.")

with st.sidebar:
    st.header("Saved data")
    uploaded = st.file_uploader("Load saved weekly JSON", type=["json"])
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

    payload = save_payload(
        st.session_state.week_start,
        st.session_state.day_data,
        st.session_state.machines,
        st.session_state.products,
    )
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

manager_tab, entry_tab, review_tab, report_tab = st.tabs(
    ["Machines & Products", "Enter Production", "Final Review", "Generate Report"]
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

        save = st.form_submit_button("Save Data for This Machine", use_container_width=True)
        if save:
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
            item = normalise_machine_data(raw)
            rows.append({"Machine": machine, **item})
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
            item = normalise_machine_data(raw)
            all_rows.append({"Day": day, "Date": st.session_state.day_data[day]["date"], "Machine": machine, **item})

    if all_rows:
        review_df = pd.DataFrame(all_rows)
        st.dataframe(review_df, hide_index=True, use_container_width=True)

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
            filename = f"Production_Report_{st.session_state.week_start.strftime('%d%m%Y')}_to_{end_date.strftime('%d%m%Y')}.pdf"
            st.download_button(
                "Generate / Download Weekly Production Report PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
            )
            st.success("Report is ready to download.")
        except Exception as exc:
            st.error(f"Could not generate the PDF: {exc}")

st.divider()
st.caption("Weekly data is kept in the current browser session. Download the JSON file if you want to retain or transfer the week between sessions/devices.")

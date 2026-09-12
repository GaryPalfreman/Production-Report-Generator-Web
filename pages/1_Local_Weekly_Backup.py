from calendar import month_name
from datetime import date, timedelta
from hashlib import sha256
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

from report_generator import (
    blank_week,
    generate_pdf,
    load_payload,
    save_payload,
    weekly_summary,
)

st.set_page_config(page_title="Local Weekly Backup", page_icon="💾", layout="wide")


def most_recent_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def build_backup_zip(monday, day_data, machines, products, pdf_bytes):
    end_date = monday + timedelta(days=5)
    json_text = save_payload(monday, day_data, machines, products)
    json_bytes = json_text.encode("utf-8")

    month_folder = f"{monday.month:02d} {month_name[monday.month]}"
    archive_root = (
        f"Production Reports/{monday.year}/{month_folder}/"
        f"Week {monday.isoformat()}"
    )

    json_name = f"production_week_{monday.isoformat()}.json"
    pdf_name = (
        f"Production_Report_{monday.strftime('%d%m%Y')}_to_"
        f"{end_date.strftime('%d%m%Y')}.pdf"
    )

    manifest = (
        "Production Report Local Backup\n"
        "================================\n\n"
        f"Reporting period: {monday.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}\n"
        f"Week start: {monday.isoformat()}\n\n"
        "Contents:\n"
        f"- {json_name} - editable weekly source data for future monthly/annual reports\n"
        f"- {pdf_name} - finished weekly production report\n"
        "- MANIFEST_SHA256.txt - file integrity checksums\n\n"
        "Privacy / storage:\n"
        "This package is generated for download. Keep the ZIP or extracted folder on your local computer or approved local storage.\n"
        "The application does not require a cloud database to retain this weekly archive.\n"
    )

    checksums = (
        f"{sha256(json_bytes).hexdigest()}  {json_name}\n"
        f"{sha256(pdf_bytes).hexdigest()}  {pdf_name}\n"
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(f"{archive_root}/{json_name}", json_bytes)
        archive.writestr(f"{archive_root}/{pdf_name}", pdf_bytes)
        archive.writestr(f"{archive_root}/ARCHIVE_INFO.txt", manifest)
        archive.writestr(f"{archive_root}/MANIFEST_SHA256.txt", checksums)
    return buffer.getvalue(), json_text, json_name, pdf_name


if "week_start" not in st.session_state:
    st.session_state.week_start = most_recent_monday()
if "day_data" not in st.session_state:
    st.session_state.day_data = blank_week(st.session_state.week_start)
if "machines" not in st.session_state:
    st.session_state.machines = []
if "products" not in st.session_state:
    st.session_state.products = []

st.title("Local Weekly Backup")
st.caption(
    "Download one ZIP containing the weekly JSON source data and finished PDF. "
    "The ZIP is structured so extracting it creates Year / Month / Week folders automatically."
)

source = st.radio(
    "Backup source",
    ["Current week in this browser session", "Load a saved weekly JSON file"],
    horizontal=True,
)

if source == "Current week in this browser session":
    monday = st.session_state.week_start
    day_data = st.session_state.day_data
    machines = st.session_state.machines
    products = st.session_state.products
else:
    uploaded = st.file_uploader("Choose a saved weekly JSON file", type=["json"], key="backup_json_upload")
    if uploaded is None:
        st.info("Upload a weekly JSON file to build its local backup package.")
        st.stop()
    try:
        monday, day_data, machines, products = load_payload(uploaded.getvalue())
    except Exception as exc:
        st.error(f"Could not load the weekly JSON file: {exc}")
        st.stop()

end_date = monday + timedelta(days=5)
summary = weekly_summary(day_data)

st.subheader("Week being archived")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Week Starting", monday.strftime("%d/%m/%Y"))
c2.metric("Completed", f"{summary['Completed Total']:,}")
c3.metric("Rejected", f"{summary['Rejected Total']:,}")
c4.metric("Accepted", f"{summary['Accepted Total']:,}")

st.code(
    f"Production Reports/{monday.year}/{monday.month:02d} {month_name[monday.month]}/Week {monday.isoformat()}/",
    language=None,
)

if summary["Completed Total"] == 0:
    st.warning("This week currently contains no completed production. Add or load production data before creating the backup package.")
else:
    try:
        pdf_bytes = generate_pdf(monday, day_data)
        zip_bytes, json_text, json_name, pdf_name = build_backup_zip(
            monday, day_data, machines, products, pdf_bytes
        )

        zip_name = (
            f"Production_Backup_{monday.isoformat()}_to_{end_date.isoformat()}.zip"
        )

        st.markdown("### Download")
        st.download_button(
            "Download Complete Weekly Backup Package (ZIP)",
            data=zip_bytes,
            file_name=zip_name,
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Download JSON only",
                data=json_text,
                file_name=json_name,
                mime="application/json",
                use_container_width=True,
            )
        with d2:
            st.download_button(
                "Download PDF only",
                data=pdf_bytes,
                file_name=pdf_name,
                mime="application/pdf",
                use_container_width=True,
            )

        st.success(
            "The ZIP contains the editable JSON, finished PDF, archive information, and SHA-256 integrity checksums."
        )
        st.info(
            "After downloading, store the ZIP locally or extract it. The internal folder structure will organise the week under its year and month."
        )
    except Exception as exc:
        st.error(f"Could not create the backup package: {exc}")

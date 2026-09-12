# Weekly Production Report Generator

Streamlit web conversion of the original Tkinter production report application.

## Features

- Select a reporting week starting on Monday
- Maintain reusable machine and product lists
- Enter production data Monday through Saturday
- Record manufacturing order and operation number
- Automatically calculate Accepted Quantity = Completed Quantity - Rejected Quantity
- Review, edit and remove entered production records
- View weekly completed, rejected and accepted totals
- Generate a downloadable landscape A4 weekly PDF report
- Weekly summary chart generated from real production data
- Daily machine production charts and daily detail tables
- Download/reload weekly JSON data for transfer between sessions or devices
- Build a Monthly Production Report from up to 5 saved weekly JSON files
- Build a One Year / Overall Production Report from up to 52 saved weekly JSON files
- Detect duplicate weeks before aggregation
- Combined completed, rejected, accepted and rejection-rate metrics
- Week-by-week production summary
- Production totals grouped by machine and by product
- Downloadable consolidated monthly/annual PDF report

## Deploy on Streamlit Community Cloud

- Repository: `GaryPalfreman/Production-Report-Generator-Web`
- Branch: `main`
- Main file path: `app.py`

## Higher-level reports

Each weekly JSON file downloaded from the app contains the source data required for aggregation. Open the `Monthly / Annual Reports` tab and upload the saved weekly JSON files. Monthly reports accept a maximum of 5 weekly files and One Year / Overall reports accept a maximum of 52. Duplicate week-start dates are rejected so the same week cannot be counted twice.

The consolidated PDF includes overall production totals, rejection rate, a weekly trend chart, a week-by-week table, production totals by machine and production totals by product.

## Data storage

The original desktop application wrote files into a local `Production_Work` directory. The web version keeps the current week in the Streamlit browser session and provides a JSON download/load workflow rather than relying on server-local files. Saved weekly JSON files act as the long-term source records for monthly and annual report generation.

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
- Annual month-to-month production comparison
- Annual monthly rejection-rate comparison
- Annual machine accepted-production trend analysis
- Select individual machines to compare in the annual dashboard
- Highlight the highest accepted-production month and lowest rejection-rate month
- Downloadable consolidated monthly/annual PDF report

## Deploy on Streamlit Community Cloud

- Repository: `GaryPalfreman/Production-Report-Generator-Web`
- Branch: `main`
- Main file path: `app.py`

## Higher-level reports

Each weekly JSON file downloaded from the app contains the source data required for aggregation. Open the `Monthly / Annual Reports` tab and upload the saved weekly JSON files. Monthly reports accept a maximum of 5 weekly files and One Year / Overall reports accept a maximum of 52. Duplicate week-start dates are rejected so the same week cannot be counted twice.

The consolidated report includes overall production totals, rejection rate, weekly trends, a week-by-week table, production totals by machine and product, and for annual reports a month-by-month management review plus machine performance trends. The annual PDF includes month-to-month comparison and machine accepted-production trend charts.

## Data storage

The original desktop application wrote files into a local `Production_Work` directory. The web version keeps the current week in the Streamlit browser session and provides a JSON download/load workflow rather than relying on server-local files. Saved weekly JSON files act as the long-term source records for monthly and annual report generation.

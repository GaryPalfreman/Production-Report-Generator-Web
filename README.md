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
- KPI target settings for accepted production and maximum rejection rate
- Green / Amber / Red production and quality status
- Period target, variance-to-target and target-attainment calculations
- Monthly KPI grading using each month's included weeks
- Management highlights including top-output machine, best-quality machine and quality-attention machine
- KPI management-review page included in consolidated PDF reports
- Downloadable consolidated monthly/annual PDF report

## Deploy on Streamlit Community Cloud

- Repository: `GaryPalfreman/Production-Report-Generator-Web`
- Branch: `main`
- Main file path: `app.py`
- Live app: `https://pr0duction-report-generator-web.streamlit.app`

## Higher-level reports

Each weekly JSON file downloaded from the app contains the source data required for aggregation. Open the `Monthly / Annual Reports` tab and upload the saved weekly JSON files. Monthly reports accept a maximum of 5 weekly files and One Year / Overall reports accept a maximum of 52. Duplicate week-start dates are rejected so the same week cannot be counted twice.

Before building the report, KPI settings can be entered for accepted production per week, maximum rejection rate and the Amber tolerance band. The app then calculates the period target automatically from the number of uploaded weeks and grades production and quality as Green, Amber or Red. Monthly KPI rows show accepted target, variance, target attainment, production status and quality status.

The consolidated report includes overall production totals, rejection rate, weekly trends, KPI status, management highlights, a week-by-week table, production totals by machine and product, and for annual reports a month-by-month management review plus machine performance trends. The PDF includes the KPI management review and relevant trend charts.

## Data storage

The original desktop application wrote files into a local `Production_Work` directory. The web version keeps the current week in the Streamlit browser session and provides a JSON download/load workflow rather than relying on server-local files. Saved weekly JSON files act as the long-term source records for monthly and annual report generation.

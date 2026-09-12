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
- Generate a downloadable landscape A4 PDF report
- Weekly summary chart generated from real production data
- Daily machine production charts and daily detail tables
- Download/reload weekly JSON data for transfer between sessions or devices

## Deploy on Streamlit Community Cloud

- Repository: `GaryPalfreman/Production-Report-Generator-Web`
- Branch: `main`
- Main file path: `app.py`

## Data storage

The original desktop application wrote files into a local `Production_Work` directory. The web version keeps the current week in the Streamlit browser session and provides a JSON download/load workflow rather than relying on server-local files.

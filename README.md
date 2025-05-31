🔍 Overview of the App

This project is a Streamlit web application designed to help users calculate and explore Marriott Vacation Club (MVC) point values across different room types, seasons, and resorts (specifically for years like 2025 and 2026).

The app is structured in two main Python files:
app.py — the Streamlit user interface and logic controller.
data.py — the reference data store, which contains point charts, season definitions, and holiday logic in a structured dictionary format.

📂 File: app.py — The Main App Interface

This is the file you run (streamlit run app.py). It does the following:

🔧 1. App Configuration

Sets the page title and layout.
Imports required libraries: streamlit, datetime, calendar, pandas, and from data the resort-specific data.

🧠 2. Core Functions

These functions power the logic of how point calculations work.

get_season(date, resort_data)
Determines whether a given date falls under: 
a holiday week or one of the defined seasons (low, high, etc.).
Looks up based on the ranges and holidays provided in data.py.

calculate_points(start_date, end_date, room_type, resort_data, discount)
Loops through each day between the two dates.
Calculates the total number of points based on:
room type
season
whether it’s a weekend
any discount (like 25% off for owner preview weeks)
Returns a daily breakdown + total points.

display_timeline(daily_data)
Generates a timeline bar chart showing how points are distributed day-by-day over the selected period.

prepare_download(daily_data)
Prepares a CSV download of the daily breakdown.

🖼️ 3. Streamlit UI Components

These sections create the user-facing interface.
Resort selector (st.selectbox)
Date pickers (st.date_input)
Room type dropdown, discount checkbox, calculate button

Outputs:
Point summary
Breakdown table
Timeline chart
Downloadable CSV

🔁 How to Modify app.py

Want to...	Go to this section

Add a new resort	data.py → Add to resorts dictionary
Change how points are calculated	calculate_points() in app.py

Modify season or holiday rules	get_season() and data.py definitions

Change UI layout	Streamlit layout area (bottom of app.py)
Add new features like multi-room	Modify the UI + calculate_points() logic

📂 File: data.py — The Point Chart and Season Definitions
This file contains all hardcoded reference values for resorts.

🏨 resorts dictionary
Each key is a resort (e.g., "Ko Olina", "Kauai Beach Club"), and the value is another dictionary with:
"2025", "2026", etc. — Years of operation.
Inside each year:
"seasons": Dictionary with season names and date ranges.
"holidays": List of holiday week start dates.
"points": Nested dict mapping room types → season → weekday/weekend → point values.

Example Structure:
python
Copy
Edit
resorts = {
    "Ko Olina": {
        "2025": {
            "seasons": {
                "High": [("2025-06-01", "2025-08-31")],
                "Low": [("2025-01-01", "2025-05-31")]
            },
            "holidays": ["2025-12-25", "2025-11-23"],
            "points": {
                "2BR OV": {
                    "High": {"weekday": 500, "weekend": 700},
                    "Low": {"weekday": 300, "weekend": 500},
                    "Holiday": {"weekday": 800, "weekend": 1000}
                }
            }
        }
    }
}

🔁 How to Modify data.py
Want to...	Do this...

Add a new resort	Copy existing structure, add new resort key and values
Add/adjust room types or point values	Update "points" dictionary under the right year and season

Add a new season or change dates	Edit the "seasons" dictionary under the desired resort/year
Change holiday weeks	Modify the "holidays" list with new date strings
Add more years like 2027	Duplicate a year block (e.g., "2025") and adjust the values

✅ Summary
This app is modular and highly extensible. Here's where to go:

🛠 Logic & Interface: app.py
Date handling, calculations, timeline chart, CSV download

📊 Reference Data: data.py
All point values, season ranges, holidays

If you're expanding or modifying, you’ll typically:
Update data.py with new resorts/seasons/values.
Tweak app.py if you need new UI features or logic changes.

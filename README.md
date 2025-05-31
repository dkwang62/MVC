Marriott Points Calculator – Code Overview
==========================================
This application is a Streamlit-based web tool for calculating and visualizing Marriott Vacation Club (MVC) point requirements across different resorts, room types, and seasons.
File Structure
--------------
1. app.py – The main Streamlit app and logic controller
2. data.json – JSON file containing reference data (replaces data.py)
You can see the app.py and data.json here
https://github.com/dkwang62/MVC
----------------------------------------------------------
app.py – User Interface and Point Calculation Logic
----------------------------------------------------------
This file handles user interaction and core functionality.
Main Components:
1. App Configuration:
- Sets Streamlit layout and page title
- Loads resort data from `data.json`
2. Core Functions:
- get_season(date, resort_data)
- Determines if a date is within a defined season or holiday week
- calculate_points(start_date, end_date, room_type, resort_data, discount)
- Loops over date range to compute total and per-day point values
- Applies different point rules based on weekday/weekend and season
- display_timeline(daily_data)
- Creates a bar chart timeline of points across selected dates
- prepare_download(daily_data)
- Exports the per-day breakdown to CSV
3. Streamlit UI Layout:
- Resort and room type dropdowns
- Date range selectors
- Discount checkbox
- Output: point total, breakdown table, chart, and CSV download
Modify app.py to:
- Change point logic: edit `calculate_points()`
- Customize season rules: edit `get_season()`
- Alter UI layout: modify Streamlit section near the bottom
- Adjust how data is read: change how `data.json` is loaded or parsed
----------------------------------------------------------
data.json – Reference Data and Metadata
----------------------------------------------------------
This file defines all resort-specific data for point calculation in a structured JSON format.
Main Sections:
1. resorts (object)
- Top-level keys: Resort names (e.g., "Ko Olina", "Kauai Beach Club")
- Sub-keys per year (e.g., "2025", "2026")
- seasons: object of season names to date ranges
- holidays: array of high-demand week start dates
- points: nested object
room_type → season → weekday/weekend → point value
2. room_type_legend (object)
- Maps short room codes to descriptive names
e.g., "2BR OV" → "2-Bedroom Ocean View"
3. view_codes (object)
- Maps abbreviated view codes from charts to full descriptions
e.g., "MA" → "Mountain View"
4. room_categories (optional)
- Groups room types by size/class (e.g., Studio, 1BR, 2BR)
Modify data.json to:
- Add new resorts or years: expand the `resorts` object
- Change room types or point values: update `points` entries
- Adjust season or holiday weeks: edit `seasons` and `holidays`
- Add new legends or clarify labels: update `room_type_legend` and `view_codes`
Interaction Summary
--------------------
| Task | Modify in... |
|----------------------------------------|--------------------------|
| Add a new resort | data.json → resorts |
| Adjust season/holiday dates | data.json → seasons |
| Add/change point values | data.json → points |
| Change dropdown room labels | data.json → room_type_legend |
| Update view abbreviations | data.json → view_codes |
| Tweak calculation rules | app.py → calculate_points() |
| Redesign UI layout | app.py (Streamlit UI) |
This structure ensures the app is modular, maintainable, and JSON-driven. For new resorts or years, just follow the format and extend `data.json`.
   - Top-level keys: Resort names (e.g., "Ko Olina", "Kauai Beach Club")
   - Sub-keys per year (e.g., "2025", "2026")
     - seasons: dict of season names to date ranges
     - holidays: list of high-demand week start dates
     - points: nested dict
         room_type → season → weekday/weekend → point value

2. room_type_legend (dict)
   - Maps short room codes to descriptive names
     e.g., "2BR OV" → "2-Bedroom Ocean View"

3. view_codes (dict)
   - Maps abbreviated view codes from charts to full descriptions
     e.g., "MA" → "Mountain View"

4. room_categories (optional)
   - Groups room types by size/class (e.g., Studio, 1BR, 2BR)

Modify data.py to:
   - Add new resorts or years: expand the `resorts` dictionary
   - Change room types or point values: update `points` blocks
   - Adjust season or holiday weeks: edit `seasons` and `holidays`
   - Add new legends or clarify labels: update `room_type_legend` and `view_codes`

Interaction Summary
--------------------

| Task                                   | Modify in...         |
|----------------------------------------|------------------------|
| Add a new resort                      | data.py → resorts      |
| Adjust season/holiday dates           | data.py → seasons      |
| Add/change point values               | data.py → points       |
| Change dropdown room labels           | data.py → room_type_legend |
| Update view abbreviations             | data.py → view_codes   |
| Tweak calculation rules               | app.py → calculate_points() |
| Redesign UI layout                    | app.py (Streamlit UI)  |

This structure ensures the app is easily maintainable and extensible. For new resorts or years, just follow the format and extend `data.py`.

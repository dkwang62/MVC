Logic for Handling Holiday Weeks in app.py
The app.py code manages date ranges that include holiday weeks by separating the processing of non-holiday and holiday periods. Here’s a breakdown of how it works:

Data Structure:
The Marriott_2025.json file contains data for the "Ko Olina Beach Club" resort, with daily entries for 2025.
Each date entry includes:
Day: The day of the week.
Room types (e.g., Studio Mountain, 2-BR OV) with points required.
HolidayWeek: A boolean indicating if the date is part of a holiday week.
HolidayWeekStart: A boolean marking the start of a holiday week (typically a Friday).
Non-Holiday Stay Calculation (calculate_non_holiday_stay):
This function iterates through each day of the stay (from checkin_date to checkin_date + num_nights).
For each date, it checks if HolidayWeek is False. If so, it includes the day in the breakdown.
It retrieves:
Points required for the selected room type.
Estimated rent (calculated as math.ceil(points * 0.81)).
If the date is a holiday week (HolidayWeek: true) or missing, it skips the day or marks it as "Date Not Found."
Outputs a table with daily details (Date, Day, Points Required, Estimated Rent) and totals for points and rent.
Holiday Week Summary (summarize_holiday_weeks):
This function identifies holiday weeks that overlap with the stay period.
It searches a window from 7 days before the check-in date to checkin_date + num_nights.
For each date, it checks if HolidayWeekStart is True.
If a holiday week starts within the search window and overlaps with the stay, it includes:
Holiday Week Start: The start date of the holiday week.
Holiday Week End (Checkout): The date 7 days later (end of the week).
Points on Start Day: Points for the room type on the start date (or fallback points from July 31, 2025, if unavailable).
Estimated Rent: Calculated as math.ceil(points * 0.81).
The function ensures holiday weeks are only included if they overlap with the user’s stay.
User Interface:
The Streamlit app allows users to select:
Resort (currently only "Ko Olina Beach Club").
Room type (dynamically populated from the JSON data).
Check-in date (constrained to 2025).
Number of nights (1 to 30).
When the "Calculate" button is clicked, it calls both functions and displays:
A table for non-holiday days with daily points and rent.
Total points and estimated rent for non-holiday days.
A table summarizing any overlapping holiday weeks.
Key Logic for Holiday Weeks:
Holiday weeks are treated as full-week bookings (7 nights), starting on dates marked HolidayWeekStart: true.
The app does not calculate daily points for holiday weeks in the non-holiday breakdown; instead, it summarizes them separately.
The search window ensures holiday weeks starting just before the check-in are considered, preventing missed overlaps.
Fallback points (from July 31, 2025) are used if points are unavailable for a holiday week’s start date.
Replicating the Logic
I can replicate this logic in another codebase, provided you share the new code and any relevant details (e.g., data structure, desired output format). Here’s what I’ll need to ensure accurate replication:

The new code you want to adapt.
Details about the data source (e.g., JSON structure, if different from Marriott_2025.json).
Any specific modifications or differences in how holiday weeks should be handled.
The framework or library (e.g., Streamlit, Flask, or plain Python) you’re using.
The core logic—iterating through dates, checking for holiday week flags, separating non-holiday and holiday calculations, and handling overlaps—can be adapted to different contexts. I’ll ensure the new code:

Identifies holiday weeks using a similar flag (e.g., HolidayWeekStart).
Calculates non-holiday days separately, skipping holiday periods.
Summarizes holiday weeks with start/end dates and relevant metrics.
Uses fallback values if needed.
Integrates with your UI or output format.

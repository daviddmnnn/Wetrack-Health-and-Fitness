# WeTrack 4.6

Individual Health and Fitness Data Tracking System prototype.

## Stack
- Python / Flask
- HTML / CSS / JavaScript
- MySQL
- Chart.js (CDN)

## Features
- Login and registration with server-side validation and required Terms & Conditions acceptance
- Dashboard, profile, fitness, diet, and sleep tracking
- Health prediction, personal goals, exercise plans, reports, and About Us
- Security settings for username/password changes and account deletion
- Dark, Green & White, and Light themes

## Database setup
1. Start MySQL and update `config.py` with your database credentials and secret key.
2. For a new installation, run `database/schema.sql`.
3. Existing WeTrack 3.x databases need no schema migration for these refinements. The profile picture column is added automatically when the profile page is opened if it is missing.

## Record dates
Fitness, diet and sleep entries can only be saved for the current day. The app checks this on the server as well as in the date controls.
## Demo account
After installing dependencies and initializing MySQL, run `python seed_demo.py` from this project folder. This creates or completes the 40-day sample account.

Credentials: `andrei` / `1234567890`. The seeder fills missing dates without duplicating existing daily records and stops if that username belongs to a different email address.

## Run
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000`.

Prediction charts remain visible while the weight prediction is locked. The prediction unlocks 30 days after account creation and uses the most recent 30 days of diet calories and logged activity burn. The net calorie balance is converted to an estimated weight change using 7,700 kcal per kg. Predictions are educational estimates, not medical advice.

## Prototype note
The Report page stores Report/Feedback messages in MySQL. There is no administrator/developer access level or reply workflow in this version.







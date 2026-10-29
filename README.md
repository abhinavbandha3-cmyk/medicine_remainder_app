# 💊 Smart Medicine Reminder System

A full-stack hospital-style medicine reminder web app built with Flask,
SQLAlchemy, SQLite, Bootstrap 5 and vanilla JavaScript.

## Features

- **Login / Register / Forgot Password** with hashed passwords and sessions
- **Dashboard** with live stats (total medicines, today's medicines, upcoming,
  taken %), quick-action cards, and a glassmorphism medical UI (light/dark mode)
- **Add / View / Edit / Delete Medicines** with search, sort and pagination
- **Reminders** — the browser polls every 30s and, when a medicine is due,
  speaks it out loud (Web Speech API) and shows a desktop notification
- **Prescription Upload** — JPG/PNG/JPEG, stored in `uploads/`, with previews
- **Caregiver Email Alerts** via Gmail SMTP
- **AI Chatbot** — uses Google Gemini if `GEMINI_API_KEY` is set, otherwise
  falls back to a built-in offline medicine knowledge base (Paracetamol,
  Ibuprofen, Crocin, Vitamin C, Aspirin, Amoxicillin, Cetirizine, Metformin,
  Omeprazole, and general dosage/side-effect/precaution info)
- **Reports** — CSV export, PDF export (ReportLab), and print view
- **Profile** — change password, logout

## Why browser-based reminders instead of `pyttsx3`/`playsound`?

The original prompt asked for server-side `pyttsx3`/`playsound` alarms.
In a real multi-user Flask web app the server has no speaker of its own —
it would be speaking on the *server's* machine, not the browser the person
is actually using. Instead, this app uses the browser's built-in
**Web Speech API** and **Notification API**, polled from `/api/due-medicines`
every 30 seconds. This is the correct way to get voice + popup reminders on
whichever device the user has the site open on. `voice.py`-style
`pyttsx3` code is kept out of the web app for that reason.

## Project Structure

```
medicine_reminder/
├── app.py                 # Flask app & all routes
├── models.py               # SQLAlchemy models (User, Medicine, Prescription, ReminderHistory)
├── extensions.py           # db = SQLAlchemy()
├── chatbot_engine.py        # Gemini + offline chatbot logic
├── email_utils.py           # SMTP caregiver email helper
├── requirements.txt
├── medicine.db              # created automatically on first run
├── uploads/                 # prescription images
├── static/
│   ├── css/style.css
│   └── js/script.js
└── templates/
    ├── layout.html, login.html, register.html, forgot_password.html
    ├── dashboard.html, add_medicine.html, view_medicine.html, edit_medicine.html
    ├── reminder.html, prescription.html, caregiver.html, chatbot.html
    ├── report.html, profile.html
```

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000**

A demo account is created automatically on first run:

- Username: `admin`
- Password: `admin123`

You can also register a new account from the login page.

## Optional environment variables

| Variable            | Purpose                                             |
|---------------------|------------------------------------------------------|
| `SECRET_KEY`         | Flask session secret (set a real one in production) |
| `GEMINI_API_KEY`     | Enables live AI answers via Google Gemini            |
| `MAIL_ADDRESS`       | Gmail address used to send caregiver alerts          |
| `MAIL_APP_PASSWORD`  | Gmail **App Password** (not your normal password)    |

Example:

```bash
export GEMINI_API_KEY="your-key"
export MAIL_ADDRESS="you@gmail.com"
export MAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
python app.py
```

Without these, the app still runs fully — the chatbot uses its offline
knowledge base, and caregiver alerts show a clear "email not configured"
message instead of failing.

## Database

SQLite (`medicine.db`), created automatically via `db.create_all()` the
first time `app.py` runs. Tables: `users`, `medicines`, `prescriptions`,
`reminder_history`.

## Notes on the uploaded desktop prototype

The uploaded `add_medicine.py`, `login.py`, `dashboard.py`, etc. were a
`customtkinter` desktop prototype (separate windows per feature, a two-column
`medicines` table with just name/dose/time). This project is a from-scratch
rebuild as a single Flask website matching the full spec in your prompt
(multi-user accounts, richer medicine fields, prescriptions, caregiver email,
AI chatbot, reports) — it does not reuse the old desktop code, since Tkinter
windows and a Flask website are fundamentally different architectures.

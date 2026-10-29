import os
import csv
import io
from datetime import datetime, date, timedelta

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file, Response
)
from werkzeug.utils import secure_filename

from extensions import db
from models import User, Medicine, Prescription, ReminderHistory
from chatbot_engine import get_chatbot_reply
from email_utils import send_caregiver_email

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "medicine.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.permanent_session_lifetime = timedelta(days=7)

db.init_app(app)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def login_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


FREQ_TIMES = {
    "Morning": "08:00",
    "Afternoon": "14:00",
    "Night": "21:00",
}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session.permanent = bool(remember)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("That username is already taken.", "danger")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        flash("If an account with that username exists, reset instructions "
              "would be emailed. (Demo mode - no email sent.)", "info")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    meds = Medicine.query.filter_by(user_id=user.id).all()

    today_str = date.today().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    total_medicines = len(meds)
    today_meds = [m for m in meds if m.status == "Active"]
    upcoming_meds = sorted(
        [m for m in today_meds if m.time >= now_time],
        key=lambda m: m.time
    )[:5]

    taken_count = ReminderHistory.query.join(Medicine).filter(
        Medicine.user_id == user.id, ReminderHistory.status == "Taken"
    ).count()
    total_history = ReminderHistory.query.join(Medicine).filter(
        Medicine.user_id == user.id
    ).count()
    taken_pct = round((taken_count / total_history) * 100) if total_history else 0

    return render_template(
        "dashboard.html",
        total_medicines=total_medicines,
        today_count=len(today_meds),
        upcoming_meds=upcoming_meds,
        taken_pct=taken_pct,
        now=datetime.now(),
    )


@app.route("/api/dashboard_stats")
@login_required
def api_dashboard_stats():
    user = current_user()
    meds = Medicine.query.filter_by(user_id=user.id).all()
    now_time = datetime.now().strftime("%H:%M")

    active = [m for m in meds if m.status == "Active"]
    upcoming = sorted([m for m in active if m.time >= now_time], key=lambda m: m.time)[:5]

    return jsonify({
        "total_medicines": len(meds),
        "today_count": len(active),
        "upcoming": [m.to_dict() for m in upcoming],
        "server_time": datetime.now().strftime("%H:%M:%S"),
    })


# ---------------------------------------------------------------------------
# Medicines: Add / View / Edit / Delete
# ---------------------------------------------------------------------------
@app.route("/add-medicine", methods=["GET", "POST"])
@login_required
def add_medicine():
    if request.method == "POST":
        name = request.form.get("medicine_name", "").strip()
        dosage = request.form.get("dosage", "").strip()
        time_val = request.form.get("time", "").strip()
        frequencies = request.form.getlist("frequency")
        start_date = request.form.get("start_date") or None
        end_date = request.form.get("end_date") or None
        notes = request.form.get("notes", "").strip()

        if not name or not time_val:
            flash("Medicine name and time are required.", "danger")
            return redirect(url_for("add_medicine"))

        med = Medicine(
            user_id=current_user().id,
            medicine_name=name,
            dosage=dosage,
            time=time_val,
            frequency=", ".join(frequencies) if frequencies else None,
            start_date=datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today(),
            end_date=datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None,
            notes=notes,
            status="Active",
        )
        db.session.add(med)
        db.session.commit()
        flash("Medicine saved successfully!", "success")
        return redirect(url_for("view_medicines"))

    return render_template("add_medicine.html", today=date.today().isoformat())


@app.route("/view-medicines")
@login_required
def view_medicines():
    meds = Medicine.query.filter_by(user_id=current_user().id).order_by(Medicine.time).all()
    return render_template("view_medicine.html", medicines=meds)


@app.route("/edit-medicine/<int:med_id>", methods=["GET", "POST"])
@login_required
def edit_medicine(med_id):
    med = Medicine.query.filter_by(id=med_id, user_id=current_user().id).first_or_404()

    if request.method == "POST":
        med.medicine_name = request.form.get("medicine_name", "").strip()
        med.dosage = request.form.get("dosage", "").strip()
        med.time = request.form.get("time", "").strip()
        frequencies = request.form.getlist("frequency")
        med.frequency = ", ".join(frequencies) if frequencies else None
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        med.start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else med.start_date
        med.end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        med.notes = request.form.get("notes", "").strip()
        med.status = request.form.get("status", med.status)

        db.session.commit()
        flash("Medicine updated successfully!", "success")
        return redirect(url_for("view_medicines"))

    return render_template("edit_medicine.html", med=med)


@app.route("/delete-medicine/<int:med_id>", methods=["POST"])
@login_required
def delete_medicine(med_id):
    med = Medicine.query.filter_by(id=med_id, user_id=current_user().id).first_or_404()
    db.session.delete(med)
    db.session.commit()
    flash("Medicine deleted.", "success")
    return redirect(url_for("view_medicines"))


@app.route("/api/medicine/<int:med_id>/log", methods=["POST"])
@login_required
def log_reminder(med_id):
    med = Medicine.query.filter_by(id=med_id, user_id=current_user().id).first_or_404()
    status = request.json.get("status", "Taken") if request.is_json else "Taken"
    entry = ReminderHistory(medicine_id=med.id, scheduled_time=med.time, status=status)
    db.session.add(entry)
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Reminders (browser-side voice + notification, backed by a JSON API)
# ---------------------------------------------------------------------------
@app.route("/reminder")
@login_required
def reminder_page():
    meds = Medicine.query.filter_by(user_id=current_user().id, status="Active").order_by(Medicine.time).all()
    return render_template("reminder.html", medicines=meds)


@app.route("/api/due-medicines")
@login_required
def api_due_medicines():
    """Polled by the browser every ~30s to check if any medicine is due now."""
    now_time = datetime.now().strftime("%H:%M")
    meds = Medicine.query.filter_by(
        user_id=current_user().id, status="Active", time=now_time
    ).all()
    return jsonify({"due": [m.to_dict() for m in meds]})


# ---------------------------------------------------------------------------
# Prescription upload
# ---------------------------------------------------------------------------
@app.route("/prescription", methods=["GET", "POST"])
@login_required
def prescription():
    user = current_user()

    if request.method == "POST":
        file = request.files.get("prescription_file")
        if not file or file.filename == "":
            flash("Please choose an image to upload.", "danger")
        elif not allowed_file(file.filename):
            flash("Only JPG, JPEG and PNG files are allowed.", "danger")
        else:
            original = secure_filename(file.filename)
            ext = original.rsplit(".", 1)[1].lower()
            stored_name = f"user{user.id}_{int(datetime.utcnow().timestamp())}.{ext}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], stored_name))

            record = Prescription(user_id=user.id, filename=stored_name, original_name=original)
            db.session.add(record)
            db.session.commit()
            flash("Prescription uploaded successfully!", "success")
        return redirect(url_for("prescription"))

    files = Prescription.query.filter_by(user_id=user.id).order_by(Prescription.uploaded_at.desc()).all()
    return render_template("prescription.html", files=files)


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_file(os.path.join(app.config["UPLOAD_FOLDER"], filename))


# ---------------------------------------------------------------------------
# Caregiver alerts
# ---------------------------------------------------------------------------
@app.route("/caregiver", methods=["GET", "POST"])
@login_required
def caregiver():
    user = current_user()

    if request.method == "POST":
        email = request.form.get("caregiver_email", "").strip()
        user.caregiver_email = email
        db.session.commit()

        ok, message = send_caregiver_email(email)
        flash(message, "success" if ok else "warning")
        return redirect(url_for("caregiver"))

    return render_template("caregiver.html", caregiver_email=user.caregiver_email)


# ---------------------------------------------------------------------------
# AI Chatbot
# ---------------------------------------------------------------------------
@app.route("/chatbot")
@login_required
def chatbot():
    return render_template("chatbot.html")


@app.route("/api/chatbot", methods=["POST"])
@login_required
def api_chatbot():
    message = (request.json or {}).get("message", "")
    reply = get_chatbot_reply(message)
    return jsonify({"reply": reply})


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
@app.route("/report")
@login_required
def report():
    meds = Medicine.query.filter_by(user_id=current_user().id).order_by(Medicine.time).all()
    return render_template("report.html", medicines=meds, generated=datetime.now())


@app.route("/report/csv")
@login_required
def report_csv():
    meds = Medicine.query.filter_by(user_id=current_user().id).order_by(Medicine.time).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Medicine", "Dosage", "Time", "Frequency", "Start Date", "End Date", "Status", "Notes"])
    for m in meds:
        writer.writerow([m.id, m.medicine_name, m.dosage, m.time, m.frequency,
                          m.start_date, m.end_date or "", m.status, m.notes or ""])

    resp = Response(output.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=medicine_report.csv"
    return resp


@app.route("/report/pdf")
@login_required
def report_pdf():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    meds = Medicine.query.filter_by(user_id=current_user().id).order_by(Medicine.time).all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Smart Medicine Reminder - Report", styles["Title"]), Spacer(1, 0.5 * cm)]

    data = [["Medicine", "Dosage", "Time", "Frequency", "Status"]]
    for m in meds:
        data.append([m.medicine_name, m.dosage or "-", m.time, m.frequency or "-", m.status])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EAF4FF")]),
    ]))
    elements.append(table)
    doc.build(elements)
    buf.seek(0)

    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="medicine_report.pdf")


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()

    if request.method == "POST":
        current_pwd = request.form.get("current_password", "")
        new_pwd = request.form.get("new_password", "")
        confirm_pwd = request.form.get("confirm_password", "")

        if not user.check_password(current_pwd):
            flash("Current password is incorrect.", "danger")
        elif len(new_pwd) < 4:
            flash("New password must be at least 4 characters.", "danger")
        elif new_pwd != confirm_pwd:
            flash("New passwords do not match.", "danger")
        else:
            user.set_password(new_pwd)
            db.session.commit()
            flash("Password updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def create_default_user():
    if not User.query.filter_by(username="admin").first():
        demo = User(username="admin")
        demo.set_password("admin123")
        db.session.add(demo)
        db.session.commit()


with app.app_context():
    db.create_all()
    create_default_user()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)

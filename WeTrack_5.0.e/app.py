from datetime import date, timedelta, datetime
from functools import wraps
import os
import uuid

import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.config["UPLOAD_FOLDER"] = os.path.join(
    app.static_folder, "uploads", "profile_pictures"
)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )

def db():
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME
    )


def query(sql, params=(), fetch=True, many=False):
    conn = db()
    cur = conn.cursor(dictionary=True)
    try:
        if many:
            cur.executemany(sql, params)
        else:
            cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def ensure_plan_activity_columns():
    """Ensure existing databases have the columns used by exercise-plan records.

    Older WeTrack databases may have an activities table created before the
    exercise-plan feature was added. The exercise-plan completion route uses
    these columns to distinguish plan-generated records from normal activities.
    """
    rows = query("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'activities'
          AND COLUMN_NAME IN ('isPlanRecord', 'planProgressID')
    """)
    existing = {row["COLUMN_NAME"] for row in rows}

    if "isPlanRecord" not in existing:
        query(
            "ALTER TABLE activities ADD COLUMN isPlanRecord BOOLEAN DEFAULT FALSE",
            fetch=False
        )

    if "planProgressID" not in existing:
        query(
            "ALTER TABLE activities ADD COLUMN planProgressID INT NULL",
            fetch=False
        )


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def current_user():
    if "user_id" not in session:
        return None
    rows = query("""
        SELECT u.*, i.heightCm, i.weightKg, i.bloodType
        FROM users u
        LEFT JOIN user_info i ON u.userID=i.userID
        WHERE u.userID=%s
    """, (session["user_id"],))
    return rows[0] if rows else None


def bmi(height_cm, weight_kg):
    if not height_cm or not weight_kg or float(height_cm) <= 0:
        return None
    h = float(height_cm) / 100
    return round(float(weight_kg) / (h * h), 1)


def bmi_status(value):
    if value is None:
        return "No data"
    if value < 18.5:
        return "Underweight"
    if value < 25:
        return "Normal"
    return "Overweight"


def account_id(user_id):
    return f"202600{int(user_id):04d}"


def date_range(days):
    return date.today() - timedelta(days=days - 1)


def json_date_rows(rows, *date_fields):
    """Convert MySQL date/datetime values to stable ISO strings for JavaScript.

    Chart.js compares dashboard dates as YYYY-MM-DD keys. MySQL connector
    returns DATE/DATETIME values as Python objects, which Flask may serialize
    differently. Normalizing them here keeps chart data matched to the
    dashboard's date labels and makes historical records visible correctly.
    """
    normalized = []
    for row in rows:
        item = dict(row)
        for field in date_fields:
            value = item.get(field)
            if hasattr(value, "isoformat"):
                item[field] = value.isoformat()
        normalized.append(item)
    return normalized


def sleep_status(hours):
    if hours is None:
        return "No data"
    hours = float(hours)
    if hours < 7:
        return "Insufficient"
    if hours > 9:
        return "Excessive"
    return "Adequate"


def food_suggestions(groups):
    values = {x["foodGroup"]: float(x["calories"] or 0) for x in groups}
    suggestions = []
    if values.get("Protein", 0) == 0:
        suggestions.append("No protein is present in the selected records. Consider logging protein foods when eaten.")
    if values.get("Carbs", 0) == 0:
        suggestions.append("No carbohydrate foods are present in the selected records.")
    if values.get("Veggies", 0) == 0:
        suggestions.append("No vegetable calories are present in the selected records; consider logging vegetables when eaten.")
    if values.get("Sweets", 0) > max(values.get("Veggies", 0), 1):
        suggestions.append("Logged sweets are higher than logged vegetables. Review the balance of your food groups.")
    if not suggestions:
        suggestions.append("Your logged food groups currently contain a mix of categories. Continue recording meals for a clearer weekly pattern.")
    return suggestions


@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "today": date.today().isoformat()}


@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form

        # Read and clean the values before validating them.
        firstname = data.get("firstname", "").strip()
        lastname = data.get("lastname", "").strip()
        birthdate = data.get("birthdate", "").strip()
        email = data.get("email", "").strip()
        contact_no = data.get("contactNo", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if data.get("termsAccepted") != "yes":
            flash("Please review and accept the Terms & Conditions.", "error")
            return render_template("register.html")

        # WeTrack 3.1 registration validation.
        # Names must not contain numbers and must not be empty.
        if not firstname or not lastname:
            flash("First name and last name are required.", "error")
            return render_template("register.html")

        if any(char.isdigit() for char in firstname + lastname):
            flash("First name and last name must not contain numbers.", "error")
            return render_template("register.html")

        # Birthdate is required and the birth year must not be greater than 2008.
        if not birthdate:
            flash("Birthdate is required.", "error")
            return render_template("register.html")

        try:
            parsed_birthdate = datetime.strptime(birthdate, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter a valid birthdate.", "error")
            return render_template("register.html")

        if parsed_birthdate.year > 2008:
            flash("Birthdate must have a birth year of 2008 or earlier.", "error")
            return render_template("register.html")

        # Mobile number must be exactly 11 digits and start with 09.
        if not contact_no:
            flash("Mobile number is required.", "error")
            return render_template("register.html")

        if not contact_no.isdigit() or len(contact_no) != 11 or not contact_no.startswith("09"):
            flash("Mobile number must contain exactly 11 digits and start with 09.", "error")
            return render_template("register.html")

        # Email must not be empty and must contain @ according to WeTrack 3.1.
        if not email:
            flash("Email is required.", "error")
            return render_template("register.html")

        if "@" not in email:
            flash("Email must contain @.", "error")
            return render_template("register.html")

        if not username:
            flash("Username is required.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("register.html")

        try:
            uid = query("""
                INSERT INTO users
                (lastname, firstname, birthdate, gender, email, contactNo, username, passwordHash)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                lastname, firstname, birthdate,
                data.get("gender", "Prefer not to say"), email,
                contact_no, username, generate_password_hash(password)
            ), fetch=False)
            query("UPDATE users SET accountID=%s WHERE userID=%s", (account_id(uid), uid), fetch=False)
            query("INSERT INTO user_info (userID) VALUES (%s)", (uid,), fetch=False)
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
        except mysql.connector.Error as e:
            flash("Registration failed. Username or email may already exist.", "error")
            print(e)
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        rows = query("SELECT * FROM users WHERE username=%s", (request.form["username"],))
        if rows and check_password_hash(rows[0]["passwordHash"], request.form["password"]):
            session["user_id"] = rows[0]["userID"]
            flash("Welcome back to WeTrack.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/security", methods=["GET", "POST"])
@login_required
def security_settings():
    uid = session["user_id"]
    user = query("SELECT * FROM users WHERE userID=%s", (uid,))[0]
    if request.method == "POST":
        action = request.form.get("action")
        if action not in {"username", "password", "delete"}:
            flash("Choose a valid account security action.", "error")
            return redirect(url_for("profile"))
        if not check_password_hash(user["passwordHash"], request.form.get("currentPassword", "")):
            flash("Current password is incorrect.", "error")
            return redirect(url_for("profile"))
        if action == "username":
            username = request.form.get("username", "").strip()
            if not username:
                flash("Username is required.", "error")
            else:
                try:
                    query("UPDATE users SET username=%s WHERE userID=%s", (username, uid), fetch=False)
                    flash("Username updated.", "success")
                except mysql.connector.Error:
                    flash("That username is already in use.", "error")
        elif action == "password":
            new_password = request.form.get("newPassword", "")
            if len(new_password) < 6:
                flash("New password must contain at least 6 characters.", "error")
            elif new_password != request.form.get("confirmPassword", ""):
                flash("The new passwords do not match.", "error")
            else:
                query("UPDATE users SET passwordHash=%s WHERE userID=%s",
                      (generate_password_hash(new_password), uid), fetch=False)
                flash("Password updated.", "success")
        elif action == "delete":
            query("DELETE FROM users WHERE userID=%s", (uid,), fetch=False)
            session.clear()
            return render_template("account_deleted.html")
        return redirect(url_for("profile"))
    return render_template("security.html", user=user)


@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    week_start = date_range(7)
    fourteen_start = date_range(14)

    activities = query("""
        SELECT activityDate, SUM(durationMin) totalMinutes, SUM(caloriesBurned) calories
        FROM activities
        WHERE userID=%s AND activityDate >= %s
        GROUP BY activityDate ORDER BY activityDate
    """, (uid, week_start))

    progress = query("""
        SELECT activityDate, SUM(durationMin) totalMinutes
        FROM activities
        WHERE userID=%s AND activityDate >= %s
        GROUP BY activityDate ORDER BY activityDate
    """, (uid, fourteen_start))

    sleep = query("""
        SELECT sleepDate, durationHours
        FROM sleep_logs
        WHERE userID=%s AND sleepDate >= %s
        ORDER BY sleepDate
    """, (uid, fourteen_start))

    diet = query("""
        SELECT f.foodGroup, SUM(d.calories) calories
        FROM diet_logs d JOIN foods f ON d.foodID=f.foodID
        WHERE d.userID=%s AND d.logDate >= %s
        GROUP BY f.foodGroup ORDER BY calories DESC
    """, (uid, week_start))

    # Normalize dates before sending chart data to JavaScript. This prevents
    # MySQL/Python date objects from becoming browser date strings that do not
    # match the dashboard's YYYY-MM-DD chart keys.
    activities = json_date_rows(activities, "activityDate")
    progress = json_date_rows(progress, "activityDate")
    sleep = json_date_rows(sleep, "sleepDate")

    recent = query("""
        SELECT actType AS label, CONCAT(durationMin,' min') AS detail,
               activityDate AS eventDate, 'activity' AS recordType
        FROM activities WHERE userID=%s
        UNION ALL
        SELECT CONCAT('Meal: ', f.foodName), CONCAT(d.calories,' kcal'),
               d.logDate, 'diet'
        FROM diet_logs d JOIN foods f ON d.foodID=f.foodID WHERE d.userID=%s
        UNION ALL
        SELECT 'Sleep', CONCAT(s.durationHours,' hrs'), s.sleepDate, 'sleep'
        FROM sleep_logs s WHERE s.userID=%s
        ORDER BY eventDate DESC LIMIT 7
    """, (uid, uid, uid))

    u = current_user()
    latest_sleep = float(sleep[-1]["durationHours"]) if sleep else None
    activity_minutes_7 = sum(float(x["totalMinutes"] or 0) for x in activities)
    activity_calories_7 = sum(float(x["calories"] or 0) for x in activities)
    activity_records_7 = len(activities)
    return render_template(
        "dashboard.html", user=u, activities=activities, progress=progress,
        sleep=sleep, diet=diet, recent=recent,
        bmi=bmi(u.get("heightCm"), u.get("weightKg")),
        bmi_status=bmi_status(bmi(u.get("heightCm"), u.get("weightKg"))),
        latest_sleep=latest_sleep,
        latest_sleep_status=sleep_status(latest_sleep),
        activity_minutes_7=round(activity_minutes_7),
        activity_calories_7=activity_calories_7,
        activity_records_7=activity_records_7
    )


def ensure_profile_picture_column():
    """Add profilePicture to older databases without disturbing existing data."""
    columns = query("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'users'
          AND COLUMN_NAME = 'profilePicture'
    """)
    if not columns:
        query(
            "ALTER TABLE users ADD COLUMN profilePicture VARCHAR(255) NULL",
            fetch=False
        )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    # Older schema.sql versions did not include this column. Migrate in place
    # so uploads also work when the project is moved to a fresh laptop/database.
    ensure_profile_picture_column()
    uid = session["user_id"]

    if request.method == "POST":

        # Profile picture upload
        profile_picture = request.files.get("profilePicture")

        if profile_picture and profile_picture.filename:
            if not allowed_image(profile_picture.filename):
                flash(
                    "Invalid image format. Please upload PNG, JPG, JPEG, or WEBP.",
                    "error"
                )
                return redirect(url_for("profile"))

            extension = profile_picture.filename.rsplit(".", 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{extension}"

            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

            profile_picture.save(
                os.path.join(app.config["UPLOAD_FOLDER"], filename)
            )

            query("""
                UPDATE users
                SET profilePicture=%s
                WHERE userID=%s
            """, (filename, uid), fetch=False)

        # WeTrack 3.2: First name, last name, birthdate, and gender
        # are account details and must not be editable from this page.
        # Only email/contact information and health measurements are updated here.

        query("""
            UPDATE users SET email=%s, contactNo=%s WHERE userID=%s
        """, (
            request.form["email"],
            request.form.get("contactNo"),
            uid
        ), fetch=False)

        query("""
            INSERT INTO user_info (userID,heightCm,weightKg,bloodType)
            VALUES (%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
            heightCm=VALUES(heightCm),
            weightKg=VALUES(weightKg),
            bloodType=VALUES(bloodType)
        """, (
            uid,
            request.form.get("heightCm") or None,
            request.form.get("weightKg") or None,
            request.form.get("bloodType")
        ), fetch=False)

        flash("Profile updated.", "success")
        return redirect(url_for("profile"))

    u = current_user()
    b = bmi(u.get("heightCm"), u.get("weightKg"))

    return render_template(
        "profile.html",
        user=u,
        bmi=b,
        bmi_status=bmi_status(b)
    )

@app.route("/activities", methods=["GET", "POST"])
@login_required
def activities_page():
    uid = session["user_id"]
    if request.method == "POST":
        if request.form.get("activityDate") != date.today().isoformat():
            flash("You can only log fitness records for today.", "error")
            return redirect(url_for("activities_page"))
        try:
            duration = int(request.form["durationMin"])
            if duration <= 0:
                raise ValueError
            intensity = request.form.get("intensity", "Moderate")
            met = {"Light": 3.0, "Moderate": 5.0, "Vigorous": 8.0}.get(intensity, 5.0)
            u = current_user()
            kcal = round(met * float(u.get("weightKg") or 60) * (duration / 60), 1)
            query("""
                INSERT INTO activities
                (userID,actType,durationMin,intensity,caloriesBurned,steps,activityDate,notes,isPlanRecord)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,FALSE)
            """, (
                uid, request.form["actType"], duration, intensity, kcal,
                int(request.form.get("steps") or 0), request.form["activityDate"], request.form.get("notes")
            ), fetch=False)
            flash("Activity logged.", "success")
        except (ValueError, mysql.connector.Error):
            flash("Please enter a valid activity duration.", "error")
        return redirect(url_for("activities_page"))
    rows = query("SELECT * FROM activities WHERE userID=%s ORDER BY activityDate DESC, actID DESC", (uid,))
    return render_template("activities.html", activities=rows)


@app.post("/activities/delete/<int:act_id>")
@login_required
def delete_activity(act_id):
    owned = query("SELECT isPlanRecord FROM activities WHERE actID=%s AND userID=%s", (act_id, session["user_id"]))
    if not owned:
        flash("Activity record not found.", "error")
    elif owned[0]["isPlanRecord"]:
        flash("Completed exercise-plan records cannot be deleted.", "error")
    else:
        query("DELETE FROM activities WHERE actID=%s AND userID=%s", (act_id, session["user_id"]), fetch=False)
        flash("Activity deleted.", "success")
    return redirect(url_for("activities_page"))


@app.route("/diet", methods=["GET", "POST"])
@login_required
def diet_page():
    uid = session["user_id"]
    today = date.today().isoformat()

    # Temporary meal builder. Nothing is written to MySQL until the user
    # clicks "Save All Meals". The builder is automatically reset when the
    # calendar date changes so yesterday's unfinished list does not appear
    # as today's meal.
    builder = session.get("diet_builder", {"date": today, "items": []})
    if builder.get("date") != today:
        builder = {"date": today, "items": []}
        session["diet_builder"] = builder

    if request.method == "POST":
        action = request.form.get("action", "add")

        if action == "add":
            try:
                food_id = int(request.form["foodID"])
                qty = float(request.form["quantity"])
                meal_type = request.form.get("mealType", "Breakfast")
                log_date = request.form.get("logDate") or today
                notes = request.form.get("notes", "").strip()

                if qty <= 0:
                    raise ValueError
                if log_date != today:
                    flash("The meal builder is for today's meals. Please use today's date.", "error")
                    return redirect(url_for("diet_page"))

                food = query("SELECT * FROM foods WHERE foodID=%s", (food_id,))
                if not food:
                    flash("Food item not found.", "error")
                    return redirect(url_for("diet_page"))

                f = food[0]
                calories = round(float(f["caloriesPerUnit"]) * qty, 1)
                builder["items"].append({
                    "foodID": f["foodID"],
                    "foodName": f["foodName"],
                    "foodGroup": f["foodGroup"],
                    "servingUnit": f["servingUnit"],
                    "quantity": qty,
                    "calories": calories,
                    "mealType": meal_type,
                    "notes": notes
                })
                session["diet_builder"] = builder
                session.modified = True
                flash(f"{f['foodName']} added to today's meal list.", "success")
            except (ValueError, TypeError):
                flash("Please enter a valid food quantity.", "error")
            return redirect(url_for("diet_page"))

        if action == "remove":
            try:
                index = int(request.form.get("index", -1))
                if 0 <= index < len(builder["items"]):
                    removed = builder["items"].pop(index)
                    session["diet_builder"] = builder
                    session.modified = True
                    flash(f"{removed['foodName']} removed from the meal list.", "success")
            except (ValueError, TypeError):
                pass
            return redirect(url_for("diet_page"))

        if action == "clear":
            session["diet_builder"] = {"date": today, "items": []}
            flash("Today's meal list was cleared.", "success")
            return redirect(url_for("diet_page"))

        if action == "save":
            items = builder.get("items", [])
            if not items:
                flash("Add at least one food to today's meal before saving.", "error")
                return redirect(url_for("diet_page"))

            rows_to_insert = []
            try:
                for item in items:
                    # Re-read the food data from MySQL before saving so the
                    # stored calorie value always comes from the food table.
                    food = query("SELECT * FROM foods WHERE foodID=%s", (item["foodID"],))
                    if not food:
                        raise ValueError("Food item no longer exists.")
                    f = food[0]
                    qty = float(item["quantity"])
                    calories = round(float(f["caloriesPerUnit"]) * qty, 1)
                    rows_to_insert.append((
                        uid, f["foodID"], item["mealType"], qty,
                        calories, today, item.get("notes") or None
                    ))

                query("""
                    INSERT INTO diet_logs
                    (userID,foodID,mealType,quantity,calories,logDate,notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, rows_to_insert, fetch=False, many=True)

                total = sum(float(row[4]) for row in rows_to_insert)
                session["diet_builder"] = {"date": today, "items": []}
                flash(f"Today's meals saved: {total:g} kcal.", "success")
            except (ValueError, TypeError, mysql.connector.Error):
                flash("We could not save the meal list. Please check the entries and try again.", "error")
            return redirect(url_for("diet_page"))

    foods = query("SELECT * FROM foods ORDER BY foodGroup, foodName")

    logs = query("""
        SELECT d.*, f.foodName, f.foodGroup, f.servingUnit
        FROM diet_logs d JOIN foods f ON d.foodID=f.foodID
        WHERE d.userID=%s ORDER BY d.logDate DESC, d.dietID DESC
    """, (uid,))

    # The main Diet Tracker card is intentionally date-scoped: it shows only
    # what was eaten today. Older records remain in the history table and are
    # still available to prediction/analytics queries.
    today_logs = query("""
        SELECT d.*, f.foodName, f.foodGroup, f.servingUnit
        FROM diet_logs d JOIN foods f ON d.foodID=f.foodID
        WHERE d.userID=%s AND d.logDate=%s
        ORDER BY FIELD(d.mealType,'Breakfast','Lunch','Dinner','Snack'), d.dietID
    """, (uid, today))

    meal_order = ["Breakfast", "Lunch", "Dinner", "Snack"]
    today_meals = []
    today_total = 0.0
    for meal_type in meal_order:
        meal_rows = [r for r in today_logs if r["mealType"] == meal_type]
        if meal_rows:
            subtotal = sum(float(r["calories"] or 0) for r in meal_rows)
            today_total += subtotal
            today_meals.append({"mealType": meal_type, "items": meal_rows, "subtotal": subtotal})

    builder_total = sum(float(x.get("calories", 0)) for x in builder.get("items", []))

    # Keep the weekly grouping for the existing nutrition-balance logic and
    # future analytics, even though the main page now emphasizes today's meals.
    week_total = query(
        "SELECT COALESCE(SUM(calories),0) total FROM diet_logs WHERE userID=%s AND logDate >= %s",
        (uid, date_range(7),)
    )[0]["total"]
    groups = query("""
        SELECT f.foodGroup, SUM(d.calories) calories
        FROM diet_logs d JOIN foods f ON d.foodID=f.foodID
        WHERE d.userID=%s AND d.logDate >= %s
        GROUP BY f.foodGroup ORDER BY calories DESC
    """, (uid, date_range(7)))
    suggestions = food_suggestions(groups) if groups else ["Log your meals to see food-group balance suggestions."]

    return render_template(
        "diet.html", foods=foods, logs=logs, today_logs=today_logs,
        today_meals=today_meals, today_total=round(today_total, 1),
        builder=builder, builder_total=round(builder_total, 1),
        today=today, week_total=week_total, groups=groups, suggestions=suggestions
    )


@app.post("/diet/delete/<int:diet_id>")
@login_required
def delete_diet(diet_id):
    query("DELETE FROM diet_logs WHERE dietID=%s AND userID=%s", (diet_id, session["user_id"]), fetch=False)
    flash("Diet entry deleted.", "success")
    return redirect(url_for("diet_page"))


@app.route("/sleep", methods=["GET", "POST"])
@login_required
def sleep_page():
    uid = session["user_id"]
    if request.method == "POST":
        if request.form.get("sleepDate") != date.today().isoformat():
            flash("You can only log sleep records for today.", "error")
            return redirect(url_for("sleep_page"))
        query("""
            INSERT INTO sleep_logs (userID,sleepDate,durationHours,sleepQuality,notes)
            VALUES (%s,%s,%s,%s,%s)
        """, (uid, request.form["sleepDate"], request.form["durationHours"],
               request.form.get("sleepQuality", "Good"), request.form.get("notes")), fetch=False)
        flash("Sleep record logged.", "success")
        return redirect(url_for("sleep_page"))
    logs = query("SELECT * FROM sleep_logs WHERE userID=%s ORDER BY sleepDate DESC, sleepID DESC", (uid,))
    return render_template("sleep.html", logs=logs)


@app.post("/sleep/delete/<int:sleep_id>")
@login_required
def delete_sleep(sleep_id):
    query("DELETE FROM sleep_logs WHERE sleepID=%s AND userID=%s", (sleep_id, session["user_id"]), fetch=False)
    flash("Sleep record deleted.", "success")
    return redirect(url_for("sleep_page"))


@app.route("/prediction")
@login_required
def prediction():
    uid = session["user_id"]
    u = current_user()
    created = u["createdAt"]
    created_date = created.date() if isinstance(created, datetime) else created
    account_days = max(0, (date.today() - created_date).days)
    prediction_available = account_days >= 30
    since30 = date_range(30)
    since14 = date_range(14)

    diet_total = query("SELECT COALESCE(SUM(calories),0) total FROM diet_logs WHERE userID=%s AND logDate BETWEEN %s AND %s",
                       (uid, since30, date.today()))[0]["total"]
    activity_burn = query("SELECT COALESCE(SUM(caloriesBurned),0) total FROM activities WHERE userID=%s AND activityDate BETWEEN %s AND %s",
                          (uid, since30, date.today()))[0]["total"]
    activity_minutes = query("SELECT COALESCE(SUM(durationMin),0) total FROM activities WHERE userID=%s AND activityDate BETWEEN %s AND %s",
                             (uid, since30, date.today()))[0]["total"]

    activity_chart = query("""
        SELECT activityDate, SUM(durationMin) totalMinutes
        FROM activities WHERE userID=%s AND activityDate BETWEEN %s AND %s
        GROUP BY activityDate ORDER BY activityDate
    """, (uid, since30, date.today()))
    sleep_chart = query("""
        SELECT sleepDate, durationHours
        FROM sleep_logs WHERE userID=%s AND sleepDate BETWEEN %s AND %s ORDER BY sleepDate
    """, (uid, since14, date.today()))
    activity_chart = json_date_rows(activity_chart, "activityDate")
    sleep_chart = json_date_rows(sleep_chart, "sleepDate")
    diet_chart = query("""
        SELECT f.foodGroup, SUM(d.calories) calories
        FROM diet_logs d JOIN foods f ON d.foodID=f.foodID
        WHERE d.userID=%s AND d.logDate BETWEEN %s AND %s
        GROUP BY f.foodGroup ORDER BY calories DESC
    """, (uid, since14, date.today()))

    current_weight = float(u.get("weightKg") or 0)
    # Convert the 30-day net calorie balance to an approximate weight change
    # using 7,700 kcal per kg; diet intake less logged exercise burn, as specified.
    net_calories = float(diet_total) - float(activity_burn)
    net_change = round(net_calories / 7700, 1) if current_weight > 0 else 0
    projected_weight = round(current_weight + net_change, 1) if current_weight else 0

    suggestions = []
    if activity_minutes < 150:
        suggestions.append("Your logged activity time is below 150 minutes in the current 30-day record window.")
    else:
        suggestions.append("Your activity records show a consistent amount of logged movement.")
    if sleep_chart:
        avg_sleep = sum(float(x["durationHours"]) for x in sleep_chart) / len(sleep_chart)
        if avg_sleep < 7:
            suggestions.append("Your recent average sleep record is below 7 hours; continue monitoring your sleep duration.")
        elif avg_sleep > 9:
            suggestions.append("Your recent average sleep record is above 9 hours; continue monitoring how this relates to your routine.")
        else:
            suggestions.append("Your recent sleep records are within a 7–9 hour range on average.")
    suggestions.extend(food_suggestions(diet_chart) if diet_chart else ["Log meals to generate diet-balance suggestions."])

    return render_template(
        "prediction.html", account_days=account_days,
        prediction_available=prediction_available, current_weight=current_weight,
        projected_weight=projected_weight, projected_change=round(net_change, 1),
        net_calories=round(net_calories, 0),
        diet_total=round(float(diet_total), 0), activity_burn=round(float(activity_burn), 0),
        activity_minutes=activity_minutes, activity_chart=activity_chart,
        sleep_chart=sleep_chart, diet_chart=diet_chart, suggestions=suggestions
    )


@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals_page():
    uid = session["user_id"]
    if request.method == "POST":
        if request.form["endDate"] < request.form["startDate"]:
            flash("End date must not be earlier than the start date.", "error")
            return redirect(url_for("goals_page"))
        query("""
            INSERT INTO goals
            (userID,goalType,title,activityType,targetValue,targetUnit,targetDescription,startDate,endDate)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            uid, request.form["goalType"], request.form["title"], request.form.get("activityType") or None,
            request.form.get("targetValue") or None, request.form.get("targetUnit") or None,
            request.form.get("targetDescription"), request.form["startDate"], request.form["endDate"]
        ), fetch=False)
        flash("Goal created.", "success")
        return redirect(url_for("goals_page"))

    goals = query("SELECT * FROM goals WHERE userID=%s ORDER BY endDate", (uid,))
    for g in goals:
        updates = query("""
            SELECT COALESCE(SUM(progressValue),0) total,
                   COUNT(*) updateCount,
                   MAX(updateDate) lastUpdate
            FROM goal_updates WHERE goalID=%s
        """, (g["goalID"],))[0]
        g["progressTotal"] = float(updates["total"] or 0)
        g["updateCount"] = updates["updateCount"] or 0
        g["lastUpdate"] = updates["lastUpdate"]
        target = float(g["targetValue"] or 0)
        g["progressPercent"] = min(100, round((g["progressTotal"] / target) * 100)) if target > 0 else 0
        if date.today() > g["endDate"] and g["status"] == "Active":
            g["status"] = "Completed"
            query("UPDATE goals SET status='Completed' WHERE goalID=%s AND userID=%s", (g["goalID"], uid), fetch=False)
        if g["status"] == "Completed":
            if target > 0:
                g["performance"] = f"Recorded {g['progressTotal']:.1f} / {target:.1f} {g['targetUnit'] or ''} ({g['progressPercent']}% of target)."
            else:
                g["performance"] = f"Goal period ended with {g['updateCount']} progress update(s)."
        else:
            g["performance"] = None
    return render_template("goals.html", goals=goals)


@app.post("/goals/<int:goal_id>/update")
@login_required
def update_goal(goal_id):
    owned = query("SELECT goalID, status, endDate FROM goals WHERE goalID=%s AND userID=%s", (goal_id, session["user_id"]))
    if not owned:
        flash("Goal not found.", "error")
        return redirect(url_for("goals_page"))
    if owned[0]["status"] != "Active" or date.today() > owned[0]["endDate"]:
        flash("This goal period has ended and can no longer be updated.", "error")
        return redirect(url_for("goals_page"))
    query("""
        INSERT INTO goal_updates (goalID,updateDate,progressValue,note)
        VALUES (%s,%s,%s,%s)
    """, (goal_id, request.form["updateDate"], request.form.get("progressValue") or 0, request.form.get("note")), fetch=False)
    flash("Goal progress updated.", "success")
    return redirect(url_for("goals_page"))


@app.post("/goals/delete/<int:goal_id>")
@login_required
def delete_goal(goal_id):
    query("DELETE FROM goals WHERE goalID=%s AND userID=%s", (goal_id, session["user_id"]), fetch=False)
    flash("Goal deleted.", "success")
    return redirect(url_for("goals_page"))


@app.route("/plans", methods=["GET"])
@login_required
def plans_page():
    uid = session["user_id"]
    selected_activity = (request.args.get("activity") or "").strip()
    activity_rows = query("""
        SELECT DISTINCT activityType
        FROM exercise_plans
        ORDER BY activityType
    """)
    activity_types = [row["activityType"] for row in activity_rows]

    # 3.2 refinement: preloaded plans are hidden until the user chooses an
    # exercise/activity from the dropdown. This keeps the page clean on entry.
    plans = []
    if selected_activity and selected_activity in activity_types:
        plans = query("""
            SELECT * FROM exercise_plans
            WHERE activityType=%s
            ORDER BY FIELD(levelMode,'Beginner','Intermediate','Vigorous'), levelNumber
        """, (selected_activity,))
    elif selected_activity:
        selected_activity = ""
    progress = query("""
        SELECT p.*, e.activityType, e.levelMode, e.levelNumber, e.durationMin, e.intensity
        FROM plan_progress p JOIN exercise_plans e ON p.planID=e.planID
        WHERE p.userID=%s ORDER BY p.completedAt DESC
    """, (uid,))
    completed_ids = {int(x["planID"]) for x in progress}

    plan_rows = []
    for p in plans:
        p = dict(p)
        p["completed"] = p["planID"] in completed_ids
        # A level is locked if the immediately preceding level/mode for the same
        # exercise has not been completed. Beginner is first, then Intermediate,
        # then Vigorous.
        previous = query("""
            SELECT planID FROM exercise_plans
            WHERE activityType=%s AND (
                (FIELD(levelMode,'Beginner','Intermediate','Vigorous') < FIELD(%s,'Beginner','Intermediate','Vigorous'))
                OR (levelMode=%s AND levelNumber < %s)
            )
            ORDER BY FIELD(levelMode,'Beginner','Intermediate','Vigorous') DESC, levelNumber DESC
            LIMIT 1
        """, (p["activityType"], p["levelMode"], p["levelMode"], p["levelNumber"]))
        p["locked"] = bool(previous and int(previous[0]["planID"]) not in completed_ids)
        plan_rows.append(p)
    return render_template("plans.html", plans=plan_rows, progress=progress,
                           activity_types=activity_types, selected_activity=selected_activity)


@app.post("/plans/<int:plan_id>/complete")
@login_required
def complete_plan(plan_id):
    uid = session["user_id"]

    # Compatibility fix for databases created before exercise-plan tracking
    # was added. This prevents an Unknown column 'isPlanRecord' error.
    ensure_plan_activity_columns()
    plan = query("SELECT * FROM exercise_plans WHERE planID=%s", (plan_id,))
    if not plan:
        flash("Exercise plan level not found.", "error")
        return redirect(url_for("plans_page"))
    p = plan[0]
    already = query("SELECT progressID FROM plan_progress WHERE userID=%s AND planID=%s", (uid, plan_id))
    if already:
        flash("This plan level is already completed.", "error")
        return redirect(url_for("plans_page"))

    previous = query("""
        SELECT e.planID FROM exercise_plans e
        WHERE e.activityType=%s AND (
            FIELD(e.levelMode,'Beginner','Intermediate','Vigorous') < FIELD(%s,'Beginner','Intermediate','Vigorous')
            OR (e.levelMode=%s AND e.levelNumber < %s)
        )
        ORDER BY FIELD(e.levelMode,'Beginner','Intermediate','Vigorous') DESC, e.levelNumber DESC
        LIMIT 1
    """, (p["activityType"], p["levelMode"], p["levelMode"], p["levelNumber"]))
    if previous:
        done = query("SELECT progressID FROM plan_progress WHERE userID=%s AND planID=%s", (uid, previous[0]["planID"]))
        if not done:
            flash("Complete the previous exercise-plan level before advancing.", "error")
            return redirect(url_for("plans_page"))

    progress_id = query("""
        INSERT INTO plan_progress (userID,planID,completedAt,note)
        VALUES (%s,%s,NOW(),%s)
    """, (uid, plan_id, request.form.get("note")), fetch=False)

    u = current_user()
    met = {"Light": 3.0, "Moderate": 5.0, "Vigorous": 8.0}.get(p["intensity"], 5.0)
    kcal = round(met * float(u.get("weightKg") or 60) * (float(p["durationMin"]) / 60), 1)
    query("""
        INSERT INTO activities
        (userID,actType,durationMin,intensity,caloriesBurned,steps,activityDate,notes,isPlanRecord,planProgressID)
        VALUES (%s,%s,%s,%s,%s,0,%s,%s,TRUE,%s)
    """, (uid, p["activityType"], p["durationMin"], p["intensity"], kcal,
           date.today(), f"Exercise Plan: {p['levelMode']} Level {p['levelNumber']}", progress_id), fetch=False)
    flash("Exercise-plan level completed and added to your Fitness Log.", "success")
    return redirect(url_for("plans_page"))


@app.route("/reports", methods=["GET", "POST"])
@login_required
def reports_page():
    uid = session["user_id"]
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        subject = request.form.get("subject", "").strip()
        if not subject or not message:
            flash("Subject and message are required.", "error")
            return redirect(url_for("reports_page"))
        query("""
            INSERT INTO reports (userID,type,subject,message,status)
            VALUES (%s,%s,%s,%s,'Submitted')
        """, (uid, request.form.get("type", "Report"), subject, message), fetch=False)
        flash("Your message has been saved and submitted.", "success")
        return redirect(url_for("reports_page"))
    reports = query("SELECT * FROM reports WHERE userID=%s ORDER BY dateSubmitted DESC, reportID DESC", (uid,))
    return render_template("reports.html", reports=reports)


@app.route("/about")
def about():
    return render_template("about.html")


@app.get("/api/summary")
@login_required
def api_summary():
    uid = session["user_id"]
    return jsonify({
        "activities": query("""
            SELECT actType, SUM(durationMin) minutes, SUM(caloriesBurned) calories
            FROM activities WHERE userID=%s GROUP BY actType ORDER BY minutes DESC
        """, (uid,)),
        "sleep": query("""
            SELECT sleepDate, durationHours FROM sleep_logs
            WHERE userID=%s ORDER BY sleepDate DESC LIMIT 14
        """, (uid,)),
        "nutrition": query("""
            SELECT f.foodGroup, SUM(d.calories) calories
            FROM diet_logs d JOIN foods f ON d.foodID=f.foodID
            WHERE d.userID=%s AND d.logDate >= %s
            GROUP BY f.foodGroup
        """, (uid,))
    })


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)




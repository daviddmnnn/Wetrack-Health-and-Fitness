
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
import mysql.connector
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

USERNAME = "ahlen"
PASSWORD = "12345678"
EMAIL = "ahlensrrn@gmail.com"

conn = mysql.connector.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
try:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT userID, email FROM users WHERE username=%s", (USERNAME,))
    existing = cur.fetchone()
    if existing and existing["email"] != EMAIL:
        raise RuntimeError("The username 'ahlen' already belongs to another account; demo seeding stopped without changing it.")
    if existing:
        user_id = existing["userID"]
        cur.execute("UPDATE users SET passwordHash=%s WHERE userID=%s", (generate_password_hash(PASSWORD), user_id))
    else:
        created_at = date.today() - timedelta(days=41)
        cur.execute("""INSERT INTO users (accountID,lastname,firstname,birthdate,gender,email,contactNo,username,passwordHash,createdAt)
                       VALUES (NULL,'Serrano','Ahlen','2005-06-14','Male',%s,'09170000000',%s,%s,%s)""",
                    (EMAIL, USERNAME, generate_password_hash(PASSWORD), created_at))
        user_id = cur.lastrowid
        cur.execute("UPDATE users SET accountID=%s WHERE userID=%s", (f"202600{int(user_id):04d}", user_id))
    cur.execute("INSERT IGNORE INTO user_info (userID,heightCm,weightKg,bloodType) VALUES (%s,172,68,'O+')", (user_id,))
    cur.execute("SELECT foodID,foodName FROM foods")
    foods = {row["foodName"]: row["foodID"] for row in cur.fetchall()}
    if not foods:
        raise RuntimeError("No foods are available. Run database/schema.sql first.")
    meals = [("Breakfast", "Oatmeal", 1.25), ("Breakfast", "Banana", 1.0), ("Breakfast", "Milk", 1.0),
             ("Lunch", "White Rice", 1.25), ("Lunch", "Chicken Breast", 1.2), ("Lunch", "Mixed Vegetables", 1.5),
             ("Dinner", "Brown Rice", 1.25), ("Dinner", "Fish", 1.2), ("Dinner", "Salad", 1.5),
             ("Snack", "Yogurt", 1.0), ("Snack", "Apple", 1.0)]
    activity_types = ["Walking", "Jogging", "Cycling", "Badminton", "Home Workout", "Swimming"]
    for offset in range(39, -1, -1):
        day = date.today() - timedelta(days=offset)
        cur.execute("SELECT sleepID FROM sleep_logs WHERE userID=%s AND sleepDate=%s LIMIT 1", (user_id, day))
        if not cur.fetchone():
            hours = [6.8, 7.2, 7.6, 8.0, 7.4, 8.3, 7.8][offset % 7]
            quality = "Fair" if hours < 7 else "Good" if hours < 8 else "Excellent"
            cur.execute("INSERT INTO sleep_logs (userID,sleepDate,durationHours,sleepQuality,notes) VALUES (%s,%s,%s,%s,%s)",
                        (user_id, day, hours, quality, "Demo wellness record"))
        cur.execute("SELECT dietID FROM diet_logs WHERE userID=%s AND logDate=%s LIMIT 1", (user_id, day))
        if not cur.fetchone():
            for meal, food_name, quantity in meals:
                if food_name not in foods:
                    continue
                cur.execute("SELECT caloriesPerUnit FROM foods WHERE foodID=%s", (foods[food_name],))
                calories = float(cur.fetchone()["caloriesPerUnit"]) * quantity
                cur.execute("INSERT INTO diet_logs (userID,foodID,mealType,quantity,calories,logDate,notes) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                            (user_id, foods[food_name], meal, quantity, calories, day, "Demo meal record"))
        cur.execute("SELECT actID FROM activities WHERE userID=%s AND activityDate=%s LIMIT 1", (user_id, day))
        if not cur.fetchone():
            # Alternate varied training with easy walking to cover the full sample window.
            if offset % 6 != 0:
                kind = activity_types[offset % len(activity_types)]
                duration = 25 + (offset * 7 % 31)
                intensity = "Light" if duration < 31 else "Moderate" if duration < 47 else "Vigorous"
                burn = round((3.5 if intensity == "Light" else 5.0 if intensity == "Moderate" else 7.5) * 68 * duration / 60, 1)
                steps = 2500 + (offset * 337 % 6500) if kind in ("Walking", "Jogging") else 0
            else:
                kind, duration, intensity, burn, steps = "Walking", 20, "Light", round(3.0 * 68 * 20 / 60, 1), 3000
            cur.execute("INSERT INTO activities (userID,actType,durationMin,intensity,caloriesBurned,steps,activityDate,notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (user_id, kind, duration, intensity, burn, steps, day, "Demo activity record"))
    conn.commit()
    print("Demo account ready: ahlen / 1234567890 (40-day sample window).")
finally:
    conn.close()






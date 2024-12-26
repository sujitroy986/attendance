from flask import Flask, request, render_template, send_from_directory, Response, session, redirect
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

DATABASE = "attendance.db"
UPLOAD_FOLDER = "uploads"

# Ensure the uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def home():
    return render_template("form.html")


@app.route("/submit", methods=["POST"])
def submit_attendance():
    name = request.form["name"]
    mobile = request.form["mobile"]
    classroom = request.form["classroom"]
    image = request.files["image"]

    # Validate the uploaded file
    if image and image.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        image_filename = f"{mobile}_{timestamp.replace(' ', '_').replace(':', '-')}.png"
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
        image.save(image_path)

        # Save data to the database
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    student_id TEXT,
                    name TEXT,
                    mobile TEXT,
                    classroom TEXT,
                    timestamp TEXT,
                    image_path TEXT
                )
            """)
            cursor.execute("""
                INSERT INTO attendance (student_id, name, mobile, classroom, timestamp, image_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (get_or_create_student_id(name, mobile), name, mobile, classroom, timestamp, image_path))
            conn.commit()

        # Success message with JavaScript dialog box
        return f"""
<script>
alert("Attendance Submitted Successfully for {name} in {classroom} at {timestamp}!");
window.location.href = "/";  // Redirect back to form.html
</script>
"""
    else:
        return "Invalid file format. Please upload an image (PNG, JPG, JPEG).", 400


@app.route("/admin", methods=["GET"])
def admin_dashboard():
    classroom_filter = request.args.get("classroom", "")
    date_filter = request.args.get("date", "")
    search_query = request.args.get("search", "")

    query = "SELECT student_id, name, mobile, classroom, timestamp, image_path FROM attendance WHERE 1=1"
    params = []

    if classroom_filter:
        query += " AND classroom = ?"
        params.append(classroom_filter)
    if date_filter:
        query += " AND DATE(timestamp) = ?"
        params.append(date_filter)
    if search_query:
        query += " AND (name LIKE ? OR student_id LIKE ?)"
        params.append(f"%{search_query}%")
        params.append(f"%{search_query}%")

    query += " ORDER BY timestamp DESC"

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        records = cursor.fetchall()

    return render_template("admin.html", records=records)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


def get_or_create_student_id(name, mobile):
    # Generate a unique student ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{mobile[:3]}_{name[:3]}_{timestamp}"


@app.route("/download_report")
def download_report():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, mobile, classroom, timestamp FROM attendance")
        records = cursor.fetchall()

    def generate_csv():
        yield "Student ID,Name,Mobile,Classroom,Timestamp\n"
        for record in records:
            yield ",".join(map(str, record)) + "\n"

    return Response(generate_csv(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})


@app.route("/stats")
def stats():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT classroom, COUNT(*) FROM attendance GROUP BY classroom")
        classroom_stats = cursor.fetchall()

        cursor.execute("SELECT DATE(timestamp), COUNT(*) FROM attendance GROUP BY DATE(timestamp)")
        date_stats = cursor.fetchall()

    return render_template("stats.html", classroom_stats=classroom_stats, date_stats=date_stats)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "admin123":
            session["logged_in"] = True
            return redirect("/admin")
        else:
            return "Invalid credentials", 401
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect("/login")


@app.before_request
def require_login():
    if not session.get("logged_in") and request.endpoint in ["admin_dashboard", "stats"]:
        return redirect("/login")


if __name__ == "__main__":
    app.run(host="10.107.10.45", port=5000)
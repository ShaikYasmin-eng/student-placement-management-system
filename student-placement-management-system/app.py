
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "student-placement-project-key"

DATABASE = "placement.db"


# Connect to database and create tables
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def create_tables():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                roll TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                branch TEXT NOT NULL,
                email TEXT NOT NULL,
                cgpa REAL NOT NULL CHECK(cgpa BETWEEN 0 AND 10)
            );

            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                min_cgpa REAL NOT NULL CHECK(min_cgpa BETWEEN 0 AND 10),
                package REAL NOT NULL CHECK(package >= 0)
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll TEXT NOT NULL,
                company_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Applied',
                UNIQUE(roll, company_id),
                FOREIGN KEY(roll) REFERENCES students(roll)
                    ON DELETE CASCADE,
                FOREIGN KEY(company_id) REFERENCES companies(id)
                    ON DELETE CASCADE
            );
        """)


# Home page
@app.route("/")
def home():
    with get_db() as db:
        students = db.execute(
            "SELECT * FROM students ORDER BY name"
        ).fetchall()

        companies = db.execute(
            "SELECT * FROM companies ORDER BY name"
        ).fetchall()

        applications = db.execute("""
            SELECT a.id, s.name AS student_name, s.roll,
                   c.name AS company_name, c.role, a.status
            FROM applications a
            JOIN students s ON a.roll = s.roll
            JOIN companies c ON a.company_id = c.id
            ORDER BY a.id DESC
        """).fetchall()

    return render_template(
        "index.html",
        students=students,
        companies=companies,
        applications=applications
    )


# Add student
@app.route("/add_student", methods=["POST"])
def add_student():
    roll = request.form.get("roll", "").strip()
    name = request.form.get("name", "").strip()
    branch = request.form.get("branch", "").strip()
    email = request.form.get("email", "").strip()

    try:
        cgpa = float(request.form.get("cgpa", ""))
        if not 0 <= cgpa <= 10:
            raise ValueError
    except ValueError:
        flash("CGPA must be between 0 and 10.", "error")
        return redirect(url_for("home"))

    if not all([roll, name, branch, email]):
        flash("Please fill in all student details.", "error")
        return redirect(url_for("home"))

    try:
        with get_db() as db:
            db.execute("""
                INSERT INTO students (roll, name, branch, email, cgpa)
                VALUES (?, ?, ?, ?, ?)
            """, (roll, name, branch, email, cgpa))

        flash("Student added successfully!", "success")

    except sqlite3.IntegrityError:
        flash("Roll number already exists or details are invalid.", "error")

    return redirect(url_for("home"))


# Add company
@app.route("/add_company", methods=["POST"])
def add_company():
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "").strip()

    try:
        min_cgpa = float(request.form.get("min_cgpa", ""))
        package = float(request.form.get("package", ""))

        if not 0 <= min_cgpa <= 10 or package < 0:
            raise ValueError
    except ValueError:
        flash("Enter a valid CGPA and non-negative package.", "error")
        return redirect(url_for("home"))

    if not name or not role:
        flash("Please enter the company name and job role.", "error")
        return redirect(url_for("home"))

    with get_db() as db:
        db.execute("""
            INSERT INTO companies (name, role, min_cgpa, package)
            VALUES (?, ?, ?, ?)
        """, (name, role, min_cgpa, package))

    flash("Company added successfully!", "success")
    return redirect(url_for("home"))


# Apply for a company
@app.route("/apply", methods=["POST"])
def apply():
    roll = request.form.get("roll", "").strip()

    try:
        company_id = int(request.form.get("company_id", ""))
    except ValueError:
        flash("Please select a valid company.", "error")
        return redirect(url_for("home"))

    with get_db() as db:
        student = db.execute(
            "SELECT * FROM students WHERE roll = ?", (roll,)
        ).fetchone()

        company = db.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()

        if not student or not company:
            flash("Student or company not found.", "error")

        elif student["cgpa"] < company["min_cgpa"]:
            flash("Student does not meet the minimum CGPA.", "error")

        else:
            try:
                db.execute("""
                    INSERT INTO applications (roll, company_id)
                    VALUES (?, ?)
                """, (roll, company_id))

                flash("Application submitted successfully!", "success")

            except sqlite3.IntegrityError:
                flash("This student has already applied to this company.",
                      "error")

    return redirect(url_for("home"))


# Update application status
@app.route("/update_status/<int:application_id>", methods=["POST"])
def update_status(application_id):
    status = request.form.get("status", "")

    allowed_statuses = [
        "Applied", "Shortlisted", "Selected", "Rejected"
    ]

    if status not in allowed_statuses:
        flash("Invalid application status.", "error")
        return redirect(url_for("home"))

    with get_db() as db:
        result = db.execute("""
            UPDATE applications
            SET status = ?
            WHERE id = ?
        """, (status, application_id))

        if result.rowcount:
            flash("Application status updated!", "success")
        else:
            flash("Application not found.", "error")

    return redirect(url_for("home"))


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)

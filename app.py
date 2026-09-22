from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import pandas as pd
import joblib
import random
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from flask import flash
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
import os


from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    ConfusionMatrixDisplay,
    roc_curve,
    auc,
    classification_report
)
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file
)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
department_codes = {
    "Accounting": "ACC",
    "Banking and Finance": "BFN",
    "Business Administration": "BUS",
    "Computer Science": "CSC",
    "Cyber Security": "CYB",
    "Data Science": "DST",
    "Economics": "ECO",
    "Education": "EDU",
    "Information Technology": "ITE",
    "Mass Communication": "MAC",
    "Nursing": "NSC",
    "Political Science": "POL",
    "Public Health": "PHL",
    "Sociology": "SOC",
    "Software Engineering": "SWE"
}
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
# ==========================
# Flask App
# ==========================

app = Flask(__name__)
print(app.url_map)
print(app.template_folder)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "student_dropout_secret_key")
# ==========================================================
# EMAIL CONFIGURATION
# ==========================================================
import os

MAIL_SERVER = "smtp.gmail.com"

MAIL_PORT = 587

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
# ==========================
# Database Connection
# ==========================
import mysql.connector

import os

# Database settings
# Railway provides MYSQL* variables; the localhost/root fallbacks keep WAMP working locally.
DB_HOST = os.getenv("MYSQLHOST", "localhost")
DB_PORT = int(os.getenv("MYSQLPORT", "3306"))
DB_USER = os.getenv("MYSQLUSER", "root")
DB_PASSWORD = os.getenv("MYSQLPASSWORD", "")
DB_NAME = os.getenv("MYSQLDATABASE", "student_dropout_db")

db = mysql.connector.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    autocommit=True,
    connection_timeout=600
)
cursor = db.cursor()
print("Connected to MySQL successfully!")
# ==========================
# Load Machine Learning Model
# ==========================

model = joblib.load("dropout_xgboost_model.pkl")

gender_encoder = joblib.load("gender_encoder.pkl")
department_encoder = joblib.load("department_encoder.pkl")
lms_encoder = joblib.load("lms_encoder.pkl")
financial_encoder = joblib.load("financial_encoder.pkl")

print("Gender encoder classes:")
print(gender_encoder.classes_)

print("Department encoder classes:")
print(department_encoder.classes_)

print("LMS encoder classes:")
print(lms_encoder.classes_)

print("Financial encoder classes:")
print(financial_encoder.classes_)
# ==========================
# Home
# ==========================

@app.route("/")
def home():

    if "user" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))
# ==========================

# ==========================
# Login
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # Reconnect if MySQL connection was lost
        if not db.is_connected():
            db.reconnect()

        cursor = db.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        print("User from DB:", user)
        print("Entered password:", password)

        if user:
            print("Stored hash:", user[2])
            print("Password matches:", check_password_hash(user[2], password))

        if user and check_password_hash(user[2], password):

            session["user"] = user[1]
            session["role"] = user[3]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid Username or Password"
        )

    return render_template("login.html")
# ==========================
# Logout
# ==========================
@app.route("/logout", methods=["GET"])
@login_required
def logout():

    session.clear()

    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():

    # =========================
    # Total Students
    # =========================

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]


    # =========================
    # High Risk
    # =========================

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE prediction = 'HIGH RISK OF DROPOUT'
    """)

    high_risk = cursor.fetchone()[0]


    # =========================
    # Low Risk
    # =========================

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE prediction = 'LOW RISK OF DROPOUT'
    """)

    low_risk = cursor.fetchone()[0]


    # =========================
    # Overall Risk Percentages
    # =========================

    if total_students > 0:

        high_risk_percentage = round(
            (high_risk / total_students) * 100, 1
        )

        low_risk_percentage = round(
            (low_risk / total_students) * 100, 1
        )

    else:

        high_risk_percentage = 0
        low_risk_percentage = 0


    # =========================
    # Total Departments
    # =========================

    cursor.execute("""
        SELECT COUNT(DISTINCT department)
        FROM students
    """)

    departments = cursor.fetchone()[0]


    # =========================
    # Average CGPA
    # =========================

    cursor.execute("""
        SELECT ROUND(AVG(cgpa), 2)
        FROM students
    """)

    average_cgpa = cursor.fetchone()[0] or 0


    # =========================
    # Average Attendance
    # =========================

    cursor.execute("""
        SELECT ROUND(AVG(attendance), 2)
        FROM students
    """)

    average_attendance = cursor.fetchone()[0] or 0


    # =========================
    # Highest Risk Department
    # =========================

    cursor.execute("""
        SELECT department, COUNT(*)
        FROM students
        WHERE prediction = 'HIGH RISK OF DROPOUT'
        GROUP BY department
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)

    result = cursor.fetchone()

    if result:

        highest_risk_department = result[0]
        highest_risk_department_count = result[1]

    else:

        highest_risk_department = "N/A"
        highest_risk_department_count = 0


    # =========================
    # Best Performing Department
    # =========================

    cursor.execute("""
        SELECT department, ROUND(AVG(cgpa), 2)
        FROM students
        GROUP BY department
        ORDER BY AVG(cgpa) DESC
        LIMIT 1
    """)

    result = cursor.fetchone()

    if result:

        best_department = result[0]
        best_department_cgpa = result[1]

    else:

        best_department = "N/A"
        best_department_cgpa = 0


    # =========================
    # Students Per Department
    # =========================

    cursor.execute("""
        SELECT department, COUNT(*)
        FROM students
        GROUP BY department
        ORDER BY COUNT(*) DESC
    """)

    dept_data = cursor.fetchall()

    department_names = [
        row[0] for row in dept_data
    ]

    department_counts = [
        row[1] for row in dept_data
    ]


    # =========================
    # High-Risk Students Per Department
    # =========================

    cursor.execute("""
        SELECT department, COUNT(*)
        FROM students
        WHERE prediction = 'HIGH RISK OF DROPOUT'
        GROUP BY department
        ORDER BY COUNT(*) DESC
    """)

    risk_dept_data = cursor.fetchall()

    risk_department_names = [
        row[0] for row in risk_dept_data
    ]

    risk_department_counts = [
        row[1] for row in risk_dept_data
    ]


    # =========================
    # High-Risk Percentage By Department
    # =========================

    cursor.execute("""
        SELECT
            department,
            COUNT(*) AS total_students,
            SUM(
                CASE
                    WHEN prediction = 'HIGH RISK OF DROPOUT'
                    THEN 1
                    ELSE 0
                END
            ) AS high_risk_students
        FROM students
        GROUP BY department
        ORDER BY department
    """)

    risk_percentage_data = cursor.fetchall()

    risk_percentage_names = []
    risk_percentage_values = []

    for row in risk_percentage_data:

        department = row[0]
        total = row[1]
        high = row[2] or 0

        if total > 0:

            percentage = round(
                (high / total) * 100,
                2
            )

        else:

            percentage = 0

        risk_percentage_names.append(department)
        risk_percentage_values.append(percentage)


    # =========================
    # High-Risk Percentage By Academic Level
    # =========================

    cursor.execute("""
        SELECT
            level,
            COUNT(*) AS total_students,
            SUM(
                CASE
                    WHEN prediction = 'HIGH RISK OF DROPOUT'
                    THEN 1
                    ELSE 0
                END
            ) AS high_risk_students
        FROM students
        GROUP BY level
        ORDER BY level
    """)

    risk_level_data = cursor.fetchall()

    risk_level_names = []
    risk_level_values = []

    for row in risk_level_data:

        level = row[0]
        total = row[1]
        high = row[2] or 0

        if total > 0:

            percentage = round(
                (high / total) * 100,
                2
            )

        else:

            percentage = 0

        risk_level_names.append(
            f"Year {int(level) // 100}"
        )

        risk_level_values.append(percentage)


    # =========================
    # FINAL DASHBOARD
    # =========================

    return render_template(
        "dashboard.html",

        total_students=total_students,

        high_risk=high_risk,

        low_risk=low_risk,

        high_risk_percentage=high_risk_percentage,

        low_risk_percentage=low_risk_percentage,

        departments=departments,

        average_cgpa=average_cgpa,

        average_attendance=average_attendance,

        highest_risk_department=highest_risk_department,

        highest_risk_department_count=highest_risk_department_count,

        best_department=best_department,

        best_department_cgpa=best_department_cgpa,

        department_names=department_names,

        department_counts=department_counts,

        risk_department_names=risk_department_names,

        risk_department_counts=risk_department_counts,

        risk_percentage_names=risk_percentage_names,

        risk_percentage_values=risk_percentage_values,

        risk_level_names=risk_level_names,

        risk_level_values=risk_level_values
    )   

@app.route("/admin_management")
@login_required
def admin_management():

    print("Session Role:", session.get("role"))
    # Only Administrators can access
    if session.get("role") != "Super Administrator":
        return redirect(url_for("dashboard"))
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, username, email, role
        FROM users
        ORDER BY id ASC
    """)

    admins = cursor.fetchall()

    return render_template(
        "admin_management.html",
        admins=admins
        )

@app.route("/add_admin", methods=["GET", "POST"])
@login_required
def add_admin():

    if session.get("role") != "Super Administrator":
        return redirect(url_for("dashboard"))

    cursor = db.cursor()

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        # Check duplicate username
        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        existing = cursor.fetchone()

        if existing:
            return render_template(
                "add_admin.html",
                error="Username already exists."
            )

        # Hash password
        hashed_password = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (username, password, role, email)
            VALUES (%s, %s, %s, %s)
            """,
            (
                username,
                hashed_password,
                role,
                email
            )
        )

        db.commit()

        return redirect(url_for("admin_management"))

    return render_template("add_admin.html")

@app.route("/edit_admin/<int:id>", methods=["GET", "POST"])
@login_required
def edit_admin(id):

    if session.get("role") != "Super Administrator":
        return redirect(url_for("dashboard"))

    cursor = db.cursor()

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        role = request.form["role"]

        cursor.execute(
            """
            UPDATE users
            SET username=%s,
                email=%s,
                role=%s
            WHERE id=%s
            """,
            (username, email, role, id)
        )

        db.commit()

        return redirect(url_for("admin_management"))

    cursor.execute(
        """
        SELECT id, username, email, role
        FROM users
        WHERE id=%s
        """,
        (id,)
    )

    admin = cursor.fetchone()

    return render_template(
        "edit_admin.html",
        admin=admin
    )
@app.route("/delete_admin/<int:id>")
@login_required
def delete_admin(id):

    if session.get("role") != "Super Administrator":
        return redirect(url_for("dashboard"))

    cursor = db.cursor()

    # Check the user to be deleted
    cursor.execute(
        "SELECT username FROM users WHERE id=%s",
        (id,)
    )

    user = cursor.fetchone()

    # Prevent deleting yourself
    if user and user[0] == session.get("user"):
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin_management"))

    # Delete the selected user
    cursor.execute(
        "DELETE FROM users WHERE id=%s",
        (id,)
          )

    db.commit()

    flash("Administrator deleted successfully.", "success")

    return redirect(url_for("admin_management"))
# ==========================
# Single Prediction
# ==========================
@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():

    if request.method == "POST":

        student_id = request.form["student_id"]
        student_name = request.form["student_name"]

        age = int(request.form["age"])
        gender = request.form["gender"]
        department = request.form["department"]
        level = int(request.form["level"])
        attendance = float(request.form["attendance"])
        cgpa = float(request.form["cgpa"])
        failed_courses = int(request.form["failed_courses"])
        lms = request.form["lms"]
        financial = request.form["financial"]

        # -------------------------
        # Gender Encoding
        # -------------------------

        if gender == "Male":
            gender_encoded = 0

        elif gender == "Female":
            gender_encoded = 1

        else:
            gender_encoded = int(gender)

        # -------------------------
        # Other Encoders
        # -------------------------

        department_encoded = department_encoder.transform([department])[0]
        lms_encoded = lms_encoder.transform([lms])[0]
        financial_encoded = financial_encoder.transform([financial])[0]

        # -------------------------
        # DataFrame
        # -------------------------

        data = pd.DataFrame([{

            "Age": age,
            "Gender": gender_encoded,
            "Department": department_encoded,
            "Level": level,
            "Attendance": attendance,
            "CGPA": cgpa,
            "Failed_Courses": failed_courses,
            "LMS_Engagement": lms_encoded,
            "Financial_Stress": financial_encoded

        }])

        prediction = model.predict(data)[0]

        probabilities = model.predict_proba(data)[0]

        if prediction == 1:
            probability = probabilities[1] * 100
        else:
            probability = probabilities[0] * 100

        reasons = []

        if attendance < 70:
            reasons.append("Attendance is below 70%.")

        if cgpa < 2.5:
            reasons.append("CGPA is below 2.50.")

        if failed_courses >= 3:
            reasons.append("Student has many failed courses.")

        if lms == "Low":
            reasons.append("Low LMS engagement.")

        if financial == "Yes":
            reasons.append("Student is experiencing financial stress.")

        if len(reasons) == 0:
            reasons.append("No major risk factors were detected for this student.")

        if prediction == 1:
            prediction_text = "HIGH RISK OF DROPOUT"
            recommendation = "Immediate academic counselling and student support are recommended."
        else:
            prediction_text = "LOW RISK OF DROPOUT"
            recommendation = "Student is progressing well. Continue regular academic monitoring."

        sql = """
        INSERT INTO students
        (student_id, student_name, age, gender, department, level,
        attendance, cgpa, failed_courses, lms_engagement,
        financial_stress, prediction)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms,
            financial,
            prediction_text
        )

        cursor.execute(sql, values)
        db.commit()

        return render_template(
            "result.html",
            student_id=student_id,
            student_name=student_name,
            prediction=prediction_text,
            probability=round(probability, 2),
            recommendation=recommendation,
            reasons=reasons
        )

    return render_template("predict.html")
# ==========================
# Batch Prediction
# ==========================

@app.route("/batch", methods=["GET", "POST"])
@login_required
def batch():

    if request.method == "POST":

        file = request.files.get("file")

        if not file or file.filename == "":
            return "Please select a CSV or Excel file."

        # =========================
        # READ FILE
        # =========================

        if file.filename.lower().endswith(".csv"):

            df = pd.read_csv(file)

        elif file.filename.lower().endswith(".xlsx"):

            df = pd.read_excel(file)

        else:

            return "Please upload a CSV or Excel (.xlsx) file."

        # Remove spaces from column names
        df.columns = df.columns.str.strip()

        print("Uploaded Columns:")
        print(df.columns.tolist())

        # =========================
        # CHECK REQUIRED COLUMNS
        # =========================

        required_columns = [
            "Student_ID",
            "Age",
            "Gender",
            "Department",
            "Level",
            "Attendance",
            "CGPA",
            "Failed_Courses",
            "LMS_Engagement",
            "Financial_Stress"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:

            return (
                "Missing required columns: "
                + ", ".join(missing_columns)
            )

        # =========================
        # REMOVE EMPTY STUDENT IDs
        # =========================

        df = df.dropna(subset=["Student_ID"])

        df["Student_ID"] = (
            df["Student_ID"]
            .astype(str)
            .str.strip()
        )

        # Remove duplicate IDs inside uploaded file
        df = df.drop_duplicates(
            subset=["Student_ID"],
            keep="first"
        )

        # =========================
        # ENCODE CATEGORICAL DATA
        # =========================

        try:

            df["Gender"] = gender_encoder.transform(
                df["Gender"].astype(str).str.strip()
            )

            df["Department"] = department_encoder.transform(
                df["Department"].astype(str).str.strip()
            )

            df["LMS_Engagement"] = lms_encoder.transform(
                df["LMS_Engagement"].astype(str).str.strip()
            )

            df["Financial_Stress"] = financial_encoder.transform(
                df["Financial_Stress"].astype(str).str.strip()
            )

        except Exception as e:

            return f"Encoding error: {str(e)}"

        # =========================
        # MACHINE LEARNING FEATURES
        # =========================

        X = df[
            [
                "Age",
                "Gender",
                "Department",
                "Level",
                "Attendance",
                "CGPA",
                "Failed_Courses",
                "LMS_Engagement",
                "Financial_Stress"
            ]
        ]

        # =========================
        # PREDICTION
        # =========================

        predictions = model.predict(X)

        probabilities = (
            model.predict_proba(X)[:, 1] * 100
        )

        df["Prediction"] = predictions

        df["Probability (%)"] = (
            probabilities.round(2)
        )

        df["Prediction"] = df["Prediction"].map({
            0: "LOW RISK OF DROPOUT",
            1: "HIGH RISK OF DROPOUT"
        })

        # =========================
        # STATISTICS
        # =========================

        total_students = len(df)

        high_risk = (
            df["Prediction"] ==
            "HIGH RISK OF DROPOUT"
        ).sum()

        low_risk = (
            df["Prediction"] ==
            "LOW RISK OF DROPOUT"
        ).sum()

        average_probability = round(
            df["Probability (%)"].mean(),
            2
        )

        # =========================
        # CONVERT BACK TO TEXT
        # =========================

        df["Gender"] = gender_encoder.inverse_transform(
            df["Gender"]
        )

        df["Department"] = department_encoder.inverse_transform(
            df["Department"]
        )

        df["LMS_Engagement"] = lms_encoder.inverse_transform(
            df["LMS_Engagement"]
        )

        df["Financial_Stress"] = financial_encoder.inverse_transform(
            df["Financial_Stress"]
        )

        # =========================
        # GET EXISTING STUDENT IDs
        # =========================

        cursor.execute(
            "SELECT student_id FROM students"
        )

        existing_ids = {
            str(row[0]).strip()
            for row in cursor.fetchall()
        }

        print(
            "Existing students in database:",
            len(existing_ids)
        )

        # =========================
        # INSERT ONLY NEW STUDENTS
        # =========================

        inserted = 0
        skipped = 0

        sql = """
            INSERT INTO students
            (
                student_id,
                student_name,
                age,
                gender,
                department,
                level,
                attendance,
                cgpa,
                failed_courses,
                lms_engagement,
                financial_stress,
                prediction
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        for _, row in df.iterrows():

            student_id = str(
                row["Student_ID"]
            ).strip()

            # =========================
            # SKIP EXISTING STUDENT
            # =========================

            if student_id in existing_ids:

                skipped += 1
                continue

            # =========================
            # STUDENT NAME
            # =========================

            if "Student_Name" in df.columns:

                student_name = str(
                    row["Student_Name"]
                ).strip()

            elif "student_name" in df.columns:

                student_name = str(
                    row["student_name"]
                ).strip()

            else:

                # CSV does not contain names
                student_name = student_id

            # =========================
            # INSERT
            # =========================

            values = (
                student_id,
                student_name,
                int(row["Age"]),
                row["Gender"],
                row["Department"],
                int(row["Level"]),
                float(row["Attendance"]),
                float(row["CGPA"]),
                int(row["Failed_Courses"]),
                row["LMS_Engagement"],
                row["Financial_Stress"],
                row["Prediction"]
            )

            cursor.execute(
                sql,
                values
            )

            existing_ids.add(student_id)

            inserted += 1

        # =========================
        # SAVE
        # =========================

        db.commit()

        print(
            "Students inserted:",
            inserted
        )

        print(
            "Students skipped:",
            skipped
        )

        # =========================
        # SAVE PREDICTION RESULTS
        # =========================

        df.to_csv(
            "prediction_results.csv",
            index=False
        )

        # =========================
        # RETURN RESULT PAGE
        # =========================

        return render_template(
            "batch_result.html",

            tables=[
                df.to_html(
                    classes=(
                        "table "
                        "table-striped "
                        "table-hover "
                        "table-bordered"
                    ),
                    index=False
                )
            ],

            titles=df.columns.values,

            total_students=total_students,

            high_risk=high_risk,

            low_risk=low_risk,

            average_probability=average_probability,

            inserted=inserted,

            skipped=skipped
        )

    return render_template("batch.html")
# Run Application
# ==========================
# ==========================
# Add Student
# ========================== 
@app.route("/add_student", methods=["GET", "POST"])
@login_required
def add_student():

    if request.method == "POST":

        student_name = request.form["student_name"]
        age = int(request.form["age"])
        gender = request.form["gender"]
        department = request.form["department"]
        level = int(request.form["level"])
        attendance = float(request.form["attendance"])
        cgpa = float(request.form["cgpa"])
        failed_courses = int(request.form["failed_courses"])
        lms_engagement = request.form["lms_engagement"]
        financial_stress = request.form["financial_stress"]

        # ----------------------------
        # Generate Registration Number
        # ----------------------------
        from datetime import datetime

        year = datetime.now().year

        department_codes = {
            "Accounting": "ACC",
            "Banking and Finance": "BFN",
            "Business Administration": "BUS",
            "Computer Science": "CSC",
            "Cyber Security": "CYB",
            "Data Science": "DST",
            "Economics": "ECO",
            "Education": "EDU",
            "Information Technology": "ITE",
            "Mass Communication": "MAC",
            "Nursing": "NUR",
            "Political Science": "POL",
            "Public Health": "PHL",
            "Sociology": "SOC",
            "Software Engineering": "SWE"
        }

        code = department_codes.get(department, "STD")

        cursor.execute("""
            SELECT COUNT(*)
            FROM students
            WHERE department=%s
            AND student_id LIKE %s
        """, (department, f"{code}/{year}/%"))

        count = cursor.fetchone()[0] + 1

        student_id = f"{code}/{year}/{count:03d}"

        # ----------------------------
        # Encode Values
        # ----------------------------
        gender_encoded = gender_encoder.transform([gender])[0]
        department_encoded = department_encoder.transform([department])[0]
        lms_encoded = lms_encoder.transform([lms_engagement])[0]
        financial_encoded = financial_encoder.transform([financial_stress])[0]

        data = pd.DataFrame([{
            "Age": age,
            "Gender": gender_encoded,
            "Department": department_encoded,
            "Level": level,
            "Attendance": attendance,
            "CGPA": cgpa,
            "Failed_Courses": failed_courses,
            "LMS_Engagement": lms_encoded,
            "Financial_Stress": financial_encoded
        }])

        prediction = model.predict(data)[0]

        if prediction == 1:
            prediction_text = "HIGH RISK OF DROPOUT"
        else:
            prediction_text = "LOW RISK OF DROPOUT"

        sql = """
        INSERT INTO students
        (
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction_text
        )

        cursor.execute(sql, values)
        db.commit()

        return redirect(url_for("students"))

    return render_template("add_student.html")
# ==========================
# Student Records
# ==========================

@app.route("/students")
@login_required
def students():

    search = request.args.get("search", "")
    department = request.args.get("department", "")
    level = request.args.get("level", "")
    prediction = request.args.get("prediction", "")
    sql = "SELECT * FROM students WHERE 1=1"
    params = []

    if search:
        sql += """
        AND (
            student_id LIKE %s
            OR student_name LIKE %s
            OR department LIKE %s
        )
        """
        value = "%" + search + "%"
        params.extend([value, value, value])

    if department:
        sql += " AND department=%s"
        params.append(department)
    if level:
        sql += " AND level=%s"
        params.append(level)    
    if prediction:
        sql += " AND prediction LIKE %s"
        params.append("%" + prediction + "%")
        sql += """
        ORDER BY department ASC,
         level ASC,
         student_id ASC
        """
    cursor.execute(sql, tuple(params))
    records = cursor.fetchall()

    return render_template(
    "students.html",
    records=records,
    search=search,
    department=department,
    level=level,
    prediction=prediction
)
# ==========================
# At-Risk Students / Early Warning
# ==========================

@app.route("/at_risk_students")
@login_required
def at_risk_students():

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            student_name,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE prediction LIKE '%HIGH%'
        ORDER BY department ASC, level ASC, student_name ASC
    """)

    records = cursor.fetchall()

    return render_template(
        "at_risk_students.html",
        records=records
    )

@app.route("/add_intervention/<int:student_id>", methods=["GET", "POST"])
@login_required
def add_intervention(student_id):

    db = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        connection_timeout=600
    )

    cursor = db.cursor()

    # ======================================================
    # GET COMPLETE STUDENT RISK INFORMATION
    # ======================================================

    cursor.execute("""
        SELECT
            id,
            student_id,
            student_name,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE id = %s
    """, (student_id,))

    student = cursor.fetchone()

    if not student:

        flash("Student not found.", "danger")

        cursor.close()
        db.close()

        return redirect(url_for("at_risk_students"))

    # ======================================================
    # IDENTIFY STUDENT RISK FACTORS
    # ======================================================

    risk_factors = []
    suggested_interventions = []

    attendance = float(student[5])
    cgpa = float(student[6])
    failed_courses = int(student[7])
    lms_engagement = str(student[8]).strip().lower()
    financial_stress = str(student[9]).strip().lower()

    # Low attendance
    if attendance < 60:

        risk_factors.append(
            f"Low attendance ({attendance}%)"
        )

        suggested_interventions.append(
            "Attendance Monitoring"
        )

    # Low CGPA
    if cgpa < 2.50:

        risk_factors.append(
            f"Low CGPA ({cgpa})"
        )

        suggested_interventions.append(
            "Academic Counselling"
        )

    # Failed courses
    if failed_courses >= 3:

        risk_factors.append(
            f"Multiple failed courses ({failed_courses})"
        )

        suggested_interventions.append(
            "Academic Advising"
        )

    # Low LMS engagement
    if lms_engagement == "low":

        risk_factors.append(
            "Low LMS engagement"
        )

        suggested_interventions.append(
            "Academic Monitoring"
        )

    # Financial stress
    if financial_stress in ["yes", "high", "true", "1"]:

        risk_factors.append(
            "Financial stress"
        )

        suggested_interventions.append(
            "Financial Support"
        )

    # Remove duplicate interventions
    suggested_interventions = list(
        dict.fromkeys(suggested_interventions)
    )

    # ======================================================
    # AUTOMATIC DEFAULT INTERVENTION
    # ======================================================

    if suggested_interventions:

        recommended_intervention = suggested_interventions[0]

    else:

        recommended_intervention = "Academic Monitoring"

    # ======================================================
    # AUTOMATIC REMARKS
    # ======================================================

    remark_parts = []

    if attendance < 60:

        remark_parts.append(
            f"low attendance ({attendance}%)"
        )

    if cgpa < 2.50:

        remark_parts.append(
            f"low CGPA ({cgpa})"
        )

    if failed_courses >= 3:

        remark_parts.append(
            f"multiple failed courses ({failed_courses})"
        )

    if lms_engagement == "low":

        remark_parts.append(
            "low LMS engagement"
        )

    if financial_stress in ["yes", "high", "true", "1"]:

        remark_parts.append(
            "financial stress"
        )

    if remark_parts:

        if len(remark_parts) == 1:

            automatic_remarks = (
                f"Student requires support due to "
                f"{remark_parts[0]}. "
                "Appropriate intervention and follow-up "
                "are recommended."
            )

        else:

            automatic_remarks = (
                "Student requires support due to "
                + ", ".join(remark_parts[:-1])
                + " and "
                + remark_parts[-1]
                + ". Appropriate intervention and "
                "follow-up are recommended."
            )

    else:

        automatic_remarks = (
            "Student identified as requiring academic "
            "support. Appropriate monitoring and "
            "follow-up are recommended."
        )

    # ======================================================
    # SAVE INTERVENTION
    # ======================================================

    if request.method == "POST":

        intervention_type = request.form.get(
            "intervention_type"
        )

        status = request.form.get(
            "status"
        )

        intervention_date = request.form.get(
            "intervention_date"
        )

        counsellor = request.form.get(
            "counsellor"
        )

        remarks = request.form.get(
            "remarks"
        )

        follow_up_date = request.form.get(
            "follow_up_date"
        )

        # If remarks are empty, use automatic remarks
        if not remarks or not remarks.strip():

            remarks = automatic_remarks

        cursor.execute("""
            INSERT INTO interventions
            (
                student_id,
                intervention_type,
                status,
                intervention_date,
                counsellor,
                remarks,
                follow_up_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            intervention_type,
            status,
            intervention_date,
            counsellor,
            remarks,
            follow_up_date
        ))

        db.commit()

        cursor.close()
        db.close()

        flash(
            "Intervention recorded successfully.",
            "success"
        )

        return redirect(
            url_for("at_risk_students")
        )

    # ======================================================
    # DISPLAY FORM
    # ======================================================

    cursor.close()
    db.close()

    return render_template(
        "add_intervention.html",
        student=student,
        risk_factors=risk_factors,
        suggested_interventions=suggested_interventions,
        recommended_intervention=recommended_intervention,
        automatic_remarks=automatic_remarks
    )
@app.route("/intervention_history/<int:student_id>")
@login_required
def intervention_history(student_id):

    db = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        connection_timeout=600
    )

    cursor = db.cursor()

    # Get student information
    cursor.execute("""
        SELECT
            id,
            student_id,
            student_name,
            department,
            level,
            prediction
        FROM students
        WHERE id = %s
    """, (student_id,))

    student = cursor.fetchone()

    if not student:
        cursor.close()
        db.close()

        flash("Student not found.", "danger")

        return redirect(url_for("at_risk_students"))

    # Get intervention history
    cursor.execute("""
        SELECT
            id,
            intervention_type,
            status,
            intervention_date,
            counsellor,
            remarks,
            follow_up_date,
            created_at
        FROM interventions
        WHERE student_id = %s
        ORDER BY intervention_date DESC, id DESC
    """, (student_id,))

    interventions = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "intervention_history.html",
        student=student,
        interventions=interventions
    )
@app.route("/student_history/<int:student_id>")
@login_required
def student_history(student_id):

    db = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        connection_timeout=600
    )

    cursor = db.cursor()

    # ==========================================
    # GET STUDENT INFORMATION
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            student_id,
            student_name,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE id = %s
    """, (student_id,))

    student = cursor.fetchone()

    if not student:

        cursor.close()
        db.close()

        flash("Student not found.", "danger")

        return redirect(url_for("at_risk_students"))

    # ==========================================
    # GET INTERVENTION HISTORY
    # ==========================================

    cursor.execute("""
        SELECT
            intervention_type,
            status,
            intervention_date,
            counsellor,
            remarks,
            follow_up_date
        FROM interventions
        WHERE student_id = %s
        ORDER BY intervention_date DESC
    """, (student_id,))

    interventions = cursor.fetchall()

    # ==========================================
    # GET MESSAGE HISTORY
    # ==========================================

    cursor.execute("""
        SELECT
            recipient_type,
            recipient_name,
            recipient_contact,
            subject,
            message,
            channel,
            status,
            sent_at,
            created_at
        FROM messages
        WHERE student_id = %s
        ORDER BY created_at DESC
    """, (student_id,))

    messages = cursor.fetchall()

    cursor.close()
    db.close()

    # ==========================================
    # DISPLAY COMBINED HISTORY
    # ==========================================

    return render_template(
        "student_history.html",
        student=student,
        interventions=interventions,
        messages=messages
    )
@app.route("/edit_intervention/<int:intervention_id>", methods=["GET", "POST"])
@login_required
def edit_intervention(intervention_id):

    db = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        connection_timeout=600
    )

    cursor = db.cursor()

    # Get the intervention record
    cursor.execute("""
        SELECT
            id,
            student_id,
            intervention_type,
            status,
            intervention_date,
            counsellor,
            remarks,
            follow_up_date
        FROM interventions
        WHERE id = %s
    """, (intervention_id,))

    intervention = cursor.fetchone()

    if not intervention:
        cursor.close()
        db.close()

        flash("Intervention record not found.", "danger")

        return redirect(url_for("at_risk_students"))

    if request.method == "POST":

        intervention_type = request.form.get("intervention_type")
        status = request.form.get("status")
        intervention_date = request.form.get("intervention_date")
        counsellor = request.form.get("counsellor")
        remarks = request.form.get("remarks")
        follow_up_date = request.form.get("follow_up_date")

        cursor.execute("""
            UPDATE interventions
            SET
                intervention_type = %s,
                status = %s,
                intervention_date = %s,
                counsellor = %s,
                remarks = %s,
                follow_up_date = %s
            WHERE id = %s
        """, (
            intervention_type,
            status,
            intervention_date,
            counsellor,
            remarks,
            follow_up_date,
            intervention_id
        ))

        db.commit()

        cursor.close()
        db.close()

        flash("Intervention updated successfully.", "success")

        return redirect(
            url_for(
                "intervention_history",
                student_id=intervention[1]
            )
        )

    cursor.close()
    db.close()

    return render_template(
        "edit_intervention.html",
        intervention=intervention
    )
@app.route("/send_message/<int:student_id>", methods=["GET", "POST"])
@login_required
def send_message(student_id):

    db = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        connection_timeout=600
    )

    cursor = db.cursor()

    # ==================================================
    # GET STUDENT INFORMATION
    # ==================================================

    cursor.execute("""
        SELECT
            id,
            student_id,
            student_name,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE id = %s
    """, (student_id,))

    student = cursor.fetchone()

    if not student:
        cursor.close()
        db.close()

        flash("Student not found.", "danger")

        return redirect(url_for("at_risk_students"))

    # ==================================================
    # STUDENT INFORMATION
    # ==================================================

    student_db_id = student[0]
    student_number = student[1]
    student_name = student[2]
    department = student[3]
    level = student[4]
    attendance = float(student[5])
    cgpa = float(student[6])
    failed_courses = int(student[7])
    lms_engagement = student[8]
    financial_stress = student[9]
    prediction = student[10]

    # ==================================================
    # IDENTIFY RISK FACTORS
    # ==================================================

    risk_factors = []

    if attendance < 60:
        risk_factors.append("low attendance")

    if cgpa < 2.50:
        risk_factors.append("academic performance")

    if failed_courses >= 3:
        risk_factors.append("failed courses")

    if str(lms_engagement).lower() == "low":
        risk_factors.append("low learning engagement")

    if str(financial_stress).lower() == "yes":
        risk_factors.append("financial challenges")

    # ==================================================
    # GENERATE STANDARD MESSAGE
    # ==================================================

    if risk_factors:

        if len(risk_factors) == 1:
            issue_text = risk_factors[0]

        elif len(risk_factors) == 2:
            issue_text = (
                f"{risk_factors[0]} and "
                f"{risk_factors[1]}"
            )

        else:
            issue_text = (
                ", ".join(risk_factors[:-1])
                + ", and "
                + risk_factors[-1]
            )

        generated_message = f"""
Dear {student_name},

Our student support system has identified that you may benefit from additional support in the following area(s): {issue_text}.

We would like to invite you to meet with the student support or academic counselling team so that we can better understand any challenges you may be experiencing and provide appropriate assistance.

Our goal is to support your academic progress and help you successfully complete your programme.

Please treat this invitation as an opportunity for support and guidance.

Kind regards,

Student Support Team
"""

    else:

        generated_message = f"""
Dear {student_name},

Our student support system has identified that you may benefit from an academic support and progress review.

We would like to invite you to meet with the student support or academic counselling team so that we can review your academic progress and discuss any support that may be beneficial.

Our goal is to support your academic success and help you successfully complete your programme.

Kind regards,

Student Support Team
"""

    # ==================================================
    # PROCESS FORM SUBMISSION
    # ==================================================

    if request.method == "POST":

        recipient_type = request.form.get("recipient_type")
        recipient_name = request.form.get("recipient_name")
        recipient_contact = request.form.get("recipient_contact")
        subject = request.form.get("subject")
        message = request.form.get("message")
        channel = request.form.get("channel")

        status = "PENDING"
        sent_at = None

        # ==================================================
        # EMAIL
        # ==================================================

        if channel == "EMAIL":

            try:

                msg = MIMEMultipart()

                msg["From"] = MAIL_USERNAME
                msg["To"] = recipient_contact
                msg["Subject"] = subject

                msg.attach(
                    MIMEText(message, "plain")
                )

                server = smtplib.SMTP(
                    MAIL_SERVER,
                    MAIL_PORT
                )

                server.starttls()

                server.login(
                    MAIL_USERNAME,
                    MAIL_PASSWORD
                )

                server.sendmail(
                    MAIL_USERNAME,
                    recipient_contact,
                    msg.as_string()
                )

                server.quit()

                status = "SENT"
                sent_at = datetime.now()

                flash(
                    "Email sent successfully to "
                    + recipient_contact,
                    "success"
                )

            except Exception as e:

                status = "FAILED"
                sent_at = None

                flash(
                    "Email could not be sent: "
                    + str(e),
                    "danger"
                )

        # ==================================================
        # SMS
        # ==================================================

        elif channel == "SMS":

            status = "PENDING"
            sent_at = None

            flash(
                "SMS message saved. SMS gateway integration is required to send it.",
                "warning"
            )

        # ==================================================
        # WHATSAPP
        # ==================================================

        elif channel == "WHATSAPP":

            status = "PENDING"
            sent_at = None

            flash(
                "WhatsApp message saved. WhatsApp API integration is required to send it.",
                "warning"
            )

        # ==================================================
        # SAVE MESSAGE
        # ==================================================

        cursor.execute("""
            INSERT INTO messages
            (
                student_id,
                recipient_type,
                recipient_name,
                recipient_contact,
                subject,
                message,
                channel,
                status,
                sent_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            student_db_id,
            recipient_type,
            recipient_name,
            recipient_contact,
            subject,
            message,
            channel,
            status,
            sent_at
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("at_risk_students")
        )

    # ==================================================
    # DISPLAY MESSAGE PAGE
    # ==================================================

    cursor.close()
    db.close()

    return render_template(
        "send_message.html",
        student=student,
        generated_message=generated_message,
        risk_factors=risk_factors
    )

@app.route("/message_history")
@login_required
def message_history():

    db = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        connection_timeout=600
    )

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            recipient_type,
            recipient_name,
            recipient_contact,
            subject,
            channel,
            status,
            sent_at,
            created_at
        FROM messages
        ORDER BY created_at DESC
    """)

    messages = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "message_history.html",
        messages=messages
    )
@app.route("/export_excel")
@login_required
def export_excel():

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
    """)

    records = cursor.fetchall()

    columns = [
        "Student ID",
        "Student Name",
        "Age",
        "Gender",
        "Department",
        "Level",
        "Attendance",
        "CGPA",
        "Failed Courses",
        "LMS Engagement",
        "Financial Stress",
        "Prediction"
    ]

    df = pd.DataFrame(records, columns=columns)

    filename = "Student_Records.xlsx"

    df.to_excel(filename, index=False)

    return send_file(
        filename,
        as_attachment=True
    )
# ==========================================================
# REPORTS DASHBOARD
# ==========================================================
@app.route("/reports")
@login_required
def reports():

    cursor = db.cursor()

    cursor.execute("""
        SELECT DISTINCT department
        FROM students
        WHERE department IS NOT NULL
        AND department != ''
        ORDER BY department ASC
    """)

    departments = cursor.fetchall()

    cursor.close()

    return render_template(
        "reports.html",
        departments=departments
    )    
@app.route("/report_department")
@login_required
def report_department():

    cursor = db.cursor()

    cursor.execute("""
        SELECT DISTINCT department
        FROM students
        ORDER BY department ASC
    """)

    departments = cursor.fetchall()

    print("========== DEBUG ==========")
    print("Departments:", departments)
    print("===========================")

    return render_template(
        "report_department.html",
        departments=departments
    )
@app.route("/report_year")
@login_required
def report_year():

    return render_template("report_year.html")
@app.route("/report_department_year")
@login_required
def report_department_year():

    cursor = db.cursor()

    cursor.execute("""
        SELECT DISTINCT department
        FROM students
        ORDER BY department ASC
    """)

    departments = cursor.fetchall()

    return render_template(
        "report_department_year.html",
        departments=departments
    )
@app.route("/print_department", methods=["POST"])
@login_required
def print_department():

    department = request.form["department"]

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            level,
            cgpa,
            prediction
        FROM students
        WHERE department=%s
        ORDER BY level ASC, student_name ASC
    """, (department,))

    students = cursor.fetchall()

    filename = f"{department}_Report.pdf"

    pdf = SimpleDocTemplate(
        filename,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER

    heading = styles["Heading2"]
    heading.alignment = TA_CENTER

    story = []

    story.append(
        Paragraph(
            "<b>MADONNA UNIVERSITY, NIGERIA</b>",
            title
        )
    )

    story.append(
        Paragraph(
            "Student Dropout Prediction System",
            heading
        )
    )

    story.append(
        Paragraph(
            f"<b>Department Report</b>",
            heading
        )
    )

    story.append(
        Paragraph(
            f"<b>Department:</b> {department}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Date Generated:</b> {datetime.now().strftime('%d %B %Y')}",
            styles["Normal"]
        )
    )

    story.append(Paragraph("<br/>", styles["Normal"]))

    data = [[
        "S/N",
        "Registration No",
        "Student Name",
        "Year",
        "CGPA",
        "Prediction"
    ]]

    high = 0
    low = 0

    for i, row in enumerate(students, start=1):

        year = int(row[2]) // 100

        if "HIGH" in row[4]:
            high += 1
        else:
            low += 1

        data.append([
            i,
            row[0],
            row[1],
            f"Year {year}",
            row[3],
            row[4]
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,1), (-1,-1), colors.beige),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BOTTOMPADDING", (0,0), (-1,0), 10),
    ]))

    story.append(table)

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(
        Paragraph(
            f"<b>Total Students:</b> {len(students)}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>High Risk Students:</b> {high}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Low Risk Students:</b> {low}",
            styles["Normal"]
        )
    )

    pdf.build(story)

    return send_file(
        filename,
        as_attachment=True
    )
# ==========================================================
# DEPARTMENT STUDENTS - EXCEL
# ==========================================================

@app.route("/export_department", methods=["GET", "POST"])
@login_required
def export_department():

    department = request.values.get("department")

    if not department:
        return "Department was not selected.", 400

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE department = %s
        ORDER BY level ASC, student_name ASC
    """, (department,))

    records = cursor.fetchall()

    columns = [
        "Student ID",
        "Student Name",
        "Age",
        "Gender",
        "Department",
        "Level",
        "Attendance",
        "CGPA",
        "Failed Courses",
        "LMS Engagement",
        "Financial Stress",
        "Prediction"
    ]

    df = pd.DataFrame(records, columns=columns)

    filename = "Department_Students.xlsx"

    df.to_excel(filename, index=False)

    return send_file(
        filename,
        as_attachment=True
    )
@app.route("/print_department_year", methods=["POST"])
@login_required
def print_department_year():

    department = request.form["department"]
    level = int(request.form["level"])

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            level,
            cgpa,
            prediction
        FROM students
        WHERE department=%s
        AND level=%s
        ORDER BY student_name ASC
    """, (department, level))

    students = cursor.fetchall()

    filename = f"{department}_Year_{level//100}_Report.pdf"

    pdf = SimpleDocTemplate(filename, pagesize=letter)

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = 1

    heading = styles["Heading2"]
    heading.alignment = 1

    story = []

    story.append(Paragraph("<b>MADONNA UNIVERSITY, NIGERIA</b>", title))
    story.append(Paragraph("Student Dropout Prediction System", heading))
    story.append(Paragraph("<b>Department + Year Report</b>", heading))
    story.append(Paragraph(f"<b>Department:</b> {department}", styles["Normal"]))
    story.append(Paragraph(f"<b>Year:</b> Year {level//100}", styles["Normal"]))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %B %Y')}", styles["Normal"]))
    story.append(Paragraph("<br/>", styles["Normal"]))

    data = [[
        "S/N",
        "Registration No",
        "Student Name",
        "CGPA",
        "Prediction"
    ]]

    high = 0
    low = 0

    for i, row in enumerate(students, start=1):

        if "HIGH" in row[4]:
            high += 1
        else:
            low += 1

        data.append([
            i,
            row[0],
            row[1],
            row[3],
            row[4]
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.darkblue),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("BACKGROUND",(0,1),(-1,-1),colors.beige),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
    ]))

    story.append(table)

    story.append(Paragraph("<br/>", styles["Normal"]))
    story.append(Paragraph(f"<b>Total Students:</b> {len(students)}", styles["Normal"]))
    story.append(Paragraph(f"<b>High Risk Students:</b> {high}", styles["Normal"]))
    story.append(Paragraph(f"<b>Low Risk Students:</b> {low}", styles["Normal"]))

    pdf.build(story)

    return send_file(filename, as_attachment=True)
@app.route("/export_department_year", methods=["POST"])
@login_required
def export_department_year():

    department = request.form["department"]
    level = int(request.form["level"])

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE department=%s
        AND level=%s
        ORDER BY student_name ASC
    """, (department, level))

    records = cursor.fetchall()

    columns = [
        "Student ID",
        "Student Name",
        "Age",
        "Gender",
        "Department",
        "Level",
        "Attendance",
        "CGPA",
        "Failed Courses",
        "LMS Engagement",
        "Financial Stress",
        "Prediction"
    ]

    df = pd.DataFrame(records, columns=columns)

    filename = f"{department}_Year_{level//100}_Report.xlsx"

    df.to_excel(filename, index=False)

    return send_file(
        filename,
        as_attachment=True
    )

@app.route("/print_year_report", methods=["POST"])
@login_required
def print_year_report():

    level = int(request.form["level"])

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            department,
            cgpa,
            prediction
        FROM students
        WHERE level=%s
        ORDER BY department ASC, student_name ASC
    """, (level,))

    students = cursor.fetchall()

    filename = f"Year_{level//100}_Report.pdf"

    pdf = SimpleDocTemplate(filename, pagesize=letter)

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER

    heading = styles["Heading2"]
    heading.alignment = TA_CENTER

    story = []

    story.append(Paragraph("<b>MADONNA UNIVERSITY, NIGERIA</b>", title))
    story.append(Paragraph("Student Dropout Prediction System", heading))
    story.append(Paragraph("<b>YEAR REPORT</b>", heading))
    story.append(Paragraph(f"<b>Year:</b> Year {level//100}", styles["Normal"]))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %B %Y')}", styles["Normal"]))
    story.append(Paragraph("<br/>", styles["Normal"]))

    data = [[
        "S/N",
        "Registration No",
        "Student Name",
        "Department",
        "CGPA",
        "Prediction"
    ]]

    high = 0
    low = 0

    for i, row in enumerate(students, start=1):

        if "HIGH" in row[4]:
            high += 1
        else:
            low += 1

        data.append([
            i,
            row[0],
            row[1],
            row[2],
            row[3],
            row[4]
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,1), (-1,-1), colors.beige),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))

    story.append(table)

    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph(f"<b>Total Students:</b> {len(students)}", styles["Normal"]))
    story.append(Paragraph(f"<b>High Risk Students:</b> {high}", styles["Normal"]))
    story.append(Paragraph(f"<b>Low Risk Students:</b> {low}", styles["Normal"]))

    pdf.build(story)

    return send_file(
        filename,
        as_attachment=True
    )
@app.route("/export_year_report", methods=["POST"])
@login_required
def export_year_report():

    level = int(request.form["level"])

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE level = %s
        ORDER BY department ASC, student_name ASC
    """, (level,))

    students = cursor.fetchall()

    columns = [
        "Registration No",
        "Student Name",
        "Department",
        "Year",
        "Attendance",
        "CGPA",
        "Failed Courses",
        "LMS Engagement",
        "Financial Stress",
        "Prediction"
    ]

    data = []

    for row in students:

        data.append([
            row[0],
            row[1],
            row[2],
            f"Year {int(row[3]) // 100}",
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9]
        ])

    df = pd.DataFrame(data, columns=columns)

    filename = f"Year_{level // 100}_Students_Report.xlsx"

    # Create Excel file
    df.to_excel(
        filename,
        index=False,
        engine="openpyxl"
    )

    print("========== EXCEL REPORT ==========")
    print("Year:", level // 100)
    print("Students:", len(students))
    print("Excel file:", filename)
    print("==================================")

    return send_file(
        filename,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
@app.route("/export_pdf")
@login_required
def export_pdf():

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            department,
            cgpa,
            prediction
        FROM students
    """)

    records = cursor.fetchall()

    filename = "Student_Records.pdf"

    pdf = SimpleDocTemplate(filename, pagesize=letter)

    data = [
        ["Student ID", "Student Name", "Department", "CGPA", "Prediction"]
    ]

    for row in records:
        data.append(list(row))

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10)
    ]))

    pdf.build([table])

    return send_file(
        filename,
        as_attachment=True
    )
@app.route("/print_all_students", methods=["GET"])
@login_required
def print_all_students():

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        ORDER BY department ASC, level ASC, student_name ASC
    """)

    students = cursor.fetchall()

    filename = "All_Students_Report.pdf"

    pdf = SimpleDocTemplate(
        filename,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER

    heading = styles["Heading2"]
    heading.alignment = TA_CENTER

    story = []

    story.append(
        Paragraph(
            "<b>MADONNA UNIVERSITY, NIGERIA</b>",
            title
        )
    )

    story.append(
        Paragraph(
            "Student Dropout Prediction System",
            heading
        )
    )

    story.append(
        Paragraph(
            "<b>ALL STUDENTS REPORT</b>",
            heading
        )
    )

    story.append(
        Paragraph(
            f"<b>Date Generated:</b> "
            f"{datetime.now().strftime('%d %B %Y')}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph("<br/>", styles["Normal"])
    )

    data = [[
        "S/N",
        "Registration No",
        "Student Name",
        "Department",
        "Year",
        "CGPA",
        "Attendance",
        "Prediction"
    ]]

    high = 0
    low = 0

    for i, row in enumerate(students, start=1):

        level = int(row[5])
        year = level // 100

        prediction = row[11]

        if "HIGH" in prediction:
            high += 1
        else:
            low += 1

        data.append([
            i,
            row[0],
            row[1],
            row[4],
            f"Year {year}",
            row[7],
            row[6],
            prediction
        ])

    table = Table(
        data,
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ])
    )

    story.append(table)

    story.append(
        Paragraph("<br/>", styles["Normal"])
    )

    story.append(
        Paragraph(
            f"<b>Total Students:</b> {len(students)}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>High Risk Students:</b> {high}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Low Risk Students:</b> {low}",
            styles["Normal"]
        )
    )

    pdf.build(story)

    return send_file(
        filename,
        as_attachment=True
    )
# ==========================================================
# HIGH RISK STUDENTS - PDF
# ==========================================================

@app.route("/print_high_risk", methods=["GET"])
@login_required
def print_high_risk():

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE prediction = 'HIGH RISK OF DROPOUT'
        ORDER BY department ASC, level ASC, student_name ASC
    """)

    students = cursor.fetchall()

    filename = "High_Risk_Students_Report.pdf"

    pdf = SimpleDocTemplate(
        filename,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER

    heading = styles["Heading2"]
    heading.alignment = TA_CENTER

    story = []

    story.append(
        Paragraph(
            "<b>MADONNA UNIVERSITY, NIGERIA</b>",
            title
        )
    )

    story.append(
        Paragraph(
            "Student Dropout Prediction System",
            heading
        )
    )

    story.append(
        Paragraph(
            "<b>HIGH RISK STUDENTS REPORT</b>",
            heading
        )
    )

    story.append(
        Paragraph(
            f"<b>Date Generated:</b> "
            f"{datetime.now().strftime('%d %B %Y')}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph("<br/>", styles["Normal"])
    )

    data = [[
        "S/N",
        "Registration No",
        "Student Name",
        "Department",
        "Year",
        "CGPA",
        "Attendance",
        "Failed Courses"
    ]]

    for i, row in enumerate(students, start=1):

        year = int(row[5]) // 100

        data.append([
            i,
            row[0],
            row[1],
            row[4],
            f"Year {year}",
            row[7],
            row[6],
            row[8]
        ])

    table = Table(
        data,
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkred),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("BACKGROUND", (0, 1), (-1, -1), colors.mistyrose),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ])
    )

    story.append(table)

    story.append(
        Paragraph("<br/>", styles["Normal"])
    )

    story.append(
        Paragraph(
            f"<b>Total High Risk Students:</b> {len(students)}",
            styles["Normal"]
        )
    )

    pdf.build(story)

    return send_file(
        filename,
        as_attachment=True
    )


# ==========================================================
# LOW RISK STUDENTS - PDF
# ==========================================================

@app.route("/print_low_risk", methods=["GET"])
@login_required
def print_low_risk():

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE prediction = 'LOW RISK OF DROPOUT'
        ORDER BY department ASC, level ASC, student_name ASC
    """)

    students = cursor.fetchall()

    filename = "Low_Risk_Students_Report.pdf"

    pdf = SimpleDocTemplate(
        filename,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER

    heading = styles["Heading2"]
    heading.alignment = TA_CENTER

    story = []

    story.append(
        Paragraph(
            "<b>MADONNA UNIVERSITY, NIGERIA</b>",
            title
        )
    )

    story.append(
        Paragraph(
            "Student Dropout Prediction System",
            heading
        )
    )

    story.append(
        Paragraph(
            "<b>LOW RISK STUDENTS REPORT</b>",
            heading
        )
    )

    story.append(
        Paragraph(
            f"<b>Date Generated:</b> "
            f"{datetime.now().strftime('%d %B %Y')}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph("<br/>", styles["Normal"])
    )

    data = [[
        "S/N",
        "Registration No",
        "Student Name",
        "Department",
        "Year",
        "CGPA",
        "Attendance",
        "Failed Courses"
    ]]

    for i, row in enumerate(students, start=1):

        year = int(row[5]) // 100

        data.append([
            i,
            row[0],
            row[1],
            row[4],
            f"Year {year}",
            row[7],
            row[6],
            row[8]
        ])

    table = Table(
        data,
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("BACKGROUND", (0, 1), (-1, -1), colors.honeydew),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ])
    )

    story.append(table)

    story.append(
        Paragraph("<br/>", styles["Normal"])
    )

    story.append(
        Paragraph(
            f"<b>Total Low Risk Students:</b> {len(students)}",
            styles["Normal"]
        )
    )

    pdf.build(story)

    return send_file(
        filename,
        as_attachment=True
    )
# ==========================================================
# HIGH RISK STUDENTS - EXCEL
# ==========================================================

@app.route("/export_high_risk")
@login_required
def export_high_risk():

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE prediction = 'HIGH RISK OF DROPOUT'
        ORDER BY department ASC, level ASC, student_name ASC
    """)

    students = cursor.fetchall()

    columns = [
        "Student ID",
        "Student Name",
        "Age",
        "Gender",
        "Department",
        "Level",
        "Attendance",
        "CGPA",
        "Failed Courses",
        "LMS Engagement",
        "Financial Stress",
        "Prediction"
    ]

    df = pd.DataFrame(students, columns=columns)

    filename = "High_Risk_Students.xlsx"

    df.to_excel(filename, index=False)

    return send_file(
        filename,
        as_attachment=True
    )


# ==========================================================
# LOW RISK STUDENTS - EXCEL
# ==========================================================

@app.route("/export_low_risk")
@login_required
def export_low_risk():

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE prediction = 'LOW RISK OF DROPOUT'
        ORDER BY department ASC, level ASC, student_name ASC
    """)

    students = cursor.fetchall()

    columns = [
        "Student ID",
        "Student Name",
        "Age",
        "Gender",
        "Department",
        "Level",
        "Attendance",
        "CGPA",
        "Failed Courses",
        "LMS Engagement",
        "Financial Stress",
        "Prediction"
    ]

    df = pd.DataFrame(students, columns=columns)

    filename = "Low_Risk_Students.xlsx"

    df.to_excel(filename, index=False)

    return send_file(
        filename,
        as_attachment=True
    )
# ==========================================================
# FILTERED HIGH / LOW RISK STUDENTS - PDF
# ==========================================================

@app.route("/print_risk_filtered", methods=["POST"])
@login_required
def print_risk_filtered():

    risk = request.form.get("risk")
    department = request.form.get("department")
    level = request.form.get("level")

    # -----------------------------
    # Validate risk type
    # -----------------------------
    if risk not in ["HIGH", "LOW"]:
        return "Invalid risk type", 400

    # -----------------------------
    # Determine prediction value
    # -----------------------------
    if risk == "HIGH":
        prediction = "HIGH RISK OF DROPOUT"
        risk_title = "HIGH RISK STUDENTS REPORT"
        header_color = colors.darkred
        body_color = colors.mistyrose
    else:
        prediction = "LOW RISK OF DROPOUT"
        risk_title = "LOW RISK STUDENTS REPORT"
        header_color = colors.darkgreen
        body_color = colors.honeydew

    # -----------------------------
    # Build SQL query
    # -----------------------------
    query = """
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE prediction = %s
    """

    params = [prediction]

    # Department filter
    if department:
        query += " AND department = %s"
        params.append(department)

    # Level filter
    if level:
        query += " AND level = %s"
        params.append(level)

    query += """
        ORDER BY department ASC, level ASC, student_name ASC
    """

    cursor = db.cursor()

    cursor.execute(query, tuple(params))

    students = cursor.fetchall()

    cursor.close()

    # -----------------------------
    # Filename
    # -----------------------------
    filename = f"{risk}_Risk_Filtered_Report.pdf"

    # -----------------------------
    # PDF
    # -----------------------------
    pdf = SimpleDocTemplate(
        filename,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER

    heading = styles["Heading2"]
    heading.alignment = TA_CENTER

    story = []

    story.append(
        Paragraph(
            "<b>MADONNA UNIVERSITY, NIGERIA</b>",
            title
        )
    )

    story.append(
        Paragraph(
            "Student Dropout Prediction System",
            heading
        )
    )

    story.append(
        Paragraph(
            f"<b>{risk_title}</b>",
            heading
        )
    )

    # -----------------------------
    # Filter information
    # -----------------------------

    filter_text = "<b>Filters:</b> "

    if department:
        filter_text += f"Department: {department} | "
    else:
        filter_text += "Department: All Departments | "

    if level:
        filter_text += f"Year: {int(level) // 100}"
    else:
        filter_text += "Year: All Levels"

    story.append(
        Paragraph(
            filter_text,
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Date Generated:</b> "
            f"{datetime.now().strftime('%d %B %Y')}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            "<br/>",
            styles["Normal"]
        )
    )

    # -----------------------------
    # Table
    # -----------------------------

    data = [[
        "S/N",
        "Registration No",
        "Student Name",
        "Department",
        "Year",
        "CGPA",
        "Attendance",
        "Failed Courses"
    ]]

    for i, row in enumerate(students, start=1):

        year = int(row[5]) // 100

        data.append([
            i,
            row[0],
            row[1],
            row[4],
            f"Year {year}",
            row[7],
            row[6],
            row[8]
        ])

    table = Table(
        data,
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("BACKGROUND", (0, 1), (-1, -1), body_color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ])
    )

    story.append(table)

    story.append(
        Paragraph(
            "<br/>",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Total {risk.title()} Students:</b> "
            f"{len(students)}",
            styles["Normal"]
        )
    )

    pdf.build(story)

    return send_file(
        filename,
        as_attachment=True
    )


# ==========================================================
# FILTERED HIGH / LOW RISK STUDENTS - EXCEL
# ==========================================================

@app.route("/export_risk_filtered", methods=["POST"])
@login_required
def export_risk_filtered():

    risk = request.form.get("risk")
    department = request.form.get("department")
    level = request.form.get("level")

    # -----------------------------
    # Validate risk type
    # -----------------------------
    if risk not in ["HIGH", "LOW"]:
        return "Invalid risk type", 400

    # -----------------------------
    # Prediction value
    # -----------------------------
    if risk == "HIGH":
        prediction = "HIGH RISK OF DROPOUT"
    else:
        prediction = "LOW RISK OF DROPOUT"

    # -----------------------------
    # SQL query
    # -----------------------------
    query = """
        SELECT
            student_id,
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction
        FROM students
        WHERE prediction = %s
    """

    params = [prediction]

    # Department
    if department:
        query += " AND department = %s"
        params.append(department)

    # Level
    if level:
        query += " AND level = %s"
        params.append(level)

    query += """
        ORDER BY department ASC, level ASC, student_name ASC
    """

    cursor = db.cursor()

    cursor.execute(
        query,
        tuple(params)
    )

    students = cursor.fetchall()

    cursor.close()

    # -----------------------------
    # Excel
    # -----------------------------

    columns = [
        "Student ID",
        "Student Name",
        "Age",
        "Gender",
        "Department",
        "Level",
        "Attendance",
        "CGPA",
        "Failed Courses",
        "LMS Engagement",
        "Financial Stress",
        "Prediction"
    ]

    df = pd.DataFrame(
        students,
        columns=columns
    )

    filename = f"{risk}_Risk_Filtered_Report.xlsx"

    df.to_excel(
        filename,
        index=False
    )

    return send_file(
        filename,
        as_attachment=True
    )
# ==========================
# Delete Student
# ==========================

@app.route("/delete/<int:id>")
@login_required
def delete(id):

    cursor.execute(
        "DELETE FROM students WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect(url_for("students"))


@app.route("/delete_selected", methods=["POST"])
@login_required
def delete_selected():

    selected = request.form.getlist("selected_students")

    if selected:

        sql = """
        DELETE FROM students
        WHERE id IN (%s)
        """ % ",".join(["%s"] * len(selected))

        cursor.execute(sql, selected)

        db.commit()

    return redirect(url_for("students"))
# ==========================
# Edit Student
# ==========================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):

    if request.method == "POST":
        print(request.form.to_dict())        

        student_name = request.form.get("student_name")
        age = int(request.form.get("age"))
        gender = request.form.get("gender")
        department = request.form.get("department")
        level = int(request.form.get("level"))
        attendance = float(request.form.get("attendance"))
        cgpa = float(request.form.get("cgpa"))
        failed_courses = int(request.form.get("failed_courses"))
        lms_engagement = request.form.get("lms_engagement")
        financial_stress = request.form.get("financial_stress")

        gender_encoded = gender_encoder.transform([gender])[0]
        department_encoded = department_encoder.transform([department])[0]
        lms_encoded = lms_encoder.transform([lms_engagement])[0]
        financial_encoded = financial_encoder.transform([financial_stress])[0]

        X = pd.DataFrame([{
            "Age": age,
            "Gender": gender_encoded,
            "Department": department_encoded,
            "Level": level,
            "Attendance": attendance,
            "CGPA": cgpa,
            "Failed_Courses": failed_courses,
            "LMS_Engagement": lms_encoded,
            "Financial_Stress": financial_encoded
        }])

        prediction = model.predict(X)[0]

        if prediction == 1:
            prediction_text = "HIGH RISK OF DROPOUT"
        else:
            prediction_text = "LOW RISK OF DROPOUT"

        sql = """
        UPDATE students
        SET
            student_name=%s,
            age=%s,
            gender=%s,
            department=%s,
            level=%s,
            attendance=%s,
            cgpa=%s,
            failed_courses=%s,
            lms_engagement=%s,
            financial_stress=%s,
            prediction=%s
        WHERE id=%s
        """

        values = (
            student_name,
            age,
            gender,
            department,
            level,
            attendance,
            cgpa,
            failed_courses,
            lms_engagement,
            financial_stress,
            prediction_text,
            id
        )

        cursor.execute(sql, values)
        db.commit()

        return redirect(url_for("students"))

    cursor.execute("SELECT * FROM students WHERE id=%s", (id,))
    student = cursor.fetchone()

    print("Student =", student)

    if student is None:
        return "Student not found!"

    return render_template(
        "edit_student.html",
        student=student
    )

@app.route("/download")
@login_required
def download():
    return send_file(
        "prediction_results.csv",
        as_attachment=True
    )
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

@app.route("/model_performance")
@login_required
def model_performance():

    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        confusion_matrix
    )
    from sklearn.model_selection import train_test_split

    # Load dataset
    df = pd.read_csv("student_dropout_dataset.csv")

    # Features and target
    X = df.drop(columns=["Student_ID", "Dropout"])
    y = df["Dropout"]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    # Predict
    y_pred = model.predict(X_test)

    # Metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

        # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)

    # ==========================
    # Create Confusion Matrix Image
    # ==========================

    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    disp.plot(cmap="Blues")
    plt.title("Confusion Matrix")
    plt.savefig("static/confusion_matrix.png")
    plt.close()

    # ==========================
    # Create ROC Curve Image
    # ==========================

    y_prob = model.predict_proba(X_test)[:, 1]

    fpr, tpr, _ = roc_curve(y_test, y_prob)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color="blue", label=f"AUC = {roc_auc:.2f}")
    plt.plot([0, 1], [0, 1], linestyle="--", color="red")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.legend(loc="lower right")
    plt.grid(True)

    plt.savefig("static/roc_curve.png")
    plt.close()

    return render_template(
        "model_performance.html",
        accuracy=round(accuracy * 100, 2),
        precision=round(precision * 100, 2),
        recall=round(recall * 100, 2),
        f1_score=round(f1 * 100, 2),
        cm=cm
    )
   

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        username = request.form["username"]

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        if user:

            # Generate 6-digit code
            code = str(random.randint(100000, 999999))

            expiry = datetime.now() + timedelta(minutes=10)

            cursor.execute(
                """
                UPDATE users
                SET reset_code=%s,
                    reset_expiry=%s
                WHERE username=%s
                """,
                (code, expiry, username)
            )

            db.commit()

            print(f"Verification Code for {username}: {code}")

            return redirect(url_for("reset_password"))

        return render_template(
            "forgot_password.html",
            error="Username not found."
        )
    return render_template("forgot_password.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":

        username = request.form["username"]
        code = request.form["code"]
        password = request.form["password"]

        cursor.execute("""
            SELECT reset_code, reset_expiry
            FROM users
            WHERE username=%s
        """, (username,))

        result = cursor.fetchone()

        if result is None:
            return render_template(
                "reset_password.html",
                error="Invalid username."
            )

        db_code = result[0]
        db_expiry = result[1]

        # Check verification code
        if db_code != code:
            return render_template(
                "reset_password.html",
                error="Invalid verification code."
            )

        # Check expiry
        if datetime.now() > db_expiry:
            return render_template(
                "reset_password.html",
                error="Verification code has expired."
            )

        # Update password
        cursor.execute("""
            UPDATE users
            SET password=%s,
                reset_code=NULL,
                reset_expiry=NULL
            WHERE username=%s
        """, (password, username))

        db.commit()

        return redirect(url_for("login"))

    return render_template("reset_password.html")
if __name__ == "__main__":
    app.run(debug=True)
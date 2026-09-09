from app import cursor

student_id = "BFN/2026/0037"

cursor.execute("""
    SELECT
        student_id,
        student_name,
        level,
        attendance,
        cgpa,
        failed_courses,
        lms_engagement,
        financial_stress,
        prediction
    FROM students
    WHERE student_id = %s
""", (student_id,))

rows = cursor.fetchall()

print("\nDUPLICATE STUDENT RECORDS:")
print("==========================")

for row in rows:
    print(row)
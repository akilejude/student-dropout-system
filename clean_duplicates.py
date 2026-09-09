from app import db, cursor

print("Checking for exact duplicate student records...")

cursor.execute("""
    DELETE s1
    FROM students s1
    INNER JOIN students s2
        ON s1.student_id = s2.student_id
        AND s1.student_name = s2.student_name
        AND s1.age = s2.age
        AND s1.gender = s2.gender
        AND s1.department = s2.department
        AND s1.level = s2.level
        AND s1.attendance = s2.attendance
        AND s1.cgpa = s2.cgpa
        AND s1.failed_courses = s2.failed_courses
        AND s1.lms_engagement = s2.lms_engagement
        AND s1.financial_stress = s2.financial_stress
        AND s1.prediction = s2.prediction
        AND s1.id > s2.id
""")

db.commit()

cursor.execute("SELECT COUNT(*) FROM students")
total = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT student_id
        FROM students
        GROUP BY student_id
        HAVING COUNT(*) > 1
    ) AS duplicates
""")

duplicate_ids = cursor.fetchone()[0]

print()
print("==============================")
print("DUPLICATE CLEANUP COMPLETE")
print("==============================")
print("Total database records:", total)
print("Student IDs still duplicated:", duplicate_ids)
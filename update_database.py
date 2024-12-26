import sqlite3

DATABASE = "attendance.db"  # Replace this with your database file name

# Add 'classroom' column if it doesn't exist
with sqlite3.connect(DATABASE) as conn:
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN classroom TEXT DEFAULT ''")
        print("Classroom column added successfully.")
    except sqlite3.OperationalError:
        print("Classroom column already exists.")
    conn.commit()

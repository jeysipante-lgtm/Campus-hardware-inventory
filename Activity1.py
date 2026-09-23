import sqlite3


# ======================================================
# 1. DATABASE SETUP
# ======================================================

def init_db():
    """Connect to SQLite and create the 'experiments' table if it doesn't exist."""
    conn = sqlite3.connect("lab_tracker.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        student_id TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


# ======================================================
# 2. CORE CRUD FUNCTIONS
# ======================================================

def add_experiment():
    """Prompt user for details and insert a new record into the database."""
    print("\n--- ADD NEW EXPERIMENT ---")
    title = input("Enter Experiment Title: ").strip()
    student_id = input("Enter Student ID: ").strip()

    print("Status Options: [1] Pending [2] In Progress [3] Completed")
    status_choice = input("Select Status (1-3): ").strip()

    status_map = {"1": "Pending", "2": "In Progress", "3": "Completed"}
    status = status_map.get(status_choice, "Pending")

    if not title or not student_id:
        print("[ERROR] Title and Student ID cannot be empty!\n")
        return

    conn = sqlite3.connect("lab_tracker.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO experiments (title, student_id, status) VALUES (?, ?, ?)",
        (title, student_id, status)
    )
    conn.commit()
    conn.close()

    print(f"[SUCCESS] Saved '{title}' to database!\n")


def view_experiments():
    """Fetch and print all recorded experiments in a formatted table layout."""
    conn = sqlite3.connect("lab_tracker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experiments")
    rows = cursor.fetchall()
    conn.close()

    print("\n" + "=" * 70)
    print(f"{'ID':<5} | {'Student ID':<12} | {'Experiment Title':<28} | {'Status':<12}")
    print("=" * 70)

    if not rows:
        print(" No records found in database.")
    else:
        for row in rows:
            # row[0]=id, row[1]=title, row[2]=student_id, row[3]=status
            print(f"{row[0]:<5} | {row[2]:<12} | {row[1]:<28} | {row[3]:<12}")

    print("=" * 70 + "\n")


def update_status():
    """Prompt for a record ID and update its status in the database."""
    view_experiments()
    exp_id = input("Enter the ID of the experiment to update: ").strip()

    if not exp_id.isdigit():
        print("[ERROR] Please enter a valid numerical ID!\n")
        return

    print("\nSelect New Status:")
    print("1. Pending")
    print("2. In Progress")
    print("3. Completed")
    status_choice = input("Choice (1-3): ").strip()

    status_map = {"1": "Pending", "2": "In Progress", "3": "Completed"}
    new_status = status_map.get(status_choice)

    if not new_status:
        print("[ERROR] Invalid status selected!\n")
        return

    conn = sqlite3.connect("lab_tracker.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE experiments SET status = ? WHERE id = ?", (new_status, exp_id))

    # Check if any row was actually updated
    if cursor.rowcount == 0:
        print(f"[ERROR] No record found with ID {exp_id}.\n")
    else:
        conn.commit()
        print(f"[SUCCESS] Updated Experiment ID {exp_id} status to '{new_status}'!\n")

    conn.close()


def delete_experiment():
    """Prompt for a record ID and delete it from the database."""
    view_experiments()
    exp_id = input("Enter the ID of the experiment to DELETE: ").strip()

    if not exp_id.isdigit():
        print("[ERROR] Please enter a valid numerical ID!\n")
        return

    confirm = input(f"Are you sure you want to delete ID {exp_id}? (y/n): ").strip().lower()
    if confirm != 'y':
        print("[CANCELLED] Deletion aborted.\n")
        return

    conn = sqlite3.connect("lab_tracker.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM experiments WHERE id = ?", (exp_id,))

    if cursor.rowcount == 0:
        print(f"[ERROR] No record found with ID {exp_id}.\n")
    else:
        conn.commit()
        print(f"[SUCCESS] Removed Experiment ID {exp_id} from database!\n")

    conn.close()


# ======================================================
# 3. INTERACTIVE CLI MENU
# ======================================================

def main():
    init_db()
    while True:
        print("===== LAB TRACKER MENU =====")
        print("1. View Experiments")
        print("2. Add Experiment")
        print("3. Update Experiment Status")
        print("4. Delete Experiment")
        print("5. Exit")
        choice = input("Select an option (1-5): ").strip()

        if choice == "1":
            view_experiments()
        elif choice == "2":
            add_experiment()
        elif choice == "3":
            update_status()
        elif choice == "4":
            delete_experiment()
        elif choice == "5":
            print("Exiting Lab Tracker. Goodbye!")
            break
        else:
            print("[ERROR] Invalid choice. Please try again.\n")


if __name__ == "__main__":
    main()
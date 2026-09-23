import sqlite3
import bcrypt

def init_db():
    conn = sqlite3.connect("hardware_inventory.db")
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'USER',
            is_locked INTEGER DEFAULT 0
        )
    ''')

    # 2. Hardware Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hardware (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity >= 0),
            unit_price REAL NOT NULL CHECK(unit_price >= 0.0),
            status TEXT NOT NULL
        )
    ''')

    # 3. Borrow Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS borrow_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            student_number TEXT,
            item_id INTEGER NOT NULL,
            requested_quantity INTEGER NOT NULL DEFAULT 1,
            borrow_date TEXT,
            return_date TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING_BORROW',
            FOREIGN KEY(item_id) REFERENCES hardware(item_id)
        )
    ''')

    # 4. Reset Requests Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reset_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            new_password_hash TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'PENDING'
        )
    ''')

    # Insert default Admin Account if absent
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        hashed_admin_pw = bcrypt.hashpw("Admin123!".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("admin", "admin@campus.edu", hashed_admin_pw, "ADMIN")
        )

    # Populate Sample Hardware if table is empty
    cursor.execute("SELECT COUNT(*) FROM hardware")
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ("Arduino Uno R3", "Microcontrollers", 12, 450.00, "In Stock"),
            ("Raspberry Pi 4 (4GB)", "Single Board Computers", 3, 3200.00, "Low Stock"),
            ("Ultrasonic Sensor HC-SR04", "Sensors", 20, 85.00, "In Stock"),
            ("L298N Motor Driver", "Actuators & Drivers", 0, 150.00, "Out of Stock"),
            ("Breadboard (MB-102)", "Prototyping", 4, 120.00, "Low Stock")
        ]
        cursor.executemany(
            "INSERT INTO hardware (item_name, category, quantity, unit_price, status) VALUES (?, ?, ?, ?, ?)",
            sample_items
        )

    conn.commit()
    conn.close()
    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()
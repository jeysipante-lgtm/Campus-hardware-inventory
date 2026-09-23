import os
import re
import csv
import sqlite3
import logging
from datetime import datetime
import bcrypt
import tkinter as tk
from tkinter import ttk, messagebox
from pydantic import BaseModel, Field, field_validator, ValidationError

# ==========================================
# 1. LOGGING SETUP
# ==========================================
def setup_logger():
    log_dir = "app_logging"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        filename=os.path.join(log_dir, "app.log"),
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger("HardwareLogger")

logger = setup_logger()

# ==========================================
# 2. DATABASE INITIALIZATION
# ==========================================
DB_NAME = "hardware_inventory.db"

def init_db():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'USER',
                    is_locked INTEGER NOT NULL DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hardware (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reset_requests (
                    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL,
                    new_password_hash TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS borrow_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    item_id INTEGER NOT NULL,
                    borrow_date TEXT NOT NULL,
                    return_date TEXT,
                    status TEXT NOT NULL DEFAULT 'BORROWED',
                    FOREIGN KEY(item_id) REFERENCES hardware(item_id)
                )
            """)
            
            # Default Admin account creation
            cursor.execute("SELECT * FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                admin_pw = bcrypt.hashpw("Admin123!".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    ('admin', 'admin@campus.edu', admin_pw, 'ADMIN')
                )
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")

# ==========================================
# 3. SCHEMAS (DATA VALIDATION)
# ==========================================
class UserRegistrationSchema(BaseModel):
    username: str = Field(..., min_length=3)
    email: str
    password: str
    role: str = "USER"

    @field_validator('username')
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError('Username must be alphanumeric.')
        return v

    @field_validator('email')
    def validate_email(cls, v):
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, v):
            raise ValueError('Invalid email address format.')
        return v

    @field_validator('password')
    def validate_password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number.')
        if not re.search(r'[@#$%^&*!]', v):
            raise ValueError('Password must contain at least one special character (@#$%^&*!).')
        return v

class PasswordResetSchema(BaseModel):
    username: str
    email: str
    new_password: str

    @field_validator('email')
    def validate_email(cls, v):
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, v):
            raise ValueError('Invalid email address format.')
        return v

    @field_validator('new_password')
    def validate_password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number.')
        if not re.search(r'[@#$%^&*!]', v):
            raise ValueError('Password must contain at least one special character (@#$%^&*!).')
        return v

class HardwareItemSchema(BaseModel):
    item_name: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    quantity: int = Field(..., ge=0)
    unit_price: float = Field(..., ge=0.0)

# ==========================================
# 4. CONTROLLERS
# ==========================================
class AuthController:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.failed_attempts = {}

    def register(self, username, email, password, role="USER"):
        try:
            validated = UserRegistrationSchema(username=username, email=email, password=password, role=role)
            hashed_pw = bcrypt.hashpw(validated.password.encode('utf-8'), bcrypt.gensalt())

            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (validated.username, validated.email, hashed_pw.decode('utf-8'), validated.role)
                )
            logger.info(f"User registration successful for: '{validated.username}'")
            return True, "Registration successful."
        except ValidationError as e:
            msg = e.errors()[0]['msg']
            logger.warning(f"Registration validation failed: {msg}")
            return False, f"Validation Error: {msg}"
        except sqlite3.IntegrityError:
            msg = "Username or Email already exists."
            logger.warning(f"Registration failed: {msg}")
            return False, msg
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False, str(e)

    def login(self, username_or_email, password):
        if not username_or_email or not password:
            return False, "Fields cannot be empty.", None

        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT password_hash, username, role, is_locked FROM users WHERE username = ? OR email = ?",
                    (username_or_email, username_or_email)
                )
                row = cursor.fetchone()

            if row:
                pw_hash, actual_user, role, is_locked = row[0], row[1], row[2], row[3]

                if is_locked:
                    return False, "ACCOUNT_LOCKED", None

                if bcrypt.checkpw(password.encode('utf-8'), pw_hash.encode('utf-8')):
                    self.failed_attempts[actual_user] = 0
                    logger.info(f"User login successful: '{actual_user}' ({role})")
                    return True, "Login successful.", {"username": actual_user, "role": role}

                self.failed_attempts[actual_user] = self.failed_attempts.get(actual_user, 0) + 1
                attempts = self.failed_attempts[actual_user]

                if attempts >= 3:
                    with sqlite3.connect(self.db_name) as conn:
                        conn.cursor().execute("UPDATE users SET is_locked = 1 WHERE username = ?", (actual_user,))
                    logger.warning(f"Account locked due to 3 failed attempts: '{actual_user}'")
                    return False, "ACCOUNT_LOCKED", None

                return False, f"Invalid password. Attempt {attempts}/3.", None

        except Exception as e:
            logger.error(f"Login database error: {e}")

        return False, "Invalid username/email or password.", None

    def request_password_reset(self, username, email, new_password, confirm_password):
        if new_password != confirm_password:
            return False, "Password Security Error: Passwords do not match."

        try:
            validated = PasswordResetSchema(username=username, email=email, new_password=new_password)
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT email FROM users WHERE username = ?", (validated.username,))
                row = cursor.fetchone()

                if not row or row[0].lower() != validated.email.lower():
                    return False, "Validation Error: Username and registered Email address do not match."

                hashed_pw = bcrypt.hashpw(validated.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute(
                    "INSERT INTO reset_requests (username, email, new_password_hash, timestamp) VALUES (?, ?, ?, ?)",
                    (validated.username, validated.email, hashed_pw, now_str)
                )
            logger.info(f"Password reset request submitted for: '{validated.username}'")
            return True, f"Reset request submitted at {now_str}.\nOnce an Admin approves it, your account will unlock."

        except ValidationError as e:
            msg = e.errors()[0]['msg']
            return False, f"Password Security Error: Value error, {msg}"
        except Exception as e:
            logger.error(f"Reset request error: {e}")
            return False, str(e)

class InventoryController:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def compute_status(self, quantity: int) -> str:
        if quantity > 5:
            return "In Stock"
        elif 1 <= quantity <= 5:
            return "Low Stock"
        else:
            return "Out of Stock"

    def fetch_all(self, search_name="", category="ALL"):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                query = "SELECT item_id, item_name, category, quantity, unit_price, status FROM hardware WHERE 1=1"
                params = []
                
                if search_name:
                    query += " AND LOWER(item_name) LIKE LOWER(?)"
                    params.append(f"%{search_name}%")
                if category and category != "ALL":
                    query += " AND category = ?"
                    params.append(category)

                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error fetching inventory records: {e}")
            return []

    def get_categories(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT category FROM hardware")
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_total_valuation(self) -> float:
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(quantity * unit_price) FROM hardware")
                val = cursor.fetchone()[0]
                return val if val else 0.0
        except sqlite3.Error:
            return 0.0

    def add_item(self, item_name, category, quantity_str, price_str):
        try:
            qty = int(quantity_str)
            price = float(price_str)
            validated = HardwareItemSchema(item_name=item_name, category=category, quantity=qty, unit_price=price)
        except ValueError:
            return False, "Quantity must be an integer and Unit Price must be a valid number."
        except ValidationError as e:
            return False, f"Validation Error: {e.errors()[0]['msg']}"

        status = self.compute_status(validated.quantity)

        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT item_id FROM hardware WHERE LOWER(item_name) = LOWER(?)", (validated.item_name,))
                if cursor.fetchone():
                    return False, f"Item Name '{validated.item_name}' already exists."

                cursor.execute(
                    "INSERT INTO hardware (item_name, category, quantity, unit_price, status) VALUES (?, ?, ?, ?, ?)",
                    (validated.item_name, validated.category, validated.quantity, validated.unit_price, status)
                )
            return True, "Item added successfully."
        except sqlite3.Error as e:
            return False, f"Database operation failed: {e}"

    def delete_items(self, item_ids):
        if not item_ids:
            return False, "No items selected."
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                placeholders = ",".join("?" for _ in item_ids)
                cursor.execute(f"DELETE FROM hardware WHERE item_id IN ({placeholders})", item_ids)
                conn.commit()
            logger.info(f"Successfully deleted item IDs: {item_ids}")
            return True, f"Successfully deleted {len(item_ids)} item(s)."
        except sqlite3.Error as e:
            logger.error(f"Error deleting items: {e}")
            return False, f"Database delete operation failed: {e}"

    def borrow_item(self, username, item_id):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT quantity, item_name FROM hardware WHERE item_id = ?", (item_id,))
                row = cursor.fetchone()
                
                if not row:
                    return False, "Item not found."
                
                quantity, item_name = row[0], row[1]
                
                if quantity <= 0:
                    return False, f"Resource Conflict: '{item_name}' is currently out of stock."

                # Check duplicate checkout conflict
                cursor.execute(
                    "SELECT log_id FROM borrow_logs WHERE username = ? AND item_id = ? AND status = 'BORROWED'",
                    (username, item_id)
                )
                if cursor.fetchone():
                    return False, f"Resource Conflict: You already have an active checkout for '{item_name}'."

                new_qty = quantity - 1
                new_status = self.compute_status(new_qty)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute(
                    "UPDATE hardware SET quantity = ?, status = ? WHERE item_id = ?",
                    (new_qty, new_status, item_id)
                )
                cursor.execute(
                    "INSERT INTO borrow_logs (username, item_id, borrow_date, status) VALUES (?, ?, ?, 'BORROWED')",
                    (username, item_id, now_str)
                )
            logger.info(f"User '{username}' borrowed item ID {item_id}")
            return True, f"Successfully checked out '{item_name}'."
        except sqlite3.Error as e:
            logger.error(f"Error borrowing item: {e}")
            return False, f"Database error: {e}"

    def return_item(self, log_id):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT item_id, status FROM borrow_logs WHERE log_id = ?", (log_id,))
                row = cursor.fetchone()
                
                if not row or row[1] != 'BORROWED':
                    return False, "Invalid or already returned record."

                item_id = row[0]
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("SELECT quantity FROM hardware WHERE item_id = ?", (item_id,))
                qty_row = cursor.fetchone()
                if qty_row:
                    new_qty = qty_row[0] + 1
                    new_status = self.compute_status(new_qty)
                    cursor.execute(
                        "UPDATE hardware SET quantity = ?, status = ? WHERE item_id = ?",
                        (new_qty, new_status, item_id)
                    )

                cursor.execute(
                    "UPDATE borrow_logs SET status = 'RETURNED', return_date = ? WHERE log_id = ?",
                    (now_str, log_id)
                )
            logger.info(f"Returned item for borrow log ID {log_id}")
            return True, "Item returned successfully."
        except sqlite3.Error as e:
            logger.error(f"Error returning item: {e}")
            return False, f"Database error: {e}"

    def fetch_user_borrows(self, username, is_admin=False):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                if is_admin:
                    query = """
                        SELECT b.log_id, b.username, h.item_name, b.borrow_date, b.return_date, b.status 
                        FROM borrow_logs b 
                        JOIN hardware h ON b.item_id = h.item_id
                        ORDER BY b.log_id DESC
                    """
                    cursor.execute(query)
                else:
                    query = """
                        SELECT b.log_id, b.username, h.item_name, b.borrow_date, b.return_date, b.status 
                        FROM borrow_logs b 
                        JOIN hardware h ON b.item_id = h.item_id
                        WHERE b.username = ?
                        ORDER BY b.log_id DESC
                    """
                    cursor.execute(query, (username,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error fetching borrow logs: {e}")
            return []

    def export_to_csv(self, filename="inventory_report.csv"):
        try:
            items = self.fetch_all()
            with open(filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["ID", "Item Name", "Category", "Quantity", "Unit Price ($)", "Status"])
                writer.writerows(items)
            return True, f"Report exported to '{filename}'."
        except Exception as e:
            return False, f"Export failed: {e}"

class AdminController:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def fetch_pending_resets(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT request_id, username, email, timestamp, new_password_hash FROM reset_requests WHERE status = 'PENDING'"
                )
                return cursor.fetchall()
        except sqlite3.Error:
            return []

    def approve_resets(self, request_ids):
        count = 0
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                for req_id in request_ids:
                    cursor.execute(
                        "SELECT username, new_password_hash FROM reset_requests WHERE request_id = ?", (req_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        user, new_pw = row[0], row[1]
                        cursor.execute(
                            "UPDATE users SET password_hash = ?, is_locked = 0 WHERE username = ?", (new_pw, user)
                        )
                        cursor.execute("UPDATE reset_requests SET status = 'APPROVED' WHERE request_id = ?", (req_id,))
                        count += 1
            return True, f"Successfully approved & unlocked {count} request(s)."
        except sqlite3.Error as e:
            return False, f"Error approving requests: {e}"

    def reject_resets(self, request_ids):
        count = 0
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                for req_id in request_ids:
                    cursor.execute("UPDATE reset_requests SET status = 'REJECTED' WHERE request_id = ?", (req_id,))
                    count += 1
            return True, f"Successfully rejected {count} request(s)."
        except sqlite3.Error as e:
            return False, f"Error rejecting requests: {e}"

# ==========================================
# 5. VIEWS
# ==========================================

class AuthWindow:
    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success
        self.auth = AuthController()

        self.root.title("System Auth - Engineering Lab Tracking")
        self.root.geometry("450x480")
        self.root.resizable(False, False)

        tk.Label(self.root, text="Engineering Lab Asset Tracker", font=("Arial", 14, "bold")).pack(pady=10)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=5)

        self.tab_login = ttk.Frame(self.notebook)
        self.tab_register = ttk.Frame(self.notebook)
        self.tab_reset = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_login, text="Login")
        self.notebook.add(self.tab_register, text="Register")
        self.notebook.add(self.tab_reset, text="Reset Password")

        self.setup_login_tab()
        self.setup_register_tab()
        self.setup_reset_tab()

    def setup_login_tab(self):
        frame = self.tab_login
        
        tk.Label(frame, text="Username or Email:", font=("Arial", 9)).pack(anchor="w", padx=35, pady=(15, 2))
        self.login_user = tk.Entry(frame, width=35)
        self.login_user.pack(padx=35, pady=(0, 10))

        tk.Label(frame, text="Password:", font=("Arial", 9)).pack(anchor="w", padx=35, pady=(0, 2))
        self.login_pass = tk.Entry(frame, show="*", width=35)
        self.login_pass.pack(padx=35, pady=(0, 4))

        self.show_pass_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frame, text="Show Password", variable=self.show_pass_var, command=self.toggle_pass
        ).pack(anchor="w", padx=35, pady=(0, 15))

        tk.Button(
            frame, text="Login", command=self.handle_login,
            width=30, bg="#4CAF50", fg="white", font=("Arial", 10, "bold")
        ).pack(padx=35, pady=10)

    def toggle_pass(self):
        self.login_pass.config(show="" if self.show_pass_var.get() else "*")

    def handle_login(self):
        user_val = self.login_user.get().strip()
        pass_val = self.login_pass.get()

        success, msg, user_data = self.auth.login(user_val, pass_val)

        if success:
            self.on_login_success(user_data)
        elif msg == "ACCOUNT_LOCKED":
            messagebox.showerror(
                "Account Locked",
                "Account has been LOCKED due to 3 failed attempts.\nReset password to regain access."
            )
            self.notebook.select(self.tab_reset)
        else:
            messagebox.showerror("Login Error", msg)

    def setup_register_tab(self):
        frame = self.tab_register

        tk.Label(frame, text="Username:").pack(anchor="w", padx=35, pady=(10, 2))
        self.reg_user = tk.Entry(frame, width=35)
        self.reg_user.pack(padx=35, pady=(0, 5))

        tk.Label(frame, text="Email Address:").pack(anchor="w", padx=35, pady=(0, 2))
        self.reg_email = tk.Entry(frame, width=35)
        self.reg_email.pack(padx=35, pady=(0, 5))

        tk.Label(frame, text="Password:").pack(anchor="w", padx=35, pady=(0, 2))
        self.reg_pass = tk.Entry(frame, show="*", width=35)
        self.reg_pass.pack(padx=35, pady=(0, 5))

        tk.Label(frame, text="Select Role:").pack(anchor="w", padx=35, pady=(0, 2))
        self.reg_role = ttk.Combobox(frame, values=["USER", "ADMIN"], width=32, state="readonly")
        self.reg_role.set("USER")
        self.reg_role.pack(padx=35, pady=(0, 15))

        tk.Button(
            frame, text="Create Account", command=self.handle_register,
            width=30, bg="#2196F3", fg="white", font=("Arial", 10, "bold")
        ).pack(padx=35, pady=5)

    def handle_register(self):
        u = self.reg_user.get().strip()
        e = self.reg_email.get().strip()
        p = self.reg_pass.get()
        r = self.reg_role.get()

        success, msg = self.auth.register(u, e, p, r)
        if success:
            messagebox.showinfo("Success", "Account created successfully! You may now login.")
            self.notebook.select(self.tab_login)
        else:
            messagebox.showwarning("Registration Failed", msg)

    def setup_reset_tab(self):
        frame = self.tab_reset

        tk.Label(frame, text="Account Username:").pack(anchor="w", padx=35, pady=(10, 2))
        self.rst_user = tk.Entry(frame, width=35)
        self.rst_user.pack(padx=35, pady=(0, 5))

        tk.Label(frame, text="Registered Email:").pack(anchor="w", padx=35, pady=(0, 2))
        self.rst_email = tk.Entry(frame, width=35)
        self.rst_email.pack(padx=35, pady=(0, 5))

        tk.Label(frame, text="Desired New Password:").pack(anchor="w", padx=35, pady=(0, 2))
        self.rst_new_pass = tk.Entry(frame, show="*", width=35)
        self.rst_new_pass.pack(padx=35, pady=(0, 5))

        tk.Label(frame, text="Confirm New Password:").pack(anchor="w", padx=35, pady=(0, 2))
        self.rst_confirm_pass = tk.Entry(frame, show="*", width=35)
        self.rst_confirm_pass.pack(padx=35, pady=(0, 15))

        tk.Button(
            frame, text="Submit Reset Request", command=self.handle_reset,
            width=30, bg="#FF9800", fg="white", font=("Arial", 10, "bold")
        ).pack(padx=35, pady=5)

    def handle_reset(self):
        u = self.rst_user.get().strip()
        e = self.rst_email.get().strip()
        p1 = self.rst_new_pass.get()
        p2 = self.rst_confirm_pass.get()

        success, msg = self.auth.request_password_reset(u, e, p1, p2)
        if success:
            messagebox.showinfo("Request Submitted", msg)
            self.notebook.select(self.tab_login)
        else:
            messagebox.showerror("Reset Request Failed", msg)

class MainDashboardView:
    def __init__(self, root, user_data, on_logout):
        self.root = root
        self.user_data = user_data
        self.on_logout = on_logout
        self.inventory_ctrl = InventoryController()
        self.admin_ctrl = AdminController()

        role_tag = f"[{self.user_data['role']}]"
        self.root.title(f"Engineering Asset Tracking System ({self.user_data['role']} PANEL)")
        self.root.geometry("900x650")

        header = tk.Frame(self.root, bg="#2C3E50", pady=8)
        header.pack(fill="x")

        tk.Label(
            header, text=f"Logged in: {self.user_data['username']} {role_tag}",
            font=("Arial", 10, "bold"), bg="#2C3E50", fg="white"
        ).pack(side="left", padx=15)

        tk.Button(
            header, text="Logout", command=self.on_logout,
            bg="#E74C3C", fg="white", font=("Arial", 9, "bold")
        ).pack(side="right", padx=15)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_catalog = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_catalog, text="Equipment Catalog")

        self.tab_logbook = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_logbook, text="Digital Borrow Logbook")

        if self.user_data['role'] == 'ADMIN':
            self.tab_approvals = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_approvals, text="Admin Approvals")
            self.setup_approvals_tab()

        self.setup_catalog_tab()
        self.setup_logbook_tab()

    def setup_catalog_tab(self):
        frame = self.tab_catalog

        filter_frame = tk.LabelFrame(frame, text="Search & Filter Components", padx=10, pady=5)
        filter_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(filter_frame, text="Search Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_search = tk.Entry(filter_frame, width=20)
        self.entry_search.grid(row=0, column=1, padx=5, pady=5)
        self.entry_search.bind("<KeyRelease>", lambda e: self.load_catalog())

        tk.Label(filter_frame, text="Category:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.combo_cat = ttk.Combobox(filter_frame, width=18, state="readonly")
        self.combo_cat.grid(row=0, column=3, padx=5, pady=5)
        self.combo_cat.bind("<<ComboboxSelected>>", lambda e: self.load_catalog())

        self.lbl_valuation = tk.Label(
            frame, text="Total Asset Valuation: $0.00",
            font=("Arial", 11, "bold"), bg="#16A085", fg="white", pady=4
        )
        self.lbl_valuation.pack(fill="x", padx=10, pady=5)

        if self.user_data['role'] == 'ADMIN':
            form = tk.LabelFrame(frame, text="Add New Item", padx=10, pady=5)
            form.pack(fill="x", padx=10, pady=5)

            tk.Label(form, text="Name:").grid(row=0, column=0, sticky="w")
            self.add_name = tk.Entry(form, width=15)
            self.add_name.grid(row=0, column=1, padx=5, pady=2)

            tk.Label(form, text="Category:").grid(row=0, column=2, sticky="w")
            self.add_cat = tk.Entry(form, width=15)
            self.add_cat.grid(row=0, column=3, padx=5, pady=2)

            tk.Label(form, text="Qty:").grid(row=0, column=4, sticky="w")
            self.add_qty = tk.Entry(form, width=8)
            self.add_qty.grid(row=0, column=5, padx=5, pady=2)

            tk.Label(form, text="Price ($):").grid(row=0, column=6, sticky="w")
            self.add_price = tk.Entry(form, width=10)
            self.add_price.grid(row=0, column=7, padx=5, pady=2)

            tk.Button(
                form, text="Save Item", command=self.handle_add_item,
                bg="#27AE60", fg="white", font=("Arial", 9, "bold")
            ).grid(row=0, column=8, padx=10)

        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        self.tree_cat = ttk.Treeview(
            tree_frame,
            columns=("Select", "ID", "Name", "Category", "Qty", "Price", "Status"),
            show="headings",
            yscrollcommand=scroll_y.set
        )
        scroll_y.config(command=self.tree_cat.yview)
        scroll_y.pack(side="right", fill="y")

        self.tree_cat.heading("Select", text="[ ✓ ]")
        self.tree_cat.heading("ID", text="ID")
        self.tree_cat.heading("Name", text="Name")
        self.tree_cat.heading("Category", text="Category")
        self.tree_cat.heading("Qty", text="Qty")
        self.tree_cat.heading("Price", text="Price")
        self.tree_cat.heading("Status", text="Status")

        self.tree_cat.column("Select", width=40, anchor="center")
        self.tree_cat.column("ID", width=40, anchor="center")
        self.tree_cat.column("Name", width=200)
        self.tree_cat.column("Category", width=140)
        self.tree_cat.column("Qty", width=60, anchor="center")
        self.tree_cat.column("Price", width=90, anchor="e")
        self.tree_cat.column("Status", width=110, anchor="center")
        self.tree_cat.pack(fill="both", expand=True)

        self.tree_cat.bind("<Button-1>", self.on_checkbox_click)

        footer = tk.Frame(frame)
        footer.pack(fill="x", padx=10, pady=5)

        tk.Button(
            footer, text="Borrow Selected Equipment", command=self.handle_borrow_selected,
            bg="#2980B9", fg="white", font=("Arial", 9, "bold")
        ).pack(side="left", padx=5)

        tk.Button(
            footer, text="Export Inventory to CSV Report", command=self.handle_export_csv,
            bg="#8E44AD", fg="white", font=("Arial", 9, "bold")
        ).pack(side="right", padx=5)

        if self.user_data['role'] == 'ADMIN':
            tk.Button(
                footer, text="Delete Selected Items", command=self.handle_delete_selected,
                bg="#C0392B", fg="white", font=("Arial", 9, "bold")
            ).pack(side="right", padx=5)

        self.refresh_categories()
        self.load_catalog()

    def refresh_categories(self):
        cats = ["ALL"] + self.inventory_ctrl.get_categories()
        self.combo_cat['values'] = cats
        self.combo_cat.set("ALL")

    def load_catalog(self):
        for item in self.tree_cat.get_children():
            self.tree_cat.delete(item)

        search = self.entry_search.get().strip()
        cat = self.combo_cat.get()

        items = self.inventory_ctrl.fetch_all(search, cat)
        for row in items:
            self.tree_cat.insert("", "end", values=("☐", row[0], row[1], row[2], row[3], f"${row[4]:.2f}", row[5]))

        val = self.inventory_ctrl.get_total_valuation()
        self.lbl_valuation.config(text=f"Total Asset Valuation: ${val:,.2f}")

    def on_checkbox_click(self, event):
        region = self.tree_cat.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree_cat.identify_column(event.x)
            if column == "#1":
                item_id = self.tree_cat.identify_row(event.y)
                if item_id:
                    current_vals = list(self.tree_cat.item(item_id, "values"))
                    current_vals[0] = "☑" if current_vals[0] == "☐" else "☐"
                    self.tree_cat.item(item_id, values=current_vals)

    def get_selected_catalog_ids(self):
        selected_ids = []
        for item_id in self.tree_cat.get_children():
            vals = self.tree_cat.item(item_id, "values")
            if vals[0] == "☑":
                selected_ids.append(vals[1])
        return selected_ids

    def handle_borrow_selected(self):
        selected_ids = self.get_selected_catalog_ids()
        if not selected_ids:
            messagebox.showwarning("No Selection", "Please check/select an item to borrow.")
            return

        if len(selected_ids) > 1:
            messagebox.showwarning("Multiple Selection", "Please check only ONE item at a time for checkout.")
            return

        item_id = selected_ids[0]
        success, msg = self.inventory_ctrl.borrow_item(self.user_data['username'], item_id)
        if success:
            messagebox.showinfo("Checkout Confirmed", msg)
            self.load_catalog()
            self.load_logbook()
        else:
            messagebox.showerror("Conflict / Error", msg)

    def handle_delete_selected(self):
        selected_ids = self.get_selected_catalog_ids()
        if not selected_ids:
            messagebox.showwarning("No Selection", "Please check/select at least one item to delete.")
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to permanently delete {len(selected_ids)} item(s)?"
        )
        if confirm:
            success, msg = self.inventory_ctrl.delete_items(selected_ids)
            if success:
                messagebox.showinfo("Success", msg)
                self.refresh_categories()
                self.load_catalog()
            else:
                messagebox.showerror("Error", msg)

    def handle_add_item(self):
        n = self.add_name.get().strip()
        c = self.add_cat.get().strip()
        q = self.add_qty.get().strip()
        p = self.add_price.get().strip()

        success, msg = self.inventory_ctrl.add_item(n, c, q, p)
        if success:
            self.add_name.delete(0, tk.END)
            self.add_cat.delete(0, tk.END)
            self.add_qty.delete(0, tk.END)
            self.add_price.delete(0, tk.END)
            messagebox.showinfo("Success", msg)
            self.refresh_categories()
            self.load_catalog()
        else:
            messagebox.showerror("Add Item Error", msg)

    def handle_export_csv(self):
        success, msg = self.inventory_ctrl.export_to_csv()
        if success:
            messagebox.showinfo("Export Success", msg)
        else:
            messagebox.showerror("Export Failed", msg)

    def setup_logbook_tab(self):
        frame = self.tab_logbook

        tk.Label(
            frame, text="Automated Asset Logbook & Conflict Avoidance Record",
            font=("Arial", 11, "bold")
        ).pack(pady=10)

        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        self.tree_log = ttk.Treeview(
            tree_frame,
            columns=("LogID", "User", "Item", "Borrow Date", "Return Date", "Status"),
            show="headings",
            yscrollcommand=scroll_y.set
        )
        scroll_y.config(command=self.tree_log.yview)
        scroll_y.pack(side="right", fill="y")

        self.tree_log.heading("LogID", text="Log ID")
        self.tree_log.heading("User", text="Borrower")
        self.tree_log.heading("Item", text="Item Name")
        self.tree_log.heading("Borrow Date", text="Checked Out At")
        self.tree_log.heading("Return Date", text="Returned At")
        self.tree_log.heading("Status", text="Status")

        self.tree_log.column("LogID", width=60, anchor="center")
        self.tree_log.column("User", width=120)
        self.tree_log.column("Item", width=200)
        self.tree_log.column("Borrow Date", width=150, anchor="center")
        self.tree_log.column("Return Date", width=150, anchor="center")
        self.tree_log.column("Status", width=100, anchor="center")
        self.tree_log.pack(fill="both", expand=True)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", padx=10, pady=10)

        tk.Button(
            btn_frame, text="Return Selected Equipment", command=self.handle_return_item,
            bg="#27AE60", fg="white", font=("Arial", 9, "bold")
        ).pack(side="left", padx=5)

        self.load_logbook()

    def load_logbook(self):
        for item in self.tree_log.get_children():
            self.tree_log.delete(item)

        is_admin = (self.user_data['role'] == 'ADMIN')
        logs = self.inventory_ctrl.fetch_user_borrows(self.user_data['username'], is_admin=is_admin)

        for row in logs:
            ret_date = row[4] if row[4] else "N/A"
            self.tree_log.insert("", "end", values=(row[0], row[1], row[2], row[3], ret_date, row[5]))

    def handle_return_item(self):
        selected = self.tree_log.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a log entry to return.")
            return

        log_id = self.tree_log.item(selected[0])['values'][0]
        success, msg = self.inventory_ctrl.return_item(log_id)
        if success:
            messagebox.showinfo("Success", msg)
            self.load_logbook()
            self.load_catalog()
        else:
            messagebox.showerror("Return Error", msg)

    def setup_approvals_tab(self):
        frame = self.tab_approvals
        tk.Label(frame, text="Pending Password Reset & Unlock Requests", font=("Arial", 11, "bold")).pack(pady=10)

        self.tree_reqs = ttk.Treeview(frame, columns=("ReqID", "User", "Email", "Timestamp"), show="headings")
        self.tree_reqs.heading("ReqID", text="ID")
        self.tree_reqs.heading("User", text="Username")
        self.tree_reqs.heading("Email", text="Email")
        self.tree_reqs.heading("Timestamp", text="Timestamp")
        self.tree_reqs.pack(fill="both", expand=True, padx=10, pady=5)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", padx=10, pady=10)

        tk.Button(
            btn_frame, text="Approve Selected", command=self.handle_approve_reset,
            bg="#27AE60", fg="white", font=("Arial", 9, "bold")
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame, text="Reject Selected", command=self.handle_reject_reset,
            bg="#C0392B", fg="white", font=("Arial", 9, "bold")
        ).pack(side="left", padx=5)

        self.load_pending_resets()

    def load_pending_resets(self):
        for item in self.tree_reqs.get_children():
            self.tree_reqs.delete(item)
        for req in self.admin_ctrl.fetch_pending_resets():
            self.tree_reqs.insert("", "end", values=(req[0], req[1], req[2], req[3]))

    def handle_approve_reset(self):
        selected = self.tree_reqs.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a request to approve.")
            return
        req_ids = [self.tree_reqs.item(item)['values'][0] for item in selected]
        success, msg = self.admin_ctrl.approve_resets(req_ids)
        messagebox.showinfo("Approval Status", msg)
        self.load_pending_resets()

    def handle_reject_reset(self):
        selected = self.tree_reqs.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a request to reject.")
            return
        req_ids = [self.tree_reqs.item(item)['values'][0] for item in selected]
        success, msg = self.admin_ctrl.reject_resets(req_ids)
        messagebox.showinfo("Rejection Status", msg)
        self.load_pending_resets()

# ==========================================
# 6. APPLICATION DRIVER
# ==========================================
class Application:
    def __init__(self):
        init_db()
        self.root = tk.Tk()
        self.current_window = None
        self.show_login()

    def show_login(self):
        if self.current_window:
            for widget in self.root.winfo_children():
                widget.destroy()
        self.current_window = AuthWindow(self.root, self.on_login_success)

    def on_login_success(self, user_data):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.current_window = MainDashboardView(self.root, user_data, self.show_login)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = Application()
    app.run()  # Properly closed with no parameters
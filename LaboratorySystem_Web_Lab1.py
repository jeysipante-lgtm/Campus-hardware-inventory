import os
import re
import csv
import sqlite3
import logging
import io
from datetime import datetime
from functools import wraps

import bcrypt
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
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
                    student_number TEXT DEFAULT '',
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
                    student_number TEXT NOT NULL DEFAULT '',
                    item_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    borrow_date TEXT NOT NULL,
                    return_date TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING_BORROW',
                    FOREIGN KEY(item_id) REFERENCES hardware(item_id)
                )
            """)

            # MIGRATION CHECKS FOR USERS TABLE
            cursor.execute("PRAGMA table_info(users)")
            user_columns = [column[1] for column in cursor.fetchall()]

            if "student_number" not in user_columns:
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN student_number TEXT DEFAULT ''"
                )

            # MIGRATION CHECKS FOR BORROW_LOGS TABLE
            cursor.execute("PRAGMA table_info(borrow_logs)")
            columns = [column[1] for column in cursor.fetchall()]

            if "student_number" not in columns:
                cursor.execute(
                    "ALTER TABLE borrow_logs ADD COLUMN student_number TEXT NOT NULL DEFAULT ''"
                )

            if "quantity" not in columns:
                cursor.execute(
                    "ALTER TABLE borrow_logs ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1"
                )

            cursor.execute("SELECT * FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                admin_pw = bcrypt.hashpw(
                    "Admin123!".encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

                cursor.execute(
                    "INSERT INTO users (username, email, student_number, password_hash, role) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("admin", "admin@campus.edu", "0000-00000", admin_pw, "ADMIN")
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
    student_number: str = ""
    password: str
    role: str = "USER"

    @field_validator("username")
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must be alphanumeric.")
        return v

    @field_validator("email")
    def validate_email(cls, v):
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email address format.")
        return v

    @field_validator("student_number")
    def validate_student_number(cls, v):
        clean_v = v.strip()
        if clean_v and not re.match(r"^\d{4}-?\d{4,6}$", clean_v):
            raise ValueError(
                "Student number must follow format YYYY-XXXXX (e.g., 2024-10021)."
            )
        return clean_v

    @field_validator("password")
    def validate_password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number.")
        if not re.search(r"[@#$%^&*!]", v):
            raise ValueError("Password must contain at least one special character (@#$%^&*!).")
        return v


class PasswordResetSchema(BaseModel):
    username: str
    email: str
    new_password: str

    @field_validator("email")
    def validate_email(cls, v):
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email address format.")
        return v

    @field_validator("new_password")
    def validate_password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number.")
        if not re.search(r"[@#$%^&*!]", v):
            raise ValueError("Password must contain at least one special character (@#$%^&*!).")
        return v


class HardwareItemSchema(BaseModel):
    item_name: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    quantity: int = Field(..., ge=0)
    unit_price: float = Field(..., ge=0.0)


class ReservationSchema(BaseModel):
    student_number: str

    @field_validator("student_number")
    def validate_student_number(cls, v):
        clean_v = v.strip()
        if not re.match(r"^\d{4}-?\d{4,6}$", clean_v):
            raise ValueError(
                "Student number must follow format YYYY-XXXXX (e.g., 2024-10021)."
            )
        return clean_v


class BorrowRequestSchema(BaseModel):
    student_number: str
    quantity: int = Field(..., ge=1)

    @field_validator("student_number")
    def validate_student_number(cls, v):
        clean_v = v.strip()
        if not re.match(r"^\d{4}-?\d{4,6}$", clean_v):
            raise ValueError(
                "Student number must follow format YYYY-XXXXX (e.g., 2024-10021)."
            )
        return clean_v


# ==========================================
# 4. CONTROLLERS
# ==========================================

class AuthController:
    db_name = DB_NAME
    failed_attempts = {}

    @classmethod
    def register(cls, username, email, password, student_number="", role="USER"):
        try:
            validated = UserRegistrationSchema(
                username=username,
                email=email,
                student_number=student_number,
                password=password,
                role=role
            )

            hashed_pw = bcrypt.hashpw(
                validated.password.encode("utf-8"),
                bcrypt.gensalt()
            )

            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, email, student_number, password_hash, role) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        validated.username,
                        validated.email,
                        validated.student_number,
                        hashed_pw.decode("utf-8"),
                        validated.role
                    )
                )

            logger.info(f"User registration successful for: '{validated.username}' ({validated.role})")
            return True, "Registration successful."

        except ValidationError as e:
            msg = e.errors()[0]["msg"]
            logger.warning(f"Registration validation failed: {msg}")
            return False, f"Validation Error: {msg}"

        except sqlite3.IntegrityError:
            msg = "Username or Email already exists."
            logger.warning(f"Registration failed: {msg}")
            return False, msg

        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False, str(e)

    @classmethod
    def login(cls, username_or_email, password):
        if not username_or_email or not password:
            return False, "Fields cannot be empty.", None

        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT password_hash, username, role, is_locked, student_number "
                    "FROM users WHERE username = ? OR email = ?",
                    (username_or_email, username_or_email)
                )
                row = cursor.fetchone()

            if row:
                pw_hash, actual_user, role, is_locked, student_number = row

                if is_locked:
                    return False, "ACCOUNT_LOCKED", None

                if bcrypt.checkpw(
                    password.encode("utf-8"),
                    pw_hash.encode("utf-8")
                ):
                    cls.failed_attempts[actual_user] = 0
                    logger.info(
                        f"User login successful: '{actual_user}' ({role})"
                    )
                    return True, "Login successful.", {
                        "username": actual_user,
                        "role": role,
                        "student_number": student_number
                    }

                cls.failed_attempts[actual_user] = (
                    cls.failed_attempts.get(actual_user, 0) + 1
                )
                attempts = cls.failed_attempts[actual_user]

                if attempts >= 3:
                    with sqlite3.connect(cls.db_name) as conn:
                        conn.cursor().execute(
                            "UPDATE users SET is_locked = 1 WHERE username = ?",
                            (actual_user,)
                        )

                    logger.warning(
                        f"Account locked due to 3 failed attempts: '{actual_user}'"
                    )
                    return False, "ACCOUNT_LOCKED", None

                return False, f"Invalid password. Attempt {attempts}/3.", None

        except Exception as e:
            logger.error(f"Login database error: {e}")

        return False, "Invalid username/email or password.", None

    @classmethod
    def request_password_reset(cls, username, email, new_password, confirm_password):
        if new_password != confirm_password:
            return False, "Passwords do not match."

        try:
            validated = PasswordResetSchema(
                username=username,
                email=email,
                new_password=new_password
            )

            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT email FROM users WHERE username = ?",
                    (validated.username,)
                )
                row = cursor.fetchone()

                if not row or row[0].lower() != validated.email.lower():
                    return False, (
                        "Username and registered Email address do not match."
                    )

                hashed_pw = bcrypt.hashpw(
                    validated.new_password.encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute(
                    "INSERT INTO reset_requests "
                    "(username, email, new_password_hash, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        validated.username,
                        validated.email,
                        hashed_pw,
                        now_str
                    )
                )

            logger.info(
                f"Password reset request submitted for: '{validated.username}'"
            )
            return True, (
                f"Reset request submitted at {now_str}. "
                "An Admin must approve it before the password changes."
            )

        except ValidationError as e:
            msg = e.errors()[0]["msg"]
            return False, f"Password Security Error: {msg}"

        except Exception as e:
            logger.error(f"Reset request error: {e}")
            return False, str(e)


class InventoryController:
    db_name = DB_NAME

    @staticmethod
    def compute_status(quantity: int) -> str:
        if quantity > 5:
            return "In Stock"
        elif 1 <= quantity <= 5:
            return "Low Stock"
        return "Out of Stock"

    @classmethod
    def fetch_all(cls, search_name="", category="ALL"):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                query = (
                    "SELECT item_id, item_name, category, quantity, "
                    "unit_price, status FROM hardware WHERE 1=1"
                )
                params = []

                if search_name:
                    query += " AND LOWER(item_name) LIKE LOWER(?)"
                    params.append(f"%{search_name}%")

                if category and category != "ALL":
                    query += " AND category = ?"
                    params.append(category)

                query += " ORDER BY item_id DESC"

                cursor.execute(query, params)
                return cursor.fetchall()

        except sqlite3.Error as e:
            logger.error(f"Error fetching inventory records: {e}")
            return []

    @classmethod
    def get_categories(cls):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT category FROM hardware ORDER BY category"
                )
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    @classmethod
    def get_total_stocks(cls):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COALESCE(SUM(quantity), 0) FROM hardware")
                return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0

    @classmethod
    def add_item(cls, item_name, category, quantity_str, price_str):
        try:
            qty = int(quantity_str)
            price = float(price_str)

            validated = HardwareItemSchema(
                item_name=item_name,
                category=category,
                quantity=qty,
                unit_price=price
            )

        except ValueError:
            return False, "Quantity must be an integer and Unit Price must be a valid number."

        except ValidationError as e:
            return False, f"Validation Error: {e.errors()[0]['msg']}"

        status = cls.compute_status(validated.quantity)

        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT item_id FROM hardware "
                    "WHERE LOWER(item_name) = LOWER(?)",
                    (validated.item_name,)
                )

                if cursor.fetchone():
                    return False, (
                        f"Item Name '{validated.item_name}' already exists."
                    )

                cursor.execute(
                    "INSERT INTO hardware "
                    "(item_name, category, quantity, unit_price, status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        validated.item_name,
                        validated.category,
                        validated.quantity,
                        validated.unit_price,
                        status
                    )
                )

            logger.info(f"Hardware item added: '{validated.item_name}'")
            return True, "Item added successfully."

        except sqlite3.Error as e:
            return False, f"Database operation failed: {e}"

    @classmethod
    def delete_items(cls, item_ids):
        if not item_ids:
            return False, "No items selected."

        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                placeholders = ",".join("?" for _ in item_ids)
                cursor.execute(
                    f"DELETE FROM hardware WHERE item_id IN ({placeholders})",
                    item_ids
                )

            logger.info(f"Successfully deleted item IDs: {item_ids}")
            return True, f"Successfully deleted {len(item_ids)} item(s)."

        except sqlite3.Error as e:
            logger.error(f"Error deleting items: {e}")
            return False, f"Database delete operation failed: {e}"

    @classmethod
    def request_borrow(cls, username, student_number, item_id, quantity):
        try:
            validated = BorrowRequestSchema(
                student_number=student_number,
                quantity=quantity
            )
        except ValidationError as e:
            return False, f"Validation Error: {e.errors()[0]['msg']}"

        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT quantity, item_name FROM hardware WHERE item_id = ?",
                    (item_id,)
                )
                row = cursor.fetchone()

                if not row:
                    return False, "Item not found."

                available_qty, item_name = row

                if validated.quantity > available_qty:
                    return False, (
                        f"Requested quantity exceeds available stock. "
                        f"Available: {available_qty}."
                    )

                cursor.execute(
                    "SELECT log_id FROM borrow_logs "
                    "WHERE student_number = ? AND item_id = ? "
                    "AND status IN ('PENDING_BORROW', 'BORROWED', 'RETURN_PENDING')",
                    (validated.student_number, item_id)
                )

                if cursor.fetchone():
                    return False, (
                        f"Student #{validated.student_number} already has "
                        f"an active request/borrow for '{item_name}'."
                    )

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute(
                    "INSERT INTO borrow_logs "
                    "(username, student_number, item_id, quantity, borrow_date, status) "
                    "VALUES (?, ?, ?, ?, ?, 'PENDING_BORROW')",
                    (
                        username,
                        validated.student_number,
                        item_id,
                        validated.quantity,
                        now_str
                    )
                )

            logger.info(
                f"Borrow request: {username}, student #{validated.student_number}, "
                f"item {item_id}, qty {validated.quantity}"
            )

            return True, (
                f"Borrow request submitted for '{item_name}' "
                f"(Quantity: {validated.quantity}). Waiting for Admin approval."
            )

        except sqlite3.Error as e:
            logger.error(f"Borrow request error: {e}")
            return False, f"Database error: {e}"

    @classmethod
    def request_return(cls, username, log_id):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT item_id, quantity, status, username "
                    "FROM borrow_logs WHERE log_id = ?",
                    (log_id,)
                )
                row = cursor.fetchone()

                if not row:
                    return False, "Borrow record not found."

                item_id, quantity, status, owner = row

                if owner != username:
                    return False, "You can only return your own borrowed item."

                if status != "BORROWED":
                    return False, "Only approved borrowed items can be returned."

                cursor.execute(
                    "UPDATE borrow_logs SET status = 'RETURN_PENDING' "
                    "WHERE log_id = ?",
                    (log_id,)
                )

            logger.info(f"Return request submitted by '{username}', log {log_id}")
            return True, "Return request submitted. Waiting for Admin approval."

        except sqlite3.Error as e:
            logger.error(f"Return request error: {e}")
            return False, f"Database error: {e}"

    @classmethod
    def fetch_borrows(cls, username=None, status=None):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                query = """
                    SELECT b.log_id, b.username, b.student_number,
                           b.item_id, h.item_name, b.quantity,
                           b.borrow_date, b.return_date, b.status
                    FROM borrow_logs b
                    JOIN hardware h ON b.item_id = h.item_id
                    WHERE 1=1
                """
                params = []

                if username:
                    query += " AND b.username = ?"
                    params.append(username)

                if status:
                    query += " AND b.status = ?"
                    params.append(status)

                query += " ORDER BY b.log_id DESC"

                cursor.execute(query, params)
                return cursor.fetchall()

        except sqlite3.Error as e:
            logger.error(f"Error fetching borrow logs: {e}")
            return []

    @classmethod
    def export_to_csv(cls):
        try:
            items = cls.fetch_all()
            output = [
                ["ID", "Item Name", "Category", "Quantity", "Unit Price", "Status"]
            ]

            for row in items:
                output.append(list(row))

            stream = io.StringIO()
            writer = csv.writer(stream)
            writer.writerows(output)

            return stream.getvalue()

        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return None


class AdminController:
    db_name = DB_NAME

    @classmethod
    def fetch_pending_resets(cls):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT request_id, username, email, timestamp "
                    "FROM reset_requests WHERE status = 'PENDING' "
                    "ORDER BY request_id DESC"
                )
                return cursor.fetchall()
        except sqlite3.Error:
            return []

    @classmethod
    def approve_resets(cls, request_ids):
        count = 0
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                for req_id in request_ids:
                    cursor.execute(
                        "SELECT username, new_password_hash "
                        "FROM reset_requests "
                        "WHERE request_id = ? AND status = 'PENDING'",
                        (req_id,)
                    )
                    row = cursor.fetchone()

                    if row:
                        user, new_pw = row

                        cursor.execute(
                            "UPDATE users SET password_hash = ?, is_locked = 0 "
                            "WHERE username = ?",
                            (new_pw, user)
                        )

                        cursor.execute(
                            "UPDATE reset_requests SET status = 'APPROVED' "
                            "WHERE request_id = ?",
                            (req_id,)
                        )

                        count += 1

            return True, f"Successfully approved {count} reset request(s)."

        except sqlite3.Error as e:
            return False, f"Error approving requests: {e}"

    @classmethod
    def reject_resets(cls, request_ids):
        count = 0
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                for req_id in request_ids:
                    cursor.execute(
                        "UPDATE reset_requests SET status = 'REJECTED' "
                        "WHERE request_id = ? AND status = 'PENDING'",
                        (req_id,)
                    )
                    count += cursor.rowcount

            return True, f"Successfully rejected {count} request(s)."

        except sqlite3.Error as e:
            return False, f"Error rejecting requests: {e}"

    @classmethod
    def fetch_pending_borrows(cls):
        return InventoryController.fetch_borrows(status="PENDING_BORROW")

    @classmethod
    def approve_borrow(cls, log_id):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT item_id, quantity, status "
                    "FROM borrow_logs WHERE log_id = ?",
                    (log_id,)
                )
                row = cursor.fetchone()

                if not row:
                    return False, "Borrow request not found."

                item_id, requested_qty, status = row

                if status != "PENDING_BORROW":
                    return False, "Borrow request is no longer pending."

                cursor.execute(
                    "SELECT quantity, item_name FROM hardware WHERE item_id = ?",
                    (item_id,)
                )
                item = cursor.fetchone()

                if not item:
                    return False, "Hardware item no longer exists."

                current_qty, item_name = item

                if requested_qty > current_qty:
                    return False, (
                        f"Cannot approve. Only {current_qty} unit(s) "
                        f"of '{item_name}' remain."
                    )

                new_qty = current_qty - requested_qty
                new_status = InventoryController.compute_status(new_qty)

                cursor.execute(
                    "UPDATE hardware SET quantity = ?, status = ? "
                    "WHERE item_id = ?",
                    (new_qty, new_status, item_id)
                )

                cursor.execute(
                    "UPDATE borrow_logs SET status = 'BORROWED' "
                    "WHERE log_id = ?",
                    (log_id,)
                )

            logger.info(f"Borrow request approved: log {log_id}")
            return True, "Borrow request approved successfully."

        except sqlite3.Error as e:
            return False, f"Error approving borrow request: {e}"

    @classmethod
    def reject_borrow(cls, log_id):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "UPDATE borrow_logs SET status = 'BORROW_REJECTED' "
                    "WHERE log_id = ? AND status = 'PENDING_BORROW'",
                    (log_id,)
                )

                if cursor.rowcount == 0:
                    return False, "Borrow request is not pending."

            logger.info(f"Borrow request rejected: log {log_id}")
            return True, "Borrow request rejected."

        except sqlite3.Error as e:
            return False, f"Error rejecting borrow request: {e}"

    @classmethod
    def fetch_pending_returns(cls):
        return InventoryController.fetch_borrows(status="RETURN_PENDING")

    @classmethod
    def approve_return(cls, log_id):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT item_id, quantity, status "
                    "FROM borrow_logs WHERE log_id = ?",
                    (log_id,)
                )
                row = cursor.fetchone()

                if not row:
                    return False, "Return request not found."

                item_id, returned_qty, status = row

                if status != "RETURN_PENDING":
                    return False, "Return request is no longer pending."

                cursor.execute(
                    "SELECT quantity FROM hardware WHERE item_id = ?",
                    (item_id,)
                )
                item = cursor.fetchone()

                if not item:
                    return False, "Hardware item no longer exists."

                current_qty = item[0]
                new_qty = current_qty + returned_qty
                new_status = InventoryController.compute_status(new_qty)

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute(
                    "UPDATE hardware SET quantity = ?, status = ? "
                    "WHERE item_id = ?",
                    (new_qty, new_status, item_id)
                )

                cursor.execute(
                    "UPDATE borrow_logs "
                    "SET status = 'RETURNED', return_date = ? "
                    "WHERE log_id = ?",
                    (now_str, log_id)
                )

            logger.info(f"Return request approved: log {log_id}")
            return True, "Return approved and stock restocked."

        except sqlite3.Error as e:
            return False, f"Error approving return request: {e}"

    @classmethod
    def reject_return(cls, log_id):
        try:
            with sqlite3.connect(cls.db_name) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "UPDATE borrow_logs SET status = 'BORROWED' "
                    "WHERE log_id = ? AND status = 'RETURN_PENDING'",
                    (log_id,)
                )

                if cursor.rowcount == 0:
                    return False, "Return request is not pending."

            logger.info(f"Return request rejected: log {log_id}")
            return True, "Return request rejected."

        except sqlite3.Error as e:
            return False, f"Error rejecting return request: {e}"
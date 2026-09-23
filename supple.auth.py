import os
import re
import sqlite3
import bcrypt
import tkinter as tk
from tkinter import ttk, messagebox
from pydantic import BaseModel, Field, field_validator, ValidationError

# ==========================================
# 1. DATABASE INITIALIZATION
# ==========================================
DB_NAME = "lab_tracker.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                experiment_title TEXT NOT NULL
            )
        """)

# ==========================================
# 2. SCHEMAS (DATA VALIDATION)
# ==========================================
class UserSchema(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)

    @field_validator('username')
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9]+$", v):
            raise ValueError('Username must be alphanumeric.')
        return v

class ExperimentSchema(BaseModel):
    student_id: str = Field(..., min_length=4)
    experiment_title: str = Field(..., min_length=2)

# ==========================================
# 3. CONTROLLERS
# ==========================================
class AuthController:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def register(self, username, password):
        try:
            validated = UserSchema(username=username, password=password)
            hashed_pw = bcrypt.hashpw(validated.password.encode('utf-8'), bcrypt.gensalt())
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                # Parameterized SQL Query against SQL Injection
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (validated.username, hashed_pw.decode('utf-8'))
                )
            return True, "Registration successful."
        except ValidationError as e:
            return False, f"Validation Error: {e.errors()[0]['msg']}"
        except sqlite3.IntegrityError:
            return False, "Username already exists."
        except Exception as e:
            return False, str(e)

    def login(self, username, password):
        if not username or not password:
            return False, "Fields cannot be empty."
            
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            # Parameterized SQL Query against SQL Injection
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            
        if row and bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8')):
            return True, "Login successful."
        return False, "Invalid credentials."


class TrackerController:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def add_experiment(self, student_id, title):
        try:
            validated = ExperimentSchema(student_id=student_id, experiment_title=title)
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO experiments (student_id, experiment_title) VALUES (?, ?)",
                    (validated.student_id, validated.experiment_title)
                )
            return True, "Experiment logged successfully."
        except ValidationError as e:
            return False, f"Validation Error: {e.errors()[0]['msg']}"

    def get_experiments(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, student_id, experiment_title FROM experiments")
            return cursor.fetchall()

# ==========================================
# 4. VIEWS
# ==========================================
class LoginView:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.auth = AuthController()

        self.root.title("Lab Tracker - Authentication")
        self.root.geometry("320x260")
        self.root.resizable(False, False)

        tk.Label(root, text="User Login", font=("Arial", 14, "bold")).pack(pady=15)

        tk.Label(root, text="Username:").pack(anchor="w", padx=30)
        self.entry_user = tk.Entry(root, width=30)
        self.entry_user.pack(padx=30, pady=(0, 10))

        tk.Label(root, text="Password:").pack(anchor="w", padx=30)
        self.entry_pass = tk.Entry(root, show="*", width=30)
        self.entry_pass.pack(padx=30, pady=(0, 15))

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Login", command=self.login, width=10, bg="#4CAF50", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Register", command=self.register, width=10, bg="#2196F3", fg="white").pack(side="right", padx=5)

    def login(self):
        success, msg = self.auth.login(self.entry_user.get().strip(), self.entry_pass.get())
        if success:
            self.on_success()
        else:
            messagebox.showerror("Authentication Error", msg)

    def register(self):
        success, msg = self.auth.register(self.entry_user.get().strip(), self.entry_pass.get())
        if success:
            messagebox.showinfo("Success", msg)
            self.entry_pass.delete(0, tk.END)
        else:
            messagebox.showwarning("Registration Failed", msg)


class TrackerView:
    def __init__(self, root):
        self.root = root
        self.controller = TrackerController()
        
        self.root.title("Student Lab Experiment Tracker")
        self.root.geometry("620x450")

        # Input Frame
        frame = tk.LabelFrame(self.root, text="Add New Experiment", padx=10, pady=10)
        frame.pack(fill="x", padx=15, pady=10)

        tk.Label(frame, text="Student ID:").grid(row=0, column=0, sticky="w")
        self.entry_id = tk.Entry(frame, width=15)
        self.entry_id.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(frame, text="Experiment Title:").grid(row=0, column=2, sticky="w")
        self.entry_title = tk.Entry(frame, width=25)
        self.entry_title.grid(row=0, column=3, padx=5, pady=5)

        tk.Button(frame, text="Add Record", command=self.add_record, bg="#4CAF50", fg="white").grid(row=0, column=4, padx=10)

        # Data Grid (ttk.Treeview)
        grid_frame = tk.Frame(self.root)
        grid_frame.pack(fill="both", expand=True, padx=15, pady=5)

        scroll_y = ttk.Scrollbar(grid_frame, orient="vertical")
        self.tree = ttk.Treeview(
            grid_frame, 
            columns=("ID", "Student ID", "Title"), 
            show="headings",
            yscrollcommand=scroll_y.set
        )
        scroll_y.config(command=self.tree.yview)
        scroll_y.pack(side="right", fill="y")

        self.tree.heading("ID", text="Record ID")
        self.tree.heading("Student ID", text="Student ID")
        self.tree.heading("Title", text="Experiment Title")

        self.tree.column("ID", width=80, anchor="center")
        self.tree.column("Student ID", width=150, anchor="center")
        self.tree.column("Title", width=320)
        self.tree.pack(fill="both", expand=True)

        # Start Real-Time Polling Loop
        self.auto_refresh()

    def add_record(self):
        success, msg = self.controller.add_experiment(
            self.entry_id.get().strip(), 
            self.entry_title.get().strip()
        )
        if success:
            self.entry_id.delete(0, tk.END)
            self.entry_title.delete(0, tk.END)
            self.load_data()
        else:
            messagebox.showerror("Error", msg)

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.controller.get_experiments():
            self.tree.insert("", "end", values=row)

    def auto_refresh(self):
        """Real-time polling synchronization loop."""
        self.load_data()
        self.root.after(2000, self.auto_refresh)

# ==========================================
# 5. APPLICATION ENTRY POINT
# ==========================================
def launch_tracker():
    for widget in root.winfo_children():
        widget.destroy()
    TrackerView(root)

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    LoginView(root, on_success=launch_tracker)
    root.mainloop()
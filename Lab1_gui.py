import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

# -----------------------------
# DATABASE SETUP
# -----------------------------

conn = sqlite3.connect("lab_tracker.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS experiments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    student_id TEXT NOT NULL,
    status TEXT NOT NULL
)
""")

conn.commit()

# -----------------------------
# FUNCTIONS
# -----------------------------

def clear_entries():
    title_entry.delete(0, tk.END)
    student_entry.delete(0, tk.END)
    status_combo.current(0)


def load_data():
    for row in tree.get_children():
        tree.delete(row)

    cursor.execute("SELECT * FROM experiments")

    rows = cursor.fetchall()

    for row in rows:
        tree.insert("", tk.END, values=row)


def save_record():

    title = title_entry.get()
    student = student_entry.get()
    status = status_combo.get()

    if title == "" or student == "":
        messagebox.showerror("Error", "Please fill in all fields.")
        return

    cursor.execute("""
    INSERT INTO experiments(title, student_id, status)
    VALUES(?,?,?)
    """, (title, student, status))

    conn.commit()

    clear_entries()

    load_data()

    messagebox.showinfo("Success", "Record Saved")


def select_record(event):

    selected = tree.focus()

    if selected == "":
        return

    values = tree.item(selected, "values")

    title_entry.delete(0, tk.END)
    student_entry.delete(0, tk.END)

    title_entry.insert(0, values[1])
    student_entry.insert(0, values[2])

    status_combo.set(values[3])


def update_status():

    selected = tree.focus()

    if selected == "":
        messagebox.showwarning("Warning", "Select a record first.")
        return

    values = tree.item(selected, "values")

    record_id = values[0]

    new_status = status_combo.get()

    cursor.execute("""
    UPDATE experiments
    SET status=?
    WHERE id=?
    """, (new_status, record_id))

    conn.commit()

    load_data()

    messagebox.showinfo("Updated", "Status Updated Successfully")


def delete_record():

    selected = tree.focus()

    if selected == "":
        messagebox.showwarning("Warning", "Select a record first.")
        return

    answer = messagebox.askyesno(
        "Delete",
        "Are you sure you want to delete this record?"
    )

    if answer:

        values = tree.item(selected, "values")

        record_id = values[0]

        cursor.execute("""
        DELETE FROM experiments
        WHERE id=?
        """, (record_id,))

        conn.commit()

        load_data()

        clear_entries()

        messagebox.showinfo("Deleted", "Record Deleted")


def auto_refresh():
    load_data()
    root.after(2000, auto_refresh)


# -----------------------------
# GUI WINDOW
# -----------------------------

root = tk.Tk()

root.title("Student Lab Experiment Log")

root.geometry("800x600")

# -----------------------------
# LABELS
# -----------------------------

tk.Label(root, text="Experiment Title").grid(row=0, column=0, padx=10, pady=10)

title_entry = tk.Entry(root, width=40)
title_entry.grid(row=0, column=1)

tk.Label(root, text="Student ID").grid(row=1, column=0)

student_entry = tk.Entry(root, width=40)
student_entry.grid(row=1, column=1)

tk.Label(root, text="Status").grid(row=2, column=0)

status_combo = ttk.Combobox(
    root,
    values=[
        "Pending",
        "In Progress",
        "Completed"
    ],
    state="readonly",
    width=37
)

status_combo.grid(row=2, column=1)
status_combo.current(0)

# -----------------------------
# BUTTONS
# -----------------------------

save_btn = tk.Button(
    root,
    text="Save",
    width=15,
    command=save_record
)

save_btn.grid(row=3, column=0, pady=10)

update_btn = tk.Button(
    root,
    text="Update Status",
    width=15,
    command=update_status
)

update_btn.grid(row=3, column=1)

delete_btn = tk.Button(
    root,
    text="Delete",
    width=15,
    command=delete_record
)

delete_btn.grid(row=3, column=2)

# -----------------------------
# TREEVIEW
# -----------------------------

columns = (
    "ID",
    "Title",
    "Student ID",
    "Status"
)

tree = ttk.Treeview(
    root,
    columns=columns,
    show="headings",
    height=15
)

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=150)

tree.grid(
    row=4,
    column=0,
    columnspan=3,
    padx=10,
    pady=20
)

tree.bind("<<TreeviewSelect>>", select_record)

# -----------------------------
# INITIAL LOAD
# -----------------------------

load_data()

auto_refresh()

root.mainloop()

conn.close()
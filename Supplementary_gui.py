import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

DB_NAME="hardware_inventory.db"

def init_db():
    conn=sqlite3.connect(DB_NAME)
    c=conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS hardware(
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT,
    category TEXT,
    quantity INTEGER,
    unit_price REAL,
    status TEXT)""")
    conn.commit(); conn.close()

def compute_status(q):
    return "In Stock" if q>5 else ("Low Stock" if q>0 else "Out of Stock")

root=tk.Tk()
root.title("Campus Hardware Inventory")
root.geometry("850x550")
tk.Label(root,text="Starter file generated.").pack(pady=20)
init_db()
root.mainloop()
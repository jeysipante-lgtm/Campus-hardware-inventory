import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

# --- DATABASE SETUP ---
DB_NAME = "hardware_inventory.db"


def init_db():
    """Initialize the SQLite database and create the hardware table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hardware (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            status TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


def compute_status(quantity: int) -> str:
    """Compute status based on quantity business logic."""
    if quantity > 5:
        return "In Stock"
    elif 1 <= quantity <= 5:
        return "Low Stock"
    else:
        return "Out of Stock"


# --- MAIN GUI APPLICATION ---
class HardwareInventoryApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Campus Hardware Inventory System")
        self.root.geometry("850x550")
        self.root.minsize(750, 480)

        # Selected ID tracker for update operations
        self.selected_item_id = None

        # Apply basic ttk theme
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.create_widgets()
        self.load_data()

        # Start real-time sync polling loop (2000 ms)
        self.auto_refresh()

    def create_widgets(self):
        """Construct the GUI layout."""

        # 1. Header Frame
        header_frame = ttk.Frame(self.root, padding=10)
        header_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            header_frame,
            text="Campus Hardware & Component Inventory Log",
            font=("Helvetica", 14, "bold"),
        )
        title_label.pack(side=tk.LEFT)

        # 2. Input Form Frame
        form_frame = ttk.LabelFrame(
            self.root, text=" Item Management ", padding=12
        )
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        # Grid configuration for inputs
        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)

        # Row 0: Name & Category
        ttk.Label(form_frame, text="Item Name:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.entry_name = ttk.Entry(form_frame)
        self.entry_name.grid(
            row=0, column=1, sticky=tk.EW, padx=(0, 15), pady=5
        )

        ttk.Label(form_frame, text="Category:").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.entry_category = ttk.Entry(form_frame)
        self.entry_category.grid(
            row=0, column=3, sticky=tk.EW, padx=(0, 5), pady=5
        )

        # Row 1: Quantity & Price
        ttk.Label(form_frame, text="Quantity:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.entry_quantity = ttk.Entry(form_frame)
        self.entry_quantity.grid(
            row=1, column=1, sticky=tk.EW, padx=(0, 15), pady=5
        )

        ttk.Label(form_frame, text="Unit Price (₱):").grid(
            row=1, column=2, sticky=tk.W, padx=5, pady=5
        )
        self.entry_price = ttk.Entry(form_frame)
        self.entry_price.grid(
            row=1, column=3, sticky=tk.EW, padx=(0, 5), pady=5
        )

        # Row 2: Action Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=(10, 0))

        self.btn_add = ttk.Button(
            btn_frame, text="Add New Item", command=self.add_item
        )
        self.btn_add.pack(side=tk.LEFT, padx=5)

        self.btn_update = ttk.Button(
            btn_frame, text="Update Selected Row", command=self.update_item
        )
        self.btn_update.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ttk.Button(
            btn_frame, text="Clear Inputs", command=self.clear_entries
        )
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        # 3. Data Grid Frame (ttk.Treeview)
        grid_frame = ttk.Frame(self.root, padding=10)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "name", "category", "qty", "price", "status")
        self.tree = ttk.Treeview(grid_frame, columns=columns, show="headings")

        # Define column headers
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("qty", text="Qty")
        self.tree.heading("price", text="Price (₱)")
        self.tree.heading("status", text="Status")

        # Define column layout & widths
        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("name", width=200, anchor=tk.W)
        self.tree.column("category", width=140, anchor=tk.W)
        self.tree.column("qty", width=70, anchor=tk.CENTER)
        self.tree.column("price", width=100, anchor=tk.E)
        self.tree.column("status", width=120, anchor=tk.CENTER)

        # Vertical Scrollbar
        scrollbar = ttk.Scrollbar(
            grid_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Selection Listener
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)

    # --- DATABASE & DATA LOGIC ---
    def load_data(self):
        """Fetch records from SQLite database and populate the Treeview grid."""
        # Preserve scroll position during auto-refresh
        scroll_pos = self.tree.yview()

        # Clear existing items
        for row in self.tree.get_children():
            self.tree.delete(row)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT item_id, item_name, category, quantity, unit_price, status FROM hardware"
        )
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            # Format unit price to 2 decimal places
            formatted_row = (
                row[0],
                row[1],
                row[2],
                row[3],
                f"₱{row[4]:,.2f}",
                row[5],
            )
            self.tree.insert("", tk.END, iid=str(row[0]), values=formatted_row)

        # Restore scroll position
        if scroll_pos:
            self.tree.yview_moveto(scroll_pos[0])

    def add_item(self):
        """Validate inputs, compute backend status, and insert a new record."""
        name = self.entry_name.get().strip()
        category = self.entry_category.get().strip()
        qty_str = self.entry_quantity.get().strip()
        price_str = self.entry_price.get().strip()

        if not name or not category or not qty_str or not price_str:
            messagebox.showwarning(
                "Input Error", "All entry fields are required."
            )
            return

        try:
            quantity = int(qty_str)
            if quantity < 0:
                raise ValueError("Quantity cannot be negative.")
            unit_price = float(price_str)
            if unit_price < 0:
                raise ValueError("Price cannot be negative.")
        except ValueError as e:
            messagebox.showerror(
                "Validation Error",
                f"Invalid number input: {e}\nQuantity must be an integer and Price must be a valid number.",
            )
            return

        # Backend automatic status calculation
        status = compute_status(quantity)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO hardware (item_name, category, quantity, unit_price, status)
            VALUES (?, ?, ?, ?, ?)
        """,
            (name, category, quantity, unit_price, status),
        )
        conn.commit()
        conn.close()

        self.clear_entries()
        self.load_data()
        messagebox.showinfo("Success", f"Item '{name}' inserted successfully!")

    def update_item(self):
        """Update Quantity and Price for the selected row, recalculating status."""
        if self.selected_item_id is None:
            messagebox.showwarning(
                "Selection Error",
                "Please select an item from the grid to update.",
            )
            return

        name = self.entry_name.get().strip()
        category = self.entry_category.get().strip()
        qty_str = self.entry_quantity.get().strip()
        price_str = self.entry_price.get().strip()

        if not name or not category or not qty_str or not price_str:
            messagebox.showwarning(
                "Input Error", "All fields must be filled to update."
            )
            return

        try:
            quantity = int(qty_str)
            if quantity < 0:
                raise ValueError("Quantity cannot be negative.")
            unit_price = float(price_str.replace("₱", "").replace(",", ""))
            if unit_price < 0:
                raise ValueError("Price cannot be negative.")
        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid input: {e}")
            return

        # Automatically recalculate status upon update
        new_status = compute_status(quantity)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE hardware
            SET item_name = ?, category = ?, quantity = ?, unit_price = ?, status = ?
            WHERE item_id = ?
        """,
            (
                name,
                category,
                quantity,
                unit_price,
                new_status,
                self.selected_item_id,
            ),
        )
        conn.commit()
        conn.close()

        self.clear_entries()
        self.load_data()
        messagebox.showinfo(
            "Success",
            f"Item ID {self.selected_item_id} updated successfully!",
        )

    def on_item_select(self, event):
        """Populate input controls when a Treeview row is selected."""
        selected_items = self.tree.selection()
        if not selected_items:
            return

        selected_iid = selected_items[0]
        values = self.tree.item(selected_iid, "values")

        if values:
            self.selected_item_id = int(values[0])
            self.entry_name.delete(0, tk.END)
            self.entry_name.insert(0, values[1])

            self.entry_category.delete(0, tk.END)
            self.entry_category.insert(0, values[2])

            self.entry_quantity.delete(0, tk.END)
            self.entry_quantity.insert(0, values[3])

            raw_price = values[4].replace("₱", "").replace(",", "").strip()
            self.entry_price.delete(0, tk.END)
            self.entry_price.insert(0, raw_price)

    def clear_entries(self):
        """Clear all form input fields and reset selection."""
        self.selected_item_id = None
        self.entry_name.delete(0, tk.END)
        self.entry_category.delete(0, tk.END)
        self.entry_quantity.delete(0, tk.END)
        self.entry_price.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def auto_refresh(self):
        """Periodically sync data with database every 2000 ms."""
        # Only auto-reload if user is not actively editing an uncommitted field selection
        self.load_data()
        self.root.after(2000, self.auto_refresh)


# --- ENTRY POINT ---
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = HardwareInventoryApp(root)
    root.mainloop()
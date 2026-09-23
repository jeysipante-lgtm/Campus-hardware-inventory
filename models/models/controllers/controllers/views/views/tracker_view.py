import tkinter as tk
from tkinter import ttk, messagebox
from controllers.tracker_controller import TrackerController

class TrackerWindow:
    def __init__(self, root):
        self.root = root
        self.controller = TrackerController()

        self.root.title("Student Lab Experiment Tracker")
        self.root.geometry("680x580")

        # --- Form Frame ---
        frame_form = tk.LabelFrame(root, text="Add New Experiment", padx=10, pady=10)
        frame_form.pack(fill="x", padx=15, pady=5)

        tk.Label(frame_form, text="Title:").grid(row=0, column=0, sticky="w")
        self.entry_title = tk.Entry(frame_form, width=35)
        self.entry_title.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(frame_form, text="Student ID:").grid(row=1, column=0, sticky="w")
        self.entry_student = tk.Entry(frame_form, width=35)
        self.entry_student.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(frame_form, text="Status:").grid(row=2, column=0, sticky="w")
        self.combo_status = ttk.Combobox(
            frame_form, values=["Pending", "In Progress", "Completed"], state="readonly", width=32
        )
        self.combo_status.current(0)
        self.combo_status.grid(row=2, column=1, padx=5, pady=5)

        btn_add = tk.Button(
            frame_form, text="Add Experiment", command=self.add_experiment, 
            bg="#4CAF50", fg="white"
        )
        btn_add.grid(row=3, column=0, columnspan=2, pady=5, padx=5, sticky="we")

        # --- Treeview Data Frame ---
        frame_data = tk.Frame(root)
        frame_data.pack(fill="both", expand=True, padx=15, pady=5)

        scroll_y = ttk.Scrollbar(frame_data, orient="vertical")
        self.tree = ttk.Treeview(
            frame_data, columns=("ID", "Title", "Student ID", "Status"), 
            show="headings", yscrollcommand=scroll_y.set
        )
        scroll_y.config(command=self.tree.yview)
        scroll_y.pack(side="right", fill="y")

        self.tree.heading("ID", text="ID")
        self.tree.heading("Title", text="Experiment Title")
        self.tree.heading("Student ID", text="Student ID")
        self.tree.heading("Status", text="Status")

        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Title", width=220)
        self.tree.column("Student ID", width=120, anchor="center")
        self.tree.column("Status", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True)

        # --- Update Frame ---
        frame_update = tk.LabelFrame(root, text="Update Selected Record Status", padx=10, pady=5)
        frame_update.pack(fill="x", padx=15, pady=5)

        tk.Label(frame_update, text="New Status:").grid(row=0, column=0, padx=5, pady=5)
        self.combo_update_status = ttk.Combobox(
            frame_update, values=["Pending", "In Progress", "Completed"], state="readonly", width=20
        )
        self.combo_update_status.current(0)
        self.combo_update_status.grid(row=0, column=1, padx=5, pady=5)

        btn_update = tk.Button(
            frame_update, text="Update Status", command=self.update_status, 
            bg="#2196F3", fg="white"
        )
        btn_update.grid(row=0, column=2, padx=10, pady=5)

        btn_delete = tk.Button(
            self.root, text="Delete Selected Record", command=self.delete_selected, 
            bg="#f44336", fg="white"
        )
        btn_delete.pack(fill="x", padx=15, pady=(0, 10))

        self.load_data()
        self.auto_refresh()

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = self.controller.fetch_all_experiments()
        for row in rows:
            self.tree.insert("", "end", values=row)

    def add_experiment(self):
        title = self.entry_title.get().strip()
        student_id = self.entry_student.get().strip()
        status = self.combo_status.get()

        success, msg = self.controller.add_experiment(title, student_id, status)
        if success:
            messagebox.showinfo("Success", msg)
            self.entry_title.delete(0, tk.END)
            self.entry_student.delete(0, tk.END)
            self.combo_status.current(0)
            self.load_data()
        else:
            messagebox.showerror("Error", msg)

    def update_status(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Warning", "Please select a row to update!")
            return

        exp_id = self.tree.item(selected[0], "values")[0]
        new_status = self.combo_update_status.get()

        success, msg = self.controller.update_status(exp_id, new_status)
        if success:
            messagebox.showinfo("Success", msg)
            self.load_data()
        else:
            messagebox.showerror("Error", msg)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Warning", "Please select a row to delete!")
            return

        exp_id = self.tree.item(selected[0], "values")[0]
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete Experiment ID {exp_id}?")
        if not confirm:
            return

        success, msg = self.controller.delete_experiment(exp_id)
        if success:
            messagebox.showinfo("Deleted", msg)
            self.load_data()
        else:
            messagebox.showerror("Error", msg)

    def auto_refresh(self):
        self.load_data()
        self.root.after(5000, self.auto_refresh)
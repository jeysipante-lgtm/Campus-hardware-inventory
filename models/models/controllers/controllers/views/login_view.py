import tkinter as tk
from tkinter import messagebox
from controllers.auth_controller import AuthController

class LoginWindow:
    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success
        self.auth = AuthController()

        self.root.title("System Auth - Login / Register")
        self.root.geometry("360x300")
        self.root.resizable(False, False)

        tk.Label(root, text="User Authentication", font=("Arial", 14, "bold")).pack(pady=15)

        tk.Label(root, text="Username:").pack(anchor="w", padx=40)
        self.entry_user = tk.Entry(root, width=32)
        self.entry_user.pack(padx=40, pady=(0, 10))

        tk.Label(root, text="Password:").pack(anchor="w", padx=40)
        self.entry_pass = tk.Entry(root, show="*", width=32)
        self.entry_pass.pack(padx=40, pady=(0, 15))

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        tk.Button(
            btn_frame, text="Login", command=self.handle_login, 
            bg="#4CAF50", fg="white", width=12
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame, text="Register", command=self.handle_register, 
            bg="#2196F3", fg="white", width=12
        ).pack(side="right", padx=5)

    def handle_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get()  # Do not strip passwords

        success, msg = self.auth.login_user(username, password)
        if success:
            messagebox.showinfo("Success", msg)
            self.on_login_success()
        else:
            messagebox.showerror("Authentication Failed", msg)

    def handle_register(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get()

        success, msg = self.auth.register_user(username, password)
        if success:
            messagebox.showinfo("Success", msg)
            self.entry_pass.delete(0, tk.END)
        else:
            messagebox.showwarning("Registration Alert", msg)
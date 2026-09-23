import webbrowser
from functools import wraps
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

# Import backend services and database setup from your core script
from engineering_lab_asset_tracking_app import (
    AssetTrackingService,
    AuthService,
    InventoryService,
    init_db,
)

app = Flask(__name__)
app.secret_key = "your_secure_secret_key_here"  # Required for web session management

# Initialize services
auth_service = AuthService()
inventory_service = InventoryService()
asset_service = AssetTrackingService()

# Ensure database tables exist on startup
init_db()


# --- Auth Helpers ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "ADMIN":
            return jsonify({"error": "Admin permission required"}), 403
        return f(*args, **kwargs)

    return decorated_function


# --- Page Routes (HTML Views) ---
@app.route("/")
@login_required
def index():
    return render_template(
        "inventory.html", username=session["username"], role=session["role"]
    )


@app.route("/asset-tracking")
@login_required
def asset_tracking_page():
    return render_template(
        "asset_tracking.html", username=session["username"], role=session["role"]
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.form
        identifier = data.get("identifier")
        password = data.get("password")

        success, msg, locked = auth_service.login_user(identifier, password)
        if success:
            account = auth_service._get_account(identifier)
            session["username"] = account[0]
            session["role"] = account[3]
            return redirect(url_for("index"))

        return render_template("login.html", error=msg)

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- REST API Endpoints (Data Exchange for HTML Frontend) ---
@app.route("/api/inventory", methods=["GET"])
@login_required
def get_inventory():
    search = request.args.get("search", "")
    category = request.args.get("category", "All")
    items = inventory_service.fetch_all(search_text=search, category=category)
    return jsonify(items)


@app.route("/api/inventory", methods=["POST"])
@login_required
@admin_required
def add_inventory_item():
    data = request.json
    success, msg = inventory_service.add_item(
        item_name=data.get("item_name"),
        category=data.get("category"),
        quantity=int(data.get("quantity", 0)),
        unit_price=float(data.get("unit_price", 0.0)),
    )
    return jsonify({"success": success, "message": msg})


@app.route("/api/asset/requests", methods=["GET"])
@login_required
def get_borrow_requests():
    username = None if session.get("role") == "ADMIN" else session.get("username")
    requests_list = (
        asset_service.get_all_requests(username=username)
        if hasattr(asset_service, "get_all_requests")
        else []
    )
    return jsonify(requests_list)


@app.route("/api/asset/request", methods=["POST"])
@login_required
def submit_borrow_request():
    data = request.json
    success, msg = asset_service.submit_request(
        username=session["username"],
        item_id=data.get("item_id"),
        quantity=data.get("quantity"),
        purpose=data.get("purpose"),
        start_date=data.get("start_date"),
        expected_return_date=data.get("expected_return_date"),
    )
    return jsonify({"success": success, "message": msg})


@app.route("/api/asset/approve/<int:transaction_id>", methods=["POST"])
@login_required
@admin_required
def approve_borrow_request(transaction_id):
    success, msg = asset_service.approve_request(
        transaction_id, session["username"]
    )
    return jsonify({"success": success, "message": msg})


if __name__ == "__main__":
    url = "http://127.0.0.1:5000"

    print("\n" + "=" * 50)
    print(" Server is running! Ctrl+Click the link below:")
    print(f" 👉 {url}")
    print("=" * 50 + "\n")

    webbrowser.open_new(url)
    app.run(debug=True, port=5000)
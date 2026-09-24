import logging
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()

def init_db(app=None):
    if app:
        db.init_app(app)
        with app.app_context():
            db.create_all()


# ==========================================
# DATABASE MODELS
# ==========================================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    student_number = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='USER')


class InventoryItem(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)


class InventoryLog(db.Model):
    __tablename__ = 'inventory_logs'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    student_number = db.Column(db.String(50), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='PENDING_BORROW', nullable=False)


# ==========================================
# AUTH CONTROLLER
# ==========================================

class AuthController:
    @staticmethod
    def register(username, email, password, student_number="", role="USER"):
        try:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return False, "Username already taken."

            hashed_pwd = generate_password_hash(password)

            new_user = User(
                username=username,
                email=email,
                student_number=student_number,
                password=hashed_pwd,
                role=role
            )

            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f"User {username} successfully registered to Supabase.")
            return True, "Registration successful! You can now log in."

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering user: {str(e)}")
            return False, f"Database error: {str(e)}"

    @staticmethod
    def login(username, password):
        try:
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                user_data = {
                    'username': user.username,
                    'role': user.role,
                    'student_number': user.student_number
                }
                return True, "Login successful!", user_data
            return False, "Invalid username or password.", None
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False, "Login error occurred.", None

    @staticmethod
    def request_password_reset(username, email, new_password, confirm_password):
        if new_password != confirm_password:
            return False, "Passwords do not match."
        try:
            user = User.query.filter_by(username=username, email=email).first()
            if not user:
                return False, "User not found with provided credentials."
            user.password = generate_password_hash(new_password)
            db.session.commit()
            return True, "Password reset successfully."
        except Exception as e:
            db.session.rollback()
            return False, f"Error resetting password: {str(e)}"


# ==========================================
# INVENTORY CONTROLLER
# ==========================================

class InventoryController:
    @staticmethod
    def fetch_all(search_name="", category="ALL"):
        try:
            query = InventoryItem.query
            if search_name:
                query = query.filter(InventoryItem.item_name.ilike(f"%{search_name}%"))
            if category and category != "ALL":
                query = query.filter(InventoryItem.category == category)
            
            items = query.order_by(InventoryItem.id.asc()).all()
            return [
                {
                    'id': item.id,
                    'item_name': item.item_name,
                    'category': item.category,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price)
                } for item in items
            ]
        except Exception as e:
            logger.error(f"Error fetching inventory: {str(e)}")
            return []

    @staticmethod
    def get_categories():
        try:
            categories = db.session.query(InventoryItem.category).distinct().all()
            cats = [c[0] for c in categories if c[0]]
            if "ALL" not in cats:
                cats.insert(0, "ALL")
            return cats
        except Exception as e:
            logger.error(f"Error fetching categories: {str(e)}")
            return ["ALL", "ELECTRONICS", "HARDWARE"]

    @staticmethod
    def get_total_stocks():
        try:
            total = db.session.query(db.func.sum(InventoryItem.quantity)).scalar()
            return total if total is not None else 0
        except Exception as e:
            logger.error(f"Error calculating total stocks: {str(e)}")
            return 0

    @staticmethod
    def add_item(name, category, quantity, price):
        if not name or not category:
            return False, "Item name and category are required."
        try:
            new_item = InventoryItem(
                item_name=name,
                category=category,
                quantity=int(quantity),
                unit_price=float(price)
            )
            db.session.add(new_item)
            db.session.commit()
            return True, f"Item '{name}' added successfully!"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding item: {str(e)}")
            return False, f"Failed to add item: {str(e)}"

    @staticmethod
    def delete_items(item_ids):
        if not item_ids:
            return False, "No items selected."
        try:
            ids = [int(i) for i in item_ids]
            InventoryItem.query.filter(InventoryItem.id.in_(ids)).delete(synchronize_session=False)
            db.session.commit()
            return True, "Selected items deleted successfully."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting items: {str(e)}")
            return False, f"Failed to delete items: {str(e)}"

    @staticmethod
    def request_borrow(username, student_number, item_id, quantity):
        try:
            item = InventoryItem.query.get(item_id)
            if not item:
                return False, "Equipment not found."
            
            qty = int(quantity)
            if item.quantity < qty:
                return False, "Not enough stock available."

            new_log = InventoryLog(
                username=username,
                student_number=student_number,
                item_id=item.id,
                item_name=item.item_name,
                quantity=qty,
                status='PENDING_BORROW'
            )
            db.session.add(new_log)
            db.session.commit()
            return True, "Borrow request submitted for admin approval!"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error requesting borrow: {str(e)}")
            return False, f"Error submitting request: {str(e)}"

    @staticmethod
    def fetch_borrows(username=None):
        try:
            query = InventoryLog.query
            if username:
                query = query.filter(InventoryLog.username == username)
            
            logs = query.order_by(InventoryLog.id.desc()).all()
            return [
                [
                    log.id,
                    log.username,
                    log.student_number,
                    log.item_id,
                    log.item_name,
                    log.quantity,
                    log.request_date.strftime('%Y-%m-%d %H:%M') if log.request_date else '',
                    log.return_date.strftime('%Y-%m-%d %H:%M') if log.return_date else '',
                    log.status
                ] for log in logs
            ]
        except Exception as e:
            logger.error(f"Error fetching borrows: {str(e)}")
            return []

    @staticmethod
    def request_return(username, log_id):
        try:
            log = InventoryLog.query.filter_by(id=log_id, username=username, status='BORROWED').first()
            if not log:
                return False, "Invalid return request."
            
            log.status = 'RETURN_PENDING'
            db.session.commit()
            return True, "Return request submitted! Awaiting admin verification."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error requesting return: {str(e)}")
            return False, f"Error processing return request: {str(e)}"

    @staticmethod
    def export_to_csv():
        try:
            items = InventoryController.fetch_all()
            csv_output = "ID,Item Name,Category,Quantity,Unit Price\n"
            for item in items:
                csv_output += f"{item['id']},{item['item_name']},{item['category']},{item['quantity']},{item['unit_price']:.2f}\n"
            return csv_output
        except Exception as e:
            logger.error(f"Error exporting CSV: {str(e)}")
            return ""


# ==========================================
# ADMIN CONTROLLER
# ==========================================

class AdminController:
    @staticmethod
    def fetch_pending_resets():
        return []

    @staticmethod
    def approve_resets(request_ids):
        return True, "Resets approved."

    @staticmethod
    def reject_resets(request_ids):
        return True, "Resets rejected."

    @staticmethod
    def fetch_pending_borrows():
        try:
            logs = InventoryLog.query.filter_by(status='PENDING_BORROW').order_by(InventoryLog.id.asc()).all()
            return [
                [
                    log.id, log.username, log.student_number, log.item_id,
                    log.item_name, log.quantity,
                    log.request_date.strftime('%Y-%m-%d %H:%M') if log.request_date else '',
                    '', log.status
                ] for log in logs
            ]
        except Exception as e:
            logger.error(f"Error fetching pending borrows: {str(e)}")
            return []

    @staticmethod
    def fetch_pending_returns():
        try:
            logs = InventoryLog.query.filter_by(status='RETURN_PENDING').order_by(InventoryLog.id.asc()).all()
            return [
                [
                    log.id, log.username, log.student_number, log.item_id,
                    log.item_name, log.quantity,
                    log.request_date.strftime('%Y-%m-%d %H:%M') if log.request_date else '',
                    '', log.status
                ] for log in logs
            ]
        except Exception as e:
            logger.error(f"Error fetching pending returns: {str(e)}")
            return []

    @staticmethod
    def approve_borrow(log_id):
        try:
            log = InventoryLog.query.filter_by(id=log_id, status='PENDING_BORROW').first()
            if not log:
                return False, "Borrow request not found."
            
            item = InventoryItem.query.get(log.item_id)
            if not item or item.quantity < log.quantity:
                return False, "Not enough stock to approve."

            item.quantity -= log.quantity
            log.status = 'BORROWED'
            db.session.commit()
            return True, f"Borrow request #{log_id} approved."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error approving borrow: {str(e)}")
            return False, f"Failed to approve borrow: {str(e)}"

    @staticmethod
    def reject_borrow(log_id):
        try:
            log = InventoryLog.query.filter_by(id=log_id, status='PENDING_BORROW').first()
            if not log:
                return False, "Borrow request not found."
            
            log.status = 'BORROW_REJECTED'
            db.session.commit()
            return True, f"Borrow request #{log_id} rejected."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error rejecting borrow: {str(e)}")
            return False, f"Failed to reject borrow: {str(e)}"

    @staticmethod
    def approve_return(log_id):
        try:
            log = InventoryLog.query.filter_by(id=log_id, status='RETURN_PENDING').first()
            if not log:
                return False, "Return request not found."
            
            item = InventoryItem.query.get(log.item_id)
            if item:
                item.quantity += log.quantity

            log.status = 'RETURNED'
            log.return_date = datetime.utcnow()
            db.session.commit()
            return True, f"Return #{log_id} verified and stock updated."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error approving return: {str(e)}")
            return False, f"Failed to verify return: {str(e)}"

    @staticmethod
    def reject_return(log_id):
        try:
            log = InventoryLog.query.filter_by(id=log_id, status='RETURN_PENDING').first()
            if not log:
                return False, "Return request not found."
            
            log.status = 'BORROWED'
            db.session.commit()
            return True, f"Return #{log_id} rejected."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error rejecting return: {str(e)}")
            return False, f"Failed to reject return: {str(e)}"
import logging
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

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    student_number = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='USER')

class AuthController:
    @staticmethod
    def register(username, email, password, student_number="", role="USER"):
        try:
            # Suriin kung umiiral na ang username
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return False, "Username already taken."

            # I-hash ang password para sa seguridad
            hashed_pwd = generate_password_hash(password)

            # Lumikha ng bagong User record
            new_user = User(
                username=username,
                email=email,
                student_number=student_number,
                password=hashed_pwd,
                role=role
            )

            # I-save at i-commit sa Supabase PostgreSQL
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


class InventoryController:
    @staticmethod
    def fetch_all(search_name="", category="ALL"):
        return []

    @staticmethod
    def get_categories():
        return ["ALL", "ELECTRONICS", "HARDWARE"]

    @staticmethod
    def get_total_stocks():
        return 0

    @staticmethod
    def fetch_borrows(username=None):
        return []

    @staticmethod
    def add_item(name, category, quantity, price):
        return True, "Item added successfully."

    @staticmethod
    def delete_items(item_ids):
        return True, "Items deleted successfully."

    @staticmethod
    def request_borrow(username, student_number, item_id, quantity):
        return True, "Borrow request submitted."

    @staticmethod
    def request_return(username, log_id):
        return True, "Return request submitted."

    @staticmethod
    def export_to_csv():
        return "id,item_name\n"


class AdminController:
    @staticmethod
    def fetch_pending_resets():
        return []

    @staticmethod
    def fetch_pending_borrows():
        return []

    @staticmethod
    def fetch_pending_returns():
        return []

    @staticmethod
    def approve_borrow(log_id):
        return True, "Borrow approved."

    @staticmethod
    def reject_borrow(log_id):
        return True, "Borrow rejected."

    @staticmethod
    def approve_return(log_id):
        return True, "Return approved."

    @staticmethod
    def reject_return(log_id):
        return True, "Return rejected."

    @staticmethod
    def approve_resets(request_ids):
        return True, "Resets approved."

    @staticmethod
    def reject_resets(request_ids):
        return True, "Resets rejected."
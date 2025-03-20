from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import pyotp
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
import logging
import qrcode
import io
import base64
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)  # Enable CORS
bcrypt = Bcrypt(app)

# JWT Configuration
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "supersecret")  # Change this in production!
jwt = JWTManager(app)

# Database configuration
config_db_config = {
    'host': os.getenv('DB_HOST'),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'port': os.getenv('DB_PORT')
}

def get_db_connection():
    return psycopg2.connect(**config_db_config)

@app.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == "OPTIONS":
        return jsonify({"message": "CORS Preflight OK"}), 200

    data = request.json
    email = data.get('email')
    password = data.get('password', 'Admin@123')  # Default password for admin
    role = data.get('role', 'user')
    location = data.get('location')
    user_ip = request.remote_addr

    if not email:
        return jsonify({"message": "Email is required!"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    # Check admin limit
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = cur.fetchone()[0]

    if role == "admin" and admin_count >= 1:
        return jsonify({"message": "Admin limit reached! Only one admin is allowed."}), 400

    status = "approved" if role == "admin" else "pending"
    pwd_changed = False if role == "admin" else True  # Set pwdchanged to FALSE for admin

    # Generate OTP Secret
    otp_secret = pyotp.random_base32()

    # Hash Password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        cur.execute(
            "INSERT INTO users (email, password_hash, role, status, otp_secret, ip_address, location, pwdchanged) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING otp_secret",
            (email, hashed_password, role, status, otp_secret, user_ip, location, pwd_changed)
        )
        otp_secret = cur.fetchone()[0]
        conn.commit()

        # Generate OTP URI
        otp_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(email, issuer_name="MyApp")

        # Generate QR Code
        qr = qrcode.make(otp_uri)
        img_buffer = io.BytesIO()
        qr.save(img_buffer, format="PNG")
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        logger.info(f"User registered: {email}, role: {role}")
        return jsonify({"message": "Registration successful!", "qr_code": qr_base64})

    except psycopg2.IntegrityError:
        logger.error(f"Email already registered: {email}")
        return jsonify({"message": "Email already registered!"}), 400
    finally:
        cur.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    otp_code = data.get('otp_code')
    requested_role = data.get('role')
    location = data.get('location')

    # Validation with detailed logging
    if not all([email, password, requested_role]):
        logger.warning(f"Login failed: Missing fields - email={email}, password={'***' if password else None}, role={requested_role}")
        return jsonify({"message": "Email, password, and role are required!"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Updated query to include rejectreason
        cur.execute("""
            SELECT password_hash, otp_secret, role, status, location, pwdchanged, rejectreason 
            FROM users 
            WHERE email = %s
        """, (email,))
        user = cur.fetchone()

        if not user:
            logger.info(f"Login failed: User not found - {email}")
            return jsonify({"message": "User not found!"}), 400

        password_hash, otp_secret, actual_role, status, stored_location, pwdchanged, rejectreason = user

        # Check status and return rejectreason if rejected
        if status == "rejected":
            logger.info(f"Login failed: Account rejected - {email}, reason: {rejectreason}")
            return jsonify({
                "message": "Your account has been rejected!",
                "reject_reason": rejectreason or "No specific reason provided"
            }), 403
        elif status != "approved":
            logger.info(f"Login failed: Account not approved - {email}")
            return jsonify({"message": "Your account is not approved yet!"}), 403

        # Proceed with other validation checks
        if requested_role != actual_role:
            logger.info(f"Login failed: Role mismatch for {email} - requested: {requested_role}, actual: {actual_role}")
            return jsonify({"message": f"Invalid role! You are registered as a {actual_role}."}), 403
        if stored_location != location:
            logger.info(f"Login failed: Location mismatch for {email} - stored: {stored_location}, provided: {location}")
            return jsonify({"message": "Location does not match!"}), 403
        if not bcrypt.check_password_hash(password_hash, password):
            logger.info(f"Login failed: Invalid password - {email}")
            return jsonify({"message": "Invalid password!"}), 400
        if actual_role == "admin" and not pwdchanged:
            logger.info(f"Login failed: Default password not reset - {email}")
            return jsonify({"message": "You are using the default password. Please reset your password before logging in."}), 403
        if not otp_code:
            logger.info(f"Login failed: OTP code required - {email}")
            return jsonify({"message": "2FA Code required!"}), 400
        if not pyotp.TOTP(otp_secret).verify(otp_code):
            logger.info(f"Login failed: Invalid OTP - {email}")
            return jsonify({"message": "Invalid 2FA Code!"}), 400

        # Generate JWT token with email as identity and role as a claim
        token = create_access_token(identity=email, additional_claims={"role": actual_role})
        refresh_token = create_refresh_token(identity=email, additional_claims={"role": actual_role})
        logger.info(f"Login successful: {email}, role: {actual_role}")
        return jsonify({
            "message": "Login successful!",
            "token": token,
            "refresh_token": refresh_token,
            "role": actual_role,
            "pwdChanged": pwdchanged
        })

    except Exception as e:
        logger.error(f"Login error for {email}: {str(e)}", exc_info=True)
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/verify-2fa', methods=['POST'])
def verify_2fa():
    data = request.json
    email = data.get('email')
    otp_code = data.get('otp_code')

    if not email or not otp_code:
        return jsonify({"message": "Email and OTP code are required!"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT otp_secret FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if not user:
            return jsonify({"message": "User not found!"}), 404

        otp_secret = user[0]
        totp = pyotp.TOTP(otp_secret)
        if not totp.verify(otp_code):
            return jsonify({"message": "Invalid 2FA Code!"}), 400

        return jsonify({"success": True, "message": "2FA verification successful!"})
    except Exception as e:
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    old_password = data.get('oldPassword')
    new_password = data.get('newPassword')

    if not email or not old_password or not new_password:
        return jsonify({"message": "Email, old password, and new password are required!"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT password_hash, otp_secret, role FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if not user:
            return jsonify({"message": "User not found!"}), 404

        password_hash, current_otp_secret, role = user

        if not bcrypt.check_password_hash(password_hash, old_password):
            return jsonify({"message": "Invalid old password!"}), 400

        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        new_otp_secret = pyotp.random_base32()

        cur.execute("""
            UPDATE users
            SET password_hash = %s, otp_secret = %s, pwdchanged = TRUE
            WHERE email = %s
        """, (hashed_password, new_otp_secret, email))
        conn.commit()

        totp = pyotp.TOTP(new_otp_secret)
        qr_data = totp.provisioning_uri(name=email, issuer_name="MyApp")
        qr = qrcode.make(qr_data)
        img_buffer = io.BytesIO()
        qr.save(img_buffer, format="PNG")
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        return jsonify({
            "message": "Password reset successful! Scan the new QR code to set up 2FA.",
            "qr_code": qr_base64
        })

    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
    new_password = data.get('new_password')
    otp_code = data.get('otp_code')

    if not email or not new_password or not otp_code:
        return jsonify({"message": "Email, new password, and 2FA code are required!"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT otp_secret FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if not user:
            return jsonify({"message": "User not found!"}), 404

        otp_secret = user[0]
        totp = pyotp.TOTP(otp_secret)
        if not totp.verify(otp_code):
            return jsonify({"message": "Invalid 2FA Code!"}), 400

        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        cur.execute("""
            UPDATE users
            SET password_hash = %s
            WHERE email = %s
        """, (hashed_password, email))
        conn.commit()

        return jsonify({"message": "Password updated successfully!"})

    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/check-admin-role', methods=['GET'])
def check_admin_role():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cur.fetchone()[0]
        return jsonify({"adminExists": admin_count > 0})
    except Exception as e:
        logger.error(f"Check admin role error: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/user-management', methods=['GET'])
@jwt_required()
def get_pending_users():
    identity = get_jwt_identity()  # Email
    claims = get_jwt()
    role = claims.get("role")
    if role != "admin":
        logger.warning(f"Access denied for {identity}: not an admin")
        return jsonify({"message": "Access denied! Admins only."}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT email, ip_address, location FROM users WHERE status = 'pending' and role = 'user'")
        pending_users = [{"email": row[0], "ip_address": row[1], "location": row[2]} for row in cur.fetchall()]
        logger.info(f"Pending users fetched: {pending_users}")
        return jsonify({"pending_users": pending_users})
    except Exception as e:
        logger.error(f"Error fetching pending users: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/approve-user', methods=['POST'])
@jwt_required()
def approve_user():
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    if role != "admin":
        logger.warning(f"Access denied for {identity}: not an admin")
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.json
    user_id = data.get("email")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        approved_time = datetime.utcnow()
        cur.execute("""
            UPDATE users 
            SET status = 'approved', approved_at = %s 
            WHERE email = %s
        """, (approved_time, user_id))
        conn.commit()
        logger.info(f"User {user_id} approved by {identity} at {approved_time}")
        return jsonify({"message": "User approved successfully!"})
    except Exception as e:
        logger.error(f"Error approving user {user_id}: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/reject-user', methods=['POST'])
@jwt_required()
def reject_user():
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    if role != "admin":
        logger.warning(f"Access denied for {identity}: not an admin")
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.json
    user_id = data.get("email")
    reject_reason = data.get("rejectreason")

    if not reject_reason:
        logger.warning(f"Reject reason missing for {user_id}")
        return jsonify({"message": "Reject reason is required!"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET status = 'rejected', rejectreason = %s
            WHERE email = %s
        """, (reject_reason, user_id))
        conn.commit()
        logger.info(f"User {user_id} rejected by {identity} with reason: {reject_reason}")
        return jsonify({"message": "User rejected successfully!"})
    except Exception as e:
        logger.error(f"Error rejecting user {user_id}: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/all-users', methods=['GET'])
@jwt_required()
def get_all_users():
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    if role != "admin":
        logger.warning(f"Access denied for {identity}: not an admin")
        return jsonify({"message": "Access denied! Admins only."}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT email, role, status, location FROM users")
        all_users = [{"email": row[0], "role": row[1], "status": row[2], "location": row[3]} for row in cur.fetchall()]
        logger.info(f"All users fetched by {identity}: {all_users}")
        return jsonify({"all_users": all_users})
    except Exception as e:
        logger.error(f"Error fetching all users: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/disable-user', methods=['POST'])
@jwt_required()
def disable_user():
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    if role != "admin":
        logger.warning(f"Access denied for {identity}: not an admin")
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.json
    email = data.get('email')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET status = 'disabled' WHERE email = %s", (email,))
        conn.commit()
        logger.info(f"User {email} disabled by {identity}")
        return jsonify({"message": "User disabled successfully!"})
    except Exception as e:
        logger.error(f"Error disabling user {email}: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/refresh-token', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    identity = get_jwt_identity()  # Email
    claims = get_jwt()
    role = claims.get("role")
    new_token = create_access_token(identity=identity, additional_claims={"role": role})
    logger.info(f"Token refreshed for {identity}")
    return jsonify({"access_token": new_token})

if __name__ == '__main__':
    app.run(host=os.getenv('LOGIN_FLASK_HOST'), port=os.getenv('LOGIN_FLASK_PORT'), debug=os.getenv('LOGIN_FLASK_DEBUG') == 'True')

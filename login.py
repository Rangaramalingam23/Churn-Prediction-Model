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

        cur.close()
        conn.close()

        # Generate OTP URI
        otp_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(email, issuer_name="MyApp")

        # Generate QR Code
        qr = qrcode.make(otp_uri)
        img_buffer = io.BytesIO()
        qr.save(img_buffer, format="PNG")
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        return jsonify({"message": "Registration successful!", "qr_code": qr_base64})

    except psycopg2.IntegrityError:
        return jsonify({"message": "Email already registered!"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    otp_code = data.get('otp_code')  # OTP entered by user
    requested_role = data.get('role')  # Role selected in frontend (admin/user)
    location = data.get('location')  # New field for user location

    if not email or not password or not requested_role:
        return jsonify({"message": "Email, password, and role are required!"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch user details, including pwdchanged
        cur.execute("""
            SELECT password_hash, otp_secret, role, status, location, pwdchanged 
            FROM users 
            WHERE email = %s
        """, (email,))
        user = cur.fetchone()

        if not user:
            return jsonify({"message": "User not found!"}), 400

        password_hash, otp_secret, actual_role, status, stored_location, pwdchanged = user

        # Check if the user is approved
        if status != "approved":
            return jsonify({"message": "Your account is not approved yet!"}), 403

        # Check if the role matches
        if requested_role != actual_role:
            return jsonify({"message": f"Invalid role! You are registered as a {actual_role}."}), 403

        # Check if the location matches
        if stored_location != location:
            return jsonify({"message": "Location does not match!"}), 403

        # Verify password
        if not bcrypt.check_password_hash(password_hash, password):
            return jsonify({"message": "Invalid password!"}), 400

        # If the user is an admin and pwdchanged is False, block login
        if actual_role == "admin" and not pwdchanged:
            return jsonify({"message": "You are using the default password. Please reset your password before logging in."}), 403

        # If OTP is not provided yet, ask for it
        if not otp_code:
            return jsonify({"message": "2FA Code required!"}), 400

        # Verify OTP
        totp = pyotp.TOTP(otp_secret)
        if not totp.verify(otp_code):
            return jsonify({"message": "Invalid 2FA Code!"}), 400

        # Generate JWT token
        token = create_access_token(identity={"email": email, "role": actual_role})
        return jsonify({
            "message": "Login successful!",
            "token": token,
            "role": actual_role,
            "pwdChanged": pwdchanged  # Return the actual value of pwdchanged
        })

    except Exception as e:
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
    old_password = data.get('oldPassword')  # Old password entered by the user
    new_password = data.get('newPassword')  # New password for reset

    if not email or not old_password or not new_password:
        return jsonify({"message": "Email, old password, and new password are required!"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Fetch user details
        cur.execute("SELECT password_hash, otp_secret, role FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if not user:
            return jsonify({"message": "User not found!"}), 404

        password_hash, current_otp_secret, role = user

        # Verify the old password
        if not bcrypt.check_password_hash(password_hash, old_password):
            return jsonify({"message": "Invalid old password!"}), 400

        # Hash the new password
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        # Generate a new OTP secret
        new_otp_secret = pyotp.random_base32()

        # Update the password, OTP secret, and set pwdchanged to TRUE
        cur.execute("""
            UPDATE users
            SET password_hash = %s, otp_secret = %s, pwdchanged = TRUE
            WHERE email = %s
        """, (hashed_password, new_otp_secret, email))
        conn.commit()

        # Generate a QR code for the new OTP secret
        totp = pyotp.TOTP(new_otp_secret)
        qr_data = totp.provisioning_uri(name=email, issuer_name="MyApp")

        # Create a QR code image
        qr = qrcode.make(qr_data)
        img_buffer = io.BytesIO()
        qr.save(img_buffer, format="PNG")
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        return jsonify({
            "message": "Password reset successful! Scan the new QR code to set up 2FA.",
            "qr_code": qr_base64
        })

    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error in reset_password: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
    new_password = data.get('new_password')
    otp_code = data.get('otp_code')  # 2FA code entered by the user

    if not email or not new_password or not otp_code:
        return jsonify({"message": "Email, new password, and 2FA code are required!"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Fetch user details
        cur.execute("SELECT otp_secret FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if not user:
            return jsonify({"message": "User not found!"}), 404

        otp_secret = user[0]

        # Verify 2FA code
        totp = pyotp.TOTP(otp_secret)
        if not totp.verify(otp_code):
            return jsonify({"message": "Invalid 2FA Code!"}), 400

        # Hash the new password
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        # Update the password in the database
        cur.execute("""
            UPDATE users
            SET password_hash = %s
            WHERE email = %s
        """, (hashed_password, email))
        conn.commit()

        return jsonify({"message": "Password updated successfully!"})

    except Exception as e:
        # Log the full error for debugging
        app.logger.error(f"Error in /forgot-password: {str(e)}")
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
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/refresh-token', methods=['POST'])
@jwt_required(refresh=True)  # Allow refresh tokens to be used here
def refresh_token():
    identity = get_jwt_identity()
    new_token = create_access_token(identity=identity)
    return jsonify({"access_token": new_token})
    
@app.route('/user-management', methods=['GET'])
@jwt_required()
def get_pending_users():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied! Admins only."}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT email, ip_address, location FROM users WHERE status = 'pending' and role = 'user' ")
        pending_users = [
            {"email": row[0], "ip_address": row[1], "location": row[2]}  # Ensure correct column order
            for row in cur.fetchall()
        ]
        logging.info(f"Pending users fetched: {pending_users}")
        cur.close()
        conn.close()
        return jsonify({"pending_users": pending_users})
    except Exception as e:
        logging.error(f"Error fetching pending users: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500

@app.route('/approve-user', methods=['POST'])
@jwt_required()
def approve_user():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.json
    user_id = data.get("email")  # Use "email" instead of "user_id"

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Log the user_id being processed
        app.logger.info(f"Approving user with email: {user_id}")

        # Get the current timestamp
        approved_time = datetime.utcnow()

        # Update the user's status to 'approved' and set the approved_at column
        cur.execute("""
            UPDATE users 
            SET status = 'approved', approved_at = %s 
            WHERE email = %s
        """, (approved_time, user_id))
        conn.commit()

        # Log success
        app.logger.info(f"User {user_id} approved successfully at {approved_time}.")

        return jsonify({"message": "User approved successfully!"})
    except Exception as e:
        # Log the error
        app.logger.error(f"Error in /approve-user: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/reject-user', methods=['POST'])
@jwt_required()
def reject_user():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.json
    user_id = data.get("email")  # Use "email" instead of "user_id"
    reject_reason = data.get("rejectreason")  # Get the reject reason

    if not reject_reason:
        return jsonify({"message": "Reject reason is required!"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Update the user's status to 'rejected' and save the reject reason
        cur.execute("""
            UPDATE users
            SET status = 'rejected', rejectreason = %s
            WHERE email = %s
        """, (reject_reason, user_id))
        conn.commit()

        return jsonify({"message": "User rejected successfully!"})
    except Exception as e:
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
    
@app.route('/all-users', methods=['GET'])
@jwt_required()
def get_all_users():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied! Admins only."}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT email, role, status, location FROM users")
        all_users = [
            {"email": row[0], "role": row[1], "status": row[2], "location": row[3]}
            for row in cur.fetchall()
        ]
        cur.close()
        conn.close()
        return jsonify({"all_users": all_users})
    except Exception as e:
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500

@app.route('/disable-user', methods=['POST'])
@jwt_required()
def disable_user():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.json
    email = data.get('email')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET status = 'disabled' WHERE email = %s", (email,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "User disabled successfully!"})
    except Exception as e:
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500

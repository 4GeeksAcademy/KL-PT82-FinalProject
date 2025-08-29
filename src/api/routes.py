import re
from flask import request, jsonify, Blueprint
from api.models import db, User
from flask_cors import CORS
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

api = Blueprint('api', __name__)
CORS(api)

# ----------------------------
# Signup Route
# ----------------------------
@api.route('/signup', methods=['POST'])
def handle_signup():
    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    # Validate required fields
    if not username or not email or not password:
        return jsonify({"error": "Username, email and password are required"}), 400

    # Check uniqueness
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    # Password requirements
    if not (len(password) >= 8 and 
            re.search(r"[A-Z]", password) and 
            re.search(r"[a-z]", password) and 
            re.search(r"[0-9]", password)):
        return jsonify({"error": "Password must be at least 8 chars long and include upper, lower, and number"}), 400

    # Hash password
    hashed_pw = generate_password_hash(password)
    user = User(username=username, email=email, password=hashed_pw, is_active=True)

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User successfully created"}), 201

# ----------------------------
# Login Route
# ----------------------------
@api.route('/login', methods=['POST'])
def handle_login():
    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not password:
        return jsonify({"error": "Password required"}), 400

    # Allow login with either username or email
    user = None
    if username:
        user = User.query.filter_by(username=username).first()
    elif email:
        user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Check password
    if not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid password"}), 401

    # Create JWT token
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "token": access_token,
        "user": user.serialize()
    }), 200

# ----------------------------
# Private Route (requires login)
# ----------------------------
@api.route('/private', methods=['GET'])
@jwt_required()
def handle_private():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Invalid token"}), 401

    return jsonify({"message": f"Welcome back {user.username}!"}), 200

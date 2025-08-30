import re
import time
from flask import request, jsonify, Blueprint
from api.models import db, User, Favorite, Event, FavoriteMember, RSVP
from flask_cors import CORS
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

api = Blueprint('api', __name__)
CORS(api)

# ----------------------------
# Signup Route
# ----------------------------


@api.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")

    if not email or not username or not password:
        return jsonify({"msg": "Missing fields"}), 400

    # Check for existing email or username
    if User.query.filter((User.email == email) | (User.username == username)).first():
        return jsonify({"msg": "Email or username already exists"}), 400

    # Password requirements
    if len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isupper() for c in password):
        return jsonify({"msg": "Password must be at least 8 characters, include a number and an uppercase letter."}), 400

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"msg": "Invalid email format"}), 400

    hashed_pw = generate_password_hash(password)
    user = User(email=email, username=username, password=hashed_pw)
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "User created"}), 201

# ----------------------------
# Login Route
# ----------------------------


login_attempts = {}


@api.route('/login', methods=['POST'])
def handle_login():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    identifier = username or email
    now = time.time()
    attempts = login_attempts.get(identifier, {"count": 0, "last": now})

    # Lockout for 5 minutes after 5 failed attempts
    if attempts["count"] >= 5 and now - attempts["last"] < 300:
        return jsonify({"msg": "Too many login attempts. Try again in 5 minutes."}), 429

    user = None
    if username:
        user = User.query.filter_by(username=username).first()
    elif email:
        user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        attempts["count"] += 1
        attempts["last"] = now
        login_attempts[identifier] = attempts
        return jsonify({"msg": "Invalid credentials"}), 401

    # Reset attempts on success
    login_attempts[identifier] = {"count": 0, "last": now}

    access_token = create_access_token(identity=user.id)
    return jsonify({"msg": "Login successful", "token": access_token}), 200

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

# ----------------------------
# Logout Route (JWT client-side)
# ----------------------------


@api.route('/logout', methods=['POST'])
@jwt_required()
def handle_logout():
    # For JWT, logout is handled by the client (delete token)
    return jsonify({"message": "Logout successful. Please delete your token on the client."}), 200

# ----------------------------
# Get User Profile
# ----------------------------


@api.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.serialize()), 200

# ----------------------------
# Update User Profile
# ----------------------------


@api.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json
    new_username = data.get('username', user.username)
    new_email = data.get('email', user.email)
    profile_photo = data.get('profile_photo', user.profile_photo if hasattr(
        user, 'profile_photo') else None)

    # Validate email format
    if new_email and not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
        return jsonify({"error": "Invalid email format"}), 400

    # Check for unique email/username (exclude current user)
    if User.query.filter(User.id != user_id, User.email == new_email).first():
        return jsonify({"error": "Email already in use"}), 400
    if User.query.filter(User.id != user_id, User.username == new_username).first():
        return jsonify({"error": "Username already in use"}), 400

    user.username = new_username
    user.email = new_email
    if profile_photo is not None:
        user.profile_photo = profile_photo  # Make sure your User model has this field

    db.session.commit()
    return jsonify({"msg": "Profile updated", "user": user.serialize()}), 200

# ----------------------------
# Password Reset Request (stub)
# ----------------------------


@api.route('/password-reset', methods=['POST'])
def password_reset_request():
    data = request.json
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    # Here you would send a reset email (stub)
    return jsonify({"msg": "Password reset link sent (stub)."}), 200

# ----------------------------
# Password Reset (stub)
# ----------------------------


@api.route('/password-reset/<token>', methods=['POST'])
def password_reset(token):
    data = request.json
    new_password = data.get('password')
    if not password_requirements(new_password):
        return jsonify({"msg": "Password must be at least 8 characters, include a number and an uppercase letter."}), 400
    # Here you would verify the token and reset the password (stub)
    return jsonify({"msg": "Password has been reset (stub)."}), 200

# ----------------------------
# Favorites Routes
# ----------------------------


@api.route('/favorites', methods=['POST'])
@jwt_required()
def add_favorite():
    user_id = get_jwt_identity()
    event_id = request.json.get('event_id')
    if not event_id or not Event.query.get(event_id):
        return jsonify({"error": "Event not found"}), 404

    # Prevent duplicate favorites
    if Favorite.query.filter_by(user_id=user_id, event_id=event_id).first():
        return jsonify({"msg": "Already favorited"}), 400

    favorite = Favorite(user_id=user_id, event_id=event_id)
    db.session.add(favorite)
    db.session.commit()
    return jsonify({"msg": "Event favorited", "favorite": favorite.serialize()}), 201


@api.route('/favorites', methods=['GET'])
@jwt_required()
def list_favorites():
    user_id = get_jwt_identity()
    favorites = Favorite.query.filter_by(user_id=user_id).all()
    return jsonify([
        {
            **fav.serialize(),
            "event": Event.query.get(fav.event_id).serialize()
        } for fav in favorites
    ]), 200


@api.route('/favorites/<int:event_id>', methods=['DELETE'])
@jwt_required()
def remove_favorite(event_id):
    user_id = get_jwt_identity()
    favorite = Favorite.query.filter_by(
        user_id=user_id, event_id=event_id).first()
    if not favorite:
        return jsonify({"error": "Favorite not found"}), 404
    db.session.delete(favorite)
    db.session.commit()
    return jsonify({"msg": "Favorite removed"}), 200

# ----------------------------
# Favorite Members Routes
# ----------------------------


@api.route('/favorite-members', methods=['POST'])
@jwt_required()
def add_favorite_member():
    user_id = get_jwt_identity()
    member_id = request.json.get('member_id')
    if not member_id or not User.query.get(member_id):
        return jsonify({"error": "Member not found"}), 404

    if FavoriteMember.query.filter_by(user_id=user_id, member_id=member_id).first():
        return jsonify({"msg": "Already favorited"}), 400

    favorite = FavoriteMember(user_id=user_id, member_id=member_id)
    db.session.add(favorite)
    db.session.commit()
    return jsonify({"msg": "Member favorited", "favorite": favorite.serialize()}), 201


@api.route('/favorite-members', methods=['GET'])
@jwt_required()
def list_favorite_members():
    user_id = get_jwt_identity()
    favorites = FavoriteMember.query.filter_by(user_id=user_id).all()
    return jsonify([
        {
            **fav.serialize(),
            "member": User.query.get(fav.member_id).serialize()
        } for fav in favorites
    ]), 200


@api.route('/favorite-members/<int:member_id>', methods=['DELETE'])
@jwt_required()
def remove_favorite_member(member_id):
    user_id = get_jwt_identity()
    favorite = FavoriteMember.query.filter_by(
        user_id=user_id, member_id=member_id).first()
    if not favorite:
        return jsonify({"error": "Favorite not found"}), 404
    db.session.delete(favorite)
    db.session.commit()
    return jsonify({"msg": "Favorite removed"}), 200


# ----------------------------
# Event CRUD Endpoints
# ----------------------------

@api.route('/events', methods=['POST'])
@jwt_required()
def create_event():
    data = request.get_json()
    name = data.get('name')
    date = data.get('date')
    location = data.get('location')
    if not name or not date or not location:
        return jsonify({"error": "Missing fields"}), 400
    event = Event(name=name, date=date, location=location)
    db.session.add(event)
    db.session.commit()
    return jsonify(event.serialize()), 201


@api.route('/events', methods=['GET'])
def list_events():
    events = Event.query.all()
    return jsonify([event.serialize() for event in events]), 200


@api.route('/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event.serialize()), 200


@api.route('/events/<int:event_id>', methods=['PUT'])
@jwt_required()
def update_event(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    data = request.get_json()
    event.name = data.get('name', event.name)
    event.date = data.get('date', event.date)
    event.location = data.get('location', event.location)
    db.session.commit()
    return jsonify(event.serialize()), 200


@api.route('/events/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_event(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    db.session.delete(event)
    db.session.commit()
    return jsonify({"msg": "Event deleted"}), 200

# ----------------------------
# RSVP Endpoints
# ----------------------------


@api.route('/events/<int:event_id>/rsvp', methods=['POST'])
@jwt_required()
def rsvp_event(event_id):
    user_id = get_jwt_identity()
    response = request.json.get('response')
    if response not in ["yes", "no", "maybe"]:
        return jsonify({"error": "Invalid response"}), 400
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    rsvp = RSVP.query.filter_by(user_id=user_id, event_id=event_id).first()
    if rsvp:
        rsvp.response = response
    else:
        rsvp = RSVP(user_id=user_id, event_id=event_id, response=response)
        db.session.add(rsvp)
    db.session.commit()
    return jsonify(rsvp.serialize()), 200


@api.route('/events/<int:event_id>/rsvp', methods=['GET'])
@jwt_required()
def get_event_rsvps(event_id):
    rsvps = RSVP.query.filter_by(event_id=event_id).all()
    return jsonify([rsvp.serialize() for rsvp in rsvps]), 200


def password_requirements(password):
    return (
        len(password) >= 8 and
        any(c.isdigit() for c in password) and
        any(c.isupper() for c in password)
    )

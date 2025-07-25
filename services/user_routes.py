from flask import Blueprint, request, jsonify
from db import mysql
import MySQLdb.cursors
import bcrypt
from flask import session, current_app
import jwt
import datetime
from middleware.jwt import token_required
import os
import random
from utils.response_helper import success_response, error_response



user = Blueprint('user', __name__, url_prefix='/user')

# Register User
@user.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify(error_response("Nama, email, dan password wajib diisi")), 400

    avatar_folder = os.path.join(os.getcwd(), 'static', 'avatars')
    available_avatars = [f for f in os.listdir(avatar_folder) if os.path.isfile(os.path.join(avatar_folder, f))]
    selected_avatar = random.choice(available_avatars) if available_avatars else None

    avatar_filename = selected_avatar if selected_avatar else None

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (name, email, password, avatar)
            VALUES (%s, %s, %s, %s)
        """, (name, email, hashed_pw, avatar_filename))
        mysql.connection.commit()
        return jsonify(success_response("Registrasi berhasil")), 201
    except MySQLdb.IntegrityError:
        return jsonify(error_response("Email sudah terdaftar")), 409


# Login User
@user.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({"error": "Email dan password wajib diisi"}), 400


    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        token = jwt.encode({
            'id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')

        user_data = {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "face_shape": user['face_shape'],
            "avatar": user["avatar"]
        }

        return jsonify(success_response("Login berhasil", {
            "token": token,
            "user": user_data
        })), 200
    return jsonify(error_response("Email atau password salah")), 401

@user.route('/logout', methods=['DELETE'])
def logout():
    session.clear()
    return jsonify(success_response("Logout berhasil")), 200

@user.route('/profile', methods=['GET'])
@token_required
def profile():
    user_id = request.user_id
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, name, email, face_shape, avatar FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify(error_response("User tidak ditemukan")), 404

    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "face_shape": user["face_shape"],
        "avatar": user["avatar"]
    }), 200
    
    
@user.route('/avatars', methods=['GET'])
def get_avatars():
    avatar_dir = os.path.join(os.getcwd(), 'static', 'avatars')

    if not os.path.exists(avatar_dir):
        return jsonify([])

    files = os.listdir(avatar_dir)
    avatars = [f for f in files if os.path.isfile(os.path.join(avatar_dir, f))]
    return jsonify(avatars)  


@user.route('/profile/avatar', methods=['PUT'])
@token_required
def update_avatar():
    user_id = request.user_id
    data = request.get_json()
    avatar = data.get('avatar')

    if not avatar:
        return jsonify(error_response("Avatar tidak boleh kosong")), 400

    if avatar.startswith('/static/avatars/'):
        avatar = avatar.replace('/static/avatars/', '')

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE users SET avatar = %s WHERE id = %s", (avatar, user_id))
    mysql.connection.commit()

    return jsonify(success_response("Avatar berhasil diperbarui")), 200



@user.route('/profile/update', methods=['PUT'])
@token_required
def update_profile():
    user_id = request.user_id
    data = request.get_json()

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')  

    if not all([name, email]):
        return jsonify(error_response("Name dan Email wajib diisi")), 400

    cursor = mysql.connection.cursor()

    try:
        if password:
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("""
                UPDATE users
                SET name = %s, email = %s, password = %s
                WHERE id = %s
            """, (name, email, hashed_pw, user_id))
        else:
            cursor.execute("""
                UPDATE users
                SET name = %s, email = %s
                WHERE id = %s
            """, (name, email, user_id))

        mysql.connection.commit()
        return jsonify(success_response("Profil berhasil diperbarui")), 200

    except MySQLdb.IntegrityError:
        return jsonify(error_response("Email sudah digunakan oleh pengguna lain")), 409


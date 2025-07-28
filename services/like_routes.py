from flask import Blueprint, request, jsonify
from db import mysql
import MySQLdb.cursors
import json
from middleware.jwt import token_required  

likes = Blueprint('likes', __name__, url_prefix='/likes')


# Fungsi untuk parse JSON fields
def parse_json_fields(row, fields):
    for field in fields:
        if row.get(field):
            try:
                row[field] = json.loads(row[field])
            except Exception:
                pass
    return row


# Toggle like/unlike
@likes.route('/', methods=['POST'])
@token_required
def toggle_like():
    user_id = request.user_id
    data = request.get_json()
    hairstyle_id = data.get('hairstyle_id')

    if not hairstyle_id:
        return jsonify({'error': 'hairstyle_id wajib diisi'}), 400

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT id FROM hairstyles WHERE id = %s", (hairstyle_id,))
    if cursor.fetchone() is None:
        return jsonify({'error': f'Hairstyle dengan id {hairstyle_id} tidak ditemukan'}), 404

    cursor.execute("""
        SELECT id FROM user_likes 
        WHERE user_id = %s AND hairstyle_id = %s
    """, (user_id, hairstyle_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            DELETE FROM user_likes 
            WHERE user_id = %s AND hairstyle_id = %s
        """, (user_id, hairstyle_id))
        mysql.connection.commit()
        return jsonify({'message': 'Unliked'}), 200
    else:
        cursor.execute("""
            INSERT INTO user_likes (user_id, hairstyle_id) 
            VALUES (%s, %s)
        """, (user_id, hairstyle_id))
        mysql.connection.commit()
        return jsonify({'message': 'Liked'}), 200


# Get liked hairstyles by authenticated user
@likes.route('/', methods=['GET'])
@token_required
def get_liked_hairstyles():
    user_id = request.user_id
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT h.*, 
            MAX(ul.id) AS user_like_id,
            (SELECT COUNT(*) FROM user_likes WHERE hairstyle_id = h.id) AS likes,
            1 AS is_liked
        FROM hairstyles h
        JOIN user_likes ul ON h.id = ul.hairstyle_id
        WHERE ul.user_id = %s
        GROUP BY h.id
        ORDER BY user_like_id DESC
    """, (user_id,))


    liked_styles = cursor.fetchall()
    processed_styles = []

    for s in liked_styles:
        s = parse_json_fields(s, ['face_shape'])

        # Ambil folder berdasarkan face shape pertama (jika ada)
        face_shape = s['face_shape'][0] if s.get('face_shape') else 'unknown'

        s['image'] = f"/hair_cut_recommendation/{face_shape}/{s['image']}"
        # Update image URL dan konversi boolean
        s['is_liked'] = True
        s['likes'] = int(s['likes'])

        processed_styles.append(s)

    return jsonify({
        "user_id": user_id,
        "liked_hairstyles": processed_styles
    })

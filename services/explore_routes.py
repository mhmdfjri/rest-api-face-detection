from flask import Blueprint, request, jsonify
from db import mysql
import MySQLdb.cursors
import json
from middleware.jwt import token_required

explore = Blueprint('explore', __name__, url_prefix='/explore')


# Fungsi untuk mengubah string JSON menjadi list/dict Python
def parse_json_fields(row, fields):
    for field in fields:
        if row.get(field):
            try:
                row[field] = json.loads(row[field])
            except Exception:
                pass
    return row


# Endpoint untuk pencarian hairstyle (dengan JWT)
@explore.route('', methods=['GET'])
@token_required
def index():
    user_id = request.user_id
    search_query = request.args.get('search', '').strip()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if search_query:
        cursor.execute("""
            SELECT h.*, 
                (SELECT COUNT(*) FROM user_likes WHERE hairstyle_id = h.id) AS likes,
                EXISTS(
                  SELECT 1 FROM user_likes ul
                  WHERE ul.user_id = %s AND ul.hairstyle_id = h.id
                ) AS is_liked
            FROM hairstyles h
            WHERE h.name LIKE %s
            ORDER BY likes DESC
        """, (user_id, '%' + search_query + '%'))
        search_results = cursor.fetchall()
    else:
        search_results = []

    processed_results = []
    for h in search_results:
        h = parse_json_fields(h, ['face_shape'])

        face_shape_list = h.get('face_shape', [])
        folder = face_shape_list[0] if face_shape_list else 'Unknown'

        h['image'] = f"/hair_cut_recommendation/{folder}/{h['image']}"
        h['is_liked'] = bool(h['is_liked'])

        processed_results.append(h)

    return jsonify({
        "search_results": processed_results
    })



# Endpoint untuk menampilkan hairstyle populer (dengan JWT)
@explore.route('/popular', methods=['GET'])
@token_required
def popular_hairstyles():
    user_id = request.user_id
    limit = request.args.get('limit', default=6, type=int)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT h.*, 
            (SELECT COUNT(*) FROM user_likes WHERE hairstyle_id = h.id) AS likes,
            EXISTS(
              SELECT 1 FROM user_likes ul
              WHERE ul.user_id = %s AND ul.hairstyle_id = h.id
            ) AS is_liked
        FROM hairstyles h
        ORDER BY likes DESC
        LIMIT %s
    """, (user_id, limit))
    popular = cursor.fetchall()

    processed_popular = []
    for h in popular:
        h = parse_json_fields(h, ['face_shape'])

        face_shape_list = h.get('face_shape', [])
        folder = face_shape_list[0] if face_shape_list else 'Unknown'

        h['image'] = f"/hair_cut_recommendation/{folder}/{h['image']}"
        h['is_liked'] = bool(h['is_liked'])  # pastikan boolean
        processed_popular.append(h)

    return jsonify({
        "popular": processed_popular
    })

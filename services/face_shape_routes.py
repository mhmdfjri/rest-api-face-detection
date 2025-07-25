import os
import cv2
import json
import numpy as np
import datetime
import MySQLdb.cursors
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image as keras_image
import mediapipe as mp
from db import mysql
from middleware.jwt import token_required
from flask import url_for

face_shape = Blueprint('face_shape', __name__, url_prefix='/face-shape')

UPLOAD_FOLDER = 'static/uploads'
ICON_FOLDER = 'icon_face_shape'
MODEL_PATH = 'MyModel.keras'

# Load model once
model = load_model(MODEL_PATH)
face_shape_labels = ['Heart', 'Oblong', 'Oval', 'Round', 'Square']
mp_face_detection = mp.solutions.face_detection


def has_face(img_path):
    img = cv2.imread(img_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as detector:
        result = detector.process(img_rgb)
        return result.detections is not None and len(result.detections) > 0


def predict_face_shape(img_path):
    img = keras_image.load_img(img_path, target_size=(224, 224))
    img_array = keras_image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) / 255.0
    prediction = model.predict(img_array)
    return face_shape_labels[np.argmax(prediction)]

def parse_json_fields(row, fields):
    for field in fields:
        if row.get(field):
            try:
                row[field] = json.loads(row[field])
            except Exception:
                pass
    return row


@face_shape.route('/upload', methods=['POST'])
@token_required
def upload_and_detect():
    user_id = request.user_id
    file = request.files.get('image')

    if not file or file.filename == '':
        return jsonify({"error": "Gambar harus diunggah"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file.save(filepath)

    if not has_face(filepath):
        os.remove(filepath)
        return jsonify({"error": "Wajah tidak terdeteksi"}), 400

    shape = predict_face_shape(filepath)
    os.remove(filepath)

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE users SET face_shape = %s WHERE id = %s", (shape, user_id))
    mysql.connection.commit()

    icon_url = url_for('static', filename=f'icon_face_shape/{shape.lower()}.png')

    return jsonify({
        "face_shape": shape,
        "face_icon": icon_url
    })


@face_shape.route('/recommend', methods=['GET'])
@token_required
def recommend():
    user_id = request.user_id
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT face_shape FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user or not user['face_shape']:
        return jsonify({"error": "Bentuk wajah belum dideteksi"}), 404

    face_shape_val = user['face_shape']
    face_shape_json = json.dumps([face_shape_val])

    cursor.execute("""
        SELECT h.*,
            COUNT(ul.id) AS likes,
            EXISTS (
                SELECT 1 FROM user_likes ul2 
                WHERE ul2.hairstyle_id = h.id AND ul2.user_id = %s
            ) AS is_liked
        FROM hairstyles h
        LEFT JOIN user_likes ul ON h.id = ul.hairstyle_id
        WHERE JSON_CONTAINS(h.face_shape, %s)
        GROUP BY h.id
        ORDER BY likes DESC
    """, (user_id, face_shape_json))

    styles = cursor.fetchall()
    processed_styles = []

    for s in styles:
        s = parse_json_fields(s, ['face_shape'])

        face_shape_list = s.get('face_shape', [])
        folder = face_shape_list[0] if face_shape_list else 'Unknown'
        s['image'] = f"/hair_cut_recommendation/{folder}/{s['image']}"

        s['likes'] = int(s['likes'])
        s['is_liked'] = bool(s['is_liked'])
        processed_styles.append(s)


    return jsonify({
        "face_shape": face_shape_val,
        "face_icon": url_for('static', filename=f'icon_face_shape/{face_shape_val.lower()}.png'),
        "recommendations": processed_styles
    })

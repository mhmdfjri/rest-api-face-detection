import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from db import mysql
import MySQLdb.cursors
from middleware.auth import login_required
import json

hairstyle = Blueprint('hairstyle', __name__, url_prefix='/hairstyles')


@hairstyle.route('/')
@login_required
def index():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            h.*, 
            COUNT(ul.id) AS like_count 
        FROM 
            hairstyles h
        LEFT JOIN 
            user_likes ul ON h.id = ul.hairstyle_id
        GROUP BY 
            h.id
        ORDER BY 
            h.name ASC
    """)
    data = cursor.fetchall()

    for h in data:
        h['face_shape'] = json.loads(h['face_shape']) if h['face_shape'] else []
        h['like_count'] = h['like_count'] or 0

    admin_id = session.get('id')
    cursor.execute('SELECT name FROM admin WHERE id = %s', (admin_id,))
    admin = cursor.fetchone()
    name = admin['name'] if admin else 'Admin'

    return render_template(
        'hairstyle/index.html',
        hairstyles=data,
        name=name,
        active_menu='hairstyle'
    )



@hairstyle.route('/create')
@login_required
def create():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    admin_id = session.get('id')
    cursor.execute('SELECT name FROM admin WHERE id = %s', (admin_id,))
    admin = cursor.fetchone()
    name = admin['name'] if admin else 'Admin'

    return render_template(
        'hairstyle/create.html',
        name=name,
        active_menu='hairstyle'
    )


@hairstyle.route('/store', methods=['POST'])
@login_required
def store():
    name = request.form.get('hairstyleName')
    face_shapes = request.form.getlist('faceShape')  
    image = request.files.get('hairstyleImage')

    if not image or image.filename == '':
        flash("Gambar harus dipilih", "error")
        return redirect(url_for('hairstyle.index'))

    filename = secure_filename(image.filename)

    for shape in face_shapes:
        folder_path = os.path.join('static', 'hair_cut_recommendation', shape)
        os.makedirs(folder_path, exist_ok=True)
        image_path = os.path.join(folder_path, filename)
        image.save(image_path)


    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO hairstyles (name, image, face_shape)
        VALUES (%s, %s, CAST(%s AS JSON))
    """, (
        name,
        filename, 
        json.dumps(face_shapes),
    ))
    mysql.connection.commit()

    flash("Hairstyle berhasil ditambahkan", "success")
    return redirect(url_for('hairstyle.index'))

@hairstyle.route('/edit/<int:id>')
@login_required
def edit(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Ambil data hairstyle berdasarkan ID
    cursor.execute("SELECT * FROM hairstyles WHERE id = %s", (id,))
    h = cursor.fetchone()

    if not h:
        flash("Data tidak ditemukan", "error")
        return redirect(url_for('hairstyle.index'))

    h['face_shape'] = json.loads(h['face_shape']) if h['face_shape'] else []

    # Ambil nama admin
    admin_id = session.get('id')
    cursor.execute('SELECT name FROM admin WHERE id = %s', (admin_id,))
    admin = cursor.fetchone()
    name = admin['name'] if admin else 'Admin'

    return render_template(
        'hairstyle/edit.html',
        hairstyle=h,
        name=name,
        active_menu='hairstyle'
    )


@hairstyle.route('/update/<int:id>', methods=['POST'])
@login_required
def update(id):
    name = request.form.get('hairstyleName')
    face_shapes = request.form.getlist('faceShape')
    image = request.files.get('hairstyleImage')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT image, face_shape FROM hairstyles WHERE id = %s", (id,))
    old_data = cursor.fetchone()
    old_filename = old_data['image'] if old_data else None
    
    old_face_shapes = json.loads(old_data['face_shape']) if old_data and old_data['face_shape'] else []

    filename = old_filename  

    if image and image.filename != '':
        filename = secure_filename(image.filename)
        
        if old_filename:
            for shape in old_face_shapes:
                try:
                    old_path = os.path.join('static', 'hair_cut_recommendation', shape, old_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception as e:
                    print(f"Error {old_path}: {e}") 

        for shape in face_shapes:
            folder_path = os.path.join('static', 'hair_cut_recommendation', shape)
            os.makedirs(folder_path, exist_ok=True)
            image_path = os.path.join(folder_path, filename)
            
            image.stream.seek(0)
            image.save(image_path)

    cursor.execute("""
        UPDATE hairstyles
        SET name=%s, image=%s, face_shape=CAST(%s AS JSON)
        WHERE id=%s
    """, (
        name,
        filename,
        json.dumps(face_shapes),
        
        id
    ))
    mysql.connection.commit()

    flash("Data hairstyle berhasil diperbarui", "success")
    return redirect(url_for('hairstyle.index'))

@hairstyle.route('/delete/<int:id>', methods=['DELETE'])
@login_required
def delete(id):
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT image, face_shape FROM hairstyles WHERE id = %s", (id,))
    hairstyle_to_delete = cursor.fetchone()

    if not hairstyle_to_delete:
        flash("Data hairstyle tidak ditemukan.", "error")
        return redirect(url_for('hairstyle.index'))

    filename = hairstyle_to_delete.get('image')
    face_shapes_json = hairstyle_to_delete.get('face_shape')

    if filename and face_shapes_json:
        try:
            face_shapes = json.loads(face_shapes_json)
            for shape in face_shapes:
                file_path = os.path.join('static', 'hair_cut_recommendation', shape, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            print(f"Gagal menghapus file {filename}. Error: {e}")

    cursor.execute("DELETE FROM hairstyles WHERE id = %s", (id,))
    mysql.connection.commit()

    # Saat dipanggil via Fetch, redirect ini tidak akan diikuti browser,
    # tapi kita akan handle redirect di JavaScript. Respon sukses sudah cukup.
    flash("Data hairstyle berhasil dihapus.", "success")
    return {"message": "success"}, 200



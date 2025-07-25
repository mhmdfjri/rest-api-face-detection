from flask import Blueprint, render_template, request, redirect, url_for, session
from db import mysql
import MySQLdb.cursors
from middleware.auth import login_required  
import bcrypt
import json

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password'].encode('utf-8')  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM admin WHERE email = %s', (email,))
        account = cursor.fetchone()
        if account and bcrypt.checkpw(password, account['password'].encode('utf-8')):
            session['loggedin'] = True
            session['id'] = account['id']
            session['name'] = account['name']
            return redirect(url_for('admin.dashboard'))
        else:
            msg = 'Email atau password salah.'
    return render_template('login.html', msg=msg)

@admin.route('/dashboard')
@login_required
def dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT name FROM admin WHERE id = %s', (session['id'],))
    admin = cursor.fetchone()
    name = admin['name'] if admin else 'Admin'

    cursor.execute('SELECT COUNT(*) AS total FROM hairstyles')
    total_hairstyle = cursor.fetchone()['total']

    cursor.execute('SELECT COUNT(*) AS total FROM users')
    total_users = cursor.fetchone()['total']

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
            like_count DESC
        LIMIT 10
    """)
    top_hairstyles = cursor.fetchall()

    for h in top_hairstyles:
        h['face_shape'] = json.loads(h['face_shape']) if h['face_shape'] else []

    return render_template(
        'dashboard.html',
        name=name,
        total_hairstyle=total_hairstyle,
        total_users=total_users,
        top_hairstyles=top_hairstyles, 
        active_menu='dashboard'
    )


@admin.route('/users', methods=['GET'])
@login_required
def list_users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, name, email, face_shape, avatar FROM users")
    users = cursor.fetchall()

    return render_template('users.html', users=users, active_menu='users')


@admin.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('admin.login'))

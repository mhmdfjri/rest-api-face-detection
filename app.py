from flask import Flask, send_from_directory, redirect
from db import init_mysql
from services import register_routes
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback_dev_key')

init_mysql(app)
register_routes(app)

@app.route('/')
def admin():
    return redirect('/admin')

# untuk akses icon wajah
@app.route('/icon_face_shape/<filename>')
def serve_icon_face(filename):
    return send_from_directory('icon_face_shape', filename)

# untuk akses gambar rekomendasi haircut
@app.route('/hair_cut_recommendation/<face_shape>/<filename>')
def serve_haircut(face_shape, filename):
    return send_from_directory(f'hair_cut_recommendation/{face_shape}', filename)

from flask import send_from_directory

@app.route('/avatars/<filename>')
def serve_avatar(filename):
    return send_from_directory('avatars', filename)



if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000, debug=True)


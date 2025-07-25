from .admin_routes import admin
from .hairstyle_routes import hairstyle
from .user_routes import user
from .face_shape_routes import face_shape
from .like_routes import likes
from .explore_routes import explore

def register_routes(app):
    app.register_blueprint(admin)
    app.register_blueprint(hairstyle)
    app.register_blueprint(user)
    app.register_blueprint(face_shape)
    app.register_blueprint(likes)
    app.register_blueprint(explore)

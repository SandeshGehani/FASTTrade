from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()
socketio = SocketIO(cors_allowed_origins="*")

def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Configure Flask-Mail
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
    
    # Only log email config in development mode
    if app.config.get('DEBUG'):
        print("Email Configuration:")
        print("MAIL_USERNAME:", app.config['MAIL_USERNAME'])
        print("MAIL_PASSWORD:", "***" if app.config['MAIL_PASSWORD'] else "Not set")
    
    # Only initialize mail if credentials are provided
    if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
        mail.init_app(app)
        if app.config.get('DEBUG'):
            print("Mail extension initialized successfully")
    else:
        if app.config.get('DEBUG'):
            print("Warning: Email credentials not set. Email functionality will not work.")

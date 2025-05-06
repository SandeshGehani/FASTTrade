import re
import random
import string
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from flask_mail import Mail
from flask_mail import Message as MailMessage
from extensions import mail, init_extensions

# --- Flask App Setup ---
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- Config ---
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance", "fasttrade.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'YL6Y6eGXY2vons4yQXerpgJIHa-pV601WX4RDRKR-_U'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Extensions ---
from extensions import init_extensions, db, bcrypt, jwt
init_extensions(app)

# --- Models ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    profile_image = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def check_password(self, plaintext_password):
        return bcrypt.check_password_hash(self.password, plaintext_password)

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'profile_image': self.profile_image,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    listings = db.relationship('Listing', backref='category', lazy=True)
    def to_dict(self):
        return {'id': self.id, 'name': self.name}

class Listing(db.Model):
    __tablename__ = 'listings'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    condition = db.Column(db.Integer, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sold = db.Column(db.Boolean, default=False)
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'image': self.image if self.image else '/uploads/default-listing.png',
            'condition': self.condition,
            'seller_id': self.seller_id,
            'category_id': self.category_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'sold': self.sold
        }

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'read': self.read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# --- Validators ---
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password):
    return True  # Accept any password for demo

def validate_phone(phone):
    pattern = r'^[0-9]{11}$'
    return bool(re.match(pattern, phone))

# --- OTP/Email Logic (no real email sending for demo) ---
otp_storage = {}
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))
def send_verification_email(email, otp):
    try:
        print("Attempting to send email...")
        print("MAIL_USERNAME:", os.getenv("MAIL_USERNAME"))
        print("MAIL_PASSWORD:", "***" if os.getenv("MAIL_PASSWORD") else "Not set")
        
        msg = MailMessage(
            'Your FASTTrade Verification Code',
            recipients=[email],
            body=f"Your verification code is: {otp}\n\nEnter this code to verify your email on FASTTrade.\nIf you did not request this, please ignore this email."
        )
        mail.send(msg)
        otp_storage[email] = {
            'otp': otp,
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        }
        print(f"Sent OTP to {email}: {otp}")
        return True
    except Exception as e:
        print(f"Failed to send verification email to {email}: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return False
def verify_otp(email, otp):
    if email not in otp_storage:
        return False
    stored = otp_storage[email]
    if datetime.utcnow() > stored['expires_at']:
        del otp_storage[email]
        return False
    if stored['otp'] == otp:
        del otp_storage[email]
        return True
    return False

def resend_otp(email):
    if email in otp_storage:
        del otp_storage[email]
    new_otp = generate_otp()
    return send_verification_email(email, new_otp)

def init_default_categories():
    try:
        existing_categories = Category.query.all()
        if not existing_categories:
            if app.config.get('DEBUG'):
                print("Initializing default categories...")
            default_categories = [
                'Electronics',
                'Clothing',
                'Books',
                'Home & Garden',
                'Sports & Outdoors',
                'Toys & Games',
                'Automotive',
                'Health & Beauty'
            ]
            
            for category_name in default_categories:
                if not Category.query.filter_by(name=category_name).first():
                    category = Category(name=category_name)
                    db.session.add(category)
            
            db.session.commit()
            if app.config.get('DEBUG'):
                print("Categories initialization completed")
        elif app.config.get('DEBUG'):
            print(f"Found {len(existing_categories)} existing categories")
    except Exception as e:
        if app.config.get('DEBUG'):
            print(f"Error initializing categories: {str(e)}")
            import traceback
            print("Full traceback:")
            print(traceback.format_exc())
        db.session.rollback()

def insert_test_users():
    if not User.query.filter_by(email='user1@nu.edu.pk').first():
        user1 = User(
            full_name='Test User One',
            email='user1@nu.edu.pk',
            password=bcrypt.generate_password_hash('password1').decode('utf-8'),
            phone='03001234567',
            profile_image=None,
            is_verified=True
        )
        db.session.add(user1)
    
    if not User.query.filter_by(email='user2@nu.edu.pk').first():
        user2 = User(
            full_name='Test User Two',
            email='user2@nu.edu.pk',
            password=bcrypt.generate_password_hash('password2').decode('utf-8'),
            phone='03007654321',
            profile_image=None,
            is_verified=True
        )
        db.session.add(user2)
    
    db.session.commit()
    if app.config.get('DEBUG'):
        print('Test users inserted.')

# --- DB Init ---
def init_db():
    with app.app_context():
        db.create_all()
        init_default_categories()
        insert_test_users()

init_db()

# --- Auth Endpoints ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        required_fields = ['full_name', 'email', 'password', 'phone']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Email domain validation
        if not data['email'].endswith('@nu.edu.pk'):
            return jsonify({'error': 'Only FAST-NUCES emails (@nu.edu.pk) are allowed.'}), 400

        # Password strength validation
        password = data['password']
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long.'}), 400
        if not re.search(r'[^A-Za-z0-9]', password):
            return jsonify({'error': 'Password must contain at least one special character.'}), 400
        if not re.search(r'\d', password):
            return jsonify({'error': 'Password must contain at least one number.'}), 400

        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400

        # Create new user
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(
            full_name=data['full_name'],
            email=data['email'],
            password=hashed_password,
            phone=data['phone'],
            is_verified=False  # User is not verified until OTP is entered
        )

        db.session.add(new_user)
        db.session.commit()

        # Generate and send OTP
        otp = generate_otp()
        if not send_verification_email(data['email'], otp):
            return jsonify({'error': 'Failed to send verification email'}), 500

        return jsonify({
            'message': 'Registration successful. Please check your email for verification code.',
            'user': new_user.to_dict()
        }), 201

    except Exception as e:
        print(f"Error in registration: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    print('Login attempt:', data)
    if not data or 'email' not in data or 'password' not in data:
        print('Missing email or password')
        return jsonify({'error': 'Email and password are required'}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user:
        print('User not found:', data['email'])
        return jsonify({'error': 'Invalid email or password'}), 401
    if not user.check_password(data['password']):
        print('Invalid password for:', data['email'])
        return jsonify({'error': 'Invalid email or password'}), 401
    if not user.is_verified:
        print('User not verified:', data['email'])
        return jsonify({'error': 'Please verify your email first'}), 403
    access_token = create_access_token(identity=str(user.id))
    print('Login successful for:', data['email'])
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token
    }), 200

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200

@app.route('/api/auth/verify-email', methods=['POST'])
def verify_email():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'otp' not in data:
            return jsonify({'error': 'Email and OTP are required'}), 400
        email = data['email']
        otp = data['otp']
        if not verify_otp(email, otp):
            return jsonify({'error': 'Invalid or expired OTP'}), 400
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user.is_verified = True
        db.session.commit()
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_access_token(identity=str(user.id))  # For demo, use same as access
        return jsonify({
            'message': 'Email verified successfully',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200
    except Exception as e:
        print(f"Error in verify_email: {str(e)}")
        return jsonify({'error': 'Verification failed'}), 500

# --- Listings Endpoint ---
@app.route('/api/listings', methods=['GET'])
@app.route('/api/listings/', methods=['GET'])
def get_listings():
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', '').strip()
    query = Listing.query
    if search:
        query = query.filter(
            (Listing.title.ilike(f'%{search}%')) |
            (Listing.description.ilike(f'%{search}%'))
        )
    # Optionally handle sort_by param
    listings = query.order_by(Listing.created_at.desc()).all()
    return jsonify({'listings': [l.to_dict() for l in listings]}), 200

@app.route('/api/listings', methods=['POST'])
@app.route('/api/listings/', methods=['POST'])
@jwt_required()
def create_listing():
    try:
        user_id = int(get_jwt_identity())
        print(f"Creating listing for user {user_id}")
        title = request.form.get('title')
        price = request.form.get('price')
        condition = request.form.get('condition')
        category_id = request.form.get('category_id')
        description = request.form.get('description')
        image = request.files.get('image')
        print(f"Received data: title={title}, price={price}, condition={condition}, category_id={category_id}")
        if not all([title, price, condition, category_id, description]):
            missing = []
            if not title: missing.append('title')
            if not price: missing.append('price')
            if not condition: missing.append('condition')
            if not category_id: missing.append('category_id')
            if not description: missing.append('description')
            return jsonify({'error': f'Missing required fields: {', '.join(missing)}'}), 400
        try:
            price = float(price)
            condition = int(condition)
            category_id = int(category_id)
        except ValueError:
            return jsonify({'error': 'Invalid price, condition, or category ID format'}), 400
        listing = Listing(
            title=title,
            price=price,
            condition=condition,
            category_id=category_id,
            description=description,
            seller_id=user_id
        )
        if image:
            filename = secure_filename(f"listing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            listing.image = f"/uploads/{filename}"
            print(f"Image uploaded: {filename}")
        db.session.add(listing)
        db.session.commit()
        print(f"Listing created successfully with ID: {listing.id}")
        return jsonify({
            'message': 'Listing created successfully',
            'listing': listing.to_dict()
        }), 201
    except ValueError as e:
        print(f"ValueError in create_listing: {str(e)}")
        return jsonify({'error': 'Invalid input data'}), 400
    except Exception as e:
        print(f"Error creating listing: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to create listing'}), 500

@app.route('/api/listings/<int:listing_id>', methods=['GET'])
def get_listing(listing_id):
    try:
        listing = Listing.query.get(listing_id)
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        return jsonify({'listing': listing.to_dict()}), 200
    except Exception as e:
        print(f"Error fetching listing {listing_id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch listing'}), 500

# --- Static file serving ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# --- Chat Endpoints ---
@app.route('/api/messages/threads', methods=['GET'])
@jwt_required()
def get_threads():
    user_id = int(get_jwt_identity())
    sent = db.session.query(Message.receiver_id).filter_by(sender_id=user_id)
    received = db.session.query(Message.sender_id).filter_by(receiver_id=user_id)
    user_ids = set([uid for (uid,) in sent.union(received)])
    threads = []
    for uid in user_ids:
        if uid == user_id:
            continue
        msg = Message.query.filter(
            ((Message.sender_id == user_id) & (Message.receiver_id == uid)) |
            ((Message.sender_id == uid) & (Message.receiver_id == user_id))
        ).order_by(Message.created_at.desc()).first()
        if msg:
            threads.append({
                'user_id': uid,
                'last_message': msg.to_dict()
            })
    return jsonify({'threads': threads}), 200

@app.route('/api/messages/<int:other_user_id>', methods=['GET'])
@jwt_required()
def get_messages_with_user(other_user_id):
    user_id = int(get_jwt_identity())
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == other_user_id)) |
        ((Message.sender_id == other_user_id) & (Message.receiver_id == user_id))
    ).order_by(Message.created_at.asc()).all()
    return jsonify({'messages': [m.to_dict() for m in messages]}), 200

@app.route('/api/messages/<int:other_user_id>', methods=['POST'])
@jwt_required()
def send_message(other_user_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Message content required'}), 400
    msg = Message(sender_id=user_id, receiver_id=other_user_id, content=content)
    db.session.add(msg)
    db.session.commit()
    return jsonify({'message': msg.to_dict()}), 201

@app.route('/api/categories', methods=['GET'])
@app.route('/api/categories/', methods=['GET'])  # Handle both with and without trailing slash
def get_categories():
    try:
        print("Attempting to fetch categories...")
        categories = Category.query.all()
        print(f"Found {len(categories)} categories")
        if not categories:
            print("No categories found, initializing default categories...")
            init_default_categories()
            categories = Category.query.all()
        return jsonify({'categories': [c.to_dict() for c in categories]}), 200
    except Exception as e:
        print(f"Error fetching categories: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to fetch categories'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            # For profile images, redirect to a placeholder avatar
            if filename.startswith('profile_'):
                return redirect('https://via.placeholder.com/150?text=User')
            # For listing images, serve a default listing image
            return send_from_directory(app.config['UPLOAD_FOLDER'], 'default-listing.png')
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        print(f"Error serving file {filename}: {str(e)}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/profile/upload-image', methods=['POST'])
@jwt_required()
def upload_profile_image():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        image = request.files.get('image')
        if not image:
            return jsonify({'error': 'No image uploaded'}), 400
        filename = secure_filename(f"profile_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)
        user.profile_image = f"/uploads/{filename}"
        db.session.commit()
        return jsonify({'message': 'Profile image updated', 'profile_image': user.profile_image}), 200
    except Exception as e:
        print(f"Error uploading profile image: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to upload profile image'}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': user.to_dict()}), 200
    except Exception as e:
        print(f"Error fetching user: {str(e)}")
        return jsonify({'error': 'Failed to fetch user'}), 500

# --- Admin Endpoints ---
@app.route('/api/admin/listings', methods=['GET'])
@jwt_required()
def admin_get_listings():
    try:
        # Check if user is admin
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.email != 'k232004@nu.edu.pk':
            return jsonify({'error': 'Unauthorized'}), 403

        # Pagination
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        query = Listing.query.order_by(Listing.created_at.desc())
        total = query.count()
        listings = query.offset((page - 1) * limit).limit(limit).all()

        return jsonify({
            'listings': [l.to_dict() for l in listings],
            'total': total
        }), 200
    except Exception as e:
        print(f"Error fetching listings: {str(e)}")
        return jsonify({'error': 'Failed to fetch listings'}), 500

@app.route('/api/admin/listings/<int:listing_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_listing(listing_id):
    try:
        # Check if user is admin
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.email != 'k232004@nu.edu.pk':
            return jsonify({'error': 'Unauthorized'}), 403

        listing = Listing.query.get(listing_id)
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        # Delete the listing image if it exists
        if listing.image:
            try:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], listing.image.split('/')[-1])
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Error deleting image: {str(e)}")

        db.session.delete(listing)
        db.session.commit()
        return jsonify({'message': 'Listing deleted successfully'}), 200
    except Exception as e:
        print(f"Error deleting listing: {str(e)}")
        return jsonify({'error': 'Failed to delete listing'}), 500

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def admin_get_users():
    try:
        # Check if user is admin
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.email != 'k232004@nu.edu.pk':
            return jsonify({'error': 'Unauthorized'}), 403

        # Pagination
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        query = User.query.order_by(User.created_at.desc())
        total = query.count()
        users = query.offset((page - 1) * limit).limit(limit).all()

        return jsonify({
            'users': [u.to_dict() for u in users],
            'total': total
        }), 200
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_user(user_id):
    try:
        # Check if user is admin
        admin_id = int(get_jwt_identity())
        admin = User.query.get(admin_id)
        if not admin or admin.email != 'k232004@nu.edu.pk':
            return jsonify({'error': 'Unauthorized'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Delete user's profile image if it exists
        if user.profile_image:
            try:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_image.split('/')[-1])
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Error deleting image: {str(e)}")

        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/api/profile/stats', methods=['GET'])
@jwt_required()
def get_profile_stats():
    user_id = int(get_jwt_identity())
    listings_count = Listing.query.filter_by(seller_id=user_id).count()
    sold_count = Listing.query.filter_by(seller_id=user_id, sold=True).count()
    return jsonify({
        'listingsCount': listings_count,
        'soldCount': sold_count
    }), 200

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    print(traceback.format_exc())
    return "Internal Server Error", 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
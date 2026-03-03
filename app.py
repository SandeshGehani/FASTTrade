import re
import random
import string
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, decode_token
from flask_socketio import join_room, emit, disconnect
from sqlalchemy import or_
import os
from werkzeug.utils import secure_filename
from flask_mail import Message as MailMessage
from config import Config
from extensions import init_extensions, db, bcrypt, jwt, mail, socketio

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# --- Flask App Setup ---
app = Flask(__name__, static_folder='.', static_url_path='', template_folder='templates')
app.config.from_object(Config)
CORS(app)

# Ensure important directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Extensions ---
init_extensions(app)

# --- Cloud Storage ---
# Cloudinary config (auto-configured if CLOUDINARY_URL is in env)
if os.environ.get('CLOUDINARY_URL'):
    cloudinary.config()

def upload_image_helper(image_file, prefix="img"):
    """Uploads image to Cloudinary if configured, otherwise saves locally."""
    if os.environ.get('CLOUDINARY_URL'):
        try:
            result = cloudinary.uploader.upload(image_file)
            return result.get('secure_url')
        except Exception as e:
            print(f"Cloudinary upload failed: {e}")
            return None
    else:
        filename = secure_filename(f"{prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{image_file.filename}")
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        return f"/uploads/{filename}"

# --- Models ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    profile_image = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default=Config.DEFAULT_USER_ROLE)
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
            'role': self.role,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    listings = db.relationship('Listing', backref='category', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description}

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
    status = db.Column(db.String(20), nullable=False, default='available')
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
            'sold': self.sold,
            'status': self.status
        }

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'listing_id': self.listing_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    payment_status = db.Column(db.String(20), nullable=False, default='unpaid')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'buyer_id': self.buyer_id,
            'seller_id': self.seller_id,
            'listing_id': self.listing_id,
            'amount': self.amount,
            'status': self.status,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AdminAction(db.Model):
    __tablename__ = 'admin_actions'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    target_listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=True)
    action_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'target_user_id': self.target_user_id,
            'target_listing_id': self.target_listing_id,
            'action_type': self.action_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# --- Validators ---
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone):
    pattern = r'^[0-9]{11}$'
    return bool(re.match(pattern, phone))

def sanitize_role(role):
    allowed_roles = app.config.get('ALLOWED_USER_ROLES', Config.ALLOWED_USER_ROLES)
    default_role = app.config.get('DEFAULT_USER_ROLE', Config.DEFAULT_USER_ROLE)
    if not role:
        return default_role
    normalized = role.lower()
    return normalized if normalized in allowed_roles else default_role

def is_admin(user) -> bool:
    return bool(user and user.role == 'admin')


def record_admin_action(admin_id, action_type, description, target_user_id=None, target_listing_id=None):
    action = AdminAction(
        admin_id=admin_id,
        target_user_id=target_user_id,
        target_listing_id=target_listing_id,
        action_type=action_type,
        description=description
    )
    db.session.add(action)


def notify_read_receipt(reader_id: int, partner_id: int):
    try:
        socketio.emit('read_receipt', {'reader_id': reader_id}, room=f"user_{partner_id}")
    except Exception as exc:
        if app.config.get('DEBUG'):
            print(f"Failed to emit read receipt: {exc}")


def mark_messages_read(reader_id: int, partner_id: int) -> int:
    try:
        updated = Message.query.filter(
            (Message.sender_id == partner_id) &
            (Message.receiver_id == reader_id) &
            (Message.is_read.is_(False))
        ).update({'is_read': True}, synchronize_session=False)
        if updated:
            db.session.commit()
            notify_read_receipt(reader_id, partner_id)
        return updated
    except Exception as exc:
        db.session.rollback()
        if app.config.get('DEBUG'):
            print(f"Failed to mark messages read: {exc}")
        return 0


def get_user_id_from_token(raw_token):
    if not raw_token:
        raise ValueError("Missing token")
    decoded = decode_token(raw_token)
    identity = decoded.get('sub')
    if identity is None:
        raise ValueError("Invalid token payload")
    return int(identity)


@socketio.on('join')
def handle_join(data):
    token = (data or {}).get('token')
    try:
        user_id = get_user_id_from_token(token)
    except Exception as exc:
        emit('socket_error', {'message': 'Authentication failed', 'details': str(exc)})
        disconnect()
        return
    join_room(f"user_{user_id}")
    emit('socket_ready', {'message': 'Connected', 'user_id': user_id})


@socketio.on('mark_read')
def handle_mark_read(data):
    token = (data or {}).get('token')
    other_user_id = (data or {}).get('other_user_id')
    if not other_user_id:
        emit('socket_error', {'message': 'Missing other_user_id for mark_read'})
        return
    try:
        user_id = get_user_id_from_token(token)
    except Exception as exc:
        emit('socket_error', {'message': 'Authentication failed', 'details': str(exc)})
        disconnect()
        return
    updated = mark_messages_read(user_id, int(other_user_id))
    emit('read_ack', {'updated': updated})

# --- OTP/Email Logic (no real email sending for demo) ---
otp_storage = {}
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))
def send_verification_email(email, otp):
    try:
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
        if app.config.get('DEBUG'):
            print(f"Sent OTP to {email}: {otp}")
        return True
    except Exception as e:
        print(f"Failed to send verification email to {email}: {e}")
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


def init_default_categories():
    try:
        existing_categories = Category.query.all()
        if not existing_categories:
            if app.config.get('DEBUG'):
                print("Initializing default categories...")
            default_categories = [
                {'name': 'Electronics', 'description': 'Phones, laptops, gadgets, accessories'},
                {'name': 'Clothing', 'description': 'Apparel and wearable accessories'},
                {'name': 'Books', 'description': 'Course books, novels, reference material'},
                {'name': 'Home & Garden', 'description': 'Furniture, decor, and household items'},
                {'name': 'Sports & Outdoors', 'description': 'Sports gear and outdoor equipment'},
                {'name': 'Toys & Games', 'description': 'Games, collectibles, and hobby items'},
                {'name': 'Automotive', 'description': 'Vehicle accessories and related items'},
                {'name': 'Health & Beauty', 'description': 'Personal care and wellness products'}
            ]
            
            for category in default_categories:
                if not Category.query.filter_by(name=category['name']).first():
                    category_obj = Category(name=category['name'], description=category.get('description'))
                    db.session.add(category_obj)
            
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
            role='student',
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
            role='admin',
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
        # Role assignment (admins created manually by staff)
        requested_role = data.get('role')
        candidate_role = sanitize_role(requested_role)
        if candidate_role == 'admin':
            candidate_role = app.config.get('DEFAULT_USER_ROLE', 'student')

        new_user = User(
            full_name=data['full_name'],
            email=data['email'],
            password=hashed_password,
            phone=data['phone'],
            role=candidate_role,
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
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password are required'}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401
    if not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    if not user.is_verified:
        return jsonify({'error': 'Please verify your email first'}), 403
    access_token = create_access_token(identity=str(user.id))
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
    status_filter = request.args.get('status', '').strip()
    category_id = request.args.get('category_id')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    query = Listing.query
    if search:
        query = query.filter(
            (Listing.title.ilike(f'%{search}%')) |
            (Listing.description.ilike(f'%{search}%'))
        )
    if status_filter:
        query = query.filter(Listing.status == status_filter)
    if category_id:
        try:
            query = query.filter(Listing.category_id == int(category_id))
        except ValueError:
            return jsonify({'error': 'Invalid category filter'}), 400
    if min_price:
        try:
            query = query.filter(Listing.price >= float(min_price))
        except ValueError:
            return jsonify({'error': 'Invalid min_price filter'}), 400
    if max_price:
        try:
            query = query.filter(Listing.price <= float(max_price))
        except ValueError:
            return jsonify({'error': 'Invalid max_price filter'}), 400
    if sort_by == 'price_low':
        query = query.order_by(Listing.price.asc(), Listing.created_at.desc())
    elif sort_by == 'price_high':
        query = query.order_by(Listing.price.desc(), Listing.created_at.desc())
    else:
        query = query.order_by(Listing.created_at.desc())
    listings = query.all()
    return jsonify({'listings': [l.to_dict() for l in listings]}), 200

@app.route('/api/listings', methods=['POST'])
@app.route('/api/listings/', methods=['POST'])
@jwt_required()
def create_listing():
    try:
        user_id = int(get_jwt_identity())
        title = request.form.get('title')
        price = request.form.get('price')
        condition = request.form.get('condition')
        category_id = request.form.get('category_id')
        description = request.form.get('description')
        image = request.files.get('image')
        if not all([title, price, condition, category_id, description]):
            missing = []
            if not title: missing.append('title')
            if not price: missing.append('price')
            if not condition: missing.append('condition')
            if not category_id: missing.append('category_id')
            if not description: missing.append('description')
            missing_fields = ', '.join(missing)
            return jsonify({'error': f"Missing required fields: {missing_fields}"}), 400
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
            image_url = upload_image_helper(image, prefix="listing")
            if image_url:
                listing.image = image_url
        db.session.add(listing)
        db.session.commit()
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

@app.route('/api/listings/<int:listing_id>/mark-sold', methods=['PUT'])
@jwt_required()
def mark_listing_sold(listing_id):
    try:
        user_id = int(get_jwt_identity())
        listing = Listing.query.get(listing_id)
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        # Only the seller can mark their listing as sold
        if listing.seller_id != user_id:
            return jsonify({'error': 'Unauthorized. Only the seller can mark this listing as sold'}), 403
        
        listing.status = 'sold'
        db.session.commit()
        return jsonify({'message': 'Listing marked as sold', 'listing': listing.to_dict()}), 200
    except Exception as e:
        print(f"Error marking listing as sold: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to mark listing as sold'}), 500

# --- Static file serving ---
@app.route('/favicon.ico')
def favicon():
    """Serve favicon - use logo.png as favicon for legacy browser support"""
    return send_from_directory('static/images', 'logo.png', mimetype='image/png')

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/index.html')
def index_html():
    return send_from_directory('templates', 'index.html')

@app.route('/listing.html')
def listing():
    return send_from_directory('templates', 'listing.html')

@app.route('/about.html')
def about():
    return send_from_directory('templates', 'about.html')

@app.route('/login.html')
def login_page():
    return send_from_directory('templates', 'login.html')

@app.route('/register.html')
def register_page():
    return send_from_directory('templates', 'register.html')

@app.route('/profile.html')
def profile_page():
    return send_from_directory('templates', 'profile.html')

@app.route('/create-listing.html')
def create_listing_page():
    return send_from_directory('templates', 'create-listing.html')

@app.route('/messages.html')
def messages_page():
    return send_from_directory('templates', 'messages.html')

@app.route('/admin.html')
def admin_page():
    return send_from_directory('templates', 'admin.html')

@app.route('/partials/<path:filename>')
def serve_partials(filename):
    """Serve partial templates (navbar, footer, etc.)"""
    return send_from_directory('templates/partials', filename)

@app.route('/<path:path>')
def serve_static(path):
    # Serve HTML files from templates folder (including subdirectories like partials/)
    if path.endswith('.html'):
        # Normalize path separators
        normalized_path = path.replace('\\', '/')
        return send_from_directory('templates', normalized_path)
    # Serve all other files from root
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
            unread_count = Message.query.filter(
                (Message.sender_id == uid) &
                (Message.receiver_id == user_id) &
                (Message.is_read.is_(False))
            ).count()
            threads.append({
                'user_id': uid,
                'last_message': msg.to_dict(),
                'unread_count': unread_count
            })
    return jsonify({'threads': threads}), 200

@app.route('/api/messages/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """Get total count of unread messages for the current user"""
    user_id = int(get_jwt_identity())
    unread_count = Message.query.filter(
        (Message.receiver_id == user_id) &
        (Message.is_read.is_(False))
    ).count()
    return jsonify({'unread_count': unread_count}), 200

@app.route('/api/messages/<int:other_user_id>', methods=['GET'])
@jwt_required()
def get_messages_with_user(other_user_id):
    user_id = int(get_jwt_identity())
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == other_user_id)) |
        ((Message.sender_id == other_user_id) & (Message.receiver_id == user_id))
    ).order_by(Message.created_at.asc()).all()
    # Mark received messages as read
    updated = False
    for msg in messages:
        if msg.receiver_id == user_id and not msg.is_read:
            msg.is_read = True
            updated = True
    if updated:
        db.session.commit()
        notify_read_receipt(user_id, other_user_id)
    return jsonify({'messages': [m.to_dict() for m in messages]}), 200

@app.route('/api/messages/<int:other_user_id>', methods=['POST'])
@jwt_required()
def send_message(other_user_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    content = data.get('content', '').strip()
    listing_id = data.get('listing_id')
    if not content:
        return jsonify({'error': 'Message content required'}), 400
    msg = Message(sender_id=user_id, receiver_id=other_user_id, content=content, listing_id=listing_id)
    db.session.add(msg)
    db.session.commit()
    payload = {'message': msg.to_dict()}
    socketio.emit('new_message', payload, room=f"user_{user_id}")
    socketio.emit('new_message', payload, room=f"user_{other_user_id}")
    return jsonify({'message': payload['message']}), 201


# --- Transaction Endpoints ---
def _get_listing_for_transaction(listing_id):
    listing = Listing.query.get(listing_id)
    if not listing:
        return None, jsonify({'error': 'Listing not found'}), 404
    return listing, None, None


@app.route('/api/transactions', methods=['POST'])
@jwt_required()
def create_transaction():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        listing_id = data.get('listing_id')
        if not listing_id:
            return jsonify({'error': 'listing_id required'}), 400
        listing, error_response, status_code = _get_listing_for_transaction(listing_id)
        if error_response:
            return error_response, status_code
        if listing.seller_id == user_id:
            return jsonify({'error': 'Sellers cannot purchase their own listings'}), 400
        if listing.status != 'available':
            return jsonify({'error': 'Listing is not available for purchase'}), 400

        amount = data.get('amount', listing.price)
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid amount'}), 400

        transaction = Transaction(
            buyer_id=user_id,
            seller_id=listing.seller_id,
            listing_id=listing.id,
            amount=amount,
            status=data.get('status', 'completed'),
            payment_status=data.get('payment_status', 'paid')
        )

        listing.sold = True
        listing.status = 'sold'
        db.session.add(transaction)
        db.session.commit()

        return jsonify({'message': 'Transaction recorded', 'transaction': transaction.to_dict()}), 201
    except Exception as e:
        print(f"Error creating transaction: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to record transaction'}), 500


@app.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        scope = request.args.get('scope', 'user')
        query = Transaction.query.order_by(Transaction.created_at.desc())
        if is_admin(user) and scope == 'all':
            transactions = query.all()
        else:
            transactions = query.filter(
                or_(Transaction.buyer_id == user_id, Transaction.seller_id == user_id)
            ).all()
        return jsonify({'transactions': [t.to_dict() for t in transactions]}), 200
    except Exception as e:
        print(f"Error fetching transactions: {str(e)}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500

@app.route('/api/categories', methods=['GET'])
@app.route('/api/categories/', methods=['GET'])  # Handle both with and without trailing slash
def get_categories():
    try:
        categories = Category.query.all()
        if not categories:
            init_default_categories()
            categories = Category.query.all()
        return jsonify({'categories': [c.to_dict() for c in categories]}), 200
    except Exception as e:
        print(f"Error fetching categories: {str(e)}")
        return jsonify({'error': 'Failed to fetch categories'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            # For profile images, serve default profile image
            if filename.startswith('profile_'):
                default_profile = os.path.join('static', 'images', 'default.png')
                if os.path.exists(default_profile):
                    return send_from_directory('static/images', 'default.png')
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
        image_url = upload_image_helper(image, prefix=f"profile_{user_id}")
        if image_url:
            user.profile_image = image_url
            db.session.commit()
            return jsonify({'message': 'Profile image updated', 'profile_image': user.profile_image}), 200
        else:
            return jsonify({'error': 'Failed to upload profile image'}), 500
    except Exception as e:
        print(f"Error uploading profile image: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to upload profile image'}), 500


@app.route('/api/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json() or {}

        full_name = data.get('full_name')
        phone = data.get('phone')
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if full_name:
            user.full_name = full_name.strip()

        if phone:
            if not validate_phone(phone):
                return jsonify({'error': 'Please provide an 11-digit phone number.'}), 400
            user.phone = phone

        if new_password:
            if not current_password or not user.check_password(current_password):
                return jsonify({'error': 'Current password is incorrect.'}), 400
            if len(new_password) < 8 or not re.search(r'[^A-Za-z0-9]', new_password) or not re.search(r'\d', new_password):
                return jsonify({'error': 'New password must be at least 8 characters long and include a number and special character.'}), 400
            user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        db.session.commit()
        return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200
    except Exception as e:
        print(f"Error updating profile: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500


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
        if not is_admin(user):
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
        if not is_admin(user):
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
        record_admin_action(
            admin_id=user_id,
            action_type='delete_listing',
            description=f"Deleted listing #{listing.id}",
            target_listing_id=listing.id
        )
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
        if not is_admin(user):
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

@app.route('/api/admin/actions', methods=['GET'])
@jwt_required()
def admin_get_actions():
    try:
        admin_id = int(get_jwt_identity())
        admin = User.query.get(admin_id)
        if not is_admin(admin):
            return jsonify({'error': 'Unauthorized'}), 403
        limit = int(request.args.get('limit', 50))
        actions = AdminAction.query.order_by(AdminAction.created_at.desc()).limit(limit).all()
        return jsonify({'actions': [a.to_dict() for a in actions]}), 200
    except Exception as e:
        print(f"Error fetching admin actions: {str(e)}")
        return jsonify({'error': 'Failed to fetch admin actions'}), 500


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_user(user_id):
    try:
        # Check if user is admin
        admin_id = int(get_jwt_identity())
        admin = User.query.get(admin_id)
        if not is_admin(admin):
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
        record_admin_action(
            admin_id=admin_id,
            action_type='delete_user',
            description=f"Deleted user #{user.id}",
            target_user_id=user.id
        )
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

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get public stats for homepage"""
    try:
        # Get actual counts from database
        active_listings = Listing.query.filter_by(status='available').count()
        total_users = User.query.filter_by(is_verified=True).count()
        
        # Calculate weekly trades (transactions from last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_trades = Transaction.query.filter(Transaction.created_at >= week_ago).count()
        
        # Return realistic stats (use actual if available, otherwise show minimums)
        return jsonify({
            'listings': max(active_listings, 50),
            'users': max(total_users, 30),
            'trades': max(weekly_trades, 10)
        }), 200
    except Exception as e:
        print(f"Error fetching stats: {str(e)}")
        # Return default realistic stats if database query fails
        return jsonify({
            'listings': 50,
            'users': 30,
            'trades': 10
        }), 200


@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    print(traceback.format_exc())
    return "Internal Server Error", 500


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
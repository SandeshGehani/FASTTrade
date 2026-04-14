import os
import re
import random
import string
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import socketio
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from config import Config
from extensions import get_db, SessionLocal, engine, Base
from models import User, Category, Listing, Message, Transaction, AdminAction
import schemas
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    get_admin_user,
    get_current_user_from_token
)

app = FastAPI(title="FASTTrade API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

Base.metadata.create_all(bind=engine)

# Setup Socket.IO
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

@sio.on('connect')
async def connect(sid, environ):
    pass

@sio.on('join')
async def handle_join(sid, data):
    token = data.get('token')
    if not token:
        await sio.emit('socket_error', {'message': 'Missing token'}, room=sid)
        return
    db = SessionLocal()
    try:
        user = get_current_user_from_token(token, db)
        sio.enter_room(sid, f"user_{user.id}")
        await sio.emit('socket_ready', {'message': 'Connected', 'user_id': user.id}, room=sid)
    except Exception as exc:
        await sio.emit('socket_error', {'message': 'Authentication failed', 'details': str(exc)}, room=sid)
        await sio.disconnect(sid)
    finally:
        db.close()


def validate_email(email: str):
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@nu\.edu\.pk$', email))

# ---- Routes ----

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    if not validate_email(user_data.email):
        raise HTTPException(status_code=400, detail="Only FAST-NUCES emails (@nu.edu.pk) are allowed.")
    
    password = user_data.password
    if len(password) < 8 or not re.search(r'[^A-Za-z0-9]', password) or not re.search(r'\d', password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long, contain a number and a special character.")
    
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    role = "student" if user_data.role not in ["student", "faculty"] else user_data.role
    
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password=hashed_password,
        phone=user_data.phone,
        role=role,
        is_verified=True # Auto verifying for demo
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Registration successful", "user": new_user.to_dict()}


@app.post("/api/auth/login")
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "message": "Login successful",
        "user": user.to_dict(),
        "access_token": access_token
    }


@app.get("/api/auth/me")
def get_user_me(current_user: User = Depends(get_current_user)):
    return {"user": current_user.to_dict()}

@app.post("/api/auth/verify-email")
def verify_email(data: schemas.EmailVerification, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    db.commit()
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"message": "Email verified successfully", "user": user.to_dict(), "access_token": access_token}


@app.get("/api/listings")
def get_listings(
    search: Optional[str] = None, 
    sort_by: Optional[str] = None, 
    status: Optional[str] = None, 
    category_id: Optional[int] = None, 
    min_price: Optional[float] = None, 
    max_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Listing).options(joinedload(Listing.seller)) # Optimization: Load seller eagerly
    if search:
        query = query.filter(or_(Listing.title.ilike(f"%{search}%"), Listing.description.ilike(f"%{search}%")))
    if status is not None:
        query = query.filter(Listing.status == status)
    if category_id is not None:
        query = query.filter(Listing.category_id == category_id)
    if min_price is not None:
        query = query.filter(Listing.price >= min_price)
    if max_price is not None:
        query = query.filter(Listing.price <= max_price)
        
    if sort_by == 'price_low':
        query = query.order_by(Listing.price.asc(), Listing.created_at.desc())
    elif sort_by == 'price_high':
        query = query.order_by(Listing.price.desc(), Listing.created_at.desc())
    else:
        query = query.order_by(Listing.created_at.desc())
        
    listings = query.all()
    return {"listings": [l.to_dict() for l in listings]}


@app.post("/api/listings", status_code=status.HTTP_201_CREATED)
async def create_listing(
    title: str = Form(...),
    price: float = Form(...),
    condition: int = Form(...),
    category_id: int = Form(...),
    description: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    listing = Listing(
        title=title, price=price, condition=condition, 
        category_id=category_id, description=description, seller_id=current_user.id
    )
    if image:
        import shutil
        filename = f"listing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{image.filename}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        listing.image = f"/uploads/{filename}"

    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {"message": "Listing created successfully", "listing": listing.to_dict()}

@app.get("/api/listings/{listing_id}")
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"listing": listing.to_dict()}

@app.put("/api/listings/{listing_id}/mark-sold")
def mark_listing_sold(listing_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    listing.status = 'sold'
    listing.sold = True
    db.commit()
    return {"message": "Listing marked as sold", "listing": listing.to_dict()}


@app.get("/api/messages/threads")
def get_threads(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sent = db.query(Message.receiver_id).filter(Message.sender_id == current_user.id)
    received = db.query(Message.sender_id).filter(Message.receiver_id == current_user.id)
    user_ids = set([uid for (uid,) in sent.union(received).all()])
    
    threads = []
    for uid in user_ids:
        if uid == current_user.id:
            continue
        msg = db.query(Message).filter(
            or_(
                (Message.sender_id == current_user.id) & (Message.receiver_id == uid),
                (Message.sender_id == uid) & (Message.receiver_id == current_user.id)
            )
        ).order_by(Message.created_at.desc()).first()
        
        if msg:
            unread_count = db.query(Message).filter(
                Message.sender_id == uid,
                Message.receiver_id == current_user.id,
                Message.is_read == False
            ).count()
            threads.append({
                'user_id': uid,
                'last_message': msg.to_dict(),
                'unread_count': unread_count
            })
    return {"threads": threads}

@app.get("/api/messages/unread-count")
def get_unread_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(Message).filter(
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).count()
    return {"unread_count": count}

@app.get("/api/messages/{other_user_id}")
async def get_messages(other_user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    messages = db.query(Message).filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.receiver_id == other_user_id),
            (Message.sender_id == other_user_id) & (Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()
    
    updated = False
    for msg in messages:
        if msg.receiver_id == current_user.id and not msg.is_read:
            msg.is_read = True
            updated = True
    if updated:
        db.commit()
        await sio.emit('read_receipt', {'reader_id': current_user.id}, room=f"user_{other_user_id}")
        
    return {"messages": [m.to_dict() for m in messages]}

@app.post("/api/messages/{other_user_id}", status_code=201)
async def send_message(other_user_id: int, data: schemas.MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msg = Message(sender_id=current_user.id, receiver_id=other_user_id, content=data.content, listing_id=data.listing_id)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    payload = {"message": msg.to_dict()}
    await sio.emit('new_message', payload, room=f"user_{current_user.id}")
    await sio.emit('new_message', payload, room=f"user_{other_user_id}")
    return payload


@app.post("/api/transactions", status_code=201)
def create_transaction(data: schemas.TransactionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == data.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id == current_user.id:
        raise HTTPException(status_code=400, detail="Sellers cannot purchase their own listings")
    if listing.status != 'available':
        raise HTTPException(status_code=400, detail="Listing is not available for purchase")

    amount = data.amount if data.amount is not None else listing.price
    transaction = Transaction(
        buyer_id=current_user.id,
        seller_id=listing.seller_id,
        listing_id=listing.id,
        amount=amount,
        status=data.status,
        payment_status=data.payment_status
    )
    listing.sold = True
    listing.status = 'sold'
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return {"message": "Transaction recorded", "transaction": transaction.to_dict()}

@app.get("/api/transactions")
def get_transactions(scope: str = "user", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Transaction).order_by(Transaction.created_at.desc())
    if current_user.role == "admin" and scope == "all":
        pass
    else:
        query = query.filter(or_(Transaction.buyer_id == current_user.id, Transaction.seller_id == current_user.id))
    return {"transactions": [t.to_dict() for t in query.all()]}

@app.get("/api/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    if not categories:
        default_cats = [
            {'name': 'Electronics', 'description': 'Phones, laptops, gadgets, accessories'},
            {'name': 'Clothing', 'description': 'Apparel and wearable accessories'},
            {'name': 'Books', 'description': 'Course books, novels, reference material'},
            {'name': 'Home & Garden', 'description': 'Furniture, decor, and household items'},
            {'name': 'Sports & Outdoors', 'description': 'Sports gear and outdoor equipment'},
            {'name': 'Toys & Games', 'description': 'Games, collectibles, and hobby items'},
            {'name': 'Automotive', 'description': 'Vehicle accessories and related items'},
            {'name': 'Health & Beauty', 'description': 'Personal care and wellness products'}
        ]
        for c in default_cats:
            db.add(Category(**c))
        db.commit()
        categories = db.query(Category).all()
    return {"categories": [c.to_dict() for c in categories]}

@app.post("/api/profile/upload-image")
def upload_profile_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import shutil
    filename = f"profile_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{image.filename}"
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    current_user.profile_image = f"/uploads/{filename}"
    db.commit()
    return {"message": "Profile image updated", "profile_image": current_user.profile_image}

@app.put("/api/profile")
def update_profile(data: schemas.ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.full_name:
        current_user.full_name = data.full_name.strip()
    if data.phone:
        current_user.phone = data.phone
    if data.new_password:
        if not data.current_password or not verify_password(data.current_password, current_user.password):
            raise HTTPException(status_code=400, detail="Current password incorrect")
        current_user.password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Profile updated successfully", "user": current_user.to_dict()}


@app.get("/api/admin/listings")
def admin_get_listings(page: int = 1, limit: int = 10, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    query = db.query(Listing).order_by(Listing.created_at.desc())
    total = query.count()
    listings = query.offset((page - 1) * limit).limit(limit).all()
    return {"listings": [l.to_dict() for l in listings], "total": total}

@app.get("/api/admin/users")
def admin_get_users(page: int = 1, limit: int = 10, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    query = db.query(User).order_by(User.created_at.desc())
    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()
    return {"users": [u.to_dict() for u in users], "total": total}

@app.get("/api/admin/actions")
def admin_get_actions(limit: int = 50, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    actions = db.query(AdminAction).order_by(AdminAction.created_at.desc()).limit(limit).all()
    return {"actions": [a.to_dict() for a in actions]}

@app.delete("/api/admin/listings/{listing_id}")
def admin_delete_listing(listing_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing.image:
        try:
            os.remove(os.path.join(Config.UPLOAD_FOLDER, listing.image.split('/')[-1]))
        except Exception:
            pass
            
    db.delete(listing)
    action = AdminAction(admin_id=admin.id, action_type='delete_listing', description=f"Deleted listing #{listing.id}", target_listing_id=listing.id)
    db.add(action)
    db.commit()
    return {"message": "Listing deleted successfully"}

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.profile_image:
        try:
            os.remove(os.path.join(Config.UPLOAD_FOLDER, user.profile_image.split('/')[-1]))
        except Exception:
            pass

    db.delete(user)
    action = AdminAction(admin_id=admin.id, action_type='delete_user', description=f"Deleted user #{user.id}", target_user_id=user.id)
    db.add(action)
    db.commit()
    return {"message": "User deleted successfully"}

@app.get("/api/profile/stats")
def get_profile_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listings_count = db.query(Listing).filter(Listing.seller_id == current_user.id).count()
    sold_count = db.query(Listing).filter(Listing.seller_id == current_user.id, Listing.sold == True).count()
    return {"listingsCount": listings_count, "soldCount": sold_count}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    active_listings = db.query(Listing).filter(Listing.status == 'available').count()
    total_users = db.query(User).filter(User.is_verified == True).count()
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_trades = db.query(Transaction).filter(Transaction.created_at >= week_ago).count()
    return {"listings": max(active_listings, 50), "users": max(total_users, 30), "trades": max(weekly_trades, 10)}

# Serving static files and uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("templates/index.html")

@app.get("/{filename}.html")
def html_pages(filename: str):
    path = f"templates/{filename}.html"
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404)

@app.get("/partials/{filename}.html")
def partial_html(filename: str):
    path = f"templates/partials/{filename}.html"
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404)

if __name__ == "__main__":
    import uvicorn
    # uvicorn app:socket_app is what runs Socket.IO
    uvicorn.run("app:socket_app", host="0.0.0.0", port=5000, reload=True)
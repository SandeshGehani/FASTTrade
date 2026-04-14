from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from extensions import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password = Column(String(128), nullable=False)
    phone = Column(String(20), nullable=False)
    profile_image = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default='student')
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    listings = relationship("Listing", back_populates="seller")

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

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    
    listings = relationship('Listing', back_populates='category')

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description}


class Listing(Base):
    __tablename__ = 'listings'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    image = Column(String(255), nullable=True)
    condition = Column(Integer, nullable=False)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sold = Column(Boolean, default=False)
    status = Column(String(20), nullable=False, default='available', index=True)
    
    seller = relationship("User", back_populates="listings")
    category = relationship("Category", back_populates="listings")

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

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    listing_id = Column(Integer, ForeignKey('listings.id'), nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

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


class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    buyer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    listing_id = Column(Integer, ForeignKey('listings.id'), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    payment_status = Column(String(20), nullable=False, default='unpaid')
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

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


class AdminAction(Base):
    __tablename__ = 'admin_actions'
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    target_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    target_listing_id = Column(Integer, ForeignKey('listings.id'), nullable=True)
    action_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

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


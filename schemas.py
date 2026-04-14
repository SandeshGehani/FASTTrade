from pydantic import BaseModel, EmailStr, constr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    role: Optional[str] = "student"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class EmailVerification(BaseModel):
    email: EmailStr
    otp: str

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    listing_id: Optional[int] = None

class TransactionCreate(BaseModel):
    listing_id: int
    amount: Optional[float] = None
    status: Optional[str] = "completed"
    payment_status: Optional[str] = "paid"

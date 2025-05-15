from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import db
import os
from dotenv import load_dotenv
import json



load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str):
    with db.get_cursor(dictionary=True) as (cursor, connection):
        cursor.execute("""
            SELECT userid, username, email, hashpassword, is_active 
            FROM user_info 
            WHERE username = %s
        """, (username,))
        user = cursor.fetchone()
        
        if not user:
            return False
        if not verify_password(password, user['hashpassword']):
            return False
        if not user.get('is_active', True):
            return False
        return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str):
    credentials_exception = Exception("Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    with db.get_cursor(dictionary=True) as (cursor, connection):
        cursor.execute("""
            SELECT userid, username, email, trait_profile, game_played, 
                   game_history, created_at, is_active
            FROM user_info 
            WHERE username = %s
        """, (username,))
        user = cursor.fetchone()
        
        if user is None:
            raise credentials_exception
        
        # Parse JSON fields
        user['trait_profile'] = json.loads(user['trait_profile']) if user['trait_profile'] else {}
        user['game_history'] = json.loads(user['game_history']) if user['game_history'] else {}
        
        return user
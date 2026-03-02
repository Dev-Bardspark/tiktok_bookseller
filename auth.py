"""
Authentication module for BardSpark
Handles user registration, login, and data persistence for all user data
"""

import streamlit as st
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
import re

# ============================================================================
# PASSWORD HASHING
# ============================================================================
def hash_password(password):
    """Hash password with salt"""
    salt = "bardspark_secure_salt_2026"  # In production, use per-user salt
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed

def validate_email(email):
    """Basic email validation"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# ============================================================================
# DATABASE CONNECTION
# ============================================================================
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            port=st.secrets["postgres"]["port"],
            database=st.secrets["postgres"]["database"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"]
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# ============================================================================
# USER AUTHENTICATION
# ============================================================================
def register_user(username, email, password, display_name=None):
    """
    Register a new user
    Returns: (success, message_or_user_id)
    """
    if not username or not email or not password:
        return False, "All fields are required"
    
    if not validate_email(email):
        return False, "Invalid email format"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cur = conn.cursor()
        password_hash = hash_password(password)
        display_name = display_name or username
        
        cur.execute("""
            INSERT INTO users (username, email, password_hash, display_name, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (username.lower(), email.lower(), password_hash, display_name, datetime.now(), datetime.now()))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return True, user_id
        
    except psycopg2.errors.UniqueViolation as e:
        conn.rollback()
        cur.close()
        conn.close()
        if "username" in str(e):
            return False, "Username already taken"
        elif "email" in str(e):
            return False, "Email already registered"
        return False, "Registration failed"
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return False, str(e)

def login_user(login, password):
    """
    Login user with username or email
    Returns: (success, user_dict_or_error_message)
    """
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, username, email, display_name, password_hash, created_at
            FROM users 
            WHERE username = %s OR email = %s
        """, (login.lower(), login.lower()))
        
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return False, "User not found"
        
        if verify_password(password, user['password_hash']):
            # Update last login
            cur.execute("""
                UPDATE users SET last_login = %s WHERE id = %s
            """, (datetime.now(), user['id']))
            conn.commit()
            
            # Remove password hash from returned user dict
            user_dict = dict(user)
            del user_dict['password_hash']
            
            cur.close()
            conn.close()
            return True, user_dict
        else:
            cur.close()
            conn.close()
            return False, "Invalid password"
            
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return False, str(e)

# ============================================================================
# SAVED READERS
# ============================================================================
def get_user_saved_readers(user_id):
    """Get all readers saved by a user"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT r.* FROM arc_readers_central r
            JOIN user_saved_readers s ON r.id = s.reader_id
            WHERE s.user_id = %s
            ORDER BY s.saved_at DESC
        """, (user_id,))
        
        readers = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in readers]
    except Exception as e:
        st.error(f"Error loading saved readers: {e}")
        return []

def save_reader(user_id, reader_id):
    """Save a reader for user"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_saved_readers (user_id, reader_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, reader_id) DO NOTHING
        """, (user_id, reader_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error saving reader: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def remove_saved_reader(user_id, reader_id):
    """Remove a saved reader"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM user_saved_readers 
            WHERE user_id = %s AND reader_id = %s
        """, (user_id, reader_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error removing reader: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

# ============================================================================
# BOOK ANALYSES
# ============================================================================
def save_book_analysis(user_id, book_title, analysis_result, cover_image_url=None):
    """Save a book analysis result"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_book_analyses 
                (user_id, book_title, analysis_result, cover_image_url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, book_title, json.dumps(analysis_result), cover_image_url, datetime.now(), datetime.now()))
        
        analysis_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return analysis_id
    except Exception as e:
        st.error(f"Error saving analysis: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def get_user_book_analyses(user_id):
    """Get all book analyses for a user"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_book_analyses 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        analyses = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(a) for a in analyses]
    except Exception as e:
        st.error(f"Error loading analyses: {e}")
        return []

# ============================================================================
# AUTHOR PERSONAS
# ============================================================================
def save_author_persona(user_id, persona_data):
    """Save author persona quiz results"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Set all existing personas to inactive
        cur.execute("""
            UPDATE user_author_personas SET is_active = FALSE 
            WHERE user_id = %s
        """, (user_id,))
        
        # Insert new persona as active
        cur.execute("""
            INSERT INTO user_author_personas (user_id, persona_data, created_at, is_active)
            VALUES (%s, %s, %s, TRUE)
            RETURNING id
        """, (user_id, json.dumps(persona_data), datetime.now()))
        
        persona_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return persona_id
    except Exception as e:
        st.error(f"Error saving persona: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def get_active_author_persona(user_id):
    """Get the active author persona for a user"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_author_personas 
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        persona = cur.fetchone()
        cur.close()
        conn.close()
        return dict(persona) if persona else None
    except Exception as e:
        st.error(f"Error loading persona: {e}")
        return None

# ============================================================================
# WEBSITE DRAFTS
# ============================================================================
def save_website_draft(user_id, draft_name, basic_info, design_preferences, book_content, cover_image_url=None):
    """Save a website builder draft"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_website_drafts 
                (user_id, draft_name, basic_info, design_preferences, book_content, cover_image_url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, draft_name, 
            json.dumps(basic_info) if basic_info else None,
            json.dumps(design_preferences) if design_preferences else None,
            json.dumps(book_content) if book_content else None,
            cover_image_url,
            datetime.now(), datetime.now()
        ))
        
        draft_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return draft_id
    except Exception as e:
        st.error(f"Error saving website draft: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def get_user_website_drafts(user_id):
    """Get all website drafts for a user"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_website_drafts 
            WHERE user_id = %s
            ORDER BY updated_at DESC
        """, (user_id,))
        
        drafts = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(d) for d in drafts]
    except Exception as e:
        st.error(f"Error loading drafts: {e}")
        return []

# ============================================================================
# MARKETING ASSETS
# ============================================================================
def save_marketing_asset(user_id, asset_type, asset_data):
    """Save a generated marketing asset"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_marketing_assets (user_id, asset_type, asset_data, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_id, asset_type, json.dumps(asset_data), datetime.now()))
        
        asset_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return asset_id
    except Exception as e:
        st.error(f"Error saving marketing asset: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def get_user_marketing_assets(user_id, asset_type=None):
    """Get marketing assets for a user, optionally filtered by type"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if asset_type:
            cur.execute("""
                SELECT * FROM user_marketing_assets 
                WHERE user_id = %s AND asset_type = %s
                ORDER BY created_at DESC
            """, (user_id, asset_type))
        else:
            cur.execute("""
                SELECT * FROM user_marketing_assets 
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
        
        assets = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(a) for a in assets]
    except Exception as e:
        st.error(f"Error loading marketing assets: {e}")
        return []

# ============================================================================
# LOAD ALL USER DATA (for session initialization)
# ============================================================================
def load_all_user_data(user_id):
    """Load all user data into session state"""
    data = {
        'saved_readers': get_user_saved_readers(user_id),
        'book_analyses': get_user_book_analyses(user_id),
        'author_persona': get_active_author_persona(user_id),
        'website_drafts': get_user_website_drafts(user_id),
        'marketing_assets': get_user_marketing_assets(user_id)
    }
    return data

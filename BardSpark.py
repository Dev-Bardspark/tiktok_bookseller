# BardSpark.py (formerly TikTok.py)
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from datetime import datetime, timedelta
from enum import Enum
import json
import plotly.express as px
import VideoGenerator
import LaunchTimeline
import BookTokCompetitorTracker
import BookAnalyzer
import MarketingGenerator
import author_persona_discovery
import arc_influencer_finder
import author_website_builder
import SimpleCRM  # <--- ADDED CRM IMPORT
import audiobook_module  # <--- LINE 1: ADD AUDIOBOOK IMPORT

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="BardSpark",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# BRANDED CSS
# ============================================================================
st.markdown("""
<style>
    .stButton > button {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        color: white !important;
        font-weight: bold;
        border: none;
        padding: 15px 10px;
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(79, 70, 229, 0.3);
    }
    .stButton > button:disabled {
        background: linear-gradient(135deg, #bdc3c7 0%, #2c3e50 100%);
        opacity: 0.5;
        transform: none;
    }
    /* Timeline card styling */
    .timeline-card {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    .phase-badge {
        background: rgba(255,255,255,0.2);
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-block;
        margin-right: 10px;
    }
    /* API Instructions styling */
    .api-instructions {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #4F46E5;
    }
    .api-step {
        margin: 8px 0;
        padding: 5px;
    }
    /* BardSpark specific */
    .brand-header {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)

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
# AUTHENTICATION FUNCTIONS (moved from auth.py)
# ============================================================================
def hash_password(password):
    """Hash password with salt"""
    salt = "bardspark_secure_salt_2026"
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def validate_email(email):
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def register_user(username, email, password, display_name=None):
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
            cur.execute("""
                UPDATE users SET last_login = %s WHERE id = %s
            """, (datetime.now(), user['id']))
            conn.commit()
            
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
# TEST CONNECTION
# ============================================================================
@st.cache_resource
def init_connection():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM arc_readers_central")
            count = cur.fetchone()[0]
            cur.close()
            st.sidebar.success(f"✅ Connected to DB ({count} ARC readers)")
        except Exception as e:
            st.sidebar.error(f"DB error: {e}")
        finally:
            conn.close()
    return True

init_connection()

# ============================================================================
# DATA FUNCTIONS
# ============================================================================
@st.cache_data(ttl=300)
def get_arc_readers_by_genre(genre=None, min_followers=0):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if genre and genre != "All":
            cur.execute("""
                SELECT * FROM arc_readers_central 
                WHERE genres @> %s 
                AND follower_count >= %s
                ORDER BY follower_count DESC
                LIMIT 100
            """, (json.dumps([genre]), min_followers))
        else:
            cur.execute("""
                SELECT * FROM arc_readers_central 
                WHERE follower_count >= %s
                ORDER BY follower_count DESC
                LIMIT 100
            """, (min_followers,))
        readers = cur.fetchall()
        cur.close()
        conn.close()
        return readers
    except Exception as e:
        st.error(f"Error fetching readers: {e}")
        return []

def get_all_genres():
    conn = get_db_connection()
    if not conn:
        return ["Romance", "Fantasy", "Thriller"]
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT jsonb_array_elements_text(genres) as genre
            FROM arc_readers_central
            WHERE genres != '[]'::jsonb
            ORDER BY genre
        """)
        genres = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return ["All"] + genres if genres else ["All", "Romance", "Fantasy", "Thriller"]
    except Exception as e:
        st.error(f"Error fetching genres: {e}")
        return ["All", "Romance", "Fantasy", "Thriller"]

# ============================================================================
# SESSION STATE
# ============================================================================
if 'saved_readers' not in st.session_state:
    st.session_state.saved_readers = []

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.user_id = None
    st.session_state.user_data = {}

if 'page' not in st.session_state:
    st.session_state.page = "🏠 Dashboard"

# ============================================================================
# SIDEBAR - AUTHENTICATION
# ============================================================================
st.sidebar.title("✨ BardSpark")
st.sidebar.markdown("---")

# Auth UI
st.sidebar.subheader("👤 Account")

if not st.session_state.authenticated:
    auth_tab1, auth_tab2 = st.sidebar.tabs(["🔑 Login", "📝 Register"])
    
    with auth_tab1:
        with st.form("login_form"):
            username = st.text_input("Username or Email", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                if username and password:
                    success, result = login_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = result
                        st.session_state.user_id = result['id']
                        
                        # Load saved readers directly from database
                        conn = get_db_connection()
                        if conn:
                            cur = conn.cursor(cursor_factory=RealDictCursor)
                            cur.execute("""
                                SELECT r.* FROM arc_readers_central r
                                JOIN user_saved_arc_readers s ON r.id = s.reader_id
                                WHERE s.user_id = %s
                                ORDER BY s.saved_at DESC
                            """, (result['id'],))
                            saved = cur.fetchall()
                            cur.close()
                            conn.close()
                            st.session_state.saved_readers = [dict(r) for r in saved]
                        else:
                            st.session_state.saved_readers = []
                        
                        st.rerun()
                    else:
                        st.sidebar.error(result)
                else:
                    st.sidebar.error("Please enter username and password")
    
    with auth_tab2:
        with st.form("register_form"):
            new_username = st.text_input("Username", key="reg_username")
            new_email = st.text_input("Email", key="reg_email")
            new_password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            display_name = st.text_input("Display Name (optional)", key="reg_display")
            submitted = st.form_submit_button("Register", type="primary", use_container_width=True)
            
            if submitted:
                if not new_username or not new_email or not new_password:
                    st.sidebar.error("All fields required")
                elif new_password != confirm_password:
                    st.sidebar.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.sidebar.error("Password must be at least 6 characters")
                else:
                    success, result = register_user(
                        new_username, new_email, new_password, 
                        display_name if display_name else None
                    )
                    if success:
                        st.sidebar.success("✅ Registration successful! Please login.")
                    else:
                        st.sidebar.error(result)

else:
    st.sidebar.success(f"✅ Logged in as: {st.session_state.user.get('display_name', st.session_state.user['username'])}")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("👤 Profile", use_container_width=True):
            st.session_state.page = "👤 My Profile"
            st.rerun()
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.user_id = None
            st.session_state.user_data = {}
            st.session_state.saved_readers = []
            st.session_state.analysis_result = None
            st.session_state.persona_results = None
            st.rerun()

st.sidebar.markdown("---")

# ============================================================================
# NAVIGATION MENU - ADDED CRM AND AUDIOBOOKS HERE
# ============================================================================
menu_options = [
    "🏠 Dashboard", 
    "❤️ Saved Readers", 
    "📇 CRM",  # <--- CRM IN MENU
    "🎧 Audiobooks",  # <--- LINE 2: AUDIOBOOKS IN MENU
    "🔍 ARC Readers/Influencers",
    "📖 Book Analyzer",
    "🎨 Marketing Assets",
    "🎬 Video Generator",
    "📊 Competitor Tracker",
    "🧠 Author Persona",
    "🌐 Website Builder"
]

if st.session_state.authenticated:
    menu_options.insert(1, "👤 My Profile")

selected = st.sidebar.radio("Menu", menu_options, index=menu_options.index(st.session_state.page) if st.session_state.page in menu_options else 0)

if selected != st.session_state.page:
    st.session_state.page = selected
    st.rerun()

st.session_state.current_page = st.session_state.page

# ============================================================================
# PAGE ROUTING - ADD THIS RIGHT BEFORE YOUR PAGE CHECKS
# ============================================================================

# If not logged in, show ONLY the login/register screen
if not st.session_state.authenticated:
    st.title("✨ BardSpark")
    st.markdown("### Write. Not Marketing.")
    st.markdown("---")
    st.info("👆 Please login or register using the sidebar to access all features")
    
    # Show a nice welcome message
    col1, col2, col3 = st.columns(3)
    with col2:
        st.image("https://via.placeholder.com/300x200?text=BardSpark", use_container_width=True)
    st.markdown("""
    ### Welcome to BardSpark
    
    Your complete book marketing platform:
    
    - 📚 **ARC Reader/Influencer Finder** - Connect with book reviewers
    - 📖 **Book Analyzer** - Deep literary analysis with marketability scoring  
    - 🎨 **Marketing Assets** - Generate content for all platforms
    - 🎬 **Video Generator** - Create BookTok videos
    - 📊 **Competitor Tracker** - Monitor similar books
    - 🧠 **Author Persona** - Discover your brand voice
    - 🌐 **Website Builder** - Create your author site
    - 📇 **CRM** - Manage contacts and email campaigns
    - 🎧 **Audiobook Marketing** - Find narrators and audiobook reviewers
    """)
    
    # Stop execution - don't show any other pages
    st.stop()

# ============================================================================
# ORIGINAL PAGE ROUTING CONTINUES HERE
# ============================================================================

# ============================================================================
# PROFILE PAGE
# ============================================================================

if st.session_state.page == "👤 My Profile":
    st.title("👤 My Profile")
    st.markdown("### Your account information")
    
    if not st.session_state.authenticated:
        st.warning("Please login to view your profile")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Account Details**")
            st.markdown(f"**Username:** {st.session_state.user['username']}")
            st.markdown(f"**Email:** {st.session_state.user['email']}")
            st.markdown(f"**Display Name:** {st.session_state.user.get('display_name', 'Not set')}")
            
            created_at = st.session_state.user.get('created_at')
            if created_at and isinstance(created_at, str) and len(created_at) >= 10:
                member_since = created_at[:10]
            else:
                member_since = "Unknown"
            st.markdown(f"**Member Since:** {member_since}")
        
        with col2:
            st.markdown("**Your Stats**")
            st.markdown(f"**Saved Readers:** {len(st.session_state.saved_readers)}")
        
        st.markdown("---")
        
        if st.button("📥 Export My Data", use_container_width=True):
            export_data = {
                'user': st.session_state.user,
                'saved_readers': st.session_state.saved_readers
            }
            st.download_button(
                "Download Data (JSON)",
                data=json.dumps(export_data, indent=2, default=str),
                file_name=f"bardspark_export_{st.session_state.user['username']}.json",
                mime="application/json"
            )

# ============================================================================
# DASHBOARD PAGE - ADDED CRM BUTTONS
# ============================================================================

elif st.session_state.page == "🏠 Dashboard":
    st.title("✨ BardSpark")
    st.markdown("### Write. Not Marketing.")
    
    if st.session_state.authenticated:
        st.success(f"Welcome back, {st.session_state.user.get('display_name', st.session_state.user['username'])}!")
    
    LaunchTimeline.show_timeline_widget()
    
    st.markdown("### 🚀 Quick Actions")
    
    # First row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 ARC Readers/Influencers", use_container_width=True):
            st.session_state.page = "🔍 ARC Readers/Influencers"
            st.rerun()
    
    with col2:
        if st.button("📖 Book Analyzer", use_container_width=True):
            st.session_state.page = "📖 Book Analyzer"
            st.rerun()
    
    with col3:
        if st.button("🎨 Marketing Assets", use_container_width=True):
            st.session_state.page = "🎨 Marketing Assets"
            st.rerun()
    
    with col4:
        if st.button("📇 CRM", use_container_width=True):  # <--- ADDED CRM BUTTON
            st.session_state.page = "📇 CRM"
            st.rerun()
    
    # Second row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📊 Competitor Tracker", use_container_width=True):
            st.session_state.page = "📊 Competitor Tracker"
            st.rerun()
    with col2:
        if st.button("🧠 Author Persona", use_container_width=True):
            st.session_state.page = "🧠 Author Persona"
            st.rerun()
    with col3:
        if st.button("🌐 Website Builder", use_container_width=True):
            st.session_state.page = "🌐 Website Builder"
            st.rerun()
    with col4:
        if st.button("🎬 Video Generator", use_container_width=True):
            st.session_state.page = "🎬 Video Generator"
            st.rerun()
    
    # Third row (added Audiobook button)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🎧 Audiobooks", use_container_width=True):
            st.session_state.page = "🎧 Audiobooks"
            st.rerun()
    with col2:
        st.button("📧 Email Campaigns", use_container_width=True, disabled=True)
    with col3:
        st.button("📱 Social Scheduler", use_container_width=True, disabled=True)
    with col4:
        st.button("📈 Sales Tracker", use_container_width=True, disabled=True)
    
    st.markdown("---")
    
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM arc_readers_central")
        total_readers = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM arc_readers_central WHERE roles @> '[\"Influencer\"]'::jsonb")
        total_influencers = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        
        # Get CRM contact count
        cur.execute("SELECT COUNT(*) FROM crm_contacts WHERE user_id = %s", (st.session_state.user_id,))
        total_contacts = cur.fetchone()[0]
        
        cur.close()
        conn.close()
    else:
        total_readers = "?"
        total_influencers = "?"
        total_users = "?"
        total_contacts = "0"
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ARC Readers", total_readers)
    col2.metric("Influencers", total_influencers)
    col3.metric("Total Users", total_users)
    col4.metric("Your Contacts", total_contacts)

# ============================================================================
# SAVED READERS PAGE
# ============================================================================

elif st.session_state.page == "❤️ Saved Readers":
    st.title("❤️ My Saved Advocates")
    
    if not st.session_state.authenticated:
        st.warning("Please login to save and view your advocates")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 ARC Readers/Influencers", use_container_width=True):
                st.session_state.page = "🔍 ARC Readers/Influencers"
                st.rerun()
    elif not st.session_state.saved_readers:
        st.info("You haven't saved any advocates yet. Go to ARC Readers/Influencers to find some!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 ARC Readers/Influencers", use_container_width=True):
                st.session_state.page = "🔍 ARC Readers/Influencers"
                st.rerun()
    else:
        st.markdown(f"### You have {len(st.session_state.saved_readers)} saved advocates")
        
        if st.button("📥 Export as CSV", key="export_csv"):
            df = pd.DataFrame(st.session_state.saved_readers)
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                f"saved_advocates_{st.session_state.user['username']}.csv",
                "text/csv",
                key="download_csv"
            )
        
        st.markdown("---")
        
        for i, reader in enumerate(st.session_state.saved_readers):
            role_icons = []
            if "ARC Reader" in reader.get('roles', []):
                role_icons.append("📚 ARC")
            if "Influencer" in reader.get('roles', []):
                role_icons.append("📢 INF")
            role_display = " | ".join(role_icons) if role_icons else "❓ Unknown"
            
            platforms_display = ""
            if reader.get('platforms') and len(reader['platforms']) > 0:
                platforms_display = f" | 📱 {', '.join(reader['platforms'][:3])}"
                if len(reader['platforms']) > 3:
                    platforms_display += f" +{len(reader['platforms'])-3}"
            
            expander_label = f"**@{reader['username']}** - {reader['follower_count']:,} followers {role_display}{platforms_display}"
            
            with st.expander(expander_label):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Name:** {reader['display_name']}")
                    
                    if reader.get('bio'):
                        st.markdown(f"**Bio:** {reader['bio']}")
                    
                    if reader.get('platforms') and len(reader['platforms']) > 0:
                        st.markdown(f"**All Platforms:** {', '.join(reader['platforms'])}")
                    
                    if reader.get('genres') and len(reader['genres']) > 0:
                        st.markdown(f"**Genres:** {', '.join(reader['genres'])}")
                    
                    if reader.get('email'):
                        st.success(f"📧 {reader['email']}")
                    
                    # Add to CRM button
                    if reader.get('email'):
                        if st.button("➕ Add to CRM", key=f"add_to_crm_{reader['id']}"):
                            # Save to CRM
                            contact_data = {
                                'contact_type': 'arc_reader',
                                'first_name': reader.get('display_name', '').split()[0] if reader.get('display_name') else '',
                                'last_name': ' '.join(reader.get('display_name', '').split()[1:]) if reader.get('display_name') and len(reader.get('display_name', '').split()) > 1 else '',
                                'email': reader.get('email'),
                                'social_handle': reader.get('username'),
                                'source': f"ARC Finder - {reader.get('username')}",
                                'notes': f"Bio: {reader.get('bio', '')[:200]}"
                            }
                            from SimpleCRM import save_contact
                            contact_id = save_contact(st.session_state.user_id, contact_data)
                            if contact_id:
                                st.success(f"✅ Added to CRM!")
                            else:
                                st.error("Failed to add to CRM")
                    
                    if reader.get('username'):
                        base_username = reader['username'].replace('@', '')
                        
                        platform_links = {
                            "TikTok": f"https://tiktok.com/@{base_username}",
                            "Instagram": f"https://instagram.com/{base_username}",
                            "YouTube": f"https://youtube.com/@{base_username}",
                            "X (Twitter)": f"https://twitter.com/{base_username}",
                            "Facebook": f"https://facebook.com/{base_username}",
                            "Bluesky": f"https://bsky.app/profile/{base_username}",
                            "Goodreads": f"https://goodreads.com/{base_username}",
                            "Pinterest": f"https://pinterest.com/{base_username}"
                        }
                        
                        links = []
                        if reader.get('platforms'):
                            for platform in reader['platforms']:
                                if platform in platform_links:
                                    links.append(f"[{platform}]({platform_links[platform]})")
                        
                        if links:
                            st.markdown("**Quick Links:** " + " | ".join(links))
                
                with col2:
                    if st.button("🗑️ Remove", key=f"remove_{reader['id']}_{i}"):
                        if st.session_state.authenticated:
                            # Direct database delete - no auth reference
                            conn = get_db_connection()
                            if conn:
                                cur = conn.cursor()
                                cur.execute("""
                                    DELETE FROM user_saved_arc_readers 
                                    WHERE user_id = %s AND reader_id = %s
                                """, (st.session_state.user_id, reader['id']))
                                conn.commit()
                                cur.close()
                                conn.close()
                            
                            st.session_state.saved_readers.pop(i)
                            st.rerun()
                        else:
                            st.session_state.saved_readers.pop(i)
                            st.rerun()

# ============================================================================
# CRM PAGE - ADDED HERE
# ============================================================================

elif st.session_state.page == "📇 CRM":
    SimpleCRM.render_crm()

# ============================================================================
# AUDIOBOOK PAGE - LINE 3: ADD THIS ENTIRE BLOCK
# ============================================================================

elif st.session_state.page == "🎧 Audiobooks":
    audiobook_module.show_audiobook_module()

# ============================================================================
# OTHER PAGES
# ============================================================================

elif st.session_state.page == "🔍 ARC Readers/Influencers":
    arc_influencer_finder.show_finder()

elif st.session_state.page == "📖 Book Analyzer":
    BookAnalyzer.show_analyzer()

elif st.session_state.page == "🎨 Marketing Assets":
    MarketingGenerator.show_generator()

elif st.session_state.page == "🎬 Video Generator":
    VideoGenerator.show_video_generator()

elif st.session_state.page == "📊 Competitor Tracker":
    BookTokCompetitorTracker.show_competitor_tracker()

elif st.session_state.page == "🧠 Author Persona":
    author_persona_discovery.render_quiz()

elif st.session_state.page == "🌐 Website Builder":
    author_website_builder.show_website_builder()

# ============================================================================
# FOOTER
# ============================================================================

st.sidebar.markdown("---")
st.sidebar.caption("BardSpark v1.0 • Write. Not Marketing.")

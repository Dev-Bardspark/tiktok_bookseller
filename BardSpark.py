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

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

if 'page' not in st.session_state:
    st.session_state.page = "🏠 Dashboard"

# ============================================================================
# SIDEBAR
# ============================================================================
st.sidebar.title("✨ BardSpark")
st.sidebar.markdown("---")

# Simple login
st.sidebar.subheader("👤 Author Demo")
if st.session_state.current_user is None:
    author_name = st.sidebar.text_input("Your name", value="Demo Author", key="login_name")
    if st.sidebar.button("Login as Demo", key="login_button"):
        st.session_state.current_user = {"id": 1, "name": author_name}
        st.rerun()
else:
    st.sidebar.success(f"Logged in as: {st.session_state.current_user['name']}")
    if st.sidebar.button("Logout", key="logout_button"):
        st.session_state.current_user = None
        st.rerun()

st.sidebar.markdown("---")

# ============================================================================
# UPDATED NAVIGATION - REMOVED ARC READERS, RENAMED ADVOCATE FINDER
# ============================================================================
menu_options = [
    "🏠 Dashboard", 
    "❤️ Saved Readers", 
    "🔍 ARC Readers/Influencers",  # RENAMED
    "📖 Book Analyzer",
    "🎨 Marketing Assets",
    "🎬 Video Generator",
    "📊 Competitor Tracker",
    "🧠 Author Persona",
    "🌐 Website Builder"
]

selected = st.sidebar.radio("Menu", menu_options, index=menu_options.index(st.session_state.page))

if selected != st.session_state.page:
    st.session_state.page = selected
    st.rerun()

st.session_state.current_page = st.session_state.page

# ============================================================================
# DASHBOARD PAGE
# ============================================================================

if st.session_state.page == "🏠 Dashboard":
    st.title("✨ BardSpark")
    st.markdown("### Write. Not Marketing.")
    
    # ============================================================================
    # TIMELINE WIDGET (from LaunchTimeline module)
    # ============================================================================
    LaunchTimeline.show_timeline_widget()
    
    # ============================================================================
    # QUICK ACTIONS BUTTON GRID - REMOVED ARC READERS BUTTON
    # ============================================================================
    st.markdown("### 🚀 Quick Actions")
    
    # Row 1
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 ARC Readers/Influencers", use_container_width=True):  # RENAMED
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
        if st.button("🎬 Video Generator", use_container_width=True):
            st.session_state.page = "🎬 Video Generator"
            st.rerun()
    
    # Row 2
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
        st.button("📧 Email Campaigns", use_container_width=True, disabled=True)
    with col4:
        st.button("📱 Social Scheduler", use_container_width=True, disabled=True)
    
    # Row 3
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🌐 Website Builder", use_container_width=True):
            st.session_state.page = "🌐 Website Builder"
            st.rerun()
    with col2:
        st.button("📈 Sales Tracker", use_container_width=True, disabled=True)
    with col3:
        st.button("🤖 AI Assistant", use_container_width=True, disabled=True)
    with col4:
        st.button("📚 Book Preview", use_container_width=True, disabled=True)
    
    # Row 4 (if it exists, otherwise ignore)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.button("⭐ Reviews", use_container_width=True, disabled=True)
    
    # ============================================================================
    # STATS SECTION
    # ============================================================================
    st.markdown("---")
    
    # Get stats
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM arc_readers_central")
        total_readers = cur.fetchone()[0]
        
        # Get influencer count
        cur.execute("SELECT COUNT(*) FROM arc_readers_central WHERE roles @> '[\"Influencer\"]'::jsonb")
        total_influencers = cur.fetchone()[0]
        
        cur.close()
        conn.close()
    else:
        total_readers = "?"
        total_influencers = "?"
    
    # Check if any analysis exists
    books_analyzed = 1 if st.session_state.get('analysis_result') else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ARC Readers", total_readers)
    col2.metric("Influencers", total_influencers)
    col3.metric("Saved Readers", len(st.session_state.saved_readers))
    col4.metric("Books Analyzed", books_analyzed)

# ============================================================================
# ARC READERS PAGE - REMOVED COMPLETELY
# ============================================================================

# ============================================================================
# SAVED READERS PAGE
# ============================================================================

elif st.session_state.page == "❤️ Saved Readers":
    st.title("❤️ My Saved Advocates")
    
    if not st.session_state.saved_readers:
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
                "my_saved_advocates.csv",
                "text/csv",
                key="download_csv"
            )
        
        st.markdown("---")
        
        for i, reader in enumerate(st.session_state.saved_readers):
            # Determine role icons
            role_icons = []
            if "ARC Reader" in reader.get('roles', []):
                role_icons.append("📚 ARC")
            if "Influencer" in reader.get('roles', []):
                role_icons.append("📢 INF")
            role_display = " | ".join(role_icons) if role_icons else "❓ Unknown"
            
            # Get platforms for display
            platforms_display = ""
            if reader.get('platforms') and len(reader['platforms']) > 0:
                platforms_display = f" | 📱 {', '.join(reader['platforms'][:3])}"
                if len(reader['platforms']) > 3:
                    platforms_display += f" +{len(reader['platforms'])-3}"
            
            # Expander label
            expander_label = f"**@{reader['username']}** - {reader['follower_count']:,} followers {role_display}{platforms_display}"
            
            with st.expander(expander_label):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Name:** {reader['display_name']}")
                    
                    if reader.get('bio'):
                        st.markdown(f"**Bio:** {reader['bio']}")
                    
                    # All platforms
                    if reader.get('platforms') and len(reader['platforms']) > 0:
                        st.markdown(f"**All Platforms:** {', '.join(reader['platforms'])}")
                    
                    # All genres
                    if reader.get('genres') and len(reader['genres']) > 0:
                        st.markdown(f"**Genres:** {', '.join(reader['genres'])}")
                    
                    if reader.get('email'):
                        st.success(f"📧 {reader['email']}")
                    
                    # Create platform links
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
                        st.session_state.saved_readers.pop(i)
                        st.rerun()

# ============================================================================
# ARC READERS/INFLUENCERS PAGE (formerly Advocate Finder)
# ============================================================================

elif st.session_state.page == "🔍 ARC Readers/Influencers":
    arc_influencer_finder.show_finder()

# ============================================================================
# BOOK ANALYZER PAGE
# ============================================================================

elif st.session_state.page == "📖 Book Analyzer":
    BookAnalyzer.show_analyzer()

# ============================================================================
# MARKETING ASSETS PAGE
# ============================================================================

elif st.session_state.page == "🎨 Marketing Assets":
    MarketingGenerator.show_generator()

# ============================================================================
# VIDEO GENERATOR PAGE
# ============================================================================

elif st.session_state.page == "🎬 Video Generator":
    VideoGenerator.show_video_generator()

# ============================================================================
# COMPETITOR TRACKER PAGE
# ============================================================================

elif st.session_state.page == "📊 Competitor Tracker":
    BookTokCompetitorTracker.show_competitor_tracker()

# ============================================================================
# AUTHOR PERSONA PAGE
# ============================================================================

elif st.session_state.page == "🧠 Author Persona":
    author_persona_discovery.render_quiz()

# ============================================================================
# WEBSITE BUILDER PAGE - ADD THIS HERE
# ============================================================================

elif st.session_state.page == "🌐 Website Builder":
    author_website_builder.show_website_builder()

# ============================================================================
# FOOTER
# ============================================================================

st.sidebar.markdown("---")
st.sidebar.caption("BardSpark v1.0 • Write. Not Marketing.")

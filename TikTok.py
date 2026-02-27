# TikTok.py
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from datetime import datetime
from enum import Enum
import json
import VideoGenerator

# DO NOT import BookReader at the top - we'll import it only when needed

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="BookTok Machine",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS FOR COLORFUL BUTTONS
# ============================================================================

st.markdown("""
<style>
    /* Colorful button styles */
    .stButton > button {
        font-weight: bold;
        border: none;
        padding: 20px 10px;
        border-radius: 10px;
        transition: transform 0.2s;
        height: 100px;
        font-size: 18px;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
        opacity: 0.9;
    }
    
    /* Individual button colors */
    div[data-testid="column"]:nth-of-type(1) .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    div[data-testid="column"]:nth-of-type(2) .stButton > button {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    
    div[data-testid="column"]:nth-of-type(3) .stButton > button {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
    }
    
    div[data-testid="column"]:nth-of-type(4) .stButton > button {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
    }
    
    /* Disabled buttons */
    .stButton > button:disabled {
        background: linear-gradient(135deg, #bdc3c7 0%, #2c3e50 100%);
        opacity: 0.5;
        transform: none;
    }
    
    /* Stats cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    
    .metric-card h2 {
        font-size: 36px;
        margin: 0;
        color: white;
    }
    
    .metric-card p {
        font-size: 16px;
        margin: 0;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATABASE CONNECTION (from secrets)
# ============================================================================

def get_db_connection():
    """Connect to Supabase PostgreSQL"""
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
# TEST CONNECTION ON STARTUP
# ============================================================================

@st.cache_resource
def init_connection():
    """Test connection and cache it"""
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

# Initialize
init_connection()

# ============================================================================
# DATA ACCESS FUNCTIONS
# ============================================================================

@st.cache_data(ttl=300)
def get_arc_readers_by_genre(genre=None, min_followers=0):
    """Get ARC readers filtered by genre"""
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
    """Get unique genres from database"""
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
# SESSION STATE FOR SAVED READERS
# ============================================================================

if 'saved_readers' not in st.session_state:
    st.session_state.saved_readers = []

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.title("📱 BookTok Machine")
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

# Navigation - Simplified menu
page = st.sidebar.radio(
    "Menu",
    [
        "🏠 Dashboard", 
        "📚 ARC Readers", 
        "❤️ Saved Readers", 
        "📖 Book Analysis", 
        "🎬 Video Generator"
    ]
)

# Store current page in session state
st.session_state.current_page = page

# ============================================================================
# DASHBOARD PAGE - Colorful 4x3 Button Grid with Stats Below
# ============================================================================

if page == "🏠 Dashboard":
    st.title("📱 BookTok Machine")
    st.markdown("### Your Author Dashboard")
    
    # 4x3 Button Grid (Stats will go below)
    
    # Row 1
    st.markdown("#### Quick Actions")
    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
    
    with row1_col1:
        if st.button("📚 ARC Readers", use_container_width=True, key="dash_arc"):
            st.session_state.page = "📚 ARC Readers"
            st.rerun()
    
    with row1_col2:
        if st.button("📖 Book Analysis", use_container_width=True, key="dash_analysis"):
            st.session_state.page = "📖 Book Analysis"
            st.rerun()
    
    with row1_col3:
        if st.button("🎬 Video Generator", use_container_width=True, key="dash_video"):
            st.session_state.page = "🎬 Video Generator"
            st.rerun()
    
    with row1_col4:
        st.button("📝 Coming Soon", use_container_width=True, key="dash_1", disabled=True)
    
    # Row 2
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
    
    with row2_col1:
        st.button("📊 Analytics", use_container_width=True, key="dash_2", disabled=True)
    
    with row2_col2:
        st.button("📧 Email Campaigns", use_container_width=True, key="dash_3", disabled=True)
    
    with row2_col3:
        st.button("📱 Social Scheduler", use_container_width=True, key="dash_4", disabled=True)
    
    with row2_col4:
        st.button("🎯 Ad Creator", use_container_width=True, key="dash_5", disabled=True)
    
    # Row 3
    row3_col1, row3_col2, row3_col3, row3_col4 = st.columns(4)
    
    with row3_col1:
        st.button("📈 Sales Tracker", use_container_width=True, key="dash_6", disabled=True)
    
    with row3_col2:
        st.button("🤖 AI Assistant", use_container_width=True, key="dash_7", disabled=True)
    
    with row3_col3:
        st.button("📚 Book Preview", use_container_width=True, key="dash_8", disabled=True)
    
    with row3_col4:
        st.button("⭐ Reviews", use_container_width=True, key="dash_9", disabled=True)
    
    # Stats Section (below buttons)
    st.markdown("---")
    st.markdown("### Your Stats")
    
    # Get stats
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM arc_readers_central")
        total_readers = cur.fetchone()[0]
        cur.close()
        conn.close()
    else:
        total_readers = "?"
    
    # Display stats in colorful cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <p>ARC Readers Available</p>
            <h2>{total_readers}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <p>Saved Readers</p>
            <h2>{len(st.session_state.saved_readers)}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Count analyzed books (you can implement this later)
        books_analyzed = 1 if st.session_state.get('manuscript_analysis') else 0
        st.markdown(f"""
        <div class="metric-card">
            <p>Books Analyzed</p>
            <h2>{books_analyzed}</h2>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# ARC READERS PAGE
# ============================================================================

elif page == "📚 ARC Readers":
    st.title("📚 ARC Reader Database")
    
    genres = get_all_genres()
    
    col1, col2 = st.columns(2)
    with col1:
        selected_genre = st.selectbox("Filter by genre", genres, key="genre_filter")
    with col2:
        min_followers = st.slider("Minimum followers", 0, 50000, 1000, step=1000, key="follower_slider")
    
    search = st.text_input("🔍 Search by username or bio", "", key="search_input")
    
    with st.spinner("Loading readers..."):
        readers = get_arc_readers_by_genre(
            selected_genre if selected_genre != "All" else None,
            min_followers
        )
    
    if search:
        search_lower = search.lower()
        readers = [
            r for r in readers 
            if search_lower in r['username'].lower() 
            or (r['bio'] and search_lower in r['bio'].lower())
        ]
    
    st.markdown(f"### Found {len(readers)} readers")
    
    for reader in readers:
        with st.expander(f"@{reader['username']} - {reader['follower_count']:,} followers"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Name:** {reader['display_name']}")
                st.markdown(f"**Bio:** {reader['bio'][:200]}..." if reader['bio'] and len(reader['bio']) > 200 else f"**Bio:** {reader['bio']}")
                
                if reader['genres']:
                    genre_list = reader['genres']
                    st.markdown(f"**Genres:** {', '.join(genre_list)}")
                
                if reader['email']:
                    st.success(f"📧 {reader['email']}")
            
            with col2:
                is_saved = any(r['id'] == reader['id'] for r in st.session_state.saved_readers)
                
                if not is_saved:
                    if st.button("❤️ Save", key=f"save_{reader['id']}"):
                        st.session_state.saved_readers.append(reader)
                        st.success("Saved!")
                        st.rerun()
                else:
                    st.button("✅ Saved", key=f"saved_{reader['id']}", disabled=True)

# ============================================================================
# SAVED READERS PAGE
# ============================================================================

elif page == "❤️ Saved Readers":
    st.title("❤️ My Saved ARC Readers")
    
    if not st.session_state.saved_readers:
        st.info("You haven't saved any readers yet. Go to the ARC Readers page to find some!")
        
        if st.button("🔍 Find ARC Readers Now", key="find_now"):
            st.session_state.page = "📚 ARC Readers"
            st.rerun()
    else:
        st.markdown(f"### You have {len(st.session_state.saved_readers)} saved readers")
        
        if st.button("📥 Export as CSV", key="export_csv"):
            df = pd.DataFrame(st.session_state.saved_readers)
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "my_saved_readers.csv",
                "text/csv",
                key="download_csv"
            )
        
        st.markdown("---")
        
        for i, reader in enumerate(st.session_state.saved_readers):
            with st.expander(f"@{reader['username']} - {reader['follower_count']:,} followers"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Name:** {reader['display_name']}")
                    st.markdown(f"**Bio:** {reader['bio'][:200]}..." if reader['bio'] and len(reader['bio']) > 200 else f"**Bio:** {reader['bio']}")
                    
                    if reader['genres']:
                        genre_list = reader['genres']
                        st.markdown(f"**Genres:** {', '.join(genre_list)}")
                    
                    if reader['email']:
                        st.success(f"📧 {reader['email']}")
                
                with col2:
                    if st.button("🗑️ Remove", key=f"remove_{reader['id']}_{i}"):
                        st.session_state.saved_readers.pop(i)
                        st.rerun()
                    
                    if st.button("📤 Contact", key=f"contact_{reader['id']}_{i}"):
                        if reader['email']:
                            st.info(f"Email them at: {reader['email']}")
                        else:
                            st.warning("No email found. Try DM on TikTok")

# ============================================================================
# BOOK ANALYSIS PAGE
# ============================================================================

elif page == "📖 Book Analysis":
    # Import BookReader ONLY when this page is selected
    import BookReader
    BookReader.show_manuscript_tools()

# ============================================================================
# VIDEO GENERATOR PAGE
# ============================================================================

elif page == "🎬 Video Generator":
    import VideoGenerator
    VideoGenerator.show_video_generator()

# ============================================================================
# FOOTER
# ============================================================================

st.sidebar.markdown("---")
st.sidebar.caption("BookTok Machine v0.1 • Data from Supabase")

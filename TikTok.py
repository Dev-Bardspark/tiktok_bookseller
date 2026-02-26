# booktok_machine_supabase.py
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from datetime import datetime
from enum import Enum
import json

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

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_arc_readers_by_genre(genre=None, min_followers=0):
    """Get ARC readers filtered by genre"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if genre and genre != "All":
            # Use JSONB containment query
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
        # This is a bit complex with JSONB, but works
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

# Simple login (just for demo)
st.sidebar.subheader("👤 Author Demo")
if st.session_state.current_user is None:
    author_name = st.sidebar.text_input("Your name", value="Demo Author")
    if st.sidebar.button("Login as Demo"):
        st.session_state.current_user = {"id": 1, "name": author_name}
        st.rerun()
else:
    st.sidebar.success(f"Logged in as: {st.session_state.current_user['name']}")
    if st.sidebar.button("Logout"):
        st.session_state.current_user = None
        st.rerun()

st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Menu",
    ["🏠 Dashboard", "📚 ARC Readers", "❤️ My Saved Readers", "📝 Templates"]
)

# ============================================================================
# DASHBOARD PAGE
# ============================================================================

if page == "🏠 Dashboard":
    st.title("📱 Your BookTok Machine")
    st.markdown("### Welcome back!")
    
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
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("ARC Readers", total_readers)
    with col2:
        st.metric("Saved Readers", len(st.session_state.saved_readers))
    with col3:
        st.metric("Campaigns", "0")
    
    st.markdown("---")
    st.markdown("### 🚀 Quick Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Find ARC Readers", use_container_width=True):
            st.session_state.page = "📚 ARC Readers"
            st.rerun()
    with col2:
        if st.button("❤️ View My Saved", use_container_width=True):
            st.session_state.page = "❤️ My Saved Readers"
            st.rerun()

# ============================================================================
# ARC READERS PAGE (with filtering)
# ============================================================================

elif page == "📚 ARC Readers":
    st.title("📚 ARC Reader Database")
    
    # Get unique genres for filter
    genres = get_all_genres()
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        selected_genre = st.selectbox("Filter by genre", genres)
    with col2:
        min_followers = st.slider("Minimum followers", 0, 50000, 1000, step=1000)
    
    # Search box
    search = st.text_input("🔍 Search by username or bio", "")
    
    # Load data
    with st.spinner("Loading readers..."):
        readers = get_arc_readers_by_genre(
            selected_genre if selected_genre != "All" else None,
            min_followers
        )
    
    # Filter by search
    if search:
        search_lower = search.lower()
        readers = [
            r for r in readers 
            if search_lower in r['username'].lower() 
            or (r['bio'] and search_lower in r['bio'].lower())
        ]
    
    st.markdown(f"### Found {len(readers)} readers")
    
    # Display readers
    for reader in readers:
        with st.expander(f"@{reader['username']} - {reader['follower_count']:,} followers"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Name:** {reader['display_name']}")
                st.markdown(f"**Bio:** {reader['bio'][:200]}..." if reader['bio'] and len(reader['bio']) > 200 else f"**Bio:** {reader['bio']}")
                
                # Display genres
                if reader['genres']:
                    genre_list = json.loads(reader['genres'])
                    st.markdown(f"**Genres:** {', '.join(genre_list)}")
                
                # Email if available
                if reader['email']:
                    st.success(f"📧 {reader['email']}")
            
            with col2:
                # Check if already saved
                is_saved = any(r['id'] == reader['id'] for r in st.session_state.saved_readers)
                
                if not is_saved:
                    if st.button("❤️ Save", key=f"save_{reader['id']}"):
                        st.session_state.saved_readers.append(reader)
                        st.success("Saved!")
                        st.rerun()
                else:
                    st.button("✅ Saved", key=f"saved_{reader['id']}", disabled=True)

# ============================================================================
# MY SAVED READERS PAGE
# ============================================================================

elif page == "❤️ My Saved Readers":
    st.title("❤️ My Saved ARC Readers")
    
    if not st.session_state.saved_readers:
        st.info("You haven't saved any readers yet. Go to the ARC Readers page to find some!")
        
        if st.button("🔍 Find ARC Readers Now"):
            st.session_state.page = "📚 ARC Readers"
            st.rerun()
    else:
        st.markdown(f"### You have {len(st.session_state.saved_readers)} saved readers")
        
        # Option to export
        if st.button("📥 Export as CSV"):
            df = pd.DataFrame(st.session_state.saved_readers)
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "my_saved_readers.csv",
                "text/csv"
            )
        
        st.markdown("---")
        
        # Display saved readers
        for i, reader in enumerate(st.session_state.saved_readers):
            with st.expander(f"@{reader['username']} - {reader['follower_count']:,} followers"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Name:** {reader['display_name']}")
                    st.markdown(f"**Bio:** {reader['bio'][:200]}..." if reader['bio'] and len(reader['bio']) > 200 else f"**Bio:** {reader['bio']}")
                    
                    if reader['genres']:
                        genre_list = json.loads(reader['genres'])
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
# TEMPLATES PAGE
# ============================================================================

elif page == "📝 Templates":
    st.title("📝 Video Templates")
    
    templates = {
        'pointing': {
            'name': '🎯 Pointing at Tropes',
            'script': """
Looking for [TROPE 1]? ✅
[TROPE 2]? ✅
[TROPE 3]? ✅
Then you need [BOOK TITLE]!
""",
            'difficulty': 'Easy'
        },
        'books_that_made_me': {
            'name': '😭 Books That Made Me Feel',
            'script': """
Books that made me [EMOTION] at 2am:
[BOOK TITLE]
Drop your favorite below 👇
""",
            'difficulty': 'Easy'
        },
        'if_you_loved': {
            'name': '📚 If You Loved X, Read Y',
            'script': """
If you loved [POPULAR BOOK],
you NEED to read [BOOK TITLE].
Same [TROPE] vibes!
""",
            'difficulty': 'Easy'
        }
    }
    
    for tid, template in templates.items():
        with st.expander(f"{template['name']} - {template['difficulty']}"):
            st.markdown("**Script:**")
            st.code(template['script'])
            
            if st.button(f"Use This Template", key=tid):
                st.session_state['selected_template'] = template
                st.success("Template selected!")

# ============================================================================
# FOOTER
# ============================================================================

st.sidebar.markdown("---")
st.sidebar.caption("BookTok Machine v0.1 • Data from Supabase")

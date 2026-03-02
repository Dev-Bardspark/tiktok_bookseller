"""
ARC & Influencer Finder Module for BardSpark
Allows searching the database by role (ARC Reader/Influencer) and platforms
"""

import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# ============================================================================
# DATABASE CONNECTION (reused from BardSpark.py)
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
# DATA FUNCTIONS
# ============================================================================
@st.cache_data(ttl=300)
def get_unique_platforms():
    """Get all unique platforms that appear in the database"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT jsonb_array_elements_text(platforms) as platform
            FROM arc_readers_central
            WHERE platforms != '[]'::jsonb
            ORDER BY platform
        """)
        platforms = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return platforms
    except Exception as e:
        st.error(f"Error fetching platforms: {e}")
        return []

@st.cache_data(ttl=300)
def get_all_genres():
    """Get all unique genres from database"""
    conn = get_db_connection()
    if not conn:
        return ["All"]
    
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
        return ["All"] + (genres if genres else [])
    except Exception as e:
        st.error(f"Error fetching genres: {e}")
        return ["All"]

def find_advocates(role_type="any", selected_platforms=None, selected_genre="All", min_followers=0, search_term=""):
    """
    Find ARC readers and/or influencers based on filters
    
    Args:
        role_type: "arc", "influencer", or "both"
        selected_platforms: list of platforms to filter by
        selected_genre: genre to filter by
        min_followers: minimum follower count
        search_term: text to search in username/bio
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query dynamically
        query = """
            SELECT * FROM arc_readers_central 
            WHERE 1=1
        """
        params = []
        
        # Filter by role
        if role_type == "arc":
            query += " AND roles @> '[\"ARC Reader\"]'::jsonb"
        elif role_type == "influencer":
            query += " AND roles @> '[\"Influencer\"]'::jsonb"
        elif role_type == "both":
            query += " AND roles @> '[\"ARC Reader\", \"Influencer\"]'::jsonb"
        
        # Filter by platforms
        if selected_platforms and len(selected_platforms) > 0:
            placeholders = []
            for platform in selected_platforms:
                placeholders.append("platforms ? %s")
                params.append(platform)
            query += " AND (" + " OR ".join(placeholders) + ")"
        
        # Filter by genre
        if selected_genre and selected_genre != "All":
            query += " AND genres @> %s::jsonb"
            params.append(json.dumps([selected_genre]))
        
        # Filter by followers
        if min_followers > 0:
            query += " AND follower_count >= %s"
            params.append(min_followers)
        
        # Search in username or bio
        if search_term:
            query += " AND (username ILIKE %s OR bio ILIKE %s)"
            params.append(f"%{search_term}%")
            params.append(f"%{search_term}%")
        
        # Order by follower count (biggest first)
        query += " ORDER BY follower_count DESC"
        
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
        
    except Exception as e:
        st.error(f"Error finding advocates: {e}")
        return []

def save_to_session(advocates):
    """Save selected advocates to session state for later use"""
    if 'saved_readers' not in st.session_state:
        st.session_state.saved_readers = []
    
    for adv in advocates:
        if not any(r['id'] == adv['id'] for r in st.session_state.saved_readers):
            st.session_state.saved_readers.append(adv)

# ============================================================================
# MAIN UI FUNCTION
# ============================================================================
def render_finder():
    st.title("🔍 ARC Reader & Influencer Finder")
    st.markdown("### Find the perfect advocates for your book")
    
    # Get filter options
    platforms = get_unique_platforms()
    genres = get_all_genres()
    
    # Create filters in sidebar
    with st.sidebar:
        st.markdown("## 🔎 Filter Advocates")
        
        role_filter = st.radio(
            "Who are you looking for?",
            options=["any", "arc", "influencer", "both"],
            format_func=lambda x: {
                "any": "🎭 Anyone",
                "arc": "📚 ARC Readers Only",
                "influencer": "📢 Influencers Only",
                "both": "⭐ ARC Readers who are also Influencers"
            }[x],
            index=0
        )
        
        st.markdown("---")
        
        platform_filter = st.multiselect(
            "Platforms they use",
            options=platforms,
            default=[]
        )
        
        st.markdown("---")
        
        genre_filter = st.selectbox(
            "Genre",
            options=genres,
            index=0
        )
        
        st.markdown("---")
        
        min_followers = st.slider(
            "Minimum followers",
            min_value=0,
            max_value=100000,
            value=1000,
            step=1000
        )
        
        st.markdown("---")
        
        search_term = st.text_input(
            "🔍 Search in username or bio",
            placeholder="e.g., fantasy, romance, arc..."
        )
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### Results")
    with col2:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    # Perform search when button clicked
    if search_button:
        with st.spinner("Searching for advocates..."):
            results = find_advocates(
                role_type=role_filter,
                selected_platforms=platform_filter if platform_filter else None,
                selected_genre=genre_filter,
                min_followers=min_followers,
                search_term=search_term
            )
        
        if results:
            st.success(f"✅ Found {len(results)} advocates matching your criteria")
            
            # Display results
            for advocate in results:
                with st.expander(f"**@{advocate['username']}** - {advocate['follower_count']:,} followers"):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"**Name:** {advocate['display_name']}")
                        if advocate['bio']:
                            st.markdown(f"**Bio:** {advocate['bio'][:200]}..." if len(advocate['bio']) > 200 else f"**Bio:** {advocate['bio']}")
                        
                        # Show platforms
                        if advocate['platforms']:
                            platform_badges = ", ".join([f"`{p}`" for p in advocate['platforms']])
                            st.markdown(f"**Platforms:** {platform_badges}")
                        
                        # Show roles
                        if advocate['roles']:
                            role_icons = []
                            if "ARC Reader" in advocate['roles']:
                                role_icons.append("📚 ARC Reader")
                            if "Influencer" in advocate['roles']:
                                role_icons.append("📢 Influencer")
                            st.markdown(f"**Role:** {' + '.join(role_icons)}")
                        
                        # Show genres
                        if advocate['genres']:
                            genre_preview = advocate['genres'][:5]
                            genre_text = ", ".join(genre_preview)
                            if len(advocate['genres']) > 5:
                                genre_text += f" +{len(advocate['genres'])-5} more"
                            st.markdown(f"**Genres:** {genre_text}")
                        
                        if advocate['email']:
                            st.success(f"📧 {advocate['email']}")
                    
                    with col2:
                        # Check if saved
                        is_saved = any(r['id'] == advocate['id'] for r in st.session_state.get('saved_readers', []))
                        
                        if not is_saved:
                            if st.button("❤️ Save", key=f"save_{advocate['id']}"):
                                if 'saved_readers' not in st.session_state:
                                    st.session_state.saved_readers = []
                                st.session_state.saved_readers.append(advocate)
                                st.success("Saved!")
                                st.rerun()
                        else:
                            st.button("✅ Saved", key=f"saved_{advocate['id']}", disabled=True)
                    
                    with col3:
                        if advocate['email']:
                            st.button("📤 Contact", key=f"contact_{advocate['id']}", 
                                    help=f"Email: {advocate['email']}")
                        else:
                            st.button("🔗 DM", key=f"dm_{advocate['id']}", 
                                    help="No email. Try social media DM.")
        else:
            st.warning("No advocates found matching your criteria. Try widening your filters.")
    
    # Show saved count in sidebar
    st.sidebar.markdown("---")
    saved_count = len(st.session_state.get('saved_readers', []))
    st.sidebar.markdown(f"### ❤️ Saved: {saved_count}")
    if saved_count > 0:
        if st.sidebar.button("📋 View Saved Readers", use_container_width=True):
            st.session_state.page = "❤️ Saved Readers"
            st.rerun()

# ============================================================================
# EXPORT FUNCTION (to be called from BardSpark.py)
# ============================================================================
def show_finder():
    render_finder()

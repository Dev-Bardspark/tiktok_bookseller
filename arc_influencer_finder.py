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

@st.cache_data(ttl=300)
def get_total_count():
    """Get total number of records in database"""
    conn = get_db_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM arc_readers_central")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        st.error(f"Error counting records: {e}")
        return 0

def find_advocates(role_type="any", selected_platforms=None, selected_genre="All", min_followers=0, search_term=""):
    """
    Find ARC readers and/or influencers based on filters
    
    Args:
        role_type: "any", "arc", "influencer", or "both"
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
            query += " AND roles @> '[\"ARC Reader\"]'::jsonb AND roles @> '[\"Influencer\"]'::jsonb"
        
        # Filter by platforms
        if selected_platforms and len(selected_platforms) > 0:
            # If "All Platforms" is selected or it's empty, don't filter
            if "All" not in selected_platforms:
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
    
    # Get total count for reference
    total_count = get_total_count()
    st.caption(f"Total in database: {total_count} advocates")
    
    # Get filter options
    platforms = get_unique_platforms()
    platform_options = ["All"] + platforms if platforms else ["All"]
    
    genres = get_all_genres()
    
    # Create filters in main area (not sidebar)
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        role_filter = st.selectbox(
            "👤 Role",
            options=["any", "arc", "influencer", "both"],
            format_func=lambda x: {
                "any": "🎭 Anyone",
                "arc": "📚 ARC Readers Only",
                "influencer": "📢 Influencers Only",
                "both": "⭐ Both (ARC + Influencer)"
            }[x],
            index=0
        )
    
    with col2:
        platform_filter = st.multiselect(
            "📱 Platforms",
            options=platform_options,
            default=["All"],
            help="Select specific platforms or leave 'All' for any"
        )
    
    with col3:
        genre_filter = st.selectbox(
            "📚 Genre",
            options=genres,
            index=0
        )
    
    # Second row - follower slider and search
    col1, col2 = st.columns([1, 2])
    
    with col1:
        min_followers = st.slider(
            "👥 Minimum followers",
            min_value=0,
            max_value=50000,
            value=0,
            step=1000,
            help="Filter by minimum follower count"
        )
    
    with col2:
        search_term = st.text_input(
            "🔍 Search by username or bio",
            placeholder="e.g., fantasy, romance, arc...",
            help="Search in usernames and bios"
        )
    
    # Search button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    st.markdown("---")
    
    # Perform search when button clicked
    if search_button:
        with st.spinner("Searching for advocates..."):
            results = find_advocates(
                role_type=role_filter,
                selected_platforms=None if "All" in platform_filter else platform_filter,
                selected_genre=genre_filter,
                min_followers=min_followers,
                search_term=search_term
            )
        
        if results:
            st.success(f"✅ Found {len(results)} advocates matching your criteria")
            
            # Summary stats
            arc_count = sum(1 for r in results if "ARC Reader" in r.get('roles', []))
            inf_count = sum(1 for r in results if "Influencer" in r.get('roles', []))
            both_count = sum(1 for r in results if "ARC Reader" in r.get('roles', []) and "Influencer" in r.get('roles', []))
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total", len(results))
            col2.metric("ARC Readers", arc_count)
            col3.metric("Influencers", inf_count)
            col4.metric("Both", both_count)
            
            st.markdown("---")
            
            # Display results
            for advocate in results:
                # Determine role icons
                role_icons = []
                if "ARC Reader" in advocate.get('roles', []):
                    role_icons.append("📚 ARC")
                if "Influencer" in advocate.get('roles', []):
                    role_icons.append("📢 INF")
                role_display = " | ".join(role_icons) if role_icons else "❓ Unknown"
                
                with st.expander(f"**@{advocate['username']}** - {advocate['follower_count']:,} followers | {role_display}"):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"**Name:** {advocate['display_name']}")
                        if advocate['bio']:
                            st.markdown(f"**Bio:** {advocate['bio'][:200]}..." if len(advocate['bio']) > 200 else f"**Bio:** {advocate['bio']}")
                        
                        # Show platforms
                        if advocate.get('platforms') and len(advocate['platforms']) > 0:
                            platform_badges = ", ".join([f"`{p}`" for p in advocate['platforms']])
                            st.markdown(f"**Platforms:** {platform_badges}")
                        else:
                            st.markdown("**Platforms:** `Not specified`")
                        
                        # Show genres (first 8)
                        if advocate.get('genres') and len(advocate['genres']) > 0:
                            genre_preview = advocate['genres'][:8]
                            genre_text = ", ".join(genre_preview)
                            if len(advocate['genres']) > 8:
                                genre_text += f" +{len(advocate['genres'])-8} more"
                            st.markdown(f"**Genres:** {genre_text}")
                        
                        if advocate.get('email'):
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
                        if advocate.get('email'):
                            st.button("📤 Email", key=f"email_{advocate['id']}", 
                                    help=f"Email: {advocate['email']}")
                        else:
                            st.button("🔗 DM", key=f"dm_{advocate['id']}", 
                                    help="No email. Try social media DM.")
        else:
            st.warning("No advocates found matching your criteria. Try widening your filters.")
    else:
        # Show preview of recent advocates
        st.markdown("### 👀 Recent Advocates (Top 10 by followers)")
        preview = find_advocates(min_followers=0)[:10]
        
        for advocate in preview:
            # Determine role icons
            role_icons = []
            if "ARC Reader" in advocate.get('roles', []):
                role_icons.append("📚 ARC")
            if "Influencer" in advocate.get('roles', []):
                role_icons.append("📢 INF")
            role_display = " | ".join(role_icons) if role_icons else "❓ Unknown"
            
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**@{advocate['username']}** - {advocate['follower_count']:,} followers | {role_display}")
                if advocate.get('platforms') and len(advocate['platforms']) > 0:
                    st.caption(f"Platforms: {', '.join(advocate['platforms'])}")
            with col2:
                is_saved = any(r['id'] == advocate['id'] for r in st.session_state.get('saved_readers', []))
                if not is_saved:
                    if st.button("❤️", key=f"preview_save_{advocate['id']}"):
                        if 'saved_readers' not in st.session_state:
                            st.session_state.saved_readers = []
                        st.session_state.saved_readers.append(advocate)
                        st.rerun()
    
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

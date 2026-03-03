"""
ARC & Influencer Finder Module for BardSpark
Allows searching the database by role (ARC Reader/Influencer) and platforms
"""

import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

# ============================================================================
# DEBUG: Print when file loads
# ============================================================================
st.write("🔥 arc_influencer_finder.py loaded at", datetime.now())

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
def get_platforms_with_counts():
    """Get all possible platforms with count of advocates on each"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        # First, get all platforms that actually appear
        cur.execute("""
            SELECT 
                platform,
                COUNT(*) as count
            FROM (
                SELECT jsonb_array_elements_text(platforms) as platform
                FROM arc_readers_central
                WHERE platforms != '[]'::jsonb
            ) p
            GROUP BY platform
            ORDER BY platform
        """)
        results = cur.fetchall()
        
        # Build dictionary of all platforms (including ones with 0)
        platform_counts = {}
        
        # Master list of ALL possible platforms
        all_platforms = [
            "TikTok", "Instagram", "YouTube", "Goodreads", "X (Twitter)", 
            "Facebook", "Bluesky", "StoryGraph", "Amazon", "BookBub",
            "NetGalley", "BookSirens", "Booksprout", "Pinterest", "Discord",
            "Patreon", "Ream", "Email Newsletter", "Author Website"
        ]
        
        # Initialize all with 0
        for platform in all_platforms:
            platform_counts[platform] = 0
        
        # Update with actual counts
        for platform, count in results:
            if platform in platform_counts:
                platform_counts[platform] = count
        
        # Convert to list of tuples for display
        platforms_with_counts = [(p, c) for p, c in platform_counts.items()]
        platforms_with_counts.sort(key=lambda x: x[1], reverse=True)  # Sort by count descending
        
        cur.close()
        conn.close()
        return platforms_with_counts
        
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

# ============================================================================
# MAIN UI FUNCTION
# ============================================================================
def render_finder():
    st.title("🔍 ARC Reader & Influencer Finder")
    st.markdown("### Find the perfect advocates for your book")
    
    # Get total count for reference
    total_count = get_total_count()
    st.caption(f"Total in database: {total_count} advocates")
    
    # Get platforms with counts
    platforms_with_counts = get_platforms_with_counts()
    platform_options = ["All"] + [f"{p} ({c})" for p, c in platforms_with_counts]
    platform_values = ["All"] + [p for p, c in platforms_with_counts]
    
    genres = get_all_genres()
    
    # Create filters in main area
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
        platform_filter_display = st.multiselect(
            "📱 Platforms",
            options=platform_options,
            default=["All"],
            help="Select specific platforms to filter by. 'All' shows everyone."
        )
        # Convert display strings back to platform names, excluding "All"
        platform_filter = []
        for item in platform_filter_display:
            if item != "All":
                # Extract platform name before the (count)
                platform_name = item.split(" (")[0]
                platform_filter.append(platform_name)
    
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
    
    # Show platform summary
    with st.expander("📊 Platform Summary (click to expand)"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Top Platforms:**")
            top_platforms = platforms_with_counts[:5]
            for platform, count in top_platforms:
                st.markdown(f"- {platform}: **{count}** advocates")
        with col2:
            st.markdown("**Other Platforms:**")
            other_platforms = platforms_with_counts[5:10]
            for platform, count in other_platforms:
                st.markdown(f"- {platform}: **{count}** advocates")
    
    st.markdown("---")
    
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
            
            # INSTRUCTION MESSAGE
            st.info("📝 **Many of these results have email addresses. If not, visit the platform and search for the username.**")
            
            st.markdown("---")
            
            # Display results with collapsible sections
            for advocate in results:
                # Determine role icons
                role_icons = []
                if "ARC Reader" in advocate.get('roles', []):
                    role_icons.append("📚 ARC")
                if "Influencer" in advocate.get('roles', []):
                    role_icons.append("📢 INF")
                role_display = " | ".join(role_icons) if role_icons else "❓ Unknown"
                
                # Get platforms for display next to name
                platforms_display = ""
                if advocate.get('platforms') and len(advocate['platforms']) > 0:
                    platforms_display = f" | 📱 {', '.join(advocate['platforms'][:3])}"
                    if len(advocate['platforms']) > 3:
                        platforms_display += f" +{len(advocate['platforms'])-3}"
                
                # Main line for expander
                expander_label = f"**@{advocate['username']}** - {advocate['follower_count']:,} followers {role_display}{platforms_display}"
                
                # Create expander for each advocate
                with st.expander(expander_label):
                    # Email if available
                    if advocate.get('email'):
                        st.markdown(f"📧 **Email:** [{advocate['email']}](mailto:{advocate['email']})")
                    
                    # Full bio
                    if advocate.get('bio'):
                        st.markdown(f"📝 **Bio:** {advocate['bio']}")
                    
                    # All platforms
                    if advocate.get('platforms') and len(advocate['platforms']) > 0:
                        st.markdown(f"📱 **All Platforms:** {', '.join(advocate['platforms'])}")
                    
                    # All genres
                    if advocate.get('genres') and len(advocate['genres']) > 0:
                        st.markdown(f"📚 **Genres:** {', '.join(advocate['genres'])}")
                    
                    # Create platform links
                    if advocate.get('username'):
                        base_username = advocate['username'].replace('@', '')
                        
                        # Common platform URLs
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
                        if advocate.get('platforms'):
                            for platform in advocate['platforms']:
                                if platform in platform_links:
                                    links.append(f"[{platform}]({platform_links[platform]})")
                        
                        if links:
                            st.markdown("🔗 **Quick Links:** " + " | ".join(links))
                    
                   # ============================================================================
                     # SAVE BUTTON WITH LIVE DEBUGGING
                    # ============================================================================
                    st.markdown("---")
                    col_a, col_b, col_c = st.columns([1, 1, 3])
                    with col_a:
                        # Create a unique key for this button
                        button_key = f"save_{advocate['id']}"
                        
                        # Check if already saved by looking at session state
                        is_saved = False
                        if 'saved_readers' in st.session_state:
                            is_saved = any(r['id'] == advocate['id'] for r in st.session_state.saved_readers)
                        
                        # Create a placeholder for debug messages
                        debug_placeholder = st.empty()
                        
                        if not is_saved:
                            if st.button("❤️ Save to My List", key=button_key):
                                with debug_placeholder.container():
                                    st.write("🔍 **DEBUG INFO:**")
                                    st.write(f"1. Button clicked for {advocate['username']}")
                                    st.write(f"2. Authenticated: {st.session_state.get('authenticated', False)}")
                                    st.write(f"3. User ID: {st.session_state.get('user_id', 'None')}")
                                    st.write(f"4. Advocate ID: {advocate['id']}")
                                    
                                    if st.session_state.get('authenticated', False):
                                        st.write("5. Attempting database connection...")
                                        conn = get_db_connection()
                                        
                                        if conn:
                                            st.write("6. ✅ Database connected")
                                            cur = conn.cursor()
                                            
                                            try:
                                                # Check if already exists
                                                st.write("7. Checking if already saved...")
                                                cur.execute("""
                                                    SELECT 1 FROM user_saved_arc_readers 
                                                    WHERE user_id = %s AND reader_id = %s
                                                """, (st.session_state.user_id, advocate['id']))
                                                exists = cur.fetchone()
                                                
                                                if not exists:
                                                    st.write("8. Not saved yet - inserting...")
                                                    cur.execute("""
                                                        INSERT INTO user_saved_arc_readers (user_id, reader_id, saved_at)
                                                        VALUES (%s, %s, %s)
                                                    """, (st.session_state.user_id, advocate['id'], datetime.now()))
                                                    conn.commit()
                                                    st.write("9. ✅ Insert successful")
                                                    
                                                    # Update session state
                                                    if 'saved_readers' not in st.session_state:
                                                        st.session_state.saved_readers = []
                                                    st.session_state.saved_readers.append(advocate)
                                                    st.write("10. ✅ Session state updated")
                                                    
                                                    st.success(f"✅ @{advocate['username']} saved!")
                                                    st.rerun()
                                                else:
                                                    st.write("8. Already exists in database")
                                                    # Still add to session state if not there
                                                    if 'saved_readers' not in st.session_state:
                                                        st.session_state.saved_readers = []
                                                    if not any(r['id'] == advocate['id'] for r in st.session_state.saved_readers):
                                                        st.session_state.saved_readers.append(advocate)
                                                    st.info("Already saved")
                                                    st.rerun()
                                                    
                                            except Exception as e:
                                                st.error(f"❌ Database error: {str(e)}")
                                                st.write(f"Error type: {type(e).__name__}")
                                            finally:
                                                cur.close()
                                                conn.close()
                                                st.write("11. Database connection closed")
                                        else:
                                            st.error("❌ Could not connect to database")
                                    else:
                                        st.warning("⚠️ Please login to save readers")
                        else:
                            st.button("✅ Saved", key=f"saved_{advocate['id']}", disabled=True)

# ============================================================================
# EXPORT FUNCTION (to be called from BardSpark.py)
# ============================================================================
def show_finder():
    render_finder()

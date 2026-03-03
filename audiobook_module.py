import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json

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

def seed_sample_data():
    """Add sample narrators and reviewers"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # Check if we already have data
        cur.execute("SELECT COUNT(*) FROM audiobook_narrators")
        if cur.fetchone()[0] == 0:
            # Note: ARRAY columns need to be passed as Python lists
            narrators = [
                ("Julia Whelan", "Female", ["warm", "dramatic"], "https://juliawhelan.com/sample", "julia@example.com", "$$$", ["Romance", "Fiction"], 4.9),
                ("Steven Pacey", "Male", ["versatile", "character_voices"], "https://stevenpacey.com/sample", "steven@example.com", "$$$", ["Fantasy", "Sci-Fi"], 4.8),
                ("Bahni Turpin", "Female", ["expressive", "captivating"], "https://bahniturpin.com/sample", "bahni@example.com", "$$", ["Fiction", "YA"], 4.9),
                ("RC Bray", "Male", ["gravelly", "intense"], "https://rcbray.com/sample", "rc@example.com", "$$$", ["Sci-Fi", "Thriller"], 4.7),
                ("January LaVoy", "Female", ["clear", "engaging"], "https://januarylavoy.com/sample", "january@example.com", "$$", ["Mystery", "Thriller"], 4.8),
            ]
            for n in narrators:
                cur.execute("""
                    INSERT INTO audiobook_narrators 
                    (narrator_name, voice_gender, voice_style, sample_url, contact_email, rate_range, genres, rating)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, n)
            st.success("✅ Sample narrators added!")
        
        cur.execute("SELECT COUNT(*) FROM audiobook_reviewers")
        if cur.fetchone()[0] == 0:
            reviewers = [
                ("Audiobook Reviewer", "YouTube", "AudiobookReviews", "https://youtube.com/@audiobookreviews", 50000, ["Fantasy", "Sci-Fi"], "contact@audiobookreviews.com"),
                ("Listening Stories", "Podcast", "The Listening Hour", "https://listeningstories.com", 25000, ["Romance", "Fiction"], "hello@listeningstories.com"),
                ("Audiobook Junkie", "Instagram", "@audiobookjunkie", "https://instagram.com/audiobookjunkie", 15000, ["Thriller", "Mystery"], "dm for contact"),
                ("BookTok Listens", "TikTok", "@booktoklistens", "https://tiktok.com/@booktoklistens", 75000, ["YA", "Romance"], "booktoklistens@gmail.com"),
            ]
            for r in reviewers:
                cur.execute("""
                    INSERT INTO audiobook_reviewers 
                    (reviewer_name, platform, channel_name, url, follower_count, genres, contact_email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, r)
            st.success("✅ Sample reviewers added!")
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error seeding data: {e}")
        return False

def show_narrator_finder():
    st.subheader("Find Narrators")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search_genre = st.selectbox("Genre", ["Any", "Romance", "Fantasy", "Sci-Fi", "Mystery", "Thriller", "Fiction", "YA"])
    with col2:
        search_gender = st.selectbox("Voice Gender", ["Any", "Male", "Female"])
    with col3:
        search_rating = st.slider("Minimum Rating", 0.0, 5.0, 4.0, 0.1)
    
    if st.button("🔍 Search Narrators", use_container_width=True):
        conn = get_db_connection()
        if not conn:
            return
        
        query = "SELECT * FROM audiobook_narrators WHERE rating >= %s"
        params = [search_rating]
        
        if search_genre != "Any":
            query += " AND %s = ANY(genres)"
            params.append(search_genre)
        
        if search_gender != "Any":
            query += " AND voice_gender = %s"
            params.append(search_gender)
        
        query += " ORDER BY rating DESC"
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        narrators = cur.fetchall()
        cur.close()
        conn.close()
        
        if narrators:
            st.success(f"Found {len(narrators)} narrators")
            for n in narrators:
                with st.expander(f"🎙️ {n['narrator_name']} - ⭐ {n['rating']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Gender:** {n['voice_gender']}")
                        st.write(f"**Style:** {', '.join(n['voice_style'])}")
                        st.write(f"**Genres:** {', '.join(n['genres'])}")
                        st.write(f"**Rate:** {n['rate_range']}")
                    with col2:
                        if n['sample_url']:
                            st.markdown(f"[🎧 Listen to Sample]({n['sample_url']})")
                        if n['contact_email']:
                            st.info(f"📧 {n['contact_email']}")
        else:
            st.info("No narrators found. Try different filters.")

def show_reviewer_finder():
    st.subheader("Find Audiobook Reviewers")
    
    col1, col2 = st.columns(2)
    with col1:
        search_genre = st.selectbox("Genre", ["Any", "Romance", "Fantasy", "Sci-Fi", "Mystery", "Thriller", "YA"])
    with col2:
        min_followers = st.number_input("Minimum Followers", 0, 100000, 1000, 1000)
    
    if st.button("🔍 Search Reviewers", use_container_width=True):
        conn = get_db_connection()
        if not conn:
            return
        
        query = "SELECT * FROM audiobook_reviewers WHERE follower_count >= %s"
        params = [min_followers]
        
        if search_genre != "Any":
            query += " AND %s = ANY(genres)"
            params.append(search_genre)
        
        query += " ORDER BY follower_count DESC"
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        reviewers = cur.fetchall()
        cur.close()
        conn.close()
        
        if reviewers:
            st.success(f"Found {len(reviewers)} reviewers")
            for r in reviewers:
                with st.expander(f"🎧 {r['reviewer_name']} - {r['platform']} ({r['follower_count']} followers)"):
                    st.write(f"**Channel:** {r['channel_name']}")
                    st.write(f"**Genres:** {', '.join(r['genres'])}")
                    if r['url']:
                        st.markdown(f"[Visit Channel]({r['url']})")
                    if r['contact_email'] and r['contact_email'] != 'dm for contact':
                        st.info(f"📧 {r['contact_email']}")
        else:
            st.info("No reviewers found.")

def show_my_audiobooks():
    st.subheader("My Audiobook Projects")
    
    if not st.session_state.authenticated:
        st.warning("Please login to manage your audiobooks")
        return
    
    # Add new audiobook form
    with st.expander("➕ Add New Audiobook Project"):
        with st.form("new_audiobook"):
            title = st.text_input("Book Title")
            genre = st.selectbox("Genre", ["Romance", "Fantasy", "Sci-Fi", "Mystery", "Thriller", "Fiction"])
            status = st.selectbox("Status", ["Planning", "Looking for narrator", "Recording", "Released"])
            
            col1, col2 = st.columns(2)
            with col1:
                release = st.date_input("Release Date (optional)", None)
            with col2:
                audible = st.text_input("Audible URL (optional)")
            
            if st.form_submit_button("💾 Save Project"):
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO user_audiobooks 
                        (user_id, book_title, book_genre, audiobook_status, release_date, audible_url)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (st.session_state.user_id, title, genre, status, release, audible))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("✅ Audiobook added!")
                    st.rerun()
    
    # Show existing audiobooks
    conn = get_db_connection()
    if conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_audiobooks 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (st.session_state.user_id,))
        books = cur.fetchall()
        cur.close()
        conn.close()
        
        if books:
            for book in books:
                with st.expander(f"📚 {book['book_title']} - {book['audiobook_status']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Genre:** {book['book_genre']}")
                        st.write(f"**Status:** {book['audiobook_status']}")
                        if book['release_date']:
                            st.write(f"**Released:** {book['release_date']}")
                    with col2:
                        if book['audible_url']:
                            st.markdown(f"[🔊 View on Audible]({book['audible_url']})")
                        st.write(f"**Added:** {book['created_at'][:10]}")
                    
                    if st.button("🗑️ Delete", key=f"del_{book['id']}"):
                        conn = get_db_connection()
                        if conn:
                            cur = conn.cursor()
                            cur.execute("DELETE FROM user_audiobooks WHERE id = %s", (book['id'],))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.rerun()
        else:
            st.info("You haven't added any audiobook projects yet.")

def show_audiobook_module():
    """Main audiobook module UI"""
    
    st.title("🎧 Audiobook Marketing")
    st.markdown("### Tools for audiobook authors")
    
    # Seed data if needed
    with st.spinner("Checking database..."):
        seed_sample_data()
    
    tab1, tab2, tab3 = st.tabs(["🔍 Find Narrators", "🎙️ Find Reviewers", "📚 My Audiobooks"])
    
    with tab1:
        show_narrator_finder()
    
    with tab2:
        show_reviewer_finder()
    
    with tab3:
        show_my_audiobooks()

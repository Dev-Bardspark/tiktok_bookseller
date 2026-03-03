import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

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

def init_audiobook_tables():
    """Create tables if they don't exist"""
    conn = get_db_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    # Narrators table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audiobook_narrators (
            id SERIAL PRIMARY KEY,
            narrator_name VARCHAR(255),
            voice_gender VARCHAR(20),
            voice_style TEXT[],
            sample_url TEXT,
            contact_email VARCHAR(255),
            rate_range VARCHAR(50),
            genres TEXT[],
            rating DECIMAL(3,2),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Reviewers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audiobook_reviewers (
            id SERIAL PRIMARY KEY,
            reviewer_name VARCHAR(255),
            platform VARCHAR(100),
            channel_name VARCHAR(255),
            url TEXT,
            follower_count INTEGER,
            genres TEXT[],
            contact_email VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # User's audiobooks table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_audiobooks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            book_title VARCHAR(255),
            book_genre VARCHAR(100),
            audiobook_status VARCHAR(50),
            narrator_id INTEGER REFERENCES audiobook_narrators(id),
            release_date DATE,
            audible_url TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()

def seed_sample_data():
    """Add some sample narrators and reviewers"""
    conn = get_db_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    # Check if we already have data
    cur.execute("SELECT COUNT(*) FROM audiobook_narrators")
    count = cur.fetchone()[0]
    
    if count == 0:
        # Add sample narrators
        sample_narrators = [
            ("Julia Whelan", "Female", ARRAY['warm', 'dramatic'], "https://juliawhelan.com/sample", "julia@example.com", "$$$", ARRAY['Romance', 'Fiction'], 4.9),
            ("Steven Pacey", "Male", ARRAY['versatile', 'character_voices'], "https://stevenpacey.com/sample", "steven@example.com", "$$$", ARRAY['Fantasy', 'Sci-Fi'], 4.8),
            ("Bahni Turpin", "Female", ARRAY['expressive', 'captivating'], "https://bahniturpin.com/sample", "bahni@example.com", "$$", ARRAY['Fiction', 'YA'], 4.9),
            ("RC Bray", "Male", ARRAY['gravelly', 'intense'], "https://rcbray.com/sample", "rc@example.com", "$$$", ARRAY['Sci-Fi', 'Thriller'], 4.7),
            ("January LaVoy", "Female", ARRAY['clear', 'engaging'], "https://januarylavoy.com/sample", "january@example.com", "$$", ARRAY['Mystery', 'Thriller'], 4.8)
        ]
        
        for narrator in sample_narrators:
            cur.execute("""
                INSERT INTO audiobook_narrators 
                (narrator_name, voice_gender, voice_style, sample_url, contact_email, rate_range, genres, rating)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, narrator)
    
    cur.execute("SELECT COUNT(*) FROM audiobook_reviewers")
    count = cur.fetchone()[0]
    
    if count == 0:
        # Add sample reviewers
        sample_reviewers = [
            ("Audiobook Reviewer", "YouTube", "AudiobookReviews", "https://youtube.com/@audiobookreviews", 50000, ARRAY['Fantasy', 'Sci-Fi'], "contact@audiobookreviews.com"),
            ("Listening Stories", "Podcast", "The Listening Hour", "https://listeningstories.com", 25000, ARRAY['Romance', 'Fiction'], "hello@listeningstories.com"),
            ("Audiobook Junkie", "Instagram", "@audiobookjunkie", "https://instagram.com/audiobookjunkie", 15000, ARRAY['Thriller', 'Mystery'], "dm for contact"),
            ("BookTok Listens", "TikTok", "@booktoklistens", "https://tiktok.com/@booktoklistens", 75000, ARRAY['YA', 'Romance'], "booktoklistens@gmail.com")
        ]
        
        for reviewer in sample_reviewers:
            cur.execute("""
                INSERT INTO audiobook_reviewers 
                (reviewer_name, platform, channel_name, url, follower_count, genres, contact_email)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, reviewer)
    
    conn.commit()
    cur.close()
    conn.close()

def show_audiobook_module():
    """Main audiobook module UI"""
    
    # Initialize tables if needed
    init_audiobook_tables()
    seed_sample_data()
    
    st.title("🎧 Audiobook Marketing")
    st.markdown("### Tools for audiobook authors")
    
    tab1, tab2, tab3 = st.tabs(["Find Narrators", "Find Reviewers", "My Audiobooks"])
    
    with tab1:
        show_narrator_finder()
    
    with tab2:
        show_reviewer_finder()
    
    with tab3:
        show_my_audiobooks()

def show_narrator_finder():
    st.subheader("Find Narrators")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        genre = st.selectbox("Genre", ["Any", "Romance", "Fantasy", "Sci-Fi", "Mystery", "Thriller", "Fiction"])
    with col2:
        gender = st.selectbox("Voice Gender", ["Any", "Male", "Female"])
    with col3:
        budget = st.selectbox("Budget", ["Any", "$", "$$", "$$$"])
    
    if st.button("Search Narrators"):
        conn = get_db_connection()
        if not conn:
            return
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM audiobook_narrators WHERE 1=1"
        params = []
        
        if genre != "Any":
            query += " AND %s = ANY(genres)"
            params.append(genre)
        
        if gender != "Any":
            query += " AND voice_gender = %s"
            params.append(gender)
        
        if budget != "Any":
            query += " AND rate_range = %s"
            params.append(budget)
        
        query += " ORDER BY rating DESC"
        
        cur.execute(query, params)
        narrators = cur.fetchall()
        cur.close()
        conn.close()
        
        if narrators:
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
    
    genre = st.selectbox("Filter by Genre", ["Any", "Romance", "Fantasy", "Sci-Fi", "Mystery", "Thriller", "YA"])
    
    if st.button("Search Reviewers"):
        conn = get_db_connection()
        if not conn:
            return
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if genre != "Any":
            cur.execute("SELECT * FROM audiobook_reviewers WHERE %s = ANY(genres) ORDER BY follower_count DESC", (genre,))
        else:
            cur.execute("SELECT * FROM audiobook_reviewers ORDER BY follower_count DESC")
        
        reviewers = cur.fetchall()
        cur.close()
        conn.close()
        
        if reviewers:
            df = pd.DataFrame(reviewers)
            for _, r in df.iterrows():
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
            
            if st.form_submit_button("Save Project"):
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO user_audiobooks (user_id, book_title, book_genre, audiobook_status)
                        VALUES (%s, %s, %s, %s)
                    """, (st.session_state.user_id, title, genre, status))
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
            SELECT ua.*, an.narrator_name 
            FROM user_audiobooks ua
            LEFT JOIN audiobook_narrators an ON ua.narrator_id = an.id
            WHERE ua.user_id = %s
            ORDER BY ua.created_at DESC
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
                        if book.get('narrator_name'):
                            st.write(f"**Narrator:** {book['narrator_name']}")
                    with col2:
                        if book.get('release_date'):
                            st.write(f"**Released:** {book['release_date']}")
                        if book.get('audible_url'):
                            st.markdown(f"[View on Audible]({book['audible_url']})")
        else:
            st.info("You haven't added any audiobook projects yet.")

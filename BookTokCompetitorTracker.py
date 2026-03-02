# BookTokCompetitorTracker.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

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

def save_tracked_author_to_db(user_id, author_name, author_data, notes=None):
    """Save a tracked author to database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_tracked_authors 
            (user_id, author_name, author_data, notes, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            author_name,
            json.dumps(author_data),
            notes,
            datetime.now()
        ))
        
        tracked_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return tracked_id
    except Exception as e:
        st.error(f"Error saving tracked author: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def load_user_tracked_authors(user_id):
    """Load all tracked authors for a user"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_tracked_authors 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        authors = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to list with parsed JSON
        result = []
        for a in authors:
            author_dict = dict(a)
            if author_dict.get('author_data'):
                if isinstance(author_dict['author_data'], str):
                    author_dict['author_data'] = json.loads(author_dict['author_data'])
            result.append(author_dict)
        
        return result
    except Exception as e:
        st.error(f"Error loading tracked authors: {e}")
        return []

def update_tracked_author_metrics(user_id, author_id, mentions, top_views):
    """Update metrics for a tracked author"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Get current data
        cur.execute("""
            SELECT author_data FROM user_tracked_authors 
            WHERE user_id = %s AND id = %s
        """, (user_id, author_id))
        
        result = cur.fetchone()
        if not result:
            cur.close()
            conn.close()
            return False
        
        author_data = result[0]
        if isinstance(author_data, str):
            author_data = json.loads(author_data)
        
        # Update metrics
        author_data['mentions'] = mentions
        author_data['top_views'] = top_views
        
        # Save back
        cur.execute("""
            UPDATE user_tracked_authors 
            SET author_data = %s, notes = %s
            WHERE user_id = %s AND id = %s
        """, (
            json.dumps(author_data),
            json.dumps({"last_updated": datetime.now().isoformat()}),
            user_id,
            author_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating metrics: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def delete_tracked_author(user_id, author_id):
    """Delete a tracked author"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM user_tracked_authors 
            WHERE user_id = %s AND id = %s
        """, (user_id, author_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error deleting tracked author: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def show_competitor_tracker():
    """Display the BookTok competitor tracking dashboard"""
    
    st.markdown("## 📚 BookTok Competitor Analysis")
    st.markdown("Track similar books launching on BookTok and learn from their success")
    
    # Check authentication
    if not st.session_state.get('authenticated', False):
        st.warning("Please login to track competitors")
        return
    
    # Initialize session state for competitor data from database
    if 'competitor_books' not in st.session_state or not st.session_state.competitor_books:
        # Load from database
        db_books = load_user_tracked_authors(st.session_state.user_id)
        if db_books:
            # Convert database format to session format
            st.session_state.competitor_books = []
            for book in db_books:
                author_data = book.get('author_data', {})
                if author_data:
                    book_dict = {
                        "id": book['id'],
                        "title": author_data.get('title', 'Unknown'),
                        "author": author_data.get('author', 'Unknown'),
                        "genre": author_data.get('genre', 'Unknown'),
                        "sub_genre": author_data.get('sub_genre', ''),
                        "launch_date": author_data.get('launch_date', ''),
                        "booktok_handle": author_data.get('booktok_handle', ''),
                        "mentions": author_data.get('mentions', 0),
                        "top_views": author_data.get('top_views', 0),
                        "viral_sound": author_data.get('viral_sound', ''),
                        "praise": author_data.get('praise', []),
                        "criticism": author_data.get('criticism', []),
                        "date_added": book.get('created_at', '')[:10] if book.get('created_at') else '',
                        "last_updated": datetime.now().strftime("%Y-%m-%d")
                    }
                    st.session_state.competitor_books.append(book_dict)
        else:
            # Load sample data if no books tracked yet
            st.session_state.competitor_books = load_sample_competitors()
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Track Competitors", 
        "📊 Genre Trends", 
        "🔍 BookTok Insights",
        "📈 Launch Analysis"
    ])
    
    with tab1:
        show_competitor_tracking()
    
    with tab2:
        show_genre_trends()
    
    with tab3:
        show_booktok_insights()
    
    with tab4:
        show_launch_analysis()

def show_competitor_tracking():
    """Main competitor tracking interface"""
    
    # Add new competitor form
    with st.expander("➕ Add New Book to Track", expanded=False):
        with st.form("add_competitor"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Book Title *", placeholder="e.g., Fourth Wing")
                author = st.text_input("Author *", placeholder="Rebecca Yarros")
                genre = st.selectbox(
                    "Genre *",
                    ["Romantasy", "YA Fantasy", "Contemporary Romance", 
                     "Thriller", "YA Contemporary", "Sci-Fi", "Historical Fiction"]
                )
                
            with col2:
                launch_date = st.date_input(
                    "Launch Date *",
                    min_value=datetime.now().date() - timedelta(days=365),
                    max_value=datetime.now().date() + timedelta(days=180)
                )
                sub_genre = st.text_input("Sub-genre/Tropes", 
                    placeholder="e.g., enemies to lovers, dragon riders")
                booktok_handle = st.text_input("Author BookTok Handle", 
                    placeholder="@author (if known)")
            
            # Viral metrics (optional)
            st.markdown("### 🚀 Current BookTok Performance (Optional)")
            col3, col4, col5 = st.columns(3)
            
            with col3:
                mentions = st.number_input("BookTok Mentions", min_value=0, value=0)
            with col4:
                top_views = st.number_input("Top Video Views", min_value=0, value=0)
            with col5:
                viral_sound = st.text_input("Viral Sound Used", placeholder="Sound name")
            
            # What's working
            st.markdown("### 💡 What's Working for This Book")
            praise = st.text_area(
                "What readers LOVE (one per line)",
                placeholder="Enemies to lovers done right\nAmazing worldbuilding\nStrong female lead"
            )
            
            criticism = st.text_area(
                "What readers CRITICIZE (one per line)",
                placeholder="Slow pacing in middle\nToo many POVs\nPredictable plot"
            )
            
            # Submit button
            submitted = st.form_submit_button("🚀 Start Tracking This Book")
            
            if submitted and title and author:
                # Prepare author data
                author_data = {
                    "title": title,
                    "author": author,
                    "genre": genre,
                    "sub_genre": sub_genre,
                    "launch_date": launch_date.strftime("%Y-%m-%d"),
                    "booktok_handle": booktok_handle,
                    "mentions": mentions,
                    "top_views": top_views,
                    "viral_sound": viral_sound,
                    "praise": [p.strip() for p in praise.split("\n") if p.strip()],
                    "criticism": [c.strip() for c in criticism.split("\n") if c.strip()],
                    "date_added": datetime.now().strftime("%Y-%m-%d")
                }
                
                # Save to database
                tracked_id = save_tracked_author_to_db(
                    st.session_state.user_id,
                    f"{title} by {author}",
                    author_data,
                    "Tracked from competitor analyzer"
                )
                
                if tracked_id:
                    # Add to session state
                    new_book = {
                        "id": tracked_id,
                        "title": title,
                        "author": author,
                        "genre": genre,
                        "sub_genre": sub_genre,
                        "launch_date": launch_date.strftime("%Y-%m-%d"),
                        "booktok_handle": booktok_handle,
                        "mentions": mentions,
                        "top_views": top_views,
                        "viral_sound": viral_sound,
                        "praise": [p.strip() for p in praise.split("\n") if p.strip()],
                        "criticism": [c.strip() for c in criticism.split("\n") if c.strip()],
                        "date_added": datetime.now().strftime("%Y-%m-%d"),
                        "last_updated": datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    st.session_state.competitor_books.append(new_book)
                    st.success(f"✅ Now tracking '{title}'! Add more books or view insights below.")
                    st.rerun()
    
    # Display tracked competitors
    st.markdown("### 📖 Books You're Tracking")
    
    if not st.session_state.competitor_books:
        st.info("👆 Add your first competitor book above to start tracking!")
        return
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        genres = ["All"] + list(set(b["genre"] for b in st.session_state.competitor_books if b.get("genre")))
        selected_genre = st.selectbox("Filter by Genre", genres)
    with col2:
        sort_by = st.selectbox("Sort by", ["Recently Added", "Most Mentions", "Launch Date"])
    
    # Filter books
    filtered_books = st.session_state.competitor_books
    if selected_genre != "All":
        filtered_books = [b for b in filtered_books if b.get("genre") == selected_genre]
    
    # Sort books
    if sort_by == "Recently Added":
        filtered_books.sort(key=lambda x: x.get("date_added", ""), reverse=True)
    elif sort_by == "Most Mentions":
        filtered_books.sort(key=lambda x: x.get("mentions", 0), reverse=True)
    elif sort_by == "Launch Date":
        filtered_books.sort(key=lambda x: x.get("launch_date", ""))
    
    # Display books in cards
    for book in filtered_books:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{book.get('title', 'Unknown')}** by {book.get('author', 'Unknown')}")
                st.caption(f"📅 {book.get('launch_date', '')} | {book.get('genre', '')}")
            
            with col2:
                st.metric("Mentions", book.get('mentions', 0))
            
            with col3:
                views = book.get('top_views', 0)
                if views > 1000000:
                    views_display = f"{views/1000000:.1f}M"
                else:
                    views_display = f"{views/1000:.1f}K"
                st.metric("Top Views", views_display)
            
            with col4:
                if st.button("🔍 Details", key=f"view_{book['id']}"):
                    st.session_state.selected_book = book['id']
            
            with col5:
                if st.button("🗑️ Delete", key=f"delete_{book['id']}"):
                    if delete_tracked_author(st.session_state.user_id, book['id']):
                        st.session_state.competitor_books = [b for b in st.session_state.competitor_books if b['id'] != book['id']]
                        st.success(f"Removed {book.get('title', '')}")
                        st.rerun()
            
            # Show details if selected
            if st.session_state.get('selected_book') == book['id']:
                show_book_details(book)
            
            st.divider()

def show_book_details(book):
    """Show detailed view of a competitor book"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💚 What Readers LOVE")
        for praise in book.get('praise', []):
            st.markdown(f"✅ {praise}")
        
        if book.get('viral_sound'):
            st.markdown(f"🎵 **Viral Sound:** {book['viral_sound']}")
    
    with col2:
        st.markdown("#### 💔 What Readers CRITICIZE")
        for criticism in book.get('criticism', []):
            st.markdown(f"❌ {criticism}")
    
    # Update metrics
    st.markdown("#### 📊 Update Metrics")
    col3, col4, col5 = st.columns(3)
    
    with col3:
        new_mentions = st.number_input(
            "Update Mentions", 
            value=book.get('mentions', 0),
            key=f"mentions_{book['id']}"
        )
    with col4:
        new_views = st.number_input(
            "Update Top Views",
            value=book.get('top_views', 0),
            key=f"views_{book['id']}"
        )
    with col5:
        if st.button("Update", key=f"update_{book['id']}"):
            # Update in database
            if update_tracked_author_metrics(st.session_state.user_id, book['id'], new_mentions, new_views):
                # Update in session state
                for b in st.session_state.competitor_books:
                    if b['id'] == book['id']:
                        b['mentions'] = new_mentions
                        b['top_views'] = new_views
                        b['last_updated'] = datetime.now().strftime("%Y-%m-%d")
                st.success("Updated!")
                st.rerun()

def show_genre_trends():
    """Analyze trends across your genre"""
    
    st.markdown("### 📊 Genre Trends Analysis")
    
    # Aggregate data from tracked books
    books = st.session_state.competitor_books
    
    if not books:
        st.info("Add some competitor books first to see genre trends!")
        return
    
    # Filter out books without genre
    valid_books = [b for b in books if b.get('genre')]
    
    if not valid_books:
        st.info("No genre data available yet.")
        return
    
    # Genre distribution
    genre_counts = pd.DataFrame([
        {"genre": b["genre"], "mentions": b.get("mentions", 0)} 
        for b in valid_books
    ])
    
    fig = px.pie(
        genre_counts, 
        names="genre", 
        values="mentions",
        title="BookTok Mentions by Genre"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Common praise and criticism
    all_praise = []
    all_criticism = []
    
    for book in books:
        all_praise.extend(book.get('praise', []))
        all_criticism.extend(book.get('criticism', []))
    
    if all_praise:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔥 Most Common PRAISE")
            praise_df = pd.Series(all_praise).value_counts().head(10)
            for item, count in praise_df.items():
                if item:  # Only show non-empty items
                    st.markdown(f"✅ {item} *({count} books)*")
        
        with col2:
            st.markdown("#### ⚠️ Most Common CRITICISM")
            criticism_df = pd.Series(all_criticism).value_counts().head(10)
            for item, count in criticism_df.items():
                if item:  # Only show non-empty items
                    st.markdown(f"❌ {item} *({count} books)*")

def show_booktok_insights():
    """Display actionable insights for your book"""
    
    st.markdown("### 💡 Actionable Insights for Your Launch")
    
    books = st.session_state.competitor_books
    
    if not books:
        st.info("Track competitor books to get personalized insights!")
        return
    
    # Generate insights based on tracked books
    insights = []
    
    # Find what's working
    all_praise = []
    for book in books:
        if book.get('mentions', 0) > 100:  # Only consider successful books
            all_praise.extend(book.get('praise', []))
    
    if all_praise:
        praise_counts = pd.Series(all_praise).value_counts()
        if not praise_counts.empty:
            top_praise = praise_counts.head(3)
            insights.append({
                "type": "success",
                "title": "🎯 What's Working for Similar Books",
                "points": [f"Emphasize {item.lower()} in your marketing" for item in top_praise.index if item]
            })
    
    # Find what to avoid
    all_criticism = []
    for book in books:
        if book.get('mentions', 0) > 100:
            all_criticism.extend(book.get('criticism', []))
    
    if all_criticism:
        criticism_counts = pd.Series(all_criticism).value_counts()
        if not criticism_counts.empty:
            top_criticism = criticism_counts.head(3)
            insights.append({
                "type": "warning",
                "title": "⚠️ What to Avoid",
                "points": [f"Avoid {item.lower()} in your story/marketing" for item in top_criticism.index if item]
            })
    
    # Sound trends
    viral_sounds = [b.get('viral_sound') for b in books if b.get('viral_sound')]
    if viral_sounds:
        sound_counts = pd.Series(viral_sounds).value_counts().head(3)
        insights.append({
            "type": "info",
            "title": "🎵 Trending Sounds in Your Genre",
            "points": [f"Consider using: {sound}" for sound in sound_counts.index if sound]
        })
    
    # Display insights
    if not insights:
        st.info("Add more competitor data to generate insights!")
        return
    
    for insight in insights:
        if insight["type"] == "success":
            with st.expander(insight["title"], expanded=True):
                for point in insight["points"]:
                    st.markdown(f"✅ {point}")
        
        elif insight["type"] == "warning":
            with st.expander(insight["title"], expanded=True):
                for point in insight["points"]:
                    st.markdown(f"⚠️ {point}")
        
        else:
            with st.expander(insight["title"], expanded=True):
                for point in insight["points"]:
                    st.markdown(f"💡 {point}")

def show_launch_analysis():
    """Analyze launch timing and performance"""
    
    st.markdown("### 📈 Launch Timing Analysis")
    
    books = st.session_state.competitor_books
    
    if not books:
        st.info("Add competitor books to analyze launch patterns!")
        return
    
    # Filter books with valid dates
    valid_books = []
    for book in books:
        try:
            launch_date = pd.to_datetime(book.get('launch_date', ''))
            if pd.notna(launch_date):
                valid_books.append({
                    "title": book.get('title', 'Unknown'),
                    "launch_date": launch_date,
                    "mentions": book.get('mentions', 0),
                    "genre": book.get('genre', 'Unknown')
                })
        except:
            pass
    
    if not valid_books:
        st.info("No valid launch date data available yet.")
        return
    
    df = pd.DataFrame(valid_books)
    
    # Launch timing chart
    fig = px.scatter(
        df,
        x="launch_date",
        y="mentions",
        size="mentions",
        hover_data=["title"],
        title="Book Launches: Timing vs Success",
        labels={"mentions": "BookTok Mentions", "launch_date": "Launch Date"}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Best times to launch
    st.markdown("#### 📅 Optimal Launch Windows")
    
    # Group by month
    df['month'] = df['launch_date'].dt.month
    monthly_avg = df.groupby('month')['mentions'].mean()
    
    if not monthly_avg.empty:
        best_month = monthly_avg.idxmax()
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        st.info(f"🎯 Based on your tracked books, **{month_names[best_month-1]}** shows the highest BookTok engagement in your genre!")

# Helper functions
def load_sample_competitors():
    """Load sample data for demonstration"""
    return [
        {
            "id": 1,
            "title": "Fourth Wing",
            "author": "Rebecca Yarros",
            "genre": "Romantasy",
            "sub_genre": "Dragon riders, enemies to lovers",
            "launch_date": "2023-05-02",
            "booktok_handle": "@rebeccayarros",
            "mentions": 500000,
            "top_views": 2500000,
            "viral_sound": "Dark academia playlist",
            "praise": ["Dragon bonding", "Enemies to lovers done right", "Fast-paced", "Strong female lead"],
            "criticism": ["Slow start", "Too much worldbuilding", "Predictable romance"],
            "date_added": "2024-01-15",
            "last_updated": "2024-01-15"
        },
        {
            "id": 2,
            "title": "Icebreaker",
            "author": "Hannah Grace",
            "genre": "Contemporary Romance",
            "sub_genre": "Sports romance, college",
            "launch_date": "2022-08-16",
            "booktok_handle": "@hannahgraceauthor",
            "mentions": 350000,
            "top_views": 1800000,
            "viral_sound": "Spicy romance playlist",
            "praise": ["Amazing chemistry", "Fun banter", "Dual POV", "Steamy scenes"],
            "criticism": ["Too long", "Not enough plot", "Repetitive"],
            "date_added": "2024-01-15",
            "last_updated": "2024-01-15"
        }
    ]

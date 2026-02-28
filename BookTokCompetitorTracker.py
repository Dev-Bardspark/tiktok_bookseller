# BookTokCompetitorTracker.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from pathlib import Path

def show_competitor_tracker():
    """Display the BookTok competitor tracking dashboard"""
    
    st.markdown("## 📚 BookTok Competitor Analysis")
    st.markdown("Track similar books launching on BookTok and learn from their success")
    
    # Initialize session state for competitor data
    if 'competitor_books' not in st.session_state:
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
                new_book = {
                    "id": len(st.session_state.competitor_books) + 1,
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
                save_competitor_data(st.session_state.competitor_books)
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
        genres = ["All"] + list(set(b["genre"] for b in st.session_state.competitor_books))
        selected_genre = st.selectbox("Filter by Genre", genres)
    with col2:
        sort_by = st.selectbox("Sort by", ["Recently Added", "Most Mentions", "Launch Date"])
    
    # Filter books
    filtered_books = st.session_state.competitor_books
    if selected_genre != "All":
        filtered_books = [b for b in filtered_books if b["genre"] == selected_genre]
    
    # Sort books
    if sort_by == "Recently Added":
        filtered_books.sort(key=lambda x: x["date_added"], reverse=True)
    elif sort_by == "Most Mentions":
        filtered_books.sort(key=lambda x: x["mentions"], reverse=True)
    elif sort_by == "Launch Date":
        filtered_books.sort(key=lambda x: x["launch_date"])
    
    # Display books in cards
    for book in filtered_books:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{book['title']}** by {book['author']}")
                st.caption(f"📅 {book['launch_date']} | {book['genre']} | {book.get('sub_genre', '')}")
            
            with col2:
                st.metric("Mentions", book.get('mentions', 0))
            
            with col3:
                if book.get('top_views', 0) > 1000000:
                    views = f"{book['top_views']/1000000:.1f}M"
                else:
                    views = f"{book['top_views']/1000:.1f}K"
                st.metric("Top Views", views)
            
            with col4:
                if st.button("🔍 View Details", key=f"view_{book['id']}"):
                    st.session_state.selected_book = book['id']
            
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
            value=book['mentions'],
            key=f"mentions_{book['id']}"
        )
    with col4:
        new_views = st.number_input(
            "Update Top Views",
            value=book['top_views'],
            key=f"views_{book['id']}"
        )
    with col5:
        if st.button("Update", key=f"update_{book['id']}"):
            # Update in session state
            for b in st.session_state.competitor_books:
                if b['id'] == book['id']:
                    b['mentions'] = new_mentions
                    b['top_views'] = new_views
                    b['last_updated'] = datetime.now().strftime("%Y-%m-%d")
            save_competitor_data(st.session_state.competitor_books)
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
    
    # Genre distribution
    genre_counts = pd.DataFrame([
        {"genre": b["genre"], "mentions": b["mentions"]} 
        for b in books
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔥 Most Common PRAISE")
        praise_df = pd.Series(all_praise).value_counts().head(10)
        for item, count in praise_df.items():
            st.markdown(f"✅ {item} *({count} books)*")
    
    with col2:
        st.markdown("#### ⚠️ Most Common CRITICISM")
        criticism_df = pd.Series(all_criticism).value_counts().head(10)
        for item, count in criticism_df.items():
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
        top_praise = pd.Series(all_praise).value_counts().head(3)
        insights.append({
            "type": "success",
            "title": "🎯 What's Working for Similar Books",
            "points": [f"Emphasize {item.lower()} in your marketing" for item in top_praise.index]
        })
    
    # Find what to avoid
    all_criticism = []
    for book in books:
        if book.get('mentions', 0) > 100:
            all_criticism.extend(book.get('criticism', []))
    
    if all_criticism:
        top_criticism = pd.Series(all_criticism).value_counts().head(3)
        insights.append({
            "type": "warning",
            "title": "⚠️ What to Avoid",
            "points": [f"Avoid {item.lower()} in your story/marketing" for item in top_criticism.index]
        })
    
    # Sound trends
    viral_sounds = [b.get('viral_sound') for b in books if b.get('viral_sound')]
    if viral_sounds:
        insights.append({
            "type": "info",
            "title": "🎵 Trending Sounds in Your Genre",
            "points": [f"Consider using: {sound}" for sound in viral_sounds[:3]]
        })
    
    # Display insights
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
    
    # Create launch timeline
    launch_data = []
    for book in books:
        launch_data.append({
            "title": book["title"],
            "launch_date": pd.to_datetime(book["launch_date"]),
            "mentions": book["mentions"],
            "genre": book["genre"]
        })
    
    df = pd.DataFrame(launch_data)
    
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

def save_competitor_data(data):
    """Save to local JSON file"""
    try:
        with open('competitor_books.json', 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass  # Silently fail in demo

def load_competitor_data():
    """Load from local JSON file"""
    try:
        if os.path.exists('competitor_books.json'):
            with open('competitor_books.json', 'r') as f:
                return json.load(f)
    except:
        pass
    return load_sample_competitors()

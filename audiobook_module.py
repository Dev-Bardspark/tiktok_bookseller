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

def show_audiobook_module():
    """Main audiobook module UI"""
    
    st.title("🎧 Audiobook Marketing")
    st.markdown("### Tools for audiobook authors")
    
    # Simple sample data - no database needed for this part
    narrators = [
        {"name": "Julia Whelan", "gender": "Female", "genres": "Romance, Fiction", "rating": 4.9},
        {"name": "Steven Pacey", "gender": "Male", "genres": "Fantasy, Sci-Fi", "rating": 4.8},
        {"name": "Bahni Turpin", "gender": "Female", "genres": "Fiction, YA", "rating": 4.9},
    ]
    
    reviewers = [
        {"name": "Audiobook Reviewer", "platform": "YouTube", "followers": 50000},
        {"name": "Listening Stories", "platform": "Podcast", "followers": 25000},
    ]
    
    tab1, tab2 = st.tabs(["Find Narrators", "Find Reviewers"])
    
    with tab1:
        st.subheader("🎙️ Narrators")
        for n in narrators:
            st.write(f"**{n['name']}** - {n['gender']} - {n['genres']} - ⭐ {n['rating']}")
    
    with tab2:
        st.subheader("🔍 Reviewers")
        for r in reviewers:
            st.write(f"**{r['name']}** - {r['platform']} - {r['followers']} followers")

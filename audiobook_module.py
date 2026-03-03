import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import traceback
import sys

def show_audiobook_module():
    """Main audiobook module UI with full debugging"""
    
    try:
        st.title("🎧 Audiobook Marketing")
        st.write("✅ Step 1: Page loaded")
        
        # Show connection info (without password)
        try:
            st.write("🔌 Database host:", st.secrets["postgres"]["host"])
            st.write("🔌 Database name:", st.secrets["postgres"]["database"])
            st.write("🔌 Database user:", st.secrets["postgres"]["user"])
        except Exception as e:
            st.error(f"❌ Cannot read secrets: {e}")
            return
        
        # Test database connection
        try:
            st.write("🔄 Testing connection...")
            conn = psycopg2.connect(
                host=st.secrets["postgres"]["host"],
                port=st.secrets["postgres"]["port"],
                database=st.secrets["postgres"]["database"],
                user=st.secrets["postgres"]["user"],
                password=st.secrets["postgres"]["password"]
            )
            st.write("✅ Connection successful")
            
            # Test query
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM audiobook_narrators")
            count = cur.fetchone()[0]
            st.write(f"✅ Found {count} narrators in database")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            st.error(f"❌ Database error: {str(e)}")
            st.code(traceback.format_exc())
            return
        
        # Create tabs
        st.write("✅ Step 2: Creating tabs")
        tab1, tab2, tab3 = st.tabs(["Find Narrators", "Find Reviewers", "My Audiobooks"])
        
        with tab1:
            st.write("✅ Narrator tab loaded")
            show_narrator_finder()
        
        with tab2:
            st.write("✅ Reviewer tab loaded")
            show_reviewer_finder()
        
        with tab3:
            st.write("✅ My Audiobooks tab loaded")
            show_my_audiobooks()
            
        st.write("✅ All tabs loaded successfully")
        
    except Exception as e:
        st.error(f"❌ CRITICAL ERROR: {str(e)}")
        st.code(traceback.format_exc())

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
        st.error(f"🔴 DB Connection error: {e}")
        return None

def show_narrator_finder():
    try:
        st.subheader("Find Narrators")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            genre = st.selectbox("Genre", ["Any", "Romance", "Fantasy", "Sci-Fi", "Mystery", "Thriller", "Fiction"])
        with col2:
            gender = st.selectbox("Voice Gender", ["Any", "Male", "Female"])
        with col3:
            budget = st.selectbox("Budget", ["Any", "$", "$$", "$$$"])
        
        if st.button("Search Narrators"):
            st.write("Searching...")
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
            
            st.write(f"Query: {query}")
            st.write(f"Params: {params}")
            
            cur.execute(query, params)
            narrators = cur.fetchall()
            st.write(f"Found {len(narrators)} narrators")
            
            cur.close()
            conn.close()
            
            if narrators:
                for n in narrators:
                    with st.expander(f"🎙️ {n['narrator_name']}"):
                        st.write(n)
            else:
                st.info("No narrators found")
                
    except Exception as e:
        st.error(f"Error in narrator finder: {e}")
        st.code(traceback.format_exc())

def show_reviewer_finder():
    try:
        st.subheader("Find Audiobook Reviewers")
        st.write("Reviewer tab working")
        
        genre = st.selectbox("Filter by Genre", ["Any", "Romance", "Fantasy", "Sci-Fi", "Mystery", "Thriller", "YA"])
        
        if st.button("Search Reviewers"):
            st.write("Searching reviewers...")
            
    except Exception as e:
        st.error(f"Error in reviewer finder: {e}")

def show_my_audiobooks():
    try:
        st.subheader("My Audiobook Projects")
        st.write("My Audiobooks tab working")
        
        if not st.session_state.authenticated:
            st.warning("Please login")
            return
            
        st.write(f"User ID: {st.session_state.user_id}")
        
    except Exception as e:
        st.error(f"Error in my audiobooks: {e}")

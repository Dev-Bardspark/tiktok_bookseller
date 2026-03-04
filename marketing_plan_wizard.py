# marketing_plan.py - FIXED to use REAL data
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
import psycopg2
from psycopg2.extras import RealDictCursor

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

def load_user_book_analysis(user_id):
    """Load the most recent book analysis from database"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_book_analyses 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        result = cur.fetchone()
        return dict(result) if result else None
    except Exception as e:
        st.error(f"Error loading book analysis: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def load_user_persona(user_id):
    """Load the most recent author persona from database"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_author_personas 
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        result = cur.fetchone()
        return dict(result) if result else None
    except Exception as e:
        st.error(f"Error loading author persona: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def load_user_marketing_assets(user_id):
    """Load the most recent marketing assets from database"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_marketing_assets 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        result = cur.fetchone()
        if result:
            asset_data = result['asset_data']
            if isinstance(asset_data, str):
                try:
                    asset_data = json.loads(asset_data)
                except:
                    pass
            return asset_data
        return None
    except Exception as e:
        st.error(f"Error loading marketing assets: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def extract_book_info(analysis_data):
    """Extract book info from analysis data"""
    if not analysis_data:
        return {}
    
    if isinstance(analysis_data, dict):
        # Try different possible structures
        if 'analysis_result' in analysis_data:
            result = analysis_data['analysis_result']
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    pass
            if isinstance(result, dict) and 'book_info' in result:
                return result['book_info']
        elif 'book_info' in analysis_data:
            return analysis_data['book_info']
        elif 'title' in analysis_data:
            return analysis_data
    
    return {}

def extract_persona_data(persona_record):
    """Extract persona data from database record"""
    if not persona_record:
        return {}
    
    persona_data = persona_record.get('persona_data')
    if isinstance(persona_data, str):
        try:
            return json.loads(persona_data)
        except:
            return {}
    return persona_data or {}

def show_plan():
    """Display the integrated marketing plan"""
    
    # Check login
    if not st.session_state.get('authenticated', False):
        st.warning("🔒 Please login to view your marketing plan")
        if st.button("Go to Login", use_container_width=True):
            st.session_state.page = "🏠 Dashboard"
            st.rerun()
        return
    
    st.title("📊 Your Integrated Marketing Plan")
    st.markdown("---")
    
    user_id = st.session_state.get('user_id', 1)
    
    # LOAD REAL DATA FROM DATABASE
    with st.spinner("Loading your marketing data..."):
        book_analysis = load_user_book_analysis(user_id)
        author_persona = load_user_persona(user_id)
        marketing_assets = load_user_marketing_assets(user_id)
    
    # Extract book info
    book_info = extract_book_info(book_analysis) if book_analysis else {}
    book_title = book_info.get('title', 'No book analyzed yet')
    book_genre = book_info.get('genre', 'Unknown')
    
    # Extract persona info
    persona_data = extract_persona_data(author_persona) if author_persona else {}
    author_type = persona_data.get('author_type', 'No persona yet')
    
    # Header with REAL data
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div style="padding: 1rem; background: #f0f2f6; border-radius: 10px; text-align: center;">
            <h3 style="margin: 0;">📚 Book</h3>
            <p style="font-size: 1.2rem; font-weight: bold; margin: 0;">{book_title}</p>
            <p style="color: #666;">{book_genre}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        persona_display = author_type if author_type != 'No persona yet' else "Not set"
        st.markdown(f"""
        <div style="padding: 1rem; background: #f0f2f6; border-radius: 10px; text-align: center;">
            <h3 style="margin: 0;">🎭 Author Persona</h3>
            <p style="font-size: 1.2rem; font-weight: bold; margin: 0;">{persona_display}</p>
            <p style="color: #666;">{persona_data.get('interaction_style', '')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        asset_status = "✅ Ready" if marketing_assets else "⚠️ Not generated"
        st.markdown(f"""
        <div style="padding: 1rem; background: #f0f2f6; border-radius: 10px; text-align: center;">
            <h3 style="margin: 0;">🎨 Marketing Assets</h3>
            <p style="font-size: 1.2rem; font-weight: bold; margin: 0;">{asset_status}</p>
            <p style="color: #666;">{len(marketing_assets) if marketing_assets else 0} assets available</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Show missing data warnings
    if not book_analysis:
        st.warning("⚠️ No book analysis found. Please analyze a book first.")
        if st.button("📖 Go to Book Analyzer"):
            st.session_state.page = "📖 Book Analyzer"
            st.rerun()
    
    if not author_persona:
        st.warning("⚠️ No author persona found. Please take the persona quiz.")
        if st.button("🎭 Discover Your Persona"):
            st.session_state.page = "🎭 Author Persona"
            st.rerun()
    
    if not marketing_assets:
        st.warning("⚠️ No marketing assets generated. Please generate assets for your book.")
        if st.button("🎨 Generate Marketing Assets"):
            st.session_state.page = "🎨 Marketing Assets"
            st.rerun()
    
    # If we have data, show the integrated plan
    if book_analysis and author_persona and marketing_assets:
        st.success("✅ All marketing data loaded successfully!")
        
        # Create tabs for different plan views
        tab1, tab2, tab3 = st.tabs(["📅 Launch Timeline", "📱 Platform Strategy", "📊 Progress Tracker"])
        
        with tab1:
            st.markdown("### Your Personalized Launch Timeline")
            
            # Get timeline from marketing assets
            timeline = marketing_assets.get('launch_timeline', {})
            if timeline:
                phases = [
                    ("6_weeks_before", "6 Weeks Before Launch"),
                    ("4_weeks_before", "4 Weeks Before Launch"),
                    ("2_weeks_before", "2 Weeks Before Launch"),
                    ("launch_week", "Launch Week"),
                    ("post_launch", "Post-Launch")
                ]
                
                for phase_key, phase_name in phases:
                    items = timeline.get(phase_key, [])
                    if items:
                        with st.expander(f"**{phase_name}**", expanded=True):
                            for i, item in enumerate(items, 1):
                                st.markdown(f"{i}. {item}")
            else:
                st.info("No timeline found in marketing assets")
        
        with tab2:
            st.markdown("### Platform Strategy Based on Your Persona")
            
            # Get platform scores from persona
            platform_scores = persona_data.get('platform_scores', [])
            if platform_scores:
                df = pd.DataFrame(platform_scores)
                fig = px.bar(df, x='name', y='score', 
                           title="Your Platform Match Scores",
                           color='score', 
                           color_continuous_scale='viridis')
                st.plotly_chart(fig, use_container_width=True)
                
                # Show top platforms
                st.markdown("#### Your Top 3 Platforms")
                cols = st.columns(3)
                for i, platform in enumerate(platform_scores[:3]):
                    with cols[i]:
                        st.markdown(f"""
                        <div style="padding: 1rem; background: #f0f2f6; border-radius: 10px; text-align: center;">
                            <h4>{platform['name']}</h4>
                            <p style="font-size: 2rem; font-weight: bold;">{platform['score']}%</p>
                            <small>{platform['reason']}</small>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No platform scores found in persona data")
        
        with tab3:
            st.markdown("### Your Marketing Progress")
            
            # Calculate progress metrics
            total_assets = sum(1 for v in marketing_assets.values() if v)
            
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            metrics_col1.metric("Total Asset Types", total_assets)
            metrics_col2.metric("Book Analysis", "✅ Complete")
            metrics_col3.metric("Author Persona", "✅ Complete")
            
            # Asset checklist
            st.markdown("#### Generated Assets Checklist")
            asset_types = [
                "Blurbs", "TikTok Scripts", "YouTube Scripts", "Instagram Posts",
                "Instagram Reels", "Amazon Options", "Facebook Ads", "Email Sequences",
                "Press Kits", "Pinterest Options", "Goodreads Options", "Podcast Pitches",
                "Launch Timeline"
            ]
            
            cols = st.columns(3)
            for i, asset_type in enumerate(asset_types):
                key = asset_type.lower().replace(' ', '_')
                if key == 'blurbs':
                    exists = 'blurbs' in marketing_assets
                elif key == 'tiktok_scripts':
                    exists = 'tiktok_scripts' in marketing_assets
                # ... add all mappings
                else:
                    exists = key in marketing_assets
                
                with cols[i % 3]:
                    if exists:
                        st.markdown(f"✅ **{asset_type}**")
                    else:
                        st.markdown(f"⬜ {asset_type}")
    
    else:
        # Show getting started guide
        st.markdown("### 🚀 Getting Started")
        st.markdown("""
        To create your integrated marketing plan, you need to complete these steps:
        
        1. **📖 Analyze your book** in the Book Analyzer
        2. **🎭 Discover your author persona** with the quiz
        3. **🎨 Generate marketing assets** for your book
        
        Once all three are complete, this page will show your personalized plan!
        """)

if __name__ == "__main__":
    show_plan()

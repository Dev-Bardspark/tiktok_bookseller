"""
Author Website Builder Module for BardSpark
Creates a website using Mozilla Soloist.ai based on author data and questionnaire
"""

import streamlit as st
import json
import webbrowser
import base64
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

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

def save_website_draft_to_db(user_id, draft_name, basic_info, design_preferences, book_content, cover_image_url=None):
    """Save a website builder draft to database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Combine all website data
        website_data = {
            "basic_info": basic_info,
            "design_preferences": design_preferences,
            "book_content": book_content,
            "created_at": datetime.now().isoformat()
        }
        
        cur.execute("""
            INSERT INTO user_website_drafts 
            (user_id, draft_name, website_data, cover_image_url, created_at, updated_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            draft_name,
            json.dumps(website_data),
            cover_image_url,
            datetime.now(),
            datetime.now(),
            'draft'
        ))
        
        draft_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return draft_id
    except Exception as e:
        st.error(f"Error saving website draft: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def load_user_website_drafts(user_id):
    """Load all website drafts for a user"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_website_drafts 
            WHERE user_id = %s
            ORDER BY updated_at DESC
        """, (user_id,))
        
        drafts = cur.fetchall()
        cur.close()
        conn.close()
        
        # Parse JSON data
        result = []
        for d in drafts:
            draft_dict = dict(d)
            if draft_dict.get('website_data'):
                if isinstance(draft_dict['website_data'], str):
                    draft_dict['website_data'] = json.loads(draft_dict['website_data'])
            result.append(draft_dict)
        
        return result
    except Exception as e:
        st.error(f"Error loading website drafts: {e}")
        return []

def update_website_draft(user_id, draft_id, website_data, cover_image_url=None):
    """Update an existing website draft"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE user_website_drafts 
            SET website_data = %s, cover_image_url = %s, updated_at = %s
            WHERE user_id = %s AND id = %s
        """, (
            json.dumps(website_data),
            cover_image_url,
            datetime.now(),
            user_id,
            draft_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating website draft: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def delete_website_draft(user_id, draft_id):
    """Delete a website draft"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM user_website_drafts 
            WHERE user_id = %s AND id = %s
        """, (user_id, draft_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error deleting website draft: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

# ============================================================================
# DATA FUNCTIONS - Pull from existing session data
# ============================================================================
def get_author_data():
    """Pull existing author data from session state"""
    # Safely get current_user
    current_user = st.session_state.get('current_user')
    author_name = ''
    if current_user and isinstance(current_user, dict):
        author_name = current_user.get('name', '')
    
    # Safely get saved readers
    saved_readers = st.session_state.get('saved_readers', [])
    if not isinstance(saved_readers, list):
        saved_readers = []
    
    data = {
        "author_name": author_name,
        "author_persona": {},
        "latest_book": {},
        "saved_advocates": saved_readers[:6],  # Top 6 saved
        "genres": []
    }
    
    # Try to get from author_persona if it exists
    if 'persona_results' in st.session_state:
        persona = st.session_state.persona_results
        if isinstance(persona, dict):
            data["author_persona"] = persona
    
    # Try to get from book analyzer
    if 'analysis_result' in st.session_state:
        analysis = st.session_state.analysis_result
        if isinstance(analysis, dict):
            data["latest_book"] = analysis
    
    return data

# ============================================================================
# QUESTIONNAIRE UI
# ============================================================================
def render_questionnaire():
    st.title("🌐 Author Website Builder")
    st.markdown("### Create your professional author website in minutes")
    
    # Check authentication
    if not st.session_state.get('authenticated', False):
        st.warning("Please login to save your website drafts")
    
    # Initialize session state for website drafts
    if 'website_drafts' not in st.session_state:
        st.session_state.website_drafts = []
        if st.session_state.get('authenticated', False):
            st.session_state.website_drafts = load_user_website_drafts(st.session_state.user_id)
    
    # Pull existing data
    author_data = get_author_data()
    
    # Progress tracking
    if 'website_step' not in st.session_state:
        st.session_state.website_step = 1
    
    # Create tabs for builder and saved drafts
    tab1, tab2 = st.tabs(["🏗️ Website Builder", "💾 My Saved Drafts"])
    
    with tab1:
        show_builder(author_data)
    
    with tab2:
        show_saved_drafts()

def show_builder(author_data):
    """Main website builder interface"""
    
    # Step indicators
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**Step 1** 📋" if st.session_state.website_step >= 1 else "Step 1")
    with col2:
        st.markdown("**Step 2** 🎨" if st.session_state.website_step >= 2 else "Step 2")
    with col3:
        st.markdown("**Step 3** 📚" if st.session_state.website_step >= 3 else "Step 3")
    with col4:
        st.markdown("**Step 4** 🚀" if st.session_state.website_step >= 4 else "Step 4")
    
    st.markdown("---")
    
    # ============================================================================
    # STEP 1: BASIC INFO
    # ============================================================================
    if st.session_state.website_step == 1:
        st.header("Step 1: Basic Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            author_name = st.text_input(
                "Your Name *",
                value=author_data.get('author_name', '')
            )
            
            pen_name = st.text_input(
                "Pen Name (if different)",
                value=""
            )
            
            tagline = st.text_input(
                "Tagline",
                placeholder="e.g., Award-winning Fantasy Author"
            )
        
        with col2:
            email = st.text_input(
                "Email for Contact *",
                placeholder="author@example.com"
            )
            
            website_url = st.text_input(
                "Current Website (if any)",
                placeholder="https://..."
            )
            
            if author_data.get('author_persona'):
                default_audience = author_data['author_persona'].get('target_audience', '')
            else:
                default_audience = ''
            
            target_audience = st.text_area(
                "Target Audience",
                value=default_audience,
                placeholder="e.g., Romance readers who love slow-burn and spice"
            )
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col3:
            if st.button("Next →", type="primary", use_container_width=True):
                st.session_state.website_basic = {
                    "author_name": author_name,
                    "pen_name": pen_name,
                    "tagline": tagline,
                    "email": email,
                    "website_url": website_url,
                    "target_audience": target_audience
                }
                st.session_state.website_step = 2
                st.rerun()
    
    # ============================================================================
    # STEP 2: DESIGN & PAGES
    # ============================================================================
    elif st.session_state.website_step == 2:
        st.header("Step 2: Design & Pages")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎨 Color Theme")
            color_theme = st.selectbox(
                "Choose a color scheme",
                options=[
                    "Professional Blue",
                    "Warm Romance",
                    "Dark Fantasy", 
                    "Minimalist Light",
                    "Mystery Noir",
                    "Vibrant YA"
                ],
                index=0
            )
            
            font_style = st.selectbox(
                "Font Style",
                options=[
                    "Classic Serif",
                    "Modern Sans",
                    "Elegant Script",
                    "Bold Display",
                    "Clean Minimal"
                ],
                index=0
            )
        
        with col2:
            st.subheader("📄 Pages to Include")
            
            st.markdown("**Required Pages:**")
            st.markdown("- ✅ Home Page (auto-included)")
            st.markdown("- ✅ About Me (auto-included)")
            st.markdown("- ✅ Contact (auto-included)")
            
            st.markdown("**Optional Pages:**")
            pages = {
                "books": "📚 My Books (catalog)",
                "book_detail": "📖 Individual Book Pages",
                "blog": "✍️ Blog / News",
                "newsletter": "📧 Newsletter Signup",
                "arc": "⭐ ARC Readers/Influencers Showcase",
                "events": "🗓️ Events / Appearances",
                "reviews": "💬 Reviews / Testimonials",
                "press": "📰 Press Kit"
            }
            
            selected_pages = {}
            for key, label in pages.items():
                selected_pages[key] = st.checkbox(label, value=(key == "books"))
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back", use_container_width=True):
                st.session_state.website_step = 1
                st.rerun()
        with col3:
            if st.button("Next →", type="primary", use_container_width=True):
                st.session_state.website_design = {
                    "color_theme": color_theme,
                    "font_style": font_style,
                    "selected_pages": selected_pages
                }
                st.session_state.website_step = 3
                st.rerun()
    
    # ============================================================================
    # STEP 3: BOOKS & CONTENT (WITH BOOK ANALYZER DATA)
    # ============================================================================
    elif st.session_state.website_step == 3:
        st.header("Step 3: Books & Content")
        
        # Get book data from analyzer
        book_data = author_data.get('latest_book', {})
        book_info = book_data.get('book_info', {}) if isinstance(book_data, dict) else {}
        
        # Get marketability data for description fallback
        market_data = book_data.get('marketability', {}) if isinstance(book_data, dict) else {}
        
        st.subheader("📚 Your Book")
        
        col1, col2 = st.columns(2)
        
        with col1:
            book_title = st.text_input(
                "Book Title *",
                value=book_info.get('title', '')
            )
            
            book_genre = st.text_input(
                "Genre",
                value=book_info.get('genre', '')
            )
            
            book_link_amazon = st.text_input(
                "Amazon Link",
                placeholder="https://amazon.com/dp/..."
            )
        
        with col2:
            # COVER UPLOAD
            book_cover = st.file_uploader(
                "📸 Book Cover Image",
                type=['jpg', 'jpeg', 'png', 'webp'],
                help="Upload your book cover (this will be included in your site)"
            )
            
            if book_cover:
                st.image(book_cover, width=150, caption="Cover Preview")
            
            book_link_goodreads = st.text_input(
                "Goodreads Link",
                placeholder="https://goodreads.com/book/..."
            )
        
        # Book description (pulled from analyzer)
        default_desc = book_info.get('description', market_data.get('overall_assessment', ''))
        book_description = st.text_area(
            "Book Description",
            value=default_desc,
            placeholder="Enter your book blurb...",
            height=150
        )
        
        # Advocate showcase option
        if author_data.get('saved_advocates'):
            st.subheader("⭐ Showcase Your Advocates")
            st.markdown(f"**{len(author_data['saved_advocates'])} saved advocates available**")
            
            showcase_advocates = st.checkbox(
                "Include advocate showcase on my site",
                value=True,
                help="Show ARC readers and influencers who support your work"
            )
        else:
            showcase_advocates = False
            st.info("Save some ARC readers/influencers first to showcase them on your site!")
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back", use_container_width=True):
                st.session_state.website_step = 2
                st.rerun()
        with col3:
            if st.button("Next →", type="primary", use_container_width=True):
                st.session_state.website_books = {
                    "book_title": book_title,
                    "book_genre": book_genre,
                    "book_description": book_description,
                    "book_cover": book_cover,
                    "book_link_amazon": book_link_amazon,
                    "book_link_goodreads": book_link_goodreads,
                    "showcase_advocates": showcase_advocates
                }
                st.session_state.website_step = 4
                st.rerun()
    
    # ============================================================================
    # STEP 4: REVIEW & BUILD
    # ============================================================================
    elif st.session_state.website_step == 4:
        st.header("Step 4: Review & Build")
        
        st.markdown("### 📋 Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Author Info:**")
            basic = st.session_state.get('website_basic', {})
            st.markdown(f"- Name: {basic.get('author_name', '—')}")
            st.markdown(f"- Tagline: {basic.get('tagline', '—')}")
            st.markdown(f"- Email: {basic.get('email', '—')}")
            
            st.markdown("**Design:**")
            design = st.session_state.get('website_design', {})
            st.markdown(f"- Theme: {design.get('color_theme', '—')}")
            st.markdown(f"- Font: {design.get('font_style', '—')}")
        
        with col2:
            st.markdown("**Book:**")
            books = st.session_state.get('website_books', {})
            st.markdown(f"- Title: {books.get('book_title', '—')}")
            st.markdown(f"- Genre: {books.get('book_genre', '—')}")
            st.markdown(f"- Cover: {'✅ Uploaded' if books.get('book_cover') else '❌ Not uploaded'}")
            st.markdown(f"- Showcase Advocates: {'✅' if books.get('showcase_advocates') else '❌'}")
        
        st.markdown("---")
        st.markdown("### 🚀 Ready to Build")
        
        # Get book data from analyzer for additional info
        book_data = author_data.get('latest_book', {})
        book_info = book_data.get('book_info', {}) if isinstance(book_data, dict) else {}
        market_data = book_data.get('marketability', {}) if isinstance(book_data, dict) else {}
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back", use_container_width=True):
                st.session_state.website_step = 3
                st.rerun()
        
        with col2:
            # Save draft button
            if st.button("💾 Save Draft", use_container_width=True):
                if st.session_state.get('authenticated', False):
                    basic = st.session_state.get('website_basic', {})
                    design = st.session_state.get('website_design', {})
                    books = st.session_state.get('website_books', {})
                    
                    draft_name = f"{books.get('book_title', 'My Website')} - {datetime.now().strftime('%Y-%m-%d')}"
                    
                    draft_id = save_website_draft_to_db(
                        st.session_state.user_id,
                        draft_name,
                        basic,
                        design,
                        books
                    )
                    
                    if draft_id:
                        st.success("✅ Draft saved to your library!")
                        # Refresh drafts
                        st.session_state.website_drafts = load_user_website_drafts(st.session_state.user_id)
                else:
                    st.warning("Please login to save drafts")
        
        with col3:
            if st.button("🚀 Build My Site", type="primary", use_container_width=True):
                books = st.session_state.get('website_books', {})
                
                # CORRECT URL for Soloist.ai onboarding
                onboarding_url = "https://soloist.ai/onboarding"
                
                # Open the onboarding page
                st.markdown(f"**[Click here to start building your site on Soloist.ai]({onboarding_url})**")
                
                # Show helpful info with their data
                st.info("""
                **📋 Next Steps:**
                1. Click the link above to open Soloist.ai
                2. Enter your **Author Name** as the Business name
                3. Use your book description below
                4. Complete the remaining steps
                """)
                
                # Show their data in an expander for easy copying
                with st.expander("📋 Your Book Data (Copy this into Soloist.ai)", expanded=True):
                    st.markdown(f"**Business Name:** {basic.get('author_name', '')}")
                    st.markdown(f"**Book Title:** {books.get('book_title', book_info.get('title', ''))}")
                    st.markdown(f"**Genre:** {books.get('book_genre', book_info.get('genre', ''))}")
                    st.markdown(f"**Description:** {books.get('book_description', book_info.get('description', market_data.get('overall_assessment', '')))}")
                    
                    if books.get('book_cover'):
                        st.markdown("**Cover Image:** ✅ Uploaded (you'll need to upload it manually on Soloist.ai)")
                    
                    if books.get('showcase_advocates') and author_data.get('saved_advocates'):
                        st.markdown("**Advocates to Showcase:**")
                        for a in author_data['saved_advocates'][:5]:
                            st.markdown(f"- @{a.get('username')} ({a.get('follower_count', 0)} followers)")

def show_saved_drafts():
    """Display user's saved website drafts"""
    
    if not st.session_state.get('authenticated', False):
        st.warning("Please login to view your saved drafts")
        return
    
    if not st.session_state.website_drafts:
        st.info("You haven't saved any website drafts yet. Build a site and click 'Save Draft' in Step 4.")
        return
    
    st.markdown(f"### 📚 Your Saved Drafts ({len(st.session_state.website_drafts)})")
    
    for draft in st.session_state.website_drafts:
        with st.expander(f"🌐 {draft.get('draft_name', 'Untitled')} - {draft.get('created_at', '')[:10] if draft.get('created_at') else ''}"):
            website_data = draft.get('website_data', {})
            
            if website_data:
                st.markdown("**Basic Info:**")
                basic = website_data.get('basic_info', {})
                st.markdown(f"- Name: {basic.get('author_name', 'N/A')}")
                st.markdown(f"- Tagline: {basic.get('tagline', 'N/A')}")
                
                st.markdown("**Book:**")
                book = website_data.get('book_content', {})
                st.markdown(f"- Title: {book.get('book_title', 'N/A')}")
                st.markdown(f"- Genre: {book.get('book_genre', 'N/A')}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📂 Load Draft", key=f"load_{draft['id']}"):
                    # Load draft into session
                    website_data = draft.get('website_data', {})
                    st.session_state.website_basic = website_data.get('basic_info', {})
                    st.session_state.website_design = website_data.get('design_preferences', {})
                    st.session_state.website_books = website_data.get('book_content', {})
                    st.session_state.website_step = 4
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Delete", key=f"delete_{draft['id']}"):
                    if delete_website_draft(st.session_state.user_id, draft['id']):
                        st.session_state.website_drafts = [d for d in st.session_state.website_drafts if d['id'] != draft['id']]
                        st.success("Draft deleted!")
                        st.rerun()

# ============================================================================
# MAIN FUNCTION TO CALL FROM BARDSPARK
# ============================================================================
def show_website_builder():
    render_questionnaire()

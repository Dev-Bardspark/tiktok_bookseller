"""
Author Website Builder Module for BardSpark
Creates a website using Mozilla Soloist.ai based on author data and questionnaire
"""

import streamlit as st
import json
import webbrowser
import base64
from datetime import datetime

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
    
    # Pull existing data
    author_data = get_author_data()
    
    # Progress tracking
    if 'website_step' not in st.session_state:
        st.session_state.website_step = 1
    
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
    # STEP 3: BOOKS & CONTENT
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
            # COVER UPLOAD - THIS IS NEW
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
        
        # Book description
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
        
        with col3:
            if st.button("🚀 Build My Site", type="primary", use_container_width=True):
                books = st.session_state.get('website_books', {})
                
                # Handle cover image if uploaded - convert to data URL
                cover_data_url = None
                if books.get('book_cover'):
                    bytes_data = books['book_cover'].getvalue()
                    base64_str = base64.b64encode(bytes_data).decode('utf-8')
                    file_ext = books['book_cover'].name.split('.')[-1]
                    mime_type = f"image/{file_ext}"
                    cover_data_url = f"data:{mime_type};base64,{base64_str}"
                
                # Create JSON-serializable data
                json_safe_data = {
                    "author": st.session_state.get('website_basic', {}),
                    "design": st.session_state.get('website_design', {}),
                    "books": {
                        "book_title": books.get('book_title', book_info.get('title', '')),
                        "book_genre": books.get('book_genre', book_info.get('genre', '')),
                        "book_description": books.get('book_description', book_info.get('description', market_data.get('overall_assessment', ''))),
                        "book_cover_data_url": cover_data_url,  # This contains the actual image
                        "book_link_amazon": books.get('book_link_amazon', ''),
                        "book_link_goodreads": books.get('book_link_goodreads', ''),
                        "showcase_advocates": books.get('showcase_advocates', False)
                    },
                    "advocates": [
                        {
                            "username": a.get('username'),
                            "platforms": a.get('platforms', []),
                            "follower_count": a.get('follower_count', 0)
                        }
                        for a in author_data.get('saved_advocates', [])
                    ] if books.get('showcase_advocates') else []
                }
                
                # Convert to JSON for passing to Soloist
                json_data = json.dumps(json_safe_data)
                
                # Soloist.ai URL with data (they support URL parameters)
                soloist_url = f"https://soloist.ai/create?data={json_data}"
                
                # Open in new tab
                webbrowser.open_new_tab(soloist_url)
                
                st.success("✅ Opening Soloist.ai with your data!")
                st.info("Complete the final steps on Soloist.ai to publish your site.")
    
    # Show saved count in sidebar
    st.sidebar.markdown("---")
    saved_count = len(st.session_state.get('saved_readers', []))
    st.sidebar.markdown(f"### ❤️ Saved: {saved_count}")

# ============================================================================
# MAIN FUNCTION TO CALL FROM BARDSPARK
# ============================================================================
def show_website_builder():
    render_questionnaire()

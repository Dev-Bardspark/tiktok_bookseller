"""
Author Website Builder Module for BardSpark
Generates HTML sections that users can copy-paste into their website
"""

import streamlit as st
import json
import base64
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import re

# ============================================================================
# DATABASE CONNECTION (Keep your existing connection functions)
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
# IMPROVED DATA FUNCTIONS - Properly pull from all sources
# ============================================================================
def get_complete_author_data():
    """Pull ALL existing author data from session state with proper error handling"""
    
    # Initialize with defaults
    data = {
        "profile": {},
        "book_analysis": {},
        "marketing_assets": {},
        "advocates": [],
        "genres": []
    }
    
    # 1. Get User Profile Data
    if st.session_state.get('authenticated', False):
        try:
            # Try to get from current_user
            current_user = st.session_state.get('current_user', {})
            if isinstance(current_user, dict):
                data["profile"] = {
                    "name": current_user.get('name', ''),
                    "email": current_user.get('email', ''),
                    "pen_name": current_user.get('pen_name', ''),
                    "bio": current_user.get('bio', ''),
                    "website": current_user.get('website', ''),
                    "social_media": current_user.get('social_media', {})
                }
        except Exception as e:
            st.warning(f"Could not load profile data: {e}")
    
    # 2. Get Book Analyzer Results
    try:
        # Check various possible locations for book analysis
        if 'analysis_result' in st.session_state:
            analysis = st.session_state.analysis_result
            if isinstance(analysis, dict):
                # Extract book info safely
                book_info = analysis.get('book_info', {})
                if isinstance(book_info, str):
                    try:
                        book_info = json.loads(book_info)
                    except:
                        book_info = {}
                
                # Extract marketability data
                marketability = analysis.get('marketability', {})
                if isinstance(marketability, str):
                    try:
                        marketability = json.loads(marketability)
                    except:
                        marketability = {}
                
                data["book_analysis"] = {
                    "title": book_info.get('title', ''),
                    "author": book_info.get('author', data["profile"].get('name', '')),
                    "genre": book_info.get('genre', ''),
                    "subgenres": book_info.get('subgenres', []),
                    "description": book_info.get('description', ''),
                    "target_audience": marketability.get('target_audience', ''),
                    "comparable_titles": marketability.get('comparable_titles', []),
                    "unique_selling_points": marketability.get('unique_selling_points', []),
                    "themes": book_info.get('themes', [])
                }
    except Exception as e:
        st.warning(f"Could not load book analysis: {e}")
    
    # 3. Get Marketing Assets
    try:
        if 'marketing_assets' in st.session_state:
            assets = st.session_state.marketing_assets
            if isinstance(assets, dict):
                data["marketing_assets"] = {
                    "cover_image": assets.get('cover_image'),
                    "author_photo": assets.get('author_photo'),
                    "book_trailer": assets.get('book_trailer'),
                    "press_kit": assets.get('press_kit'),
                    "review_quotes": assets.get('review_quotes', []),
                    "endorsements": assets.get('endorsements', [])
                }
    except Exception as e:
        st.warning(f"Could not load marketing assets: {e}")
    
    # 4. Get Saved Advocates/Readers
    try:
        saved_readers = st.session_state.get('saved_readers', [])
        if saved_readers and isinstance(saved_readers, list):
            # Get top advocates with complete data
            data["advocates"] = []
            for reader in saved_readers[:8]:  # Top 8 advocates
                if isinstance(reader, dict):
                    data["advocates"].append({
                        "username": reader.get('username', ''),
                        "platform": reader.get('platform', ''),
                        "follower_count": reader.get('follower_count', 0),
                        "engagement_rate": reader.get('engagement_rate', ''),
                        "niche": reader.get('niche', ''),
                        "testimonial": reader.get('testimonial', '')
                    })
    except Exception as e:
        st.warning(f"Could not load advocates: {e}")
    
    return data

# ============================================================================
# HTML SECTION GENERATORS
# ============================================================================

def generate_author_bio_section(data):
    """Generate HTML for author bio section"""
    
    profile = data.get('profile', {})
    book = data.get('book_analysis', {})
    
    author_name = profile.get('pen_name') or profile.get('name', 'Your Name')
    author_bio = profile.get('bio', book.get('description', '')[:200] + '...' if book.get('description') else '')
    
    html = f"""
    <!-- AUTHOR BIO SECTION - Copy and paste this where you want your bio to appear -->
    <section class="author-bio" style="padding: 60px 20px; background-color: #f9f9f9;">
        <div style="max-width: 800px; margin: 0 auto; text-align: center;">
            <h2 style="font-size: 2.5em; margin-bottom: 20px; color: #333;">About {author_name}</h2>
            <div style="width: 100px; height: 3px; background-color: #crimson; margin: 0 auto 30px;"></div>
            <p style="font-size: 1.2em; line-height: 1.6; color: #666; margin-bottom: 30px;">
                {author_bio}
            </p>
    """
    
    # Add social links if available
    social = profile.get('social_media', {})
    if social:
        html += '<div class="social-links" style="margin-top: 30px;">'
        for platform, url in social.items():
            if url:
                html += f'<a href="{url}" target="_blank" style="display: inline-block; margin: 0 10px; padding: 10px 20px; background-color: #333; color: white; text-decoration: none; border-radius: 5px;">{platform.title()}</a>'
        html += '</div>'
    
    html += """
        </div>
    </section>
    <!-- END AUTHOR BIO SECTION -->
    """
    
    return html

def generate_book_showcase_section(data):
    """Generate HTML for book showcase section"""
    
    book = data.get('book_analysis', {})
    assets = data.get('marketing_assets', {})
    
    title = book.get('title', 'My Book')
    genre = book.get('genre', '')
    description = book.get('description', '')
    
    # Get cover image if available
    cover_image = assets.get('cover_image')
    cover_html = ''
    if cover_image:
        # Handle base64 encoded image
        if isinstance(cover_image, str) and cover_image.startswith('data:image'):
            cover_html = f'<img src="{cover_image}" alt="{title} Cover" style="max-width: 300px; width: 100%; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">'
    else:
        cover_html = '<div style="width: 300px; height: 450px; background-color: #eee; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #999;">Cover Image Placeholder</div>'
    
    # Get review quotes
    review_quotes = assets.get('review_quotes', [])
    reviews_html = ''
    if review_quotes:
        reviews_html = '<div style="margin-top: 40px;"><h3 style="color: #333;">Praise for the Book</h3><div style="display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px;">'
        for quote in review_quotes[:3]:
            if isinstance(quote, dict):
                reviews_html += f"""
                <div style="flex: 1; min-width: 250px; padding: 20px; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
                    <p style="font-style: italic; color: #555;">"{quote.get('text', '')}"</p>
                    <p style="font-weight: bold; margin-top: 10px;">— {quote.get('reviewer', 'Reviewer')}</p>
                </div>
                """
        reviews_html += '</div></div>'
    
    html = f"""
    <!-- BOOK SHOWCASE SECTION - Copy and paste this where you want your book featured -->
    <section class="book-showcase" style="padding: 60px 20px; background-color: white;">
        <div style="max-width: 1200px; margin: 0 auto;">
            <h2 style="font-size: 2.5em; text-align: center; margin-bottom: 40px; color: #333;">My Latest Book</h2>
            
            <div style="display: flex; flex-wrap: wrap; gap: 40px; align-items: center; justify-content: center;">
                <!-- Book Cover -->
                <div style="flex: 1; min-width: 300px; text-align: center;">
                    {cover_html}
                </div>
                
                <!-- Book Info -->
                <div style="flex: 2; min-width: 300px;">
                    <h3 style="font-size: 2em; color: #333; margin-bottom: 10px;">{title}</h3>
                    <p style="color: #666; font-size: 1.1em; margin-bottom: 15px;">{genre}</p>
                    <p style="line-height: 1.8; color: #555; margin-bottom: 25px;">
                        {description}
                    </p>
                    
                    <!-- Purchase Links -->
                    <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 30px;">
                        <a href="#" style="padding: 12px 30px; background-color: #crimson; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Amazon</a>
                        <a href="#" style="padding: 12px 30px; background-color: #2e4057; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Barnes & Noble</a>
                        <a href="#" style="padding: 12px 30px; background-color: #446688; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Goodreads</a>
                    </div>
                </div>
            </div>
            
            {reviews_html}
        </div>
    </section>
    <!-- END BOOK SHOWCASE SECTION -->
    """
    
    return html

def generate_advocates_section(data):
    """Generate HTML for advocates showcase section"""
    
    advocates = data.get('advocates', [])
    
    if not advocates:
        return "<!-- No advocates data available -->"
    
    html = """
    <!-- ADVOCATES SHOWCASE SECTION - Copy and paste this where you want to showcase your supporters -->
    <section class="advocates-showcase" style="padding: 60px 20px; background-color: #f5f5f5;">
        <div style="max-width: 1200px; margin: 0 auto;">
            <h2 style="font-size: 2.5em; text-align: center; margin-bottom: 20px; color: #333;">Our Amazing Advocates</h2>
            <p style="text-align: center; color: #666; margin-bottom: 40px;">The readers and influencers who support our work</p>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 30px;">
    """
    
    for advocate in advocates:
        username = advocate.get('username', 'Reader')
        platform = advocate.get('platform', 'Social Media')
        followers = advocate.get('follower_count', 0)
        engagement = advocate.get('engagement_rate', 'High')
        testimonial = advocate.get('testimonial', f'Amazing book! Can\'t wait for more from this author.')
        
        # Format follower count
        if followers >= 1000000:
            follower_text = f"{followers/1000000:.1f}M followers"
        elif followers >= 1000:
            follower_text = f"{followers/1000:.1f}K followers"
        else:
            follower_text = f"{followers} followers"
        
        html += f"""
                <div style="background-color: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <div style="width: 50px; height: 50px; background-color: #crimson; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; margin-right: 15px;">
                            {username[0].upper()}
                        </div>
                        <div>
                            <h4 style="margin: 0; color: #333;">@{username}</h4>
                            <p style="margin: 5px 0 0; color: #666; font-size: 0.9em;">{platform} • {follower_text}</p>
                        </div>
                    </div>
                    <p style="color: #555; line-height: 1.6; font-style: italic;">"{testimonial}"</p>
                    <p style="color: #crimson; margin-top: 10px; font-weight: bold;">Engagement: {engagement}</p>
                </div>
        """
    
    html += """
            </div>
        </div>
    </section>
    <!-- END ADVOCATES SHOWCASE SECTION -->
    """
    
    return html

def generate_marketing_assets_section(data):
    """Generate HTML for marketing assets section"""
    
    assets = data.get('marketing_assets', {})
    endorsements = assets.get('endorsements', [])
    
    html = """
    <!-- MARKETING ASSETS SECTION - Copy and paste this for your press/promotion page -->
    <section class="marketing-assets" style="padding: 60px 20px; background-color: white;">
        <div style="max-width: 1000px; margin: 0 auto;">
            <h2 style="font-size: 2.5em; text-align: center; margin-bottom: 40px; color: #333;">Press & Marketing</h2>
    """
    
    # Endorsements section
    if endorsements:
        html += """
            <div style="margin-bottom: 50px;">
                <h3 style="color: #333; margin-bottom: 30px;">Endorsements</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 30px;">
        """
        
        for endorsement in endorsements[:3]:
            if isinstance(endorsement, dict):
                html += f"""
                    <div style="flex: 1; min-width: 250px; padding: 30px; background-color: #f9f9f9; border-left: 4px solid crimson;">
                        <p style="font-size: 1.2em; font-style: italic; color: #444;">"{endorsement.get('quote', '')}"</p>
                        <p style="font-weight: bold; margin-top: 15px;">— {endorsement.get('author', '')}</p>
                        <p style="color: #666;">{endorsement.get('title', '')}</p>
                    </div>
                """
        
        html += """
                </div>
            </div>
        """
    
    # Press kit link
    if assets.get('press_kit'):
        html += """
            <div style="text-align: center; margin-top: 40px; padding: 30px; background-color: #f0f0f0; border-radius: 10px;">
                <h3 style="color: #333; margin-bottom: 20px;">Download Press Kit</h3>
                <a href="#" style="display: inline-block; padding: 15px 40px; background-color: #333; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Download Press Materials</a>
            </div>
        """
    
    html += """
        </div>
    </section>
    <!-- END MARKETING ASSETS SECTION -->
    """
    
    return html

def generate_complete_html_package(data):
    """Generate a complete HTML package with all sections"""
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Author Website Content</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; margin: 0; padding: 0; }
        .section-divider { text-align: center; padding: 20px; background-color: #f0f0f0; color: #999; font-size: 0.9em; }
    </style>
</head>
<body>
    <!-- ========== AUTHOR WEBSITE CONTENT ========== -->
    <!-- Copy and paste the sections you want into your website builder -->
    
    <div class="section-divider">--- AUTHOR BIO SECTION (START) ---</div>
"""
    
    html += generate_author_bio_section(data)
    
    html += """
    <div class="section-divider">--- AUTHOR BIO SECTION (END) ---</div>
    
    <div class="section-divider">--- BOOK SHOWCASE SECTION (START) ---</div>
"""
    
    html += generate_book_showcase_section(data)
    
    html += """
    <div class="section-divider">--- BOOK SHOWCASE SECTION (END) ---</div>
    """
    
    if data.get('advocates'):
        html += """
    <div class="section-divider">--- ADVOCATES SHOWCASE SECTION (START) ---</div>
    """
        html += generate_advocates_section(data)
        html += """
    <div class="section-divider">--- ADVOCATES SHOWCASE SECTION (END) ---</div>
    """
    
    if data.get('marketing_assets'):
        html += """
    <div class="section-divider">--- MARKETING ASSETS SECTION (START) ---</div>
    """
        html += generate_marketing_assets_section(data)
        html += """
    <div class="section-divider">--- MARKETING ASSETS SECTION (END) ---</div>
    """
    
    html += """
    <!-- ========== END AUTHOR WEBSITE CONTENT ========== -->
</body>
</html>
"""
    
    return html

# ============================================================================
# MAIN UI FUNCTION
# ============================================================================
def show_website_builder():
    """Main function to display the website builder"""
    
    st.title("🌐 Author Website Content Generator")
    st.markdown("""
    ### Generate HTML sections you can copy-paste into any website builder
    
    This tool pulls data from:
    - ✅ Your user profile (name, bio, social media)
    - ✅ Book Analyzer results (title, description, genre)
    - ✅ Marketing Assets (cover images, endorsements, reviews)
    - ✅ Saved Advocates (ARC readers and influencers)
    """)
    
    # Pull all data
    with st.spinner("Loading your data..."):
        author_data = get_complete_author_data()
    
    # Show data summary
    with st.expander("📊 View Data Being Used", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Profile Data:**")
            profile = author_data.get('profile', {})
            st.markdown(f"- Name: {profile.get('name', 'Not found')}")
            st.markdown(f"- Email: {profile.get('email', 'Not found')}")
            st.markdown(f"- Bio: {'✅' if profile.get('bio') else '❌'}")
        
        with col2:
            st.markdown("**Book Data:**")
            book = author_data.get('book_analysis', {})
            st.markdown(f"- Title: {book.get('title', 'Not found')}")
            st.markdown(f"- Genre: {book.get('genre', 'Not found')}")
            st.markdown(f"- Description: {'✅' if book.get('description') else '❌'}")
        
        with col3:
            st.markdown("**Other Assets:**")
            st.markdown(f"- Advocates: {len(author_data.get('advocates', []))}")
            st.markdown(f"- Reviews: {len(author_data.get('marketing_assets', {}).get('review_quotes', []))}")
            st.markdown(f"- Endorsements: {len(author_data.get('marketing_assets', {}).get('endorsements', []))}")
    
    st.markdown("---")
    
    # Section selector
    st.subheader("1. Choose sections to generate")
    
    col1, col2 = st.columns(2)
    
    with col1:
        include_bio = st.checkbox("Author Bio Section", value=True)
        include_book = st.checkbox("Book Showcase Section", value=True)
        include_advocates = st.checkbox("Advocates Showcase Section", value=bool(author_data.get('advocates')))
    
    with col2:
        include_marketing = st.checkbox("Marketing/Press Section", value=bool(author_data.get('marketing_assets', {}).get('endorsements')))
        include_all = st.checkbox("Generate Complete HTML Package", value=False)
    
    st.markdown("---")
    
    # Generate button
    if st.button("🎨 Generate HTML Sections", type="primary"):
        if include_all:
            # Generate complete HTML package
            html_content = generate_complete_html_package(author_data)
            
            st.subheader("2. Your Complete HTML Package")
            st.markdown("Copy the entire code below and paste it into your website builder:")
            
            # Display HTML in a code block
            st.code(html_content, language="html")
            
            # Download button
            b64 = base64.b64encode(html_content.encode()).decode()
            href = f'<a href="data:text/html;base64,{b64}" download="author_website_content.html">📥 Download HTML File</a>'
            st.markdown(href, unsafe_allow_html=True)
            
        else:
            # Generate individual sections
            st.subheader("2. Copy & Paste These Sections")
            
            if include_bio:
                st.markdown("### Author Bio Section")
                st.code(generate_author_bio_section(author_data), language="html")
                st.markdown("---")
            
            if include_book:
                st.markdown("### Book Showcase Section")
                st.code(generate_book_showcase_section(author_data), language="html")
                st.markdown("---")
            
            if include_advocates and author_data.get('advocates'):
                st.markdown("### Advocates Showcase Section")
                st.code(generate_advocates_section(author_data), language="html")
                st.markdown("---")
            
            if include_marketing:
                st.markdown("### Marketing/Press Section")
                st.code(generate_marketing_assets_section(author_data), language="html")
        
        st.success("✅ Sections generated! Copy the HTML code and paste into your website builder.")
    
    st.markdown("---")
    st.markdown("""
    ### 📋 Instructions:
    1. Click "Generate HTML Sections" above
    2. Copy the HTML code for the sections you want
    3. In your website builder (Soloist.ai, WordPress, Wix, etc.), find the "HTML" or "Embed Code" element
    4. Paste the code
    5. Customize colors and links as needed
    
    **Note:** You'll need to manually add your purchase links and replace placeholder images.
    """)

# For backward compatibility
def render_questionnaire():
    show_website_builder()

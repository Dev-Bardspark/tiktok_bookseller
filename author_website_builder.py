"""
Complete Author Marketing Website Generator
Harvests ALL available data and builds a professional author site
"""

import streamlit as st
import json
import base64
from datetime import datetime
import os

# ============================================================================
# MAIN FUNCTION (this is what BardSpark calls)
# ============================================================================
def show_website_builder():
    """Main entry point for the website builder"""
    show_website_questionnaire()

def load_all_author_data():
    """Load ALL data from every source"""
    data = {
        "author": {
            "name": "",
            "pen_name": "",
            "email": "",
            "website": "",
            "bio": "",
            "location": "",
            "awards": []
        },
        "books": [],
        "social": {
            "profiles": {},
            "newsletter": {},
            "advocates": []
        },
        "content": {
            "media": [],
            "blog": {},
            "bonus": {},
            "analytics": {}
        }
    }
    
    # 1. Load from current_user
    if st.session_state.get('current_user'):
        user = st.session_state.current_user
        data["author"]["name"] = user.get('name', '')
        data["author"]["pen_name"] = user.get('pen_name', '')
        data["author"]["email"] = user.get('email', '')
        data["author"]["website"] = user.get('website', '')
        data["author"]["bio"] = user.get('bio', '')
        data["author"]["location"] = user.get('location', '')
        data["social"]["profiles"] = user.get('social_media', {})
    
    # 2. Load from analysis_result
    if st.session_state.get('analysis_result'):
        analysis = st.session_state.analysis_result
        if isinstance(analysis, dict):
            book_info = analysis.get('book_info', {})
            if isinstance(book_info, str):
                try:
                    book_info = json.loads(book_info)
                except:
                    book_info = {}
            
            if book_info.get('title'):
                data["books"] = [{
                    "title": book_info.get('title', ''),
                    "genre": book_info.get('genre', ''),
                    "description": book_info.get('description', ''),
                    "series": "",
                    "series_order": 1,
                    "cover": None,
                    "links": {}
                }]
    
    # 3. Load from marketing assets
    marketing_data = {}
    if st.session_state.get('generated_assets'):
        marketing_data = st.session_state.generated_assets
    elif st.session_state.get('edited_assets'):
        marketing_data = st.session_state.edited_assets
    
    if marketing_data:
        # Get blurbs for book description
        if marketing_data.get('blurbs') and data["books"]:
            blurbs = marketing_data['blurbs']
            if blurbs and isinstance(blurbs, list) and len(blurbs) > 0:
                data["books"][0]["description"] = blurbs[0]
        
        # Get media mentions
        media_mentions = []
        if marketing_data.get('podcast_pitches'):
            for pitch in marketing_data['podcast_pitches']:
                if isinstance(pitch, dict) and 'podcast_ideas' in pitch:
                    for idea in pitch.get('podcast_ideas', [])[:3]:
                        media_mentions.append(f"🎙️ {idea}")
        data["content"]["media"] = media_mentions
    
    # 4. Load from saved_readers
    if st.session_state.get('saved_readers'):
        saved = st.session_state.saved_readers
        advocates = []
        for adv in saved[:6]:
            if isinstance(adv, dict):
                advocates.append({
                    "username": adv.get('username', ''),
                    "platform": adv.get('platform', ''),
                    "follower_count": adv.get('follower_count', 0),
                    "testimonial": adv.get('testimonial', '')
                })
        data["social"]["advocates"] = advocates
    
    return data

def show_website_questionnaire():
    st.title("📚 Complete Author Website Generator")
    st.markdown("### Build your professional author site in 5 minutes")
    
    # Show logged in user
    if st.session_state.get('current_user'):
        user = st.session_state.current_user
        st.sidebar.success(f"👤 Logged in as: {user.get('name', 'User')}")
    
    # ============================================================================
    # LOAD ALL DATA FIRST (before any UI elements)
    # ============================================================================
    if 'website_data' not in st.session_state:
        with st.spinner("Loading your data..."):
            st.session_state.website_data = load_all_author_data()
    
    # Progress tracking
    if 'website_step' not in st.session_state:
        st.session_state.website_step = 1
    
    # Step indicators
    col1, col2, col3, col4, col5 = st.columns(5)
    steps = ["Profile", "Books", "Social", "Content", "Generate"]
    for i, (col, step) in enumerate(zip([col1, col2, col3, col4, col5], steps)):
        with col:
            if st.session_state.website_step > i + 1:
                st.markdown(f"✅ **{step}**")
            elif st.session_state.website_step == i + 1:
                st.markdown(f"📝 **{step}**")
            else:
                st.markdown(f"⚪ {step}")
    
    st.markdown("---")
    
    # Show what was auto-filled
    with st.expander("📊 Auto-Filled Data", expanded=False):
        data = st.session_state.website_data
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**👤 Author:**")
            st.markdown(f"- Name: {data['author']['name'] or '❌'}")
            st.markdown(f"- Email: {data['author']['email'] or '❌'}")
            st.markdown(f"- Bio: {'✅' if data['author']['bio'] else '❌'}")
        with col2:
            st.markdown("**📚 Books:**")
            st.markdown(f"- Count: {len(data['books'])}")
            if data['books']:
                st.markdown(f"- Title: {data['books'][0]['title'] or '❌'}")
        with col3:
            st.markdown("**👥 Advocates:**")
            st.markdown(f"- Count: {len(data['social']['advocates'])}")
    
    # ============================================================================
    # STEP 1: AUTHOR PROFILE
    # ============================================================================
    if st.session_state.website_step == 1:
        st.header("Step 1: Author Profile")
        
        data = st.session_state.website_data
        author = data['author']
        
        # Show success if data was loaded
        if author['name']:
            st.success(f"✅ Auto-filled profile for: {author['name']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            author_name = st.text_input(
                "Your Full Name *",
                value=author['name'],
                key="profile_name"
            )
            
            pen_name = st.text_input(
                "Pen Name (if different)",
                value=author['pen_name'],
                key="profile_pen"
            )
            
            author_email = st.text_input(
                "Email for Contact *",
                value=author['email'],
                key="profile_email"
            )
            
            author_website = st.text_input(
                "Your Website (if any)",
                value=author['website'],
                key="profile_website"
            )
        
        with col2:
            author_photo = st.file_uploader(
                "Author Photo (professional headshot)",
                type=['jpg', 'png', 'webp'],
                key="profile_photo"
            )
            
            author_bio = st.text_area(
                "Author Bio *",
                value=author['bio'],
                height=150,
                key="profile_bio"
            )
            
            location = st.text_input(
                "Location",
                value=author['location'],
                placeholder="City, Country",
                key="profile_location"
            )
        
        st.markdown("---")
        
        # Awards
        st.subheader("🏆 Awards & Recognition")
        num_awards = st.number_input(
            "How many awards/mentions?", 
            0, 10, 
            len(author['awards']),
            key="num_awards"
        )
        
        awards_list = []
        for i in range(int(num_awards)):
            col1, col2 = st.columns(2)
            with col1:
                award_name = st.text_input(
                    f"Award {i+1} Name", 
                    key=f"award_name_{i}"
                )
            with col2:
                award_year = st.text_input(
                    f"Year", 
                    key=f"award_year_{i}"
                )
            if award_name:
                awards_list.append(f"{award_name} ({award_year})" if award_year else award_name)
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col3:
            if st.button("Next: Your Books →", type="primary", key="next_to_books"):
                st.session_state.website_data["author"] = {
                    "name": author_name,
                    "pen_name": pen_name,
                    "email": author_email,
                    "website": author_website,
                    "photo": author_photo,
                    "bio": author_bio,
                    "location": location,
                    "awards": awards_list
                }
                st.session_state.website_step = 2
                st.rerun()
    
    # ============================================================================
    # STEP 2: BOOKS & SERIES
    # ============================================================================
    elif st.session_state.website_step == 2:
        st.header("Step 2: Your Books")
        
        data = st.session_state.website_data
        existing_books = data['books']
        
        if existing_books:
            st.success(f"📖 Auto-filled {len(existing_books)} book(s)")
        
        num_books = st.number_input(
            "How many books do you have?", 
            1, 20, 
            value=max(1, len(existing_books)),
            key="num_books"
        )
        
        books = []
        for i in range(int(num_books)):
            with st.expander(f"📖 Book {i+1}", expanded=i==0):
                existing = existing_books[i] if i < len(existing_books) else {}
                
                col1, col2 = st.columns(2)
                
                with col1:
                    title = st.text_input(
                        "Book Title *", 
                        value=existing.get('title', ''),
                        key=f"book_title_{i}"
                    )
                    
                    genre = st.text_input(
                        "Genre *",
                        value=existing.get('genre', ''),
                        key=f"book_genre_{i}"
                    )
                    
                    series = st.text_input(
                        "Series Name",
                        value=existing.get('series', ''),
                        key=f"book_series_{i}"
                    )
                    
                    series_order = st.number_input(
                        "Book # in Series", 1, 20,
                        value=existing.get('series_order', 1),
                        key=f"book_order_{i}"
                    )
                
                with col2:
                    cover = st.file_uploader(
                        "Book Cover Image",
                        type=['jpg', 'png', 'webp'],
                        key=f"book_cover_{i}"
                    )
                    
                    description = st.text_area(
                        "Book Description *",
                        value=existing.get('description', ''),
                        height=150,
                        key=f"book_desc_{i}"
                    )
                    
                    buy_links = st.text_area(
                        "Purchase Links (one per line)",
                        value="\n".join(existing.get('links', {}).values()) if existing.get('links') else '',
                        key=f"book_links_{i}"
                    )
                    
                    # Parse links
                    links = {}
                    if buy_links:
                        for link in buy_links.split('\n'):
                            link = link.strip()
                            if not link:
                                continue
                            if 'amazon' in link.lower():
                                links['amazon'] = link
                            elif 'goodreads' in link.lower():
                                links['goodreads'] = link
                            elif 'apple' in link.lower():
                                links['apple'] = link
                            elif 'barnes' in link.lower():
                                links['barnes'] = link
                
                if title:
                    books.append({
                        "title": title,
                        "genre": genre,
                        "description": description,
                        "series": series,
                        "series_order": series_order,
                        "cover": cover,
                        "links": links
                    })
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back", key="back_to_profile"):
                st.session_state.website_step = 1
                st.rerun()
        with col3:
            if st.button("Next: Social Media →", type="primary", key="next_to_social"):
                st.session_state.website_data["books"] = books
                st.session_state.website_step = 3
                st.rerun()
    
    # ============================================================================
    # STEP 3: SOCIAL MEDIA & COMMUNITY
    # ============================================================================
    elif st.session_state.website_step == 3:
        st.header("Step 3: Social Media & Community")
        
        data = st.session_state.website_data
        social = data['social']
        profiles = social['profiles']
        advocates = social['advocates']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📱 Your Profiles")
            twitter = st.text_input("Twitter/X", value=profiles.get('twitter', ''), key="social_twitter")
            instagram = st.text_input("Instagram", value=profiles.get('instagram', ''), key="social_instagram")
            facebook = st.text_input("Facebook", value=profiles.get('facebook', ''), key="social_facebook")
            tiktok = st.text_input("TikTok", value=profiles.get('tiktok', ''), key="social_tiktok")
        
        with col2:
            st.subheader("📚 Reading Platforms")
            goodreads = st.text_input("Goodreads", value=profiles.get('goodreads', ''), key="social_goodreads")
            amazon = st.text_input("Amazon Author Page", value=profiles.get('amazon', ''), key="social_amazon")
        
        st.markdown("---")
        
        # Newsletter
        st.subheader("📧 Email Newsletter")
        newsletter = social['newsletter']
        
        has_newsletter = st.checkbox(
            "I have a newsletter", 
            value=newsletter.get('has', False),
            key="has_newsletter"
        )
        
        if has_newsletter:
            col1, col2 = st.columns(2)
            with col1:
                newsletter_link = st.text_input(
                    "Signup link",
                    value=newsletter.get('link', ''),
                    key="newsletter_link"
                )
            with col2:
                lead_magnet = st.text_input(
                    "Freebie for subscribers",
                    value=newsletter.get('lead_magnet', ''),
                    key="lead_magnet"
                )
        
        st.markdown("---")
        
        # Advocates
        st.subheader("⭐ Your Advocates")
        
        if advocates:
            st.success(f"👥 Auto-filled {len(advocates)} advocates")
            show_advocates = st.checkbox("Show advocates on site", value=True, key="show_advocates")
            
            advocates_to_show = []
            if show_advocates:
                for idx, adv in enumerate(advocates):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"**@{adv.get('username')}**")
                    with col2:
                        st.write(f"{adv.get('platform')} • {adv.get('follower_count')} followers")
                    with col3:
                        include = st.checkbox("Include", value=True, key=f"adv_include_{idx}")
                        if include:
                            advocates_to_show.append(adv)
        else:
            st.info("No advocates found")
            advocates_to_show = []
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back", key="back_to_books"):
                st.session_state.website_step = 2
                st.rerun()
        with col3:
            if st.button("Next: Content →", type="primary", key="next_to_content"):
                st.session_state.website_data["social"] = {
                    "profiles": {
                        "twitter": twitter,
                        "instagram": instagram,
                        "facebook": facebook,
                        "tiktok": tiktok,
                        "goodreads": goodreads,
                        "amazon": amazon
                    },
                    "newsletter": {
                        "has": has_newsletter,
                        "link": newsletter_link if has_newsletter else None,
                        "lead_magnet": lead_magnet if has_newsletter else None
                    },
                    "advocates": advocates_to_show
                }
                st.session_state.website_step = 4
                st.rerun()
    
    # ============================================================================
    # STEP 4: ADDITIONAL CONTENT
    # ============================================================================
    elif st.session_state.website_step == 4:
        st.header("Step 4: Additional Content")
        
        data = st.session_state.website_data
        content = data['content']
        
        if content['media']:
            st.success(f"🎙️ Auto-filled {len(content['media'])} media mentions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎤 Media & Press")
            media_text = "\n".join(content['media'])
            media_mentions = st.text_area(
                "Media mentions (one per line)",
                value=media_text,
                height=100,
                key="media_mentions"
            )
        
        with col2:
            st.subheader("📊 Analytics")
            ga = st.text_input("Google Analytics ID", value=content['analytics'].get('ga', ''), key="ga_id")
            fb = st.text_input("Facebook Pixel ID", value=content['analytics'].get('pixel', ''), key="fb_pixel")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back", key="back_to_social"):
                st.session_state.website_step = 3
                st.rerun()
        with col3:
            if st.button("Next: Design →", type="primary", key="next_to_design"):
                st.session_state.website_data["content"] = {
                    "media": [m.strip() for m in media_mentions.split('\n') if m.strip()],
                    "analytics": {
                        "ga": ga,
                        "pixel": fb
                    }
                }
                st.session_state.website_step = 5
                st.rerun()
    
    # ============================================================================
    # STEP 5: DESIGN & GENERATE
    # ============================================================================
    elif st.session_state.website_step == 5:
        st.header("Step 5: Design & Generate")
        
        col1, col2 = st.columns(2)
        
        with col1:
            color_theme = st.selectbox(
                "Color Scheme",
                ["Professional & Clean", "Warm & Inviting", "Dark & Mysterious"],
                key="color_theme"
            )
        
        with col2:
            font_style = st.selectbox(
                "Font Style",
                ["Classic Serif", "Modern Sans", "Elegant"],
                key="font_style"
            )
        
        st.markdown("---")
        
        # Summary
        data = st.session_state.website_data
        st.markdown("### 📋 Ready to Generate")
        st.markdown(f"**Author:** {data['author']['name']}")
        st.markdown(f"**Books:** {len(data['books'])}")
        st.markdown(f"**Advocates:** {len(data['social']['advocates'])}")
        
        if st.button("🚀 GENERATE WEBSITE", type="primary", key="generate"):
            with st.spinner("Building your website..."):
                html = generate_website_html(data)
                if html:
                    st.success("✅ Website generated!")
                    st.components.v1.html(html, height=600, scrolling=True)
                    
                    # Download
                    b64 = base64.b64encode(html.encode()).decode()
                    filename = f"{data['author']['name'].replace(' ', '_')}_website.html"
                    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display:inline-block;padding:12px 30px;background:#667eea;color:white;text-decoration:none;border-radius:5px;">📥 Download HTML</a>'
                    st.markdown(href, unsafe_allow_html=True)

def generate_website_html(data):
    """Generate the complete HTML website"""
    author = data['author']
    books = data['books']
    social = data['social']
    content = data['content']
    
    author_name = author.get('pen_name') or author.get('name', 'Author')
    
    # Build books HTML
    books_html = ""
    for i, book in enumerate(books):
        books_html += f"""
        <div class="book-card">
            <div class="book-cover">
                <div class="cover-placeholder">{book.get('title', 'Book Cover')}</div>
            </div>
            <div class="book-info">
                <h3>{book.get('title')}</h3>
                <p class="genre">{book.get('genre')}</p>
                <p class="description">{book.get('description')}</p>
                <div class="links">
                    {f'<a href="{book["links"].get("amazon", "#")}" class="button amazon">Amazon</a>' if book.get('links', {}).get('amazon') else ''}
                    {f'<a href="{book["links"].get("goodreads", "#")}" class="button goodreads">Goodreads</a>' if book.get('links', {}).get('goodreads') else ''}
                </div>
            </div>
        </div>
        """
    
    # Build social HTML
    social_html = ""
    for platform, url in social['profiles'].items():
        if url:
            social_html += f'<a href="{url}" class="social-link">{platform.title()}</a>'
    
    # Build advocates HTML
    advocates_html = ""
    for adv in social['advocates']:
        advocates_html += f"""
        <div class="advocate-card">
            <div class="avatar">{adv.get('username', 'R')[0].upper()}</div>
            <h4>@{adv.get('username')}</h4>
            <p class="testimonial">"{adv.get('testimonial', '')}"</p>
        </div>
        """
    
    # Build media HTML
    media_html = ""
    for mention in content['media']:
        media_html += f'<li>{mention}</li>'
    
    # Simple HTML template
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{author_name} - Author Website</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 20px; }}
        nav {{ background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.1); position: sticky; top: 0; }}
        .nav-container {{ display: flex; justify-content: space-between; align-items: center; padding: 1rem 20px; max-width: 1200px; margin: 0 auto; }}
        .logo {{ font-size: 1.5rem; font-weight: bold; color: #667eea; text-decoration: none; }}
        .nav-links a {{ margin-left: 2rem; text-decoration: none; color: #333; }}
        .hero {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 100px 20px; text-align: center; }}
        .hero h1 {{ font-size: 3rem; margin-bottom: 1rem; }}
        .section {{ padding: 80px 20px; }}
        .section-title {{ text-align: center; font-size: 2.5rem; margin-bottom: 50px; }}
        .section-title:after {{ content: ''; display: block; width: 100px; height: 3px; background: #667eea; margin: 20px auto; }}
        .book-card {{ display: flex; gap: 40px; margin-bottom: 60px; padding: 30px; background: white; border-radius: 10px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
        .book-cover {{ flex: 1; min-width: 200px; }}
        .cover-placeholder {{ width: 200px; height: 300px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; padding: 20px; }}
        .book-info {{ flex: 2; }}
        .button {{ display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px; }}
        .advocates-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 30px; margin-top: 40px; }}
        .advocate-card {{ background: white; padding: 30px; border-radius: 10px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .avatar {{ width: 80px; height: 80px; background: #667eea; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 2rem; margin: 0 auto 20px; }}
        .social-links {{ display: flex; justify-content: center; gap: 20px; margin: 40px 0; }}
        .social-link {{ padding: 10px 20px; background: #f0f0f0; color: #333; text-decoration: none; border-radius: 5px; }}
        footer {{ background: #333; color: white; text-align: center; padding: 40px; }}
        @media (max-width: 768px) {{ .book-card {{ flex-direction: column; }} .nav-links {{ display: none; }} }}
    </style>
</head>
<body>
    <nav>
        <div class="nav-container">
            <a href="#" class="logo">{author_name}</a>
            <div class="nav-links">
                <a href="#home">Home</a>
                <a href="#books">Books</a>
                <a href="#about">About</a>
                <a href="#contact">Contact</a>
            </div>
        </div>
    </nav>
    
    <section id="home" class="hero">
        <h1>{author_name}</h1>
        <p>{author.get('bio', '')[:150]}...</p>
        <a href="#books" class="button" style="margin-top: 30px;">Explore Books</a>
    </section>
    
    <section id="books" class="section">
        <div class="container">
            <h2 class="section-title">My Books</h2>
            {books_html if books_html else '<p style="text-align:center;">No books added yet.</p>'}
        </div>
    </section>
    
    {f'''
    <section class="section" style="background:#f8f9fa;">
        <div class="container">
            <h2 class="section-title">Readers Love My Books</h2>
            <div class="advocates-grid">{advocates_html}</div>
        </div>
    </section>
    ''' if advocates_html else ''}
    
    <section id="about" class="section">
        <div class="container">
            <h2 class="section-title">About {author_name}</h2>
            <p style="max-width:800px; margin:0 auto;">{author.get('bio', '')}</p>
            {f'<ul style="margin-top:30px;">{media_html}</ul>' if media_html else ''}
        </div>
    </section>
    
    <section id="contact" class="section" style="background:#f8f9fa;">
        <div class="container">
            <h2 class="section-title">Connect</h2>
            <div class="social-links">{social_html}</div>
            <p style="text-align:center;">Email: <a href="mailto:{author.get('email', '')}">{author.get('email', '')}</a></p>
        </div>
    </section>
    
    <footer>
        <p>© {datetime.now().year} {author_name}</p>
    </footer>
</body>
</html>"""
    
    return html

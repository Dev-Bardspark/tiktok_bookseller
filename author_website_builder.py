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

def show_website_questionnaire():
    st.title("📚 Complete Author Website Generator")
    st.markdown("### Build your professional author site in 5 minutes")
    
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
    
    # Initialize session state for all data
    if 'website_data' not in st.session_state:
        st.session_state.website_data = {
            "author": {},
            "books": [],
            "social": {},
            "content": {},
            "design": {}
        }
    
    # ============================================================================
    # AUTO-FILL from existing data
    # ============================================================================
    # Pre-fill author data from profile
    if st.session_state.get('current_user') and not st.session_state.website_data.get('author'):
        user = st.session_state.current_user
        st.session_state.website_data["author"] = {
            "name": user.get('name', ''),
            "pen_name": user.get('pen_name', ''),
            "email": user.get('email', ''),
            "website": user.get('website', ''),
            "bio": user.get('bio', ''),
            "photo": None,
            "location": user.get('location', ''),
            "awards": []
        }
    
    # Pre-fill book data from analyzer
    if st.session_state.get('analysis_result') and not st.session_state.website_data.get('books'):
        analysis = st.session_state.analysis_result
        if isinstance(analysis, dict):
            book_info = analysis.get('book_info', {})
            if isinstance(book_info, str):
                try:
                    book_info = json.loads(book_info)
                except:
                    book_info = {}
            
            if book_info.get('title'):
                st.session_state.website_data["books"] = [{
                    "title": book_info.get('title', ''),
                    "genre": book_info.get('genre', ''),
                    "description": book_info.get('description', ''),
                    "series": "",
                    "series_order": 1,
                    "cover": None,
                    "links": {}
                }]
    
    # Pre-fill social data from profile
    if st.session_state.get('current_user') and not st.session_state.website_data.get('social'):
        user = st.session_state.current_user
        st.session_state.website_data["social"] = {
            "profiles": user.get('social_media', {}),
            "newsletter": {},
            "advocates": []
        }
    
    # ============================================================================
    # STEP 1: AUTHOR PROFILE
    # ============================================================================
    if st.session_state.website_step == 1:
        st.header("Step 1: Author Profile")
        
        # Get existing data
        existing = st.session_state.website_data.get("author", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            author_name = st.text_input(
                "Your Full Name *",
                value=existing.get('name', '')
            )
            
            pen_name = st.text_input(
                "Pen Name (if different)",
                value=existing.get('pen_name', '')
            )
            
            author_email = st.text_input(
                "Email for Contact *",
                value=existing.get('email', '')
            )
            
            author_website = st.text_input(
                "Your Website (if any)",
                value=existing.get('website', '')
            )
        
        with col2:
            author_photo = st.file_uploader(
                "Author Photo (professional headshot)",
                type=['jpg', 'png', 'webp']
            )
            
            author_bio = st.text_area(
                "Author Bio *",
                value=existing.get('bio', ''),
                height=150,
                help="Tell readers about yourself, your journey, and why you write"
            )
            
            location = st.text_input(
                "Location",
                value=existing.get('location', ''),
                placeholder="City, Country"
            )
        
        st.markdown("---")
        
        # Awards & Recognition
        st.subheader("🏆 Awards & Recognition")
        st.caption("Add any awards, nominations, or media mentions")
        
        awards = existing.get('awards', [])
        num_awards = st.number_input("How many awards/mentions?", 0, 10, len(awards))
        
        awards_list = []
        for i in range(int(num_awards)):
            col1, col2 = st.columns(2)
            with col1:
                award_name = st.text_input(
                    f"Award {i+1} Name", 
                    value=awards[i].split(' (')[0] if i < len(awards) else '',
                    key=f"award_name_{i}"
                )
            with col2:
                award_year = st.text_input(
                    f"Year", 
                    value=awards[i].split('(')[-1].replace(')', '') if i < len(awards) and '(' in awards[i] else '',
                    key=f"award_year_{i}"
                )
            if award_name:
                awards_list.append(f"{award_name} ({award_year})" if award_year else award_name)
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col3:
            if st.button("Next: Your Books →", type="primary", use_container_width=True):
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
        
        # Get existing books
        existing_books = st.session_state.website_data.get('books', [])
        
        # How many books?
        num_books = st.number_input(
            "How many books do you have?", 
            1, 20, 
            value=max(1, len(existing_books)),
            key="num_books_input"
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
                        "Series Name (if part of series)",
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
                        placeholder="https://amazon.com/dp/...\nhttps://goodreads.com/...\nhttps://apple.com/...",
                        key=f"book_links_{i}"
                    )
                    
                    # Parse buy links
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
                            elif 'apple' in link.lower() or 'books' in link.lower():
                                links['apple'] = link
                            elif 'barnes' in link.lower() or 'noble' in link.lower():
                                links['barnes'] = link
                            else:
                                links['other'] = link
                
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
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back", use_container_width=True):
                st.session_state.website_step = 1
                st.rerun()
        with col3:
            if st.button("Next: Social Media →", type="primary", use_container_width=True):
                st.session_state.website_data["books"] = books
                st.session_state.website_step = 3
                st.rerun()
    
    # ============================================================================
    # STEP 3: SOCIAL MEDIA & COMMUNITY
    # ============================================================================
    elif st.session_state.website_step == 3:
        st.header("Step 3: Social Media & Community")
        
        # Get existing social data
        existing_social = st.session_state.website_data.get('social', {})
        existing_profiles = existing_social.get('profiles', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📱 Your Profiles")
            twitter = st.text_input("Twitter/X", value=existing_profiles.get('twitter', ''), key="social_twitter")
            instagram = st.text_input("Instagram", value=existing_profiles.get('instagram', ''), key="social_instagram")
            facebook = st.text_input("Facebook", value=existing_profiles.get('facebook', ''), key="social_facebook")
            tiktok = st.text_input("TikTok", value=existing_profiles.get('tiktok', ''), key="social_tiktok")
            threads = st.text_input("Threads", value=existing_profiles.get('threads', ''), key="social_threads")
        
        with col2:
            st.subheader("📚 Reading Platforms")
            goodreads = st.text_input("Goodreads Author Page", value=existing_profiles.get('goodreads', ''), key="social_goodreads")
            bookbub = st.text_input("BookBub", value=existing_profiles.get('bookbub', ''), key="social_bookbub")
            amazon_author = st.text_input("Amazon Author Page", value=existing_profiles.get('amazon', ''), key="social_amazon")
        
        st.markdown("---")
        
        # Newsletter Setup
        st.subheader("📧 Email Newsletter")
        st.caption("This is your most important marketing tool!")
        
        existing_newsletter = existing_social.get('newsletter', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            has_newsletter = st.checkbox(
                "I have a newsletter", 
                value=existing_newsletter.get('has', False),
                key="has_newsletter"
            )
            if has_newsletter:
                newsletter_service = st.selectbox(
                    "Which service do you use?",
                    ["Mailchimp", "ConvertKit", "MailerLite", "Substack", "Other"],
                    index=["Mailchimp", "ConvertKit", "MailerLite", "Substack", "Other"].index(existing_newsletter.get('service', 'Mailchimp')) 
                        if existing_newsletter.get('service') in ["Mailchimp", "ConvertKit", "MailerLite", "Substack", "Other"] else 0,
                    key="newsletter_service"
                )
                newsletter_link = st.text_input(
                    "Newsletter signup link",
                    value=existing_newsletter.get('link', ''),
                    key="newsletter_link"
                )
        
        with col2:
            lead_magnet = st.text_input(
                "Lead Magnet (Freebie for subscribers)",
                value=existing_newsletter.get('lead_magnet', ''),
                placeholder="e.g., Free prequel chapter, character art, short story",
                key="lead_magnet"
            )
            
            lead_magnet_description = st.text_area(
                "Describe your freebie",
                value=existing_newsletter.get('lead_magnet_desc', ''),
                placeholder="What will they get? Why should they subscribe?",
                height=100,
                key="lead_magnet_desc"
            )
        
        st.markdown("---")
        
        # Advocates/ARC Readers
        st.subheader("⭐ Your Advocates")
        st.caption("Showcase your biggest fans and ARC readers")
        
        # Pull from saved advocates
        saved_advocates = st.session_state.get('saved_readers', [])
        existing_advocates = existing_social.get('advocates', [])
        advocates_to_show = []
        
        if saved_advocates:
            st.success(f"You have {len(saved_advocates)} saved advocates!")
            show_advocates = st.checkbox(
                "Showcase advocates on my site", 
                value=bool(existing_advocates),
                key="show_advocates_main"
            )
            
            if show_advocates:
                for idx, adv in enumerate(saved_advocates[:6]):
                    username = adv.get('username', f'reader_{idx}')
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**@{username}** - {adv.get('platform', '')} ({adv.get('follower_count', 0)} followers)")
                    with col2:
                        # Check if this advocate was previously selected
                        was_selected = any(a.get('username') == username for a in existing_advocates)
                        include = st.checkbox(
                            "Include", 
                            value=was_selected,
                            key=f"adv_include_{idx}_{username}"
                        )
                        if include:
                            advocates_to_show.append(adv)
        else:
            st.info("No advocates saved yet. You can add them manually:")
            num_advocates = st.number_input(
                "How many advocates to showcase?", 
                0, 10, 
                len(existing_advocates),
                key="num_advocates_manual"
            )
            for i in range(int(num_advocates)):
                existing = existing_advocates[i] if i < len(existing_advocates) else {}
                col1, col2 = st.columns(2)
                with col1:
                    username = st.text_input(
                        f"Username {i+1}", 
                        value=existing.get('username', ''),
                        key=f"manual_adv_user_{i}"
                    )
                with col2:
                    testimonial = st.text_input(
                        f"Testimonial {i+1}", 
                        value=existing.get('testimonial', ''),
                        key=f"manual_adv_test_{i}"
                    )
                if username:
                    advocates_to_show.append({
                        "username": username,
                        "testimonial": testimonial
                    })
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back", use_container_width=True):
                st.session_state.website_step = 2
                st.rerun()
        with col3:
            if st.button("Next: Content →", type="primary", use_container_width=True):
                st.session_state.website_data["social"] = {
                    "profiles": {
                        "twitter": twitter,
                        "instagram": instagram,
                        "facebook": facebook,
                        "tiktok": tiktok,
                        "threads": threads,
                        "goodreads": goodreads,
                        "bookbub": bookbub,
                        "amazon": amazon_author
                    },
                    "newsletter": {
                        "has": has_newsletter,
                        "service": newsletter_service if has_newsletter else None,
                        "link": newsletter_link if has_newsletter else None,
                        "lead_magnet": lead_magnet,
                        "lead_magnet_desc": lead_magnet_description
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
        
        existing_content = st.session_state.website_data.get('content', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 Blog/News")
            has_blog = st.checkbox(
                "I want a blog/news section",
                value=existing_content.get('blog', {}).get('has', False),
                key="has_blog"
            )
            if has_blog:
                blog_feed = st.text_area(
                    "Paste your blog RSS feed or latest posts",
                    value=existing_content.get('blog', {}).get('feed', ''),
                    placeholder="Post 1: Title and link\nPost 2: Title and link",
                    height=100,
                    key="blog_feed"
                )
        
        with col2:
            st.subheader("🎤 Media & Press")
            existing_media = existing_content.get('media', [])
            media_mentions = st.text_area(
                "Media mentions (one per line)",
                value="\n".join(existing_media),
                placeholder="Interview on Author Spotlight Podcast\nFeatured in Writer's Digest\nGuest post on JaneFriedman.com",
                height=100,
                key="media_mentions"
            )
        
        st.markdown("---")
        
        st.subheader("📖 Bonus Content")
        
        existing_bonus = existing_content.get('bonus', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            has_sample = st.checkbox(
                "Offer a free sample chapter",
                value=bool(existing_bonus.get('sample')),
                key="has_sample"
            )
            if has_sample:
                sample_file = st.file_uploader(
                    "Upload sample chapter (PDF)",
                    type=['pdf'],
                    key="sample_file"
                )
        
        with col2:
            has_playlist = st.checkbox(
                "Create a book playlist",
                value=bool(existing_bonus.get('playlist_link')),
                key="has_playlist"
            )
            if has_playlist:
                playlist_link = st.text_input(
                    "Spotify/Apple Music link",
                    value=existing_bonus.get('playlist_link', ''),
                    key="playlist_link"
                )
                playlist_description = st.text_area(
                    "Describe the vibe",
                    value=existing_bonus.get('playlist_desc', ''),
                    height=80,
                    key="playlist_desc"
                )
        
        st.markdown("---")
        
        st.subheader("📊 Analytics & Tracking")
        
        existing_analytics = existing_content.get('analytics', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            google_analytics = st.text_input(
                "Google Analytics ID",
                value=existing_analytics.get('ga', ''),
                placeholder="G-XXXXXXXXXX",
                help="Optional: Add for visitor tracking",
                key="google_analytics"
            )
        
        with col2:
            facebook_pixel = st.text_input(
                "Facebook Pixel ID",
                value=existing_analytics.get('pixel', ''),
                placeholder="XXXXXXXXXX",
                help="Optional: For ad retargeting",
                key="facebook_pixel"
            )
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("← Back", use_container_width=True):
                st.session_state.website_step = 3
                st.rerun()
        with col3:
            if st.button("Next: Design →", type="primary", use_container_width=True):
                st.session_state.website_data["content"] = {
                    "blog": {
                        "has": has_blog,
                        "feed": blog_feed if has_blog else None
                    },
                    "media": [m.strip() for m in media_mentions.split('\n') if m.strip()] if media_mentions else [],
                    "bonus": {
                        "sample": sample_file if 'sample_file' in locals() else None,
                        "playlist_link": playlist_link if 'playlist_link' in locals() else None,
                        "playlist_desc": playlist_description if 'playlist_description' in locals() else None
                    },
                    "analytics": {
                        "ga": google_analytics,
                        "pixel": facebook_pixel
                    }
                }
                st.session_state.website_step = 5
                st.rerun()
    
    # ============================================================================
    # STEP 5: DESIGN & GENERATE
    # ============================================================================
    elif st.session_state.website_step == 5:
        st.header("Step 5: Design & Generate")
        
        existing_design = st.session_state.website_data.get('design', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎨 Color Scheme")
            color_theme = st.selectbox(
                "Choose your vibe",
                ["Professional & Clean", "Warm & Inviting", "Dark & Mysterious", 
                 "Bright & Energetic", "Elegant & Sophisticated", "Minimalist"],
                index=["Professional & Clean", "Warm & Inviting", "Dark & Mysterious", 
                       "Bright & Energetic", "Elegant & Sophisticated", "Minimalist"].index(existing_design.get('color_theme', 'Professional & Clean'))
                    if existing_design.get('color_theme') in ["Professional & Clean", "Warm & Inviting", "Dark & Mysterious", 
                       "Bright & Energetic", "Elegant & Sophisticated", "Minimalist"] else 0,
                key="color_theme"
            )
            
            font_style = st.selectbox(
                "Font Style",
                ["Classic Serif (traditional)", "Modern Sans (clean)", 
                 "Elegant (sophisticated)", "Bold (statement)"],
                index=["Classic Serif (traditional)", "Modern Sans (clean)", 
                       "Elegant (sophisticated)", "Bold (statement)"].index(existing_design.get('font_style', 'Modern Sans (clean)'))
                    if existing_design.get('font_style') in ["Classic Serif (traditional)", "Modern Sans (clean)", 
                       "Elegant (sophisticated)", "Bold (statement)"] else 1,
                key="font_style"
            )
        
        with col2:
            st.subheader("📱 Layout")
            layout = st.selectbox(
                "Page structure",
                ["Single page (recommended)", "Multi-page with menu"],
                index=0 if existing_design.get('layout', 'Single page (recommended)') == "Single page (recommended)" else 1,
                key="layout"
            )
            
            show_sidebar = st.checkbox(
                "Show author sidebar", 
                value=existing_design.get('sidebar', True),
                key="show_sidebar"
            )
            
            social_icons = st.checkbox(
                "Show social media icons in header", 
                value=existing_design.get('social_header', True),
                key="social_icons"
            )
        
        st.markdown("---")
        
        # Summary of all collected data
        with st.expander("📋 Review Your Data", expanded=True):
            data = st.session_state.website_data
            
            st.markdown(f"**Author:** {data['author'].get('name', 'Not set')}")
            st.markdown(f"**Books:** {len(data['books'])}")
            st.markdown(f"**Social Profiles:** {len([v for v in data['social'].get('profiles', {}).values() if v])}")
            st.markdown(f"**Advocates:** {len(data['social'].get('advocates', []))}")
        
        st.markdown("---")
        
        # Generate button
        if st.button("🚀 GENERATE COMPLETE WEBSITE", type="primary", use_container_width=True):
            with st.spinner("Building your professional author website..."):
                html = generate_complete_author_site(st.session_state.website_data, {
                    "color_theme": color_theme,
                    "font_style": font_style,
                    "layout": layout,
                    "sidebar": show_sidebar,
                    "social_header": social_icons
                })
                
                if html:
                    st.success("✅ Your website is ready!")
                    
                    # Preview
                    st.components.v1.html(html, height=600, scrolling=True)
                    
                    # Download
                    b64 = base64.b64encode(html.encode()).decode()
                    filename = f"{data['author'].get('name', 'author').replace(' ', '_')}_website.html"
                    
                    st.markdown(f'''
                    <a href="data:text/html;base64,{b64}" download="{filename}" 
                       style="display: inline-block; padding: 15px 40px; 
                              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: white; text-decoration: none; border-radius: 50px; 
                              font-weight: bold; font-size: 1.2rem; margin-top: 20px;">
                        📥 Download Complete Website
                    </a>
                    ''', unsafe_allow_html=True)
                    
                    st.info("""
                    **Next Steps:**
                    1. Download the HTML file
                    2. Go to [app.netlify.com/drop](https://app.netlify.com/drop)
                    3. Drag and drop the file
                    4. Your site is live!
                    """)


def generate_complete_author_site(data, design):
    """Generate complete HTML with ALL marketing features"""
    
    author = data.get('author', {})
    books = data.get('books', [])
    social = data.get('social', {})
    content = data.get('content', {})
    
    # Build author name for display
    author_name = author.get('pen_name') or author.get('name', 'Your Name')
    
    # Build book HTML
    books_html = ""
    for i, book in enumerate(books):
        books_html += f"""
        <div class="book-card" id="book-{i}">
            <div class="book-cover">
                <div class="cover-placeholder">{book.get('title', 'Book Cover')}</div>
            </div>
            <div class="book-info">
                <h3>{book.get('title')}</h3>
                <p class="book-genre">{book.get('genre')}</p>
                <p class="book-description">{book.get('description')}</p>
                <div class="purchase-links">
                    {f'<a href="{book["links"].get("amazon", "#")}" class="purchase-link amazon">Amazon</a>' if book.get('links', {}).get('amazon') else ''}
                    {f'<a href="{book["links"].get("goodreads", "#")}" class="purchase-link goodreads">Goodreads</a>' if book.get('links', {}).get('goodreads') else ''}
                    {f'<a href="{book["links"].get("apple", "#")}" class="purchase-link">Apple Books</a>' if book.get('links', {}).get('apple') else ''}
                    {f'<a href="{book["links"].get("barnes", "#")}" class="purchase-link">Barnes & Noble</a>' if book.get('links', {}).get('barnes') else ''}
                </div>
            </div>
        </div>
        """
    
    # Build social links HTML
    social_html = ""
    profiles = social.get('profiles', {})
    for platform, url in profiles.items():
        if url:
            social_html += f'<a href="{url}" class="social-link" target="_blank">{platform.title()}</a>'
    
    # Build advocates HTML
    advocates_html = ""
    for adv in social.get('advocates', []):
        advocates_html += f"""
        <div class="advocate-card">
            <div class="advocate-avatar">{adv.get('username', 'R')[0].upper()}</div>
            <h4>@{adv.get('username')}</h4>
            <p class="testimonial">"{adv.get('testimonial', '')}"</p>
        </div>
        """
    
    # Build awards HTML
    awards_html = ""
    for award in author.get('awards', []):
        awards_html += f'<span class="award-badge">🏆 {award}</span>'
    
    # Build media mentions HTML
    media_html = ""
    for mention in content.get('media', []):
        media_html += f'<li class="media-item">📰 {mention}</li>'
    
    # Build newsletter HTML
    newsletter = social.get('newsletter', {})
    newsletter_html = ""
    if newsletter.get('has'):
        lead_magnet = newsletter.get('lead_magnet')
        newsletter_html = f"""
        <div class="newsletter-section">
            <h3>Join the Newsletter</h3>
            {f'<p class="lead-magnet">✨ <strong>Free:</strong> {lead_magnet}</p>' if lead_magnet else ''}
            <p class="newsletter-desc">{newsletter.get('lead_magnet_desc', 'Get exclusive content and updates!')}</p>
            <form class="newsletter-form" action="{newsletter.get('link', '#')}" method="post">
                <input type="email" placeholder="Your email address" required>
                <button type="submit">Subscribe</button>
            </form>
        </div>
        """
    
    # Complete HTML template
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{author_name} - Author Website</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        /* Navigation */
        nav {{
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .nav-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .logo {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #667eea;
            text-decoration: none;
        }}
        
        .nav-links a {{
            margin-left: 2rem;
            text-decoration: none;
            color: #333;
        }}
        
        .nav-links a:hover {{
            color: #667eea;
        }}
        
        {f'.social-header {{ display: flex; gap: 10px; }}' if design.get('social_header') else ''}
        
        /* Hero Section */
        .hero {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 100px 20px;
            text-align: center;
        }}
        
        .hero-content {{
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .hero h1 {{
            font-size: 3.5rem;
            margin-bottom: 1rem;
        }}
        
        .hero h2 {{
            font-size: 1.5rem;
            font-weight: 300;
            margin-bottom: 2rem;
            opacity: 0.9;
        }}
        
        .hero .author-photo {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            margin: 20px auto;
            background: #ddd;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            color: white;
            background: rgba(255,255,255,0.2);
        }}
        
        .hero .cta-button {{
            display: inline-block;
            padding: 15px 40px;
            background: white;
            color: #764ba2;
            text-decoration: none;
            border-radius: 50px;
            font-weight: bold;
            font-size: 1.2rem;
            transition: transform 0.3s;
        }}
        
        .hero .cta-button:hover {{
            transform: translateY(-3px);
        }}
        
        /* Awards Section */
        .awards-bar {{
            background: #f8f9fa;
            padding: 20px 0;
            text-align: center;
        }}
        
        .award-badge {{
            display: inline-block;
            margin: 0 10px;
            padding: 5px 15px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        /* Books Section */
        .books-section {{
            padding: 80px 20px;
        }}
        
        .section-title {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 50px;
        }}
        
        .section-title:after {{
            content: '';
            display: block;
            width: 100px;
            height: 3px;
            background: #667eea;
            margin: 20px auto;
        }}
        
        .book-card {{
            display: flex;
            gap: 40px;
            margin-bottom: 60px;
            padding: 30px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        
        .book-cover {{
            flex: 1;
            min-width: 250px;
        }}
        
        .cover-placeholder {{
            width: 250px;
            height: 375px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2rem;
            text-align: center;
            padding: 20px;
        }}
        
        .book-info {{
            flex: 2;
        }}
        
        .book-info h3 {{
            font-size: 2rem;
            margin-bottom: 10px;
        }}
        
        .book-genre {{
            color: #666;
            margin-bottom: 20px;
        }}
        
        .book-description {{
            margin-bottom: 30px;
            line-height: 1.8;
        }}
        
        .purchase-links {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        
        .purchase-link {{
            padding: 10px 25px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .purchase-link.amazon {{
            background: #232f3e;
        }}
        
        .purchase-link.goodreads {{
            background: #372213;
        }}
        
        /* Advocates Section */
        .advocates-section {{
            background: #f8f9fa;
            padding: 80px 20px;
        }}
        
        .advocates-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }}
        
        .advocate-card {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        }}
        
        .advocate-avatar {{
            width: 80px;
            height: 80px;
            background: #667eea;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2rem;
            margin: 0 auto 20px;
        }}
        
        .advocate-card h4 {{
            margin-bottom: 15px;
        }}
        
        .testimonial {{
            font-style: italic;
            color: #555;
        }}
        
        /* Newsletter Section */
        .newsletter-section {{
            background: white;
            padding: 60px;
            text-align: center;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            margin: 40px 0;
        }}
        
        .lead-magnet {{
            font-size: 1.2rem;
            color: #667eea;
            margin: 20px 0;
        }}
        
        .newsletter-form {{
            display: flex;
            max-width: 500px;
            margin: 30px auto 0;
            gap: 10px;
        }}
        
        .newsletter-form input {{
            flex: 1;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 1rem;
        }}
        
        .newsletter-form button {{
            padding: 15px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
        }}
        
        /* About Section */
        .about-section {{
            padding: 80px 20px;
        }}
        
        .about-content {{
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .bio {{
            font-size: 1.2rem;
            line-height: 1.8;
            margin-bottom: 30px;
        }}
        
        .media-list {{
            list-style: none;
            margin: 30px 0;
        }}
        
        .media-item {{
            margin: 10px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        
        /* Contact Section */
        .contact-section {{
            background: #f8f9fa;
            padding: 80px 20px;
        }}
        
        .social-links {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin: 40px 0;
        }}
        
        .social-link {{
            padding: 10px 25px;
            background: white;
            color: #333;
            text-decoration: none;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .social-link:hover {{
            background: #667eea;
            color: white;
        }}
        
        /* Footer */
        footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 40px 20px;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .nav-links {{
                display: none;
            }}
            
            .hero h1 {{
                font-size: 2.5rem;
            }}
            
            .book-card {{
                flex-direction: column;
                text-align: center;
            }}
            
            .cover-placeholder {{
                margin: 0 auto;
            }}
            
            .purchase-links {{
                justify-content: center;
            }}
            
            .newsletter-form {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav>
        <div class="nav-container">
            <a href="#" class="logo">{author_name}</a>
            <div class="nav-links">
                <a href="#home">Home</a>
                <a href="#books">Books</a>
                <a href="#about">About</a>
                <a href="#contact">Contact</a>
            </div>
            {f'<div class="social-header">{social_html}</div>' if design.get('social_header') and social_html else ''}
        </div>
    </nav>
    
    <!-- Hero Section -->
    <section id="home" class="hero">
        <div class="hero-content">
            <div class="author-photo">📸</div>
            <h1>{author_name}</h1>
            <h2>{author.get('bio', '')[:150]}...</h2>
            <a href="#books" class="cta-button">Explore My Books</a>
        </div>
    </section>
    
    <!-- Awards Bar -->
    {f'''
    <div class="awards-bar">
        <div class="container">
            {awards_html}
        </div>
    </div>
    ''' if awards_html else ''}
    
    <!-- Books Section -->
    <section id="books" class="books-section">
        <div class="container">
            <h2 class="section-title">My Books</h2>
            {books_html}
        </div>
    </section>
    
    <!-- Advocates Section -->
    {f'''
    <section class="advocates-section">
        <div class="container">
            <h2 class="section-title">Readers Love My Books</h2>
            <div class="advocates-grid">
                {advocates_html}
            </div>
        </div>
    </section>
    ''' if advocates_html else ''}
    
    <!-- Newsletter Section -->
    {f'''
    <section class="container">
        {newsletter_html}
    </section>
    ''' if newsletter_html else ''}
    
    <!-- About Section -->
    <section id="about" class="about-section">
        <div class="container">
            <h2 class="section-title">About {author_name}</h2>
            <div class="about-content">
                <p class="bio">{author.get('bio', '')}</p>
                
                {f'''
                <h3>Media Mentions</h3>
                <ul class="media-list">
                    {media_html}
                </ul>
                ''' if media_html else ''}
            </div>
        </div>
    </section>
    
    <!-- Contact Section -->
    <section id="contact" class="contact-section">
        <div class="container">
            <h2 class="section-title">Connect With Me</h2>
            <div class="social-links">
                {social_html}
            </div>
            <p style="text-align: center;">
                Email: <a href="mailto:{author.get('email', '')}">{author.get('email', '')}</a>
            </p>
        </div>
    </section>
    
    <!-- Footer -->
    <footer>
        <div class="container">
            <p>© {datetime.now().year} {author_name}. All rights reserved.</p>
        </div>
    </footer>
    
    <!-- Analytics -->
    {f'''
    <script async src="https://www.googletagmanager.com/gtag/js?id={content.get('analytics', {}).get('ga')}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{content.get('analytics', {}).get('ga')}');
    </script>
    ''' if content.get('analytics', {}).get('ga') else ''}
</body>
</html>"""
    
    return html

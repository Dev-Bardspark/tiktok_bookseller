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
    
    # ============================================================================
    # AGGRESSIVE AUTO-FILL from EVERY source
    # ============================================================================
    
    # Initialize session state if needed
    if 'website_data' not in st.session_state:
        st.session_state.website_data = {
            "author": {},
            "books": [],
            "social": {},
            "content": {},
            "design": {}
        }
    
    # Show logged in user
    if st.session_state.get('current_user'):
        user = st.session_state.current_user
        st.sidebar.success(f"👤 Logged in as: {user.get('name', 'User')}")
        
        # ========================================================================
        # 1. PULL FROM USER PROFILE (ALWAYS)
        # ========================================================================
        current_author = st.session_state.website_data.get("author", {})
        
        # Update with EVERY field from user profile
        if user.get('name') and not current_author.get('name'):
            current_author['name'] = user.get('name')
        if user.get('pen_name') and not current_author.get('pen_name'):
            current_author['pen_name'] = user.get('pen_name')
        if user.get('email') and not current_author.get('email'):
            current_author['email'] = user.get('email')
        if user.get('website') and not current_author.get('website'):
            current_author['website'] = user.get('website')
        if user.get('bio') and not current_author.get('bio'):
            current_author['bio'] = user.get('bio')
        if user.get('location') and not current_author.get('location'):
            current_author['location'] = user.get('location')
        
        st.session_state.website_data["author"] = current_author
        
        # ========================================================================
        # 2. PULL SOCIAL MEDIA FROM USER PROFILE
        # ========================================================================
        if user.get('social_media') and not st.session_state.website_data.get('social'):
            st.session_state.website_data["social"] = {
                "profiles": user.get('social_media', {}),
                "newsletter": {},
                "advocates": []
            }
    
    # ========================================================================
    # 3. PULL FROM BOOK ANALYZER
    # ========================================================================
    if st.session_state.get('analysis_result'):
        analysis = st.session_state.analysis_result
        if isinstance(analysis, dict):
            # Get book info
            book_info = analysis.get('book_info', {})
            if isinstance(book_info, str):
                try:
                    book_info = json.loads(book_info)
                except:
                    book_info = {}
            
            # Get marketability data
            marketability = analysis.get('marketability', {})
            if isinstance(marketability, str):
                try:
                    marketability = json.loads(marketability)
                except:
                    marketability = {}
            
            # Create book entry if we have a title and no books yet
            if book_info.get('title') and not st.session_state.website_data.get('books'):
                st.session_state.website_data["books"] = [{
                    "title": book_info.get('title', ''),
                    "genre": book_info.get('genre', ''),
                    "description": book_info.get('description', '') or marketability.get('overall_assessment', ''),
                    "series": "",
                    "series_order": 1,
                    "cover": None,
                    "links": {}
                }]
    
    # ========================================================================
    # 4. PULL FROM MARKETING ASSETS (EVERYTHING!)
    # ========================================================================
    marketing_data = {}
    
    # Check session state for marketing assets
    if st.session_state.get('generated_assets'):
        marketing_data = st.session_state.generated_assets
    elif st.session_state.get('edited_assets'):
        marketing_data = st.session_state.edited_assets
    
    if marketing_data:
        # Update books with blurbs if available
        if marketing_data.get('blurbs') and st.session_state.website_data.get('books'):
            books = st.session_state.website_data['books']
            if books and isinstance(marketing_data['blurbs'], list) and marketing_data['blurbs']:
                # Use the first blurb as enhanced description
                books[0]['description'] = marketing_data['blurbs'][0]
        
        # Pull reviews for content section
        content = st.session_state.website_data.get('content', {})
        
        # Get reviews from press kit
        reviews = []
        if marketing_data.get('press_kit_options'):
            for kit in marketing_data['press_kit_options']:
                if isinstance(kit, dict) and 'author_qanda' in kit:
                    for qa in kit.get('author_qanda', []):
                        if isinstance(qa, dict) and 'answer' in qa:
                            reviews.append(qa['answer'][:150] + '...')
        
        # Get media mentions
        media_mentions = []
        if marketing_data.get('podcast_pitches'):
            for pitch in marketing_data['podcast_pitches']:
                if isinstance(pitch, dict) and 'podcast_ideas' in pitch:
                    for idea in pitch.get('podcast_ideas', []):
                        media_mentions.append(f"🎙️ {idea}")
        
        # Update content
        content['media'] = list(set(media_mentions[:5]))  # Unique, max 5
        st.session_state.website_data['content'] = content
    
    # ========================================================================
    # 5. PULL FROM SAVED ADVOCATES
    # ========================================================================
    if st.session_state.get('saved_readers'):
        saved_advocates = st.session_state.saved_readers
        social = st.session_state.website_data.get('social', {})
        
        if saved_advocates and isinstance(saved_advocates, list):
            # Take top 6 advocates
            advocates = []
            for adv in saved_advocates[:6]:
                if isinstance(adv, dict):
                    advocates.append({
                        "username": adv.get('username', ''),
                        "platform": adv.get('platform', ''),
                        "follower_count": adv.get('follower_count', 0),
                        "testimonial": adv.get('testimonial', '')
                    })
            social['advocates'] = advocates
            st.session_state.website_data['social'] = social
    
    # ========================================================================
    # 6. PULL FROM DATABASE (if needed)
    # ========================================================================
    # You could add database queries here for additional saved data
    
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
    
    # Show data summary (what we found)
    with st.expander("📊 Auto-Filled Data Summary", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**👤 Author:**")
            author = st.session_state.website_data.get('author', {})
            st.markdown(f"- Name: {author.get('name', '❌')}")
            st.markdown(f"- Email: {author.get('email', '❌')}")
            st.markdown(f"- Bio: {'✅' if author.get('bio') else '❌'}")
        
        with col2:
            st.markdown("**📚 Books:**")
            books = st.session_state.website_data.get('books', [])
            st.markdown(f"- Count: {len(books)}")
            if books:
                st.markdown(f"- Title: {books[0].get('title', '❌')}")
        
        with col3:
            st.markdown("**👥 Advocates:**")
            social = st.session_state.website_data.get('social', {})
            advocates = social.get('advocates', [])
            st.markdown(f"- Count: {len(advocates)}")
            st.markdown(f"- Marketing Assets: {'✅' if marketing_data else '❌'}")
    
    # ============================================================================
    # STEP 1: AUTHOR PROFILE
    # ============================================================================
    if st.session_state.website_step == 1:
        st.header("Step 1: Author Profile")
        
        # Get existing data (now should be fully filled)
        existing = st.session_state.website_data.get("author", {})
        
        # Show what we auto-filled
        if existing.get('name'):
            st.success(f"✅ Auto-filled profile for: {existing.get('name')}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            author_name = st.text_input(
                "Your Full Name *",
                value=existing.get('name', ''),
                key="author_name_input"
            )
            
            pen_name = st.text_input(
                "Pen Name (if different)",
                value=existing.get('pen_name', ''),
                key="pen_name_input"
            )
            
            author_email = st.text_input(
                "Email for Contact *",
                value=existing.get('email', ''),
                key="author_email_input"
            )
            
            author_website = st.text_input(
                "Your Website (if any)",
                value=existing.get('website', ''),
                key="author_website_input"
            )
        
        with col2:
            author_photo = st.file_uploader(
                "Author Photo (professional headshot)",
                type=['jpg', 'png', 'webp'],
                key="author_photo_input"
            )
            
            author_bio = st.text_area(
                "Author Bio *",
                value=existing.get('bio', ''),
                height=150,
                help="Tell readers about yourself, your journey, and why you write",
                key="author_bio_input"
            )
            
            location = st.text_input(
                "Location",
                value=existing.get('location', ''),
                placeholder="City, Country",
                key="author_location_input"
            )
        
        st.markdown("---")
        
        # Awards & Recognition
        st.subheader("🏆 Awards & Recognition")
        st.caption("Add any awards, nominations, or media mentions")
        
        awards = existing.get('awards', [])
        num_awards = st.number_input(
            "How many awards/mentions?", 
            0, 10, 
            len(awards),
            key="num_awards"
        )
        
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
        
        # Show what we auto-filled
        if existing_books:
            st.success(f"📖 Auto-filled {len(existing_books)} book(s) from your analysis")
            if marketing_data:
                st.success(f"🎨 Enhanced with marketing assets")
        
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
        existing_advocates = existing_social.get('advocates', [])
        
        # Show what we auto-filled
        if existing_profiles:
            st.success(f"📱 Auto-filled social media profiles")
        if existing_advocates:
            st.success(f"👥 Auto-filled {len(existing_advocates)} advocates")
        
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
        
        # Show if we auto-filled anything
        if existing_content.get('media'):
            st.success(f"🎙️ Auto-filled {len(existing_content.get('media', []))} media mentions from marketing assets")
        
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
            if data['books']:
                st.markdown(f"**Main Book:** {data['books'][0].get('title', '')}")
            st.markdown(f"**Social Profiles:** {len([v for v in data['social'].get('profiles', {}).values() if v])}")
            st.markdown(f"**Advocates:** {len(data['social'].get('advocates', []))}")
            st.markdown(f"**Media Mentions:** {len(data['content'].get('media', []))}")
        
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
    
    # Complete HTML template (keeping your existing HTML here - it's long so I'll truncate for this message)
    # [Your existing HTML generation code stays exactly the same]
    
    return html

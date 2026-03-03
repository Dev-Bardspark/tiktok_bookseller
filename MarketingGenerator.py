# MarketingGenerator.py
import streamlit as st
from openai import OpenAI
import json
import time
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

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

def save_marketing_asset_to_db(user_id, book_title, asset_type, asset_data):
    """Save marketing asset to database"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_marketing_assets 
            (user_id, asset_type, asset_name, asset_data, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            asset_type,
            f"{book_title} - {asset_type}",
            json.dumps(asset_data),
            datetime.now(),
            datetime.now()
        ))
        
        asset_id = cur.fetchone()[0]
        conn.commit()
        return asset_id
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def load_user_marketing_assets(user_id):
    """Load user's saved marketing assets"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_marketing_assets 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        assets = cur.fetchall()
        return [dict(a) for a in assets]
    except Exception as e:
        st.error(f"Error loading assets: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def extract_book_info(book_data):
    """Safely extract book info from potentially nested data"""
    if not book_data:
        return {}
    
    # Try different possible structures
    if 'book_info' in book_data:
        book_info = book_data['book_info']
        # Handle case where book_info might contain another book_info
        if isinstance(book_info, dict) and 'book_info' in book_info:
            return book_info['book_info']
        return book_info
    elif 'analysis_result' in book_data:
        # Handle database stored format
        analysis = book_data['analysis_result']
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except:
                pass
        if isinstance(analysis, dict) and 'book_info' in analysis:
            return extract_book_info(analysis)
    
    return book_data

def safe_get_str(dictionary, key, default=""):
    """Safely get string value from dictionary"""
    if dictionary and isinstance(dictionary, dict):
        value = dictionary.get(key, default)
        return str(value) if value is not None else default
    return default

def safe_get_list(dictionary, key, default=None):
    """Safely get list value from dictionary"""
    if default is None:
        default = []
    if dictionary and isinstance(dictionary, dict):
        value = dictionary.get(key, default)
        return value if isinstance(value, list) else default
    return default

def show_generator():
    """Generate marketing assets from saved analysis"""
    
    # ============================================================================
    # LOGIN CHECK
    # ============================================================================
    if not st.session_state.get('authenticated', False):
        st.warning("🔒 Please login to access the Marketing Asset Generator")
        if st.button("Go to Login", use_container_width=True):
            st.session_state.page = "🏠 Dashboard"
            st.rerun()
        return
    
    # Initialize session state
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    
    if 'loaded_analysis' not in st.session_state:
        st.session_state.loaded_analysis = None
    
    if 'generated_assets' not in st.session_state:
        st.session_state.generated_assets = None
    
    if 'edited_assets' not in st.session_state:
        st.session_state.edited_assets = None
    
    # Header
    st.title("🎨 Marketing Asset Generator")
    st.markdown("Generate LOTS of marketing options for every platform")
    st.markdown("---")
    
    # API Key input
    if not st.session_state.openai_api_key:
        with st.container():
            st.markdown("### 🔑 OpenAI API Key")
            api_key = st.text_input("Enter your API key", type="password", key="api_key_input")
            if api_key:
                st.session_state.openai_api_key = api_key
                st.rerun()
        return
    
    # ============================================================================
    # BOOK SELECTION SECTION
    # ============================================================================
    
    st.markdown("### 📚 Select a Book to Market")
    
    # Check for saved analyses in session and database
    if 'analysis_library' not in st.session_state:
        st.session_state.analysis_library = {}
    
    # Also check database for saved analyses
    db_analyses = []
    if st.session_state.get('authenticated', False):
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT * FROM user_book_analyses 
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (st.session_state.get('user_id', 1),))
                db_analyses = cur.fetchall()
                cur.close()
                conn.close()
            except Exception as e:
                st.error(f"Error loading saved analyses: {e}")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Combine session and database analyses for selection
        all_books = []
        
        # Add session analyses
        for filename, data in st.session_state.analysis_library.items():
            book_info = extract_book_info(data)
            title = book_info.get('title', 'Unknown')
            all_books.append({
                'display': f"📁 {title} (Session)",
                'source': 'session',
                'data': data,
                'filename': filename
            })
        
        # Add database analyses
        for analysis in db_analyses:
            analysis_data = analysis
            title = analysis.get('book_title', 'Unknown')
            all_books.append({
                'display': f"💾 {title} (Saved)",
                'source': 'database',
                'data': analysis_data,
                'analysis_id': analysis.get('id')
            })
        
        if all_books:
            book_options = [b['display'] for b in all_books]
            selected_index = st.selectbox(
                "Choose a book to market:",
                range(len(book_options)),
                format_func=lambda x: book_options[x],
                key="book_selector"
            )
            selected_book = all_books[selected_index]
        else:
            st.info("No books found. Please analyze a book first in the Book Analyzer.")
            if st.button("📖 Go to Book Analyzer"):
                st.session_state.page = "📖 Book Analyzer"
                st.rerun()
            return
    
    with col2:
        if all_books and st.button("📂 Load Book", type="primary", use_container_width=True):
            st.session_state.loaded_analysis = selected_book['data']
            st.session_state.generated_assets = None
            st.session_state.edited_assets = None
            st.rerun()
    
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # ============================================================================
    # ASSET GENERATION SECTION
    # ============================================================================
    
    if st.session_state.loaded_analysis:
        st.markdown("---")
        
        # Show loaded book info
        book_info = extract_book_info(st.session_state.loaded_analysis)
        title = book_info.get('title', 'Unknown')
        genre = book_info.get('genre', 'Unknown')
        
        st.success(f"✅ Loaded: **{title}** ({genre})")
        
        # Generate button
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🎬 GENERATE MARKETING ASSETS", type="primary", use_container_width=True):
                with st.spinner("Generating LOTS of assets... (60-90 seconds)"):
                    try:
                        client = OpenAI(api_key=st.session_state.openai_api_key)
                        assets = generate_marketing_assets(client, st.session_state.loaded_analysis)
                        
                        if assets:
                            st.session_state.generated_assets = assets
                            st.session_state.edited_assets = assets.copy()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Generation failed: {str(e)}")
        
        with col2:
            if st.session_state.generated_assets:
                if st.button("🔄 Regenerate Assets", use_container_width=True):
                    st.session_state.generated_assets = None
                    st.session_state.edited_assets = None
                    st.rerun()
        
        with col3:
            if st.session_state.edited_assets:
                # Save to database button
                if st.session_state.get('authenticated', False):
                    if st.button("💾 Save to My Library", use_container_width=True):
                        saved_count = 0
                        # Save each asset type separately
                        for asset_type in ['blurbs', 'tiktok_scripts', 'youtube_scripts', 'instagram_posts', 
                                          'instagram_reels', 'amazon_options', 'facebook_ads', 'email_sequences', 
                                          'press_kit_options', 'pinterest_options', 'goodreads_options', 
                                          'podcast_pitches', 'launch_timeline']:
                            if asset_type in st.session_state.edited_assets:
                                asset_data = {asset_type: st.session_state.edited_assets[asset_type]}
                                asset_id = save_marketing_asset_to_db(
                                    st.session_state.get('user_id', 1),
                                    title,
                                    asset_type,
                                    asset_data
                                )
                                if asset_id:
                                    saved_count += 1
                        if saved_count > 0:
                            st.success(f"✅ {saved_count} assets saved to your library!")
                        else:
                            st.error("Failed to save assets")
                
                # Export button
                export_data = json.dumps(st.session_state.edited_assets, indent=2)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{title.replace(' ', '_')}_assets_{timestamp}.json"
                
                st.download_button(
                    "📥 Export Assets",
                    export_data,
                    filename,
                    "application/json",
                    use_container_width=True
                )
        
        # ============================================================================
        # ASSET DISPLAY AND EDITING SECTION
        # ============================================================================
        
        if st.session_state.generated_assets and st.session_state.edited_assets:
            st.markdown("---")
            st.success("✅ Assets generated! Choose from MULTIPLE options below.")
            
            edited = st.session_state.edited_assets
            
            # Create tabs for each platform
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13 = st.tabs([
                "📝 Blurbs", "🎬 TikTok", "🎥 YouTube", "📸 Instagram Posts", "🎞️ Instagram Reels",
                "🛒 Amazon", "📢 Facebook Ads", "📧 Email Sequences", "📰 Press Kits", 
                "📌 Pinterest", "📚 Goodreads", "🎙️ Podcasts", "📅 Launch Timeline"
            ])
            
            # Tab 1: Blurbs (multiple options)
            with tab1:
                st.markdown("### 📝 Book Blurb Options")
                st.markdown("Choose from multiple blurbs with different angles:")
                
                blurbs = edited.get('blurbs', [])
                if blurbs and isinstance(blurbs, list):
                    for i, blurb in enumerate(blurbs):
                        with st.expander(f"Blurb Option {i+1}", expanded=i==0):
                            current_text = str(blurb) if blurb else ""
                            edited['blurbs'][i] = st.text_area(
                                f"Edit Blurb {i+1}", 
                                current_text, 
                                height=150,
                                key=f"blurb_{i}"
                            )
                else:
                    st.info("No blurbs generated")
            
            # Tab 2: TikTok Scripts (multiple options)
            with tab2:
                st.markdown("### 🎬 TikTok Script Options")
                st.markdown("Multiple script options with different hooks and styles:")
                
                scripts = edited.get('tiktok_scripts', [])
                if scripts and isinstance(scripts, list):
                    for i, script in enumerate(scripts):
                        with st.expander(f"TikTok Script {i+1}", expanded=i==0):
                            if isinstance(script, dict):
                                # Ensure all expected keys exist
                                script['hook'] = st.text_input(
                                    "Hook", 
                                    safe_get_str(script, 'hook'), 
                                    key=f"tiktok_{i}_hook"
                                )
                                script['visuals'] = st.text_input(
                                    "Visuals", 
                                    safe_get_str(script, 'visuals'), 
                                    key=f"tiktok_{i}_visuals"
                                )
                                script['voiceover'] = st.text_area(
                                    "Voiceover", 
                                    safe_get_str(script, 'voiceover'), 
                                    height=100,
                                    key=f"tiktok_{i}_voiceover"
                                )
                                script['music'] = st.text_input(
                                    "Music", 
                                    safe_get_str(script, 'music'), 
                                    key=f"tiktok_{i}_music"
                                )
                                script['cta'] = st.text_input(
                                    "Call to Action", 
                                    safe_get_str(script, 'cta'), 
                                    key=f"tiktok_{i}_cta"
                                )
                                
                                # Handle hashtags
                                hashtags = safe_get_list(script, 'hashtags')
                                tag_string = ' '.join(hashtags)
                                edited_tags = st.text_input(
                                    "Hashtags (space separated)", 
                                    tag_string, 
                                    key=f"tiktok_{i}_hashtags"
                                )
                                script['hashtags'] = edited_tags.split() if edited_tags else []
                else:
                    st.info("No TikTok scripts generated")
            
            # Tab 3: YouTube Scripts (multiple options)
            with tab3:
                st.markdown("### 🎥 YouTube Video Script Options")
                st.markdown("Long-form video scripts for deeper content:")
                
                scripts = edited.get('youtube_scripts', [])
                if scripts and isinstance(scripts, list):
                    for i, script in enumerate(scripts):
                        with st.expander(f"YouTube Script {i+1}", expanded=i==0):
                            if isinstance(script, dict):
                                script['title'] = st.text_input(
                                    "Title", 
                                    safe_get_str(script, 'title'), 
                                    key=f"youtube_{i}_title"
                                )
                                script['script'] = st.text_area(
                                    "Script", 
                                    safe_get_str(script, 'script'), 
                                    height=200,
                                    key=f"youtube_{i}_script"
                                )
                                script['length'] = st.text_input(
                                    "Length", 
                                    safe_get_str(script, 'length'), 
                                    key=f"youtube_{i}_length"
                                )
                                script['cta'] = st.text_input(
                                    "Call to Action", 
                                    safe_get_str(script, 'cta'), 
                                    key=f"youtube_{i}_cta"
                                )
                else:
                    st.info("No YouTube scripts generated")
            
            # Tab 4: Instagram Posts (multiple options)
            with tab4:
                st.markdown("### 📸 Instagram Post Options")
                st.markdown("Multiple post ideas with different visuals and captions:")
                
                posts = edited.get('instagram_posts', [])
                if posts and isinstance(posts, list):
                    for i, post in enumerate(posts):
                        with st.expander(f"Instagram Post {i+1}", expanded=i==0):
                            if isinstance(post, dict):
                                post['image_description'] = st.text_input(
                                    "Image Description", 
                                    safe_get_str(post, 'image_description'), 
                                    key=f"insta_post_{i}_image"
                                )
                                post['caption'] = st.text_area(
                                    "Caption", 
                                    safe_get_str(post, 'caption'), 
                                    height=100,
                                    key=f"insta_post_{i}_caption"
                                )
                                
                                # Handle hashtags
                                hashtags = safe_get_list(post, 'hashtags')
                                tag_string = ' '.join(hashtags)
                                edited_tags = st.text_input(
                                    "Hashtags (space separated)", 
                                    tag_string, 
                                    key=f"insta_post_{i}_hashtags"
                                )
                                post['hashtags'] = edited_tags.split() if edited_tags else []
                else:
                    st.info("No Instagram posts generated")
            
            # Tab 5: Instagram Reels (multiple options)
            with tab5:
                st.markdown("### 🎞️ Instagram Reel Options")
                st.markdown("Multiple reel concepts with different approaches:")
                
                reels = edited.get('instagram_reels', [])
                if reels and isinstance(reels, list):
                    for i, reel in enumerate(reels):
                        with st.expander(f"Instagram Reel {i+1}", expanded=i==0):
                            if isinstance(reel, dict):
                                reel['concept'] = st.text_input(
                                    "Concept", 
                                    safe_get_str(reel, 'concept'), 
                                    key=f"insta_reel_{i}_concept"
                                )
                                reel['script'] = st.text_area(
                                    "Script", 
                                    safe_get_str(reel, 'script'), 
                                    height=100,
                                    key=f"insta_reel_{i}_script"
                                )
                                reel['music'] = st.text_input(
                                    "Music", 
                                    safe_get_str(reel, 'music'), 
                                    key=f"insta_reel_{i}_music"
                                )
                                reel['duration'] = st.text_input(
                                    "Duration", 
                                    safe_get_str(reel, 'duration'), 
                                    key=f"insta_reel_{i}_duration"
                                )
                else:
                    st.info("No Instagram reels generated")
            
            # Tab 6: Amazon Options (multiple options)
            with tab6:
                st.markdown("### 🛒 Amazon Listing Options")
                st.markdown("Multiple Amazon page approaches:")
                
                amazon_options = edited.get('amazon_options', [])
                if amazon_options and isinstance(amazon_options, list):
                    for i, amazon in enumerate(amazon_options):
                        with st.expander(f"Amazon Option {i+1}", expanded=i==0):
                            if isinstance(amazon, dict):
                                # A+ Content
                                if 'a_plus_content' in amazon and isinstance(amazon['a_plus_content'], dict):
                                    ap = amazon['a_plus_content']
                                    ap['title'] = st.text_input(
                                        "A+ Title", 
                                        safe_get_str(ap, 'title'), 
                                        key=f"amazon_ap_title_{i}"
                                    )
                                    ap['description'] = st.text_area(
                                        "A+ Description", 
                                        safe_get_str(ap, 'description'), 
                                        height=100, 
                                        key=f"amazon_ap_desc_{i}"
                                    )
                                    
                                    features = safe_get_list(ap, 'key_features')
                                    for f_idx, feature in enumerate(features[:5]):  # Limit to 5 features
                                        features[f_idx] = st.text_input(
                                            f"Feature {f_idx+1}", 
                                            str(feature) if feature else "", 
                                            key=f"amazon_feat_{i}_{f_idx}"
                                        )
                                    ap['key_features'] = features
                                
                                # Search Terms
                                terms = safe_get_list(amazon, 'search_terms')
                                term_string = ', '.join(terms)
                                edited_terms = st.text_input(
                                    "Keywords (comma separated)", 
                                    term_string, 
                                    key=f"amazon_terms_{i}"
                                )
                                amazon['search_terms'] = [t.strip() for t in edited_terms.split(',') if t.strip()]
                                
                                # Author Bio
                                amazon['author_bio'] = st.text_area(
                                    "Author Bio", 
                                    safe_get_str(amazon, 'author_bio'), 
                                    height=150, 
                                    key=f"amazon_bio_{i}"
                                )
                else:
                    st.info("No Amazon options generated")
            
            # Tab 7: Facebook Ads (multiple options)
            with tab7:
                st.markdown("### 📢 Facebook Ad Options")
                st.markdown("Multiple ad variations for different audiences:")
                
                ads = edited.get('facebook_ads', [])
                if ads and isinstance(ads, list):
                    for i, ad in enumerate(ads):
                        with st.expander(f"Facebook Ad {i+1}", expanded=i==0):
                            if isinstance(ad, dict):
                                ad['audience'] = st.text_input(
                                    "Audience", 
                                    safe_get_str(ad, 'audience'), 
                                    key=f"fb_ad_{i}_audience"
                                )
                                ad['headline'] = st.text_input(
                                    "Headline", 
                                    safe_get_str(ad, 'headline'), 
                                    key=f"fb_ad_{i}_headline"
                                )
                                ad['primary_text'] = st.text_area(
                                    "Primary Text", 
                                    safe_get_str(ad, 'primary_text'), 
                                    height=100,
                                    key=f"fb_ad_{i}_text"
                                )
                                ad['description'] = st.text_input(
                                    "Description", 
                                    safe_get_str(ad, 'description'), 
                                    key=f"fb_ad_{i}_desc"
                                )
                                ad['cta'] = st.text_input(
                                    "Call to Action", 
                                    safe_get_str(ad, 'cta'), 
                                    key=f"fb_ad_{i}_cta"
                                )
                else:
                    st.info("No Facebook ads generated")
            
            # Tab 8: Email Sequences (multiple sequences)
            with tab8:
                st.markdown("### 📧 Email Sequence Options")
                st.markdown("Complete email sequences for different phases:")
                
                sequences = edited.get('email_sequences', [])
                if sequences and isinstance(sequences, list):
                    for seq_idx, sequence in enumerate(sequences):
                        sequence_name = safe_get_str(sequence, 'name', f'Email Sequence {seq_idx+1}')
                        with st.expander(sequence_name, expanded=seq_idx==0):
                            if isinstance(sequence, dict):
                                sequence['name'] = st.text_input(
                                    "Sequence Name", 
                                    sequence_name, 
                                    key=f"seq_name_{seq_idx}"
                                )
                                emails = safe_get_list(sequence, 'emails')
                                for email_idx, email in enumerate(emails):
                                    if isinstance(email, dict):
                                        st.markdown(f"**Email {email_idx+1}**")
                                        email['subject'] = st.text_input(
                                            "Subject", 
                                            safe_get_str(email, 'subject'), 
                                            key=f"email_{seq_idx}_{email_idx}_subject"
                                        )
                                        email['body'] = st.text_area(
                                            "Body", 
                                            safe_get_str(email, 'body'), 
                                            height=150,
                                            key=f"email_{seq_idx}_{email_idx}_body"
                                        )
                else:
                    st.info("No email sequences generated")
            
            # Tab 9: Press Kit Options (multiple options)
            with tab9:
                st.markdown("### 📰 Press Kit Options")
                st.markdown("Multiple press kit variations:")
                
                press_options = edited.get('press_kit_options', [])
                if press_options and isinstance(press_options, list):
                    for i, press in enumerate(press_options):
                        with st.expander(f"Press Kit Option {i+1}", expanded=i==0):
                            if isinstance(press, dict):
                                press['press_release'] = st.text_area(
                                    "Press Release", 
                                    safe_get_str(press, 'press_release'), 
                                    height=200,
                                    key=f"press_release_{i}"
                                )
                                
                                # Handle talking points
                                points = safe_get_list(press, 'key_talking_points')
                                point_string = '\n'.join(points)
                                edited_points = st.text_area(
                                    "Key Talking Points (one per line)", 
                                    point_string, 
                                    height=100,
                                    key=f"press_points_{i}"
                                )
                                press['key_talking_points'] = [p.strip() for p in edited_points.split('\n') if p.strip()]
                else:
                    st.info("No press kit options generated")
            
            # Tab 10: Pinterest Options (multiple options)
            with tab10:
                st.markdown("### 📌 Pinterest Options")
                st.markdown("Multiple pin strategies:")
                
                pinterest_options = edited.get('pinterest_options', [])
                if pinterest_options and isinstance(pinterest_options, list):
                    for i, pinterest in enumerate(pinterest_options):
                        with st.expander(f"Pinterest Option {i+1}", expanded=i==0):
                            if isinstance(pinterest, dict):
                                # Handle pin descriptions
                                pins = safe_get_list(pinterest, 'pin_descriptions')
                                pin_string = '\n'.join(pins)
                                edited_pins = st.text_area(
                                    "Pin Descriptions (one per line)", 
                                    pin_string, 
                                    height=100,
                                    key=f"pinterest_pins_{i}"
                                )
                                pinterest['pin_descriptions'] = [p.strip() for p in edited_pins.split('\n') if p.strip()]
                else:
                    st.info("No Pinterest options generated")
            
            # Tab 11: Goodreads Options (multiple options)
            with tab11:
                st.markdown("### 📚 Goodreads Options")
                st.markdown("Multiple Goodreads strategies:")
                
                goodreads_options = edited.get('goodreads_options', [])
                if goodreads_options and isinstance(goodreads_options, list):
                    for i, goodreads in enumerate(goodreads_options):
                        with st.expander(f"Goodreads Option {i+1}", expanded=i==0):
                            if isinstance(goodreads, dict):
                                goodreads['giveaway_description'] = st.text_area(
                                    "Giveaway Description", 
                                    safe_get_str(goodreads, 'giveaway_description'), 
                                    height=150,
                                    key=f"goodreads_giveaway_{i}"
                                )
                                
                                # Handle discussion questions
                                questions = safe_get_list(goodreads, 'discussion_questions')
                                q_string = '\n'.join(questions)
                                edited_qs = st.text_area(
                                    "Discussion Questions (one per line)", 
                                    q_string, 
                                    height=100,
                                    key=f"goodreads_questions_{i}"
                                )
                                goodreads['discussion_questions'] = [q.strip() for q in edited_qs.split('\n') if q.strip()]
                else:
                    st.info("No Goodreads options generated")
            
            # Tab 12: Podcast Pitches (multiple options)
            with tab12:
                st.markdown("### 🎙️ Podcast Pitch Options")
                st.markdown("Multiple podcast pitch approaches:")
                
                podcast_options = edited.get('podcast_pitches', [])
                if podcast_options and isinstance(podcast_options, list):
                    for i, podcast in enumerate(podcast_options):
                        with st.expander(f"Podcast Pitch {i+1}", expanded=i==0):
                            if isinstance(podcast, dict):
                                podcast['pitch_email'] = st.text_area(
                                    "Pitch Email", 
                                    safe_get_str(podcast, 'pitch_email'), 
                                    height=200,
                                    key=f"podcast_email_{i}"
                                )
                                
                                # Handle talking points
                                points = safe_get_list(podcast, 'talking_points')
                                point_string = '\n'.join(points)
                                edited_points = st.text_area(
                                    "Talking Points (one per line)", 
                                    point_string, 
                                    height=100,
                                    key=f"podcast_points_{i}"
                                )
                                podcast['talking_points'] = [p.strip() for p in edited_points.split('\n') if p.strip()]
                else:
                    st.info("No podcast pitches generated")
            
            # Tab 13: Launch Timeline
            with tab13:
                st.markdown("### 📅 Launch Timeline")
                st.markdown("Complete launch plan with timing:")
                
                timeline = edited.get('launch_timeline', {})
                if timeline and isinstance(timeline, dict):
                    phases = [
                        ("6_weeks_before", "6 Weeks Before Launch"),
                        ("4_weeks_before", "4 Weeks Before Launch"),
                        ("2_weeks_before", "2 Weeks Before Launch"),
                        ("launch_week", "Launch Week"),
                        ("post_launch", "Post-Launch")
                    ]
                    
                    for phase_key, phase_name in phases:
                        with st.expander(phase_name, expanded=True):
                            items = safe_get_list(timeline, phase_key)
                            if items:
                                for idx, item in enumerate(items):
                                    edited_item = st.text_input(
                                        f"Item {idx+1}", 
                                        str(item) if item else "",
                                        key=f"timeline_{phase_key}_{idx}"
                                    )
                                    items[idx] = edited_item
                                timeline[phase_key] = items
                else:
                    st.info("No launch timeline generated")
            
            st.success("✅ All edits saved in current session")

def generate_marketing_assets(client, analysis_data):
    """Generate LOTS of marketing assets from saved analysis"""
    
    # Extract the actual analysis
    book_info = extract_book_info(analysis_data)
    
    # Try to get cover analysis if it exists
    cover_analysis = {}
    if isinstance(analysis_data, dict):
        cover_analysis = analysis_data.get('cover_analysis', {})
    
    prompt = f"""
    Based on this book analysis, create comprehensive marketing assets for ALL platforms.
    For EACH platform, generate MULTIPLE options (5-10 each) so the author can choose.
    Include a COMPLETE LAUNCH TIMELINE with specific actions for each phase.
    
    BOOK ANALYSIS:
    {json.dumps(book_info, indent=2)}
    
    COVER ANALYSIS:
    {json.dumps(cover_analysis, indent=2)}
    
    Return JSON with:
    
    1. blurbs: [
        "Option 1: Compelling 150-word blurb focusing on plot",
        "Option 2: Emotional blurb focusing on characters",
        "Option 3: High-concept blurb focusing on hook",
        "Option 4: Mystery blurb leaving questions",
        "Option 5: Comparison-based blurb (For fans of X...)"
    ]
    
    2. tiktok_scripts: [
        {{
            "hook": "attention grabber option 1",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }},
        {{
            "hook": "attention grabber option 2",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }}
    ]
    
    3. youtube_scripts: [
        {{
            "title": "video title option 1",
            "script": "full video script with intro, main content, and outro",
            "length": "estimated minutes",
            "cta": "call to action"
        }},
        {{
            "title": "video title option 2",
            "script": "full video script with intro, main content, and outro",
            "length": "estimated minutes",
            "cta": "call to action"
        }}
    ]
    
    4. instagram_posts: [
        {{
            "image_description": "what to post option 1",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }},
        {{
            "image_description": "what to post option 2",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }}
    ]
    
    5. instagram_reels: [
        {{
            "concept": "reel idea option 1",
            "script": "content",
            "music": "trending audio",
            "duration": "15-30 seconds"
        }},
        {{
            "concept": "reel idea option 2",
            "script": "content",
            "music": "trending audio",
            "duration": "15-30 seconds"
        }}
    ]
    
    6. amazon_options: [
        {{
            "a_plus_content": {{
                "title": "enhanced brand content title",
                "description": "enhanced description",
                "key_features": ["feature1", "feature2", "feature3", "feature4", "feature5"]
            }},
            "search_terms": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
            "categories": ["suggested category 1", "suggested category 2"],
            "author_bio": "compelling author bio option 1"
        }},
        {{
            "a_plus_content": {{
                "title": "enhanced brand content title",
                "description": "enhanced description",
                "key_features": ["feature1", "feature2", "feature3", "feature4", "feature5"]
            }},
            "search_terms": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
            "categories": ["suggested category 1", "suggested category 2"],
            "author_bio": "compelling author bio option 2"
        }}
    ]
    
    7. facebook_ads: [
        {{
            "audience": "target demographic 1",
            "headline": "ad headline option 1",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "Shop Now"
        }},
        {{
            "audience": "target demographic 2",
            "headline": "ad headline option 2",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "Learn More"
        }}
    ]
    
    8. email_sequences: [
        {{
            "name": "Hype/Teaser Sequence (5 emails)",
            "emails": [
                {{
                    "subject": "Subject line 1 - The announcement",
                    "body": "Email content 1 - full email text"
                }},
                {{
                    "subject": "Subject line 2 - Behind the scenes",
                    "body": "Email content 2 - full email text"
                }}
            ]
        }},
        {{
            "name": "Launch Week Sequence (5 emails)",
            "emails": [
                {{
                    "subject": "Subject line 1 - It's live!",
                    "body": "Email content 1 - full email text"
                }},
                {{
                    "subject": "Subject line 2 - Reviews coming in",
                    "body": "Email content 2 - full email text"
                }}
            ]
        }}
    ]
    
    9. press_kit_options: [
        {{
            "press_release": "full press release option 1 - standard format",
            "author_qanda": [
                {{"question": "Question 1 about inspiration", "answer": "Answer 1"}},
                {{"question": "Question 2 about writing process", "answer": "Answer 2"}}
            ],
            "key_talking_points": ["point1", "point2", "point3", "point4", "point5"]
        }},
        {{
            "press_release": "full press release option 2 - angle on market trends",
            "author_qanda": [
                {{"question": "Question 1 about inspiration", "answer": "Answer 1"}},
                {{"question": "Question 2 about writing process", "answer": "Answer 2"}}
            ],
            "key_talking_points": ["point1", "point2", "point3", "point4", "point5"]
        }}
    ]
    
    10. pinterest_options: [
        {{
            "pin_descriptions": ["Pin 1: Quote from book", "Pin 2: Character aesthetic", "Pin 3: Setting inspiration"],
            "board_ideas": ["{{Book Title}} Inspiration", "Characters", "Settings"],
            "keywords": ["keyword1", "keyword2", "keyword3"]
        }},
        {{
            "pin_descriptions": ["Pin 1: Book review quote", "Pin 2: Reading playlist", "Pin 3: Fan art inspiration"],
            "board_ideas": ["{{Book Title}} Vibes", "Readers Love", "Book Club"],
            "keywords": ["keyword1", "keyword2", "keyword3"]
        }}
    ]
    
    11. goodreads_options: [
        {{
            "giveaway_description": "Option 1 - Standard giveaway: Enter to win a signed copy!",
            "discussion_questions": ["Q1: What was your favorite moment?", "Q2: Which character did you relate to most?"],
            "similar_books": ["Book 1 in similar genre", "Book 2 by similar author"]
        }},
        {{
            "giveaway_description": "Option 2 - Bundle giveaway: Win the book plus swag!",
            "discussion_questions": ["Q1: How did the ending make you feel?", "Q2: What surprised you most?"],
            "similar_books": ["Book 1 readers also enjoyed", "Book 2 if you liked this"]
        }}
    ]
    
    12. podcast_pitches: [
        {{
            "pitch_email": "Email template for book podcasts - angle on author journey",
            "talking_points": ["point1 about inspiration", "point2 about writing process"],
            "podcast_ideas": ["Episode 1: The story behind the story", "Episode 2: Writing in this genre"]
        }},
        {{
            "pitch_email": "Email template for genre-specific podcasts - angle on expertise",
            "talking_points": ["point1 about genre trends", "point2 about research"],
            "podcast_ideas": ["Episode 1: Deep dive into the world", "Episode 2: Character creation"]
        }}
    ]
    
    13. launch_timeline: {{
        "6_weeks_before": [
            "Action 1: Cover reveal on social media",
            "Action 2: Set up pre-order links",
            "Action 3: Create ARC team and send copies"
        ],
        "4_weeks_before": [
            "Action 1: Start posting teasers on TikTok",
            "Action 2: Share character introductions on Instagram",
            "Action 3: Send ARC reminder to reviewers"
        ],
        "2_weeks_before": [
            "Action 1: Increase posting frequency",
            "Action 2: Share early reviews/testimonials",
            "Action 3: Host Goodreads giveaway"
        ],
        "launch_week": [
            "Action 1: Launch day posts on ALL platforms",
            "Action 2: Send launch email to list",
            "Action 3: Go live on TikTok/Instagram"
        ],
        "post_launch": [
            "Action 1: Follow up with reviewers",
            "Action 2: Share fan posts/reactions",
            "Action 3: Plan next phase of content"
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a marketing expert. Return valid JSON only. Generate MULTIPLE options for each platform as requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Asset generation failed: {str(e)}")
        return None


# For direct testing
if __name__ == "__main__":
    show_generator()

# MarketingGenerator.py - FIXED VERSION
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
    if isinstance(book_data, dict):
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
            
            with st.expander("📋 How to get an OpenAI API Key", expanded=True):
                st.markdown("""
                <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #667eea;">
                <h4>To get an OpenAI API key, follow these steps:</h4>
                <div style="margin: 8px 0; padding: 5px;">1️⃣ <strong>Go to the OpenAI Platform</strong><br>👉 https://platform.openai.com/</div>
                <div style="margin: 8px 0; padding: 5px;">2️⃣ <strong>Sign in or Create an Account</strong><br>Log in with your existing account or create a new one.</div>
                <div style="margin: 8px 0; padding: 5px;">3️⃣ <strong>Open the API Keys Page</strong><br>Click your profile icon (top right) → Select "View API keys"</div>
                <div style="margin: 8px 0; padding: 5px;">4️⃣ <strong>Create a New Key</strong><br>Click "Create new secret key" → Give it a name → Copy the key immediately</div>
                </div>
                """, unsafe_allow_html=True)
            
            if api_key:
                st.session_state.openai_api_key = api_key
                st.rerun()
        return
    
    # ============================================================================
    # BOOK SELECTION SECTION
    # ============================================================================
    
    st.markdown("### 📚 Select a Book to Market")
    
    # Check for loaded analysis from Book Analyzer
    if st.session_state.get('loaded_analysis') and not st.session_state.get('_assets_generated', False):
        st.session_state.loaded_analysis = st.session_state.loaded_analysis
        st.success(f"✅ Book loaded from analyzer: {extract_book_info(st.session_state.loaded_analysis).get('title', 'Unknown')}")
    
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
        
        # Add current loaded analysis if it exists
        if st.session_state.loaded_analysis and not any(b.get('data') == st.session_state.loaded_analysis for b in all_books):
            book_info = extract_book_info(st.session_state.loaded_analysis)
            title = book_info.get('title', 'Unknown')
            all_books.append({
                'display': f"📌 CURRENT: {title} (From Analyzer)",
                'source': 'current',
                'data': st.session_state.loaded_analysis,
                'filename': 'current'
            })
        
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
            if st.button("📖 Go to Book Analyzer", use_container_width=True):
                st.session_state.page = "📖 Book Analyzer"
                st.rerun()
            return
    
    with col2:
        if all_books and st.button("📂 Load Book", type="primary", use_container_width=True):
            st.session_state.loaded_analysis = selected_book['data']
            st.session_state.generated_assets = None
            st.session_state.edited_assets = None
            st.session_state._assets_generated = False
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
                            st.session_state._assets_generated = True
                            st.rerun()
                    except Exception as e:
                        st.error(f"Generation failed: {str(e)}")
        
        with col2:
            if st.session_state.generated_assets:
                if st.button("🔄 Regenerate Assets", use_container_width=True):
                    st.session_state.generated_assets = None
                    st.session_state.edited_assets = None
                    st.session_state._assets_generated = False
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
    For EACH platform, generate MULTIPLE options (at least 5-8 each) so the author can choose.
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
        "Option 5: Comparison-based blurb (For fans of X...)",
        "Option 6: Short punchy version for social media",
        "Option 7: Question-based blurb that hooks readers",
        "Option 8: Atmosphere-focused blurb"
    ]
    
    2. tiktok_scripts: [
        {{
            "hook": "attention grabber option 1 - dramatic reading",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }},
        {{
            "hook": "attention grabber option 2 - emotional angle",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }},
        {{
            "hook": "attention grabber option 3 - plot twist reveal",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }},
        {{
            "hook": "attention grabber option 4 - character focus",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }},
        {{
            "hook": "attention grabber option 5 - aesthetic vibes",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }},
        {{
            "hook": "attention grabber option 6 - behind the scenes",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }},
        {{
            "hook": "attention grabber option 7 - reader reaction",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }},
        {{
            "hook": "attention grabber option 8 - writing process",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }}
    ]
    
    3. youtube_scripts: [
        {{
            "title": "video title option 1 - Book Review/Reaction",
            "script": "full video script with intro, main content, and outro",
            "length": "estimated minutes",
            "cta": "call to action"
        }},
        {{
            "title": "video title option 2 - Deep Dive Analysis",
            "script": "full video script with intro, main content, and outro",
            "length": "estimated minutes",
            "cta": "call to action"
        }},
        {{
            "title": "video title option 3 - Author Interview Style",
            "script": "full video script with intro, main content, and outro",
            "length": "estimated minutes",
            "cta": "call to action"
        }},
        {{
            "title": "video title option 4 - Themes & Symbolism",
            "script": "full video script with intro, main content, and outro",
            "length": "estimated minutes",
            "cta": "call to action"
        }},
        {{
            "title": "video title option 5 - Character Study",
            "script": "full video script with intro, main content, and outro",
            "length": "estimated minutes",
            "cta": "call to action"
        }},
        {{
            "title": "video title option 6 - Writing Craft Analysis",
            "script": "full video script with intro, main content, and outro",
            "length": "estimated minutes",
            "cta": "call to action"
        }}
    ]
    
    4. instagram_posts: [
        {{
            "image_description": "what to post option 1 - quote graphic",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }},
        {{
            "image_description": "what to post option 2 - character aesthetic",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }},
        {{
            "image_description": "what to post option 3 - setting mood board",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }},
        {{
            "image_description": "what to post option 4 - book stack/flatlay",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }},
        {{
            "image_description": "what to post option 5 - behind the scenes",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }},
        {{
            "image_description": "what to post option 6 - reader questions",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }},
        {{
            "image_description": "what to post option 7 - writing tips",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }},
        {{
            "image_description": "what to post option 8 - release countdown",
            "caption": "caption text",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
        }}
    ]
    
    5. instagram_reels: [
        {{
            "concept": "reel idea option 1 - book trailer style",
            "script": "content",
            "music": "trending audio",
            "duration": "15-30 seconds"
        }},
        {{
            "concept": "reel idea option 2 - POV character",
            "script": "content",
            "music": "trending audio",
            "duration": "15-30 seconds"
        }},
        {{
            "concept": "reel idea option 3 - aesthetic montage",
            "script": "content",
            "music": "trending audio",
            "duration": "15-30 seconds"
        }},
        {{
            "concept": "reel idea option 4 - reaction to plot twist",
            "script": "content",
            "music": "trending audio",
            "duration": "15-30 seconds"
        }},
        {{
            "concept": "reel idea option 5 - writing process timelapse",
            "script": "content",
            "music": "trending audio",
            "duration": "15-30 seconds"
        }},
        {{
            "concept": "reel idea option 6 - character introduction",
            "script": "content",
            "music": "trending audio",
            "duration": "15-30 seconds"
        }},
        {{
            "concept": "reel idea option 7 - book haul/collection",
            "script": "content",
            "music": "trending audio",
            "duration": "15-30 seconds"
        }}
    ]
    
    6. amazon_options: [
        {{
            "a_plus_content": {{
                "title": "enhanced brand content title option 1",
                "description": "enhanced description",
                "key_features": ["feature1", "feature2", "feature3", "feature4", "feature5"]
            }},
            "search_terms": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
            "categories": ["suggested category 1", "suggested category 2"],
            "author_bio": "compelling author bio option 1"
        }},
        {{
            "a_plus_content": {{
                "title": "enhanced brand content title option 2",
                "description": "enhanced description",
                "key_features": ["feature1", "feature2", "feature3", "feature4", "feature5"]
            }},
            "search_terms": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
            "categories": ["suggested category 1", "suggested category 2"],
            "author_bio": "compelling author bio option 2"
        }},
        {{
            "a_plus_content": {{
                "title": "enhanced brand content title option 3",
                "description": "enhanced description",
                "key_features": ["feature1", "feature2", "feature3", "feature4", "feature5"]
            }},
            "search_terms": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
            "categories": ["suggested category 1", "suggested category 2"],
            "author_bio": "compelling author bio option 3"
        }},
        {{
            "a_plus_content": {{
                "title": "enhanced brand content title option 4",
                "description": "enhanced description",
                "key_features": ["feature1", "feature2", "feature3", "feature4", "feature5"]
            }},
            "search_terms": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
            "categories": ["suggested category 1", "suggested category 2"],
            "author_bio": "compelling author bio option 4"
        }}
    ]
    
    7. facebook_ads: [
        {{
            "audience": "target demographic 1 - similar authors",
            "headline": "ad headline option 1",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "Shop Now"
        }},
        {{
            "audience": "target demographic 2 - genre readers",
            "headline": "ad headline option 2",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "Learn More"
        }},
        {{
            "audience": "target demographic 3 - book club members",
            "headline": "ad headline option 3",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "Sign Up"
        }},
        {{
            "audience": "target demographic 4 - bargain hunters",
            "headline": "ad headline option 4",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "Buy Now"
        }},
        {{
            "audience": "target demographic 5 - series readers",
            "headline": "ad headline option 5",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "Pre-order"
        }},
        {{
            "audience": "target demographic 6 - gift shoppers",
            "headline": "ad headline option 6",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "Shop Now"
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
                }},
                {{
                    "subject": "Subject line 3 - Character introduction",
                    "body": "Email content 3 - full email text"
                }},
                {{
                    "subject": "Subject line 4 - Exclusive excerpt",
                    "body": "Email content 4 - full email text"
                }},
                {{
                    "subject": "Subject line 5 - Pre-order reminder",
                    "body": "Email content 5 - full email text"
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
                }},
                {{
                    "subject": "Subject line 3 - Reader reactions",
                    "body": "Email content 3 - full email text"
                }},
                {{
                    "subject": "Subject line 4 - Thank you",
                    "body": "Email content 4 - full email text"
                }},
                {{
                    "subject": "Subject line 5 - What's next",
                    "body": "Email content 5 - full email text"
                }}
            ]
        }},
        {{
            "name": "Review/Engagement Sequence (3 emails)",
            "emails": [
                {{
                    "subject": "Subject line 1 - Loved the book?",
                    "body": "Email content 1 - full email text"
                }},
                {{
                    "subject": "Subject line 2 - Join the discussion",
                    "body": "Email content 2 - full email text"
                }},
                {{
                    "subject": "Subject line 3 - Stay connected",
                    "body": "Email content 3 - full email text"
                }}
            ]
        }},
        {{
            "name": "Series Announcement Sequence (4 emails)",
            "emails": [
                {{
                    "subject": "Subject line 1 - What's coming next",
                    "body": "Email content 1 - full email text"
                }},
                {{
                    "subject": "Subject line 2 - Exclusive sneak peek",
                    "body": "Email content 2 - full email text"
                }},
                {{
                    "subject": "Subject line 3 - Pre-order next book",
                    "body": "Email content 3 - full email text"
                }},
                {{
                    "subject": "Subject line 4 - Bonus content",
                    "body": "Email content 4 - full email text"
                }}
            ]
        }}
    ]
    
    9. press_kit_options: [
        {{
            "press_release": "full press release option 1 - standard format",
            "author_qanda": [
                {{"question": "Question 1 about inspiration", "answer": "Answer 1"}},
                {{"question": "Question 2 about writing process", "answer": "Answer 2"}},
                {{"question": "Question 3 about future projects", "answer": "Answer 3"}}
            ],
            "key_talking_points": ["point1", "point2", "point3", "point4", "point5"]
        }},
        {{
            "press_release": "full press release option 2 - angle on market trends",
            "author_qanda": [
                {{"question": "Question 1 about inspiration", "answer": "Answer 1"}},
                {{"question": "Question 2 about writing process", "answer": "Answer 2"}},
                {{"question": "Question 3 about future projects", "answer": "Answer 3"}}
            ],
            "key_talking_points": ["point1", "point2", "point3", "point4", "point5"]
        }},
        {{
            "press_release": "full press release option 3 - personal journey angle",
            "author_qanda": [
                {{"question": "Question 1 about inspiration", "answer": "Answer 1"}},
                {{"question": "Question 2 about writing process", "answer": "Answer 2"}},
                {{"question": "Question 3 about future projects", "answer": "Answer 3"}}
            ],
            "key_talking_points": ["point1", "point2", "point3", "point4", "point5"]
        }}
    ]
    
    10. pinterest_options: [
        {{
            "pin_descriptions": ["Pin 1: Quote from book", "Pin 2: Character aesthetic", "Pin 3: Setting inspiration", "Pin 4: Mood board", "Pin 5: Writing tips", "Pin 6: Reading playlist"],
            "board_ideas": ["Book Title Inspiration", "Characters", "Settings", "Quotes", "Author Life", "Book Club"],
            "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
        }},
        {{
            "pin_descriptions": ["Pin 1: Book review quote", "Pin 2: Reading playlist", "Pin 3: Fan art inspiration", "Pin 4: Similar books", "Pin 5: Author interview", "Pin 6: Behind the scenes"],
            "board_ideas": ["Book Title Vibes", "Readers Love", "Book Club", "Author Journey", "Writing Process", "Book Aesthetics"],
            "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
        }},
        {{
            "pin_descriptions": ["Pin 1: Character quotes", "Pin 2: Scene illustrations", "Pin 3: Bookish recipes", "Pin 4: Writing inspiration", "Pin 5: Author recommendations", "Pin 6: Themed playlists"],
            "board_ideas": ["Book Title World", "Character Art", "Bookish Lifestyle", "Creative Writing", "Author Picks", "Reader Resources"],
            "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
        }}
    ]
    
    11. goodreads_options: [
        {{
            "giveaway_description": "Option 1 - Standard giveaway: Enter to win a signed copy!",
            "discussion_questions": ["Q1: What was your favorite moment?", "Q2: Which character did you relate to most?", "Q3: How did the setting affect the story?", "Q4: What themes stood out to you?", "Q5: Would you recommend this book?"],
            "similar_books": ["Book 1 in similar genre", "Book 2 by similar author", "Book 3 with similar themes"]
        }},
        {{
            "giveaway_description": "Option 2 - Bundle giveaway: Win the book plus swag!",
            "discussion_questions": ["Q1: How did the ending make you feel?", "Q2: What surprised you most?", "Q3: Who was your favorite side character?", "Q4: What would you ask the author?", "Q5: Rate the pacing"],
            "similar_books": ["Book 1 readers also enjoyed", "Book 2 if you liked this", "Book 3 in the same vein"]
        }},
        {{
            "giveaway_description": "Option 3 - ARC giveaway: Be among the first to read!",
            "discussion_questions": ["Q1: What do you think will happen next?", "Q2: Which character intrigues you most?", "Q3: What theories do you have?", "Q4: How does this compare to other books?", "Q5: What would you change?"],
            "similar_books": ["Book 1 for fans of", "Book 2 similar vibes", "Book 3 recommended reads"]
        }}
    ]
    
    12. podcast_pitches: [
        {{
            "pitch_email": "Email template for book podcasts - angle on author journey",
            "talking_points": ["point1 about inspiration", "point2 about writing process", "point3 about themes", "point4 about market timing", "point5 about future projects"],
            "podcast_ideas": ["Episode 1: The story behind the story", "Episode 2: Writing in this genre", "Episode 3: From manuscript to publication"]
        }},
        {{
            "pitch_email": "Email template for genre-specific podcasts - angle on expertise",
            "talking_points": ["point1 about genre trends", "point2 about research", "point3 about character development", "point4 about worldbuilding", "point5 about reader reactions"],
            "podcast_ideas": ["Episode 1: Deep dive into the world", "Episode 2: Character creation", "Episode 3: Genre insights"]
        }},
        {{
            "pitch_email": "Email template for author interview shows - personal angle",
            "talking_points": ["point1 about personal journey", "point2 about challenges", "point3 about successes", "point4 about daily routine", "point5 about advice for writers"],
            "podcast_ideas": ["Episode 1: My writing journey", "Episode 2: Daily habits of a writer", "Episode 3: Advice for new authors"]
        }},
        {{
            "pitch_email": "Email template for writing craft podcasts - technical angle",
            "talking_points": ["point1 about craft choices", "point2 about revisions", "point3 about overcoming blocks", "point4 about editing process", "point5 about publishing journey"],
            "podcast_ideas": ["Episode 1: Crafting compelling characters", "Episode 2: Plot structure secrets", "Episode 3: Revision strategies"]
        }}
    ]
    
    13. launch_timeline: {{
        "6_weeks_before": [
            "Action 1: Cover reveal on social media",
            "Action 2: Set up pre-order links",
            "Action 3: Create ARC team and send copies",
            "Action 4: Schedule blog tour",
            "Action 5: Prepare newsletter announcement",
            "Action 6: Create media kit",
            "Action 7: Reach out to early reviewers"
        ],
        "4_weeks_before": [
            "Action 1: Start posting teasers on TikTok",
            "Action 2: Share character introductions on Instagram",
            "Action 3: Send ARC reminder to reviewers",
            "Action 4: Pitch to podcasters",
            "Action 5: Create launch graphics",
            "Action 6: Schedule social media posts",
            "Action 7: Prepare giveaway items"
        ],
        "2_weeks_before": [
            "Action 1: Increase posting frequency",
            "Action 2: Share early reviews/testimonials",
            "Action 3: Host Goodreads giveaway",
            "Action 4: Prepare launch day emails",
            "Action 5: Coordinate with street team",
            "Action 6: Create countdown posts",
            "Action 7: Finalize Amazon listing"
        ],
        "launch_week": [
            "Action 1: Launch day posts on ALL platforms",
            "Action 2: Send launch email to list",
            "Action 3: Go live on TikTok/Instagram",
            "Action 4: Monitor reviews and engage",
            "Action 5: Thank supporters publicly",
            "Action 6: Run launch day ads",
            "Action 7: Host launch party (virtual)"
        ],
        "post_launch": [
            "Action 1: Follow up with reviewers",
            "Action 2: Share fan posts/reactions",
            "Action 3: Plan next phase of content",
            "Action 4: Analyze what worked best",
            "Action 5: Start planning next book marketing",
            "Action 6: Collect testimonials",
            "Action 7: Update website/socials"
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a marketing expert. Return valid JSON only. Generate MULTIPLE options (at least 5-8) for each platform as requested."},
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

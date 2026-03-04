# MarketingGenerator.py - COMPLETE WORKING VERSION with ALL TABS
import streamlit as st
from openai import OpenAI
import json
import time
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# DATABASE CONNECTION - USING SECRETS
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

def auto_save_marketing_assets(user_id, book_title, assets_data):
    """AUTO-SAVE all marketing assets to database"""
    if not user_id or not assets_data or not book_title:
        return False
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        
        # Delete existing assets for this book to keep only latest
        cur.execute("""
            DELETE FROM user_marketing_assets 
            WHERE user_id = %s AND asset_name LIKE %s
        """, (user_id, f"{book_title} - %"))
        
        # Save each asset type
        saved_count = 0
        for asset_type, asset_content in assets_data.items():
            if asset_content:  # Only save if there's content
                cur.execute("""
                    INSERT INTO user_marketing_assets 
                    (user_id, asset_type, asset_name, asset_data, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    asset_type,
                    f"{book_title} - {asset_type}",
                    json.dumps({asset_type: asset_content}),
                    datetime.now(),
                    datetime.now()
                ))
                saved_count += 1
        
        conn.commit()
        
        if saved_count > 0:
            st.toast(f"💾 Auto-saved {saved_count} assets", icon="✅")
        return True
        
    except Exception as e:
        st.error(f"Auto-save failed: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def load_user_marketing_assets(user_id, book_title=None):
    """Load user's saved marketing assets"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return {}
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if book_title:
            cur.execute("""
                SELECT * FROM user_marketing_assets 
                WHERE user_id = %s AND asset_name LIKE %s
                ORDER BY updated_at DESC
            """, (user_id, f"{book_title} - %"))
        else:
            cur.execute("""
                SELECT * FROM user_marketing_assets 
                WHERE user_id = %s
                ORDER BY updated_at DESC
            """, (user_id,))
        
        assets = cur.fetchall()
        
        combined = {}
        for asset in assets:
            asset_data = asset['asset_data']
            if isinstance(asset_data, str):
                try:
                    asset_data = json.loads(asset_data)
                except:
                    continue
            if isinstance(asset_data, dict):
                combined.update(asset_data)
        
        return combined
    except Exception as e:
        st.error(f"Error loading assets: {e}")
        return {}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def extract_book_info(book_data):
    """Safely extract book info"""
    if not book_data:
        return {}
    
    if isinstance(book_data, dict):
        if 'book_info' in book_data:
            book_info = book_data['book_info']
            if isinstance(book_info, dict) and 'book_info' in book_info:
                return book_info['book_info']
            return book_info
        elif 'analysis_result' in book_data:
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
    if dictionary and isinstance(dictionary, dict):
        value = dictionary.get(key, default)
        return str(value) if value is not None else default
    return default

def safe_get_list(dictionary, key, default=None):
    if default is None:
        default = []
    if dictionary and isinstance(dictionary, dict):
        value = dictionary.get(key, default)
        return value if isinstance(value, list) else default
    return default

def show_generator():
    """Generate marketing assets with AUTO-SAVE"""
    
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
    
    if 'current_book_title' not in st.session_state:
        st.session_state.current_book_title = None
    
    if '_last_auto_save' not in st.session_state:
        st.session_state._last_auto_save = None
    
    # Header
    st.title("🎨 Marketing Asset Generator")
    st.markdown("**✨ AUTO-SAVE ENABLED** - All changes save to database automatically")
    st.markdown("---")
    
    # API Key input
    if not st.session_state.openai_api_key:
        with st.container():
            st.markdown("### 🔑 OpenAI API Key")
            api_key = st.text_input("Enter your API key", type="password", key="api_key_input")
            
            with st.expander("📋 How to get an OpenAI API Key", expanded=True):
                st.markdown("""
                <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #667eea;">
                <h4>To get an OpenAI API key:</h4>
                <div style="margin: 8px 0; padding: 5px;">1️⃣ <strong>Go to</strong> https://platform.openai.com/</div>
                <div style="margin: 8px 0; padding: 5px;">2️⃣ <strong>Sign in → View API keys → Create new key</strong></div>
                </div>
                """, unsafe_allow_html=True)
            
            if api_key:
                st.session_state.openai_api_key = api_key
                st.rerun()
        return
    
    # ============================================================================
    # BOOK SELECTION
    # ============================================================================
    
    st.markdown("### 📚 Select a Book")
    
    # Get analyzed books from database
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
                st.error(f"Error loading analyses: {e}")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if db_analyses:
            book_options = []
            for analysis in db_analyses:
                title = analysis.get('book_title', 'Unknown')
                date = analysis.get('created_at', datetime.now()).strftime('%Y-%m-%d')
                book_options.append({
                    'display': f"📖 {title} ({date})",
                    'data': analysis,
                    'title': title
                })
            
            selected_index = st.selectbox(
                "Choose a book:",
                range(len(book_options)),
                format_func=lambda x: book_options[x]['display'],
                key="book_selector"
            )
            selected_book = book_options[selected_index]
        else:
            st.info("No analyzed books found. Please analyze a book first.")
            if st.button("📖 Go to Book Analyzer", use_container_width=True):
                st.session_state.page = "📖 Book Analyzer"
                st.rerun()
            return
    
    with col2:
        if db_analyses and st.button("📂 Load Book", type="primary", use_container_width=True):
            st.session_state.loaded_analysis = selected_book['data']
            st.session_state.current_book_title = selected_book['title']
            st.session_state.generated_assets = None
            st.session_state.edited_assets = None
            st.session_state._assets_generated = False
            
            # Try to load existing assets
            existing_assets = load_user_marketing_assets(
                st.session_state.get('user_id', 1),
                selected_book['title']
            )
            if existing_assets:
                st.session_state.generated_assets = existing_assets
                st.session_state.edited_assets = existing_assets.copy()
                st.session_state._assets_generated = True
            st.rerun()
    
    # ============================================================================
    # ASSET GENERATION
    # ============================================================================
    
    if st.session_state.loaded_analysis:
        st.markdown("---")
        
        book_info = extract_book_info(st.session_state.loaded_analysis)
        title = book_info.get('title', st.session_state.current_book_title or 'Unknown')
        genre = book_info.get('genre', 'Unknown')
        
        st.success(f"✅ Working on: **{title}** ({genre})")
        
        # Generate button (only if no assets exist)
        if not st.session_state.generated_assets:
            col1, col2 = st.columns(2)
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
                                
                                # AUTO-SAVE to database
                                auto_save_marketing_assets(
                                    st.session_state.get('user_id', 1),
                                    title,
                                    assets
                                )
                                st.rerun()
                        except Exception as e:
                            st.error(f"Generation failed: {str(e)}")
            
            with col2:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()
        
        # ============================================================================
        # ASSET DISPLAY WITH ALL 13 TABS - COMPLETE
        # ============================================================================
        
        if st.session_state.generated_assets and st.session_state.edited_assets:
            st.markdown("---")
            st.success("✅ Assets loaded - Edit below (auto-saves to database)")
            
            edited = st.session_state.edited_assets
            book_title = st.session_state.current_book_title or title
            
            # ALL 13 TABS
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13 = st.tabs([
                "📝 Blurbs", 
                "🎬 TikTok", 
                "🎥 YouTube", 
                "📸 Instagram Posts", 
                "🎞️ Instagram Reels",
                "🛒 Amazon", 
                "📢 Facebook Ads", 
                "📧 Email Sequences", 
                "📰 Press Kits", 
                "📌 Pinterest", 
                "📚 Goodreads", 
                "🎙️ Podcasts", 
                "📅 Launch Timeline"
            ])
            
            changes_made = False
            
            # ========== TAB 1: BLURBS ==========
            with tab1:
                st.markdown("### 📝 Book Blurb Options")
                st.caption("8 different angles - edit any")
                
                blurbs = edited.get('blurbs', [])
                if blurbs and isinstance(blurbs, list):
                    cols = st.columns(2)
                    for i, blurb in enumerate(blurbs):
                        with cols[i % 2]:
                            with st.container():
                                st.markdown(f"**Option {i+1}**")
                                new_text = st.text_area(
                                    "", 
                                    str(blurb) if blurb else "", 
                                    height=120,
                                    key=f"blurb_{i}",
                                    label_visibility="collapsed"
                                )
                                if new_text != str(blurb):
                                    edited['blurbs'][i] = new_text
                                    changes_made = True
                else:
                    st.info("No blurbs generated")
            
            # ========== TAB 2: TIKTOK ==========
            with tab2:
                st.markdown("### 🎬 TikTok Script Options")
                st.caption("8 script options with different hooks")
                
                scripts = edited.get('tiktok_scripts', [])
                if scripts and isinstance(scripts, list):
                    for i, script in enumerate(scripts):
                        with st.expander(f"TikTok Script {i+1}", expanded=i==0):
                            if isinstance(script, dict):
                                col1, col2 = st.columns(2)
                                with col1:
                                    new_hook = st.text_input("Hook", safe_get_str(script, 'hook'), key=f"tiktok_{i}_hook")
                                    if new_hook != safe_get_str(script, 'hook'):
                                        script['hook'] = new_hook
                                        changes_made = True
                                    
                                    new_visuals = st.text_input("Visuals", safe_get_str(script, 'visuals'), key=f"tiktok_{i}_visuals")
                                    if new_visuals != safe_get_str(script, 'visuals'):
                                        script['visuals'] = new_visuals
                                        changes_made = True
                                
                                with col2:
                                    new_music = st.text_input("Music", safe_get_str(script, 'music'), key=f"tiktok_{i}_music")
                                    if new_music != safe_get_str(script, 'music'):
                                        script['music'] = new_music
                                        changes_made = True
                                    
                                    new_cta = st.text_input("CTA", safe_get_str(script, 'cta'), key=f"tiktok_{i}_cta")
                                    if new_cta != safe_get_str(script, 'cta'):
                                        script['cta'] = new_cta
                                        changes_made = True
                                
                                new_voiceover = st.text_area("Voiceover", safe_get_str(script, 'voiceover'), height=100, key=f"tiktok_{i}_voiceover")
                                if new_voiceover != safe_get_str(script, 'voiceover'):
                                    script['voiceover'] = new_voiceover
                                    changes_made = True
                                
                                hashtags = safe_get_list(script, 'hashtags')
                                tag_string = ' '.join(hashtags)
                                new_tags = st.text_input("Hashtags (space separated)", tag_string, key=f"tiktok_{i}_hashtags")
                                if new_tags != tag_string:
                                    script['hashtags'] = new_tags.split() if new_tags else []
                                    changes_made = True
                else:
                    st.info("No TikTok scripts generated")
            
            # ========== TAB 3: YOUTUBE ==========
            with tab3:
                st.markdown("### 🎥 YouTube Video Script Options")
                st.caption("6 long-form video scripts")
                
                scripts = edited.get('youtube_scripts', [])
                if scripts and isinstance(scripts, list):
                    for i, script in enumerate(scripts):
                        with st.expander(f"YouTube Script {i+1}", expanded=i==0):
                            if isinstance(script, dict):
                                new_title = st.text_input("Title", safe_get_str(script, 'title'), key=f"youtube_{i}_title")
                                if new_title != safe_get_str(script, 'title'):
                                    script['title'] = new_title
                                    changes_made = True
                                
                                new_script = st.text_area("Script", safe_get_str(script, 'script'), height=200, key=f"youtube_{i}_script")
                                if new_script != safe_get_str(script, 'script'):
                                    script['script'] = new_script
                                    changes_made = True
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    new_length = st.text_input("Length", safe_get_str(script, 'length'), key=f"youtube_{i}_length")
                                    if new_length != safe_get_str(script, 'length'):
                                        script['length'] = new_length
                                        changes_made = True
                                with col2:
                                    new_cta = st.text_input("CTA", safe_get_str(script, 'cta'), key=f"youtube_{i}_cta")
                                    if new_cta != safe_get_str(script, 'cta'):
                                        script['cta'] = new_cta
                                        changes_made = True
                else:
                    st.info("No YouTube scripts generated")
            
            # ========== TAB 4: INSTAGRAM POSTS ==========
            with tab4:
                st.markdown("### 📸 Instagram Post Options")
                st.caption("8 post ideas with different visuals")
                
                posts = edited.get('instagram_posts', [])
                if posts and isinstance(posts, list):
                    for i, post in enumerate(posts):
                        with st.expander(f"Instagram Post {i+1}", expanded=i==0):
                            if isinstance(post, dict):
                                new_image = st.text_input("Image Description", safe_get_str(post, 'image_description'), key=f"insta_post_{i}_image")
                                if new_image != safe_get_str(post, 'image_description'):
                                    post['image_description'] = new_image
                                    changes_made = True
                                
                                new_caption = st.text_area("Caption", safe_get_str(post, 'caption'), height=100, key=f"insta_post_{i}_caption")
                                if new_caption != safe_get_str(post, 'caption'):
                                    post['caption'] = new_caption
                                    changes_made = True
                                
                                hashtags = safe_get_list(post, 'hashtags')
                                tag_string = ' '.join(hashtags)
                                new_tags = st.text_input("Hashtags", tag_string, key=f"insta_post_{i}_hashtags")
                                if new_tags != tag_string:
                                    post['hashtags'] = new_tags.split() if new_tags else []
                                    changes_made = True
                else:
                    st.info("No Instagram posts generated")
            
            # ========== TAB 5: INSTAGRAM REELS ==========
            with tab5:
                st.markdown("### 🎞️ Instagram Reel Options")
                st.caption("7 reel concepts")
                
                reels = edited.get('instagram_reels', [])
                if reels and isinstance(reels, list):
                    for i, reel in enumerate(reels):
                        with st.expander(f"Instagram Reel {i+1}", expanded=i==0):
                            if isinstance(reel, dict):
                                new_concept = st.text_input("Concept", safe_get_str(reel, 'concept'), key=f"insta_reel_{i}_concept")
                                if new_concept != safe_get_str(reel, 'concept'):
                                    reel['concept'] = new_concept
                                    changes_made = True
                                
                                new_script = st.text_area("Script", safe_get_str(reel, 'script'), height=100, key=f"insta_reel_{i}_script")
                                if new_script != safe_get_str(reel, 'script'):
                                    reel['script'] = new_script
                                    changes_made = True
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    new_music = st.text_input("Music", safe_get_str(reel, 'music'), key=f"insta_reel_{i}_music")
                                    if new_music != safe_get_str(reel, 'music'):
                                        reel['music'] = new_music
                                        changes_made = True
                                with col2:
                                    new_duration = st.text_input("Duration", safe_get_str(reel, 'duration'), key=f"insta_reel_{i}_duration")
                                    if new_duration != safe_get_str(reel, 'duration'):
                                        reel['duration'] = new_duration
                                        changes_made = True
                else:
                    st.info("No Instagram reels generated")
            
            # ========== TAB 6: AMAZON ==========
            with tab6:
                st.markdown("### 🛒 Amazon Listing Options")
                st.caption("4 different Amazon page approaches")
                
                amazon_options = edited.get('amazon_options', [])
                if amazon_options and isinstance(amazon_options, list):
                    for i, amazon in enumerate(amazon_options):
                        with st.expander(f"Amazon Option {i+1}", expanded=i==0):
                            if isinstance(amazon, dict):
                                # A+ Content
                                if 'a_plus_content' in amazon and isinstance(amazon['a_plus_content'], dict):
                                    ap = amazon['a_plus_content']
                                    st.markdown("**A+ Content**")
                                    
                                    new_ap_title = st.text_input("Title", safe_get_str(ap, 'title'), key=f"amazon_ap_title_{i}")
                                    if new_ap_title != safe_get_str(ap, 'title'):
                                        ap['title'] = new_ap_title
                                        changes_made = True
                                    
                                    new_ap_desc = st.text_area("Description", safe_get_str(ap, 'description'), height=100, key=f"amazon_ap_desc_{i}")
                                    if new_ap_desc != safe_get_str(ap, 'description'):
                                        ap['description'] = new_ap_desc
                                        changes_made = True
                                    
                                    features = safe_get_list(ap, 'key_features')
                                    new_features = []
                                    for f_idx, feature in enumerate(features[:5]):
                                        new_feat = st.text_input(f"Feature {f_idx+1}", str(feature) if feature else "", key=f"amazon_feat_{i}_{f_idx}")
                                        new_features.append(new_feat)
                                        if new_feat != str(feature):
                                            changes_made = True
                                    ap['key_features'] = new_features
                                
                                # Search Terms
                                terms = safe_get_list(amazon, 'search_terms')
                                term_string = ', '.join(terms)
                                new_terms = st.text_input("Keywords (comma separated)", term_string, key=f"amazon_terms_{i}")
                                if new_terms != term_string:
                                    amazon['search_terms'] = [t.strip() for t in new_terms.split(',') if t.strip()]
                                    changes_made = True
                                
                                # Author Bio
                                new_bio = st.text_area("Author Bio", safe_get_str(amazon, 'author_bio'), height=150, key=f"amazon_bio_{i}")
                                if new_bio != safe_get_str(amazon, 'author_bio'):
                                    amazon['author_bio'] = new_bio
                                    changes_made = True
                else:
                    st.info("No Amazon options generated")
            
            # ========== TAB 7: FACEBOOK ADS ==========
            with tab7:
                st.markdown("### 📢 Facebook Ad Options")
                st.caption("6 ad variations for different audiences")
                
                ads = edited.get('facebook_ads', [])
                if ads and isinstance(ads, list):
                    for i, ad in enumerate(ads):
                        with st.expander(f"Facebook Ad {i+1}", expanded=i==0):
                            if isinstance(ad, dict):
                                new_audience = st.text_input("Audience", safe_get_str(ad, 'audience'), key=f"fb_ad_{i}_audience")
                                if new_audience != safe_get_str(ad, 'audience'):
                                    ad['audience'] = new_audience
                                    changes_made = True
                                
                                new_headline = st.text_input("Headline", safe_get_str(ad, 'headline'), key=f"fb_ad_{i}_headline")
                                if new_headline != safe_get_str(ad, 'headline'):
                                    ad['headline'] = new_headline
                                    changes_made = True
                                
                                new_text = st.text_area("Primary Text", safe_get_str(ad, 'primary_text'), height=100, key=f"fb_ad_{i}_text")
                                if new_text != safe_get_str(ad, 'primary_text'):
                                    ad['primary_text'] = new_text
                                    changes_made = True
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    new_desc = st.text_input("Description", safe_get_str(ad, 'description'), key=f"fb_ad_{i}_desc")
                                    if new_desc != safe_get_str(ad, 'description'):
                                        ad['description'] = new_desc
                                        changes_made = True
                                with col2:
                                    new_cta = st.text_input("CTA", safe_get_str(ad, 'cta'), key=f"fb_ad_{i}_cta")
                                    if new_cta != safe_get_str(ad, 'cta'):
                                        ad['cta'] = new_cta
                                        changes_made = True
                else:
                    st.info("No Facebook ads generated")
            
            # ========== TAB 8: EMAIL SEQUENCES ==========
            with tab8:
                st.markdown("### 📧 Email Sequence Options")
                st.caption("Complete email sequences")
                
                sequences = edited.get('email_sequences', [])
                if sequences and isinstance(sequences, list):
                    for seq_idx, sequence in enumerate(sequences):
                        seq_name = safe_get_str(sequence, 'name', f'Sequence {seq_idx+1}')
                        with st.expander(seq_name, expanded=seq_idx==0):
                            if isinstance(sequence, dict):
                                new_seq_name = st.text_input("Sequence Name", seq_name, key=f"seq_name_{seq_idx}")
                                if new_seq_name != seq_name:
                                    sequence['name'] = new_seq_name
                                    changes_made = True
                                
                                emails = safe_get_list(sequence, 'emails')
                                for email_idx, email in enumerate(emails):
                                    if isinstance(email, dict):
                                        st.markdown(f"**Email {email_idx+1}**")
                                        col1, col2 = st.columns([1, 3])
                                        with col1:
                                            new_subject = st.text_input("Subject", safe_get_str(email, 'subject'), key=f"email_{seq_idx}_{email_idx}_subject")
                                            if new_subject != safe_get_str(email, 'subject'):
                                                email['subject'] = new_subject
                                                changes_made = True
                                        with col2:
                                            new_body = st.text_area("Body", safe_get_str(email, 'body'), height=100, key=f"email_{seq_idx}_{email_idx}_body")
                                            if new_body != safe_get_str(email, 'body'):
                                                email['body'] = new_body
                                                changes_made = True
                else:
                    st.info("No email sequences generated")
            
            # ========== TAB 9: PRESS KITS ==========
            with tab9:
                st.markdown("### 📰 Press Kit Options")
                st.caption("3 press kit variations")
                
                press_options = edited.get('press_kit_options', [])
                if press_options and isinstance(press_options, list):
                    for i, press in enumerate(press_options):
                        with st.expander(f"Press Kit Option {i+1}", expanded=i==0):
                            if isinstance(press, dict):
                                new_release = st.text_area("Press Release", safe_get_str(press, 'press_release'), height=200, key=f"press_release_{i}")
                                if new_release != safe_get_str(press, 'press_release'):
                                    press['press_release'] = new_release
                                    changes_made = True
                                
                                points = safe_get_list(press, 'key_talking_points')
                                point_string = '\n'.join(points)
                                new_points = st.text_area("Key Talking Points (one per line)", point_string, height=100, key=f"press_points_{i}")
                                if new_points != point_string:
                                    press['key_talking_points'] = [p.strip() for p in new_points.split('\n') if p.strip()]
                                    changes_made = True
                else:
                    st.info("No press kit options generated")
            
            # ========== TAB 10: PINTEREST ==========
            with tab10:
                st.markdown("### 📌 Pinterest Options")
                st.caption("3 pin strategies")
                
                pinterest_options = edited.get('pinterest_options', [])
                if pinterest_options and isinstance(pinterest_options, list):
                    for i, pinterest in enumerate(pinterest_options):
                        with st.expander(f"Pinterest Option {i+1}", expanded=i==0):
                            if isinstance(pinterest, dict):
                                pins = safe_get_list(pinterest, 'pin_descriptions')
                                pin_string = '\n'.join(pins)
                                new_pins = st.text_area("Pin Descriptions (one per line)", pin_string, height=100, key=f"pinterest_pins_{i}")
                                if new_pins != pin_string:
                                    pinterest['pin_descriptions'] = [p.strip() for p in new_pins.split('\n') if p.strip()]
                                    changes_made = True
                else:
                    st.info("No Pinterest options generated")
            
            # ========== TAB 11: GOODREADS ==========
            with tab11:
                st.markdown("### 📚 Goodreads Options")
                st.caption("3 Goodreads strategies")
                
                goodreads_options = edited.get('goodreads_options', [])
                if goodreads_options and isinstance(goodreads_options, list):
                    for i, goodreads in enumerate(goodreads_options):
                        with st.expander(f"Goodreads Option {i+1}", expanded=i==0):
                            if isinstance(goodreads, dict):
                                new_giveaway = st.text_area("Giveaway Description", safe_get_str(goodreads, 'giveaway_description'), height=100, key=f"goodreads_giveaway_{i}")
                                if new_giveaway != safe_get_str(goodreads, 'giveaway_description'):
                                    goodreads['giveaway_description'] = new_giveaway
                                    changes_made = True
                                
                                questions = safe_get_list(goodreads, 'discussion_questions')
                                q_string = '\n'.join(questions)
                                new_qs = st.text_area("Discussion Questions (one per line)", q_string, height=100, key=f"goodreads_questions_{i}")
                                if new_qs != q_string:
                                    goodreads['discussion_questions'] = [q.strip() for q in new_qs.split('\n') if q.strip()]
                                    changes_made = True
                else:
                    st.info("No Goodreads options generated")
            
            # ========== TAB 12: PODCAST PITCHES ==========
            with tab12:
                st.markdown("### 🎙️ Podcast Pitch Options")
                st.caption("4 podcast pitch approaches")
                
                podcast_options = edited.get('podcast_pitches', [])
                if podcast_options and isinstance(podcast_options, list):
                    for i, podcast in enumerate(podcast_options):
                        with st.expander(f"Podcast Pitch {i+1}", expanded=i==0):
                            if isinstance(podcast, dict):
                                new_pitch = st.text_area("Pitch Email", safe_get_str(podcast, 'pitch_email'), height=200, key=f"podcast_email_{i}")
                                if new_pitch != safe_get_str(podcast, 'pitch_email'):
                                    podcast['pitch_email'] = new_pitch
                                    changes_made = True
                                
                                points = safe_get_list(podcast, 'talking_points')
                                point_string = '\n'.join(points)
                                new_points = st.text_area("Talking Points (one per line)", point_string, height=100, key=f"podcast_points_{i}")
                                if new_points != point_string:
                                    podcast['talking_points'] = [p.strip() for p in new_points.split('\n') if p.strip()]
                                    changes_made = True
                else:
                    st.info("No podcast pitches generated")
            
            # ========== TAB 13: LAUNCH TIMELINE ==========
            with tab13:
                st.markdown("### 📅 Launch Timeline")
                st.caption("Complete 5-phase launch plan")
                
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
                                new_items = []
                                for idx, item in enumerate(items):
                                    new_item = st.text_input(
                                        f"Step {idx+1}", 
                                        str(item) if item else "",
                                        key=f"timeline_{phase_key}_{idx}"
                                    )
                                    new_items.append(new_item)
                                    if new_item != str(item):
                                        changes_made = True
                                timeline[phase_key] = new_items
                else:
                    st.info("No launch timeline generated")
            
            # ========== AUTO-SAVE ==========
            if changes_made and book_title:
                auto_save_marketing_assets(
                    st.session_state.get('user_id', 1),
                    book_title,
                    edited
                )
            
            # ========== EXPORT BUTTON ==========
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                export_data = json.dumps(edited, indent=2)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{book_title.replace(' ', '_')}_assets_{timestamp}.json"
                
                st.download_button(
                    "📥 Export JSON",
                    export_data,
                    filename,
                    "application/json",
                    use_container_width=True
                )
            
            with col2:
                if st.button("🔄 Regenerate All", use_container_width=True):
                    st.session_state.generated_assets = None
                    st.session_state.edited_assets = None
                    st.session_state._assets_generated = False
                    st.rerun()
            
            st.markdown("---")
            st.caption("✨ AUTO-SAVE ACTIVE: All changes save to PostgreSQL database instantly")

def generate_marketing_assets(client, analysis_data):
    """Generate marketing assets"""
    
    book_info = extract_book_info(analysis_data)
    
    prompt = f"""
    Based on this book analysis, create comprehensive marketing assets.
    For EACH platform, generate MULTIPLE options.
    
    BOOK ANALYSIS:
    {json.dumps(book_info, indent=2)}
    
    Return JSON with these exact keys:
    - blurbs: array of 8 strings
    - tiktok_scripts: array of 8 objects with hook, visuals, voiceover, music, cta, hashtags
    - youtube_scripts: array of 6 objects with title, script, length, cta
    - instagram_posts: array of 8 objects with image_description, caption, hashtags
    - instagram_reels: array of 7 objects with concept, script, music, duration
    - amazon_options: array of 4 objects with a_plus_content, search_terms, author_bio
    - facebook_ads: array of 6 objects with audience, headline, primary_text, description, cta
    - email_sequences: array of 4 sequences with name and emails array
    - press_kit_options: array of 3 objects with press_release, key_talking_points
    - pinterest_options: array of 3 objects with pin_descriptions
    - goodreads_options: array of 3 objects with giveaway_description, discussion_questions
    - podcast_pitches: array of 4 objects with pitch_email, talking_points
    - launch_timeline: object with 6_weeks_before, 4_weeks_before, 2_weeks_before, launch_week, post_launch arrays
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a marketing expert. Return valid JSON only."},
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

if __name__ == "__main__":
    show_generator()

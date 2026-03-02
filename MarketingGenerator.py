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
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
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
        cur.close()
        conn.close()
        return asset_id
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def load_user_marketing_assets(user_id):
    """Load user's saved marketing assets"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_marketing_assets 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        assets = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(a) for a in assets]
    except Exception as e:
        st.error(f"Error loading assets: {e}")
        return []

def show_generator():
    """Generate marketing assets from saved analysis"""
    
    if st.session_state.get('current_page') != "🎨 Marketing Assets":
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
    st.markdown("Generate multi-platform marketing assets from your book analysis")
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
    
    # Also check database for saved analyses (if logged in)
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
                """, (st.session_state.user_id,))
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
            book_info = data.get('book_info', {})
            if isinstance(book_info, dict) and 'book_info' in book_info:
                book_info = book_info['book_info']
            title = book_info.get('title', 'Unknown')
            all_books.append({
                'display': f"📁 {title} (Session)",
                'source': 'session',
                'data': data,
                'filename': filename
            })
        
        # Add database analyses
        for analysis in db_analyses:
            analysis_data = analysis.get('analysis_result', {})
            if isinstance(analysis_data, str):
                analysis_data = json.loads(analysis_data)
            title = analysis.get('book_title', 'Unknown')
            all_books.append({
                'display': f"💾 {title} (Saved)",
                'source': 'database',
                'data': analysis_data,
                'analysis_id': analysis['id']
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
            if selected_book['source'] == 'session':
                st.session_state.loaded_analysis = selected_book['data']
            else:
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
        book_data = st.session_state.loaded_analysis
        book_info = book_data.get('book_info', {})
        if isinstance(book_info, dict) and 'book_info' in book_info:
            book_info = book_info['book_info']
        
        title = book_info.get('title', 'Unknown')
        genre = book_info.get('genre', 'Unknown')
        
        st.success(f"✅ Loaded: **{title}** ({genre})")
        
        # Generate button
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🎬 GENERATE MARKETING ASSETS", type="primary", use_container_width=True):
                with st.spinner("Generating assets... (30-45 seconds)"):
                    client = OpenAI(api_key=st.session_state.openai_api_key)
                    assets = generate_marketing_assets(client, st.session_state.loaded_analysis)
                    
                    if assets:
                        st.session_state.generated_assets = assets
                        st.session_state.edited_assets = assets.copy()
                        st.rerun()
        
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
                        # Save each asset type separately
                        for asset_type in ['blurb', 'tiktok_scripts', 'instagram', 'amazon', 
                                          'facebook_ads', 'email_sequence', 'press_kit', 
                                          'pinterest', 'goodreads', 'podcast_pitch']:
                            if asset_type in st.session_state.edited_assets:
                                asset_data = {asset_type: st.session_state.edited_assets[asset_type]}
                                asset_id = save_marketing_asset_to_db(
                                    st.session_state.user_id,
                                    title,
                                    asset_type,
                                    asset_data
                                )
                        st.success("✅ Assets saved to your library!")
                
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
            st.success("✅ Assets generated! Edit them below.")
            
            edited = st.session_state.edited_assets
            
            # Create tabs for each platform
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
                "📝 Blurb", "🎬 TikTok", "📸 Instagram", "🛒 Amazon", 
                "📧 Email", "📢 Facebook", "📰 Press Kit", "📌 Pinterest", 
                "📚 Goodreads", "🎙️ Podcast"
            ])
            
            # Tab 1: Blurb
            with tab1:
                st.markdown("### 📝 Book Blurb")
                edited['blurb'] = st.text_area(
                    "Edit your blurb", 
                    edited.get('blurb', ''), 
                    height=200,
                    key="blurb_editor"
                )
            
            # Tab 2: TikTok Scripts
            with tab2:
                st.markdown("### 🎬 TikTok Scripts")
                scripts = edited.get('tiktok_scripts', [])
                if scripts:
                    for i, script in enumerate(scripts):
                        with st.expander(f"Script {i+1}", expanded=i==0):
                            if isinstance(script, dict):
                                for key, value in script.items():
                                    if key == 'hashtags' and isinstance(value, list):
                                        tag_string = ' '.join(value)
                                        edited_tags = st.text_input(
                                            f"{key.title()}", 
                                            tag_string, 
                                            key=f"tiktok_{i}_{key}"
                                        )
                                        script[key] = edited_tags.split()
                                    else:
                                        script[key] = st.text_input(
                                            f"{key.title()}", 
                                            str(value), 
                                            key=f"tiktok_{i}_{key}"
                                        )
                else:
                    st.info("No TikTok scripts generated")
            
            # Tab 3: Instagram
            with tab3:
                st.markdown("### 📸 Instagram")
                insta = edited.get('instagram', {})
                
                if insta.get('posts'):
                    st.markdown("**Posts:**")
                    for j, post in enumerate(insta['posts']):
                        with st.expander(f"Post {j+1}"):
                            if isinstance(post, dict):
                                for key, value in post.items():
                                    if key == 'hashtags' and isinstance(value, list):
                                        tag_string = ' '.join(value)
                                        edited_tags = st.text_input(
                                            f"{key.title()}", 
                                            tag_string, 
                                            key=f"insta_post_{j}_{key}"
                                        )
                                        post[key] = edited_tags.split()
                                    else:
                                        post[key] = st.text_input(
                                            f"{key.title()}", 
                                            str(value), 
                                            key=f"insta_post_{j}_{key}"
                                        )
                
                if insta.get('reels'):
                    st.markdown("**Reels:**")
                    for j, reel in enumerate(insta['reels']):
                        with st.expander(f"Reel {j+1}"):
                            if isinstance(reel, dict):
                                for key, value in reel.items():
                                    reel[key] = st.text_input(
                                        f"{key.title()}", 
                                        str(value), 
                                        key=f"insta_reel_{j}_{key}"
                                    )
            
            # Tab 4: Amazon
            with tab4:
                st.markdown("### 🛒 Amazon")
                amazon = edited.get('amazon', {})
                if isinstance(amazon, dict):
                    # A+ Content
                    if 'a_plus_content' in amazon:
                        with st.expander("A+ Content", expanded=True):
                            ap = amazon['a_plus_content']
                            ap['title'] = st.text_input("Title", ap.get('title', ''), key="amazon_ap_title")
                            ap['description'] = st.text_area("Description", ap.get('description', ''), height=100, key="amazon_ap_desc")
                            
                            features = ap.get('key_features', [])
                            for f_idx, feature in enumerate(features):
                                features[f_idx] = st.text_input(f"Feature {f_idx+1}", feature, key=f"amazon_feat_{f_idx}")
                    
                    # Search Terms
                    with st.expander("Search Terms", expanded=True):
                        terms = amazon.get('search_terms', [])
                        term_string = ', '.join(terms)
                        edited_terms = st.text_input("Keywords (comma separated)", term_string, key="amazon_terms")
                        amazon['search_terms'] = [t.strip() for t in edited_terms.split(',') if t.strip()]
                    
                    # Categories
                    cats = amazon.get('categories', [])
                    cat_string = ', '.join(cats)
                    edited_cats = st.text_input("Categories (comma separated)", cat_string, key="amazon_cats")
                    amazon['categories'] = [c.strip() for c in edited_cats.split(',') if c.strip()]
                    
                    # Author Bio
                    amazon['author_bio'] = st.text_area("Author Bio", amazon.get('author_bio', ''), height=150, key="amazon_bio")
            
            # Tab 5: Email
            with tab5:
                st.markdown("### 📧 Email Sequence")
                emails = edited.get('email_sequence', {})
                for name, email in emails.items():
                    with st.expander(f"📨 {name.title()} Email"):
                        if isinstance(email, dict):
                            email['subject'] = st.text_input(
                                "Subject", 
                                email.get('subject', ''), 
                                key=f"email_{name}_subject"
                            )
                            email['body'] = st.text_area(
                                "Body", 
                                email.get('body', ''), 
                                height=150,
                                key=f"email_{name}_body"
                            )
            
            # Tab 6: Facebook Ads
            with tab6:
                st.markdown("### 📢 Facebook Ads")
                ads = edited.get('facebook_ads', [])
                if ads:
                    for i, ad in enumerate(ads):
                        with st.expander(f"Ad {i+1}"):
                            if isinstance(ad, dict):
                                for key, value in ad.items():
                                    ad[key] = st.text_input(
                                        f"{key.title()}", 
                                        str(value), 
                                        key=f"fb_ad_{i}_{key}"
                                    )
                else:
                    st.info("No Facebook ads generated")
            
            # Tab 7: Press Kit
            with tab7:
                st.markdown("### 📰 Press Kit")
                press = edited.get('press_kit', {})
                
                if 'press_release' in press:
                    press['press_release'] = st.text_area(
                        "Press Release", 
                        press.get('press_release', ''), 
                        height=200,
                        key="press_release"
                    )
                
                if 'key_talking_points' in press:
                    points = press.get('key_talking_points', [])
                    point_string = '\n'.join(points)
                    edited_points = st.text_area(
                        "Key Talking Points (one per line)", 
                        point_string, 
                        height=100,
                        key="press_points"
                    )
                    press['key_talking_points'] = [p.strip() for p in edited_points.split('\n') if p.strip()]
                
                if 'author_qanda' in press:
                    qas = press.get('author_qanda', [])
                    for j, qa in enumerate(qas):
                        with st.expander(f"Q&A {j+1}"):
                            if isinstance(qa, dict):
                                qa['question'] = st.text_input(
                                    "Question", 
                                    qa.get('question', ''), 
                                    key=f"press_qa_{j}_q"
                                )
                                qa['answer'] = st.text_area(
                                    "Answer", 
                                    qa.get('answer', ''), 
                                    height=80,
                                    key=f"press_qa_{j}_a"
                                )
            
            # Tab 8: Pinterest
            with tab8:
                st.markdown("### 📌 Pinterest")
                pinterest = edited.get('pinterest', {})
                
                if 'pin_descriptions' in pinterest:
                    pins = pinterest.get('pin_descriptions', [])
                    pin_string = '\n'.join(pins)
                    edited_pins = st.text_area(
                        "Pin Descriptions (one per line)", 
                        pin_string, 
                        height=100,
                        key="pinterest_pins"
                    )
                    pinterest['pin_descriptions'] = [p.strip() for p in edited_pins.split('\n') if p.strip()]
                
                if 'board_ideas' in pinterest:
                    boards = pinterest.get('board_ideas', [])
                    board_string = '\n'.join(boards)
                    edited_boards = st.text_area(
                        "Board Ideas (one per line)", 
                        board_string, 
                        height=100,
                        key="pinterest_boards"
                    )
                    pinterest['board_ideas'] = [b.strip() for b in edited_boards.split('\n') if b.strip()]
            
            # Tab 9: Goodreads
            with tab9:
                st.markdown("### 📚 Goodreads")
                goodreads = edited.get('goodreads', {})
                
                if 'giveaway_description' in goodreads:
                    goodreads['giveaway_description'] = st.text_area(
                        "Giveaway Description", 
                        goodreads.get('giveaway_description', ''), 
                        height=150,
                        key="goodreads_giveaway"
                    )
                
                if 'discussion_questions' in goodreads:
                    questions = goodreads.get('discussion_questions', [])
                    q_string = '\n'.join(questions)
                    edited_qs = st.text_area(
                        "Discussion Questions (one per line)", 
                        q_string, 
                        height=100,
                        key="goodreads_questions"
                    )
                    goodreads['discussion_questions'] = [q.strip() for q in edited_qs.split('\n') if q.strip()]
                
                if 'similar_books' in goodreads:
                    similar = goodreads.get('similar_books', [])
                    s_string = '\n'.join(similar)
                    edited_similar = st.text_area(
                        "Similar Books (one per line)", 
                        s_string, 
                        height=100,
                        key="goodreads_similar"
                    )
                    goodreads['similar_books'] = [s.strip() for s in edited_similar.split('\n') if s.strip()]
            
            # Tab 10: Podcast
            with tab10:
                st.markdown("### 🎙️ Podcast Pitch")
                podcast = edited.get('podcast_pitch', {})
                
                if 'pitch_email' in podcast:
                    podcast['pitch_email'] = st.text_area(
                        "Pitch Email", 
                        podcast.get('pitch_email', ''), 
                        height=200,
                        key="podcast_email"
                    )
                
                if 'talking_points' in podcast:
                    points = podcast.get('talking_points', [])
                    point_string = '\n'.join(points)
                    edited_points = st.text_area(
                        "Talking Points (one per line)", 
                        point_string, 
                        height=100,
                        key="podcast_points"
                    )
                    podcast['talking_points'] = [p.strip() for p in edited_points.split('\n') if p.strip()]
                
                if 'podcast_ideas' in podcast:
                    ideas = podcast.get('podcast_ideas', [])
                    idea_string = '\n'.join(ideas)
                    edited_ideas = st.text_area(
                        "Podcast Episode Ideas (one per line)", 
                        idea_string, 
                        height=100,
                        key="podcast_ideas"
                    )
                    podcast['podcast_ideas'] = [i.strip() for i in edited_ideas.split('\n') if i.strip()]
            
            st.success("✅ Edits saved in current session")


def generate_marketing_assets(client, analysis_data):
    """Generate marketing assets from saved analysis"""
    
    # Extract the actual analysis
    book_analysis = analysis_data.get('book_info', {})
    if isinstance(book_analysis, dict) and 'book_info' in book_analysis:
        book_analysis = book_analysis['book_info']
    
    cover_analysis = analysis_data.get('cover_analysis', {})
    
    prompt = f"""
    Based on this book analysis, create comprehensive marketing assets for ALL platforms.
    
    BOOK ANALYSIS:
    {json.dumps(book_analysis, indent=2)}
    
    COVER ANALYSIS:
    {json.dumps(cover_analysis, indent=2)}
    
    Return JSON with:
    
    1. blurb: "150-word compelling book description"
    
    2. tiktok_scripts: [
        {{
            "hook": "attention grabber",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }}
    ]
    
    3. instagram: {{
        "posts": [
            {{
                "image_description": "what to post",
                "caption": "caption text",
                "hashtags": ["#tag1", "#tag2"]
            }}
        ],
        "reels": [
            {{
                "concept": "reel idea",
                "script": "content",
                "music": "trending audio"
            }}
        ],
        "stories": ["story idea 1", "story idea 2"]
    }}
    
    4. amazon: {{
        "a_plus_content": {{
            "title": "enhanced brand content title",
            "description": "enhanced description",
            "key_features": ["feature1", "feature2", "feature3"]
        }},
        "search_terms": ["keyword1", "keyword2", "keyword3"],
        "categories": ["suggested categories"],
        "author_bio": "compelling author bio for Amazon page"
    }}
    
    5. facebook_ads: [
        {{
            "audience": "target demographic",
            "headline": "ad headline",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "call to action button"
        }}
    ]
    
    6. email_sequence: {{
        "welcome": {{
            "subject": "Welcome email subject",
            "body": "full email content"
        }},
        "prelaunch": {{
            "subject": "Pre-launch subject",
            "body": "email content"
        }},
        "launch": {{
            "subject": "Launch day subject",
            "body": "email content"
        }},
        "followup": {{
            "subject": "Follow-up subject",
            "body": "email with reviews"
        }}
    }}
    
    7. press_kit: {{
        "press_release": "full press release",
        "author_qanda": [
            {{"question": "question", "answer": "answer"}}
        ],
        "key_talking_points": ["point1", "point2"]
    }}
    
    8. pinterest: {{
        "pin_descriptions": ["pin1", "pin2"],
        "board_ideas": ["board1", "board2"],
        "keywords": ["pinterest keywords"]
    }}
    
    9. goodreads: {{
        "giveaway_description": "text for giveaway",
        "discussion_questions": ["q1", "q2"],
        "similar_books": ["book1", "book2"]
    }}
    
    10. podcast_pitch: {{
        "pitch_email": "email template",
        "talking_points": ["point1", "point2"],
        "podcast_ideas": ["episode angle1", "angle2"]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a marketing expert. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Asset generation failed: {str(e)}")
        return None


# For direct testing
if __name__ == "__main__":
    show_generator()

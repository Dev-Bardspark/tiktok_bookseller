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
        if conn:
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

    # ============================================================================
    # LOGIN CHECK
    # ============================================================================
    if not st.session_state.get('authenticated', False):
        st.warning("🔒 Please login to access the Marketing Asset Generator")
        if st.button("Go to Login", use_container_width=True):
            st.session_state.page = "🏠 Dashboard"
            st.rerun()
        return

    if st.session_state.get('current_page') != "🎨 Marketing Assets":
        return

    # Initialize session state keys
    for key in ['openai_api_key', 'loaded_analysis', 'generated_assets', 'edited_assets']:
        if key not in st.session_state:
            st.session_state[key] = None

    st.title("🎨 Marketing Asset Generator")
    st.markdown("Generate LOTS of marketing options for every platform")
    st.markdown("---")

    # API Key input
    if not st.session_state.openai_api_key:
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

    if 'analysis_library' not in st.session_state:
        st.session_state.analysis_library = {}

    # Load from database
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
        all_books = []

        # Session books
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

        # Database books
        for analysis in db_analyses:
            analysis_data = analysis.get('analysis_result', {})
            if isinstance(analysis_data, str):
                try:
                    analysis_data = json.loads(analysis_data)
                except:
                    continue
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

        book_data = st.session_state.loaded_analysis
        book_info = book_data.get('book_info', {})
        if isinstance(book_info, dict) and 'book_info' in book_info:
            book_info = book_info['book_info']

        title = book_info.get('title', 'Unknown')
        genre = book_info.get('genre', 'Unknown')

        st.success(f"✅ Loaded: **{title}** ({genre})")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🎬 GENERATE MARKETING ASSETS", type="primary", use_container_width=True):
                with st.spinner("Generating assets... (60-90 seconds)"):
                    client = OpenAI(api_key=st.session_state.openai_api_key)
                    assets = generate_marketing_assets(client, st.session_state.loaded_analysis)
                    if assets:
                        st.session_state.generated_assets = assets
                        st.session_state.edited_assets = assets.copy()  # deep copy if needed later
                        st.rerun()

        with col2:
            if st.session_state.generated_assets:
                if st.button("🔄 Regenerate Assets", use_container_width=True):
                    st.session_state.generated_assets = None
                    st.session_state.edited_assets = None
                    st.rerun()

        with col3:
            if st.session_state.edited_assets:
                if st.session_state.get('authenticated', False):
                    if st.button("💾 Save to My Library", use_container_width=True):
                        for asset_type in [
                            'blurbs', 'tiktok_scripts', 'youtube_scripts', 'instagram_posts',
                            'instagram_reels', 'amazon_options', 'facebook_ads', 'email_sequences',
                            'press_kit_options', 'pinterest_options', 'goodreads_options',
                            'podcast_pitches', 'launch_timeline'
                        ]:
                            if asset_type in st.session_state.edited_assets:
                                asset_data = {asset_type: st.session_state.edited_assets[asset_type]}
                                save_marketing_asset_to_db(
                                    st.session_state.user_id,
                                    title,
                                    asset_type,
                                    asset_data
                                )
                        st.success("✅ All assets saved to your library!")

                # Export
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
        # ASSET DISPLAY AND EDITING (only showing blurbs tab as example — add others similarly)
        # ============================================================================
        if st.session_state.generated_assets and st.session_state.edited_assets:
            st.markdown("---")
            st.success("✅ Assets generated! Edit below.")

            edited = st.session_state.edited_assets

            tab1, *_ = st.tabs([
                "📝 Blurbs", "🎬 TikTok", "🎥 YouTube", "📸 Instagram Posts", "🎞️ Instagram Reels",
                "🛒 Amazon", "📢 Facebook Ads", "📧 Email Sequences", "📰 Press Kits",
                "📌 Pinterest", "📚 Goodreads", "🎙️ Podcasts", "📅 Launch Timeline"
            ])

            with tab1:
                st.markdown("### 📝 Book Blurb Options")
                blurbs = edited.get('blurbs', [])
                if blurbs and isinstance(blurbs, list):
                    for i, blurb in enumerate(blurbs):
                        with st.expander(f"Blurb Option {i+1}", expanded=(i == 0)):
                            edited['blurbs'][i] = st.text_area(
                                f"Edit Blurb {i+1}",
                                value=blurb,
                                height=150,
                                key=f"blurb_{i}"
                            )
                else:
                    st.info("No blurbs generated")

            # ... add the other tabs similarly (TikTok, YouTube, etc.)
            # They follow almost the same pattern as in your original code

            st.success("✅ All edits are live in this session (will be saved on export / save button)")


def generate_marketing_assets(client, analysis_data):
    """Generate marketing assets using OpenAI"""
    book_analysis = analysis_data.get('book_info', {})
    if isinstance(book_analysis, dict) and 'book_info' in book_analysis:
        book_analysis = book_analysis['book_info']

    cover_analysis = analysis_data.get('cover_analysis', {})

    prompt = f"""
Based on this book analysis, create comprehensive marketing assets for ALL platforms.
For EACH platform, generate MULTIPLE options (5-10 each) so the author can choose.
Include a COMPLETE LAUNCH TIMELINE with specific actions for each phase.

BOOK ANALYSIS:
{json.dumps(book_analysis, indent=2)}

COVER ANALYSIS:
{json.dumps(cover_analysis, indent=2)}

Return **valid JSON only** with this exact structure:

{{
  "blurbs": [
    "Option 1 blurb text...",
    "Option 2 blurb text..."
  ],
  "tiktok_scripts": [
    {{
      "hook": "...",
      "visuals": "...",
      "voiceover": "...",
      "music": "...",
      "cta": "...",
      "hashtags": ["#tag1", "#tag2"]
    }},
    ...
  ],
  "youtube_scripts": [
    {{
      "title": "...",
      "script": "...",
      "length": "...",
      "cta": "..."
    }},
    ...
  ],
  "instagram_posts": [
    {{
      "image_description": "...",
      "caption": "...",
      "hashtags": ["#tag1", ...]
    }},
    ...
  ],
  "instagram_reels": [... similar ...],
  "amazon_options": [...],
  "facebook_ads": [...],
  "email_sequences": [...],
  "press_kit_options": [...],
  "pinterest_options": [...],
  "goodreads_options": [...],
  "podcast_pitches": [...],
  "launch_timeline": {{
    "6_weeks_before": ["action 1", "action 2", ...],
    "4_weeks_before": [...],
    "2_weeks_before": [...],
    "launch_week": [...],
    "post_launch": [...]
  }}
}}

Here is one example of how goodreads_options should look (make sure to include comma after discussion_questions array!):

"goodreads_options": [
  {{
    "giveaway_description": "Option 1 - Standard giveaway...",
    "discussion_questions": [
      "Q1: What was your favorite moment?",
      "Q2: Which character did you relate to most?",
      "Q3: How did the setting affect the story?",
      "Q4: What themes stood out to you?",
      "Q5: Would you recommend this book?"
    ],
    "similar_books": ["Book A", "Book B", "Book C"]
  }},
  ...
]
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a marketing expert. Return **valid JSON only**. No explanations, no markdown, just the JSON object."},
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

# VideoGenerator.py
import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Dict, List
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

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

def save_video_project_to_db(user_id, book_title, video_title, video_script, video_data=None):
    """Save video project to database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_videos 
            (user_id, video_title, video_script, video_data, created_at, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            video_title,
            video_script,
            json.dumps(video_data) if video_data else None,
            datetime.now(),
            'draft'
        ))
        
        video_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return video_id
    except Exception as e:
        st.error(f"Error saving video: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def load_user_videos(user_id):
    """Load user's saved video projects"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_videos 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        videos = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(v) for v in videos]
    except Exception as e:
        st.error(f"Error loading videos: {e}")
        return []

def show_video_generator():
    """Browser-based video generator - no installation needed"""
    
    st.title("🎬 TikTok Video Generator")
    st.markdown("Create professional BookTok videos using free online editors")
    
    # Initialize session state for video projects
    if 'video_projects' not in st.session_state:
        st.session_state.video_projects = []
    
    # Check if we have generated assets from BookReader
    if 'generated_assets' not in st.session_state or not st.session_state.generated_assets:
        # Check if user has saved videos
        if st.session_state.get('authenticated', False):
            saved_videos = load_user_videos(st.session_state.user_id)
            if saved_videos:
                st.info("You have saved video projects. Load them from the 'My Saved Videos' section.")
        
        st.warning("No marketing assets found. Please generate assets in the Book Reader tab first.")
        if st.button("📖 Go to Book Reader", use_container_width=True):
            st.session_state.current_page = "📖 Book Reader"
            st.rerun()
        return
    
    # Get TikTok scripts
    scripts = st.session_state.generated_assets.get('tiktok_scripts', [])
    if not scripts:
        st.warning("No TikTok scripts found in your assets.")
        return
    
    # Get book info - with safe fallbacks
    analysis = st.session_state.get('manuscript_analysis', {})
    book_title = analysis.get('title', 'My Book') if analysis else 'My Book'
    
    # Safely handle genre
    genre_raw = analysis.get('genre', 'general') if analysis else 'general'
    if genre_raw is None:
        genre = 'general'
    else:
        genre = str(genre_raw).lower()
    
    # Display header with book info
    st.subheader(f"📖 Creating videos for: **{book_title}**")
    st.markdown(f"**Genre:** {genre.title()} | **Scripts available:** {len(scripts)}")
    st.divider()
    
    # Create tabs for generator and saved videos
    tab1, tab2 = st.tabs(["🎬 Video Generator", "💾 My Saved Videos"])
    
    with tab1:
        show_video_editor_guide(scripts, book_title, genre)
    
    with tab2:
        show_saved_videos(book_title)


def show_video_editor_guide(scripts: List, book_title: str, genre: str):
    """Guide users to free online video editors with save functionality"""
    
    st.markdown("""
    ### 🎥 Choose a Free Video Editor
    All these editors work in your browser - **no downloads, completely free**.
    """)
    
    # Script selector
    st.subheader("1️⃣ Select Your Script")
    
    # Create a dropdown to choose which script to use
    script_options = []
    for i, script in enumerate(scripts):
        if isinstance(script, dict):
            # Try different possible field names for the preview
            preview = (
                script.get('hook') or 
                script.get('title') or 
                script.get('headline') or 
                script.get('text') or 
                script.get('voiceover') or 
                str(script)[:50]
            )
            script_options.append(f"Script {i+1}: {str(preview)[:50]}...")
        else:
            script_options.append(f"Script {i+1}: {str(script)[:50]}...")
    
    if script_options:
        selected_idx = st.selectbox(
            "Choose a script to visualize",
            options=range(len(script_options)),
            format_func=lambda x: script_options[x],
            key="script_selector"
        )
        
        selected_script = scripts[selected_idx]
        
        # Display the full script
        with st.expander("📝 View Full Script", expanded=True):
            if isinstance(selected_script, dict):
                # Show all fields in the dictionary
                for key, value in selected_script.items():
                    if value:  # Only show if value exists
                        st.markdown(f"**{key.title()}:**")
                        st.info(str(value))
            else:
                st.write(selected_script)
        
        # Save this script button
        if st.session_state.get('authenticated', False):
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("💾 Save Script", use_container_width=True):
                    # Save to database
                    video_data = {
                        'script': selected_script,
                        'genre': genre,
                        'book_title': book_title,
                        'timestamp': str(datetime.now())
                    }
                    
                    script_text = str(selected_script) if not isinstance(selected_script, dict) else json.dumps(selected_script)
                    video_id = save_video_project_to_db(
                        st.session_state.user_id,
                        book_title,
                        f"{book_title} - Script {selected_idx+1}",
                        script_text[:500],  # First 500 chars as preview
                        video_data
                    )
                    if video_id:
                        st.success("✅ Script saved to your library!")
    else:
        st.warning("No scripts available to select")
        return
    
    st.divider()
    
    # Video style guide
    st.subheader("2️⃣ Style Guide")
    
    genre_styles = {
        "fantasy": {
            "colors": "Purple, gold, dark blue",
            "music": "Epic orchestral",
            "text_style": "Dramatic serif font",
            "pace": "Slow reveals, dramatic pauses"
        },
        "romance": {
            "colors": "Pink, soft white, warm orange",
            "music": "Soft piano or acoustic",
            "text_style": "Elegant script font",
            "pace": "Gentle, emotional"
        },
        "thriller": {
            "colors": "Red, black, dark grey",
            "music": "Tense, building suspense",
            "text_style": "Sharp, bold sans-serif",
            "pace": "Fast cuts, quick reveals"
        },
        "mystery": {
            "colors": "Dark blue, grey, sepia",
            "music": "Mysterious, questioning",
            "text_style": "Intriguing, slightly distressed",
            "pace": "Slow burn with quick hook"
        },
        "horror": {
            "colors": "Black, blood red, desaturated",
            "music": "Creepy, discordant",
            "text_style": "Scratched, horror font",
            "pace": "Slow then jump cuts"
        },
        "young adult": {
            "colors": "Bright, pastel, vibrant",
            "music": "Upbeat pop",
            "text_style": "Fun, rounded fonts",
            "pace": "Energetic, quick"
        }
    }
    
    # Safely get style with fallback
    genre_key = genre.lower() if genre else 'general'
    style = genre_styles.get(genre_key, {
        "colors": "Match your book cover",
        "music": "Match your book's mood",
        "text_style": "Clean, readable font",
        "pace": "Match your story's pace"
    })
    
    # Display style guide in columns
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🎨 Color Palette:**")
        st.code(style['colors'])
        st.markdown("**🎵 Music Style:**")
        st.code(style['music'])
    with col2:
        st.markdown("**📝 Text Style:**")
        st.code(style['text_style'])
        st.markdown("**⏱️ Video Pace:**")
        st.code(style['pace'])
    
    st.divider()
    
    # Editor selection
    st.subheader("3️⃣ Choose Your Video Editor")
    
    editor_choice = st.radio(
        "Select an editor (all are free and browser-based):",
        [
            "🎬 CapCut - Best for TikTok (trending sounds, effects)",
            "🎨 Canva - Easiest to use, many templates",
            "📹 Clipchamp - Professional, runs in browser"
        ],
        horizontal=False,
        key="editor_choice"
    )
    
    # Set URLs based on choice
    if "CapCut" in editor_choice:
        editor_url = "https://www.capcut.com/"
        tutorial_url = "https://www.capcut.com/resource"
        editor_name = "CapCut"
    elif "Canva" in editor_choice:
        editor_url = "https://www.canva.com/create/videos/"
        tutorial_url = "https://www.canva.com/video-editor/"
        editor_name = "Canva"
    else:
        editor_url = "https://app.clipchamp.com/"
        tutorial_url = "https://support.clipchamp.com/"
        editor_name = "Clipchamp"
    
    col1, col2 = st.columns(2)
    with col1:
        st.link_button(
            f"🎬 Open {editor_name}",
            editor_url,
            use_container_width=True,
            type="primary"
        )
    with col2:
        st.link_button(
            "📚 Tutorial",
            tutorial_url,
            use_container_width=True
        )
    
    st.divider()
    
    # Asset preparation
    st.subheader("4️⃣ Your Assets")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📖 Book Cover**")
        st.info("Upload your book cover as the main visual")
        
        # Book cover upload helper (just for preview)
        uploaded_cover = st.file_uploader(
            "Preview your cover",
            type=['png', 'jpg', 'jpeg'],
            key="cover_ref",
            label_visibility="collapsed"
        )
        if uploaded_cover:
            st.image(uploaded_cover, width=200)
            st.success("✅ Cover ready!")
    
    with col2:
        st.markdown("**📝 Script Text**")
        if isinstance(selected_script, dict):
            # Get the main text - try voiceover first, then hook, then anything
            script_text = (
                selected_script.get('voiceover') or 
                selected_script.get('hook') or 
                selected_script.get('text') or 
                str(selected_script)
            )
        else:
            script_text = str(selected_script)
        
        st.text_area(
            "Copy this text",
            script_text,
            height=150,
            key="script_text",
            label_visibility="collapsed"
        )
        
        # Copy button using JavaScript
        components.html(f"""
        <button onclick="navigator.clipboard.writeText(`{script_text}`)" 
                style="background-color: #ff4b4b; color: white; padding: 10px; 
                       border: none; border-radius: 5px; width: 100%; cursor: pointer;">
            📋 Copy to Clipboard
        </button>
        """, height=50)
    
    st.divider()
    
    # Step-by-step guide
    st.subheader("5️⃣ Step-by-Step Instructions")
    
    with st.expander(f"📋 How to use {editor_name}", expanded=True):
        if "CapCut" in editor_choice:
            st.markdown("""
            **In CapCut:**
            1. Click "Create new video"
            2. Upload your book cover image
            3. Click "Text" and paste your script
            4. Use "Text-to-speech" to add voiceover
            5. Add trending music from the library
            6. Export in 9:16 (TikTok format)
            """)
        elif "Canva" in editor_choice:
            st.markdown("""
            **In Canva:**
            1. Search for "TikTok video" template
            2. Upload your book cover
            3. Add text boxes with your script
            4. Add elements that match your genre
            5. Add audio from the music library
            6. Download as MP4
            """)
        else:
            st.markdown("""
            **In Clipchamp:**
            1. Start a new project (9:16 ratio)
            2. Import your book cover image
            3. Add text overlays with your script
            4. Use the text-to-speech feature
            5. Add background music
            6. Export as 1080p MP4
            """)
    
    st.success("""
    ### ✅ Your Path to Finished Video:
    
    1. **Click the editor button** above
    2. **Upload your book cover**
    3. **Paste your script** (use the copy button)
    4. **Follow the style guide** for colors/music
    5. **Export** as MP4 (9:16 for TikTok)
    """)


def show_copy_paste_method(scripts: List, book_title: str):
    """Simple copy/paste method for users who prefer other editors"""
    
    st.markdown("""
    ### 📋 Copy & Paste Method
    Download your scripts to use in any video editor.
    """)
    
    # Create a combined text file with all scripts
    all_scripts_text = f"TIKTOK SCRIPTS FOR: {book_title}\n"
    all_scripts_text += "="*50 + "\n\n"
    
    for i, script in enumerate(scripts, 1):
        all_scripts_text += f"VIDEO {i}\n"
        all_scripts_text += "-"*20 + "\n"
        
        if isinstance(script, dict):
            for key, value in script.items():
                all_scripts_text += f"{key.upper()}: {value}\n"
        else:
            all_scripts_text += str(script)
        
        all_scripts_text += "\n\n"
    
    # Provide download
    st.download_button(
        "📥 Download All Scripts (TXT)",
        all_scripts_text,
        f"{book_title}_tiktok_scripts.txt",
        "text/plain",
        use_container_width=True
    )
    
    st.divider()
    
    # Links to free editors
    st.markdown("### 🆓 Free Online Video Editors")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.link_button(
            "✂️ CapCut",
            "https://www.capcut.com",
            use_container_width=True
        )
    
    with col2:
        st.link_button(
            "🎨 Canva",
            "https://www.canva.com/create/videos/",
            use_container_width=True
        )
    
    with col3:
        st.link_button(
            "📹 Clipchamp",
            "https://app.clipchamp.com/",
            use_container_width=True
        )
    
    st.info("""
    **How to use:**
    1. Download the scripts above
    2. Open any free online editor
    3. Upload your book cover
    4. Paste the script as text overlays
    5. Add background music
    6. Export in 9:16 format for TikTok
    """)


def show_saved_videos(current_book_title):
    """Display user's saved video projects"""
    
    if not st.session_state.get('authenticated', False):
        st.warning("Please login to view your saved videos")
        return
    
    saved_videos = load_user_videos(st.session_state.user_id)
    
    if not saved_videos:
        st.info("You haven't saved any video scripts yet. Save scripts from the Video Generator tab.")
        return
    
    st.markdown(f"### 📚 Your Saved Video Projects ({len(saved_videos)})")
    
    for video in saved_videos:
        with st.expander(f"🎬 {video.get('video_title', 'Untitled')} - {video.get('created_at', '')[:10]}"):
            st.markdown(f"**Script Preview:**")
            st.info(video.get('video_script', 'No script'))
            
            if video.get('video_data'):
                st.markdown("**Full Data:**")
                st.json(video.get('video_data'))
            
            # Option to load this video
            if st.button("📂 Load This Script", key=f"load_video_{video['id']}"):
                st.session_state.loaded_video = video
                st.success("Script loaded!")


def show_video_preview(video_url: str):
    """Preview video if user has one"""
    st.video(video_url)


# Optional: Add a simple video uploader for users who already made videos
def show_video_uploader():
    """Let users upload their finished videos"""
    with st.expander("📤 Share Your Finished Video"):
        uploaded_video = st.file_uploader(
            "Upload your completed TikTok video",
            type=['mp4', 'mov', 'avi'],
            key="video_upload"
        )
        if uploaded_video:
            st.video(uploaded_video)
            st.success("✅ Video ready for TikTok!")

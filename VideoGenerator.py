# VideoGenerator.py
import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Dict, List
import time

def show_video_generator():
    """Browser-based video generator using OpenReel - no installation needed"""
    
    st.title("🎬 TikTok Video Generator")
    st.markdown("Create professional BookTok videos directly in your browser - **no software to install**")
    
    # Check if we have generated assets from BookReader
    if 'generated_assets' not in st.session_state or not st.session_state.generated_assets:
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
    
    # FIX: Safely handle genre - it might be None or not a string
    genre_raw = analysis.get('genre', 'general') if analysis else 'general'
    if genre_raw is None:
        genre = 'general'
    else:
        genre = str(genre_raw).lower()
    
    # Display header with book info
    st.subheader(f"📖 Creating videos for: **{book_title}**")
    st.markdown(f"**Genre:** {genre.title()} | **Scripts available:** {len(scripts)}")
    st.divider()
    
    # Create tabs for different approaches
    tab1, tab2 = st.tabs(["🎬 OpenReel Editor (Recommended)", "📋 Copy/Paste Method"])
    
    with tab1:
        show_openreel_integration(scripts, book_title, genre)
    
    with tab2:
        show_copy_paste_method(scripts, book_title)


def show_openreel_integration(scripts: List, book_title: str, genre: str):
    """Embed OpenReel video editor directly in Streamlit"""
    
    st.markdown("""
    ### 🎥 OpenReel Video Editor
    OpenReel runs entirely in your browser - **no uploads, no installations, completely free**.
    """)
    
    # Script selector
    st.subheader("1️⃣ Select Your Script")
    
    # Create a dropdown to choose which script to use
    script_options = []
    for i, script in enumerate(scripts):
        if isinstance(script, dict):
            hook = script.get('hook', 'No hook')[:50]
            script_options.append(f"Script {i+1}: {hook}...")
        else:
            script_options.append(f"Script {i+1}")
    
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
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Hook:**")
                    st.info(selected_script.get('hook', 'N/A'))
                    st.markdown("**Visuals:**")
                    st.write(selected_script.get('visuals', 'N/A'))
                with col2:
                    st.markdown("**Voiceover:**")
                    st.info(selected_script.get('voiceover', 'N/A'))
                    st.markdown("**Music:**")
                    st.write(selected_script.get('music', 'N/A'))
                st.markdown(f"**CTA:** {selected_script.get('cta', 'N/A')}")
            else:
                st.write(selected_script)
    else:
        st.warning("No scripts available to select")
        return
    
    st.divider()
    
    # Video style guide
    st.subheader("2️⃣ Style Guide (Copy These Settings)")
    
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
    
    # FIX: Safely get style with fallback
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
    
    # OpenReel integration
    st.subheader("3️⃣ Open Video Editor")
    
    st.markdown("""
    Click the button below to open OpenReel - a professional video editor that runs entirely in your browser:
    
    ✨ **Features you can use:**
    - Add text overlays with your hook and CTA
    - Upload your book cover as the main visual
    - Choose background music that matches your genre
    - Add transitions between scenes
    - Export in 9:16 TikTok format
    """)
    
    # Direct link to OpenReel
    col1, col2 = st.columns(2)
    with col1:
        st.link_button(
            "🎬 Open OpenReel Editor",
            "https://www.openreel.com/",
            use_container_width=True,
            type="primary"
        )
    
    with col2:
        st.link_button(
            "📚 OpenReel Tutorial",
            "https://www.openreel.com/resources",
            use_container_width=True
        )
    
    st.divider()
    
    # Asset preparation
    st.subheader("4️⃣ Assets to Use")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📖 Cover Image**")
        st.info("Upload your book cover as the main visual")
        
        # Book cover upload helper
        uploaded_cover = st.file_uploader(
            "Your book cover (for reference)",
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
            script_text = selected_script.get('voiceover', '') or selected_script.get('hook', '')
        else:
            script_text = str(selected_script)
        
        st.text_area(
            "Copy this text",
            script_text,
            height=150,
            key="script_text",
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # Success path
    st.success("""
    ### ✅ Your 5-Step Path to Finished Video:
    
    1. **Click OpenReel Editor** above
    2. **Upload your book cover** as the main image
    3. **Paste your script** from the box above
    4. **Follow the style guide** for colors and music
    5. **Export** as MP4 (9:16 for TikTok)
    
    All processing happens in your browser - no files leave your computer!
    """)


def show_copy_paste_method(scripts: List, book_title: str):
    """Simple copy/paste method for users who prefer other editors"""
    
    st.markdown("""
    ### 📋 Copy & Paste Method
    Use this if you prefer CapCut or another video editor.
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
            "✂️ CapCut Online",
            "https://www.capcut.com",
            use_container_width=True
        )
    
    with col2:
        st.link_button(
            "🎬 Canva",
            "https://www.canva.com",
            use_container_width=True
        )
    
    with col3:
        st.link_button(
            "📱 Clipchamp",
            "https://clipchamp.com",
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

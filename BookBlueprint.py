# BookBlueprint.py
import streamlit as st
from openai import OpenAI
import PyPDF2
import docx
import json
import time
from typing import Optional, Dict, List, Any
from datetime import datetime
import plotly.express as px
import pandas as pd
from PIL import Image
import io
import base64

def show_blueprint_analyzer():
    """Main Book Marketing Blueprint Analyzer"""
    
    # Check if we're on the correct page
    if st.session_state.get('current_page') != "📖 Book Blueprint":
        return
    
    # Inherit API key from main app
    if 'openai_api_key' in st.session_state and st.session_state.openai_api_key:
        st.session_state.api_configured = True
    else:
        st.session_state.api_configured = False
    
    # Initialize session state
    if 'blueprint' not in st.session_state:
        st.session_state.blueprint = None
    
    if 'blueprint_stage' not in st.session_state:
        st.session_state.blueprint_stage = "upload"
    
    # Header
    st.title("📖 Book Marketing Blueprint")
    st.markdown("""
    <style>
    .blueprint-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="blueprint-header"><h2>Your Complete Marketing Roadmap</h2><p>Upload your manuscript and cover. Get a 360° marketing strategy tailored to YOUR book.</p></div>', unsafe_allow_html=True)
    
    # API Configuration (only if not already configured)
    if not st.session_state.api_configured:
        with st.expander("🔑 API Settings", expanded=True):
            api_key = st.text_input("OpenAI API Key", type="password", key="blueprint_api_key", 
                                   value=st.session_state.get('openai_api_key', ''))
            if api_key and st.button("Connect", key="blueprint_connect"):
                st.session_state.openai_api_key = api_key
                st.session_state.api_configured = True
                st.rerun()
        return
    
    # Progress tracker
    stages = ["upload", "analyzing", "results"]
    stage_names = ["📤 Upload", "⚙️ Analysis", "🎯 Blueprint"]
    current_idx = stage_names.index(stage_names[stages.index(st.session_state.blueprint_stage)]) if st.session_state.blueprint_stage in stages else 0
    
    cols = st.columns(3)
    for i, (col, stage_name) in enumerate(zip(cols, stage_names)):
        with col:
            if i < current_idx:
                st.success(f"✅ {stage_name}")
            elif i == current_idx:
                st.info(f"⏳ {stage_name}")
            else:
                st.write(f"⚪ {stage_name}")
    
    st.divider()
    
    # Route to appropriate stage
    if st.session_state.blueprint_stage == "upload":
        show_upload_stage()
    elif st.session_state.blueprint_stage == "analyzing":
        show_analyzing_stage()
    elif st.session_state.blueprint_stage == "results":
        show_blueprint_results()


def show_upload_stage():
    """Stage 1: Upload manuscript and cover"""
    
    st.subheader("📤 Upload Your Book Materials")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📄 Manuscript")
        manuscript_file = st.file_uploader(
            "Upload manuscript (PDF, DOCX, TXT)",
            type=['pdf', 'docx', 'txt'],
            key="blueprint_manuscript",
            help="Your complete book text"
        )
        
        if manuscript_file:
            st.success(f"✅ Loaded: {manuscript_file.name}")
            
            with st.expander("Preview"):
                text = extract_text_preview(manuscript_file)
                st.text(text[:500] + "..." if len(text) > 500 else text)
    
    with col2:
        st.markdown("### 🎨 Cover Image")
        cover_file = st.file_uploader(
            "Upload cover image (JPG, PNG)",
            type=['jpg', 'jpeg', 'png'],
            key="blueprint_cover",
            help="Your book cover"
        )
        
        if cover_file:
            st.success(f"✅ Loaded: {cover_file.name}")
            image = Image.open(cover_file)
            st.image(image, caption="Cover Preview", width=200)
    
    st.divider()
    
    with st.expander("📋 Additional Information (Optional but Helpful)"):
        col1, col2 = st.columns(2)
        with col1:
            target_genre = st.text_input("Primary Genre (if known)", placeholder="e.g., Romantasy")
            comp_titles = st.text_area("Comparable Titles (one per line)", placeholder="Fourth Wing\nACOTAR\nSerpent & Wings of Night")
        with col2:
            target_audience = st.text_input("Target Audience (if known)", placeholder="e.g., Adult fantasy romance readers")
            author_platform = st.multiselect("Author Platforms", ["TikTok", "Instagram", "Twitter", "Facebook", "Newsletter", "None"])
    
    if manuscript_file and cover_file:
        if st.button("🚀 GENERATE COMPLETE MARKETING BLUEPRINT", type="primary", use_container_width=True):
            st.session_state.manuscript_bytes = manuscript_file.getvalue()
            st.session_state.manuscript_type = manuscript_file.type
            st.session_state.cover_bytes = cover_file.getvalue()
            st.session_state.cover_type = cover_file.type
            
            st.session_state.blueprint_options = {
                "genre": target_genre if target_genre else None,
                "comp_titles": [c.strip() for c in comp_titles.split("\n") if c.strip()] if comp_titles else [],
                "target_audience": target_audience if target_audience else None,
                "author_platforms": author_platform
            }
            
            st.session_state.blueprint_stage = "analyzing"
            st.rerun()
    else:
        st.info("👆 Please upload both manuscript and cover to continue")


def show_analyzing_stage():
    """Stage 2: Analysis in progress with REAL cover vision"""
    
    st.subheader("⚙️ Analyzing Your Book")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Step 1: Extract text
    status_text.text("📄 Extracting text from manuscript...")
    progress_bar.progress(10)
    manuscript_text = extract_full_text(
        st.session_state.manuscript_bytes,
        st.session_state.manuscript_type
    )
    
    # Step 2: Encode cover for vision
    status_text.text("🖼️ Preparing cover for analysis...")
    progress_bar.progress(20)
    cover_base64 = base64.b64encode(st.session_state.cover_bytes).decode('utf-8')
    
    # Step 3: ACTUALLY analyze cover with vision
    status_text.text("🔍 Analyzing your cover with AI vision...")
    progress_bar.progress(30)
    
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
        cover_analysis = analyze_cover_with_vision(client, cover_base64)
        
        # Show what we found in real-time
        st.success("✅ Cover analyzed! Here's what we detected:")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Colors:** {', '.join(cover_analysis.get('colors', ['Unknown']))}")
            st.write(f"**Figures:** {cover_analysis.get('figures', 'None detected')}")
        with col2:
            st.write(f"**Mood:** {cover_analysis.get('mood', 'Unknown')}")
            st.write(f"**Genre signals:** {cover_analysis.get('genre_signals', 'Unknown')}")
        
        # Step 4: Generate full blueprint with REAL cover data
        status_text.text("📝 Generating complete marketing strategy...")
        progress_bar.progress(60)
        
        blueprint = generate_complete_blueprint(
            client,
            manuscript_text,
            cover_analysis,
            st.session_state.blueprint_options
        )
        
        if blueprint:
            # Add the real cover analysis
            blueprint['cover_analysis'] = cover_analysis
            st.session_state.blueprint = blueprint
            
            status_text.text("✅ Blueprint generated successfully!")
            progress_bar.progress(100)
            time.sleep(1)
            st.session_state.blueprint_stage = "results"
            st.rerun()
        else:
            st.error("Failed to generate blueprint")
            
    except Exception as e:
        st.error(f"Error during analysis: {str(e)}")
        if st.button("⬅️ Back to Upload"):
            st.session_state.blueprint_stage = "upload"
            st.rerun()


def analyze_cover_with_vision(client, cover_base64):
    """ACTUALLY analyze the cover image using GPT-4o Mini vision"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # This supports vision!
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """You are a book cover expert. Analyze this cover and return JSON with:
                            
                            - colors: list of specific colors you see (e.g., ["bright red", "gold", "black"])
                            - figures: describe any people/figures present. If none, say "No figures detected"
                            - composition: describe the layout (where is the title? what imagery?)
                            - typography: describe the font style (serif, sans-serif, handwritten, etc.)
                            - mood: what emotional feeling does this cover convey?
                            - genre_signals: what genre does this cover suggest?
                            - strengths: 3 specific strengths of THIS EXACT cover
                            - weaknesses: 3 specific weaknesses of THIS EXACT cover
                            - suggestions: 3 specific improvements for THIS EXACT cover
                            
                            Be SPECIFIC. If it's bright red, say "bright red". If there are no people, say "No figures detected".
                            Return ONLY valid JSON, no other text."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{cover_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        st.error(f"Vision API Error: {str(e)}")
        # Return honest error fallback
        return {
            "colors": ["Analysis failed"],
            "figures": "Could not analyze",
            "composition": "Analysis failed",
            "typography": "Analysis failed",
            "mood": "Analysis failed",
            "genre_signals": "Analysis failed",
            "strengths": ["Cover uploaded successfully"],
            "weaknesses": [f"AI vision error: {str(e)[:50]}..."],
            "suggestions": ["Try uploading a clearer image", "Ensure cover is front-facing", "Check API key permissions"]
        }


def generate_complete_blueprint(client, manuscript_text, cover_analysis, options):
    """Generate full marketing blueprint using REAL cover data"""
    
    try:
        # Truncate manuscript
        if len(manuscript_text) > 20000:
            manuscript_text = manuscript_text[:20000] + "... [truncated]"
        
        prompt = f"""
        Create a complete book marketing blueprint.
        
        MANUSCRIPT SAMPLE:
        {manuscript_text[:2000]}
        
        ACTUAL COVER ANALYSIS (from visual inspection):
        - Colors: {', '.join(cover_analysis.get('colors', []))}
        - Figures: {cover_analysis.get('figures', 'None')}
        - Composition: {cover_analysis.get('composition', 'Unknown')}
        - Typography: {cover_analysis.get('typography', 'Unknown')}
        - Mood: {cover_analysis.get('mood', 'Unknown')}
        - Genre signals: {cover_analysis.get('genre_signals', 'Unknown')}
        
        Cover strengths: {', '.join(cover_analysis.get('strengths', []))}
        Cover weaknesses: {', '.join(cover_analysis.get('weaknesses', []))}
        Cover suggestions: {', '.join(cover_analysis.get('suggestions', []))}
        
        Additional info: {json.dumps(options)}
        
        Return a complete marketing blueprint as JSON with these sections:
        - book_profile: title, genre, subgenres, tone, pace, main_characters
        - reader_avatar: primary reader profile
        - market_position: primary_shelf, comp_titles, positioning_statement
        - keyword_cloud: amazon_keywords, search_volume, categories
        - blurb_analysis: score, strengths, weaknesses, optimized_version
        - marketing_blueprint: channel_strategies (tiktok, instagram, email, ads), launch_timeline
        - generated_assets: blurbs, tiktok_scripts, emails, social_posts, ad_copy, quote_cards
        
        The cover analysis above is REAL - use it exactly. Do not make up different cover details.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a book marketing expert. Use the provided cover analysis exactly."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        st.error(f"Blueprint generation error: {str(e)}")
        return None


def show_blueprint_results():
    """Stage 3: Display the complete blueprint with REAL cover data"""
    
    blueprint = st.session_state.blueprint
    if not blueprint:
        st.error("No blueprint found")
        return
    
    # Header with book title
    st.success(f"✅ Marketing Blueprint Complete: **{blueprint.get('book_profile', {}).get('title', 'Your Book')}**")
    
    # Export options
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📥 Download PDF Report", use_container_width=True):
            st.info("PDF export coming soon")
    with col2:
        if st.button("📋 Copy Summary", use_container_width=True):
            st.info("Copy feature coming soon")
    with col3:
        if st.button("🔄 New Analysis", use_container_width=True):
            st.session_state.blueprint_stage = "upload"
            st.session_state.blueprint = None
            st.rerun()
    
    st.divider()
    
    # Create tabs
    tabs = st.tabs([
        "📖 Book Profile", 
        "🎨 Cover Analysis", 
        "👥 Reader Avatar", 
        "🎯 Market Position",
        "🔑 Keywords",
        "📝 Blurb",
        "📱 Channel Strategy",
        "🗓️ Timeline",
        "🎬 Assets"
    ])
    
    with tabs[0]:
        show_book_profile(blueprint.get('book_profile', {}))
    
    with tabs[1]:
        show_cover_analysis(blueprint.get('cover_analysis', {}))  # This is the REAL vision data
    
    with tabs[2]:
        show_reader_avatar(blueprint.get('reader_avatar', {}))
    
    with tabs[3]:
        show_market_position(blueprint.get('market_position', {}))
    
    with tabs[4]:
        show_keywords(blueprint.get('keyword_cloud', {}))
    
    with tabs[5]:
        show_blurb_analysis(blueprint.get('blurb_analysis', {}))
    
    with tabs[6]:
        show_channel_strategy(blueprint.get('marketing_blueprint', {}).get('channel_strategies', {}))
    
    with tabs[7]:
        show_timeline(blueprint.get('marketing_blueprint', {}).get('launch_timeline', {}))
    
    with tabs[8]:
        show_assets(blueprint.get('generated_assets', {}))


def show_cover_analysis(cover):
    """Display REAL cover analysis from vision"""
    if not cover:
        st.info("No cover analysis available")
        return
    
    st.markdown("### 🎨 Cover Analysis (From AI Vision)")
    
    # Show what the AI actually saw
    with st.expander("🔍 What the AI detected", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Colors detected:** {', '.join(cover.get('colors', ['Unknown']))}")
            st.write(f"**Composition:** {cover.get('composition', 'Unknown')}")
            st.write(f"**Figures:** {cover.get('figures', 'Unknown')}")
        with col2:
            st.write(f"**Typography:** {cover.get('typography', 'Unknown')}")
            st.write(f"**Mood:** {cover.get('mood', 'Unknown')}")
            st.write(f"**Genre signals:** {cover.get('genre_signals', 'Unknown')}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ Strengths:**")
        for s in cover.get('strengths', []):
            st.write(f"• {s}")
    
    with col2:
        st.markdown("**❌ Weaknesses:**")
        for w in cover.get('weaknesses', []):
            st.write(f"• {w}")
    
    st.markdown("**💡 Suggestions:**")
    for s in cover.get('suggestions', []):
        st.write(f"• {s}")


# ============================================================================
# Other display functions (keep your existing ones)
# ============================================================================

def show_book_profile(profile):
    """Display book profile"""
    if not profile:
        st.info("No profile data")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📖 Book Details")
        st.write(f"**Title:** {profile.get('title', 'N/A')}")
        st.write(f"**Genre:** {profile.get('genre', 'N/A')}")
        st.write(f"**Subgenres:** {', '.join(profile.get('subgenres', []))}")
        st.write(f"**Tone:** {profile.get('tone', 'N/A')}")
        st.write(f"**Pace:** {profile.get('pace', 'N/A')}")
    
    with col2:
        st.markdown("### 🎭 Characters")
        characters = profile.get('main_characters', [])
        for char in characters:
            st.write(f"• {char}")


def show_reader_avatar(avatar):
    """Display reader avatar"""
    if not avatar:
        st.info("No reader avatar data")
        return
    
    primary = avatar.get('primary', {})
    
    st.markdown("### 👤 Primary Reader Avatar")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Name:** {primary.get('name', 'N/A')}")
        st.write(f"**Age:** {primary.get('age', 'N/A')}")
        st.write(f"**Occupation:** {primary.get('occupation', 'N/A')}")
    with col2:
        st.write(f"**Seeks:** {primary.get('what_she_seeks', 'N/A')}")
        st.write(f"**Hangs out:** {primary.get('where_she_hangs_out', 'N/A')}")
        st.write(f"**Avoids:** {primary.get('what_she_avoids', 'N/A')}")


def show_market_position(position):
    """Display market position"""
    if not position:
        st.info("No market position data")
        return
    
    st.markdown(f"**Primary Shelf:** {position.get('primary_shelf', 'N/A')}")
    st.markdown(f"**Positioning Statement:** {position.get('positioning_statement', 'N/A')}")
    
    st.markdown("### 📚 Comparable Titles")
    comps = position.get('comp_titles', [])
    for comp in comps:
        if isinstance(comp, dict):
            st.write(f"• **{comp.get('title')}** - {comp.get('similarity', '')}")
        else:
            st.write(f"• {comp}")


def show_keywords(keywords):
    """Display keyword cloud"""
    if not keywords:
        st.info("No keyword data")
        return
    
    st.markdown("**🔑 Amazon Keywords:**")
    for k in keywords.get('amazon_keywords', []):
        st.write(f"• {k}")


def show_blurb_analysis(blurb):
    """Display blurb analysis"""
    if not blurb:
        st.info("No blurb data")
        return
    
    score = blurb.get('score', 0)
    st.metric("Blurb Score", f"{score}/100")
    
    st.markdown("**✨ Optimized Version:**")
    st.success(blurb.get('optimized_version', 'N/A'))


def show_channel_strategy(strategies):
    """Display channel strategies"""
    if not strategies:
        st.info("No channel strategy data")
        return
    
    for channel, data in strategies.items():
        with st.expander(f"📱 {channel.title()} Strategy"):
            st.json(data)


def show_timeline(timeline):
    """Display launch timeline"""
    if not timeline:
        st.info("No timeline data")
        return
    
    phases = [
        ("6_months_out", "6 Months Before Launch"),
        ("3_months_out", "3 Months Before Launch"),
        ("1_month_out", "1 Month Before Launch"),
        ("launch_week", "Launch Week"),
        ("post_launch", "Post-Launch")
    ]
    
    for phase_key, phase_name in phases:
        tasks = timeline.get(phase_key, [])
        if tasks:
            with st.expander(f"📅 {phase_name}"):
                for task in tasks:
                    st.write(f"• {task}")


def show_assets(assets):
    """Display generated assets"""
    if not assets:
        st.info("No assets generated")
        return
    
    for asset_type, content in assets.items():
        with st.expander(f"📎 {asset_type.title()}"):
            if isinstance(content, list):
                for item in content:
                    st.write(item)
            else:
                st.write(content)


# ============================================================================
# Helper functions
# ============================================================================

def extract_text_preview(file):
    """Extract preview text from file"""
    try:
        if file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(file)
            return pdf_reader.pages[0].extract_text()[:500]
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(file)
            return doc.paragraphs[0].text[:500] if doc.paragraphs else ""
        else:
            return file.getvalue().decode("utf-8")[:500]
    except:
        return "Preview not available"


def extract_full_text(bytes_data, file_type):
    """Extract full text from file bytes"""
    try:
        import io
        if "pdf" in file_type:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(bytes_data))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        elif "document" in file_type:
            doc = docx.Document(io.BytesIO(bytes_data))
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        else:
            return bytes_data.decode("utf-8")
    except Exception as e:
        st.error(f"Error extracting text: {e}")
        return ""

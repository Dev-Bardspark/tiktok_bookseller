# BookReader.py
import streamlit as st
import openai
import PyPDF2
import docx
import json
import time
from typing import Optional, Dict, List

def show_manuscript_tools():
    """Main function for manuscript analysis and marketing asset generation"""
    
    # Check if we're on the correct page to avoid duplicate widget issues
    if st.session_state.get('current_page') != "📖 Book Reader":
        # Don't render anything if we're not on this page
        return
    
    # Initialize session state for this module
    if 'manuscript_analysis' not in st.session_state:
        st.session_state.manuscript_analysis = None
        
    if 'generated_assets' not in st.session_state:
        st.session_state.generated_assets = {}
        
    if 'api_configured' not in st.session_state:
        st.session_state.api_configured = False
        
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None

    # Header
    st.title("📖 Book Reader & Marketing Engine")
    st.markdown("Upload your manuscript to analyze it and generate marketing assets")
    st.markdown("---")

    # API Configuration
    with st.expander("🔑 OpenAI API Settings", expanded=not st.session_state.api_configured):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if not st.session_state.api_configured:
                api_key = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    key="openai_api_key_input",  # Unique key
                    help="Get your key at https://platform.openai.com"
                )
                
                if api_key:
                    if st.button("Connect", key="connect_api_button"):
                        st.session_state.openai_api_key = api_key
                        openai.api_key = api_key
                        st.session_state.api_configured = True
                        st.rerun()
            else:
                st.success("✅ OpenAI connected")
                st.caption(f"Using: {st.session_state.get('model', 'gpt-4')}")
                
                if st.button("Disconnect", key="disconnect_api_button"):
                    st.session_state.api_configured = False
                    st.session_state.openai_api_key = None
                    st.rerun()
        
        with col2:
            if st.session_state.api_configured:
                st.session_state.model = st.selectbox(
                    "Model",
                    ["gpt-4", "gpt-3.5-turbo-16k"],
                    index=0,
                    key="model_select"
                )
                
                st.session_state.temperature = st.slider(
                    "Creativity",
                    0.0, 1.0, 0.7, 0.1,
                    key="temp_slider"
                )

    # Only show the rest if API is configured
    if not st.session_state.api_configured:
        st.info("👆 Please configure your OpenAI API key above to continue")
        return

    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["📄 Upload Manuscript", "🔍 Analysis Results", "🚀 Generated Assets"])
    
    # Tab 1: Upload Manuscript
    with tab1:
        st.subheader("Upload Your Manuscript")
        
        uploaded_file = st.file_uploader(
            "Choose a file (PDF, DOCX, or TXT)",
            type=['pdf', 'docx', 'txt'],
            key="manuscript_uploader",
            help="Upload your complete manuscript for AI analysis"
        )
        
        if uploaded_file:
            # Extract text
            with st.spinner("📄 Extracting text..."):
                manuscript_text = extract_text_from_file(uploaded_file)
            
            if manuscript_text:
                st.success(f"✅ Extracted {len(manuscript_text)} characters")
                
                with st.expander("Preview"):
                    st.text(manuscript_text[:1000] + "..." if len(manuscript_text) > 1000 else manuscript_text)
                
                # Analyze button
                if st.button("🔍 Analyze Manuscript", type="primary", key="analyze_button", use_container_width=True):
                    analysis = analyze_manuscript_text(manuscript_text)
                    
                    if analysis:
                        st.session_state.manuscript_analysis = analysis
                        st.session_state.generated_assets = {}
                        st.success("✅ Analysis complete!")
                        st.rerun()
    
    # Tab 2: Analysis Results
    with tab2:
        if st.session_state.manuscript_analysis:
            display_analysis(st.session_state.manuscript_analysis)
            
            # Generate assets button
            if st.button("🚀 Generate All Marketing Assets", type="primary", key="generate_button", use_container_width=True):
                with st.spinner("Generating assets..."):
                    assets = generate_all_assets(st.session_state.manuscript_analysis)
                    st.session_state.generated_assets = assets
                    st.success("✅ Assets generated!")
                    st.rerun()
        else:
            st.info("No manuscript analyzed yet. Upload a file in the Upload tab.")
    
    # Tab 3: Generated Assets
    with tab3:
        if st.session_state.generated_assets:
            display_assets(st.session_state.generated_assets)
        else:
            st.info("No assets generated yet. Analyze a manuscript first.")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_text_from_file(uploaded_file) -> Optional[str]:
    """Extract text from uploaded file based on type"""
    file_type = uploaded_file.type
    
    try:
        if file_type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
            
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
            
        elif file_type == "text/plain":
            return uploaded_file.getvalue().decode("utf-8")
            
        else:
            st.error(f"Unsupported file type: {file_type}")
            return None
            
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None


def analyze_manuscript_text(text: str) -> Dict:
    """Analyze manuscript with OpenAI"""
    
    # Truncate if too long
    if len(text) > 15000:
        text = text[:15000] + "... [truncated]"
        st.warning("Text truncated for API limits")
    
    prompt = f"""
    Analyze this manuscript and return JSON with:
    - title: The book title
    - genre: Primary genre
    - main_characters: List of main characters
    - central_themes: 3-5 themes
    - target_audience: Who would enjoy this
    - unique_selling_points: What makes it special
    - tone: Emotional atmosphere
    - plot_hooks: 3 compelling moments for teasers
    - comparable_titles: 2-3 similar books
    
    Manuscript:
    {text}
    """
    
    try:
        response = openai.ChatCompletion.create(
            model=st.session_state.get('model', 'gpt-4'),
            messages=[
                {"role": "system", "content": "You are a literary analyst. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return None


def generate_book_blurb(analysis: Dict) -> str:
    """Generate book blurb"""
    prompt = f"""
    Write a compelling book blurb (150 words) for:
    Title: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Characters: {', '.join(analysis.get('main_characters', ['']))}
    Themes: {', '.join(analysis.get('central_themes', ['']))}
    """
    
    response = openai.ChatCompletion.create(
        model=st.session_state.get('model', 'gpt-4'),
        messages=[
            {"role": "system", "content": "You are a copywriter."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    return response.choices[0].message.content


def generate_tiktok_scripts(analysis: Dict) -> List[Dict]:
    """Generate TikTok video scripts"""
    prompt = f"""
    Create 3 TikTok video scripts (15-30 seconds each) for this book:
    Title: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Plot Hooks: {', '.join(analysis.get('plot_hooks', ['']))}
    
    For each script include: hook, visuals, voiceover, music, cta
    Return as JSON array.
    """
    
    response = openai.ChatCompletion.create(
        model=st.session_state.get('model', 'gpt-4'),
        messages=[
            {"role": "system", "content": "You are a viral video creator. Return JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def generate_email_sequence(analysis: Dict) -> Dict:
    """Generate launch email sequence"""
    prompt = f"""
    Create 3 emails for book launch:
    1. Pre-launch teaser
    2. Launch day announcement
    3. Follow-up with reviews
    
    Book: {analysis.get('title', 'Untitled')}
    Target: {analysis.get('target_audience', '')}
    Return as JSON.
    """
    
    response = openai.ChatCompletion.create(
        model=st.session_state.get('model', 'gpt-4'),
        messages=[
            {"role": "system", "content": "You are an email marketer. Return JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def generate_social_posts(analysis: Dict) -> List[Dict]:
    """Generate social media posts"""
    prompt = f"""
    Create 5 social media posts for:
    Book: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    
    Include platform, caption, hashtags for each.
    Return as JSON array.
    """
    
    response = openai.ChatCompletion.create(
        model=st.session_state.get('model', 'gpt-4'),
        messages=[
            {"role": "system", "content": "You are a social media manager. Return JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def generate_ad_copy(analysis: Dict) -> Dict:
    """Generate ad copy"""
    prompt = f"""
    Create 3 ad variations for Facebook/Amazon:
    Book: {analysis.get('title', 'Untitled')}
    USP: {', '.join(analysis.get('unique_selling_points', ['']))}
    Return as JSON with headline, text, cta for each.
    """
    
    response = openai.ChatCompletion.create(
        model=st.session_state.get('model', 'gpt-4'),
        messages=[
            {"role": "system", "content": "You are an ad copywriter. Return JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def generate_all_assets(analysis: Dict) -> Dict:
    """Generate all marketing assets"""
    assets = {}
    
    assets['blurb'] = generate_book_blurb(analysis)
    assets['tiktok_scripts'] = generate_tiktok_scripts(analysis)
    assets['emails'] = generate_email_sequence(analysis)
    assets['social_posts'] = generate_social_posts(analysis)
    assets['ad_copy'] = generate_ad_copy(analysis)
    
    return assets


def display_analysis(analysis: Dict):
    """Display analysis results"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📖 Book Info")
        st.write(f"**Title:** {analysis.get('title', 'N/A')}")
        st.write(f"**Genre:** {analysis.get('genre', 'N/A')}")
        st.write(f"**Tone:** {analysis.get('tone', 'N/A')}")
        
        st.subheader("👥 Characters")
        for char in analysis.get('main_characters', []):
            st.write(f"• {char}")
    
    with col2:
        st.subheader("🎨 Themes")
        for theme in analysis.get('central_themes', []):
            st.write(f"• {theme}")
        
        st.subheader("🎯 Target Audience")
        st.write(analysis.get('target_audience', 'N/A'))
        
        st.subheader("📚 Comparable")
        for comp in analysis.get('comparable_titles', []):
            st.write(f"• {comp}")


def display_assets(assets: Dict):
    """Display generated assets"""
    tabs = st.tabs(["📝 Blurb", "🎬 TikTok", "📧 Emails", "📱 Social", "📢 Ads"])
    
    with tabs[0]:
        st.subheader("Book Blurb")
        blurb_text = assets.get('blurb', 'Not generated')
        st.write(blurb_text)
        st.download_button(
            "Download",
            blurb_text,
            "blurb.txt",
            key="download_blurb"
        )
    
    with tabs[1]:
        st.subheader("TikTok Scripts")
        scripts = assets.get('tiktok_scripts', [])
        if isinstance(scripts, dict):
            scripts = [scripts]
        for i, script in enumerate(scripts, 1):
            with st.expander(f"Script {i}"):
                st.json(script)
    
    with tabs[2]:
        st.subheader("Email Sequence")
        emails = assets.get('emails', {})
        st.json(emails)
    
    with tabs[3]:
        st.subheader("Social Posts")
        posts = assets.get('social_posts', [])
        st.json(posts)
    
    with tabs[4]:
        st.subheader("Ad Copy")
        ads = assets.get('ad_copy', {})
        st.json(ads)

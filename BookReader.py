# BookReader.py
import streamlit as st
from openai import OpenAI
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
                    key="openai_api_key_input",
                    help="Get your key at https://platform.openai.com"
                )
                
                if api_key:
                    if st.button("Connect", key="connect_api_button"):
                        st.session_state.openai_api_key = api_key
                        st.session_state.api_configured = True
                        st.rerun()
            else:
                st.success("✅ OpenAI connected")
                st.caption(f"Using: {st.session_state.get('model', 'gpt-4o-mini')}")
                
                if st.button("Disconnect", key="disconnect_api_button"):
                    st.session_state.api_configured = False
                    st.session_state.openai_api_key = None
                    st.rerun()
        
        with col2:
            if st.session_state.api_configured:
                st.session_state.model = st.selectbox(
                    "Model",
                    ["gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-3.5-turbo-1106"],
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
                    # Show first 1000 chars as preview only
                    st.text(manuscript_text[:1000] + "..." if len(manuscript_text) > 1000 else manuscript_text)
                
                # Analyze button - NO SIZE LIMIT
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
    """Analyze manuscript with OpenAI using GPT-4o mini"""
    
    # Initialize the client
    client = OpenAI(api_key=st.session_state.openai_api_key)
    
    # Use GPT-4o mini as default (supports JSON mode and large context)
    model_to_use = st.session_state.get('model', 'gpt-4o-mini')
    
    # GPT-4o mini has 128k context - plenty for most books
    # But if it's extremely long, we'll use the first 500k chars to be safe
    if len(text) > 500000:
        text = text[:500000]
        st.info("Using first 500,000 characters of your manuscript for analysis.")
    
    prompt = f"""
    Analyze this manuscript and return JSON with:
    - title: The book title (suggest one if unclear)
    - genre: Primary genre and subgenres
    - main_characters: List of main characters with brief descriptions
    - central_themes: 3-5 core themes explored
    - target_audience: Who would most enjoy this book?
    - unique_selling_points: What makes it special/different?
    - tone: Emotional atmosphere (e.g., suspenseful, humorous, melancholy)
    - plot_hooks: 3 compelling moments for teasers
    - comparable_titles: 2-3 well-known books similar in style/theme
    
    Manuscript:
    {text}
    """
    
    try:
        # Check if model supports JSON mode
        json_supported_models = ["gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-4-1106-preview", "gpt-3.5-turbo-1106"]
        
        if model_to_use in json_supported_models:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "You are a literary analyst and marketing expert. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
        else:
            # Fallback for older models
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "You are a literary analyst and marketing expert. You must return valid JSON only, no other text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return None


def generate_book_blurb(analysis: Dict) -> str:
    """Generate book blurb"""
    client = OpenAI(api_key=st.session_state.openai_api_key)
    
    prompt = f"""
    Write a compelling book blurb (150 words) for:
    Title: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Characters: {', '.join(analysis.get('main_characters', ['']))}
    Themes: {', '.join(analysis.get('central_themes', ['']))}
    Tone: {analysis.get('tone', '')}
    """
    
    response = client.chat.completions.create(
        model=st.session_state.get('model', 'gpt-4o-mini'),
        messages=[
            {"role": "system", "content": "You are a professional copywriter specializing in book descriptions."},
            {"role": "user", "content": prompt}
        ],
        temperature=st.session_state.get('temperature', 0.7),
        max_tokens=300
    )
    
    return response.choices[0].message.content


def generate_tiktok_scripts(analysis: Dict) -> List[Dict]:
    """Generate TikTok video scripts"""
    client = OpenAI(api_key=st.session_state.openai_api_key)
    
    prompt = f"""
    Create 3 TikTok video scripts (15-30 seconds each) for this book:
    Title: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Plot Hooks: {', '.join(analysis.get('plot_hooks', ['']))}
    Tone: {analysis.get('tone', '')}
    
    For each script include:
    - hook: The first 3 seconds to grab attention
    - visuals: Scene descriptions
    - voiceover: The spoken text
    - music: Background music suggestion
    - cta: Call to action
    
    Return as JSON array.
    """
    
    response = client.chat.completions.create(
        model=st.session_state.get('model', 'gpt-4o-mini'),
        messages=[
            {"role": "system", "content": "You are a viral video creator specializing in BookTok. Return JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def generate_email_sequence(analysis: Dict) -> Dict:
    """Generate launch email sequence"""
    client = OpenAI(api_key=st.session_state.openai_api_key)
    
    prompt = f"""
    Create 3 emails for book launch:
    1. Pre-launch teaser email
    2. Launch day announcement email  
    3. Follow-up email with reviews/social proof
    
    Book: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Target Audience: {analysis.get('target_audience', '')}
    Unique Selling Points: {', '.join(analysis.get('unique_selling_points', ['']))}
    
    Return as JSON with keys: prelaunch_email, launch_email, followup_email
    Each should include subject line and body.
    """
    
    response = client.chat.completions.create(
        model=st.session_state.get('model', 'gpt-4o-mini'),
        messages=[
            {"role": "system", "content": "You are an email marketing specialist for authors. Return JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def generate_social_posts(analysis: Dict) -> List[Dict]:
    """Generate social media posts"""
    client = OpenAI(api_key=st.session_state.openai_api_key)
    
    prompt = f"""
    Create 5 social media posts to promote this book:
    Book: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Plot Hooks: {', '.join(analysis.get('plot_hooks', ['']))}
    
    For each post, include:
    - platform: (mix of Instagram, TikTok, Twitter, Facebook)
    - caption: The post text
    - hashtags: 3-5 relevant hashtags
    - visual_suggestion: What image/video to use
    
    Return as JSON array.
    """
    
    response = client.chat.completions.create(
        model=st.session_state.get('model', 'gpt-4o-mini'),
        messages=[
            {"role": "system", "content": "You are a social media manager for authors. Return JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def generate_ad_copy(analysis: Dict) -> Dict:
    """Generate ad copy"""
    client = OpenAI(api_key=st.session_state.openai_api_key)
    
    prompt = f"""
    Create 3 ad variations for Facebook/Amazon ads:
    Book: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Unique Selling Points: {', '.join(analysis.get('unique_selling_points', ['']))}
    Target Audience: {analysis.get('target_audience', '')}
    
    For each variation, provide:
    - headline: Catchy headline (max 5 words)
    - text: Primary ad text (1-2 sentences)
    - cta: Call to action
    
    Return as JSON with keys: ad_variation_1, ad_variation_2, ad_variation_3
    """
    
    response = client.chat.completions.create(
        model=st.session_state.get('model', 'gpt-4o-mini'),
        messages=[
            {"role": "system", "content": "You are a direct response copywriter for book advertising. Return JSON."},
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
        characters = analysis.get('main_characters', [])
        if isinstance(characters, list):
            for char in characters:
                st.write(f"• {char}")
        else:
            st.write(f"• {characters}")
    
    with col2:
        st.subheader("🎨 Themes")
        themes = analysis.get('central_themes', [])
        if isinstance(themes, list):
            for theme in themes:
                st.write(f"• {theme}")
        else:
            st.write(f"• {themes}")
        
        st.subheader("🎯 Target Audience")
        st.write(analysis.get('target_audience', 'N/A'))
        
        st.subheader("📚 Comparable")
        comps = analysis.get('comparable_titles', [])
        if isinstance(comps, list):
            for comp in comps:
                st.write(f"• {comp}")
        else:
            st.write(f"• {comps}")


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
            # Handle case where API returns a dict with a scripts field
            if 'scripts' in scripts:
                scripts = scripts['scripts']
            else:
                scripts = [scripts]
        
        if isinstance(scripts, list):
            for i, script in enumerate(scripts, 1):
                with st.expander(f"Script {i}"):
                    if isinstance(script, dict):
                        for key, value in script.items():
                            st.write(f"**{key}:** {value}")
                    else:
                        st.write(script)
        else:
            st.json(scripts)
    
    with tabs[2]:
        st.subheader("Email Sequence")
        emails = assets.get('emails', {})
        if isinstance(emails, dict):
            for key, value in emails.items():
                with st.expander(key.replace('_', ' ').title()):
                    st.write(value)
        else:
            st.json(emails)
    
    with tabs[3]:
        st.subheader("Social Posts")
        posts = assets.get('social_posts', [])
        if isinstance(posts, dict):
            if 'posts' in posts:
                posts = posts['posts']
            else:
                posts = [posts]
        
        if isinstance(posts, list):
            for i, post in enumerate(posts, 1):
                with st.expander(f"Post {i}"):
                    if isinstance(post, dict):
                        for key, value in post.items():
                            st.write(f"**{key}:** {value}")
                    else:
                        st.write(post)
        else:
            st.json(posts)
    
    with tabs[4]:
        st.subheader("Ad Copy")
        ads = assets.get('ad_copy', {})
        if isinstance(ads, dict):
            for key, value in ads.items():
                with st.expander(key.replace('_', ' ').title()):
                    if isinstance(value, dict):
                        for k, v in value.items():
                            st.write(f"**{k}:** {v}")
                    else:
                        st.write(value)
        else:
            st.json(ads)

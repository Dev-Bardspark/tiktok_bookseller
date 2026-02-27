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
            with st.spinner("📄 Extracting text from file..."):
                manuscript_text = extract_text_from_file(uploaded_file)
            
            if manuscript_text:
                st.success(f"✅ Extracted {len(manuscript_text)} characters")
                
                with st.expander("Preview first 1000 characters"):
                    st.text(manuscript_text[:1000] + "..." if len(manuscript_text) > 1000 else manuscript_text)
                
                # Analyze button
                if st.button("🔍 Analyze Manuscript", type="primary", key="analyze_button", use_container_width=True):
                    with st.spinner("🔄 Analyzing manuscript with AI... (this may take a minute)"):
                        analysis = analyze_manuscript_text(manuscript_text)
                    
                    if analysis:
                        st.session_state.manuscript_analysis = analysis
                        st.session_state.generated_assets = {}
                        st.success("✅ Analysis complete! Go to the Analysis Results tab to see results.")
                        st.rerun()
    
    # Tab 2: Analysis Results
    with tab2:
        if st.session_state.manuscript_analysis:
            display_analysis(st.session_state.manuscript_analysis)
            
            # Generate assets button
            if st.button("🚀 Generate All Marketing Assets", type="primary", key="generate_button", use_container_width=True):
                with st.spinner("Generating marketing assets... (this may take 1-2 minutes)"):
                    assets = generate_all_assets(st.session_state.manuscript_analysis)
                    if assets:
                        st.session_state.generated_assets = assets
                        st.success("✅ Assets generated! Go to the Generated Assets tab to see them.")
                        st.rerun()
                    else:
                        st.error("Failed to generate assets. Check the error messages above.")
        else:
            st.info("No manuscript analyzed yet. Upload a file in the Upload tab and click Analyze.")
    
    # Tab 3: Generated Assets
    with tab3:
        if st.session_state.generated_assets:
            display_assets(st.session_state.generated_assets)
        else:
            st.info("No assets generated yet. Analyze a manuscript first, then click Generate.")


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
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
    except Exception as e:
        st.error(f"Failed to initialize OpenAI client: {str(e)}")
        return None
    
    # Use GPT-4o mini as default
    model_to_use = st.session_state.get('model', 'gpt-4o-mini')
    
    # GPT-4o mini has 128k context - plenty for most books
    # But if it's extremely long, we'll use the first 500k chars to be safe
    original_length = len(text)
    if original_length > 500000:
        text = text[:500000]
        st.warning(f"Manuscript is very long ({original_length} chars). Using first 500,000 characters for analysis.")
    
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
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return None


def generate_book_blurb(analysis: Dict) -> str:
    """Generate book blurb"""
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
    except Exception as e:
        return f"Error initializing client: {str(e)}"
    
    # Safely get values
    title = analysis.get('title', 'Untitled')
    genre = analysis.get('genre', 'Unknown Genre')
    
    # Handle characters
    characters = analysis.get('main_characters', [])
    if isinstance(characters, list):
        char_text = ', '.join([str(c) for c in characters[:3]])
    else:
        char_text = str(characters)
    
    # Handle themes
    themes = analysis.get('central_themes', [])
    if isinstance(themes, list):
        theme_text = ', '.join([str(t) for t in themes[:3]])
    else:
        theme_text = str(themes)
    
    tone = analysis.get('tone', '')
    
    prompt = f"""
    Write a compelling book blurb (150 words) for:
    Title: {title}
    Genre: {genre}
    Characters: {char_text}
    Themes: {theme_text}
    Tone: {tone}
    
    Make it engaging and sales-focused. Include a hook, stakes, and a call to action.
    """
    
    try:
        response = client.chat.completions.create(
            model=st.session_state.get('model', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": "You are a professional copywriter specializing in book descriptions."},
                {"role": "user", "content": prompt}
            ],
            temperature=st.session_state.get('temperature', 0.7),
            max_tokens=400
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error generating blurb: {str(e)}"


def generate_tiktok_scripts(analysis: Dict) -> List:
    """Generate TikTok video scripts"""
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
    except Exception as e:
        return [{"error": str(e)}]
    
    # Safely get plot hooks
    plot_hooks = analysis.get('plot_hooks', [])
    if isinstance(plot_hooks, list):
        hooks_text = ', '.join([str(h) for h in plot_hooks[:3]])
    else:
        hooks_text = str(plot_hooks)
    
    prompt = f"""
    Create 3 TikTok video scripts (15-30 seconds each) for this book:
    Title: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Plot Hooks: {hooks_text}
    Tone: {analysis.get('tone', '')}
    
    For each script include:
    - hook: The first 3 seconds to grab attention
    - visuals: Scene descriptions
    - voiceover: The spoken text
    - music: Background music suggestion
    - cta: Call to action
    
    Return as a JSON array with 3 objects.
    """
    
    try:
        response = client.chat.completions.create(
            model=st.session_state.get('model', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": "You are a viral video creator specializing in BookTok. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        # Ensure we return a list
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            # Check if it has a scripts key
            if 'scripts' in result:
                return result['scripts']
            else:
                return [result]
        else:
            return [{"error": "Unexpected response format"}]
            
    except Exception as e:
        return [{"error": str(e)}]


def generate_email_sequence(analysis: Dict) -> Dict:
    """Generate launch email sequence"""
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
    except Exception as e:
        return {"error": str(e)}
    
    # Safely get values
    usp = analysis.get('unique_selling_points', [])
    if isinstance(usp, list):
        usp_text = ', '.join([str(u) for u in usp[:3]])
    else:
        usp_text = str(usp)
    
    prompt = f"""
    Create 3 emails for book launch:
    1. Pre-launch teaser email
    2. Launch day announcement email  
    3. Follow-up email with reviews/social proof
    
    Book: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Target Audience: {analysis.get('target_audience', '')}
    Unique Selling Points: {usp_text}
    
    Return as JSON with keys: prelaunch_email, launch_email, followup_email
    Each should include subject line and body.
    """
    
    try:
        response = client.chat.completions.create(
            model=st.session_state.get('model', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": "You are an email marketing specialist for authors. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        return {"error": str(e)}


def generate_social_posts(analysis: Dict) -> List:
    """Generate social media posts"""
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
    except Exception as e:
        return [{"error": str(e)}]
    
    # Safely get plot hooks
    plot_hooks = analysis.get('plot_hooks', [])
    if isinstance(plot_hooks, list):
        hooks_text = ', '.join([str(h) for h in plot_hooks[:3]])
    else:
        hooks_text = str(plot_hooks)
    
    prompt = f"""
    Create 5 social media posts to promote this book:
    Book: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Plot Hooks: {hooks_text}
    
    For each post, include:
    - platform: (mix of Instagram, TikTok, Twitter, Facebook)
    - caption: The post text
    - hashtags: 3-5 relevant hashtags
    - visual_suggestion: What image/video to use
    
    Return as a JSON array with 5 objects.
    """
    
    try:
        response = client.chat.completions.create(
            model=st.session_state.get('model', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": "You are a social media manager for authors. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        # Ensure we return a list
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            if 'posts' in result:
                return result['posts']
            else:
                return [result]
        else:
            return [{"error": "Unexpected response format"}]
            
    except Exception as e:
        return [{"error": str(e)}]


def generate_ad_copy(analysis: Dict) -> Dict:
    """Generate ad copy"""
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
    except Exception as e:
        return {"error": str(e)}
    
    # Safely get USP
    usp = analysis.get('unique_selling_points', [])
    if isinstance(usp, list):
        usp_text = ', '.join([str(u) for u in usp[:3]])
    else:
        usp_text = str(usp)
    
    prompt = f"""
    Create 3 ad variations for Facebook/Amazon ads:
    Book: {analysis.get('title', 'Untitled')}
    Genre: {analysis.get('genre', '')}
    Unique Selling Points: {usp_text}
    Target Audience: {analysis.get('target_audience', '')}
    
    For each variation, provide:
    - headline: Catchy headline (max 5 words)
    - text: Primary ad text (1-2 sentences)
    - cta: Call to action
    
    Return as JSON with keys: ad_variation_1, ad_variation_2, ad_variation_3
    """
    
    try:
        response = client.chat.completions.create(
            model=st.session_state.get('model', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": "You are a direct response copywriter for book advertising. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        return {"error": str(e)}


def generate_all_assets(analysis: Dict) -> Dict:
    """Generate all marketing assets"""
    assets = {}
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Book Blurb
        status_text.text("📝 Generating book blurb...")
        assets['blurb'] = generate_book_blurb(analysis)
        progress_bar.progress(20)
        time.sleep(0.3)
        
        # TikTok Scripts
        status_text.text("🎬 Creating TikTok scripts...")
        assets['tiktok_scripts'] = generate_tiktok_scripts(analysis)
        progress_bar.progress(40)
        time.sleep(0.3)
        
        # Email Sequence
        status_text.text("📧 Writing email sequence...")
        assets['emails'] = generate_email_sequence(analysis)
        progress_bar.progress(60)
        time.sleep(0.3)
        
        # Social Posts
        status_text.text("📱 Crafting social posts...")
        assets['social_posts'] = generate_social_posts(analysis)
        progress_bar.progress(80)
        time.sleep(0.3)
        
        # Ad Copy
        status_text.text("📢 Generating ad copy...")
        assets['ad_copy'] = generate_ad_copy(analysis)
        progress_bar.progress(100)
        time.sleep(0.3)
        
        status_text.text("✅ All assets generated successfully!")
        time.sleep(1)
        
    except Exception as e:
        st.error(f"Error in asset generation: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
    
    finally:
        status_text.empty()
        progress_bar.empty()
    
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
    if not assets:
        st.warning("No assets to display")
        return
    
    tabs = st.tabs(["📝 Blurb", "🎬 TikTok", "📧 Emails", "📱 Social", "📢 Ads"])
    
    # Tab 1: Blurb
    with tabs[0]:
        st.subheader("Book Blurb")
        blurb_text = assets.get('blurb', 'Not generated')
        if blurb_text and not blurb_text.startswith("Error"):
            st.write(blurb_text)
            st.download_button(
                "📥 Download Blurb",
                blurb_text,
                "book_blurb.txt",
                key="download_blurb"
            )
        else:
            st.error(blurb_text)
    
    # Tab 2: TikTok Scripts
    with tabs[1]:
        st.subheader("TikTok Video Scripts")
        scripts = assets.get('tiktok_scripts', [])
        if scripts and isinstance(scripts, list):
            for i, script in enumerate(scripts, 1):
                with st.expander(f"🎬 Script {i}"):
                    if isinstance(script, dict):
                        for key, value in script.items():
                            st.write(f"**{key.title()}:** {value}")
                    else:
                        st.write(script)
        else:
            st.info("No TikTok scripts generated")
    
    # Tab 3: Emails
    with tabs[2]:
        st.subheader("Email Sequence")
        emails = assets.get('emails', {})
        if emails and isinstance(emails, dict):
            for key, value in emails.items():
                if key != "error":
                    with st.expander(f"📧 {key.replace('_', ' ').title()}"):
                        st.write(value)
                else:
                    st.error(f"Error: {value}")
        else:
            st.info("No emails generated")
    
    # Tab 4: Social Posts
    with tabs[3]:
        st.subheader("Social Media Posts")
        posts = assets.get('social_posts', [])
        if posts and isinstance(posts, list):
            for i, post in enumerate(posts, 1):
                with st.expander(f"📱 Post {i}"):
                    if isinstance(post, dict):
                        for key, value in post.items():
                            st.write(f"**{key.title()}:** {value}")
                    else:
                        st.write(post)
        else:
            st.info("No social posts generated")
    
    # Tab 5: Ads
    with tabs[4]:
        st.subheader("Ad Copy")
        ads = assets.get('ad_copy', {})
        if ads and isinstance(ads, dict):
            for key, value in ads.items():
                if key != "error":
                    with st.expander(f"📢 {key.replace('_', ' ').title()}"):
                        if isinstance(value, dict):
                            for k, v in value.items():
                                st.write(f"**{k.title()}:** {v}")
                        else:
                            st.write(value)
                else:
                    st.error(f"Error: {value}")
        else:
            st.info("No ad copy generated")

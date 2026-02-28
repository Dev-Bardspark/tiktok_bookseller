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
    """Stage 2: Analysis in progress with REAL cover vision and deep manuscript analysis"""
    
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
    
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
        
        # Step 3: ACTUALLY analyze cover with vision
        status_text.text("🔍 Analyzing your cover with AI vision...")
        progress_bar.progress(30)
        cover_analysis = analyze_cover_with_vision(client, cover_base64)
        
        # Show cover findings
        st.success("✅ Cover analyzed!")
        with st.expander("🎨 What the AI saw on your cover", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Colors detected:** {', '.join(cover_analysis.get('colors', ['Unknown']))}")
                st.write(f"**Figures:** {cover_analysis.get('figures', 'None detected')}")
                st.write(f"**Composition:** {cover_analysis.get('composition', 'Unknown')}")
            with col2:
                st.write(f"**Typography:** {cover_analysis.get('typography', 'Unknown')}")
                st.write(f"**Mood:** {cover_analysis.get('mood', 'Unknown')}")
                st.write(f"**Genre signals:** {cover_analysis.get('genre_signals', 'Unknown')}")
        
        # Step 4: Deep manuscript analysis
        status_text.text("📖 Analyzing your manuscript deeply...")
        progress_bar.progress(50)
        manuscript_analysis = analyze_manuscript_deeply(client, manuscript_text)
        
        if manuscript_analysis:
            # Show manuscript findings
            st.success("✅ Manuscript analyzed!")
            with st.expander("📚 What the AI found in your book", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    characters = manuscript_analysis.get('characters', {}).get('main', [])
                    st.write(f"**Main characters:** {len(characters)}")
                    for c in characters[:2]:
                        if isinstance(c, dict):
                            st.write(f"• {c.get('name', 'Unknown')}: {c.get('role', '')}")
                    
                    themes = manuscript_analysis.get('themes', {}).get('primary', [])
                    st.write(f"**Primary themes:** {', '.join(themes) if isinstance(themes, list) else themes}")
                
                with col2:
                    pacing = manuscript_analysis.get('pacing', {}).get('overall', 'Unknown')
                    st.write(f"**Pacing:** {pacing}")
                    
                    strengths = manuscript_analysis.get('strengths', [])
                    if strengths:
                        st.write(f"**Top strength:** {strengths[0]}")
        
        # Step 5: Generate complete blueprint with ALL real data
        status_text.text("🎯 Generating complete marketing blueprint...")
        progress_bar.progress(80)
        
        blueprint = generate_complete_blueprint(
            client,
            manuscript_text,
            cover_analysis,
            manuscript_analysis,
            st.session_state.blueprint_options
        )
        
        if blueprint:
            # Add both real analyses
            blueprint['cover_analysis'] = cover_analysis
            blueprint['manuscript_analysis'] = manuscript_analysis
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
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """You are a book cover expert. Analyze this cover and return JSON with:
                            
                            - colors: list of specific colors you see (e.g., ["bright red", "gold", "black", "white"])
                            - figures: describe any people/figures present. If none, say "No figures detected"
                            - composition: describe the layout (where is the title? what imagery? how are elements arranged?)
                            - typography: describe the font style (serif, sans-serif, handwritten, bold, elegant, etc.)
                            - mood: what emotional feeling does this cover convey in 2-3 words?
                            - genre_signals: what genre does this cover suggest? (e.g., "romantasy", "thriller", "contemporary romance")
                            - strengths: 3 specific strengths of THIS EXACT cover based on what you see
                            - weaknesses: 3 specific weaknesses of THIS EXACT cover based on what you see
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
        return {
            "colors": ["Analysis failed - check API key"],
            "figures": "Could not analyze",
            "composition": "Analysis failed",
            "typography": "Analysis failed",
            "mood": "Analysis failed",
            "genre_signals": "Analysis failed",
            "strengths": ["Cover uploaded successfully"],
            "weaknesses": [f"Error: {str(e)[:50]}..."],
            "suggestions": ["Check OpenAI API key permissions", "Ensure cover image is valid", "Try again"]
        }


def analyze_manuscript_deeply(client, full_text):
    """Deep analysis of the entire manuscript"""
    
    # Split into logical chunks
    total_length = len(full_text)
    first_part = full_text[:int(total_length * 0.1)]
    
    # Take middle section (around 50% mark)
    middle_start = int(total_length * 0.4)
    middle_end = int(total_length * 0.6)
    middle_part = full_text[middle_start:middle_end]
    
    last_part = full_text[int(total_length * 0.9):]
    
    # Truncate if needed
    if len(first_part) > 3000:
        first_part = first_part[:3000]
    if len(middle_part) > 4000:
        middle_part = middle_part[:4000]
    if len(last_part) > 3000:
        last_part = last_part[:3000]
    
    prompt = f"""
    You are a professional book editor and literary analyst. Analyze this book thoroughly.
    
    OPENING (first 10%):
    {first_part}
    
    MIDDLE (representative section from around 50%):
    {middle_part}
    
    ENDING (last 10%):
    {last_part}
    
    Based on these samples, provide a detailed analysis as JSON:
    
    1. characters: {{
        "main": [
            {{"name": "Character name", "role": "protagonist/antagonist/love interest", 
              "arc": "how they change", "traits": ["trait1", "trait2"]}}
        ],
        "supporting": ["list of supporting characters with brief description"],
        "relationships": ["key relationships and dynamics"]
    }}
    
    2. plot: {{
        "opening_hook": "what grabs reader attention",
        "inciting_incident": "what starts the story",
        "major_turning_points": ["point1", "point2", "point3"],
        "climax": "the big moment",
        "resolution": "how it ends"
    }}
    
    3. themes: {{
        "primary": ["main theme explained"],
        "secondary": ["other themes"],
        "motifs": ["recurring symbols/elements"]
    }}
    
    4. pacing: {{
        "overall": "fast/medium/slow",
        "opening_pace": "description",
        "middle_pace": "description",
        "ending_pace": "description",
        "variations": ["any pace changes"]
    }}
    
    5. tone_and_voice: {{
        "narrative_voice": "first person/third limited/omniscient/etc",
        "tone": "overall emotional atmosphere",
        "style": "descriptive/spare/lyrical/ dialogue-heavy/etc",
        "dialogue_style": "how characters speak"
    }}
    
    6. strengths: ["3-5 specific strengths of THIS manuscript based on the actual text"]
    
    7. weaknesses: ["3-5 specific areas for improvement based on the actual text"]
    
    8. comparable_titles: [
        {{"title": "Book Title", "similarity": "how it's similar", "difference": "how it's different"}}
    ]
    
    9. target_audience: {{
        "primary": "who will love this (age, gender, reading preferences)",
        "appeal": "what makes it appealing to them"
    }}
    
    Be SPECIFIC. Reference actual elements from the text. Don't make generic statements.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a literary analyst. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Manuscript analysis error: {str(e)}")
        return None


def generate_complete_blueprint(client, manuscript_text, cover_analysis, manuscript_analysis, options):
    """Generate full marketing blueprint using REAL manuscript and cover analysis"""
    
    try:
        # Truncate manuscript for final prompt
        if len(manuscript_text) > 5000:
            manuscript_excerpt = manuscript_text[:5000] + "... [truncated]"
        else:
            manuscript_excerpt = manuscript_text
        
        prompt = f"""
        Create a complete book marketing blueprint using these REAL analyses.
        
        MANUSCRIPT ANALYSIS:
        {json.dumps(manuscript_analysis, indent=2)}
        
        COVER ANALYSIS:
        {json.dumps(cover_analysis, indent=2)}
        
        MANUSCRIPT EXCERPT (for voice reference):
        {manuscript_excerpt[:2000]}
        
        ADDITIONAL INFO:
        {json.dumps(options)}
        
        Create a comprehensive marketing blueprint with these sections as JSON:
        
        1. book_profile: {{
            "title": "suggested title or based on content",
            "genre": "primary genre",
            "subgenres": ["subgenre1", "subgenre2"],
            "tone": "from analysis",
            "pace": "from analysis",
            "main_characters": ["character descriptions from analysis"]
        }}
        
        2. reader_avatar: {{
            "primary": {{
                "name": "Persona name",
                "age": "age range",
                "occupation": "typical job",
                "reading_habits": "how they read",
                "what_she_seeks": "what they want from books like this",
                "where_she_hangs_out": "social platforms",
                "what_she_avoids": "turnoffs"
            }}
        }}
        
        3. market_position: {{
            "primary_shelf": "Amazon category",
            "comp_titles": "from analysis",
            "positioning_statement": "For fans of X who want Y"
        }}
        
        4. keyword_cloud: {{
            "amazon_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
            "search_volume": {{"high": ["term1"], "medium": ["term2"], "low": ["term3"]}},
            "categories": ["category1", "category2"]
        }}
        
        5. blurb_analysis: {{
            "score": 0-100,
            "strengths": ["strength1", "strength2"],
            "weaknesses": ["weakness1", "weakness2"],
            "optimized_version": "compelling 150-word blurb"
        }}
        
        6. marketing_blueprint: {{
            "channel_strategies": {{
                "tiktok": {{
                    "content_pillars": ["pillar1", "pillar2", "pillar3"],
                    "sound_suggestions": ["sound1", "sound2"],
                    "hashtags": ["#tag1", "#tag2", "#tag3"]
                }},
                "instagram": {{
                    "post_types": ["type1", "type2", "type3"],
                    "reel_ideas": ["idea1", "idea2", "idea3"]
                }},
                "email": {{
                    "welcome_sequence": ["email1", "email2", "email3"],
                    "launch_sequence": ["email1", "email2", "email3"]
                }},
                "ads": {{
                    "amazon_ads": {{
                        "headlines": ["headline1", "headline2", "headline3"],
                        "keywords_to_bid": ["keyword1", "keyword2"],
                        "negative_keywords": ["term1", "term2"]
                    }}
                }}
            }},
            "launch_timeline": {{
                "6_months_out": ["task1", "task2", "task3"],
                "3_months_out": ["task1", "task2", "task3"],
                "1_month_out": ["task1", "task2", "task3"],
                "launch_week": ["task1", "task2", "task3", "task4"],
                "post_launch": ["task1", "task2", "task3"]
            }}
        }}
        
        7. generated_assets: {{
            "blurbs": ["3-5 sentence blurb version 1", "version 2", "version 3"],
            "tiktok_scripts": [
                {{"hook": "hook text", "visuals": "visual description", "voiceover": "script", "music": "suggestion", "cta": "call to action"}},
                {{"hook": "hook text", "visuals": "visual description", "voiceover": "script", "music": "suggestion", "cta": "call to action"}}
            ],
            "emails": {{
                "prelaunch": "prelaunch email content",
                "launch": "launch day email content",
                "followup": "follow-up email content"
            }},
            "social_posts": [
                "post 1 text",
                "post 2 text",
                "post 3 text",
                "post 4 text",
                "post 5 text"
            ],
            "ad_copy": {{
                "variation1": "ad text 1",
                "variation2": "ad text 2",
                "variation3": "ad text 3"
            }},
            "quote_cards": [
                {{"text": "quote from book", "visual": "visual suggestion"}},
                {{"text": "quote from book", "visual": "visual suggestion"}},
                {{"text": "quote from book", "visual": "visual suggestion"}}
            ]
        }}
        
        Use the EXACT analyses provided. Everything should reference actual elements from the book's content and cover.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a book marketing expert. Use the provided analyses exactly."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        st.error(f"Blueprint generation error: {str(e)}")
        return None


def show_blueprint_results():
    """Stage 3: Display the complete blueprint with REAL data"""
    
    blueprint = st.session_state.blueprint
    if not blueprint:
        st.error("No blueprint found")
        return
    
    # Header with book title
    title = blueprint.get('book_profile', {}).get('title', 'Your Book')
    st.success(f"✅ Marketing Blueprint Complete: **{title}**")
    
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
        show_cover_analysis(blueprint.get('cover_analysis', {}))
    
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
        st.markdown("### 🎭 Main Characters")
        characters = profile.get('main_characters', [])
        for char in characters:
            st.write(f"• {char}")


def show_cover_analysis(cover):
    """Display REAL cover analysis from vision"""
    if not cover:
        st.info("No cover analysis available")
        return
    
    st.markdown("### 🎨 Cover Analysis (From AI Vision)")
    
    # Show what the AI actually saw
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Colors detected:** {', '.join(cover.get('colors', ['Unknown']))}")
        st.write(f"**Composition:** {cover.get('composition', 'Unknown')}")
        st.write(f"**Figures:** {cover.get('figures', 'Unknown')}")
    with col2:
        st.write(f"**Typography:** {cover.get('typography', 'Unknown')}")
        st.write(f"**Mood:** {cover.get('mood', 'Unknown')}")
        st.write(f"**Genre signals:** {cover.get('genre_signals', 'Unknown')}")
    
    st.divider()
    
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
        st.write(f"**Reading Habits:** {primary.get('reading_habits', 'N/A')}")
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
            st.write(f"• **{comp.get('title')}**")
            st.write(f"  Similar: {comp.get('similarity', '')}")
            st.write(f"  Different: {comp.get('difference', '')}")
        else:
            st.write(f"• {comp}")


def show_keywords(keywords):
    """Display keyword cloud"""
    if not keywords:
        st.info("No keyword data")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔑 Amazon Keywords:**")
        for k in keywords.get('amazon_keywords', []):
            st.write(f"• {k}")
    
    with col2:
        st.markdown("**📊 Search Volume:**")
        search_volume = keywords.get('search_volume', {})
        for vol, terms in search_volume.items():
            if isinstance(terms, list):
                st.write(f"**{vol}:** {', '.join(terms)}")
    
    st.markdown("**📁 Categories:**")
    for cat in keywords.get('categories', []):
        st.write(f"• {cat}")


def show_blurb_analysis(blurb):
    """Display blurb analysis"""
    if not blurb:
        st.info("No blurb data")
        return
    
    score = blurb.get('score', 0)
    st.metric("Blurb Score", f"{score}/100")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ Strengths:**")
        for s in blurb.get('strengths', []):
            st.write(f"• {s}")
    
    with col2:
        st.markdown("**❌ Weaknesses:**")
        for w in blurb.get('weaknesses', []):
            st.write(f"• {w}")
    
    st.markdown("**✨ Optimized Version:**")
    st.info(blurb.get('optimized_version', 'N/A'))


def show_channel_strategy(strategies):
    """Display channel strategies"""
    if not strategies:
        st.info("No channel strategy data")
        return
    
    channel_names = list(strategies.keys())
    if channel_names:
        channel_tabs = st.tabs(channel_names)
        
        for i, (channel_name, channel_data) in enumerate(strategies.items()):
            with channel_tabs[i]:
                if isinstance(channel_data, dict):
                    for key, value in channel_data.items():
                        st.markdown(f"**{key.replace('_', ' ').title()}:**")
                        if isinstance(value, list):
                            for item in value:
                                st.write(f"• {item}")
                        elif isinstance(value, dict):
                            for k, v in value.items():
                                st.write(f"  **{k}:** {v}")
                        else:
                            st.write(value)
                else:
                    st.write(channel_data)


def show_timeline(timeline):
    """Display launch timeline"""
    if not timeline:
        st.info("No timeline data")
        return
    
    phases = [
        ("6_months_out", "📅 6 Months Before Launch"),
        ("3_months_out", "📅 3 Months Before Launch"),
        ("1_month_out", "📅 1 Month Before Launch"),
        ("launch_week", "🚀 Launch Week"),
        ("post_launch", "🎉 Post-Launch")
    ]
    
    for phase_key, phase_name in phases:
        tasks = timeline.get(phase_key, [])
        if tasks:
            with st.expander(phase_name):
                for task in tasks:
                    st.write(f"• {task}")


def show_assets(assets):
    """Display generated assets"""
    if not assets:
        st.info("No assets generated")
        return
    
    asset_types = ["blurbs", "tiktok_scripts", "emails", "social_posts", "ad_copy", "quote_cards"]
    asset_names = ["📝 Blurbs", "🎬 TikTok Scripts", "📧 Emails", "📱 Social Posts", "📢 Ad Copy", "💬 Quote Cards"]
    
    if any(assets.get(atype) for atype in asset_types):
        tabs = st.tabs(asset_names)
        
        for i, (atype, aname) in enumerate(zip(asset_types, asset_names)):
            with tabs[i]:
                content = assets.get(atype, [])
                if content:
                    if isinstance(content, list):
                        for j, item in enumerate(content):
                            with st.expander(f"{aname} #{j+1}"):
                                if isinstance(item, dict):
                                    for k, v in item.items():
                                        st.write(f"**{k}:** {v}")
                                else:
                                    st.write(item)
                    elif isinstance(content, dict):
                        for key, value in content.items():
                            with st.expander(f"{key.replace('_', ' ').title()}"):
                                st.write(value)
                    else:
                        st.write(content)
                else:
                    st.info(f"No {aname} generated")


# ============================================================================
# Helper functions for file extraction
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

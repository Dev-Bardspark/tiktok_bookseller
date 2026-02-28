# BookBlueprint.py
import streamlit as st
from openai import OpenAI
import PyPDF2
import docx
import json
import time
import re
from typing import Optional, Dict, List, Any
from datetime import datetime
import plotly.express as px
import pandas as pd
from PIL import Image
import io
import base64

def show_blueprint_analyzer():
    """Main Book Marketing Blueprint Analyzer"""
    
    if st.session_state.get('current_page') != "📖 Book Blueprint":
        return
    
    if 'openai_api_key' in st.session_state and st.session_state.openai_api_key:
        st.session_state.api_configured = True
    else:
        st.session_state.api_configured = False
    
    if 'blueprint' not in st.session_state:
        st.session_state.blueprint = None
    
    if 'blueprint_stage' not in st.session_state:
        st.session_state.blueprint_stage = "upload"
    
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
    
    if not st.session_state.api_configured:
        with st.expander("🔑 API Settings", expanded=True):
            api_key = st.text_input("OpenAI API Key", type="password", key="blueprint_api_key", 
                                   value=st.session_state.get('openai_api_key', ''))
            if api_key and st.button("Connect", key="blueprint_connect"):
                st.session_state.openai_api_key = api_key
                st.session_state.api_configured = True
                st.rerun()
        return
    
    stages = ["upload", "analyzing", "results"]
    stage_names = ["📤 Upload", "⚙️ Deep Analysis", "🎯 Blueprint"]
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
    
    if st.session_state.blueprint_stage == "upload":
        show_upload_stage()
    elif st.session_state.blueprint_stage == "analyzing":
        show_deep_analysis_stage()
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
            target_genre = st.text_input("Primary Genre (if known)", placeholder="e.g., Memoir")
            comp_titles = st.text_area("Comparable Titles (one per line)", placeholder="Wind, Sand and Stars\nFlying Solo\nSkyward")
        with col2:
            target_audience = st.text_input("Target Audience (if known)", placeholder="e.g., Aviation enthusiasts, memoir readers")
            author_platform = st.multiselect("Author Platforms", ["TikTok", "Instagram", "Twitter", "Facebook", "Newsletter", "None"])
    
    if manuscript_file and cover_file:
        cost_estimate = "$3-5 for complete analysis"
        st.info(f"💰 Estimated API cost: {cost_estimate}")
        
        if st.button("🚀 START DEEP ANALYSIS", type="primary", use_container_width=True):
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


def show_deep_analysis_stage():
    """Stage 2: DEEP analysis - chapter by chapter"""
    
    st.subheader("⚙️ Deep Analysis in Progress")
    st.warning("This analyzes your book chapter by chapter. It takes 2-3 minutes and costs $3-5 in API fees.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    details_container = st.container()
    
    # Step 1: Extract text
    status_text.text("📄 Extracting full manuscript...")
    progress_bar.progress(5)
    manuscript_text = extract_full_text(
        st.session_state.manuscript_bytes,
        st.session_state.manuscript_type
    )
    
    # Step 2: Split into chapters
    status_text.text("📑 Splitting into chapters...")
    progress_bar.progress(10)
    chapters = split_into_chapters(manuscript_text)
    with details_container:
        st.success(f"✅ Found {len(chapters)} chapters")
    
    # Step 3: Analyze cover
    status_text.text("🎨 Analyzing cover with vision...")
    progress_bar.progress(15)
    cover_base64 = base64.b64encode(st.session_state.cover_bytes).decode('utf-8')
    client = OpenAI(api_key=st.session_state.openai_api_key)
    cover_analysis = analyze_cover_with_vision(client, cover_base64)
    with details_container:
        st.success("✅ Cover analyzed")
    
    # Step 4: Analyze each chapter
    status_text.text("📖 Analyzing chapters (this takes time)...")
    progress_bar.progress(20)
    
    chapter_analyses = []
    for i, chapter in enumerate(chapters):
        status_text.text(f"📖 Analyzing chapter {i+1}/{len(chapters)}...")
        analysis = analyze_single_chapter(client, chapter, i+1)
        chapter_analyses.append(analysis)
        
        # Update progress (20% to 80% across chapters)
        progress = 20 + (60 * (i+1) / len(chapters))
        progress_bar.progress(int(progress))
        
        with details_container:
            st.write(f"✅ Chapter {i+1}: {analysis.get('summary', '')[:50]}...")
    
    # Step 5: Synthesize across ALL chapters
    status_text.text("🧠 Synthesizing across all chapters...")
    progress_bar.progress(85)
    
    book_analysis = synthesize_chapter_analyses(chapter_analyses)
    with details_container:
        st.success("✅ Full book synthesis complete")
    
    # Step 6: Generate complete blueprint
    status_text.text("🎯 Generating complete marketing blueprint...")
    progress_bar.progress(95)
    
    blueprint = generate_complete_blueprint(
        client,
        book_analysis,
        cover_analysis,
        chapters,
        st.session_state.blueprint_options
    )
    
    if blueprint:
        blueprint['cover_analysis'] = cover_analysis
        blueprint['book_analysis'] = book_analysis
        blueprint['chapter_count'] = len(chapters)
        st.session_state.blueprint = blueprint
        
        status_text.text("✅ Complete!")
        progress_bar.progress(100)
        time.sleep(1)
        st.session_state.blueprint_stage = "results"
        st.rerun()
    else:
        st.error("Failed to generate blueprint")


def split_into_chapters(text):
    """Intelligently split manuscript into chapters"""
    # Look for common chapter markers
    chapter_patterns = [
        r'Chapter \d+',
        r'CHAPTER \d+',
        r'Chapitre \d+',
        r'\n\d+\n',  # Just a number on its own line
        r'Part [IVX]+',
        r'Book [IVX]+'
    ]
    
    # Try to find chapter breaks
    best_pattern = None
    best_split = None
    
    for pattern in chapter_patterns:
        splits = re.split(pattern, text)
        if len(splits) > 3:  # Found at least a few chapters
            best_split = splits
            best_pattern = pattern
            break
    
    if best_split and len(best_split) > 1:
        # Remove empty first element if text started with chapter
        if not best_split[0].strip():
            best_split = best_split[1:]
        return best_split
    
    # If no chapters found, split by approximate page count
    words = text.split()
    words_per_page = 300
    total_pages = len(words) // words_per_page
    target_chapters = max(10, min(30, total_pages // 10))
    
    # Split into roughly equal chunks
    chunk_size = len(text) // target_chapters
    chunks = []
    for i in range(target_chapters):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < target_chapters - 1 else len(text)
        chunks.append(text[start:end])
    
    return chunks


def analyze_single_chapter(client, chapter_text, chapter_num):
    """Analyze a single chapter in depth with SAFE data structures"""
    
    if len(chapter_text) > 4000:
        chapter_text = chapter_text[:4000]
    
    prompt = f"""
    Analyze this chapter in detail and return ONLY valid JSON.
    
    CHAPTER {chapter_num}:
    {chapter_text}
    
    Return JSON with EXACTLY this structure:
    {{
        "summary": "Brief summary of what happens",
        "characters_present": ["character1", "character2"],
        "plot_development": "Key plot points",
        "themes": ["theme1", "theme2"],
        "tone": "Emotional tone",
        "pacing": "fast/medium/slow",
        "important_quotes": ["quote1"],
        "cliffhanger": true/false,
        "character_development": "How characters change"
    }}
    
    IMPORTANT: 
    - characters_present MUST be a list, even if empty
    - themes MUST be a list, even if empty
    - important_quotes MUST be a list, even if empty
    - Use ONLY valid JSON format
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a literary analyst. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # SAFETY: Ensure all fields exist and are correct types
        safe_result = {
            "chapter_number": chapter_num,
            "summary": str(result.get('summary', 'Summary not available')),
            "characters_present": result.get('characters_present', []),
            "plot_development": str(result.get('plot_development', 'Plot not available')),
            "themes": result.get('themes', []),
            "tone": str(result.get('tone', 'Unknown')),
            "pacing": str(result.get('pacing', 'medium')),
            "important_quotes": result.get('important_quotes', []),
            "cliffhanger": bool(result.get('cliffhanger', False)),
            "character_development": str(result.get('character_development', 'Unknown'))
        }
        
        # Force list types
        if not isinstance(safe_result['characters_present'], list):
            safe_result['characters_present'] = []
        if not isinstance(safe_result['themes'], list):
            safe_result['themes'] = []
        if not isinstance(safe_result['important_quotes'], list):
            safe_result['important_quotes'] = []
            
        return safe_result
        
    except Exception as e:
        st.error(f"Error analyzing chapter {chapter_num}: {str(e)}")
        # Return safe default with proper list types
        return {
            "chapter_number": chapter_num,
            "summary": "Analysis failed",
            "characters_present": [],
            "plot_development": "Error",
            "themes": [],
            "tone": "Unknown",
            "pacing": "Unknown",
            "important_quotes": [],
            "cliffhanger": False,
            "character_development": "Unknown"
        }


def synthesize_chapter_analyses(chapter_analyses):
    """Synthesize all chapter analyses into complete book understanding with SAFE data handling"""
    
    # Initialize with safe defaults
    character_arcs = {}
    plot_progression = []
    theme_tracking = {}
    tone_progression = []
    
    for i, chapter in enumerate(chapter_analyses):
        if not isinstance(chapter, dict):
            continue
            
        # SAFELY get characters_present - ensure it's a list
        chars = chapter.get('characters_present', [])
        if not isinstance(chars, list):
            chars = []
            
        # Track characters
        for char in chars:
            if char and isinstance(char, str):  # Only process valid strings
                if char not in character_arcs:
                    character_arcs[char] = {
                        'first_seen': i+1,
                        'chapters_present': [],
                        'development': []
                    }
                character_arcs[char]['chapters_present'].append(i+1)
        
        # Track plot safely
        plot_progression.append({
            'chapter': i+1,
            'plot': str(chapter.get('plot_development', '')),
            'summary': str(chapter.get('summary', ''))
        })
        
        # SAFELY get themes - ensure it's a list
        themes = chapter.get('themes', [])
        if not isinstance(themes, list):
            themes = []
            
        # Track themes
        for theme in themes:
            if theme and isinstance(theme, str):
                if theme not in theme_tracking:
                    theme_tracking[theme] = []
                theme_tracking[theme].append(i+1)
        
        # Track tone safely
        tone_progression.append({
            'chapter': i+1,
            'tone': str(chapter.get('tone', 'Unknown')),
            'pacing': str(chapter.get('pacing', 'Unknown'))
        })
    
    # Identify main characters (appear in most chapters) with SAFE calculation
    main_characters = []
    total_chapters = len(chapter_analyses) if chapter_analyses else 1
    
    for char, data in character_arcs.items():
        if len(data['chapters_present']) > total_chapters * 0.3:
            main_characters.append(char)
    
    # Identify primary themes with SAFE calculation
    primary_themes = []
    for theme, chapters in theme_tracking.items():
        if len(chapters) > total_chapters * 0.2:
            primary_themes.append(theme)
    
    # Build plot structure safely
    plot_structure = {
        'opening': plot_progression[0] if plot_progression else {},
        'rising_action': plot_progression[len(plot_progression)//4:len(plot_progression)//2] if len(plot_progression) > 2 else [],
        'climax': plot_progression[len(plot_progression)//2] if plot_progression and len(plot_progression) > len(plot_progression)//2 else {},
        'resolution': plot_progression[-1] if plot_progression else {}
    }
    
    return {
        'main_characters': main_characters[:5],
        'character_arcs': character_arcs,
        'plot_structure': plot_structure,
        'primary_themes': primary_themes[:3],
        'tone_progression': tone_progression,
        'chapter_count': total_chapters
    }


def analyze_cover_with_vision(client, cover_base64):
    """Analyze cover with vision"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this book cover in detail. Return JSON with:
                            - colors: list of specific colors
                            - figures: describe any people/figures
                            - composition: layout description
                            - typography: font style
                            - mood: emotional feeling
                            - genre_signals: what genre it suggests
                            - strengths: 3 specific strengths
                            - weaknesses: 3 specific weaknesses
                            - suggestions: 3 improvements
                            
                            Return ONLY valid JSON."""
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
        
        # Ensure lists are lists
        if 'colors' in result and not isinstance(result['colors'], list):
            result['colors'] = [str(result['colors'])]
        if 'strengths' in result and not isinstance(result['strengths'], list):
            result['strengths'] = [str(result['strengths'])]
        if 'weaknesses' in result and not isinstance(result['weaknesses'], list):
            result['weaknesses'] = [str(result['weaknesses'])]
        if 'suggestions' in result and not isinstance(result['suggestions'], list):
            result['suggestions'] = [str(result['suggestions'])]
            
        return result
        
    except Exception as e:
        return {
            "colors": ["Analysis failed"],
            "figures": "Error",
            "composition": "Error",
            "typography": "Error",
            "mood": "Error",
            "genre_signals": "Error",
            "strengths": ["Upload successful"],
            "weaknesses": [f"Error: {str(e)[:50]}"],
            "suggestions": ["Check API key", "Try again", "Ensure image is valid"]
        }


def generate_complete_blueprint(client, book_analysis, cover_analysis, chapters, options):
    """Generate complete marketing blueprint from full analysis"""
    
    # Get representative excerpts from first, middle, last chapters
    excerpts = []
    if chapters and len(chapters) > 0:
        excerpts.append(str(chapters[0][:1000]) if len(str(chapters[0])) > 1000 else str(chapters[0]))
        if len(chapters) > len(chapters)//2:
            mid_idx = len(chapters)//2
            excerpts.append(str(chapters[mid_idx][:1000]) if len(str(chapters[mid_idx])) > 1000 else str(chapters[mid_idx]))
        if len(chapters) > 1:
            excerpts.append(str(chapters[-1][:1000]) if len(str(chapters[-1])) > 1000 else str(chapters[-1]))
    
    # SAFELY get values
    main_chars = book_analysis.get('main_characters', [])
    if not isinstance(main_chars, list):
        main_chars = []
        
    primary_themes = book_analysis.get('primary_themes', [])
    if not isinstance(primary_themes, list):
        primary_themes = []
    
    prompt = f"""
    You are a book marketing expert. Create a COMPLETE marketing blueprint for this book.
    
    BOOK ANALYSIS (from full chapter-by-chapter review):
    Main characters: {', '.join(main_chars)}
    Primary themes: {', '.join(primary_themes)}
    Total chapters: {book_analysis.get('chapter_count', 0)}
    
    COVER ANALYSIS:
    {json.dumps(cover_analysis, indent=2)}
    
    REPRESENTATIVE EXCERPTS:
    EXCERPT 1 (opening):
    {excerpts[0] if len(excerpts) > 0 else "No excerpt"}
    
    EXCERPT 2 (middle):
    {excerpts[1] if len(excerpts) > 1 else "No excerpt"}
    
    EXCERPT 3 (ending):
    {excerpts[2] if len(excerpts) > 2 else "No excerpt"}
    
    Based on this COMPLETE analysis, create a marketing blueprint with:
    
    1. book_profile: {{
        "title": "Determine from content",
        "genre": "From analysis",
        "subgenres": ["derived from themes"],
        "tone": "From tone progression",
        "pace": "From pacing analysis",
        "main_characters": {json.dumps(main_chars)}
    }}
    
    2. reader_avatar: {{
        "primary": {{
            "name": "Persona name",
            "age": "appropriate range",
            "occupation": "relevant to themes",
            "reading_habits": "how they read",
            "what_she_seeks": "what they want from THIS book",
            "where_she_hangs_out": "relevant platforms",
            "what_she_avoids": "turnoffs"
        }}
    }}
    
    3. market_position: {{
        "primary_shelf": "Amazon category",
        "comp_titles": [
            {{"title": "Real comparable book", "similarity": "based on themes", "difference": "unique aspects"}},
            {{"title": "Another comparable", "similarity": "based on style", "difference": "unique elements"}}
        ],
        "positioning_statement": "For readers who love [elements from analysis]"
    }}
    
    4. keyword_cloud: {{
        "amazon_keywords": ["keywords from themes", "from characters", "from setting"],
        "search_volume": {{"high": ["main themes"], "medium": ["related terms"]}},
        "categories": ["2-3 Amazon categories"]
    }}
    
    5. blurb_analysis: {{
        "score": 75,
        "strengths": ["3 strengths from full analysis"],
        "weaknesses": ["3 areas from analysis"],
        "optimized_version": "150-word blurb using actual book elements"
    }}
    
    6. marketing_blueprint: {{
        "channel_strategies": {{
            "tiktok": {{
                "content_pillars": ["3 pillars from themes"],
                "sound_suggestions": ["2 matching sounds"],
                "hashtags": ["5 relevant hashtags"]
            }},
            "instagram": {{
                "post_types": ["3 visual post types"],
                "reel_ideas": ["2 reel concepts"]
            }},
            "email": {{
                "welcome_sequence": ["2 welcome emails"],
                "launch_sequence": ["2 launch emails"]
            }},
            "ads": {{
                "amazon_ads": {{
                    "headlines": ["3 headlines from excerpts"],
                    "keywords_to_bid": ["keywords from analysis"],
                    "negative_keywords": ["irrelevant terms"]
                }}
            }}
        }},
        "launch_timeline": {{
            "6_months_out": ["3 tasks"],
            "3_months_out": ["3 tasks"],
            "1_month_out": ["3 tasks"],
            "launch_week": ["4 tasks"],
            "post_launch": ["3 tasks"]
        }}
    }}
    
    7. generated_assets: {{
        "blurbs": [
            "Blurb using opening excerpt",
            "Blurb using themes",
            "Blurb using emotional arc"
        ],
        "tiktok_scripts": [
            {{"hook": "From excerpt 1", "visuals": "Matching", "voiceover": "Script", "music": "Suggestion", "cta": "Buy now"}},
            {{"hook": "From excerpt 2", "visuals": "Matching", "voiceover": "Script", "music": "Suggestion", "cta": "Pre-order"}}
        ],
        "emails": {{
            "prelaunch": "Email about book's origin",
            "launch": "Launch announcement",
            "followup": "Thank you with quotes"
        }},
        "social_posts": [
            "Post about main character",
            "Post about themes",
            "Post with quote",
            "Post about setting",
            "Post connecting to readers"
        ],
        "ad_copy": {{
            "variation1": "Ad focusing on plot",
            "variation2": "Ad focusing on emotion",
            "variation3": "Ad focusing on characters"
        }},
        "quote_cards": [
            {{"text": "Quote from opening", "visual": "Visual suggestion"}},
            {{"text": "Quote from middle", "visual": "Visual suggestion"}},
            {{"text": "Quote from ending", "visual": "Visual suggestion"}}
        ]
    }}
    
    IMPORTANT: EVERYTHING must reference the ACTUAL analysis and excerpts.
    Return ONLY valid JSON.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a book marketing expert. Use the provided analysis."},
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
    """Display the complete blueprint"""
    
    blueprint = st.session_state.blueprint
    if not blueprint:
        st.error("No blueprint found")
        return
    
    title = blueprint.get('book_profile', {}).get('title', 'Your Book')
    st.success(f"✅ Complete Marketing Blueprint: **{title}**")
    st.info(f"📊 Analyzed {blueprint.get('chapter_count', 'all')} chapters")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📥 Download PDF", use_container_width=True):
            st.info("Coming soon")
    with col2:
        if st.button("📋 Copy Summary", use_container_width=True):
            st.info("Coming soon")
    with col3:
        if st.button("🔄 New Analysis", use_container_width=True):
            st.session_state.blueprint_stage = "upload"
            st.session_state.blueprint = None
            st.rerun()
    
    st.divider()
    
    # Show book analysis summary
    if 'book_analysis' in blueprint:
        with st.expander("📚 Full Book Analysis", expanded=False):
            book = blueprint['book_analysis']
            chars = book.get('main_characters', [])
            if not isinstance(chars, list):
                chars = []
            st.write(f"**Main Characters:** {', '.join(chars)}")
            
            themes = book.get('primary_themes', [])
            if not isinstance(themes, list):
                themes = []
            st.write(f"**Primary Themes:** {', '.join(themes)}")
            st.write(f"**Plot Structure:**")
            st.json(book.get('plot_structure', {}))
    
    tabs = st.tabs([
        "📖 Book Profile", "🎨 Cover", "👥 Reader", "🎯 Market",
        "🔑 Keywords", "📝 Blurb", "📱 Strategy", "🗓️ Timeline", "🎬 Assets"
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
    if not profile or not isinstance(profile, dict):
        st.info("No profile data")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📖 Book Details")
        st.write(f"**Title:** {profile.get('title', 'N/A')}")
        st.write(f"**Genre:** {profile.get('genre', 'N/A')}")
        
        subgenres = profile.get('subgenres', [])
        if not isinstance(subgenres, list):
            subgenres = []
        st.write(f"**Subgenres:** {', '.join(subgenres)}")
        
        st.write(f"**Tone:** {profile.get('tone', 'N/A')}")
        st.write(f"**Pace:** {profile.get('pace', 'N/A')}")
    with col2:
        st.markdown("### 🎭 Main Characters")
        chars = profile.get('main_characters', [])
        if not isinstance(chars, list):
            chars = []
        for char in chars:
            st.write(f"• {char}")


def show_cover_analysis(cover):
    if not cover or not isinstance(cover, dict):
        st.info("No cover analysis")
        return
    
    st.markdown("### 🎨 Cover Analysis")
    col1, col2 = st.columns(2)
    with col1:
        colors = cover.get('colors', [])
        if not isinstance(colors, list):
            colors = [str(colors)]
        st.write(f"**Colors:** {', '.join(colors)}")
        st.write(f"**Composition:** {cover.get('composition', '')}")
        st.write(f"**Figures:** {cover.get('figures', '')}")
    with col2:
        st.write(f"**Typography:** {cover.get('typography', '')}")
        st.write(f"**Mood:** {cover.get('mood', '')}")
        st.write(f"**Genre signals:** {cover.get('genre_signals', '')}")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ Strengths:**")
        strengths = cover.get('strengths', [])
        if not isinstance(strengths, list):
            strengths = [str(strengths)]
        for s in strengths:
            st.write(f"• {s}")
    with col2:
        st.markdown("**❌ Weaknesses:**")
        weaknesses = cover.get('weaknesses', [])
        if not isinstance(weaknesses, list):
            weaknesses = [str(weaknesses)]
        for w in weaknesses:
            st.write(f"• {w}")
    
    st.markdown("**💡 Suggestions:**")
    suggestions = cover.get('suggestions', [])
    if not isinstance(suggestions, list):
        suggestions = [str(suggestions)]
    for s in suggestions:
        st.write(f"• {s}")


def show_reader_avatar(avatar):
    if not avatar or not isinstance(avatar, dict):
        st.info("No reader avatar")
        return
    
    primary = avatar.get('primary', {})
    if not isinstance(primary, dict):
        primary = {}
        
    st.markdown("### 👤 Primary Reader")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Name:** {primary.get('name', '')}")
        st.write(f"**Age:** {primary.get('age', '')}")
        st.write(f"**Occupation:** {primary.get('occupation', '')}")
    with col2:
        st.write(f"**Seeks:** {primary.get('what_she_seeks', '')}")
        st.write(f"**Hangs out:** {primary.get('where_she_hangs_out', '')}")
        st.write(f"**Avoids:** {primary.get('what_she_avoids', '')}")


def show_market_position(position):
    if not position or not isinstance(position, dict):
        st.info("No market position")
        return
    
    st.write(f"**Shelf:** {position.get('primary_shelf', '')}")
    st.write(f"**Positioning:** {position.get('positioning_statement', '')}")
    st.markdown("### 📚 Comparable")
    
    comps = position.get('comp_titles', [])
    if not isinstance(comps, list):
        comps = []
        
    for comp in comps:
        if isinstance(comp, dict):
            st.write(f"• **{comp.get('title', '')}**")
            st.write(f"  Similar: {comp.get('similarity', '')}")
            st.write(f"  Different: {comp.get('difference', '')}")


def show_keywords(keywords):
    if not keywords or not isinstance(keywords, dict):
        st.info("No keywords")
        return
    
    st.markdown("**🔑 Amazon Keywords:**")
    amazon_keywords = keywords.get('amazon_keywords', [])
    if not isinstance(amazon_keywords, list):
        amazon_keywords = [str(amazon_keywords)]
    for k in amazon_keywords:
        st.write(f"• {k}")


def show_blurb_analysis(blurb):
    if not blurb or not isinstance(blurb, dict):
        st.info("No blurb")
        return
    
    score = blurb.get('score', 0)
    if not isinstance(score, (int, float)):
        score = 0
    st.metric("Score", f"{score}/100")
    st.markdown("**✨ Optimized:**")
    st.info(blurb.get('optimized_version', ''))


def show_channel_strategy(strategies):
    if not strategies or not isinstance(strategies, dict):
        st.info("No strategies")
        return
    
    for channel, data in strategies.items():
        with st.expander(f"📱 {channel.title()}"):
            st.json(data)


def show_timeline(timeline):
    if not timeline or not isinstance(timeline, dict):
        st.info("No timeline")
        return
    
    phases = [
        ("6_months_out", "6 Months Before"),
        ("3_months_out", "3 Months Before"),
        ("1_month_out", "1 Month Before"),
        ("launch_week", "Launch Week"),
        ("post_launch", "Post-Launch")
    ]
    
    for key, name in phases:
        tasks = timeline.get(key, [])
        if not isinstance(tasks, list):
            tasks = []
        if tasks:
            with st.expander(f"📅 {name}"):
                for task in tasks:
                    st.write(f"• {task}")


def show_assets(assets):
    if not assets or not isinstance(assets, dict):
        st.info("No assets")
        return
    
    for asset_type, content in assets.items():
        with st.expander(f"📎 {asset_type.title()}"):
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            st.write(f"**{k}:** {v}")
                    else:
                        st.write(item)
            elif isinstance(content, dict):
                for k, v in content.items():
                    st.write(f"**{k}:** {v}")
            else:
                st.write(content)


def extract_text_preview(file):
    try:
        if "pdf" in file.type:
            pdf_reader = PyPDF2.PdfReader(file)
            return pdf_reader.pages[0].extract_text()[:500]
        elif "document" in file.type:
            doc = docx.Document(file)
            return doc.paragraphs[0].text[:500] if doc.paragraphs else ""
        else:
            return file.getvalue().decode("utf-8")[:500]
    except:
        return "Preview unavailable"


def extract_full_text(bytes_data, file_type):
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

# BookAnalyzer.py
import streamlit as st
from openai import OpenAI
import PyPDF2
import docx
import json
import time
import base64
from PIL import Image
import io
from typing import Optional, Dict, List

def show_analyzer():
    """Main book analyzer with cover vision and deep analysis"""
    
    if st.session_state.get('current_page') != "📖 Book Analyzer":
        return
    
    # Initialize session state
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    if 'cover_analysis' not in st.session_state:
        st.session_state.cover_analysis = None
    
    if 'generated_assets' not in st.session_state:
        st.session_state.generated_assets = None
    
    if 'edited_assets' not in st.session_state:
        st.session_state.edited_assets = None
    
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    
    # Header
    st.title("📖 Book Analyzer & Marketing Engine")
    st.markdown("Upload your manuscript and cover for complete AI analysis and multi-platform marketing assets")
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
    
    # If analysis is complete, show results with tabs
    if st.session_state.analysis_complete and st.session_state.analysis_result:
        st.success("✅ Analysis complete! Your book has been analyzed and marketing assets generated.")
        
        tab1, tab2, tab3 = st.tabs(["📊 Book Analysis", "🚀 Marketing Assets", "✏️ Edit Assets"])
        
        with tab1:
            show_analysis_results(st.session_state.analysis_result, st.session_state.cover_analysis)
        
        with tab2:
            if st.session_state.generated_assets:
                show_assets_readonly(st.session_state.generated_assets)
            else:
                if st.button("🎬 Generate Marketing Assets", type="primary"):
                    with st.spinner("Generating marketing assets..."):
                        client = OpenAI(api_key=st.session_state.openai_api_key)
                        assets = generate_all_assets(client, st.session_state.analysis_result)
                        st.session_state.generated_assets = assets
                        st.session_state.edited_assets = assets.copy()
                        st.rerun()
        
        with tab3:
            if st.session_state.edited_assets:
                show_assets_editable(st.session_state.edited_assets)
            else:
                st.info("Generate assets first to edit them")
        
        # Button for new analysis
        if st.button("🔄 Analyze Another Book", use_container_width=True):
            st.session_state.analysis_complete = False
            st.session_state.analysis_result = None
            st.session_state.cover_analysis = None
            st.session_state.generated_assets = None
            st.session_state.edited_assets = None
            st.rerun()
        return
    
    # Main upload area
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📄 Manuscript")
        manuscript_file = st.file_uploader(
            "Upload PDF, DOCX, or TXT",
            type=['pdf', 'docx', 'txt'],
            key="manuscript_file"
        )
        
        if manuscript_file:
            st.success(f"✅ Loaded: {manuscript_file.name}")
    
    with col2:
        st.markdown("### 🎨 Cover Image")
        cover_file = st.file_uploader(
            "Upload JPG or PNG",
            type=['jpg', 'jpeg', 'png'],
            key="cover_file"
        )
        
        if cover_file:
            st.success(f"✅ Loaded: {cover_file.name}")
            image = Image.open(cover_file)
            st.image(image, caption="Cover Preview", width=150)
    
    st.markdown("---")
    
    # Analyze button
    if manuscript_file and cover_file:
        cost_estimate = "$0.50-$1.00 for complete analysis + assets"
        st.info(f"💰 Estimated API cost: {cost_estimate}")
        
        if st.button("🔍 ANALYZE BOOK & GENERATE ASSETS", type="primary", use_container_width=True):
            with st.spinner("Analyzing your book... (this takes about 60 seconds)"):
                # Extract text
                manuscript_text = extract_text(manuscript_file)
                
                # Encode cover
                cover_bytes = cover_file.getvalue()
                cover_base64 = base64.b64encode(cover_bytes).decode('utf-8')
                
                # Initialize OpenAI
                client = OpenAI(api_key=st.session_state.openai_api_key)
                
                # Step 1: Analyze cover with vision
                cover_analysis = analyze_cover(client, cover_base64)
                st.session_state.cover_analysis = cover_analysis
                
                # Step 2: Deep manuscript analysis
                analysis = analyze_manuscript_deep(client, manuscript_text, cover_analysis)
                st.session_state.analysis_result = analysis
                
                # Step 3: Generate marketing assets
                assets = generate_all_assets(client, analysis)
                st.session_state.generated_assets = assets
                st.session_state.edited_assets = assets.copy()
                
                # Mark complete
                st.session_state.analysis_complete = True
                st.rerun()
    else:
        st.info("👆 Please upload both manuscript and cover to begin")


def analyze_cover(client, cover_base64):
    """Analyze cover with vision"""
    
    prompt = """Analyze this book cover in detail. Return JSON with:
    {
        "colors": ["list of dominant colors"],
        "has_figure": true/false,
        "figure_description": "description if any figures present",
        "typography": "description of font style",
        "composition": "how elements are arranged",
        "mood": "emotional feeling",
        "genre_signals": "what genre this suggests",
        "strengths": ["3 specific strengths"],
        "weaknesses": ["3 specific weaknesses"],
        "suggestions": ["3 improvements"]
    }"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
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
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "colors": ["Error analyzing"],
            "has_figure": False,
            "figure_description": f"Error: {str(e)}",
            "typography": "Error",
            "composition": "Error",
            "mood": "Error",
            "genre_signals": "Error",
            "strengths": ["Unable to analyze"],
            "weaknesses": ["Vision API error"],
            "suggestions": ["Check image format", "Try again"]
        }


def analyze_manuscript_deep(client, text, cover_analysis):
    """Single comprehensive manuscript analysis"""
    
    # Truncate if needed
    if len(text) > 50000:
        text = text[:50000] + "... [truncated]"
    
    # Get beginning, middle, end for context
    total_len = len(text)
    beginning = text[:min(5000, total_len//3)]
    middle = text[total_len//3:total_len//3*2][:5000]
    ending = text[-5000:]
    
    prompt = f"""
    You are a professional literary analyst. Analyze this book in depth.
    
    COVER ANALYSIS (for context):
    {json.dumps(cover_analysis, indent=2)}
    
    MANUSCRIPT EXCERPTS:
    
    BEGINNING:
    {beginning}
    
    MIDDLE:
    {middle}
    
    ENDING:
    {ending}
    
    Based on these excerpts, provide a COMPLETE analysis as JSON with:
    
    1. book_info: {{
        "title": "suggested or detected title",
        "genre": "primary genre",
        "subgenres": ["subgenre1", "subgenre2"],
        "tone": "overall emotional tone",
        "writing_style": "descriptive/lyrical/direct/etc",
        "pacing": "fast/medium/slow with explanation"
    }}
    
    2. characters: {{
        "main": [
            {{"name": "name", "role": "protagonist/antagonist/etc", 
              "description": "who they are", "arc": "how they change"}}
        ],
        "supporting": ["list of supporting characters"],
        "relationships": ["key dynamics"]
    }}
    
    3. plot: {{
        "opening_hook": "what grabs attention",
        "inciting_incident": "what starts the story",
        "major_plot_points": ["point1", "point2", "point3"],
        "climax": "the big moment",
        "resolution": "how it ends"
    }}
    
    4. themes: {{
        "primary": ["main themes with explanation"],
        "secondary": ["other themes"],
        "motifs": ["recurring elements"]
    }}
    
    5. strengths: ["5 specific strengths of this manuscript with examples"]
    
    6. areas_for_improvement: ["5 specific weaknesses with suggestions"]
    
    7. target_audience: {{
        "primary": "who will love this",
        "appeal": "why they'll love it",
        "comparable_titles": [
            {{"title": "Book 1", "similarity": "how it's similar", "difference": "how it's different"}},
            {{"title": "Book 2", "similarity": "how it's similar", "difference": "how it's different"}}
        ]
    }}
    
    8. marketing: {{
        "unique_selling_points": ["what makes it special"],
        "keyword_cloud": ["amazon_keywords"],
        "compelling_quotes": ["3 actual or potential pull quotes"]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a literary analyst. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return None


def generate_all_assets(client, analysis):
    """Generate marketing assets for ALL platforms"""
    
    prompt = f"""
    Based on this book analysis, create comprehensive marketing assets for ALL platforms.
    
    ANALYSIS:
    {json.dumps(analysis, indent=2)}
    
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


def extract_text(file) -> str:
    """Extract text from uploaded file"""
    try:
        if file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
            
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(file)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
            
        else:  # txt
            return file.getvalue().decode("utf-8")
            
    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        return ""


def show_analysis_results(analysis, cover):
    """Display analysis results"""
    
    # Cover Analysis Summary
    if cover:
        with st.expander("🎨 Cover Analysis", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Colors:** {', '.join(cover.get('colors', []))}")
                st.write(f"**Mood:** {cover.get('mood', '')}")
                st.write(f"**Genre signals:** {cover.get('genre_signals', '')}")
            with col2:
                st.write(f"**Typography:** {cover.get('typography', '')}")
                st.write(f"**Composition:** {cover.get('composition', '')}")
                if cover.get('has_figure'):
                    st.write(f"**Figure:** {cover.get('figure_description', '')}")
    
    # Book Info
    book_info = analysis.get('book_info', {})
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📖 Book Info")
        st.write(f"**Title:** {book_info.get('title', 'N/A')}")
        st.write(f"**Genre:** {book_info.get('genre', 'N/A')}")
        st.write(f"**Subgenres:** {', '.join(book_info.get('subgenres', []))}")
    with col2:
        st.write(f"**Tone:** {book_info.get('tone', 'N/A')}")
        st.write(f"**Style:** {book_info.get('writing_style', 'N/A')}")
        st.write(f"**Pacing:** {book_info.get('pacing', 'N/A')}")
    
    # Characters
    chars = analysis.get('characters', {})
    with st.expander("👥 Characters", expanded=True):
        for char in chars.get('main', []):
            st.markdown(f"**{char.get('name', 'Unknown')}** ({char.get('role', '')})")
            st.write(char.get('description', ''))
            st.write(f"*Arc:* {char.get('arc', '')}")
            st.divider()
    
    # Plot & Themes
    col1, col2 = st.columns(2)
    with col1:
        plot = analysis.get('plot', {})
        st.markdown("### 📊 Plot")
        st.write(f"**Opening:** {plot.get('opening_hook', '')}")
        st.write(f"**Inciting Incident:** {plot.get('inciting_incident', '')}")
        st.write("**Major Points:**")
        for point in plot.get('major_plot_points', []):
            st.write(f"• {point}")
        st.write(f"**Climax:** {plot.get('climax', '')}")
        st.write(f"**Resolution:** {plot.get('resolution', '')}")
    
    with col2:
        themes = analysis.get('themes', {})
        st.markdown("### 🎨 Themes")
        st.write("**Primary:**")
        for theme in themes.get('primary', []):
            st.write(f"• {theme}")
        st.write("**Secondary:**")
        for theme in themes.get('secondary', []):
            st.write(f"• {theme}")
    
    # Target Audience
    target = analysis.get('target_audience', {})
    with st.expander("🎯 Target Audience"):
        st.write(f"**Primary:** {target.get('primary', 'N/A')}")
        st.write(f"**Appeal:** {target.get('appeal', 'N/A')}")
        st.write("**Comparable Titles:**")
        for comp in target.get('comparable_titles', []):
            st.write(f"• **{comp.get('title', '')}**")
            st.write(f"  Similar: {comp.get('similarity', '')}")
            st.write(f"  Different: {comp.get('difference', '')}")
    
    # Strengths & Improvements
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ✅ Strengths")
        for s in analysis.get('strengths', []):
            st.write(f"• {s}")
    with col2:
        st.markdown("### 📝 Areas to Improve")
        for i in analysis.get('areas_for_improvement', []):
            st.write(f"• {i}")


def show_assets_readonly(assets):
    """Display generated assets in read-only mode"""
    
    platform_tabs = st.tabs([
        "📝 Blurb", "🎬 TikTok", "📸 Instagram", "🛒 Amazon", 
        "📧 Email", "📢 Facebook", "📰 Press", "📌 Pinterest", "📚 Goodreads", "🎙️ Podcast"
    ])
    
    with platform_tabs[0]:
        st.markdown("### 📝 Book Blurb")
        st.info(assets.get('blurb', 'Not generated'))
    
    with platform_tabs[1]:
        st.markdown("### 🎬 TikTok Scripts")
        for i, script in enumerate(assets.get('tiktok_scripts', [])):
            with st.expander(f"Script {i+1}"):
                for key, value in script.items():
                    if key == 'hashtags' and isinstance(value, list):
                        st.write(f"**{key.title()}:** {' '.join(value)}")
                    else:
                        st.write(f"**{key.title()}:** {value}")
    
    with platform_tabs[2]:
        st.markdown("### 📸 Instagram")
        insta = assets.get('instagram', {})
        if insta.get('posts'):
            st.write("**Posts:**")
            for post in insta['posts']:
                st.json(post)
        if insta.get('reels'):
            st.write("**Reels:**")
            for reel in insta['reels']:
                st.json(reel)
    
    with platform_tabs[3]:
        st.markdown("### 🛒 Amazon")
        amazon = assets.get('amazon', {})
        st.json(amazon)
    
    with platform_tabs[4]:
        st.markdown("### 📧 Email Sequence")
        emails = assets.get('email_sequence', {})
        for name, email in emails.items():
            with st.expander(f"📨 {name.title()}"):
                st.json(email)
    
    with platform_tabs[5]:
        st.markdown("### 📢 Facebook Ads")
        for ad in assets.get('facebook_ads', []):
            st.json(ad)
    
    with platform_tabs[6]:
        st.markdown("### 📰 Press Kit")
        press = assets.get('press_kit', {})
        st.json(press)
    
    with platform_tabs[7]:
        st.markdown("### 📌 Pinterest")
        pinterest = assets.get('pinterest', {})
        st.json(pinterest)
    
    with platform_tabs[8]:
        st.markdown("### 📚 Goodreads")
        goodreads = assets.get('goodreads', {})
        st.json(goodreads)
    
    with platform_tabs[9]:
        st.markdown("### 🎙️ Podcast Pitch")
        podcast = assets.get('podcast_pitch', {})
        st.json(podcast)


def show_assets_editable(assets):
    """Display generated assets in editable mode"""
    
    st.markdown("### ✏️ Edit Your Marketing Assets")
    st.caption("Changes are saved automatically in this session")
    
    platform_tabs = st.tabs([
        "📝 Blurb", "🎬 TikTok", "📸 Instagram", "🛒 Amazon", 
        "📧 Email", "📢 Facebook", "📰 Press", "📌 Pinterest", "📚 Goodreads", "🎙️ Podcast"
    ])
    
    with platform_tabs[0]:
        st.markdown("### 📝 Book Blurb")
        assets['blurb'] = st.text_area("Edit your blurb", assets.get('blurb', ''), height=200)
    
    with platform_tabs[1]:
        st.markdown("### 🎬 TikTok Scripts")
        for i, script in enumerate(assets.get('tiktok_scripts', [])):
            with st.expander(f"Script {i+1}"):
                if isinstance(script, dict):
                    for key, value in script.items():
                        if key == 'hashtags' and isinstance(value, list):
                            tag_string = ' '.join(value)
                            edited_tags = st.text_input(f"{key.title()}", tag_string, key=f"tiktok_{i}_{key}")
                            script[key] = edited_tags.split()
                        else:
                            script[key] = st.text_input(f"{key.title()}", str(value), key=f"tiktok_{i}_{key}")
    
    with platform_tabs[2]:
        st.markdown("### 📸 Instagram")
        insta = assets.get('instagram', {})
        if insta.get('posts'):
            for j, post in enumerate(insta['posts']):
                with st.expander(f"Post {j+1}"):
                    if isinstance(post, dict):
                        for key, value in post.items():
                            if key == 'hashtags' and isinstance(value, list):
                                tag_string = ' '.join(value)
                                edited_tags = st.text_input(f"{key.title()}", tag_string, key=f"insta_post_{j}_{key}")
                                post[key] = edited_tags.split()
                            else:
                                post[key] = st.text_input(f"{key.title()}", str(value), key=f"insta_post_{j}_{key}")
    
    with platform_tabs[3]:
        st.markdown("### 🛒 Amazon")
        amazon = assets.get('amazon', {})
        if isinstance(amazon, dict):
            for key, value in amazon.items():
                if key == 'search_terms' and isinstance(value, list):
                    term_string = ', '.join(value)
                    edited_terms = st.text_input(f"{key.replace('_', ' ').title()}", term_string, key=f"amazon_{key}")
                    amazon[key] = [t.strip() for t in edited_terms.split(',')]
                elif key == 'categories' and isinstance(value, list):
                    cat_string = ', '.join(value)
                    edited_cats = st.text_input(f"{key.title()}", cat_string, key=f"amazon_{key}")
                    amazon[key] = [c.strip() for c in edited_cats.split(',')]
                elif isinstance(value, dict):
                    st.json(value)  # Skip editing nested for simplicity
                else:
                    amazon[key] = st.text_input(f"{key.replace('_', ' ').title()}", str(value), key=f"amazon_{key}")
    
    with platform_tabs[4]:
        st.markdown("### 📧 Email Sequence")
        emails = assets.get('email_sequence', {})
        for name, email in emails.items():
            with st.expander(f"📨 {name.title()}"):
                if isinstance(email, dict):
                    for key, value in email.items():
                        email[key] = st.text_area(f"{key.title()}", str(value), height=100 if key == 'body' else 50, key=f"email_{name}_{key}")
    
    with platform_tabs[5]:
        st.markdown("### 📢 Facebook Ads")
        for i, ad in enumerate(assets.get('facebook_ads', [])):
            with st.expander(f"Ad {i+1}"):
                if isinstance(ad, dict):
                    for key, value in ad.items():
                        ad[key] = st.text_input(f"{key.title()}", str(value), key=f"fb_ad_{i}_{key}")
    
    with platform_tabs[6]:
        st.markdown("### 📰 Press Kit")
        press = assets.get('press_kit', {})
        if isinstance(press, dict):
            for key, value in press.items():
                if key == 'author_qanda' and isinstance(value, list):
                    for j, qa in enumerate(value):
                        with st.expander(f"Q&A {j+1}"):
                            if isinstance(qa, dict):
                                qa['question'] = st.text_input("Question", qa.get('question', ''), key=f"press_qa_{j}_q")
                                qa['answer'] = st.text_area("Answer", qa.get('answer', ''), height=80, key=f"press_qa_{j}_a")
                elif key == 'key_talking_points' and isinstance(value, list):
                    point_string = '\n'.join(value)
                    edited_points = st.text_area("Key Talking Points", point_string, height=100, key=f"press_{key}")
                    press[key] = edited_points.split('\n')
                else:
                    press[key] = st.text_area(f"{key.replace('_', ' ').title()}", str(value), height=100, key=f"press_{key}")
    
    with platform_tabs[7]:
        st.markdown("### 📌 Pinterest")
        pinterest = assets.get('pinterest', {})
        if isinstance(pinterest, dict):
            for key, value in pinterest.items():
                if isinstance(value, list):
                    list_string = '\n'.join(value)
                    edited_list = st.text_area(f"{key.replace('_', ' ').title()}", list_string, height=80, key=f"pinterest_{key}")
                    pinterest[key] = edited_list.split('\n')
                else:
                    pinterest[key] = st.text_input(f"{key.replace('_', ' ').title()}", str(value), key=f"pinterest_{key}")
    
    with platform_tabs[8]:
        st.markdown("### 📚 Goodreads")
        goodreads = assets.get('goodreads', {})
        if isinstance(goodreads, dict):
            for key, value in goodreads.items():
                if isinstance(value, list):
                    list_string = '\n'.join(value)
                    edited_list = st.text_area(f"{key.replace('_', ' ').title()}", list_string, height=80, key=f"goodreads_{key}")
                    goodreads[key] = edited_list.split('\n')
                else:
                    goodreads[key] = st.text_area(f"{key.replace('_', ' ').title()}", str(value), height=100, key=f"goodreads_{key}")
    
    with platform_tabs[9]:
        st.markdown("### 🎙️ Podcast Pitch")
        podcast = assets.get('podcast_pitch', {})
        if isinstance(podcast, dict):
            for key, value in podcast.items():
                if isinstance(value, list):
                    list_string = '\n'.join(value)
                    edited_list = st.text_area(f"{key.replace('_', ' ').title()}", list_string, height=80, key=f"podcast_{key}")
                    podcast[key] = edited_list.split('\n')
                else:
                    podcast[key] = st.text_area(f"{key.replace('_', ' ').title()}", str(value), height=100, key=f"podcast_{key}")
    
    st.success("✅ Edits saved in current session")

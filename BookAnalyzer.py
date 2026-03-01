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
    
    # Header
    st.title("📖 Book Analyzer")
    st.markdown("Upload your manuscript and cover for complete AI analysis")
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
        if st.button("🔍 ANALYZE BOOK", type="primary", use_container_width=True):
            with st.spinner("Analyzing your book... (this takes about 30 seconds)"):
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
                
                # Step 2: Deep manuscript analysis (single comprehensive call)
                analysis = analyze_manuscript_deep(client, manuscript_text, cover_analysis)
                st.session_state.analysis_result = analysis
                
                st.success("✅ Analysis complete!")
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
    
    # Truncate if needed (gpt-4o-mini has 128k context, so this is generous)
    if len(text) > 50000:
        text = text[:50000] + "... [truncated]"
        st.warning("Long manuscript truncated to 50,000 characters")
    
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
        "compelling_quotes": ["3 actual or potential pull quotes"],
        "blurb": "150-word compelling book description"
    }}
    
    9. tiktok_strategy: {{
        "content_pillars": ["3 angles for videos"],
        "script_ideas": [
            {{"hook": "attention grabber", "visual": "what to show", "voiceover": "script"}},
            {{"hook": "another angle", "visual": "what to show", "voiceover": "script"}}
        ],
        "hashtags": ["relevant hashtags"]
    }}
    
    Be specific. Reference actual elements from the excerpts. Make this feel like a REAL analysis of THIS book.
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


def show_results():
    """Display analysis results"""
    
    if not st.session_state.analysis_result:
        st.info("No analysis yet. Upload and analyze a book first.")
        return
    
    analysis = st.session_state.analysis_result
    cover = st.session_state.cover_analysis
    
    # Title and export
    title = analysis.get('book_info', {}).get('title', 'Your Book')
    st.success(f"✅ Analysis Complete: **{title}**")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Copy Summary", use_container_width=True):
            st.info("Copy to clipboard feature coming")
    with col2:
        if st.button("🔄 New Analysis", use_container_width=True):
            st.session_state.analysis_result = None
            st.session_state.cover_analysis = None
            st.rerun()
    
    st.divider()
    
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
    
    # Main tabs
    tabs = st.tabs([
        "📖 Book Info", "👥 Characters", "📊 Plot & Themes",
        "🎯 Target Market", "📝 Marketing", "🎬 TikTok Strategy"
    ])
    
    # Tab 1: Book Info
    with tabs[0]:
        book_info = analysis.get('book_info', {})
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Title:** " + book_info.get('title', 'N/A'))
            st.markdown("**Genre:** " + book_info.get('genre', 'N/A'))
            st.markdown("**Subgenres:** " + ', '.join(book_info.get('subgenres', [])))
        with col2:
            st.markdown("**Tone:** " + book_info.get('tone', 'N/A'))
            st.markdown("**Writing Style:** " + book_info.get('writing_style', 'N/A'))
            st.markdown("**Pacing:** " + book_info.get('pacing', 'N/A'))
    
    # Tab 2: Characters
    with tabs[1]:
        chars = analysis.get('characters', {})
        st.markdown("### Main Characters")
        for char in chars.get('main', []):
            with st.expander(f"**{char.get('name', 'Unknown')}** - {char.get('role', '')}"):
                st.write(char.get('description', ''))
                st.write(f"*Arc:* {char.get('arc', '')}")
        
        if chars.get('supporting'):
            st.markdown("### Supporting Characters")
            for char in chars.get('supporting', []):
                st.write(f"• {char}")
        
        if chars.get('relationships'):
            st.markdown("### Key Relationships")
            for rel in chars.get('relationships', []):
                st.write(f"• {rel}")
    
    # Tab 3: Plot & Themes
    with tabs[2]:
        plot = analysis.get('plot', {})
        themes = analysis.get('themes', {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Plot")
            st.markdown(f"**Opening Hook:** {plot.get('opening_hook', '')}")
            st.markdown(f"**Inciting Incident:** {plot.get('inciting_incident', '')}")
            st.markdown("**Major Plot Points:**")
            for point in plot.get('major_plot_points', []):
                st.write(f"• {point}")
            st.markdown(f"**Climax:** {plot.get('climax', '')}")
            st.markdown(f"**Resolution:** {plot.get('resolution', '')}")
        
        with col2:
            st.markdown("### Themes")
            st.markdown("**Primary:**")
            for theme in themes.get('primary', []):
                st.write(f"• {theme}")
            st.markdown("**Secondary:**")
            for theme in themes.get('secondary', []):
                st.write(f"• {theme}")
            if themes.get('motifs'):
                st.markdown("**Motifs:**")
                for motif in themes.get('motifs', []):
                    st.write(f"• {motif}")
    
    # Tab 4: Target Market
    with tabs[3]:
        target = analysis.get('target_audience', {})
        st.markdown(f"**Primary Audience:** {target.get('primary', 'N/A')}")
        st.markdown(f"**Appeal:** {target.get('appeal', 'N/A')}")
        
        st.markdown("### Comparable Titles")
        for comp in target.get('comparable_titles', []):
            with st.expander(f"**{comp.get('title', '')}**"):
                st.write(f"Similar: {comp.get('similarity', '')}")
                st.write(f"Different: {comp.get('difference', '')}")
        
        strengths = analysis.get('strengths', [])
        if strengths:
            st.markdown("### Strengths")
            for s in strengths:
                st.write(f"✅ {s}")
        
        improvements = analysis.get('areas_for_improvement', [])
        if improvements:
            st.markdown("### Areas for Improvement")
            for i in improvements:
                st.write(f"📝 {i}")
    
    # Tab 5: Marketing
    with tabs[4]:
        marketing = analysis.get('marketing', {})
        
        st.markdown("### Unique Selling Points")
        for usp in marketing.get('unique_selling_points', []):
            st.write(f"✨ {usp}")
        
        st.markdown("### Keywords")
        keywords = marketing.get('keyword_cloud', [])
        st.write(', '.join(keywords))
        
        st.markdown("### Compelling Quotes")
        for quote in marketing.get('compelling_quotes', []):
            st.info(f"“{quote}”")
        
        st.markdown("### Book Blurb")
        st.success(marketing.get('blurb', 'N/A'))
    
    # Tab 6: TikTok Strategy
    with tabs[5]:
        tiktok = analysis.get('tiktok_strategy', {})
        
        st.markdown("### Content Pillars")
        for pillar in tiktok.get('content_pillars', []):
            st.write(f"📌 {pillar}")
        
        st.markdown("### Script Ideas")
        for i, script in enumerate(tiktok.get('script_ideas', []), 1):
            with st.expander(f"Script {i}"):
                st.write(f"**Hook:** {script.get('hook', '')}")
                st.write(f"**Visual:** {script.get('visual', '')}")
                st.write(f"**Voiceover:** {script.get('voiceover', '')}")
        
        st.markdown("### Hashtags")
        hashtags = tiktok.get('hashtags', [])
        st.write(' '.join(hashtags))


# Main execution
if __name__ == "__main__":
    # This allows the script to be imported or run directly
    pass

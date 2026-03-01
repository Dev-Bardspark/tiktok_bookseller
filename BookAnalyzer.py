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
import os
from datetime import datetime

def show_analyzer():
    """Pure book analysis without marketing assets"""
    
    if st.session_state.get('current_page') != "📖 Book Analyzer":
        return
    
    # Initialize session state
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    if 'cover_analysis' not in st.session_state:
        st.session_state.cover_analysis = None
    
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    
    if 'current_book_id' not in st.session_state:
        st.session_state.current_book_id = None
    
    # Header
    st.title("📖 Book Analyzer")
    st.markdown("Upload your manuscript and cover for deep literary analysis")
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
    
    # If analysis is complete, show results and save option
    if st.session_state.analysis_complete and st.session_state.analysis_result:
        st.success("✅ Analysis complete! Your book has been analyzed.")
        
        col1, col2 = st.columns(2)
        with col1:
            # Show results
            show_analysis_results(st.session_state.analysis_result, st.session_state.cover_analysis)
        
        with col2:
            st.markdown("### 💾 Save Analysis")
            st.markdown("Save this analysis to use in the Marketing Generator")
            
            book_title = st.session_state.analysis_result.get('book_info', {}).get('title', 'Untitled')
            filename = st.text_input("Filename", value=f"{book_title.replace(' ', '_')}_analysis.json")
            
            if st.button("💾 Save to File", use_container_width=True):
                # Prepare data to save
                save_data = {
                    "book_info": st.session_state.analysis_result,
                    "cover_analysis": st.session_state.cover_analysis,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "book_id": st.session_state.current_book_id
                }
                
                # Save to session state for download
                st.session_state.saved_analysis = json.dumps(save_data, indent=2)
                
                # Also save to a "library" in session state
                if 'analysis_library' not in st.session_state:
                    st.session_state.analysis_library = {}
                
                st.session_state.analysis_library[filename] = save_data
                
                st.success(f"✅ Saved as {filename}")
            
            # Download button
            if 'saved_analysis' in st.session_state:
                st.download_button(
                    "📥 Download JSON",
                    st.session_state.saved_analysis,
                    filename,
                    "application/json"
                )
            
            st.markdown("---")
            st.markdown("### 📚 Next Step")
            st.markdown("Go to **Marketing Generator** to create assets from this analysis")
            
            if st.button("🔄 New Analysis", use_container_width=True):
                st.session_state.analysis_complete = False
                st.session_state.analysis_result = None
                st.session_state.cover_analysis = None
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
        cost_estimate = "$0.30-$0.50 for analysis"
        st.info(f"💰 Estimated API cost: {cost_estimate}")
        
        if st.button("🔍 ANALYZE BOOK", type="primary", use_container_width=True):
            with st.spinner("Analyzing your book... (this takes about 30 seconds)"):
                # Generate a simple book ID
                st.session_state.current_book_id = f"book_{int(time.time())}"
                
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


# For direct testing
if __name__ == "__main__":
    show_analyzer()

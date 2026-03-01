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
    
    # API Key input with instructions
    if not st.session_state.openai_api_key:
        with st.container():
            st.markdown("### 🔑 OpenAI API Key")
            
            with st.expander("📋 How to get an OpenAI API Key", expanded=True):
                st.markdown("""
                <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #667eea;">
                <h4>To get an OpenAI API key, follow these steps:</h4>
                
                <div style="margin: 8px 0; padding: 5px;">1️⃣ <strong>Go to the OpenAI Platform</strong><br>
                👉 https://platform.openai.com/</div>
                
                <div style="margin: 8px 0; padding: 5px;">2️⃣ <strong>Sign in or Create an Account</strong><br>
                Log in with your existing account or create a new one.</div>
                
                <div style="margin: 8px 0; padding: 5px;">3️⃣ <strong>Open the API Keys Page</strong><br>
                Click your profile icon (top right) → Select "View API keys"<br>
                Or go directly to: https://platform.openai.com/api-keys</div>
                
                <div style="margin: 8px 0; padding: 5px;">4️⃣ <strong>Create a New Key</strong><br>
                Click "Create new secret key" → Give it a name → Copy the key immediately</div>
                
                <div style="margin: 8px 0; padding: 5px;">🔐 <strong>Important Security Tips</strong><br>
                Never share your API key publicly</div>
                </div>
                """, unsafe_allow_html=True)
            
            api_key = st.text_input("Enter your API key", type="password", key="api_key_input")
            if api_key:
                st.session_state.openai_api_key = api_key
                st.rerun()
        return
    
    # If analysis is complete, show results
    if st.session_state.analysis_complete and st.session_state.analysis_result:
        st.success("✅ Analysis complete! Your book has been analyzed.")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            show_analysis_results(st.session_state.analysis_result, st.session_state.cover_analysis)
        
        with col2:
            st.markdown("### 💾 Save Analysis")
            st.markdown("Save this analysis to use in the Marketing Generator")
            
            book_title = st.session_state.analysis_result.get('book_info', {}).get('title', 'Untitled')
            filename = st.text_input("Filename", value=f"{book_title.replace(' ', '_')}_analysis.json")
            
            if st.button("💾 Save to Library", use_container_width=True):
                # Prepare data to save
                save_data = {
                    "book_info": st.session_state.analysis_result,
                    "cover_analysis": st.session_state.cover_analysis,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "book_id": st.session_state.current_book_id
                }
                
                # Save to library in session state
                if 'analysis_library' not in st.session_state:
                    st.session_state.analysis_library = {}
                
                st.session_state.analysis_library[filename] = save_data
                st.success(f"✅ Saved to library as {filename}")
            
            st.markdown("---")
            st.markdown("### 📚 Next Step")
            st.markdown("Go to **Marketing Assets** to create campaigns from this analysis")
            
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
    """Display analysis results in full-width layout"""
    
    # Cover Analysis - Full width at top
    if cover:
        with st.expander("🎨 Cover Analysis", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Colors:** {', '.join(cover.get('colors', []))}")
                st.write(f"**Mood:** {cover.get('mood', '')}")
            with col2:
                st.write(f"**Typography:** {cover.get('typography', '')}")
                st.write(f"**Composition:** {cover.get('composition', '')}")
            with col3:
                st.write(f"**Genre signals:** {cover.get('genre_signals', '')}")
                if cover.get('has_figure'):
                    st.write(f"**Figure:** {cover.get('figure_description', '')}")
            
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
    
    # Book Info - Full width metrics
    book_info = analysis.get('book_info', {})
    st.markdown("### 📖 Book Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Title", book_info.get('title', 'N/A'), help="Book title")
    with col2:
        st.metric("Genre", book_info.get('genre', 'N/A'), help="Primary genre")
    with col3:
        st.metric("Tone", book_info.get('tone', 'N/A'), help="Emotional atmosphere")
    with col4:
        st.metric("Pacing", book_info.get('pacing', 'N/A'), help="Story pace")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Writing Style:** {book_info.get('writing_style', 'N/A')}")
    with col2:
        subgenres = book_info.get('subgenres', [])
        st.write(f"**Subgenres:** {', '.join(subgenres) if subgenres else 'None'}")
    
    st.divider()
    
    # Characters - Grid layout
    chars = analysis.get('characters', {})
    st.markdown("### 👥 Main Characters")
    
    main_chars = chars.get('main', [])
    if main_chars:
        # Create rows of 3 characters
        for i in range(0, len(main_chars), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(main_chars):
                    char = main_chars[i + j]
                    with cols[j]:
                        with st.container():
                            st.markdown(f"**{char.get('name', 'Unknown')}** *({char.get('role', '')})*")
                            st.write(char.get('description', ''))
                            st.caption(f"Arc: {char.get('arc', '')}")
    
    # Supporting characters in expander
    if chars.get('supporting'):
        with st.expander("👥 Supporting Characters"):
            for char in chars.get('supporting', []):
                st.write(f"• {char}")
    
    if chars.get('relationships'):
        with st.expander("🔄 Key Relationships"):
            for rel in chars.get('relationships', []):
                st.write(f"• {rel}")
    
    st.divider()
    
    # Plot & Themes side by side
    col1, col2 = st.columns(2)
    
    with col1:
        plot = analysis.get('plot', {})
        st.markdown("### 📊 Plot Structure")
        
        if plot.get('opening_hook'):
            st.markdown(f"**Opening Hook:** {plot['opening_hook']}")
        
        if plot.get('inciting_incident'):
            st.markdown(f"**Inciting Incident:** {plot['inciting_incident']}")
        
        if plot.get('major_plot_points'):
            st.markdown("**Major Plot Points:**")
            for point in plot['major_plot_points']:
                st.write(f"• {point}")
        
        if plot.get('climax'):
            st.markdown(f"**Climax:** {plot['climax']}")
        
        if plot.get('resolution'):
            st.markdown(f"**Resolution:** {plot['resolution']}")
    
    with col2:
        themes = analysis.get('themes', {})
        st.markdown("### 🎨 Themes & Motifs")
        
        if themes.get('primary'):
            st.markdown("**Primary Themes:**")
            for theme in themes['primary']:
                st.write(f"• {theme}")
        
        if themes.get('secondary'):
            st.markdown("**Secondary Themes:**")
            for theme in themes['secondary']:
                st.write(f"• {theme}")
        
        if themes.get('motifs'):
            st.markdown("**Motifs:**")
            for motif in themes['motifs']:
                st.write(f"• {motif}")
    
    st.divider()
    
    # Target Audience
    target = analysis.get('target_audience', {})
    if target:
        st.markdown("### 🎯 Target Audience")
        
        col1, col2 = st.columns(2)
        with col1:
            if target.get('primary'):
                st.markdown(f"**Primary:** {target['primary']}")
            if target.get('appeal'):
                st.markdown(f"**Appeal:** {target['appeal']}")
        
        with col2:
            if target.get('comparable_titles'):
                st.markdown("**Comparable Titles:**")
                for comp in target['comparable_titles']:
                    if isinstance(comp, dict):
                        st.markdown(f"• **{comp.get('title', '')}**")
                        st.caption(f"  Similar: {comp.get('similarity', '')}")
                        st.caption(f"  Different: {comp.get('difference', '')}")
                    else:
                        st.write(f"• {comp}")
    
    st.divider()
    
    # Strengths & Areas for Improvement
    col1, col2 = st.columns(2)
    
    with col1:
        strengths = analysis.get('strengths', [])
        if strengths:
            st.markdown("### ✅ Strengths")
            for s in strengths:
                st.write(f"• {s}")
    
    with col2:
        improvements = analysis.get('areas_for_improvement', [])
        if improvements:
            st.markdown("### 📝 Areas for Improvement")
            for i in improvements:
                st.write(f"• {i}")
    
    # Marketing Insights
    marketing = analysis.get('marketing', {})
    if marketing:
        st.divider()
        st.markdown("### 📈 Marketing Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if marketing.get('unique_selling_points'):
                st.markdown("**Unique Selling Points:**")
                for usp in marketing['unique_selling_points']:
                    st.write(f"• {usp}")
        
        with col2:
            if marketing.get('keyword_cloud'):
                st.markdown("**Keywords:**")
                st.write(', '.join(marketing['keyword_cloud']))
        
        if marketing.get('compelling_quotes'):
            st.markdown("**Pull Quotes:**")
            for quote in marketing['compelling_quotes']:
                st.info(f"“{quote}”")


# For direct testing
if __name__ == "__main__":
    show_analyzer()

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
import re
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# DATABASE CONNECTION
# ============================================================================
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            port=st.secrets["postgres"]["port"],
            database=st.secrets["postgres"]["database"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"]
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

def show_analyzer():
    """Complete book analysis with marketability dashboard"""
    
    # Check login first
    if not st.session_state.get('authenticated', False):
        st.warning("🔒 Please login to access the Book Analyzer")
        if st.button("Go to Login", use_container_width=True):
            st.session_state.page = "🏠 Dashboard"
            st.rerun()
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
    
    # ============================================================================
    # AUTO-LOAD MOST RECENT ANALYSIS IF LOGGED IN
    # ============================================================================
    if st.session_state.get('authenticated', False) and not st.session_state.analysis_result:
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT * FROM user_book_analyses 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (st.session_state.user_id,))
                latest = cur.fetchone()
                if latest:
                    # Load the analysis into session state
                    analysis_result = latest['analysis_result']
                    if isinstance(analysis_result, str):
                        analysis_result = json.loads(analysis_result)
                    st.session_state.analysis_result = analysis_result
                    st.session_state.analysis_complete = True
                    st.session_state.current_book_id = f"loaded_{latest['id']}"
                    st.success(f"✅ Loaded your most recent analysis: {latest['book_title']}")
        except Exception as e:
            st.error(f"Error loading saved analysis: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    
    # Header
    st.title("📖 Book Analyzer with Marketability Dashboard")
    st.markdown("Upload your manuscript and cover for deep literary analysis with **commercial potential scoring**")
    st.markdown("---")
    
    # API Key input (only show if no key)
    if not st.session_state.openai_api_key:
        with st.container():
            st.markdown("### 🔑 OpenAI API Key")
            api_key = st.text_input("Enter your API key", type="password", key="api_key_input")
            
            with st.expander("📋 How to get an OpenAI API Key", expanded=True):
                st.markdown("""
                <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #667eea;">
                <h4>To get an OpenAI API key, follow these steps:</h4>
                <div style="margin: 8px 0; padding: 5px;">1️⃣ <strong>Go to the OpenAI Platform</strong><br>👉 https://platform.openai.com/</div>
                <div style="margin: 8px 0; padding: 5px;">2️⃣ <strong>Sign in or Create an Account</strong><br>Log in with your existing account or create a new one.</div>
                <div style="margin: 8px 0; padding: 5px;">3️⃣ <strong>Open the API Keys Page</strong><br>Click your profile icon (top right) → Select "View API keys"</div>
                <div style="margin: 8px 0; padding: 5px;">4️⃣ <strong>Create a New Key</strong><br>Click "Create new secret key" → Give it a name → Copy the key immediately</div>
                </div>
                """, unsafe_allow_html=True)
            
            if api_key:
                st.session_state.openai_api_key = api_key
                st.rerun()
        return
    
    # If analysis is complete, show results
    if st.session_state.analysis_complete and st.session_state.analysis_result:
        show_results()  # This calls your original COMPLETE results function
        return
    
    # Otherwise show upload screen
    show_upload_screen()


def show_upload_screen():
    """Show only the upload interface"""
    
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
        cost_estimate = "$0.35-$0.60 for analysis with marketability scoring"
        st.info(f"💰 Estimated API cost: {cost_estimate}")
        
        if st.button("🔍 ANALYZE BOOK WITH MARKETABILITY SCORE", type="primary", use_container_width=True):
            with st.spinner("Analyzing your book with marketability scoring... (this takes about 45 seconds)"):
                st.session_state.current_book_id = f"book_{int(time.time())}"
                
                manuscript_text = extract_text(manuscript_file)
                cover_bytes = cover_file.getvalue()
                cover_base64 = base64.b64encode(cover_bytes).decode('utf-8')
                
                client = OpenAI(api_key=st.session_state.openai_api_key)
                
                cover_analysis = analyze_cover(client, cover_base64)
                st.session_state.cover_analysis = cover_analysis
                
                analysis = analyze_manuscript_complete(client, manuscript_text, cover_analysis)
                st.session_state.analysis_result = analysis
                st.session_state.analysis_complete = True
                
                # AUTO-SAVE to database if logged in
                if st.session_state.get('authenticated', False):
                    conn = None
                    cur = None
                    try:
                        book_title = analysis.get('book_info', {}).get('title', 'Untitled')
                        conn = get_db_connection()
                        if conn:
                            cur = conn.cursor()
                            cur.execute("""
                                INSERT INTO user_book_analyses 
                                (user_id, book_title, analysis_result, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                st.session_state.user_id,
                                book_title,
                                json.dumps(analysis),
                                datetime.now(),
                                datetime.now()
                            ))
                            conn.commit()
                            st.success("✅ Analysis auto-saved to your library!")
                    except Exception as e:
                        st.error(f"Auto-save failed: {e}")
                    finally:
                        if cur:
                            cur.close()
                        if conn:
                            conn.close()
                
                st.rerun()
    else:
        st.info("👆 Please upload both manuscript and cover to begin")


def show_results():
    """YOUR ORIGINAL COMPLETE results display - FULLY RESTORED"""
    
    st.success("✅ Analysis complete!")
    
    # Show marketability dashboard
    show_marketability_dashboard(st.session_state.analysis_result)
    
    # Then show complete literary analysis in expander
    with st.expander("📚 View Complete Literary Analysis", expanded=False):
        show_complete_analysis(st.session_state.analysis_result, st.session_state.cover_analysis)
    
    # Navigation buttons
    col1, col2, col3, col4 = st.columns(4)
    with col2:
        if st.button("🎨 Marketing Assets", use_container_width=True):
            st.session_state.page = "🎨 Marketing Assets"
            st.rerun()
    with col3:
        if st.button("🔄 New Analysis", use_container_width=True):
            st.session_state.analysis_complete = False
            st.session_state.analysis_result = None
            st.session_state.cover_analysis = None
            st.rerun()


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


def analyze_manuscript_complete(client, text, cover_analysis):
    """Complete manuscript analysis"""
    
    if len(text) > 50000:
        text = text[:50000] + "... [truncated]"
    
    total_len = len(text)
    beginning = text[:min(5000, total_len//3)]
    middle = text[total_len//3:total_len//3*2][:5000]
    ending = text[-5000:]
    
    prompt = f"""
    You are a professional literary analyst. Analyze this book based SOLELY on the manuscript excerpts provided.
    
    COVER ANALYSIS (for context):
    {json.dumps(cover_analysis, indent=2)}
    
    MANUSCRIPT EXCERPTS:
    
    BEGINNING:
    {beginning}
    
    MIDDLE:
    {middle}
    
    ENDING:
    {ending}
    
    Based ONLY on these excerpts, provide analysis as JSON with these sections.
    IMPORTANT: Do NOT include comparable successes, comparable bestsellers, or any external book titles.
    
    Return EXACTLY this structure:
    
    {{
        "marketability": {{
            "overall_score": 85,
            "overall_grade": "A-",
            "overall_assessment": "Brief summary based on manuscript quality",
            "scores": {{
                "writing_quality": {{"score": 88, "explanation": "Based on prose quality in excerpts", "strengths": ["specific strength from text"], "weaknesses": ["specific weakness from text"]}},
                "commercial_potential": {{"score": 82, "explanation": "Based on hook and pacing", "strengths": [], "weaknesses": []}},
                "genre_fit": {{"score": 90, "explanation": "How well it matches genre conventions", "strengths": [], "weaknesses": []}},
                "hook_strength": {{"score": 85, "explanation": "Based on opening", "strengths": [], "weaknesses": []}},
                "character_appeal": {{"score": 80, "explanation": "Based on character depth shown", "strengths": [], "weaknesses": []}},
                "pacing": {{"score": 75, "explanation": "Based on flow of excerpts", "strengths": [], "weaknesses": []}},
                "originality": {{"score": 70, "explanation": "Unique elements observed", "strengths": [], "weaknesses": []}},
                "target_audience_appeal": {{"score": 85, "explanation": "Appeal to genre readers", "strengths": [], "weaknesses": []}}
            }},
            "market_gap_analysis": "Where this book fits based on its themes",
            "competitive_advantage": "What makes it stand out based on excerpts",
            "potential_challenges": ["Challenge 1 based on manuscript weaknesses", "Challenge 2 based on manuscript weaknesses"]
        }},
        
        "writing_quality_detailed": {{
            "prose_quality": "Assessment of sentence-level writing from excerpts",
            "dialogue": "Quality and naturalness of dialogue from excerpts",
            "description": "Quality of descriptive passages from excerpts",
            "voice": "Strength and consistency of narrative voice from excerpts",
            "technical_execution": "Grammar, punctuation, formatting",
            "strengths": ["Specific writing strengths observed"],
            "improvements": ["Specific writing improvements needed"]
        }},
        
        "title_analysis": {{
            "current_title": "Title detected or suggested from content",
            "title_effectiveness": {{
                "score": 70,
                "memorability": "Assessment based on title",
                "genre_appropriateness": "Assessment based on genre",
                "uniqueness": "Assessment",
                "searchability": "Assessment"
            }},
            "suggested_titles": [
                {{"title": "Alternative Title 1", "rationale": "Based on book's themes", "estimated_impact": "High"}},
                {{"title": "Alternative Title 2", "rationale": "Based on book's themes", "estimated_impact": "High"}},
                {{"title": "Alternative Title 3", "rationale": "Based on book's themes", "estimated_impact": "Medium"}},
                {{"title": "Alternative Title 4", "rationale": "Based on book's themes", "estimated_impact": "Medium"}},
                {{"title": "Alternative Title 5", "rationale": "Based on book's themes", "estimated_impact": "Low"}}
            ],
            "title_change_recommendation": "Should the title be changed? Why?",
            "subtitle_suggestion": "If applicable, a subtitle suggestion"
        }},
        
        "salability_analysis": {{
            "estimated_market_size": "Small/Medium/Large with explanation",
            "format_potential": {{
                "ebook": "High/Medium/Low",
                "paperback": "High/Medium/Low", 
                "hardcover": "High/Medium/Low",
                "audiobook": "High/Medium/Low"
            }},
            "series_potential": "Yes/No with explanation",
            "adaptation_potential": "Film/TV/None with explanation",
            "estimated_price_point": "Suggested pricing"
        }},
        
        "book_info": {{
            "title": "suggested or detected title",
            "genre": "primary genre",
            "subgenres": ["subgenre1", "subgenre2"],
            "tone": "overall emotional tone",
            "writing_style": "descriptive/lyrical/direct/etc",
            "pacing_summary": "fast/medium/slow with explanation"
        }},
        
        "characters": {{
            "main": [
                {{
                    "name": "name",
                    "role": "protagonist/antagonist/etc",
                    "description": "who they are",
                    "arc": "how they change",
                    "motivation": "what drives them",
                    "conflict": "internal or external struggles",
                    "appeal_factor": "Why readers will connect"
                }}
            ],
            "supporting": ["list of supporting characters"],
            "relationships": ["key dynamics between characters"]
        }},
        
        "character_development": {{
            "protagonist_journey": "how the main character changes",
            "antagonist_motivation": "what drives the opposition",
            "supporting_arcs": ["how other characters evolve"]
        }},
        
        "narrative_arc": {{
            "exposition": "setup and background",
            "rising_action": "events that build tension",
            "climax": "the turning point",
            "falling_action": "aftermath of climax",
            "resolution": "how story concludes"
        }},
        
        "plot": {{
            "opening_hook": "what grabs attention",
            "inciting_incident": "what starts the story",
            "major_plot_points": ["point1", "point2", "point3", "point4", "point5"],
            "plot_twists": ["any surprises or reveals"],
            "subplots": ["secondary storylines"]
        }},
        
        "themes": {{
            "primary": ["main themes with explanation"],
            "secondary": ["other themes"],
            "motifs": ["recurring elements"]
        }},
        
        "strengths": ["5 specific strengths of this manuscript with examples"],
        
        "areas_for_improvement": ["5 specific weaknesses with suggestions"],
        
        "target_audience": {{
            "primary": "who will love this based on content",
            "appeal": "why they'll love it",
            "demographics": ["age range", "gender skew", "interests"]
        }},
        
        "marketing": {{
            "unique_selling_points": ["what makes it special based on content"],
            "keyword_cloud": ["keywords from the text"],
            "compelling_quotes": ["3 actual quotes from the manuscript or potential pull quotes"],
            "blurb_suggestion": "A potential back-cover blurb based on content"
        }}
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a literary analyst. Return valid JSON only. Do NOT include comparable successes or comparable bestsellers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=6000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
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


def show_marketability_dashboard(analysis):
    """Display marketability dashboard"""
    
    st.markdown("## 📊 MARKETABILITY DASHBOARD")
    st.markdown("---")
    
    if 'marketability' not in analysis:
        st.warning("Marketability data not available")
        return
    
    market = analysis['marketability']
    
    overall_score = market.get('overall_score', 0)
    overall_grade = market.get('overall_grade', 'N/A')
    
    if overall_score >= 80:
        score_color = "#00cc66"
        emoji = "🚀"
        score_text = "EXCELLENT MARKETABILITY"
    elif overall_score >= 70:
        score_color = "#ffaa00"
        emoji = "📈"
        score_text = "GOOD MARKETABILITY"
    elif overall_score >= 60:
        score_color = "#ff8800"
        emoji = "📊"
        score_text = "FAIR MARKETABILITY"
    else:
        score_color = "#ff4444"
        emoji = "⚠️"
        score_text = "NEEDS WORK"
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px;">
            <h2 style="font-size: 48px; margin: 0; color: white;">{overall_score}</h2>
            <h4 style="font-size: 20px; margin: 5px 0; color: white;">{score_text}</h4>
            <p style="font-size: 18px; margin: 5px 0 0 0; color: white;">Grade: {overall_grade} {emoji}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"**Overall Assessment:** {market.get('overall_assessment', 'No assessment available')}")
    st.markdown("---")
    
    st.markdown("### 📈 Detailed Scores")
    scores = market.get('scores', {})
    
    if scores:
        score_items = list(scores.items())
        for i in range(0, len(score_items), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(score_items):
                    score_name, score_data = score_items[i + j]
                    display_name = score_name.replace('_', ' ').title()
                    score_value = score_data.get('score', 0)
                    explanation = score_data.get('explanation', '')
                    
                    if score_value >= 80:
                        bg_color = "#e6f7e6"
                        border_color = "#00cc66"
                        bar_color = "#00cc66"
                    elif score_value >= 70:
                        bg_color = "#fff4e6"
                        border_color = "#ffaa00"
                        bar_color = "#ffaa00"
                    else:
                        bg_color = "#fff0e6"
                        border_color = "#ff8800"
                        bar_color = "#ff8800"
                    
                    with cols[j]:
                        st.markdown(f"""
                        <div style="padding: 15px; background-color: {bg_color}; border-radius: 8px; border-left: 5px solid {border_color}; margin-bottom: 10px;">
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                                <span style="font-weight: 600; font-size: 16px;">{display_name}</span>
                                <span style="font-weight: 600; font-size: 20px; color: {border_color};">{score_value}</span>
                            </div>
                            <div style="height: 8px; background-color: #ddd; border-radius: 4px; margin-bottom: 10px;">
                                <div style="width: {score_value}%; height: 8px; background-color: {bar_color}; border-radius: 4px;"></div>
                            </div>
                            <p style="margin: 0; font-size: 14px; color: #666;">{explanation}</p>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.warning("No detailed scores available")
    
    st.markdown("---")
    
    if 'title_analysis' in analysis:
        title_analysis = analysis['title_analysis']
        st.markdown("### 🏷️ Title Analysis & Suggestions")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            current_title = title_analysis.get('current_title', 'Unknown')
            st.markdown(f"**Current Title:** {current_title}")
            
            effectiveness = title_analysis.get('title_effectiveness', {})
            if effectiveness:
                score = effectiveness.get('score', 0)
                st.markdown(f"**Effectiveness Score:** {score}/100")
        
        with col2:
            rec = title_analysis.get('title_change_recommendation', '')
            if rec:
                st.markdown(f"**Recommendation:** {rec}")
            
            subtitle = title_analysis.get('subtitle_suggestion', '')
            if subtitle:
                st.markdown(f"**Suggested Subtitle:** {subtitle}")
    
    st.markdown("---")
    
    if 'salability_analysis' in analysis:
        salability = analysis['salability_analysis']
        st.markdown("### 💰 Salability Analysis")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"**Market Size**  \n{salability.get('estimated_market_size', 'Medium')}")
        with col2:
            st.markdown(f"**Series Potential**  \n{salability.get('series_potential', 'Unknown')}")
        with col3:
            st.markdown(f"**Adaptation**  \n{salability.get('adaptation_potential', 'Unknown')}")
        with col4:
            st.markdown(f"**Price Point**  \n{salability.get('estimated_price_point', 'Unknown')}")


def show_complete_analysis(analysis, cover):
    """YOUR ORIGINAL COMPLETE literary analysis display - FULLY RESTORED"""
    
    if cover:
        with st.expander("🎨 Cover Analysis", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Visual Elements**")
                st.write(f"**Colors:** {', '.join(cover.get('colors', []))}")
                st.write(f"**Has Figure:** {cover.get('has_figure', False)}")
                if cover.get('has_figure'):
                    st.write(f"**Figure Description:** {cover.get('figure_description', '')}")
                st.write(f"**Mood:** {cover.get('mood', '')}")
            
            with col2:
                st.markdown("**Design Analysis**")
                st.write(f"**Typography:** {cover.get('typography', '')}")
                st.write(f"**Composition:** {cover.get('composition', '')}")
                st.write(f"**Genre Signals:** {cover.get('genre_signals', '')}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Strengths**")
                for s in cover.get('strengths', []):
                    st.write(f"✅ {s}")
            with col2:
                st.markdown("**Weaknesses**")
                for w in cover.get('weaknesses', []):
                    st.write(f"⚠️ {w}")
            with col3:
                st.markdown("**Suggestions**")
                for sug in cover.get('suggestions', []):
                    st.write(f"💡 {sug}")
    
    # Book Overview
    book_info = analysis.get('book_info', {})
    st.markdown("### 📖 Book Overview")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Title:** {book_info.get('title', 'Unknown')}")
        st.markdown(f"**Genre:** {book_info.get('genre', 'Unknown')}")
        st.markdown(f"**Subgenres:** {', '.join(book_info.get('subgenres', []))}")
    with col2:
        st.markdown(f"**Tone:** {book_info.get('tone', 'Unknown')}")
        st.markdown(f"**Writing Style:** {book_info.get('writing_style', 'Unknown')}")
        st.markdown(f"**Pacing:** {book_info.get('pacing_summary', 'Unknown')}")
    
    st.markdown("---")
    
    # Writing Quality Detailed
    if 'writing_quality_detailed' in analysis:
        writing = analysis['writing_quality_detailed']
        st.markdown("### ✍️ Writing Quality Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Prose Quality:** {writing.get('prose_quality', '')}")
            st.markdown(f"**Dialogue:** {writing.get('dialogue', '')}")
            st.markdown(f"**Description:** {writing.get('description', '')}")
        with col2:
            st.markdown(f"**Voice:** {writing.get('voice', '')}")
            st.markdown(f"**Technical Execution:** {writing.get('technical_execution', '')}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Strengths**")
            for s in writing.get('strengths', []):
                st.write(f"✅ {s}")
        with col2:
            st.markdown("**Areas for Improvement**")
            for i in writing.get('improvements', []):
                st.write(f"📝 {i}")
    
    st.markdown("---")
    
    # Characters
    if 'characters' in analysis:
        chars = analysis['characters']
        st.markdown("### 👥 Characters")
        
        # Main Characters
        st.markdown("#### Main Characters")
        for char in chars.get('main', []):
            with st.expander(f"**{char.get('name', 'Unknown')}** - {char.get('role', '')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Description:** {char.get('description', '')}")
                    st.markdown(f"**Motivation:** {char.get('motivation', '')}")
                with col2:
                    st.markdown(f"**Arc:** {char.get('arc', '')}")
                    st.markdown(f"**Conflict:** {char.get('conflict', '')}")
                st.markdown(f"**Appeal Factor:** {char.get('appeal_factor', '')}")
        
        # Supporting Characters
        if chars.get('supporting'):
            st.markdown("#### Supporting Characters")
            st.write(', '.join(chars.get('supporting', [])))
        
        # Relationships
        if chars.get('relationships'):
            st.markdown("#### Key Relationships")
            for rel in chars.get('relationships', []):
                st.write(f"• {rel}")
    
    st.markdown("---")
    
    # Character Development
    if 'character_development' in analysis:
        dev = analysis['character_development']
        st.markdown("### 📈 Character Development")
        
        st.markdown(f"**Protagonist Journey:** {dev.get('protagonist_journey', '')}")
        st.markdown(f"**Antagonist Motivation:** {dev.get('antagonist_motivation', '')}")
        
        if dev.get('supporting_arcs'):
            st.markdown("**Supporting Character Arcs:**")
            for arc in dev.get('supporting_arcs', []):
                st.write(f"• {arc}")
    
    st.markdown("---")
    
    # Plot Analysis
    if 'plot' in analysis:
        plot = analysis['plot']
        st.markdown("### 📊 Plot Analysis")
        
        st.markdown(f"**Opening Hook:** {plot.get('opening_hook', '')}")
        st.markdown(f"**Inciting Incident:** {plot.get('inciting_incident', '')}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Major Plot Points**")
            for point in plot.get('major_plot_points', []):
                st.write(f"• {point}")
        
        with col2:
            if plot.get('plot_twists'):
                st.markdown("**Plot Twists**")
                for twist in plot.get('plot_twists', []):
                    st.write(f"• {twist}")
        
        if plot.get('subplots'):
            st.markdown("**Subplots**")
            for sub in plot.get('subplots', []):
                st.write(f"• {sub}")
    
    st.markdown("---")
    
    # Narrative Arc
    if 'narrative_arc' in analysis:
        arc = analysis['narrative_arc']
        st.markdown("### 📖 Narrative Arc")
        
        st.markdown(f"**Exposition:** {arc.get('exposition', '')}")
        st.markdown(f"**Rising Action:** {arc.get('rising_action', '')}")
        st.markdown(f"**Climax:** {arc.get('climax', '')}")
        st.markdown(f"**Falling Action:** {arc.get('falling_action', '')}")
        st.markdown(f"**Resolution:** {arc.get('resolution', '')}")
    
    st.markdown("---")
    
    # Themes
    if 'themes' in analysis:
        themes = analysis['themes']
        st.markdown("### 🎯 Themes & Motifs")
        
        st.markdown("**Primary Themes:**")
        for theme in themes.get('primary', []):
            st.write(f"• {theme}")
        
        if themes.get('secondary'):
            st.markdown("**Secondary Themes:**")
            for theme in themes.get('secondary', []):
                st.write(f"• {theme}")
        
        if themes.get('motifs'):
            st.markdown("**Motifs:**")
            for motif in themes.get('motifs', []):
                st.write(f"• {motif}")
    
    st.markdown("---")
    
    # Strengths
    if 'strengths' in analysis:
        st.markdown("### 💪 Key Strengths")
        for s in analysis['strengths']:
            st.write(f"✅ {s}")
    
    st.markdown("---")
    
    # Areas for Improvement
    if 'areas_for_improvement' in analysis:
        st.markdown("### 🔧 Areas for Improvement")
        for area in analysis['areas_for_improvement']:
            st.write(f"📝 {area}")
    
    st.markdown("---")
    
    # Target Audience
    if 'target_audience' in analysis:
        audience = analysis['target_audience']
        st.markdown("### 🎯 Target Audience")
        
        st.markdown(f"**Primary Audience:** {audience.get('primary', '')}")
        st.markdown(f"**Appeal:** {audience.get('appeal', '')}")
        
        if audience.get('demographics'):
            st.markdown("**Demographics:**")
            for demo in audience.get('demographics', []):
                st.write(f"• {demo}")
    
    st.markdown("---")
    
    # Marketing
    if 'marketing' in analysis:
        marketing = analysis['marketing']
        st.markdown("### 📢 Marketing Insights")
        
        st.markdown("**Unique Selling Points:**")
        for usp in marketing.get('unique_selling_points', []):
            st.write(f"• {usp}")
        
        if marketing.get('keyword_cloud'):
            st.markdown("**Keywords:**")
            st.write(', '.join(marketing.get('keyword_cloud', [])))
        
        if marketing.get('compelling_quotes'):
            st.markdown("**Compelling Quotes:**")
            for quote in marketing.get('compelling_quotes', []):
                st.write(f"💬 {quote}")
        
        if marketing.get('blurb_suggestion'):
            st.markdown("**Suggested Blurb:**")
            st.info(marketing['blurb_suggestion'])


# For direct testing
if __name__ == "__main__":
    show_analyzer()

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

# Add database connection function (same as in BardSpark.py)
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

def save_analysis_to_db(user_id, book_title, analysis_result, cover_image=None):
    """Save book analysis to database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Get genre from analysis if available
        book_info = analysis_result.get('book_info', {})
        book_genre = book_info.get('genre', 'Unknown')
        
        # Handle cover image if provided
        cover_url = None
        # In a real implementation, you might upload to cloud storage
        # For now, we'll store a placeholder
        cover_url = "uploaded_cover"
        
        cur.execute("""
            INSERT INTO user_book_analyses 
            (user_id, book_title, book_genre, analysis_result, cover_image_url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            book_title,
            book_genre,
            json.dumps(analysis_result),
            cover_url,
            datetime.now(),
            datetime.now()
        ))
        
        analysis_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return analysis_id
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def show_analyzer():
    """Complete book analysis with marketability dashboard"""
    
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
    
    # If analysis is complete, show ONLY the dashboard (no upload screen)
    if st.session_state.analysis_complete and st.session_state.analysis_result:
        show_results()
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
                st.rerun()
    else:
        st.info("👆 Please upload both manuscript and cover to begin")


def show_results():
    """Display ONLY the results dashboard (no upload interface)"""
    
    st.success("✅ Analysis complete! Your book has been analyzed with marketability scoring.")
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        book_title = st.session_state.analysis_result.get('book_info', {}).get('title', 'Untitled')
        filename = f"{book_title.replace(' ', '_')}_analysis.json"
        
        if st.button("💾 Save to Library", use_container_width=True):
            # Check if user is logged in
            if st.session_state.get('authenticated', False):
                # Save to database
                analysis_id = save_analysis_to_db(
                    st.session_state.user_id,
                    book_title,
                    st.session_state.analysis_result
                )
                if analysis_id:
                    st.success(f"✅ Analysis saved to your library!")
                else:
                    st.error("Failed to save to database")
            else:
                # Fallback to session state for non-logged in users
                save_data = {
                    "book_info": st.session_state.analysis_result,
                    "cover_analysis": st.session_state.cover_analysis,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "book_id": st.session_state.current_book_id
                }
                
                if 'analysis_library' not in st.session_state:
                    st.session_state.analysis_library = {}
                
                st.session_state.analysis_library[filename] = save_data
                st.warning("⚠️ Not logged in - saved to current session only. Login to save permanently.")
    
    with col2:
        if st.button("🎨 Marketing Assets", use_container_width=True):
            st.session_state.page = "🎨 Marketing Assets"
            st.rerun()
    
    with col3:
        if st.button("📊 Export Report", use_container_width=True):
            st.info("Export feature coming soon!")
    
    with col4:
        if st.button("🔄 New Analysis", use_container_width=True):
            st.session_state.analysis_complete = False
            st.session_state.analysis_result = None
            st.session_state.cover_analysis = None
            st.rerun()
    
    st.markdown("---")
    
    # Show marketability dashboard FIRST
    show_marketability_dashboard(st.session_state.analysis_result)
    
    # Then show complete literary analysis in expander
    with st.expander("📚 View Complete Literary Analysis", expanded=False):
        show_complete_analysis(st.session_state.analysis_result, st.session_state.cover_analysis)


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
    """Complete manuscript analysis with ALL metrics - REMOVED fake comparable sections"""
    
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
    """Display marketability dashboard with BEAUTIFUL design but NORMAL fonts"""
    
    st.markdown("## 📊 MARKETABILITY DASHBOARD")
    st.markdown("---")
    
    if 'marketability' not in analysis:
        st.warning("Marketability data not available")
        return
    
    market = analysis['marketability']
    
    # Overall score - Beautiful card with NORMAL font sizes
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
    
    # Beautiful card with normal sized text (48px max)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px;">
            <h2 style="font-size: 48px; margin: 0; color: white;">{overall_score}</h2>
            <h4 style="font-size: 20px; margin: 5px 0; color: white;">{score_text}</h4>
            <p style="font-size: 18px; margin: 5px 0 0 0; color: white;">Grade: {overall_grade} {emoji}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Overall assessment - normal font
    st.markdown(f"**Overall Assessment:** {market.get('overall_assessment', 'No assessment available')}")
    
    st.markdown("---")
    
    # Individual scores - Beautiful cards with normal fonts
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
    
    # Title Analysis - Beautiful but normal fonts
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
                st.markdown(f"*Memorability:* {effectiveness.get('memorability', '')}")
                st.markdown(f"*Genre Appropriateness:* {effectiveness.get('genre_appropriateness', '')}")
                st.markdown(f"*Uniqueness:* {effectiveness.get('uniqueness', '')}")
                st.markdown(f"*Searchability:* {effectiveness.get('searchability', '')}")
        
        with col2:
            rec = title_analysis.get('title_change_recommendation', '')
            if rec:
                st.markdown(f"**Recommendation:** {rec}")
            
            subtitle = title_analysis.get('subtitle_suggestion', '')
            if subtitle:
                st.markdown(f"**Suggested Subtitle:** {subtitle}")
        
        suggestions = title_analysis.get('suggested_titles', [])
        if suggestions:
            st.markdown("#### 💡 Alternative Title Suggestions")
            
            for i, suggestion in enumerate(suggestions, 1):
                if isinstance(suggestion, dict):
                    impact = suggestion.get('estimated_impact', 'Medium')
                    if impact.lower() == 'high':
                        impact_color = "#ff4444"
                        impact_display = "🔴 HIGH IMPACT"
                    elif impact.lower() == 'medium':
                        impact_color = "#ffaa00"
                        impact_display = "🟡 MEDIUM IMPACT"
                    else:
                        impact_color = "#00cc66"
                        impact_display = "🟢 LOW IMPACT"
                    
                    st.markdown(f"""
                    <div style="padding: 15px; background-color: #f8f9fa; border-radius: 8px; margin-bottom: 10px; border: 1px solid #ddd;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-weight: 600; font-size: 16px;">{i}. {suggestion.get('title', '')}</span>
                            <span style="background-color: {impact_color}; color: white; padding: 3px 10px; border-radius: 15px; font-size: 12px;">{impact_display}</span>
                        </div>
                        <p style="margin: 0; color: #666; font-size: 14px;"><em>{suggestion.get('rationale', '')}</em></p>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Salability Analysis - Beautiful but normal fonts
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
        
        format_potential = salability.get('format_potential', {})
        if format_potential:
            st.markdown("**Format Potential:**")
            cols = st.columns(4)
            formats = list(format_potential.items())
            for i, (fmt, potential) in enumerate(formats[:4]):
                with cols[i]:
                    if potential.lower() == 'high':
                        color = "#00cc66"
                    elif potential.lower() == 'medium':
                        color = "#ffaa00"
                    else:
                        color = "#ff4444"
                    st.markdown(f"**{fmt.title()}:**  \n<span style='color: {color}; font-weight: bold;'>{potential}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Market Position - Beautiful but normal fonts
    if 'marketability' in analysis:
        market = analysis['marketability']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📍 Market Position")
            st.markdown(f"**Market Gap:** {market.get('market_gap_analysis', 'Not specified')}")
            st.markdown(f"**Competitive Advantage:** {market.get('competitive_advantage', 'Not specified')}")
        
        with col2:
            challenges = market.get('potential_challenges', [])
            if challenges:
                st.markdown("### ⚠️ Potential Challenges")
                for challenge in challenges:
                    st.markdown(f"• {challenge}")
    
    st.markdown("---")
    
    # Writing Quality (condensed, normal font)
    if 'writing_quality_detailed' in analysis:
        writing = analysis['writing_quality_detailed']
        
        with st.expander("✍️ Writing Quality Details", expanded=False):
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
                st.markdown("**✅ Writing Strengths:**")
                for s in writing.get('strengths', []):
                    st.write(f"• {s}")
            with col2:
                st.markdown("**📝 Needed Improvements:**")
                for i in writing.get('improvements', []):
                    st.write(f"• {i}")
    
    # Marketing insights
    if 'marketing' in analysis:
        marketing = analysis['marketing']
        
        with st.expander("📈 Marketing Insights", expanded=False):
            if marketing.get('unique_selling_points'):
                st.markdown("**Unique Selling Points:**")
                for usp in marketing['unique_selling_points']:
                    st.write(f"• {usp}")
            
            if marketing.get('keyword_cloud'):
                st.markdown("**Keywords:**")
                st.write(', '.join(marketing['keyword_cloud']))
            
            if marketing.get('compelling_quotes'):
                st.markdown("**Pull Quotes:**")
                for quote in marketing['compelling_quotes']:
                    st.info(f"“{quote}”")
            
            if marketing.get('blurb_suggestion'):
                st.markdown("**Suggested Blurb:**")
                st.write(marketing['blurb_suggestion'])


def show_complete_analysis(analysis, cover):
    """Display complete literary analysis - PACING ANALYSIS REMOVED (redundant)"""
    
    # Cover Analysis
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
    
    # Book Info - INCLUDES PACING SUMMARY
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
        st.markdown(f"**Pacing Summary:** {book_info.get('pacing_summary', 'Unknown')}")
    
    st.divider()
    
    # Narrative Arc
    narrative = analysis.get('narrative_arc', {})
    if narrative:
        st.markdown("### 📊 Narrative Arc")
        
        st.markdown(f"**Exposition:** {narrative.get('exposition', 'Not specified')}")
        st.markdown(f"**Rising Action:** {narrative.get('rising_action', 'Not specified')}")
        st.markdown(f"**Climax:** {narrative.get('climax', 'Not specified')}")
        st.markdown(f"**Falling Action:** {narrative.get('falling_action', 'Not specified')}")
        st.markdown(f"**Resolution:** {narrative.get('resolution', 'Not specified')}")
        
        st.divider()
    
    # Characters
    chars = analysis.get('characters', {})
    st.markdown("### 👥 Characters")
    
    main_chars = chars.get('main', [])
    if main_chars:
        st.markdown("**Main Characters**")
        for char in main_chars:
            st.markdown(f"**{char.get('name', 'Unknown')}** *({char.get('role', '')})*")
            st.markdown(f"*Description:* {char.get('description', '')}")
            if char.get('motivation'):
                st.markdown(f"*Motivation:* {char.get('motivation')}")
            if char.get('conflict'):
                st.markdown(f"*Conflict:* {char.get('conflict')}")
            if char.get('arc'):
                st.markdown(f"*Arc:* {char.get('arc')}")
            if char.get('appeal_factor'):
                st.markdown(f"*Appeal:* {char.get('appeal_factor')}")
            st.markdown("---")
    
    # Character Development
    dev = analysis.get('character_development', {})
    if dev:
        with st.expander("📈 Character Development", expanded=False):
            if dev.get('protagonist_journey'):
                st.markdown(f"**Protagonist Journey:** {dev['protagonist_journey']}")
            if dev.get('antagonist_motivation'):
                st.markdown(f"**Antagonist Motivation:** {dev['antagonist_motivation']}")
            if dev.get('supporting_arcs'):
                st.markdown("**Supporting Arcs:**")
                for arc in dev['supporting_arcs']:
                    st.write(f"• {arc}")
    
    # Supporting Characters
    if chars.get('supporting'):
        with st.expander("👥 Supporting Characters", expanded=False):
            for char in chars.get('supporting', []):
                st.write(f"• {char}")
    
    # Relationships
    if chars.get('relationships'):
        with st.expander("🔄 Key Relationships", expanded=False):
            for rel in chars.get('relationships', []):
                st.write(f"• {rel}")
    
    st.divider()
    
    # Plot
    plot = analysis.get('plot', {})
    if plot:
        st.markdown("### 📊 Plot")
        
        if plot.get('opening_hook'):
            st.markdown(f"**Opening Hook:** {plot['opening_hook']}")
        
        if plot.get('inciting_incident'):
            st.markdown(f"**Inciting Incident:** {plot['inciting_incident']}")
        
        if plot.get('major_plot_points'):
            st.markdown("**Major Plot Points:**")
            for point in plot['major_plot_points']:
                st.write(f"• {point}")
        
        if plot.get('plot_twists'):
            st.markdown("**Plot Twists:**")
            for twist in plot['plot_twists']:
                st.write(f"• {twist}")
        
        if plot.get('subplots'):
            st.markdown("**Subplots:**")
            for subplot in plot['subplots']:
                st.write(f"• {subplot}")
        
        st.divider()
    
    # Themes
    themes = analysis.get('themes', {})
    if themes:
        st.markdown("### 🎨 Themes")
        
        if themes.get('primary'):
            st.markdown("**Primary Themes:**")
            for theme in themes['primary']:
                if isinstance(theme, dict):
                    st.write(f"• {theme.get('theme', theme)}: {theme.get('explanation', '')}")
                else:
                    st.write(f"• {theme}")
        
        if themes.get('secondary'):
            st.markdown("**Secondary Themes:**")
            for theme in themes['secondary']:
                if isinstance(theme, dict):
                    st.write(f"• {theme.get('theme', theme)}: {theme.get('explanation', '')}")
                else:
                    st.write(f"• {theme}")
        
        if themes.get('motifs'):
            st.markdown("**Motifs:**")
            for motif in themes['motifs']:
                st.write(f"• {motif}")
        
        st.divider()
    
    # Strengths & Improvements
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
            st.markdown("### 📝 Areas to Improve")
            for i in improvements:
                st.write(f"• {i}")
    
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
            if target.get('demographics'):
                st.markdown(f"**Demographics:** {', '.join(target['demographics'])}")


# For direct testing
if __name__ == "__main__":
    show_analyzer()

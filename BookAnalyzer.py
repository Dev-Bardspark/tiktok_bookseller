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
    
    # API Key input
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
    
    # Show results if analysis is complete
    if st.session_state.analysis_complete and st.session_state.analysis_result:
        show_results()


def show_results():
    """Display analysis results with marketability dashboard FIRST"""
    
    st.success("✅ Analysis complete! Your book has been analyzed with marketability scoring.")
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        book_title = st.session_state.analysis_result.get('book_info', {}).get('title', 'Untitled')
        filename = f"{book_title.replace(' ', '_')}_analysis.json"
        
        if st.button("💾 Save to Library", use_container_width=True):
            save_data = {
                "book_info": st.session_state.analysis_result,
                "cover_analysis": st.session_state.cover_analysis,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "book_id": st.session_state.current_book_id
            }
            
            if 'analysis_library' not in st.session_state:
                st.session_state.analysis_library = {}
            
            st.session_state.analysis_library[filename] = save_data
            st.success(f"✅ Saved!")
    
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
    """Complete manuscript analysis with ALL metrics including marketability"""
    
    if len(text) > 50000:
        text = text[:50000] + "... [truncated]"
    
    total_len = len(text)
    beginning = text[:min(5000, total_len//3)]
    middle = text[total_len//3:total_len//3*2][:5000]
    ending = text[-5000:]
    
    prompt = f"""
    You are a professional literary analyst and publishing industry expert. Analyze this book in depth with special focus on its marketability and commercial potential.
    
    COVER ANALYSIS (for context):
    {json.dumps(cover_analysis, indent=2)}
    
    MANUSCRIPT EXCERPTS:
    
    BEGINNING:
    {beginning}
    
    MIDDLE:
    {middle}
    
    ENDING:
    {ending}
    
    Based on these excerpts, provide a COMPLETE analysis as JSON with ALL of the following sections.
    
    CRITICAL: The analysis MUST include a comprehensive marketability section with numerical scores (0-100).
    
    Return EXACTLY this structure:
    
    {{
        "marketability": {{
            "overall_score": 85,
            "overall_grade": "A-",
            "overall_assessment": "Brief summary of commercial potential",
            "scores": {{
                "writing_quality": {{"score": 88, "explanation": "Why this score", "strengths": ["specific strength"], "weaknesses": ["specific weakness"]}},
                "commercial_potential": {{"score": 82, "explanation": "Why this score", "strengths": [], "weaknesses": []}},
                "genre_fit": {{"score": 90, "explanation": "Why this score", "strengths": [], "weaknesses": []}},
                "hook_strength": {{"score": 85, "explanation": "Why this score", "strengths": [], "weaknesses": []}},
                "character_appeal": {{"score": 80, "explanation": "Why this score", "strengths": [], "weaknesses": []}},
                "pacing": {{"score": 75, "explanation": "Why this score", "strengths": [], "weaknesses": []}},
                "originality": {{"score": 70, "explanation": "Why this score", "strengths": [], "weaknesses": []}},
                "target_audience_appeal": {{"score": 85, "explanation": "Why this score", "strengths": [], "weaknesses": []}}
            }},
            "comparable_successes": [
                {{"title": "Similar Successful Book 1", "similarity": "How it's similar", "why_it_succeeded": "Market factors"}},
                {{"title": "Similar Successful Book 2", "similarity": "How it's similar", "why_it_succeeded": "Market factors"}}
            ],
            "market_gap_analysis": "Where this book fits in current market",
            "competitive_advantage": "What makes it stand out",
            "potential_challenges": ["Challenge 1", "Challenge 2", "Challenge 3"]
        }},
        
        "writing_quality_detailed": {{
            "prose_quality": "Assessment of sentence-level writing",
            "dialogue": "Quality and naturalness of dialogue",
            "description": "Quality of descriptive passages",
            "voice": "Strength and consistency of narrative voice",
            "technical_execution": "Grammar, punctuation, formatting",
            "strengths": ["Specific writing strengths"],
            "improvements": ["Specific writing improvements needed"]
        }},
        
        "title_analysis": {{
            "current_title": "Title detected or suggested from content",
            "title_effectiveness": {{
                "score": 70,
                "memorability": "Assessment",
                "genre_appropriateness": "Assessment",
                "uniqueness": "Assessment",
                "searchability": "Assessment"
            }},
            "suggested_titles": [
                {{"title": "Alternative Title 1", "rationale": "Why this works better", "estimated_impact": "High"}},
                {{"title": "Alternative Title 2", "rationale": "Why this works better", "estimated_impact": "High"}},
                {{"title": "Alternative Title 3", "rationale": "Why this works better", "estimated_impact": "Medium"}},
                {{"title": "Alternative Title 4", "rationale": "Why this works better", "estimated_impact": "Medium"}},
                {{"title": "Alternative Title 5", "rationale": "Why this works better", "estimated_impact": "Low"}}
            ],
            "title_change_recommendation": "Should the title be changed? Why?",
            "subtitle_suggestion": "If applicable, a subtitle suggestion"
        }},
        
        "salability_analysis": {{
            "estimated_market_size": "Small/Medium/Large with explanation",
            "target_retailers": ["Amazon", "Barnes & Noble", "etc"],
            "format_potential": {{
                "ebook": "High/Medium/Low",
                "paperback": "High/Medium/Low", 
                "hardcover": "High/Medium/Low",
                "audiobook": "High/Medium/Low"
            }},
            "series_potential": "Yes/No with explanation",
            "adaptation_potential": "Film/TV/None with explanation",
            "estimated_price_point": "Suggested pricing",
            "comparable_bestsellers": [
                {{"title": "Bestseller 1", "similarity": "What's similar", "copies_sold": "Estimated"}},
                {{"title": "Bestseller 2", "similarity": "What's similar", "copies_sold": "Estimated"}}
            ]
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
        
        "pacing_analysis": {{
            "overall": "fast/medium/slow",
            "opening": "description",
            "middle": "description",
            "ending": "description",
            "tension_curve": "how tension rises and falls"
        }},
        
        "strengths": ["5 specific strengths of this manuscript with examples"],
        
        "areas_for_improvement": ["5 specific weaknesses with suggestions"],
        
        "target_audience": {{
            "primary": "who will love this",
            "appeal": "why they'll love it",
            "demographics": ["age range", "gender skew", "interests"],
            "comparable_titles": [
                {{"title": "Book 1", "similarity": "how it's similar", "difference": "how it's different"}},
                {{"title": "Book 2", "similarity": "how it's similar", "difference": "how it's different"}},
                {{"title": "Book 3", "similarity": "how it's similar", "difference": "how it's different"}}
            ]
        }},
        
        "marketing": {{
            "unique_selling_points": ["what makes it special"],
            "keyword_cloud": ["amazon_keywords"],
            "compelling_quotes": ["3 actual or potential pull quotes"],
            "blurb_suggestion": "A potential back-cover blurb"
        }}
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a literary analyst and publishing industry expert. Return valid JSON only with ALL sections exactly as specified. The marketability section is REQUIRED."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=6000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Verify marketability section exists
        if 'marketability' not in result:
            # If missing, add a default structure
            result['marketability'] = {
                "overall_score": 75,
                "overall_grade": "C+",
                "overall_assessment": "Standard marketability with room for improvement",
                "scores": {
                    "writing_quality": {"score": 75, "explanation": "Average writing quality", "strengths": [], "weaknesses": []},
                    "commercial_potential": {"score": 75, "explanation": "Standard commercial potential", "strengths": [], "weaknesses": []},
                    "genre_fit": {"score": 75, "explanation": "Good genre fit", "strengths": [], "weaknesses": []},
                    "hook_strength": {"score": 75, "explanation": "Average hook", "strengths": [], "weaknesses": []},
                    "character_appeal": {"score": 75, "explanation": "Characters are relatable", "strengths": [], "weaknesses": []},
                    "pacing": {"score": 75, "explanation": "Good pacing", "strengths": [], "weaknesses": []},
                    "originality": {"score": 75, "explanation": "Some original elements", "strengths": [], "weaknesses": []},
                    "target_audience_appeal": {"score": 75, "explanation": "Appeals to target audience", "strengths": [], "weaknesses": []}
                },
                "comparable_successes": [],
                "market_gap_analysis": "Standard market positioning",
                "competitive_advantage": "Unique voice",
                "potential_challenges": ["Market competition"]
            }
        
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
    """Display marketability dashboard with all commercial metrics"""
    
    st.markdown("## 📊 MARKETABILITY DASHBOARD")
    st.markdown("---")
    
    if 'marketability' not in analysis:
        st.warning("Marketability data not available")
        return
    
    market = analysis['marketability']
    
    # Overall score
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
        <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px;">
            <h1 style="font-size: 80px; margin: 0; color: white;">{overall_score}</h1>
            <h2 style="margin: 0; color: white;">{score_text}</h2>
            <p style="font-size: 30px; margin: 10px 0 0 0; color: white;">Grade: {overall_grade} {emoji}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Overall assessment
    st.markdown(f"### 📝 Overall Assessment")
    st.info(market.get('overall_assessment', 'No assessment available'))
    
    st.markdown("---")
    
    # Individual scores
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
                    elif score_value >= 60:
                        bg_color = "#fff0e6"
                        border_color = "#ff8800"
                        bar_color = "#ff8800"
                    else:
                        bg_color = "#ffe6e6"
                        border_color = "#ff4444"
                        bar_color = "#ff4444"
                    
                    with cols[j]:
                        st.markdown(f"""
                        <div style="padding: 15px; background-color: {bg_color}; border-radius: 8px; border-left: 5px solid {border_color}; margin-bottom: 10px;">
                            <h4 style="margin: 0 0 5px 0;">{display_name}</h4>
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <h2 style="margin: 0 10px 0 0; color: {border_color};">{score_value}</h2>
                                <div style="flex-grow: 1; height: 10px; background-color: #ddd; border-radius: 5px;">
                                    <div style="width: {score_value}%; height: 10px; background-color: {bar_color}; border-radius: 5px;"></div>
                                </div>
                            </div>
                            <p style="margin: 5px 0 0 0; font-size: 0.9em;">{explanation}</p>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.warning("No detailed scores available")
    
    st.markdown("---")
    
    # Title Analysis
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
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="font-size: 1.2em;">{i}. {suggestion.get('title', '')}</strong>
                            <span style="background-color: {impact_color}; color: white; padding: 3px 10px; border-radius: 15px; font-size: 0.8em;">{impact_display}</span>
                        </div>
                        <p style="margin: 10px 0 0 0; color: #666;"><em>{suggestion.get('rationale', '')}</em></p>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("---")
    
    # Salability Analysis
    if 'salability_analysis' in analysis:
        salability = analysis['salability_analysis']
        
        st.markdown("### 💰 Salability Analysis")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Market Size", salability.get('estimated_market_size', 'Unknown'))
        with col2:
            st.metric("Series Potential", salability.get('series_potential', 'Unknown'))
        with col3:
            st.metric("Adaptation", salability.get('adaptation_potential', 'Unknown'))
        with col4:
            st.metric("Price Point", salability.get('estimated_price_point', 'Unknown'))
        
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
                    st.markdown(f"**{fmt.title()}:** <span style='color: {color}; font-weight: bold;'>{potential}</span>", unsafe_allow_html=True)
        
        st.markdown("---")
    
    # Comparable successes and market analysis
    if 'marketability' in analysis:
        market = analysis['marketability']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏆 Comparable Successes")
            comps = market.get('comparable_successes', [])
            if comps:
                for comp in comps:
                    if isinstance(comp, dict):
                        st.markdown(f"""
                        <div style="padding: 10px; background-color: #f0f2f6; border-radius: 5px; margin-bottom: 10px;">
                            <strong>{comp.get('title', '')}</strong><br>
                            <span style="color: #666;">Similarity: {comp.get('similarity', '')}</span><br>
                            <span style="color: #666;">Why it succeeded: {comp.get('why_it_succeeded', '')}</span>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No comparable successes identified")
        
        with col2:
            st.markdown("### 🔍 Market Position")
            st.markdown(f"**Market Gap:** {market.get('market_gap_analysis', 'Not specified')}")
            st.markdown(f"**Competitive Advantage:** {market.get('competitive_advantage', 'Not specified')}")
            
            challenges = market.get('potential_challenges', [])
            if challenges:
                st.markdown("**Potential Challenges:**")
                for challenge in challenges:
                    st.markdown(f"• {challenge}")
    
    st.markdown("---")


def show_complete_analysis(analysis, cover):
    """Display complete literary analysis with ALL original metrics"""
    
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
    
    # Book Info
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
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Exposition**")
            st.write(narrative.get('exposition', 'Not specified'))
            st.markdown("**Rising Action**")
            st.write(narrative.get('rising_action', 'Not specified'))
            st.markdown("**Climax**")
            st.write(narrative.get('climax', 'Not specified'))
        with col2:
            st.markdown("**Falling Action**")
            st.write(narrative.get('falling_action', 'Not specified'))
            st.markdown("**Resolution**")
            st.write(narrative.get('resolution', 'Not specified'))
        
        st.divider()
    
    # Characters
    chars = analysis.get('characters', {})
    st.markdown("### 👥 Characters")
    
    main_chars = chars.get('main', [])
    if main_chars:
        st.markdown("**Main Characters**")
        for char in main_chars:
            with st.container():
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
    
    # Pacing Analysis
    pacing = analysis.get('pacing_analysis', {})
    if pacing:
        st.markdown("### ⏱️ Pacing Analysis")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overall", pacing.get('overall', 'Unknown'))
        with col2:
            st.metric("Opening", pacing.get('opening', 'Unknown'))
        with col3:
            st.metric("Ending", pacing.get('ending', 'Unknown'))
        
        if pacing.get('tension_curve'):
            st.write(f"**Tension Curve:** {pacing['tension_curve']}")
        
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
            if target.get('demographics'):
                st.markdown(f"**Demographics:** {', '.join(target['demographics'])}")
        
        with col2:
            if target.get('comparable_titles'):
                st.markdown("**Comparable Titles:**")
                for comp in target['comparable_titles']:
                    if isinstance(comp, dict):
                        st.markdown(f"• **{comp.get('title', '')}**")
                        if comp.get('similarity'):
                            st.write(f"  *Similar:* {comp['similarity']}")
                        if comp.get('difference'):
                            st.write(f"  *Different:* {comp['difference']}")


# For direct testing
if __name__ == "__main__":
    show_analyzer()

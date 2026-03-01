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
    st.markdown("Upload your manuscript and cover for deep literary analysis with **marketability scoring**")
    st.markdown("---")
    
    # API Key input with instructions
    if not st.session_state.openai_api_key:
        with st.container():
            st.markdown("### 🔑 OpenAI API Key")
            
            # API Key input FIRST (above instructions)
            api_key = st.text_input("Enter your API key", type="password", key="api_key_input")
            
            # Instructions below the input
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
            
            # Check if key was entered
            if api_key:
                st.session_state.openai_api_key = api_key
                st.rerun()
        return
    
    # If analysis is complete, show results
    if st.session_state.analysis_complete and st.session_state.analysis_result:
        st.success("✅ Analysis complete! Your book has been analyzed with marketability scoring.")
        
        # Action buttons at the top with instructions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            book_title = st.session_state.analysis_result.get('book_info', {}).get('title', 'Untitled')
            filename = f"{book_title.replace(' ', '_')}_analysis.json"
            
            st.markdown("**Step 1**")
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
                st.success(f"✅ Saved!")
            st.caption("Save this analysis to create marketing assets")
        
        with col2:
            st.markdown("**Step 2**")
            if st.button("🎨 Go to Marketing Assets", type="primary", use_container_width=True):
                st.session_state.page = "🎨 Marketing Assets"
                st.rerun()
            st.caption("Create your marketing assets")
        
        with col3:
            st.markdown("**Step 3**")
            if st.button("🔄 New Analysis", use_container_width=True):
                st.session_state.analysis_complete = False
                st.session_state.analysis_result = None
                st.session_state.cover_analysis = None
                st.rerun()
            st.caption("If you've made changes, run analysis again")
        
        st.markdown("---")
        
        # Show analysis results with marketability scores prominently displayed
        show_analysis_results(st.session_state.analysis_result, st.session_state.cover_analysis)
        
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
                
                # Step 2: Deep manuscript analysis with marketability
                analysis = analyze_manuscript_with_marketability(client, manuscript_text, cover_analysis)
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


def analyze_manuscript_with_marketability(client, text, cover_analysis):
    """Single comprehensive manuscript analysis with marketability scoring"""
    
    # Truncate if needed
    if len(text) > 50000:
        text = text[:50000] + "... [truncated]"
    
    # Get beginning, middle, end for context
    total_len = len(text)
    beginning = text[:min(5000, total_len//3)]
    middle = text[total_len//3:total_len//3*2][:5000]
    ending = text[-5000:]
    
    prompt = f"""
    You are a professional literary analyst and publishing industry expert. Analyze this book in depth with special focus on its **marketability and commercial potential**.
    
    COVER ANALYSIS (for context):
    {json.dumps(cover_analysis, indent=2)}
    
    MANUSCRIPT EXCERPTS:
    
    BEGINNING:
    {beginning}
    
    MIDDLE:
    {middle}
    
    ENDING:
    {ending}
    
    Based on these excerpts, provide a COMPLETE analysis as JSON with the following structure.
    
    CRITICAL: Include a comprehensive marketability section with numerical scores (0-100) for:
    - Overall Marketability Score
    - Writing Quality Score
    - Commercial Potential Score
    - Genre Fit Score
    - Hook Strength Score
    - Character Appeal Score
    - Pacing Score
    - Originality Score
    - Target Audience Appeal Score
    
    For each score, provide a brief explanation and specific justification.
    
    Here's the complete JSON structure to return:
    
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
                {{"title": "Alternative Title 1", "rationale": "Why this works better", "estimated_impact": "High/Medium/Low"}},
                {{"title": "Alternative Title 2", "rationale": "Why this works better", "estimated_impact": "High/Medium/Low"}},
                {{"title": "Alternative Title 3", "rationale": "Why this works better", "estimated_impact": "High/Medium/Low"}},
                {{"title": "Alternative Title 4", "rationale": "Why this works better", "estimated_impact": "High/Medium/Low"}},
                {{"title": "Alternative Title 5", "rationale": "Why this works better", "estimated_impact": "High/Medium/Low"}}
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
            "pacing": "fast/medium/slow with explanation"
        }},
        
        "characters": {{
            "main": [
                {{"name": "name", "role": "protagonist/antagonist/etc", 
                  "description": "who they are", 
                  "arc": "how they change throughout the story",
                  "motivation": "what drives them",
                  "conflict": "internal or external struggles",
                  "appeal_factor": "Why readers will connect"}}
            ],
            "supporting": ["list of supporting characters"],
            "relationships": ["key dynamics between characters"]
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
        
        "character_development": {{
            "protagonist_journey": "how the main character changes",
            "antagonist_motivation": "what drives the opposition",
            "supporting_arcs": ["how other characters evolve"]
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
                {"role": "system", "content": "You are a literary analyst and publishing industry expert. Return valid JSON only with comprehensive marketability analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=6000,
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
    """Display analysis results with marketability scores prominently"""
    
    # MARKETABILITY SCORES - Display prominently at the top
    if 'marketability' in analysis:
        market = analysis['marketability']
        
        # Create a visually striking score card
        st.markdown("## 📊 MARKETABILITY ANALYSIS")
        
        # Overall score in a big box
        overall_score = market.get('overall_score', 0)
        overall_grade = market.get('overall_grade', 'N/A')
        
        # Determine color based on score
        if overall_score >= 80:
            score_color = "#00cc66"  # Green
            emoji = "🚀"
            score_text = "EXCELLENT MARKETABILITY"
        elif overall_score >= 70:
            score_color = "#ffaa00"  # Orange/Yellow
            emoji = "📈"
            score_text = "GOOD MARKETABILITY"
        elif overall_score >= 60:
            score_color = "#ff8800"  # Dark Orange
            emoji = "📊"
            score_text = "FAIR MARKETABILITY"
        else:
            score_color = "#ff4444"  # Red
            emoji = "⚠️"
            score_text = "NEEDS WORK"
        
        # Display main score card
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 10px; border: 2px solid {score_color};">
                <h1 style="font-size: 60px; margin: 0; color: {score_color};">{overall_score}</h1>
                <h2 style="margin: 0; color: {score_color};">{score_text}</h2>
                <p style="font-size: 24px; margin: 0;">Grade: {overall_grade} {emoji}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"**Overall Assessment:** {market.get('overall_assessment', '')}")
        st.markdown("---")
        
        # Individual scores in a grid
        st.markdown("### 📈 Detailed Scores")
        
        scores = market.get('scores', {})
        
        # Create 4 rows of 2 columns each for 8 scores
        score_items = list(scores.items())
        for i in range(0, len(score_items), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(score_items):
                    score_name, score_data = score_items[i + j]
                    # Format the score name for display
                    display_name = score_name.replace('_', ' ').title()
                    score_value = score_data.get('score', 0)
                    explanation = score_data.get('explanation', '')
                    
                    # Color code individual scores
                    if score_value >= 80:
                        bg_color = "#e6f7e6"
                        border_color = "#00cc66"
                    elif score_value >= 70:
                        bg_color = "#fff4e6"
                        border_color = "#ffaa00"
                    elif score_value >= 60:
                        bg_color = "#fff0e6"
                        border_color = "#ff8800"
                    else:
                        bg_color = "#ffe6e6"
                        border_color = "#ff4444"
                    
                    with cols[j]:
                        st.markdown(f"""
                        <div style="padding: 15px; background-color: {bg_color}; border-radius: 8px; border-left: 5px solid {border_color}; margin-bottom: 10px;">
                            <h4 style="margin: 0 0 5px 0;">{display_name}</h4>
                            <h2 style="margin: 0; color: {border_color};">{score_value}</h2>
                            <p style="margin: 5px 0 0 0; font-size: 0.9em;">{explanation}</p>
                        </div>
                        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Comparable successes and market analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏆 Comparable Successes")
            comps = market.get('comparable_successes', [])
            for comp in comps:
                if isinstance(comp, dict):
                    st.markdown(f"**{comp.get('title', '')}**")
                    st.write(f"*Similarity:* {comp.get('similarity', '')}")
                    st.write(f"*Why it succeeded:* {comp.get('why_it_succeeded', '')}")
                    st.markdown("---")
        
        with col2:
            st.markdown("### 🔍 Market Position")
            st.markdown(f"**Market Gap:** {market.get('market_gap_analysis', '')}")
            st.markdown(f"**Competitive Advantage:** {market.get('competitive_advantage', '')}")
            
            st.markdown("**Potential Challenges:**")
            for challenge in market.get('potential_challenges', []):
                st.write(f"• {challenge}")
        
        st.markdown("---")
    
    # WRITING QUALITY DETAILED
    if 'writing_quality_detailed' in analysis:
        writing = analysis['writing_quality_detailed']
        
        st.markdown("### ✍️ Writing Quality Deep Dive")
        
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
            for strength in writing.get('strengths', []):
                st.write(f"• {strength}")
        
        with col2:
            st.markdown("**📝 Needed Improvements:**")
            for imp in writing.get('improvements', []):
                st.write(f"• {imp}")
        
        st.markdown("---")
    
    # TITLE ANALYSIS
    if 'title_analysis' in analysis:
        title_analysis = analysis['title_analysis']
        
        st.markdown("### 🏷️ Title Analysis")
        
        current_title = title_analysis.get('current_title', 'Unknown')
        st.markdown(f"**Current Title:** {current_title}")
        
        # Title effectiveness
        effectiveness = title_analysis.get('title_effectiveness', {})
        if effectiveness:
            score = effectiveness.get('score', 0)
            st.markdown(f"**Title Effectiveness Score:** {score}/100")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"*Memorability:* {effectiveness.get('memorability', '')}")
                st.markdown(f"*Genre Appropriateness:* {effectiveness.get('genre_appropriateness', '')}")
            with col2:
                st.markdown(f"*Uniqueness:* {effectiveness.get('uniqueness', '')}")
                st.markdown(f"*Searchability:* {effectiveness.get('searchability', '')}")
        
        # Title suggestions
        suggestions = title_analysis.get('suggested_titles', [])
        if suggestions:
            st.markdown("**💡 Suggested Alternative Titles:**")
            
            for i, suggestion in enumerate(suggestions, 1):
                if isinstance(suggestion, dict):
                    impact = suggestion.get('estimated_impact', 'Medium')
                    # Color code impact
                    if impact.lower() == 'high':
                        impact_display = "🔴 HIGH IMPACT"
                    elif impact.lower() == 'medium':
                        impact_display = "🟡 MEDIUM IMPACT"
                    else:
                        impact_display = "🟢 LOW IMPACT"
                    
                    st.markdown(f"""
                    <div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px; margin-bottom: 10px;">
                        <strong>{i}. {suggestion.get('title', '')}</strong> - {impact_display}<br>
                        <em>{suggestion.get('rationale', '')}</em>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Recommendation
        rec = title_analysis.get('title_change_recommendation', '')
        if rec:
            st.markdown(f"**Recommendation:** {rec}")
        
        subtitle = title_analysis.get('subtitle_suggestion', '')
        if subtitle:
            st.markdown(f"**Suggested Subtitle:** {subtitle}")
        
        st.markdown("---")
    
    # SALABILITY ANALYSIS
    if 'salability_analysis' in analysis:
        salability = analysis['salability_analysis']
        
        st.markdown("### 💰 Salability Analysis")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Market Size", salability.get('estimated_market_size', 'Unknown'))
        with col2:
            st.metric("Series Potential", salability.get('series_potential', 'Unknown'))
        with col3:
            st.metric("Adaptation Potential", salability.get('adaptation_potential', 'Unknown'))
        
        st.markdown(f"**Target Retailers:** {', '.join(salability.get('target_retailers', []))}")
        
        # Format potential
        format_potential = salability.get('format_potential', {})
        if format_potential:
            st.markdown("**Format Potential:**")
            cols = st.columns(4)
            formats = list(format_potential.items())
            for i, (fmt, potential) in enumerate(formats[:4]):
                with cols[i]:
                    st.markdown(f"**{fmt.title()}:** {potential}")
        
        # Comparable bestsellers
        comps = salability.get('comparable_bestsellers', [])
        if comps:
            st.markdown("**Comparable Bestsellers:**")
            for comp in comps:
                if isinstance(comp, dict):
                    st.markdown(f"• **{comp.get('title', '')}** - {comp.get('similarity', '')} (Est. {comp.get('copies_sold', 'Unknown')} copies)")
        
        st.markdown("---")
    
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
    
    # Book Info - Proper font sizes (not huge)
    book_info = analysis.get('book_info', {})
    st.markdown("### 📖 Book Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**Title**")
        st.write(book_info.get('title', 'Unknown'))
    with col2:
        st.markdown("**Genre**")
        st.write(book_info.get('genre', 'Unknown'))
    with col3:
        st.markdown("**Tone**")
        st.write(book_info.get('tone', 'Unknown'))
    with col4:
        st.markdown("**Pacing**")
        st.write(book_info.get('pacing', 'Unknown'))
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Writing Style**")
        st.write(book_info.get('writing_style', 'Unknown'))
    with col2:
        st.markdown("**Subgenres**")
        subgenres = book_info.get('subgenres', [])
        st.write(', '.join(subgenres) if subgenres else 'None')
    
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
        for i in range(0, len(main_chars), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(main_chars):
                    char = main_chars[i + j]
                    with cols[j]:
                        with st.container():
                            st.markdown(f"**{char.get('name', 'Unknown')}** *({char.get('role', '')})*")
                            st.write(f"*Description:* {char.get('description', '')}")
                            if char.get('motivation'):
                                st.write(f"*Motivation:* {char.get('motivation')}")
                            if char.get('conflict'):
                                st.write(f"*Conflict:* {char.get('conflict')}")
                            if char.get('arc'):
                                st.write(f"*Arc:* {char.get('arc')}")
                            if char.get('appeal_factor'):
                                st.write(f"*Appeal:* {char.get('appeal_factor')}")
    
    # Character Development
    dev = analysis.get('character_development', {})
    if dev:
        with st.expander("📈 Character Development"):
            if dev.get('protagonist_journey'):
                st.markdown(f"**Protagonist Journey:** {dev['protagonist_journey']}")
            if dev.get('antagonist_motivation'):
                st.markdown(f"**Antagonist Motivation:** {dev['antagonist_motivation']}")
            if dev.get('supporting_arcs'):
                st.markdown("**Supporting Arcs:**")
                for arc in dev['supporting_arcs']:
                    st.write(f"• {arc}")
    
    if chars.get('supporting'):
        with st.expander("👥 Supporting Characters"):
            for char in chars.get('supporting', []):
                st.write(f"• {char}")
    
    if chars.get('relationships'):
        with st.expander("🔄 Key Relationships"):
            for rel in chars.get('relationships', []):
                st.write(f"• {rel}")
    
    st.divider()
    
    # Plot & Themes
    col1, col2 = st.columns(2)
    
    with col1:
        plot = analysis.get('plot', {})
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
    
    with col2:
        themes = analysis.get('themes', {})
        st.markdown("### 🎨 Themes")
        
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
    
    # Pacing Analysis
    pacing = analysis.get('pacing_analysis', {})
    if pacing:
        st.markdown("### ⏱️ Pacing")
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
                keywords = marketing['keyword_cloud']
                if isinstance(keywords, list):
                    st.write(', '.join(keywords))
        
        if marketing.get('compelling_quotes'):
            st.markdown("**Pull Quotes:**")
            for quote in marketing['compelling_quotes']:
                st.info(f"“{quote}”")
        
        if marketing.get('blurb_suggestion'):
            with st.expander("📝 Suggested Blurb"):
                st.write(marketing['blurb_suggestion'])


# For direct testing
if __name__ == "__main__":
    show_analyzer()

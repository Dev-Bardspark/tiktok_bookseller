# marketing_plan_wizard.py - FIXED with DATA DISPLAY and REAL REASONS
import streamlit as st
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from openai import OpenAI

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

def load_user_book_analysis(user_id):
    """Load the most recent book analysis"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_book_analyses 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        result = cur.fetchone()
        return dict(result) if result else None
    except Exception as e:
        st.error(f"Error loading book analysis: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def load_user_persona(user_id):
    """Load the most recent author persona"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_author_personas 
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        result = cur.fetchone()
        return dict(result) if result else None
    except Exception as e:
        st.error(f"Error loading author persona: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def load_user_marketing_assets(user_id):
    """Load ALL marketing assets and combine them"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT asset_type, asset_data FROM user_marketing_assets 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        rows = cur.fetchall()
        if not rows:
            return None
        
        combined_assets = {}
        for row in rows:
            asset_data = row['asset_data']
            if isinstance(asset_data, str):
                try:
                    asset_data = json.loads(asset_data)
                except:
                    continue
            if isinstance(asset_data, dict):
                combined_assets.update(asset_data)
        
        return combined_assets
    except Exception as e:
        st.error(f"Error loading marketing assets: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def save_marketing_plan(user_id, plan_data):
    """Save generated plan to database"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_marketing_plans 
            (user_id, plan_name, plan_data, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            f"Marketing Plan {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            json.dumps(plan_data),
            datetime.now()
        ))
        
        plan_id = cur.fetchone()[0]
        conn.commit()
        return plan_id
    except Exception as e:
        st.error(f"Error saving plan: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def extract_book_info(analysis_data):
    """Extract book info from analysis data"""
    if not analysis_data:
        return {}
    
    if isinstance(analysis_data, dict):
        if 'analysis_result' in analysis_data:
            result = analysis_data['analysis_result']
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    pass
            if isinstance(result, dict) and 'book_info' in result:
                return result['book_info']
        elif 'book_info' in analysis_data:
            return analysis_data['book_info']
        elif 'title' in analysis_data:
            return analysis_data
    
    return {}

def extract_persona_data(persona_record):
    """Extract persona data from database record"""
    if not persona_record:
        return {}
    
    persona_data = persona_record.get('persona_data')
    if isinstance(persona_data, str):
        try:
            return json.loads(persona_data)
        except:
            return {}
    return persona_data or {}

def generate_marketing_plan(client, book_info, persona_data, assets):
    """Call OpenAI to generate a marketing plan with REAL reasoning"""
    
    prompt = f"""
    Create a comprehensive 90-day marketing plan for this book.
    
    You MUST base ALL decisions on the actual data provided below.
    For EVERY recommendation, explain WHY based on the book genre, author persona, and available assets.
    
    ========== YOUR DATA ==========
    
    BOOK INFORMATION:
    {json.dumps(book_info, indent=2)}
    
    AUTHOR PERSONA:
    {json.dumps(persona_data, indent=2)}
    
    EXISTING ASSETS (use these specifically):
    {json.dumps(assets, indent=2)}
    
    ========== REQUIREMENTS ==========
    
    Return a JSON with:
    
    1. data_summary: {{
        "book_title": "from data",
        "book_genre": "from data",
        "author_type": "from persona",
        "interaction_style": "from persona",
        "social_battery": "from persona",
        "available_assets": ["list what exists"]
    }}
    
    2. arc_reader_strategy: {{
        "recruitment": "HOW to find ARC readers specifically for THIS genre",
        "timeline": "WHEN to send ARCs",
        "communication": "HOW to communicate with ARC readers",
        "incentives": "WHAT incentives work for THIS audience",
        "review_followup": "HOW to get reviews after reading"
    }}
    
    3. review_generation_plan: {{
        "pre_launch": ["specific actions to get early reviews"],
        "launch_week": ["specific actions during launch"],
        "post_launch": ["specific followup actions"],
        "target_sites": ["Goodreads", "Amazon", "BookBub", etc WITH REASONS"]
    }}
    
    4. platform_recommendations: [
        {{
            "platform": "name",
            "match_score": 0-100,
            "reason_for_match": "EXPLAIN based on genre + persona + social battery",
            "content_strategy": "WHAT to post",
            "frequency": "HOW often based on energy budget",
            "arc_promotion": "HOW to use this platform for ARC recruitment",
            "review_leveraging": "HOW to share reviews on this platform"
        }}
    ]
    
    5. email_sequence_timeline: {{
        "arc_invitation": {{
            "timing": "when to send",
            "subject": "subject line",
            "content": "email content",
            "why_this_works": "reason based on persona"
        }},
        "arc_reminder": {{
            "timing": "when to send",
            "subject": "subject line",
            "content": "email content"
        }},
        "review_request": {{
            "timing": "when to send",
            "subject": "subject line",
            "content": "email content"
        }},
        "launch_announcement": {{
            "timing": "when to send",
            "subject": "subject line",
            "content": "email content"
        }},
        "post_launch_followup": {{
            "timing": "when to send",
            "subject": "subject line",
            "content": "email content"
        }}
    }}
    
    6. weekly_breakdown: [
        {{
            "week": 1,
            "theme": "theme",
            "arc_focus": "what ARC-related task",
            "review_focus": "what review-related task",
            "platform_focus": "main platform to use",
            "specific_action": "exactly what to do",
            "asset_to_use": "which of their existing assets to use"
        }}
    ] (12 weeks)
    
    7. budget_allocation: {{
        "arc_copies": {{
            "amount": "$",
            "how_many": "number",
            "reason": "why this many for this genre"
        }},
        "review_sites": {{
            "amount": "$",
            "which_sites": ["names"],
            "reason": "why these sites"
        }},
        "email_tools": {{
            "amount": "$",
            "reason": "why needed"
        }},
        "ads": {{
            "amount": "$",
            "timing": "when to start",
            "reason": "why this timing"
        }}
    }}
    
    8. success_metrics: {{
        "arc_goals": {{
            "target": "number",
            "timeline": "by when",
            "why_realistic": "reason based on genre"
        }},
        "review_goals": {{
            "amazon": "target by launch",
            "goodreads": "target by launch",
            "why_realistic": "reason based on genre"
        }}
    }}
    
    9. decision_rationale: {{
        "platform_choices": "EXPLAIN why these platforms match this specific author",
        "arc_timing": "EXPLAIN why this timing works for this genre",
        "email_strategy": "EXPLAIN how this fits their interaction style",
        "budget_decisions": "EXPLAIN why this allocation makes sense"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional book marketing strategist. EVERY recommendation must include a specific reason based on the provided data. Never give generic advice - always tie it to the book's genre, the author's persona, or their existing assets."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=5000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Plan generation failed: {str(e)}")
        return None

def show_marketing_plan_wizard():
    """AI-POWERED Marketing Plan Generator with DATA DISPLAY"""
    
    # Check login
    if not st.session_state.get('authenticated', False):
        st.warning("🔒 Please login to access the Marketing Plan Wizard")
        if st.button("Go to Login", use_container_width=True):
            st.session_state.page = "🏠 Dashboard"
            st.rerun()
        return
    
    # Check for API key
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    
    st.title("🤖 AI Marketing Plan Wizard")
    st.markdown("Generate a customized 90-day marketing plan based on YOUR actual data")
    st.markdown("---")
    
    # API Key input
    if not st.session_state.openai_api_key:
        with st.container():
            st.markdown("### 🔑 OpenAI API Key Required")
            api_key = st.text_input("Enter your API key", type="password", key="plan_api_key")
            
            if api_key:
                st.session_state.openai_api_key = api_key
                st.rerun()
        return
    
    user_id = st.session_state.get('user_id', 1)
    
    # LOAD DATA
    with st.spinner("Loading your marketing data..."):
        book_analysis = load_user_book_analysis(user_id)
        author_persona = load_user_persona(user_id)
        marketing_assets = load_user_marketing_assets(user_id)
    
    # Extract data
    book_info = extract_book_info(book_analysis) if book_analysis else None
    persona_data = extract_persona_data(author_persona) if author_persona else None
    
    # ========== SHOW THE DATA ==========
    st.markdown("## 🔍 YOUR DATA (verify this is correct)")
    
    tab1, tab2, tab3 = st.tabs(["📚 Book Data", "🎭 Persona Data", "🎨 Asset Data"])
    
    with tab1:
        if book_info:
            st.json(book_info)
            st.success(f"✅ Book loaded: {book_info.get('title', 'Unknown')}")
        else:
            st.error("❌ NO BOOK DATA FOUND - Please analyze a book first")
            if st.button("📖 Go to Book Analyzer"):
                st.session_state.page = "📖 Book Analyzer"
                st.rerun()
    
    with tab2:
        if persona_data:
            st.json(persona_data)
            st.success(f"✅ Persona loaded: {persona_data.get('author_type', 'Unknown')}")
        else:
            st.error("❌ NO PERSONA DATA FOUND - Please take the persona quiz")
            if st.button("🎭 Discover Your Persona"):
                st.session_state.page = "🎭 Author Persona"
                st.rerun()
    
    with tab3:
        if marketing_assets:
            st.json(marketing_assets)
            asset_types = list(marketing_assets.keys())
            st.success(f"✅ Assets loaded: {len(asset_types)} types available")
            st.markdown("**Asset types:** " + ", ".join(asset_types))
        else:
            st.warning("⚠️ No marketing assets found - optional but recommended")
            if st.button("🎨 Generate Marketing Assets"):
                st.session_state.page = "🎨 Marketing Assets"
                st.rerun()
    
    st.markdown("---")
    
    # Check if we have minimum required data
    if not book_info or not persona_data:
        st.warning("⚠️ You need both a book analysis and author persona to generate a plan.")
        return
    
    # Generate plan button
    if st.button("🚀 GENERATE AI MARKETING PLAN", type="primary", use_container_width=True):
        with st.spinner("🧠 AI is analyzing YOUR data and creating a custom plan... (45-60 seconds)"):
            try:
                client = OpenAI(api_key=st.session_state.openai_api_key)
                
                plan = generate_marketing_plan(
                    client, 
                    book_info, 
                    persona_data, 
                    marketing_assets or {}
                )
                
                if plan:
                    # Save to database
                    plan_id = save_marketing_plan(user_id, plan)
                    
                    if plan_id:
                        st.session_state.generated_plan = plan
                        st.session_state.plan_id = plan_id
                        st.success(f"✅ Plan generated and saved! (ID: {plan_id})")
                        st.rerun()
                    else:
                        st.session_state.generated_plan = plan
                        st.warning("⚠️ Plan generated but failed to save to database")
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Failed to generate plan: {str(e)}")
    
    # Display generated plan if it exists
    if st.session_state.get('generated_plan'):
        plan = st.session_state.generated_plan
        
        st.markdown("---")
        st.markdown(f"## 📋 Your Custom Marketing Plan")
        
        # Show data summary first
        with st.expander("📊 PLAN BASED ON THIS DATA", expanded=True):
            st.json(plan.get('data_summary', {}))
        
        # ARC Reader Strategy
        with st.expander("📚 ARC READER STRATEGY (CRITICAL)", expanded=True):
            arc = plan.get('arc_reader_strategy', {})
            if arc:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Recruitment:** {arc.get('recruitment', '')}")
                    st.markdown(f"**Timeline:** {arc.get('timeline', '')}")
                with col2:
                    st.markdown(f"**Incentives:** {arc.get('incentives', '')}")
                    st.markdown(f"**Review Follow-up:** {arc.get('review_followup', '')}")
                st.markdown(f"**Communication:** {arc.get('communication', '')}")
        
        # Review Generation Plan
        with st.expander("⭐ REVIEW GENERATION PLAN", expanded=True):
            reviews = plan.get('review_generation_plan', {})
            if reviews:
                st.markdown(f"**Target Sites:** {', '.join(reviews.get('target_sites', []))}")
                
                cols = st.columns(3)
                with cols[0]:
                    st.markdown("**Pre-Launch**")
                    for action in reviews.get('pre_launch', []):
                        st.markdown(f"- {action}")
                with cols[1]:
                    st.markdown("**Launch Week**")
                    for action in reviews.get('launch_week', []):
                        st.markdown(f"- {action}")
                with cols[2]:
                    st.markdown("**Post-Launch**")
                    for action in reviews.get('post_launch', []):
                        st.markdown(f"- {action}")
        
        # Platform Recommendations WITH REASONS
        with st.expander("📱 PLATFORM RECOMMENDATIONS (with reasons)", expanded=True):
            platforms = plan.get('platform_recommendations', [])
            for p in platforms:
                with st.container():
                    st.markdown(f"### {p.get('platform', 'Unknown')} - {p.get('match_score', 0)}% Match")
                    st.info(f"**WHY this platform:** {p.get('reason_for_match', '')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Content Strategy:** {p.get('content_strategy', '')}")
                        st.markdown(f"**Frequency:** {p.get('frequency', '')}")
                    with col2:
                        st.markdown(f"**ARC Promotion:** {p.get('arc_promotion', '')}")
                        st.markdown(f"**Review Leveraging:** {p.get('review_leveraging', '')}")
                    st.markdown("---")
        
        # Email Sequence
        with st.expander("📧 EMAIL SEQUENCE", expanded=True):
            email = plan.get('email_sequence_timeline', {})
            for key, value in email.items():
                with st.container():
                    st.markdown(f"**{key.replace('_', ' ').title()}**")
                    if isinstance(value, dict):
                        st.markdown(f"- Timing: {value.get('timing', '')}")
                        st.markdown(f"- Subject: {value.get('subject', '')}")
                        if 'why_this_works' in value:
                            st.markdown(f"- **Why:** {value['why_this_works']}")
        
        # Budget with reasons
        with st.expander("💰 BUDGET ALLOCATION", expanded=True):
            budget = plan.get('budget_allocation', {})
            for key, value in budget.items():
                if isinstance(value, dict):
                    st.markdown(f"**{key.replace('_', ' ').title()}**")
                    st.markdown(f"- Amount: {value.get('amount', '')}")
                    if 'how_many' in value:
                        st.markdown(f"- Quantity: {value['how_many']}")
                    if 'which_sites' in value:
                        st.markdown(f"- Sites: {', '.join(value['which_sites'])}")
                    st.markdown(f"- **Why:** {value.get('reason', '')}")
                    st.markdown("---")
        
        # Decision Rationale (shows WHY)
        with st.expander("🤔 WHY THESE DECISIONS?", expanded=True):
            rationale = plan.get('decision_rationale', {})
            for key, value in rationale.items():
                st.markdown(f"**{key.replace('_', ' ').title()}**")
                st.markdown(value)
                st.markdown("---")
        
        # Weekly Breakdown
        with st.expander("📅 12-WEEK ACTION PLAN", expanded=False):
            weeks = plan.get('weekly_breakdown', [])
            for week in weeks:
                with st.container():
                    st.markdown(f"### Week {week.get('week', '')}: {week.get('theme', '')}")
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown(f"**ARC Focus:** {week.get('arc_focus', '')}")
                        st.markdown(f"**Review Focus:** {week.get('review_focus', '')}")
                    with cols[1]:
                        st.markdown(f"**Platform Focus:** {week.get('platform_focus', '')}")
                        st.markdown(f"**Asset to Use:** {week.get('asset_to_use', '')}")
                    st.markdown(f"**Action:** {week.get('specific_action', '')}")
                    st.markdown("---")
        
        # Success Metrics
        with st.expander("🎯 SUCCESS METRICS", expanded=True):
            metrics = plan.get('success_metrics', {})
            arc_goals = metrics.get('arc_goals', {})
            review_goals = metrics.get('review_goals', {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**ARC Goals**")
                st.markdown(f"Target: {arc_goals.get('target', '')}")
                st.markdown(f"Timeline: {arc_goals.get('timeline', '')}")
                st.info(f"Why: {arc_goals.get('why_realistic', '')}")
            
            with col2:
                st.markdown("**Review Goals**")
                st.markdown(f"Amazon: {review_goals.get('amazon', '')}")
                st.markdown(f"Goodreads: {review_goals.get('goodreads', '')}")
                st.info(f"Why: {review_goals.get('why_realistic', '')}")
        
        # Export
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Generate New Plan", use_container_width=True):
                st.session_state.generated_plan = None
                st.session_state.plan_id = None
                st.rerun()
        
        with col2:
            export_data = json.dumps(plan, indent=2)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"marketing_plan_{timestamp}.json"
            
            st.download_button(
                "📥 Export Plan",
                export_data,
                filename,
                "application/json",
                use_container_width=True
            )

if __name__ == "__main__":
    show_marketing_plan_wizard()

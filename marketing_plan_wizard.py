# marketing_plan_wizard.py - DATA FIRST, EVERYTHING ELSE SECOND
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

def extract_full_analysis(analysis_data):
    """Extract COMPLETE analysis including marketability scores"""
    if not analysis_data:
        return {}
    
    if isinstance(analysis_data, dict):
        if 'analysis_result' in analysis_data:
            result = analysis_data['analysis_result']
            if isinstance(result, str):
                try:
                    return json.loads(result)
                except:
                    return {}
            return result
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

def generate_marketing_plan(client, full_analysis, persona_data, assets):
    """Call OpenAI to generate a marketing plan using ALL available data"""
    
    prompt = f"""
    Create a SPECIFIC, ACTIONABLE 90-day marketing plan for this book.
    
    EVERY recommendation must be DIRECTLY tied to the data below.
    NO generic advice. EVERY decision needs a "BECAUSE" statement.
    
    ========== COMPLETE BOOK DATA ==========
    
    FULL ANALYSIS (everything the Book Analyzer produced):
    {json.dumps(full_analysis, indent=2)}
    
    ========== AUTHOR PERSONA ==========
    {json.dumps(persona_data, indent=2)}
    
    ========== EXISTING ASSETS ==========
    {json.dumps(assets, indent=2)}
    
    ========== REQUIRED OUTPUT STRUCTURE ==========
    
    Return a JSON with:
    
    1. book_summary: {{
        "title": "from data",
        "marketability_score": "from data",
        "key_strengths": ["list 3-5 main strengths to highlight"],
        "target_audience_description": "detailed description",
        "unique_selling_points": ["specific points based on analysis"]
    }}
    
    2. arc_reader_strategy: {{
        "recruitment_approach": "EXACTLY how to find ARC readers for THIS specific audience",
        "where_to_find_them": ["specific places/communities based on genre and themes"],
        "arc_timeline": {{
            "recruitment_start": "date",
            "arcs_sent": "date", 
            "reviews_due": "date"
        }},
        "arc_email_template": "full email template to recruit ARCs",
        "follow_up_template": "full email template for follow-up",
        "why_this_works": "explain why this approach fits this specific book"
    }}
    
    3. review_generation_plan: {{
        "pre_launch_review_targets": {{
            "Goodreads": "target number",
            "Amazon": "target number",
            "specific_action": "exactly what to do to get these"
        }},
        "launch_week_review_actions": [
            "specific action 1",
            "specific action 2"
        ],
        "review_request_templates": {{
            "email": "full template",
            "social": "full template"
        }},
        "incentive_strategy": "what incentives work for THIS audience"
    }}
    
    4. platform_recommendations: [
        {{
            "platform": "name",
            "priority": "High/Medium/Low",
            "exact_reason": "BECAUSE [tie directly to book content/audience/persona]",
            "content_ideas": [
                "specific idea 1 using their actual quotes/themes",
                "specific idea 2 using their actual quotes/themes"
            ],
            "posting_frequency": "based on their social battery",
            "arc_promotion_plan": "how to use this platform for ARC recruitment"
        }}
    ]
    
    5. email_marketing_plan: {{
        "sequence_name": "name for sequence",
        "emails": [
            {{
                "day": "Day X",
                "subject": "subject line",
                "purpose": "purpose of this email",
                "full_content": "complete email content using their actual book content"
            }}
        ]
    }}
    
    6. weekly_breakdown: [
        {{
            "week": 1,
            "focus": "focus area",
            "arc_task": "specific ARC task",
            "review_task": "specific review task",
            "content_task": "specific content to create",
            "platform_to_use": "specific platform",
            "asset_to_leverage": "which existing asset to use"
        }}
    ] (12 weeks)
    
    7. budget_breakdown: {{
        "arc_copies": {{
            "quantity": "number",
            "cost": "$",
            "reason": "why this many for this genre"
        }},
        "review_site_promotions": {{
            "sites": ["names"],
            "cost": "$",
            "reason": "why these sites"
        }},
        "advertising": {{
            "platforms": ["names"],
            "cost": "$",
            "timing": "when to start",
            "reason": "why this timing"
        }}
    }}
    
    8. success_metrics: {{
        "arc_goals": {{
            "target": "number",
            "deadline": "date",
            "why_realistic": "based on genre data"
        }},
        "review_goals": {{
            "launch_day": "target",
            "first_week": "target",
            "first_month": "target"
        }}
    }}
    
    9. decision_rationale_summary: {{
        "platform_choices": "explain why these platforms match THIS book",
        "arc_strategy": "explain why this ARC approach works for THIS audience",
        "timing_decisions": "explain why this timeline",
        "budget_decisions": "explain why this budget allocation"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional book marketing strategist. Create SPECIFIC, ACTIONABLE plans. EVERY recommendation must include 'BECAUSE' with a reason tied to the actual book data. NEVER give generic advice."},
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
    """AI-POWERED Marketing Plan Generator using COMPLETE analysis"""
    
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
    
    # ========== STEP 1: LOAD ALL DATA ==========
    st.markdown("## 📥 STEP 1: LOADING YOUR DATA")
    
    with st.spinner("Loading your data from database..."):
        book_analysis = load_user_book_analysis(user_id)
        author_persona = load_user_persona(user_id)
        marketing_assets = load_user_marketing_assets(user_id)
    
    # ========== STEP 2: EXTRACT AND VERIFY DATA ==========
    st.markdown("## 🔍 STEP 2: VERIFY YOUR DATA")
    
    full_analysis = extract_full_analysis(book_analysis) if book_analysis else None
    persona_data = extract_persona_data(author_persona) if author_persona else None
    
    # SHOW EVERYTHING THAT WAS LOADED
    
    st.markdown("### 📚 BOOK ANALYSIS DATA")
    if full_analysis:
        st.success(f"✅ Book data loaded: {full_analysis.get('book_info', {}).get('title', 'Unknown')}")
        
        # Show marketability score if available
        marketability = full_analysis.get('marketability_dashboard', {})
        if marketability:
            st.metric("Marketability Score", f"{marketability.get('overall_score', 'N/A')} - {marketability.get('grade', 'N/A')}")
        
        # Show complete raw data
        with st.expander("VIEW COMPLETE BOOK ANALYSIS JSON", expanded=True):
            st.json(full_analysis)
        
        # Show key sections
        col1, col2 = st.columns(2)
        with col1:
            strengths = full_analysis.get('key_strengths', [])
            if strengths:
                st.markdown("**Key Strengths:**")
                for s in strengths:
                    st.markdown(f"✅ {s}")
        
        with col2:
            target = full_analysis.get('target_audience', {})
            if target:
                st.markdown(f"**Target Audience:** {target.get('primary_audience', 'N/A')}")
        
        # Show compelling quotes if available
        quotes = full_analysis.get('marketing_insights', {}).get('compelling_quotes', [])
        if quotes:
            st.markdown("**Compelling Quotes for Marketing:**")
            for q in quotes:
                st.markdown(f"💬 {q}")
    else:
        st.error("❌ NO BOOK ANALYSIS FOUND")
        if st.button("📖 Go to Book Analyzer"):
            st.session_state.page = "📖 Book Analyzer"
            st.rerun()
        return
    
    st.markdown("---")
    
    st.markdown("### 🎭 AUTHOR PERSONA DATA")
    if persona_data:
        st.success(f"✅ Persona loaded: {persona_data.get('author_type', 'Unknown')}")
        with st.expander("VIEW COMPLETE PERSONA JSON", expanded=True):
            st.json(persona_data)
    else:
        st.warning("⚠️ No author persona found - plan will be based only on book data")
        with st.expander("VIEW PERSONA DATA", expanded=True):
            st.json({})
    
    st.markdown("---")
    
    st.markdown("### 🎨 MARKETING ASSETS DATA")
    if marketing_assets:
        st.success(f"✅ Assets loaded: {len(marketing_assets)} types available")
        with st.expander("VIEW ASSETS JSON", expanded=True):
            st.json(list(marketing_assets.keys()))
    else:
        st.info("ℹ️ No marketing assets found - optional")
        with st.expander("VIEW ASSETS DATA", expanded=True):
            st.json({})
    
    st.markdown("---")
    
    # ========== STEP 3: GENERATE PLAN ==========
    st.markdown("## 🚀 STEP 3: GENERATE MARKETING PLAN")
    
    if st.button("GENERATE PLAN USING YOUR DATA ABOVE", type="primary", use_container_width=True):
        with st.spinner("🧠 AI is analyzing YOUR data above and creating a custom plan... (45-60 seconds)"):
            try:
                client = OpenAI(api_key=st.session_state.openai_api_key)
                
                plan = generate_marketing_plan(
                    client, 
                    full_analysis, 
                    persona_data or {}, 
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
    
    # ========== STEP 4: DISPLAY PLAN ==========
    if st.session_state.get('generated_plan'):
        plan = st.session_state.generated_plan
        
        st.markdown("---")
        st.markdown("## 📋 YOUR CUSTOM MARKETING PLAN")
        
        # Book Summary
        with st.expander("📖 BOOK SUMMARY", expanded=True):
            summary = plan.get('book_summary', {})
            if summary:
                st.markdown(f"**Title:** {summary.get('title', 'N/A')}")
                st.markdown(f"**Marketability Score:** {summary.get('marketability_score', 'N/A')}")
                st.markdown(f"**Target Audience:** {summary.get('target_audience_description', 'N/A')}")
                st.markdown("**Unique Selling Points:**")
                for usp in summary.get('unique_selling_points', []):
                    st.markdown(f"• {usp}")
        
        # ARC Strategy
        with st.expander("📚 ARC READER STRATEGY", expanded=True):
            arc = plan.get('arc_reader_strategy', {})
            if arc:
                st.markdown(f"**Recruitment Approach:** {arc.get('recruitment_approach', '')}")
                st.markdown("**Where to Find ARC Readers:**")
                for place in arc.get('where_to_find_them', []):
                    st.markdown(f"• {place}")
                
                timeline = arc.get('arc_timeline', {})
                if timeline:
                    st.markdown("**Timeline:**")
                    st.markdown(f"• Recruitment Start: {timeline.get('recruitment_start', '')}")
                    st.markdown(f"• ARCs Sent: {timeline.get('arcs_sent', '')}")
                    st.markdown(f"• Reviews Due: {timeline.get('reviews_due', '')}")
                
                st.markdown("**ARC Email Template:**")
                st.info(arc.get('arc_email_template', ''))
                st.markdown(f"**Why This Works:** {arc.get('why_this_works', '')}")
        
        # Review Generation
        with st.expander("⭐ REVIEW GENERATION PLAN", expanded=True):
            reviews = plan.get('review_generation_plan', {})
            if reviews:
                targets = reviews.get('pre_launch_review_targets', {})
                if targets:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"Goodreads Target: {targets.get('Goodreads', 'N/A')}")
                    with col2:
                        st.markdown(f"Amazon Target: {targets.get('Amazon', 'N/A')}")
                    st.markdown(f"**Action:** {targets.get('specific_action', '')}")
                
                st.markdown("**Review Request Templates:**")
                templates = reviews.get('review_request_templates', {})
                if templates.get('email'):
                    st.markdown("📧 Email Template:")
                    st.info(templates['email'])
        
        # Platform Recommendations
        with st.expander("📱 PLATFORM RECOMMENDATIONS", expanded=True):
            platforms = plan.get('platform_recommendations', [])
            for p in platforms:
                priority_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(p.get('priority', ''), "⚪")
                st.markdown(f"### {priority_color} {p.get('platform', '')} - {p.get('priority', '')} Priority")
                st.markdown(f"**BECAUSE:** {p.get('exact_reason', '')}")
                
                st.markdown("**Content Ideas:**")
                for idea in p.get('content_ideas', []):
                    st.markdown(f"• {idea}")
                
                st.markdown(f"**Frequency:** {p.get('posting_frequency', '')}")
                st.markdown("---")
        
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

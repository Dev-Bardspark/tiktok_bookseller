# marketing_plan_wizard.py - AI-POWERED VERSION
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
    """Call OpenAI to generate a marketing plan"""
    
    prompt = f"""
    Create a comprehensive 90-day marketing plan for this book based on the author's persona and existing assets.
    
    BOOK INFORMATION:
    {json.dumps(book_info, indent=2)}
    
    AUTHOR PERSONA:
    {json.dumps(persona_data, indent=2)}
    
    EXISTING MARKETING ASSETS (use these in the plan):
    {json.dumps(assets, indent=2)}
    
    Return a JSON with:
    
    1. overview: {{
        "book_title": "title",
        "author_type": "persona type",
        "target_audience": "primary reader demographic",
        "unique_selling_points": ["point1", "point2", "point3"],
        "campaign_theme": "overarching theme"
    }}
    
    2. monthly_breakdown: [
        {{
            "month": 1,
            "theme": "month theme",
            "focus": "primary focus",
            "weekly_actions": [
                "Week 1: action",
                "Week 2: action",
                "Week 3: action", 
                "Week 4: action"
            ],
            "key_platforms": ["platform1", "platform2"],
            "content_milestones": ["milestone1", "milestone2"]
        }},
        ... (months 2 and 3)
    ]
    
    3. platform_strategy: [
        {{
            "platform": "name",
            "frequency": "how often to post",
            "content_types": ["type1", "type2"],
            "goals": ["goal1", "goal2"],
            "best_times": "when to post"
        }}
    ]
    
    4. asset_utilization: {{
        "blurbs": "how to use blurbs in the plan",
        "tiktok_scripts": "when to use which scripts",
        "email_sequences": "timing for email campaigns",
        "launch_timeline": "how to adapt the timeline"
    }}
    
    5. budget_recommendations: {{
        "minimum": "$ amount",
        "recommended": "$ amount",
        "allocation": {{
            "ads": "percentage",
            "promotions": "percentage",
            "tools": "percentage",
            "events": "percentage"
        }}
    }}
    
    6. success_metrics: {{
        "week_1": ["metric1", "metric2"],
        "month_1": ["metric1", "metric2"],
        "month_3": ["metric1", "metric2"]
    }}
    
    7. risks_and_mitigations: [
        {{
            "risk": "description",
            "mitigation": "strategy"
        }}
    ]
    
    8. weekly_checklist: [
        "Week 1 task",
        "Week 2 task",
        ... (through week 12)
    ]
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional book marketing strategist. Create detailed, actionable marketing plans based on the book and author data provided."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Plan generation failed: {str(e)}")
        return None

def show_marketing_plan_wizard():
    """AI-POWERED Marketing Plan Generator"""
    
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
    st.markdown("Generate a customized 90-day marketing plan based on your book and author persona")
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
    
    # Show status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if book_info:
            st.success(f"✅ Book: {book_info.get('title', 'Unknown')}")
        else:
            st.error("❌ No book analysis found")
    
    with col2:
        if persona_data:
            st.success(f"✅ Persona: {persona_data.get('author_type', 'Unknown')}")
        else:
            st.error("❌ No author persona found")
    
    with col3:
        if marketing_assets:
            st.success(f"✅ Assets: {len(marketing_assets)} types available")
        else:
            st.warning("⚠️ No marketing assets found (optional)")
    
    st.markdown("---")
    
    # Check if we have minimum required data
    if not book_info or not persona_data:
        st.warning("⚠️ You need both a book analysis and author persona to generate a plan.")
        
        if not book_info:
            if st.button("📖 Go to Book Analyzer"):
                st.session_state.page = "📖 Book Analyzer"
                st.rerun()
        
        if not persona_data:
            if st.button("🎭 Discover Your Persona"):
                st.session_state.page = "🎭 Author Persona"
                st.rerun()
        
        return
    
    # Generate plan button
    if st.button("🚀 GENERATE AI MARKETING PLAN", type="primary", use_container_width=True):
        with st.spinner("🧠 AI is creating your custom 90-day marketing plan... (30-45 seconds)"):
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
        st.markdown(f"## 📋 Your 90-Day Marketing Plan")
        
        # Overview section
        with st.container():
            st.markdown("### 📊 Campaign Overview")
            
            overview = plan.get('overview', {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Book:** {overview.get('book_title', 'Unknown')}")
                st.markdown(f"**Author Type:** {overview.get('author_type', 'Unknown')}")
                st.markdown(f"**Target Audience:** {overview.get('target_audience', 'Unknown')}")
            
            with col2:
                st.markdown(f"**Campaign Theme:** {overview.get('campaign_theme', 'Unknown')}")
                st.markdown("**Unique Selling Points:**")
                for usp in overview.get('unique_selling_points', []):
                    st.markdown(f"- {usp}")
        
        st.markdown("---")
        
        # Monthly breakdown
        st.markdown("### 📅 Monthly Breakdown")
        
        months = plan.get('monthly_breakdown', [])
        month_tabs = st.tabs([f"Month {m.get('month', i+1)}: {m.get('theme', '')}" for i, m in enumerate(months)])
        
        for i, (tab, month) in enumerate(zip(month_tabs, months)):
            with tab:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Focus:** {month.get('focus', '')}")
                    st.markdown("**Weekly Actions:**")
                    for action in month.get('weekly_actions', []):
                        st.markdown(f"- {action}")
                
                with col2:
                    st.markdown(f"**Key Platforms:** {', '.join(month.get('key_platforms', []))}")
                    st.markdown("**Content Milestones:**")
                    for milestone in month.get('content_milestones', []):
                        st.markdown(f"- {milestone}")
        
        st.markdown("---")
        
        # Platform Strategy
        st.markdown("### 📱 Platform Strategy")
        
        platforms = plan.get('platform_strategy', [])
        for platform in platforms:
            with st.expander(f"**{platform.get('platform', 'Unknown')}**"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Frequency:** {platform.get('frequency', '')}")
                    st.markdown(f"**Best Times:** {platform.get('best_times', '')}")
                with col2:
                    st.markdown("**Content Types:**")
                    for ct in platform.get('content_types', []):
                        st.markdown(f"- {ct}")
                    st.markdown("**Goals:**")
                    for goal in platform.get('goals', []):
                        st.markdown(f"- {goal}")
        
        st.markdown("---")
        
        # Asset Utilization
        st.markdown("### 🎯 How to Use Your Existing Assets")
        
        asset_util = plan.get('asset_utilization', {})
        cols = st.columns(2)
        with cols[0]:
            if asset_util.get('blurbs'):
                st.info(f"📝 **Blurbs:** {asset_util['blurbs']}")
            if asset_util.get('tiktok_scripts'):
                st.info(f"🎬 **TikTok:** {asset_util['tiktok_scripts']}")
        with cols[1]:
            if asset_util.get('email_sequences'):
                st.info(f"📧 **Email:** {asset_util['email_sequences']}")
            if asset_util.get('launch_timeline'):
                st.info(f"📅 **Launch:** {asset_util['launch_timeline']}")
        
        st.markdown("---")
        
        # Budget
        st.markdown("### 💰 Budget Recommendations")
        
        budget = plan.get('budget_recommendations', {})
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Minimum Budget", budget.get('minimum', '$0'))
        with col2:
            st.metric("Recommended Budget", budget.get('recommended', '$0'))
        with col3:
            st.markdown("**Allocation:**")
            alloc = budget.get('allocation', {})
            for k, v in alloc.items():
                st.markdown(f"- {k}: {v}")
        
        st.markdown("---")
        
        # Success Metrics
        st.markdown("### 📊 Success Metrics")
        
        metrics = plan.get('success_metrics', {})
        cols = st.columns(3)
        
        with cols[0]:
            st.markdown("**Week 1**")
            for m in metrics.get('week_1', []):
                st.markdown(f"- {m}")
        
        with cols[1]:
            st.markdown("**Month 1**")
            for m in metrics.get('month_1', []):
                st.markdown(f"- {m}")
        
        with cols[2]:
            st.markdown("**Month 3**")
            for m in metrics.get('month_3', []):
                st.markdown(f"- {m}")
        
        st.markdown("---")
        
        # Risks
        st.markdown("### ⚠️ Risks & Mitigations")
        
        risks = plan.get('risks_and_mitigations', [])
        for risk in risks:
            with st.container():
                st.warning(f"**Risk:** {risk.get('risk', '')}")
                st.info(f"**Mitigation:** {risk.get('mitigation', '')}")
        
        st.markdown("---")
        
        # Weekly Checklist
        st.markdown("### ✅ 12-Week Checklist")
        
        checklist = plan.get('weekly_checklist', [])
        cols = st.columns(3)
        for i, task in enumerate(checklist):
            with cols[i % 3]:
                st.checkbox(f"Week {i+1}: {task}", key=f"week_{i}")
        
        st.markdown("---")
        
        # Save/Export options
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Generate New Plan", use_container_width=True):
                st.session_state.generated_plan = None
                st.session_state.plan_id = None
                st.rerun()
        
        with col2:
            # Export as JSON
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

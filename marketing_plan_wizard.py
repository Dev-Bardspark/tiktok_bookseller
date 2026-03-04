# marketing_plan_wizard.py
import streamlit as st
import json
import openai
from openai import OpenAI
from datetime import datetime

client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

def show_marketing_plan_wizard():
    st.title("📋 Marketing Plan Generator")
    
    # Initialize
    if 'plan_result' not in st.session_state:
        st.session_state.plan_result = None
    
    # =========================================
    # PULL EXISTING DATA
    # =========================================
    
    # From Book Analyzer
    book_data = st.session_state.get('analysis_result', {})
    has_book = bool(book_data)
    
    # From Author Persona
    persona_data = st.session_state.get('persona_results', {})
    has_persona = bool(persona_data)
    
    # From Marketing Assets
    assets_data = st.session_state.get('marketing_assets', {})
    has_assets = bool(assets_data)
    
    # =========================================
    # SHOW WHAT WE FOUND
    # =========================================
    
    st.markdown("### 📊 Found in Your Account:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if has_book:
            st.success(f"✅ Book: {book_data.get('title', 'Your Book')}")
        else:
            st.warning("⚠️ No book analysis yet")
    
    with col2:
        if has_persona:
            st.success(f"✅ Persona: {persona_data.get('persona', {}).get('archetype', 'Found')}")
        else:
            st.warning("⚠️ No author persona yet")
    
    with col3:
        if has_assets:
            st.success(f"✅ Assets: {len(assets_data.get('generated', []))} items")
        else:
            st.warning("⚠️ No marketing assets yet")
    
    st.markdown("---")
    
    # =========================================
    # ASK ONLY WHAT'S MISSING
    # =========================================
    
    missing_info = {}
    
    with st.form("plan_form"):
        
        # Ask for book info if missing
        if not has_book:
            st.markdown("### 📖 Tell us about your book")
            title = st.text_input("Book title*")
            genre = st.selectbox("Genre*", ["Romance", "Fantasy", "Thriller", "Mystery", "Sci-Fi", "YA", "Other"])
            blurb = st.text_area("Brief description*", height=100)
            missing_info['title'] = title
            missing_info['genre'] = genre
            missing_info['blurb'] = blurb
        
        # Ask for persona if missing
        if not has_persona:
            st.markdown("### 🧠 Your author voice")
            voice = st.selectbox("How would you describe your writing voice?",
                ["Witty and conversational", "Professional and authoritative", 
                 "Warm and nurturing", "Edgy and bold", "Poetic and literary"])
            audience = st.text_input("Who is your ideal reader?")
            missing_info['voice'] = voice
            missing_info['audience'] = audience
        
        # Ask about assets if missing
        if not has_assets:
            st.markdown("### 🎨 What marketing content do you have?")
            col1, col2 = st.columns(2)
            with col1:
                has_social = st.checkbox("Social media posts")
                has_email = st.checkbox("Email copy")
            with col2:
                has_ads = st.checkbox("Ad copy")
                has_blog = st.checkbox("Blog content")
            missing_info['has_social'] = has_social
            missing_info['has_email'] = has_email
            missing_info['has_ads'] = has_ads
            missing_info['has_blog'] = has_blog
        
        st.markdown("---")
        
        # Generate button
        generate = st.form_submit_button("🚀 Generate My Marketing Plan", type="primary", use_container_width=True)
        
        if generate:
            with st.spinner("Creating your strategic plan..."):
                
                # Combine existing data with missing info
                full_data = {
                    'book': book_data if has_book else missing_info,
                    'persona': persona_data if has_persona else missing_info,
                    'assets': assets_data if has_assets else missing_info,
                    'has_book': has_book,
                    'has_persona': has_persona,
                    'has_assets': has_assets
                }
                
                # Generate plan with AI
                plan = generate_plan(full_data)
                st.session_state.plan_result = plan
                st.rerun()
    
    # =========================================
    # SHOW THE PLAN
    # =========================================
    
    if st.session_state.plan_result:
        st.markdown("---")
        st.markdown("## 🎯 Your Marketing Plan")
        st.markdown(st.session_state.plan_result)
        
        # Download button
        st.download_button(
            "📥 Download Plan",
            st.session_state.plan_result,
            f"marketing_plan_{datetime.now().strftime('%Y%m%d')}.md",
            "text/markdown"
        )

def generate_plan(data):
    """Call OpenAI to generate the plan"""
    
    prompt = f"""
    Create a book marketing plan based on this author's data.
    
    BOOK INFO: {json.dumps(data.get('book', {}))}
    AUTHOR PERSONA: {json.dumps(data.get('persona', {}))}
    EXISTING ASSETS: {json.dumps(data.get('assets', {}))}
    
    Provide a strategic plan with:
    1. Summary of current position
    2. Top 3 priorities (what to do next)
    3. Timeline (4-6 weeks)
    4. Which platforms to focus on
    5. What assets to create next (referencing the Marketing Assets Generator)
    6. ARC/influencer strategy
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a book marketing strategist. Create clear, actionable plans."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except:
        return "⚠️ Unable to generate plan. Please check your OpenAI API key."

# MarketingGenerator.py
import streamlit as st
from openai import OpenAI
import json
import time
from datetime import datetime

def show_generator():
    """Generate marketing assets from saved analysis"""
    
    if st.session_state.get('current_page') != "🎨 Marketing Assets":
        return
    
    # Initialize session state
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    
    if 'loaded_analysis' not in st.session_state:
        st.session_state.loaded_analysis = None
    
    if 'generated_assets' not in st.session_state:
        st.session_state.generated_assets = None
    
    if 'edited_assets' not in st.session_state:
        st.session_state.edited_assets = None
    
    # Header
    st.title("🎨 Marketing Asset Generator")
    st.markdown("Load a book analysis and generate multi-platform marketing assets")
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
    
    # Two-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📂 Load Analysis")
        
        # Option 1: Load from session library
        if 'analysis_library' in st.session_state and st.session_state.analysis_library:
            st.markdown("**From current session:**")
            book_titles = list(st.session_state.analysis_library.keys())
            selected = st.selectbox("Choose a book", book_titles)
            
            if st.button("📂 Load Selected", use_container_width=True):
                st.session_state.loaded_analysis = st.session_state.analysis_library[selected]
                st.session_state.generated_assets = None
                st.session_state.edited_assets = None
                st.rerun()
        
        # Option 2: Upload JSON file
        st.markdown("**Or upload JSON file:**")
        uploaded_file = st.file_uploader(
            "Upload analysis JSON",
            type=['json'],
            key="analysis_file"
        )
        
        if uploaded_file:
            try:
                loaded = json.load(uploaded_file)
                st.session_state.loaded_analysis = loaded
                st.session_state.generated_assets = None
                st.session_state.edited_assets = None
                st.success("✅ Analysis loaded!")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
    
    with col2:
        if st.session_state.loaded_analysis:
            st.markdown("### 📖 Loaded Book")
            book_info = st.session_state.loaded_analysis.get('book_info', {}).get('book_info', {})
            st.write(f"**Title:** {book_info.get('title', 'Unknown')}")
            st.write(f"**Genre:** {book_info.get('genre', 'Unknown')}")
            
            # Show preview of analysis
            with st.expander("Preview Analysis"):
                st.json(st.session_state.loaded_analysis)
    
    st.markdown("---")
    
    # Generate assets section
    if st.session_state.loaded_analysis:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🎬 GENERATE ALL ASSETS", type="primary", use_container_width=True):
                with st.spinner("Generating marketing assets... (30-45 seconds)"):
                    client = OpenAI(api_key=st.session_state.openai_api_key)
                    assets = generate_marketing_assets(client, st.session_state.loaded_analysis)
                    
                    if assets:
                        st.session_state.generated_assets = assets
                        st.session_state.edited_assets = assets.copy()
                        st.rerun()
        
        with col2:
            if st.session_state.generated_assets and st.button("🔄 Regenerate", use_container_width=True):
                st.session_state.generated_assets = None
                st.session_state.edited_assets = None
                st.rerun()
        
        with col3:
            if st.session_state.edited_assets:
                # Export edited assets
                export_data = json.dumps(st.session_state.edited_assets, indent=2)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"marketing_assets_{timestamp}.json"
                
                st.download_button(
                    "📥 Export Assets",
                    export_data,
                    filename,
                    "application/json",
                    use_container_width=True
                )
    
    # Display assets if generated
    if st.session_state.generated_assets and st.session_state.edited_assets:
        st.markdown("---")
        st.success("✅ Assets generated! Edit them below.")
        
        # Tabs for different platforms
        platform_tabs = st.tabs([
            "📝 Blurb", "🎬 TikTok", "📸 Instagram", "🛒 Amazon", 
            "📧 Email", "📢 Facebook", "📰 Press", "📌 Pinterest", "📚 Goodreads", "🎙️ Podcast"
        ])
        
        edited = st.session_state.edited_assets
        
        with platform_tabs[0]:
            st.markdown("### 📝 Book Blurb")
            edited['blurb'] = st.text_area("Edit your blurb", edited.get('blurb', ''), height=200)
        
        with platform_tabs[1]:
            st.markdown("### 🎬 TikTok Scripts")
            for i, script in enumerate(edited.get('tiktok_scripts', [])):
                with st.expander(f"Script {i+1}"):
                    if isinstance(script, dict):
                        for key, value in script.items():
                            if key == 'hashtags' and isinstance(value, list):
                                tag_string = ' '.join(value)
                                edited_tags = st.text_input(f"{key.title()}", tag_string, key=f"tiktok_{i}_{key}")
                                script[key] = edited_tags.split()
                            else:
                                script[key] = st.text_input(f"{key.title()}", str(value), key=f"tiktok_{i}_{key}")
        
        with platform_tabs[2]:
            st.markdown("### 📸 Instagram")
            insta = edited.get('instagram', {})
            if insta.get('posts'):
                for j, post in enumerate(insta['posts']):
                    with st.expander(f"Post {j+1}"):
                        if isinstance(post, dict):
                            for key, value in post.items():
                                if key == 'hashtags' and isinstance(value, list):
                                    tag_string = ' '.join(value)
                                    edited_tags = st.text_input(f"{key.title()}", tag_string, key=f"insta_post_{j}_{key}")
                                    post[key] = edited_tags.split()
                                else:
                                    post[key] = st.text_input(f"{key.title()}", str(value), key=f"insta_post_{j}_{key}")
        
        with platform_tabs[3]:
            st.markdown("### 🛒 Amazon")
            amazon = edited.get('amazon', {})
            if isinstance(amazon, dict):
                for key, value in amazon.items():
                    if key == 'search_terms' and isinstance(value, list):
                        term_string = ', '.join(value)
                        edited_terms = st.text_input(f"{key.replace('_', ' ').title()}", term_string, key=f"amazon_{key}")
                        amazon[key] = [t.strip() for t in edited_terms.split(',')]
                    elif key == 'categories' and isinstance(value, list):
                        cat_string = ', '.join(value)
                        edited_cats = st.text_input(f"{key.title()}", cat_string, key=f"amazon_{key}")
                        amazon[key] = [c.strip() for c in edited_cats.split(',')]
                    elif isinstance(value, dict):
                        st.json(value)
                    else:
                        amazon[key] = st.text_input(f"{key.replace('_', ' ').title()}", str(value), key=f"amazon_{key}")
        
        with platform_tabs[4]:
            st.markdown("### 📧 Email Sequence")
            emails = edited.get('email_sequence', {})
            for name, email in emails.items():
                with st.expander(f"📨 {name.title()}"):
                    if isinstance(email, dict):
                        for key, value in email.items():
                            email[key] = st.text_area(f"{key.title()}", str(value), height=100 if key == 'body' else 50, key=f"email_{name}_{key}")
        
        with platform_tabs[5]:
            st.markdown("### 📢 Facebook Ads")
            for i, ad in enumerate(edited.get('facebook_ads', [])):
                with st.expander(f"Ad {i+1}"):
                    if isinstance(ad, dict):
                        for key, value in ad.items():
                            ad[key] = st.text_input(f"{key.title()}", str(value), key=f"fb_ad_{i}_{key}")
        
        with platform_tabs[6]:
            st.markdown("### 📰 Press Kit")
            press = edited.get('press_kit', {})
            if isinstance(press, dict):
                for key, value in press.items():
                    if key == 'author_qanda' and isinstance(value, list):
                        for j, qa in enumerate(value):
                            with st.expander(f"Q&A {j+1}"):
                                if isinstance(qa, dict):
                                    qa['question'] = st.text_input("Question", qa.get('question', ''), key=f"press_qa_{j}_q")
                                    qa['answer'] = st.text_area("Answer", qa.get('answer', ''), height=80, key=f"press_qa_{j}_a")
                    elif key == 'key_talking_points' and isinstance(value, list):
                        point_string = '\n'.join(value)
                        edited_points = st.text_area("Key Talking Points", point_string, height=100, key=f"press_{key}")
                        press[key] = edited_points.split('\n')
                    else:
                        press[key] = st.text_area(f"{key.replace('_', ' ').title()}", str(value), height=100, key=f"press_{key}")
        
        with platform_tabs[7]:
            st.markdown("### 📌 Pinterest")
            pinterest = edited.get('pinterest', {})
            if isinstance(pinterest, dict):
                for key, value in pinterest.items():
                    if isinstance(value, list):
                        list_string = '\n'.join(value)
                        edited_list = st.text_area(f"{key.replace('_', ' ').title()}", list_string, height=80, key=f"pinterest_{key}")
                        pinterest[key] = edited_list.split('\n')
                    else:
                        pinterest[key] = st.text_input(f"{key.replace('_', ' ').title()}", str(value), key=f"pinterest_{key}")
        
        with platform_tabs[8]:
            st.markdown("### 📚 Goodreads")
            goodreads = edited.get('goodreads', {})
            if isinstance(goodreads, dict):
                for key, value in goodreads.items():
                    if isinstance(value, list):
                        list_string = '\n'.join(value)
                        edited_list = st.text_area(f"{key.replace('_', ' ').title()}", list_string, height=80, key=f"goodreads_{key}")
                        goodreads[key] = edited_list.split('\n')
                    else:
                        goodreads[key] = st.text_area(f"{key.replace('_', ' ').title()}", str(value), height=100, key=f"goodreads_{key}")
        
        with platform_tabs[9]:
            st.markdown("### 🎙️ Podcast Pitch")
            podcast = edited.get('podcast_pitch', {})
            if isinstance(podcast, dict):
                for key, value in podcast.items():
                    if isinstance(value, list):
                        list_string = '\n'.join(value)
                        edited_list = st.text_area(f"{key.replace('_', ' ').title()}", list_string, height=80, key=f"podcast_{key}")
                        podcast[key] = edited_list.split('\n')
                    else:
                        podcast[key] = st.text_area(f"{key.replace('_', ' ').title()}", str(value), height=100, key=f"podcast_{key}")
        
        st.success("✅ Edits saved in current session")
        
        # Copy to clipboard buttons (simulated)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📋 Copy Blurb"):
                st.info("Blurb copied to clipboard (simulated)")
        with col2:
            if st.button("📋 Copy All"):
                st.info("All assets copied (simulated)")
        with col3:
            if st.button("🔄 New Book"):
                st.session_state.loaded_analysis = None
                st.session_state.generated_assets = None
                st.session_state.edited_assets = None
                st.rerun()


def generate_marketing_assets(client, analysis_data):
    """Generate marketing assets from saved analysis"""
    
    # Extract the actual analysis
    book_analysis = analysis_data.get('book_info', {})
    cover_analysis = analysis_data.get('cover_analysis', {})
    
    prompt = f"""
    Based on this book analysis, create comprehensive marketing assets for ALL platforms.
    
    BOOK ANALYSIS:
    {json.dumps(book_analysis, indent=2)}
    
    COVER ANALYSIS:
    {json.dumps(cover_analysis, indent=2)}
    
    Return JSON with:
    
    1. blurb: "150-word compelling book description"
    
    2. tiktok_scripts: [
        {{
            "hook": "attention grabber",
            "visuals": "what to show",
            "voiceover": "full script",
            "music": "music suggestion",
            "cta": "call to action",
            "hashtags": ["#BookTok", "#relevant"]
        }}
    ]
    
    3. instagram: {{
        "posts": [
            {{
                "image_description": "what to post",
                "caption": "caption text",
                "hashtags": ["#tag1", "#tag2"]
            }}
        ],
        "reels": [
            {{
                "concept": "reel idea",
                "script": "content",
                "music": "trending audio"
            }}
        ],
        "stories": ["story idea 1", "story idea 2"]
    }}
    
    4. amazon: {{
        "a_plus_content": {{
            "title": "enhanced brand content title",
            "description": "enhanced description",
            "key_features": ["feature1", "feature2", "feature3"]
        }},
        "search_terms": ["keyword1", "keyword2", "keyword3"],
        "categories": ["suggested categories"],
        "author_bio": "compelling author bio for Amazon page"
    }}
    
    5. facebook_ads: [
        {{
            "audience": "target demographic",
            "headline": "ad headline",
            "primary_text": "main ad text",
            "description": "description",
            "cta": "call to action button"
        }}
    ]
    
    6. email_sequence: {{
        "welcome": {{
            "subject": "Welcome email subject",
            "body": "full email content"
        }},
        "prelaunch": {{
            "subject": "Pre-launch subject",
            "body": "email content"
        }},
        "launch": {{
            "subject": "Launch day subject",
            "body": "email content"
        }},
        "followup": {{
            "subject": "Follow-up subject",
            "body": "email with reviews"
        }}
    }}
    
    7. press_kit: {{
        "press_release": "full press release",
        "author_qanda": [
            {{"question": "question", "answer": "answer"}}
        ],
        "key_talking_points": ["point1", "point2"]
    }}
    
    8. pinterest: {{
        "pin_descriptions": ["pin1", "pin2"],
        "board_ideas": ["board1", "board2"],
        "keywords": ["pinterest keywords"]
    }}
    
    9. goodreads: {{
        "giveaway_description": "text for giveaway",
        "discussion_questions": ["q1", "q2"],
        "similar_books": ["book1", "book2"]
    }}
    
    10. podcast_pitch: {{
        "pitch_email": "email template",
        "talking_points": ["point1", "point2"],
        "podcast_ideas": ["episode angle1", "angle2"]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a marketing expert. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Asset generation failed: {str(e)}")
        return None


# For direct testing
if __name__ == "__main__":
    show_generator()

# author_persona_discovery.py - FIXED with AUTO-SAVE
import streamlit as st
import pandas as pd
import plotly.express as px
from enum import Enum
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Add database connection function
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

def auto_save_persona(user_id, author_type, persona_data):
    """AUTO-SAVE persona to database - NO BUTTON NEEDED"""
    if not user_id:
        return False
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        
        # First, mark existing personas as inactive (keep history but only one active)
        cur.execute("""
            UPDATE user_author_personas 
            SET is_active = FALSE 
            WHERE user_id = %s
        """, (user_id,))
        
        # Save new persona
        cur.execute("""
            INSERT INTO user_author_personas 
            (user_id, persona_name, persona_data, created_at, is_active)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            user_id,
            f"My {author_type} Persona",
            json.dumps(persona_data),
            datetime.now(),
            True
        ))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Auto-save failed: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

class AuthorType(Enum):
    SHADOW = "The Shadow"
    CURATED = "The Curated"
    BRIDGE = "The Bridge"
    OPEN_BOOK = "The Open Book"

class InteractionStyle(Enum):
    WRITTEN = "Written Word"
    AUDIO = "Audio/Narration"
    VISUAL = "Visual/Video"
    LIVE = "Live/In-Person"

class SocialBattery(Enum):
    LOW = "The Introvert"  # Needs recovery time
    MEDIUM = "The Ambivert"  # Flexible
    HIGH = "The Extrovert"  # Gains energy from people

class AuthorPersona:
    def __init__(self):
        self.visibility_score = 0
        self.interaction_style = None
        self.social_battery = None
        self.genre = None
        self.goals = []
        
    def calculate_visibility(self, answers):
        """Calculate visibility comfort level from quiz answers"""
        # Q1: Identity comfort (1-4 points)
        q1_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        
        # Q2: Camera comfort (1-4 points)
        q2_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        
        # Q3: Social setting preference (1-4 points)
        q3_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        
        total = q1_map[answers['q1']] + q2_map[answers['q2']] + q3_map[answers['q3']]
        self.visibility_score = total / 3  # Average score 1-4
        
        return self.visibility_score
    
    def get_author_type(self):
        """Determine author type based on visibility score"""
        if self.visibility_score <= 1.5:
            return AuthorType.SHADOW
        elif self.visibility_score <= 2.3:
            return AuthorType.CURATED
        elif self.visibility_score <= 3.2:
            return AuthorType.BRIDGE
        else:
            return AuthorType.OPEN_BOOK


def get_strengths(author_type, interaction_style):
    """Get strengths based on author type and interaction style"""
    strengths = {
        AuthorType.SHADOW: "Deep writing, authenticity, mystery, letting work speak for itself",
        AuthorType.CURATED: "Professional presentation, consistency, quality over quantity, planned engagement",
        AuthorType.BRIDGE: "Versatility, connection, adaptability, balancing multiple formats",
        AuthorType.OPEN_BOOK: "Relatability, trust, community building, authentic connection"
    }
    return strengths[author_type]


def calculate_energy_budget(social_battery):
    """Calculate recommended energy expenditure based on social battery"""
    budgets = {
        SocialBattery.LOW: {
            "daily": "15-20 minutes",
            "weekly": "2-3 pieces of content",
            "tip": "Batch create on weekends, schedule during week. Quality over quantity."
        },
        SocialBattery.MEDIUM: {
            "daily": "30-45 minutes",
            "weekly": "5-7 pieces of content",
            "tip": "Mix scheduled and real-time engagement. Find your sustainable rhythm."
        },
        SocialBattery.HIGH: {
            "daily": "1-2 hours",
            "weekly": "10+ pieces of content",
            "tip": "Go live, engage daily, build community. Your energy is your superpower."
        }
    }
    return budgets[social_battery]


def calculate_platform_scores(author_type, interaction_style, genre):
    """Score platforms 0-100 based on fit for author persona"""
    
    # Base scores by author type
    type_scores = {
        AuthorType.SHADOW: {
            "Newsletter": 95,
            "Medium/Substack": 95,
            "Twitter/X": 85,
            "Blog": 90,
            "Podcast (as guest)": 70,
            "Goodreads": 80,
            "Instagram": 40,
            "TikTok": 20,
            "YouTube": 30,
            "LinkedIn": 60,
            "Facebook": 50
        },
        AuthorType.CURATED: {
            "Instagram": 90,
            "LinkedIn": 85,
            "YouTube": 80,
            "Newsletter": 85,
            "Twitter/X": 75,
            "Podcast": 70,
            "Blog": 75,
            "TikTok": 60,
            "Facebook": 65,
            "Goodreads": 70,
            "Medium/Substack": 70
        },
        AuthorType.BRIDGE: {
            "Instagram": 90,
            "Twitter/X": 85,
            "Newsletter": 85,
            "Podcast": 80,
            "TikTok": 75,
            "YouTube": 75,
            "LinkedIn": 70,
            "Facebook": 70,
            "Medium/Substack": 65,
            "Blog": 65,
            "Goodreads": 60
        },
        AuthorType.OPEN_BOOK: {
            "TikTok": 95,
            "Instagram Live": 95,
            "YouTube": 90,
            "Podcast": 85,
            "Twitter/X": 80,
            "Facebook": 80,
            "Newsletter": 75,
            "LinkedIn": 70,
            "Medium/Substack": 50,
            "Blog": 50,
            "Goodreads": 60
        }
    }
    
    # Adjust for interaction style
    style_boost = {
        InteractionStyle.WRITTEN: {"Newsletter": 10, "Medium/Substack": 10, "Blog": 10, "Twitter/X": 5},
        InteractionStyle.AUDIO: {"Podcast": 15, "Clubhouse": 15, "Twitter Spaces": 10},
        InteractionStyle.VISUAL: {"TikTok": 10, "Instagram": 10, "YouTube": 10, "Pinterest": 10},
        InteractionStyle.LIVE: {"Instagram Live": 15, "TikTok Live": 15, "Facebook Live": 10, "Events": 20}
    }
    
    # Genre adjustments
    genre_boosts = {
        "Genre Fiction (Mystery/Romance/Sci-Fi/Fantasy)": {"TikTok": 10, "Instagram": 10, "Pinterest": 5},
        "Non-fiction (Self-help/Business/Memoir)": {"LinkedIn": 15, "Newsletter": 10, "YouTube": 10},
        "Poetry": {"Instagram": 15, "TikTok": 10, "Pinterest": 10},
        "Children's Books": {"Instagram": 10, "Pinterest": 15, "Facebook": 10},
        "Academic/Technical": {"LinkedIn": 15, "Twitter/X": 10, "Medium/Substack": 15}
    }
    
    # Get base scores
    platform_scores = type_scores[author_type].copy()
    
    # Apply style boost
    for platform, boost in style_boost[interaction_style].items():
        if platform in platform_scores:
            platform_scores[platform] = min(100, platform_scores[platform] + boost)
    
    # Apply genre boost
    if genre in genre_boosts:
        for platform, boost in genre_boosts[genre].items():
            if platform in platform_scores:
                platform_scores[platform] = min(100, platform_scores[platform] + boost)
    
    # Convert to list of dicts and sort
    platform_list = [{"name": k, "score": v, "reason": get_platform_reason(k, author_type)} 
                     for k, v in platform_scores.items()]
    platform_list.sort(key=lambda x: x["score"], reverse=True)
    
    return platform_list[:8]  # Return top 8


def get_platform_reason(platform, author_type):
    """Get reason why platform is recommended"""
    reasons = {
        "Newsletter": "Your words, your rules. No algorithms, direct connection.",
        "Medium/Substack": "Perfect for long-form writing that stands on its own.",
        "Twitter/X": "Quick hits, conversation, low visibility required.",
        "Blog": "Own your platform, build depth over time.",
        "Instagram": "Visual storytelling with controlled presentation.",
        "TikTok": "High reach, authentic content, viral potential.",
        "YouTube": "Depth through video, evergreen content.",
        "LinkedIn": "Professional credibility, non-fiction goldmine.",
        "Facebook": "Community groups, targeted demographics.",
        "Goodreads": "Connect with dedicated readers, build trust.",
        "Podcast": "Intimate connection, growing medium.",
        "Pinterest": "Evergreen traffic, visual discovery."
    }
    return reasons.get(platform, "Strong fit for your persona.")


def get_quick_win(author_type, interaction_style, genre):
    """Get immediate actionable step"""
    
    wins = {
        (AuthorType.SHADOW, InteractionStyle.WRITTEN): "Write a thread about your book's central theme. Post it on X/Twitter. No face required.",
        (AuthorType.SHADOW, InteractionStyle.AUDIO): "Record a 5-minute voice note about your writing process. Share with your email list.",
        (AuthorType.SHADOW, InteractionStyle.VISUAL): "Create 3 aesthetic quote cards using Canva. Schedule them on Pinterest.",
        
        (AuthorType.CURATED, InteractionStyle.WRITTEN): "Draft a professional newsletter introducing yourself and your book.",
        (AuthorType.CURATED, InteractionStyle.VISUAL): "Create a cohesive Instagram grid with 3 posts that establish your visual brand.",
        (AuthorType.CURATED, InteractionStyle.AUDIO): "Prepare 5 talking points and pitch yourself to 3 relevant podcasts.",
        
        (AuthorType.BRIDGE, InteractionStyle.WRITTEN): "Write a personal essay about why you wrote this book. Share everywhere.",
        (AuthorType.BRIDGE, InteractionStyle.VISUAL): "Film a 'day in the life' writing vlog. Show the person behind the pages.",
        (AuthorType.BRIDGE, InteractionStyle.AUDIO): "Start a casual conversation on Twitter Spaces about your genre.",
        
        (AuthorType.OPEN_BOOK, InteractionStyle.LIVE): "Go live for 10 minutes just to introduce yourself and your book.",
        (AuthorType.OPEN_BOOK, InteractionStyle.VISUAL): "Create a TikTok duet with a reader's video about your genre.",
        (AuthorType.OPEN_BOOK, InteractionStyle.WRITTEN): "Share a vulnerable post about your writing journey on social media."
    }
    
    # Try exact match
    win = wins.get((author_type, interaction_style))
    
    # Fallback by author type
    if not win:
        fallbacks = {
            AuthorType.SHADOW: "Write one piece of long-form content this week. Publish it on your blog or Medium.",
            AuthorType.CURATED: "Create and schedule 3 pieces of content across one platform this week.",
            AuthorType.BRIDGE: "Engage with 5 authors in your genre on social media. Leave meaningful comments.",
            AuthorType.OPEN_BOOK: "Post a behind-the-scenes look at your writing space or process."
        }
        win = fallbacks[author_type]
    
    return win


def render_quiz():
    """Main function to render the Streamlit quiz interface"""
    
    # Initialize session state for quiz progress
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False
    if 'quiz_complete' not in st.session_state:
        st.session_state.quiz_complete = False
    if 'answers' not in st.session_state:
        st.session_state.answers = {}
    if '_persona_auto_saved' not in st.session_state:
        st.session_state._persona_auto_saved = False
    
    # Sidebar with progress
    with st.sidebar:
        st.markdown("### 📚 Author Persona Discovery")
        st.markdown("---")
        st.markdown("**✨ AUTO-SAVE ENABLED**")
        st.markdown("Results save automatically to your account")
        st.markdown("---")
        
        if not st.session_state.get('quiz_started', False):
            st.info("✨ Ready to discover your author type?")
        elif st.session_state.get('quiz_complete', False):
            st.success("✅ Quiz Complete!")
            st.progress(1.0)
            st.balloons()
        else:
            st.warning("📝 Quiz in progress...")
            st.progress(0.5)
    
    # Main content
    if not st.session_state.quiz_started:
        # Landing page
        st.title("📚 Discover Your Author Persona")
        st.markdown("### Find the marketing approach that fits *you*—not the other way around")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **You're a writer, not a marketer.**  
            But here's the truth: readers can't love what they can't find.
            
            The problem? Most marketing advice assumes you're an extrovert who loves being on camera.
            
            **This quiz is different.** It helps you discover:
            - Your natural author type
            - Platforms that match your comfort level
            - A sustainable marketing approach
            - Quick wins that don't drain you
            """)
            
            if st.button("✨ Start the Quiz →", type="primary", use_container_width=True):
                st.session_state.quiz_started = True
                st.rerun()
        
        with col2:
            st.markdown("""
            ### The Four Author Types
            
            | Type | Style |
            |------|-------|
            | 🖤 **The Shadow** | Let the work speak |
            | 💎 **The Curated** | Polished & professional |
            | 🌉 **The Bridge** | Blend of worlds |
            | 📖 **The Open Book** | Authentic & visible |
            
            Find out which one you are in 5 minutes.
            """)
    
    elif not st.session_state.quiz_complete:
        # Quiz interface
        st.title("📝 Author Persona Quiz")
        st.markdown("### Answer these 7 questions to discover your type")
        
        with st.form("quiz_form"):
            st.markdown("#### Section 1: Public Visibility Comfort")
            
            q1 = st.radio(
                "**Q1: If you imagined your author brand having a face, you'd feel most comfortable with:**",
                options=[
                    "A) Complete anonymity—let the work speak for itself (like Banksy)",
                    "B) A curated public persona with professional photos and limited personal sharing",
                    "C) A mix—some personal elements, but boundaries maintained",
                    "D) Full transparency—readers feel like they know you personally"
                ],
                index=None,
                key="q1"
            )
            
            q2 = st.radio(
                "**Q2: When you think about book promotion, the idea of being on camera makes you feel:**",
                options=[
                    "A) Terrified—I'd rather do anything else",
                    "B) Nervous but willing to try with preparation",
                    "C) Comfortable in controlled settings (pre-recorded, edited)",
                    "D) Excited—I love connecting visually with people"
                ],
                index=None,
                key="q2"
            )
            
            q3 = st.radio(
                "**Q3: At a party, you're most likely to be found:**",
                options=[
                    "A) In a quiet corner talking to one person deeply",
                    "B) Circulating, but needing breaks",
                    "C) In the middle of a great conversation",
                    "D) Working the room, meeting everyone"
                ],
                index=None,
                key="q3"
            )
            
            st.markdown("---")
            st.markdown("#### Section 2: Preferred Interaction Style")
            
            q4 = st.radio(
                "**Q4: The way you express yourself best is through:**",
                options=[
                    "A) The written word—emails, essays, social media posts",
                    "B) Audio—podcasts, voice notes, audio recordings",
                    "C) Visual—video, photography, visual storytelling",
                    "D) Live interaction—events, workshops, conversations"
                ],
                index=None,
                key="q4"
            )
            
            q5 = st.select_slider(
                "**Q5: Your social battery after 2 hours of engaging with readers:**",
                options=[
                    "Completely drained (need alone time)",
                    "Moderately tired (can do more but need break)",
                    "Balanced (could go either way)",
                    "Energized (ready for more!)",
                    "Fully charged (this fuels me)"
                ],
                value=None,
                key="q5"
            )
            
            st.markdown("---")
            st.markdown("#### Section 3: Your Writing Context")
            
            col1, col2 = st.columns(2)
            
            with col1:
                q6 = st.selectbox(
                    "**Q6: What genre do you primarily write in?**",
                    options=[
                        "Fiction (Literary/Contemporary)",
                        "Genre Fiction (Mystery/Romance/Sci-Fi/Fantasy)",
                        "Non-fiction (Self-help/Business/Memoir)",
                        "Academic/Technical",
                        "Poetry",
                        "Children's Books",
                        "Multiple genres",
                        "Other"
                    ],
                    index=None,
                    key="q6"
                )
            
            with col2:
                q7 = st.multiselect(
                    "**Q7: What are your primary author goals?** (Select all that apply)",
                    options=[
                        "Build reader community",
                        "Sell more books",
                        "Establish authority/expertise",
                        "Connect with other authors",
                        "Get speaking engagements",
                        "Land a book deal",
                        "Supplement income",
                        "Creative expression only"
                    ],
                    key="q7"
                )
            
            # Submit button
            submitted = st.form_submit_button("✨ See My Results →", type="primary", use_container_width=True)
            
            if submitted:
                # Validate required fields
                required_fields = [q1, q2, q3, q4, q5, q6, q7]
                if None in required_fields[:-1] or not q7:  # Check all except q7 which is multiselect
                    st.error("Please answer all questions before viewing results.")
                else:
                    # Store answers
                    st.session_state.answers = {
                        'q1': q1[0],  # Get the letter option
                        'q2': q2[0],
                        'q3': q3[0],
                        'q4': q4[0],
                        'q5': q5,
                        'q6': q6,
                        'q7': q7
                    }
                    st.session_state.quiz_complete = True
                    st.rerun()
    
    else:
        render_results()


def render_results():
    """Display quiz results with author type and recommendations - AUTO-SAVE VERSION"""
    
    # Create persona and calculate results
    persona = AuthorPersona()
    visibility_score = persona.calculate_visibility(st.session_state.answers)
    author_type = persona.get_author_type()
    
    # Determine interaction style from Q4
    q4_map = {
        'A': InteractionStyle.WRITTEN,
        'B': InteractionStyle.AUDIO,
        'C': InteractionStyle.VISUAL,
        'D': InteractionStyle.LIVE
    }
    interaction_style = q4_map[st.session_state.answers['q4']]
    
    # Determine social battery from Q5
    q5_map = {
        "Completely drained (need alone time)": SocialBattery.LOW,
        "Moderately tired (can do more but need break)": SocialBattery.LOW,
        "Balanced (could go either way)": SocialBattery.MEDIUM,
        "Energized (ready for more!)": SocialBattery.MEDIUM,
        "Fully charged (this fuels me)": SocialBattery.HIGH
    }
    social_battery = q5_map[st.session_state.answers['q5']]
    
    # Type-specific styling
    type_colors = {
        AuthorType.SHADOW: "🖤",
        AuthorType.CURATED: "💎",
        AuthorType.BRIDGE: "🌉",
        AuthorType.OPEN_BOOK: "📖"
    }
    
    # Results header
    st.title("✨ Your Author Persona Results")
    
    # AUTO-SAVE when results are shown (NO BUTTON NEEDED)
    if st.session_state.get('authenticated', False) and not st.session_state.get('_persona_auto_saved', False):
        quick_win = get_quick_win(author_type, interaction_style, st.session_state.answers['q6'])
        budget = calculate_energy_budget(social_battery)
        platform_scores = calculate_platform_scores(author_type, interaction_style, st.session_state.answers['q6'])
        
        # Prepare data for saving
        persona_data = {
            "author_type": author_type.value,
            "visibility_score": visibility_score,
            "interaction_style": interaction_style.value,
            "social_battery": social_battery.value,
            "quick_win": quick_win,
            "energy_budget": budget,
            "answers": st.session_state.answers,
            "platform_scores": platform_scores
        }
        
        # Auto-save to database
        if auto_save_persona(st.session_state.get('user_id', 1), author_type.value, persona_data):
            st.session_state._persona_auto_saved = True
            st.toast("💾 Persona auto-saved to your account!", icon="✅")
    
    # Hero section
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; color: white;">
            <h1 style="font-size: 4rem; margin: 0;">{type_colors[author_type]}</h1>
            <h2 style="margin: 0.5rem 0;">{author_type.value}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Your Profile at a Glance")
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        metrics_col1.metric("Visibility Score", f"{visibility_score:.1f}/4.0")
        metrics_col2.metric("Interaction Style", interaction_style.value)
        metrics_col3.metric("Social Battery", social_battery.value)
        
        # Quick win
        quick_win = get_quick_win(author_type, interaction_style, st.session_state.answers['q6'])
        st.success(f"⚡ **Your Quick Win:** {quick_win}")
    
    st.markdown("---")
    st.caption("✨ Auto-saved to your account - no save button needed")
    st.markdown("---")
    
    # Three-tab layout
    tab1, tab2, tab3 = st.tabs(["🎯 Your Strategy", "📱 Platform Picks", "⚡ 7-Day Action Plan"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💪 Your Natural Strengths")
            st.markdown(get_strengths(author_type, interaction_style))
            
            st.markdown("### 🎯 Your Goals")
            for goal in st.session_state.answers['q7']:
                st.markdown(f"- {goal}")
        
        with col2:
            st.markdown("### 🧭 Recommended Path")
            
            recommendations = {
                AuthorType.SHADOW: """
                **Focus on:** Written content, newsletters, blog posts  
                **Start with:** Medium, Substack, or anonymous Twitter  
                **Avoid:** Live video, in-person events initially  
                **Growth strategy:** Let your writing be your voice
                """,
                
                AuthorType.CURATED: """
                **Focus on:** Professional branding, scheduled content, edited videos  
                **Start with:** LinkedIn, YouTube (edited), professional website  
                **Avoid:** Impromptu live streams, unplanned appearances  
                **Growth strategy:** Quality over quantity, planned engagement
                """,
                
                AuthorType.BRIDGE: """
                **Focus on:** Mix of content types, podcast appearances, interviews  
                **Start with:** Instagram, Twitter, occasional live events  
                **Avoid:** Overcommitting to one format  
                **Growth strategy:** Leverage both written and visual content
                """,
                
                AuthorType.OPEN_BOOK: """
                **Focus on:** Live videos, events, community building  
                **Start with:** TikTok, Instagram Live, Clubhouse, speaking events  
                **Avoid:** Hiding behind curated content  
                **Growth strategy:** Your personality is your brand—lean into it
                """
            }
            
            st.markdown(recommendations[author_type])
            
            st.markdown("### 🔋 Your Energy Budget")
            budget = calculate_energy_budget(social_battery)
            st.markdown(f"**Daily:** {budget['daily']}")
            st.markdown(f"**Weekly:** {budget['weekly']}")
            st.info(f"💡 {budget['tip']}")
    
    with tab2:
        st.markdown("### Top Platforms for You")
        st.markdown("These platforms match your comfort level and natural style:")
        
        platform_scores = calculate_platform_scores(author_type, interaction_style, st.session_state.answers['q6'])
        
        for i, platform in enumerate(platform_scores, 1):
            # Color based on score
            if platform['score'] >= 85:
                color = "#00C851"  # Green
                emoji = "🔥"
            elif platform['score'] >= 70:
                color = "#ffbb33"  # Yellow
                emoji = "👍"
            else:
                color = "#33b5e5"  # Blue
                emoji = "👌"
            
            st.markdown(f"""
            <div style="padding: 1rem; margin: 0.5rem 0; background: #f8f9fa; border-radius: 10px; border-left: 5px solid {color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span><strong>{i}. {platform['name']}</strong> {emoji}</span>
                    <span style="font-size: 1.2rem; font-weight: bold; color: {color};">{platform['score']}% match</span>
                </div>
                <small>{platform['reason']}</small>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📊 Platform Comparison")
        
        # Create DataFrame for visualization
        df = pd.DataFrame(platform_scores)
        fig = px.bar(df, x='name', y='score', title="Platform Match Score",
                    labels={'name': 'Platform', 'score': 'Match Score %'},
                    color='score', color_continuous_scale='viridis')
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### Your Personalized 7-Day Launch Plan")
        st.markdown("Start here. No overwhelm. Just action.")
        
        days = [
            ("Day 1: Set Up Foundation", "Create your profile on your top platform. Write your bio. Add a link to your book."),
            ("Day 2: Create Your First Post", f"Based on your style, create your first piece of content. {quick_win}"),
            ("Day 3: Engage with Community", "Find 5 authors in your genre. Leave meaningful comments on their posts."),
            ("Day 4: Share Behind the Scenes", "Show your writing space, process, or a sneak peek of your work."),
            ("Day 5: Ask a Question", "Engage your audience. Ask about their favorite books in your genre."),
            ("Day 6: Share a Resource", "Recommend a book, tool, or tip that helped your writing."),
            ("Day 7: Reflect & Plan", "Look at what worked. Plan next week's content. Celebrate starting!")
        ]
        
        for i, (day, description) in enumerate(days, 1):
            with st.expander(f"**{day}**", expanded=i==1):
                st.markdown(description)
                if i < 7:
                    st.progress(i/7)
                else:
                    st.progress(1.0)
                    st.balloons()
        
        st.markdown("---")
        st.markdown("### 📥 Download Your Results")
        
        # Create summary text
        summary = f"""
AUTHOR PERSONA RESULTS
======================
Type: {author_type.value}
Visibility Score: {visibility_score:.1f}/4.0
Interaction Style: {interaction_style.value}
Social Battery: {social_battery.value}

YOUR TOP PLATFORMS
=================
"""
        for p in platform_scores[:3]:
            summary += f"{p['name']}: {p['score']}% match\n"
        
        summary += f"""
        
YOUR QUICK WIN
=============
{quick_win}

ENERGY BUDGET
============
Daily: {budget['daily']}
Weekly: {budget['weekly']}
Tip: {budget['tip']}
        """
        
        st.download_button(
            label="📥 Download Summary",
            data=summary,
            file_name=f"author_persona_{author_type.value.replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    # Reset option
    st.markdown("---")
    if st.button("← Take Quiz Again", use_container_width=True):
        for key in ['quiz_started', 'quiz_complete', 'answers', '_persona_auto_saved']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


if __name__ == "__main__":
    render_quiz()

# author_persona_discovery.py
import streamlit as st
import pandas as pd
from enum import Enum

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

def render_quiz():
    """Main function to render the Streamlit quiz interface"""
    
    st.title("📝 Author Persona Discovery Quiz")
    st.markdown("### Find your author type in 5 minutes")
    st.caption("This quiz will help identify your natural author persona and ideal platform strategy.")
    
    # Initialize session state for quiz progress
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False
    if 'quiz_complete' not in st.session_state:
        st.session_state.quiz_complete = False
    if 'answers' not in st.session_state:
        st.session_state.answers = {}
    
    # Start quiz button
    if not st.session_state.quiz_started:
        if st.button("Start Quiz →", type="primary"):
            st.session_state.quiz_started = True
            st.rerun()
    
    # Quiz interface
    if st.session_state.quiz_started and not st.session_state.quiz_complete:
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
            submitted = st.form_submit_button("See My Results →", type="primary")
            
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

def render_results():
    """Display quiz results with author type and recommendations"""
    
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
    
    # Display results in a beautiful layout
    st.balloons()
    st.title("✨ Your Author Persona Results")
    
    # Author Type Badge
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        # Type-specific styling
        type_colors = {
            AuthorType.SHADOW: "🖤",
            AuthorType.CURATED: "💎",
            AuthorType.BRIDGE: "🌉",
            AuthorType.OPEN_BOOK: "📖"
        }
        
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; color: white;">
            <h1 style="font-size: 4rem; margin: 0;">{type_colors[author_type]}</h1>
            <h2 style="margin: 0.5rem 0;">{author_type.value}</h2>
            <p style="opacity: 0.9;">Visibility Score: {visibility_score:.1f}/4.0</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detailed breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Your Profile")
        st.markdown(f"**Interaction Style:** {interaction_style.value}")
        st.markdown(f"**Social Battery:** {social_battery.value}")
        st.markdown(f"**Genre:** {st.session_state.answers['q6']}")
        
        st.markdown("**Your Goals:**")
        for goal in st.session_state.answers['q7']:
            st.markdown(f"- {goal}")
    
    with col2:
        st.markdown("### 🎯 Recommended Path")
        
        # Personalized recommendations based on author type
        recommendations = {
            AuthorType.SHADOW: """
            - **Focus on:** Written content, newsletters, blog posts
            - **Platform:** Start with Medium, Substack, or anonymous Twitter
            - **Avoid:** Live video, in-person events initially
            - **Growth strategy:** Let your writing be your voice
            """,
            
            AuthorType.CURATED: """
            - **Focus on:** Professional branding, scheduled content, edited videos
            - **Platform:** LinkedIn, YouTube (edited), professional website
            - **Avoid:** Impromptu live streams, unplanned appearances
            - **Growth strategy:** Quality over quantity, planned engagement
            """,
            
            AuthorType.BRIDGE: """
            - **Focus on:** Mix of content types, podcast appearances, interviews
            - **Platform:** Instagram, Twitter, occasional live events
            - **Avoid:** Overcommitting to one format
            - **Growth strategy:** Leverage both written and visual content
            """,
            
            AuthorType.OPEN_BOOK: """
            - **Focus on:** Live videos, events, community building
            - **Platform:** TikTok, Instagram Live, Clubhouse, speaking events
            - **Avoid:** Hiding behind curated content
            - **Growth strategy:** Your personality is your brand—lean into it
            """
        }
        
        st.markdown(recommendations[author_type])
        
        # Interaction style tips
        st.markdown("**💡 Quick Tip:**")
        style_tips = {
            InteractionStyle.WRITTEN: "Start a newsletter—it's your superpower.",
            InteractionStyle.AUDIO: "Launch a podcast or seek guest spots.",
            InteractionStyle.VISUAL: "YouTube and TikTok are your playground.",
            InteractionStyle.LIVE: "Seek speaking opportunities and live events."
        }
        st.info(style_tips[interaction_style])
    
    # Next steps
    st.markdown("---")
    st.markdown("### 🚀 Your Personalized Action Plan")
    
    if st.button("Generate Detailed Strategy →", type="primary"):
        st.session_state.show_strategy = True
    
    if st.session_state.get('show_strategy', False):
        with st.expander("Your 30-Day Platform Launch Plan", expanded=True):
            st.markdown(f"""
            **Week 1-2: Foundation**
            - Set up your primary platform ({'Substack/Medium' if interaction_style == InteractionStyle.WRITTEN else 'YouTube/TikTok' if interaction_style == InteractionStyle.VISUAL else 'Podcast setup' if interaction_style == InteractionStyle.AUDIO else 'Event booking'})
            - Create your bio and consistent branding
            - Prepare 5 pieces of content
            
            **Week 3-4: Engagement**
            - Begin posting consistently
            - Engage with 5 other authors daily
            - Schedule your first {'newsletter' if interaction_style == InteractionStyle.WRITTEN else 'video' if interaction_style == InteractionStyle.VISUAL else 'podcast episode' if interaction_style == InteractionStyle.AUDIO else 'small event'}
            """)
    
    # Reset option
    if st.button("Take Quiz Again"):
        for key in ['quiz_started', 'quiz_complete', 'answers', 'show_strategy']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

def main():
    """Main app controller"""
    st.set_page_config(
        page_title="Author Persona Discovery",
        page_icon="📚",
        layout="wide"
    )
    
    # Sidebar with progress
    with st.sidebar:
        st.image("https://via.placeholder.com/150x150.png?text=📚", width=150)
        st.markdown("### Your Journey")
        
        if not st.session_state.get('quiz_started', False):
            st.info("Ready to begin? Take the 5-minute quiz to discover your author type!")
        elif st.session_state.get('quiz_complete', False):
            st.success("✅ Quiz Complete!")
            st.progress(1.0)
        else:
            st.warning("Quiz in progress...")
            st.progress(0.5)
    
    # Route to appropriate view
    if not st.session_state.get('quiz_complete', False):
        render_quiz()
    else:
        render_results()

if __name__ == "__main__":
    main()

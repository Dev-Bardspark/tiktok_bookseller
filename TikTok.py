# booktok_machine_poc.py
# Combines author persona quiz + ARC reader database

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from enum import Enum

# ============================================================================
# CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="BookTok Machine - POC",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# AUTHOR PERSONA ENUMS (from your existing code)
# ============================================================================

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
    LOW = "The Introvert"
    MEDIUM = "The Ambivert"
    HIGH = "The Extrovert"

# ============================================================================
# AUTHOR PERSONA CLASS (from your existing code)
# ============================================================================

class AuthorPersona:
    def __init__(self):
        self.visibility_score = 0
        self.interaction_style = None
        self.social_battery = None
        self.genre = None
        self.goals = []
        
    def calculate_visibility(self, answers):
        q1_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        q2_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        q3_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        
        total = q1_map[answers['q1']] + q2_map[answers['q2']] + q3_map[answers['q3']]
        self.visibility_score = total / 3
        return self.visibility_score
    
    def get_author_type(self):
        if self.visibility_score <= 1.5:
            return AuthorType.SHADOW
        elif self.visibility_score <= 2.3:
            return AuthorType.CURATED
        elif self.visibility_score <= 3.2:
            return AuthorType.BRIDGE
        else:
            return AuthorType.OPEN_BOOK

# ============================================================================
# ARC READER DATABASE LOADER
# ============================================================================

@st.cache_data
def load_arc_readers(json_path="arc_readers.json"):
    """Load and parse the ARC reader JSON from Apify"""
    
    # If you have the JSON file, load it
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Extract relevant fields from each video/creator
        readers = []
        for item in data:
            author = item.get('authorMeta', {})
            stats = item.get('videoMeta', {})
            
            # Extract email from bio if present
            bio = author.get('signature', '')
            import re
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            emails = re.findall(email_pattern, bio)
            email = emails[0] if emails else None
            
            # Extract genres from hashtags
            hashtags = [h.get('name', '') for h in item.get('hashtags', []) if h.get('name')]
            
            # Create reader record
            reader = {
                'username': author.get('name', ''),
                'display_name': author.get('nickName', ''),
                'bio': bio,
                'followers': author.get('fans', 0),
                'following': author.get('following', 0),
                'videos': author.get('video', 0),
                'hearts': author.get('heart', 0),
                'email': email,
                'hashtags': hashtags,
                'engagement': {
                    'avg_likes': item.get('diggCount', 0),
                    'avg_comments': item.get('commentCount', 0),
                    'avg_shares': item.get('shareCount', 0),
                    'views': item.get('playCount', 0)
                },
                'profile_url': author.get('profileUrl', ''),
                'discovered_date': datetime.now().isoformat()
            }
            readers.append(reader)
        
        # Remove duplicates by username
        unique_readers = {}
        for r in readers:
            if r['username'] and r['username'] not in unique_readers:
                unique_readers[r['username']] = r
        
        return list(unique_readers.values())
    
    # If no file, return sample data
    return get_sample_arc_readers()

def get_sample_arc_readers():
    """Sample ARC readers for demo when no JSON file exists"""
    return [
        {
            'username': 'megangad',
            'display_name': 'Megan Gad 📚',
            'bio': 'books, beauty, & bullsh!ttin',
            'followers': 41700,
            'email': None,
            'hashtags': ['arcreader', 'booktok'],
            'engagement': {'avg_likes': 64, 'avg_comments': 22},
            'profile_url': 'https://tiktok.com/@megangad'
        },
        {
            'username': 'beccafallbooks',
            'display_name': 'Becca Fall',
            'bio': 'romance author // everything reader',
            'followers': 221,
            'email': 'becca@example.com',
            'hashtags': ['arcreader', 'romancebooktok'],
            'engagement': {'avg_likes': 7, 'avg_comments': 7},
            'profile_url': 'https://tiktok.com/@beccafallbooks'
        },
        {
            'username': 'bookedbella',
            'display_name': 'Isabella | Booktok 📚',
            'bio': 'ARC Reader & Silent Book Club Host bookedbella93@gmail.com',
            'followers': 1972,
            'email': 'bookedbella93@gmail.com',
            'hashtags': ['arcreader', 'booktok'],
            'engagement': {'avg_likes': 29, 'avg_comments': 18},
            'profile_url': 'https://tiktok.com/@bookedbella'
        }
    ]

# ============================================================================
# INFLUENCER DISCOVERY (from your database)
# ============================================================================

@st.cache_data
def get_influencers_by_genre(genre, min_followers=1000):
    """Filter influencers by genre and follower count"""
    # This would query your central database
    # For POC, return sample data
    return [
        {
            'username': 'romancebookish_sarah',
            'followers': 24000,
            'engagement': 4.8,
            'genres': ['romance', 'romantasy'],
            'accepts_indies': True,
            'contact': 'DM',
            'rate': 'Free book'
        },
        {
            'username': 'darkromance_emma',
            'followers': 15000,
            'engagement': 5.2,
            'genres': ['dark romance', 'thriller'],
            'accepts_indies': True,
            'contact': 'emma@example.com',
            'rate': '$50-100'
        },
        {
            'username': 'fantasybooktok_aly',
            'followers': 42000,
            'engagement': 3.9,
            'genres': ['fantasy', 'romantasy'],
            'accepts_indies': True,
            'contact': 'DM',
            'rate': 'Free book + shoutout swap'
        }
    ]

# ============================================================================
# TRENDING SOUNDS DATABASE
# ============================================================================

@st.cache_data
def get_trending_sounds(genre=None):
    """Get trending sounds by genre"""
    sounds = {
        'romance': [
            {'name': 'Cruel Summer - Taylor Swift', 'uses': 45000, 'growth': '+12%'},
            {'name': 'Enchanted - Taylor Swift', 'uses': 28000, 'growth': '+8%'},
            {'name': 'I Can Do It With a Broken Heart', 'uses': 22000, 'growth': '+15%'}
        ],
        'romantasy': [
            {'name': 'Enchanted - Taylor Swift', 'uses': 32000, 'growth': '+10%'},
            {'name': 'I\'m Just a Girl - No Doubt', 'uses': 18000, 'growth': '+20%'},
            {'name': 'Unholy - Sam Smith', 'uses': 15000, 'growth': '+5%'}
        ],
        'thriller': [
            {'name': 'Murder on the Dancefloor', 'uses': 22000, 'growth': '+25%'},
            {'name': 'Creep - Radiohead', 'uses': 12000, 'growth': '+8%'},
            {'name': 'Running Up That Hill', 'uses': 10000, 'growth': '+3%'}
        ]
    }
    
    if genre and genre.lower() in sounds:
        return sounds[genre.lower()]
    return sounds.get('romance', [])

# ============================================================================
# VIDEO TEMPLATES
# ============================================================================

def get_video_templates(genre, author_type):
    """Get video templates tailored to genre and author comfort level"""
    
    templates = {
        'pointing_tropes': {
            'name': '🎯 Pointing at Tropes',
            'description': 'Point at different tropes your book includes',
            'script': f"""
            [Point at screen]
            Looking for [TROPE 1]? ✅
            [Point]
            [TROPE 2]? ✅
            [Point]
            [TROPE 3]? ✅
            [Point]
            Then you need [BOOK TITLE]!
            """,
            'visual': 'Pointing hand or finger overlay',
            'audio': 'Trending sound (any)',
            'difficulty': 'Easy'
        },
        'books_that_made_me': {
            'name': '😭 Books That Made Me Feel',
            'description': 'Show books that evoked strong emotions',
            'script': f"""
            Books that made me [EMOTION] at 2am:
            
            [Show book cover]
            [BOOK TITLE] - because [REASON]
            
            Drop your favorite below 👇
            """,
            'visual': 'Book covers, flipping pages',
            'audio': 'Emotional trending sound',
            'difficulty': 'Easy'
        },
        'if_you_loved': {
            'name': '📚 If You Loved X, Read Y',
            'description': 'Compare your book to popular titles',
            'script': f"""
            If you loved [POPULAR BOOK 1] and [POPULAR BOOK 2],
            you NEED to read [BOOK TITLE].
            
            Same [TROPE 1] vibes, plus [UNIQUE ELEMENT].
            
            Link in bio! 🔗
            """,
            'visual': 'Book covers side by side',
            'audio': 'Any trending sound',
            'difficulty': 'Easy'
        },
        'pov': {
            'name': '🎭 POV: You\'re the Character',
            'description': 'Act out a scene from your book',
            'script': f"""
            POV: You're [CHARACTER NAME] when [KEY MOMENT].
            
            [Act out or show scene]
            
            [BOOK TITLE] is out now! ✨
            """,
            'visual': 'Acting or text overlay',
            'audio': 'Dramatic sound',
            'difficulty': 'Medium'
        }
    }
    
    # Filter templates based on author type
    if author_type == AuthorType.SHADOW:
        # Shadow authors get text-only templates
        return {k: v for k, v in templates.items() if 'pov' not in k}
    
    return templates

# ============================================================================
# QUIZ RENDERING (from your existing code, simplified)
# ============================================================================

def render_quiz():
    st.markdown("### 📝 Find Your Author Type")
    st.caption("5 minutes to discover your perfect BookTok strategy")
    
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False
    if 'quiz_complete' not in st.session_state:
        st.session_state.quiz_complete = False
    if 'answers' not in st.session_state:
        st.session_state.answers = {}
    
    if not st.session_state.quiz_started:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Start Quiz →", type="primary", use_container_width=True):
                st.session_state.quiz_started = True
                st.rerun()
        return
    
    if st.session_state.quiz_started and not st.session_state.quiz_complete:
        with st.form("quiz_form"):
            st.markdown("#### Public Visibility")
            
            q1 = st.radio(
                "**Your comfort with being known:**",
                options=[
                    "A) Complete anonymity—let the work speak",
                    "B) Curated persona with boundaries",
                    "C) Mix of personal and professional",
                    "D) Full transparency"
                ],
                index=None
            )
            
            q2 = st.radio(
                "**Being on camera makes you feel:**",
                options=[
                    "A) Terrified—avoid at all costs",
                    "B) Nervous but willing to try",
                    "C) Comfortable with preparation",
                    "D) Excited—love connecting visually"
                ],
                index=None
            )
            
            q3 = st.radio(
                "**Your natural communication style:**",
                options=[
                    "A) Written word (emails, posts)",
                    "B) Audio (podcasts, voice notes)",
                    "C) Visual (video, photos)",
                    "D) Live interaction (events, talks)"
                ],
                index=None
            )
            
            q4 = st.select_slider(
                "**Your social battery:**",
                options=[
                    "Low (need recovery time)",
                    "Medium (flexible)",
                    "High (energized by people)"
                ],
                value=None
            )
            
            q5 = st.selectbox(
                "**Your primary genre:**",
                options=[
                    "Romance", "Romantasy", "Fantasy", 
                    "Thriller", "YA", "Memoir", "Other"
                ],
                index=None
            )
            
            submitted = st.form_submit_button("See My Results", type="primary")
            
            if submitted:
                if None in [q1, q2, q3, q4, q5]:
                    st.error("Please answer all questions")
                else:
                    st.session_state.answers = {
                        'q1': q1[0], 'q2': q2[0], 'q3': q3[0],
                        'q4': q4, 'q5': q5
                    }
                    st.session_state.quiz_complete = True
                    st.rerun()

def render_results():
    """Display quiz results"""
    persona = AuthorPersona()
    visibility_score = persona.calculate_visibility(st.session_state.answers)
    author_type = persona.get_author_type()
    
    # Map interaction style
    q3_map = {'A': InteractionStyle.WRITTEN, 'B': InteractionStyle.AUDIO,
              'C': InteractionStyle.VISUAL, 'D': InteractionStyle.LIVE}
    interaction = q3_map[st.session_state.answers['q3']]
    
    st.balloons()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        colors = {
            AuthorType.SHADOW: "🖤",
            AuthorType.CURATED: "💎",
            AuthorType.BRIDGE: "🌉",
            AuthorType.OPEN_BOOK: "📖"
        }
        
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; color: white;">
            <h1 style="font-size: 4rem;">{colors[author_type]}</h1>
            <h2>{author_type.value}</h2>
            <p>Visibility: {visibility_score:.1f}/4.0</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 Your Profile")
        st.markdown(f"**Style:** {interaction.value}")
        st.markdown(f"**Battery:** {st.session_state.answers['q4']}")
        st.markdown(f"**Genre:** {st.session_state.answers['q5']}")
    
    with col2:
        st.markdown("### 🎯 Your Path")
        recs = {
            AuthorType.SHADOW: "Focus on written content. Text-only videos. Let the app handle outreach.",
            AuthorType.CURATED: "Planned, edited content. Batch create. Schedule everything.",
            AuthorType.BRIDGE: "Mix of formats. Podcasts + occasional video. Find what feels good.",
            AuthorType.OPEN_BOOK: "Live videos, events, personality-driven content. You're the brand."
        }
        st.info(recs[author_type])
    
    if st.button("Start Over"):
        for key in ['quiz_started', 'quiz_complete', 'answers']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.sidebar.title("📱 BookTok Machine")
    st.sidebar.markdown("### Proof of Concept")
    
    # Navigation
    page = st.sidebar.radio(
        "Go to:",
        ["🏠 Dashboard", "👤 Author Quiz", "📚 ARC Readers", "🎯 Influencers", 
         "🎵 Trending Sounds", "📝 Video Templates", "📊 Your Campaigns"]
    )
    
    # Load data
    arc_readers = load_arc_readers()
    
    # ========================================================================
    # DASHBOARD PAGE
    # ========================================================================
    if page == "🏠 Dashboard":
        st.title("📱 Your BookTok Machine")
        st.markdown("### Welcome to your personalized marketing dashboard")
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("ARC Readers", f"{len(arc_readers)}+", "+50 this week")
        with col2:
            st.metric("Influencers", "3,200+", "+124")
        with col3:
            st.metric("Trending Sounds", "47", "+12")
        with col4:
            st.metric("Your Videos", "0", "Start today")
        
        st.markdown("---")
        
        # Getting started
        st.markdown("### 🚀 Your Next Steps")
        
        steps = [
            "1. Take the Author Quiz to discover your persona",
            "2. Add your book details",
            "3. Find ARC readers in your genre",
            "4. Connect with influencers",
            "5. Create your first video"
        ]
        
        for step in steps:
            st.markdown(f"- {step}")
        
        # Quick action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Take Quiz →", use_container_width=True):
                st.session_state.page = "👤 Author Quiz"
                st.rerun()
        with col2:
            if st.button("Find ARC Readers →", use_container_width=True):
                st.session_state.page = "📚 ARC Readers"
                st.rerun()
        with col3:
            if st.button("Create Video →", use_container_width=True):
                st.session_state.page = "📝 Video Templates"
                st.rerun()
    
    # ========================================================================
    # AUTHOR QUIZ PAGE (your existing code)
    # ========================================================================
    elif page == "👤 Author Quiz":
        st.title("👤 Author Persona Discovery")
        
        if not st.session_state.get('quiz_complete', False):
            render_quiz()
        else:
            render_results()
    
    # ========================================================================
    # ARC READERS PAGE
    # ========================================================================
    elif page == "📚 ARC Readers":
        st.title("📚 ARC Reader Database")
        st.markdown(f"### {len(arc_readers)} readers found")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            min_followers = st.slider("Min followers", 0, 50000, 1000)
        with col2:
            has_email = st.checkbox("Has email only")
        with col3:
            genre_filter = st.selectbox(
                "Genre",
                ["All", "Romance", "Romantasy", "Fantasy", "Thriller", "YA"]
            )
        
        # Filter data
        filtered = [r for r in arc_readers if r['followers'] >= min_followers]
        if has_email:
            filtered = [r for r in filtered if r['email']]
        
        # Display as dataframe
        if filtered:
            df = pd.DataFrame(filtered)
            df = df[['username', 'display_name', 'followers', 'email', 'hashtags']]
            st.dataframe(df, use_container_width=True)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download as CSV",
                csv,
                "arc_readers.csv",
                "text/csv"
            )
        else:
            st.info("No readers match your filters")
    
    # ========================================================================
    # INFLUENCERS PAGE
    # ========================================================================
    elif page == "🎯 Influencers":
        st.title("🎯 BookTok Influencers")
        
        genre = st.selectbox("Select your genre", 
                            ["romance", "romantasy", "fantasy", "thriller", "YA"])
        
        influencers = get_influencers_by_genre(genre)
        
        for inf in influencers:
            with st.expander(f"@{inf['username']} - {inf['followers']:,} followers"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Engagement:** {inf['engagement']}%")
                    st.markdown(f"**Genres:** {', '.join(inf['genres'])}")
                with col2:
                    st.markdown(f"**Accepts indies:** {'✅' if inf['accepts_indies'] else '❌'}")
                    st.markdown(f"**Rate:** {inf['rate']}")
                
                if st.button(f"📤 Send Outreach", key=inf['username']):
                    st.success(f"Outreach template copied for @{inf['username']}")
    
    # ========================================================================
    # TRENDING SOUNDS PAGE
    # ========================================================================
    elif page == "🎵 Trending Sounds":
        st.title("🎵 Trending Sounds")
        
        genre = st.selectbox("Filter by genre", 
                            ["romance", "romantasy", "fantasy", "thriller", "all"])
        
        sounds = get_trending_sounds(genre if genre != 'all' else None)
        
        for sound in sounds:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{sound['name']}**")
            with col2:
                st.markdown(f"{sound['uses']:,} uses")
            with col3:
                st.markdown(f"📈 {sound['growth']}")
            
            if st.button(f"Use This Sound", key=sound['name']):
                st.success(f"Sound saved to your library")
    
    # ========================================================================
    # VIDEO TEMPLATES PAGE
    # ========================================================================
    elif page == "📝 Video Templates":
        st.title("📝 Video Templates")
        
        # Get author type from session if available
        author_type = None
        if st.session_state.get('quiz_complete'):
            persona = AuthorPersona()
            persona.calculate_visibility(st.session_state.answers)
            author_type = persona.get_author_type()
        
        genre = st.selectbox("Your genre", 
                            ["Romance", "Romantasy", "Fantasy", "Thriller", "YA"])
        
        templates = get_video_templates(genre, author_type)
        
        for tid, template in templates.items():
            with st.expander(f"{template['name']} - {template['difficulty']}"):
                st.markdown(f"**{template['description']}**")
                st.markdown("**Script:**")
                st.code(template['script'])
                st.markdown(f"**Visual:** {template['visual']}")
                st.markdown(f"**Audio:** {template['audio']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Use This Template", key=tid):
                        st.session_state['selected_template'] = template
                        st.success("Template selected! Go to Creator Studio")
                with col2:
                    st.button("Preview", key=f"preview_{tid}")
    
    # ========================================================================
    # CAMPAIGNS PAGE
    # ========================================================================
    elif page == "📊 Your Campaigns":
        st.title("📊 Your Campaigns")
        
        st.markdown("### Active Campaigns")
        
        # Sample campaign data
        campaigns = [
            {"name": "Romance ARC Campaign", "status": "Active", 
             "readers": 45, "reviews": 12, "days_left": 23},
            {"name": "Influencer Outreach", "status": "Pending", 
             "influencers": 8, "responses": 3, "days_left": 14}
        ]
        
        for camp in campaigns:
            with st.expander(f"{camp['name']} - {camp['status']}"):
                for key, value in camp.items():
                    if key != 'name' and key != 'status':
                        st.markdown(f"**{key}:** {value}")
        
        st.markdown("---")
        st.markdown("### Start New Campaign")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 ARC Reader Campaign", use_container_width=True):
                st.info("Coming soon: Select your book and we'll find readers")
        with col2:
            if st.button("🎯 Influencer Campaign", use_container_width=True):
                st.info("Coming soon: We'll match you with BookTok influencers")

# ============================================================================
# RUN THE APP
# ============================================================================

if __name__ == "__main__":
    main()

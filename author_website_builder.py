"""
Author Website Builder Module for BardSpark
Creates COMPLETE website content using book analysis and marketing assets
WITH MANUAL QUESTIONNAIRE AND WORKING IMAGES
"""

import streamlit as st
import json
import base64
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import html
from openai import OpenAI

# ============================================================================
# DATABASE CONNECTION
# ============================================================================
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

def load_user_marketing_assets(user_id):
    """Load user's saved marketing assets"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM user_marketing_assets 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        
        assets = cur.fetchall()
        return [dict(a) for a in assets]
    except Exception as e:
        st.error(f"Error loading assets: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ============================================================================
# DATA FUNCTIONS - Pull from ALL sources
# ============================================================================
def get_complete_author_data():
    """Pull ALL existing author data from session state and database"""
    
    data = {
        "profile": {},
        "book_analysis": {},
        "marketing_assets": {},
        "advocates": []
    }
    
    # 1. Get User Profile Data
    if st.session_state.get('authenticated', False):
        current_user = st.session_state.get('current_user', {})
        if isinstance(current_user, dict):
            data["profile"] = {
                "name": current_user.get('name', ''),
                "email": current_user.get('email', ''),
                "pen_name": current_user.get('pen_name', ''),
                "bio": current_user.get('bio', ''),
                "website": current_user.get('website', ''),
                "social_media": current_user.get('social_media', {})
            }
    
    # 2. Get Book Analyzer Results
    if 'analysis_result' in st.session_state:
        analysis = st.session_state.analysis_result
        if isinstance(analysis, dict):
            book_info = analysis.get('book_info', {})
            if isinstance(book_info, str):
                try:
                    book_info = json.loads(book_info)
                except:
                    book_info = {}
            
            marketability = analysis.get('marketability', {})
            if isinstance(marketability, str):
                try:
                    marketability = json.loads(marketability)
                except:
                    marketability = {}
            
            data["book_analysis"] = {
                "title": book_info.get('title', ''),
                "author": book_info.get('author', data["profile"].get('name', '')),
                "genre": book_info.get('genre', ''),
                "subgenres": book_info.get('subgenres', []),
                "description": book_info.get('description', ''),
                "target_audience": marketability.get('target_audience', ''),
                "comparable_titles": marketability.get('comparable_titles', []),
                "unique_selling_points": marketability.get('unique_selling_points', []),
                "themes": book_info.get('themes', [])
            }
    
    # 3. Get Marketing Assets from session or database
    if 'generated_assets' in st.session_state and st.session_state.generated_assets:
        data["marketing_assets"] = st.session_state.generated_assets
    elif 'edited_assets' in st.session_state and st.session_state.edited_assets:
        data["marketing_assets"] = st.session_state.edited_assets
    elif st.session_state.get('authenticated', False):
        # Try to load from database
        db_assets = load_user_marketing_assets(st.session_state.get('user_id', 1))
        if db_assets:
            # Combine all assets
            combined = {}
            for asset in db_assets:
                asset_data = asset.get('asset_data', {})
                if isinstance(asset_data, str):
                    try:
                        asset_data = json.loads(asset_data)
                    except:
                        continue
                combined.update(asset_data)
            if combined:
                data["marketing_assets"] = combined
    
    # 4. Get Saved Advocates
    saved_readers = st.session_state.get('saved_readers', [])
    if saved_readers and isinstance(saved_readers, list):
        data["advocates"] = []
        for reader in saved_readers[:8]:
            if isinstance(reader, dict):
                data["advocates"].append({
                    "username": reader.get('username', ''),
                    "platform": reader.get('platform', ''),
                    "follower_count": reader.get('follower_count', 0),
                    "engagement_rate": reader.get('engagement_rate', ''),
                    "testimonial": reader.get('testimonial', '')
                })
    
    return data

# ============================================================================
# AI WEBSITE CONTENT GENERATOR
# ============================================================================
def generate_website_content(client, author_data):
    """Use AI to generate complete website content from all data"""
    
    book = author_data.get('book_analysis', {})
    profile = author_data.get('profile', {})
    assets = author_data.get('marketing_assets', {})
    advocates = author_data.get('advocates', [])
    
    # Extract specific assets
    blurbs = assets.get('blurbs', [])
    best_blurb = blurbs[0] if blurbs else book.get('description', '')
    
    reviews = []
    if 'press_kit_options' in assets:
        for kit in assets.get('press_kit_options', []):
            if isinstance(kit, dict) and 'author_qanda' in kit:
                for qa in kit.get('author_qanda', []):
                    if isinstance(qa, dict) and 'answer' in qa:
                        reviews.append(qa['answer'][:100] + '...')
    
    prompt = f"""
    Create COMPLETE website content for an author using this data.
    
    AUTHOR PROFILE:
    Name: {profile.get('name', 'Unknown')}
    Pen Name: {profile.get('pen_name', '')}
    Bio: {profile.get('bio', '')}
    
    BOOK INFORMATION:
    Title: {book.get('title', 'Unknown')}
    Genre: {book.get('genre', 'Unknown')}
    Description: {book.get('description', '')}
    Target Audience: {book.get('target_audience', '')}
    Unique Selling Points: {book.get('unique_selling_points', [])}
    
    MARKETING ASSETS:
    Best Blurb: {best_blurb}
    Sample Reviews: {reviews[:3]}
    Number of Advocates: {len(advocates)}
    
    Generate COMPLETE content for these pages:
    
    1. HOME PAGE: Hero section with book title, tagline, and call-to-action
    2. ABOUT PAGE: Author biography, writing journey, personal story
    3. BOOK PAGE: Complete book description, reviews, purchase links
    4. REVIEWS PAGE: Testimonials and praise
    5. CONTACT PAGE: Contact info and social links
    
    Return JSON with:
    {{
        "home_page": {{
            "hero_title": "Catchy headline",
            "hero_subtitle": "Engaging subtitle",
            "hero_cta": "Call to action text",
            "featured_quote": "Powerful quote from reviews"
        }},
        "about_page": {{
            "title": "About [Author Name]",
            "full_bio": "Complete biography with personal journey",
            "writing_philosophy": "Their approach to writing",
            "fun_facts": ["fact1", "fact2", "fact3"]
        }},
        "book_page": {{
            "title": "About the Book",
            "full_description": "Compelling book description",
            "praise_quotes": ["quote1", "quote2", "quote3"],
            "key_features": ["feature1", "feature2", "feature3"],
            "audience": "Who should read this"
        }},
        "reviews_page": {{
            "title": "Praise for the Book",
            "featured_reviews": ["review1", "review2", "review3", "review4", "review5"],
            "advocate_spotlight": "Section about supporters"
        }},
        "contact_page": {{
            "title": "Get in Touch",
            "contact_message": "Friendly message inviting contact",
            "social_text": "Follow me on social media"
        }}
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional website copywriter. Create engaging, compelling content that sells books."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"AI content generation failed: {e}")
        return None

# ============================================================================
# COMPLETE HTML GENERATOR (WITH ACTUAL IMAGES)
# ============================================================================
def generate_complete_website(author_data, ai_content=None, author_photo=None, book_cover=None):
    """Generate a complete HTML website with ACTUAL images"""
    
    book = author_data.get('book_analysis', {})
    profile = author_data.get('profile', {})
    assets = author_data.get('marketing_assets', {})
    advocates = author_data.get('advocates', [])
    
    # Get real content (prioritize AI generated, fallback to available data)
    if ai_content:
        home = ai_content.get('home_page', {})
        about = ai_content.get('about_page', {})
        book_page = ai_content.get('book_page', {})
        reviews_page = ai_content.get('reviews_page', {})
        contact = ai_content.get('contact_page', {})
    else:
        # Fallback to using available data directly
        home = {
            "hero_title": book.get('title', 'My Book'),
            "hero_subtitle": f"A {book.get('genre', '')} Novel",
            "hero_cta": "Buy Now",
            "featured_quote": ""
        }
        about = {
            "title": f"About {profile.get('name', 'the Author')}",
            "full_bio": profile.get('bio', book.get('description', '')[:200] + '...'),
            "writing_philosophy": "",
            "fun_facts": []
        }
        book_page = {
            "title": book.get('title', 'My Book'),
            "full_description": book.get('description', ''),
            "praise_quotes": [],
            "key_features": book.get('unique_selling_points', []),
            "audience": book.get('target_audience', '')
        }
        reviews_page = {
            "title": "Reviews",
            "featured_reviews": [],
            "advocate_spotlight": ""
        }
        contact = {
            "title": "Contact",
            "contact_message": "I'd love to hear from you!",
            "social_text": "Connect with me:"
        }
    
    # Get blurbs from marketing assets
    blurbs = assets.get('blurbs', [])
    best_blurb = blurbs[0] if blurbs else book.get('description', '')
    
    # Get reviews from press kit
    reviews = []
    if 'press_kit_options' in assets:
        for kit in assets.get('press_kit_options', []):
            if isinstance(kit, dict) and 'author_qanda' in kit:
                for qa in kit.get('author_qanda', []):
                    if isinstance(qa, dict) and 'answer' in qa:
                        reviews.append({
                            "text": qa['answer'][:150] + '...',
                            "source": "Reader"
                        })
    
    # Add advocate testimonials
    for advocate in advocates[:4]:
        reviews.append({
            "text": advocate.get('testimonial', ''),
            "source": f"@{advocate.get('username', 'Reader')}"
        })
    
    # Build advocate cards
    advocate_html = ""
    for adv in advocates[:6]:
        advocate_html += f"""
        <div class="advocate-card">
            <div class="advocate-avatar">{adv.get('username', 'R')[0].upper()}</div>
            <h4>@{adv.get('username', 'Reader')}</h4>
            <p class="platform">{adv.get('platform', 'Social Media')} • {adv.get('follower_count', 0)} followers</p>
            <p class="testimonial">"{adv.get('testimonial', '')}"</p>
        </div>
        """
    
    # Build reviews HTML
    reviews_html = ""
    for review in reviews[:6]:
        reviews_html += f"""
        <div class="review-card">
            <p class="review-text">"{review.get('text', '')}"</p>
            <p class="reviewer">— {review.get('source', 'Reader')}</p>
        </div>
        """
    
    # Build features HTML
    features_html = ""
    for feature in book_page.get('key_features', [])[:5]:
        features_html += f'<li class="feature-item">✓ {feature}</li>'
    
    # Build fun facts HTML
    facts_html = ""
    for fact in about.get('fun_facts', [])[:3]:
        facts_html += f'<li class="fact-item">✨ {fact}</li>'
    
    # ========================================================================
    # FIX: Convert images to base64 so they ACTUALLY SHOW
    # ========================================================================
    author_img_html = ""
    if author_photo:
        img_data = base64.b64encode(author_photo.getvalue()).decode()
        author_img_html = f'<img src="data:image/jpeg;base64,{img_data}" class="author-photo" style="width:150px;height:150px;border-radius:50%;object-fit:cover;margin:0 auto 20px;display:block;">'
    
    book_cover_html = ""
    if book_cover:
        cover_data = base64.b64encode(book_cover.getvalue()).decode()
        book_cover_html = f'<img src="data:image/jpeg;base64,{cover_data}" class="book-cover" style="max-width:300px;width:100%;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,0.2);">'
    
    # Complete HTML template with REAL images
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{profile.get('name', 'Author')} - {book.get('title', 'Official Website')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        /* Navigation */
        nav {{
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .nav-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .logo {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #crimson;
            text-decoration: none;
        }}
        
        .nav-links a {{
            margin-left: 2rem;
            text-decoration: none;
            color: #333;
            font-weight: 500;
        }}
        
        .nav-links a:hover {{
            color: #crimson;
        }}
        
        /* Hero Section */
        .hero {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 100px 20px;
            text-align: center;
        }}
        
        .hero h1 {{
            font-size: 3.5rem;
            margin-bottom: 1rem;
        }}
        
        .hero h2 {{
            font-size: 1.8rem;
            font-weight: 300;
            margin-bottom: 2rem;
            opacity: 0.9;
        }}
        
        .hero .cta-button {{
            display: inline-block;
            padding: 15px 40px;
            background: white;
            color: #764ba2;
            text-decoration: none;
            border-radius: 50px;
            font-weight: bold;
            font-size: 1.2rem;
            transition: transform 0.3s;
        }}
        
        .hero .cta-button:hover {{
            transform: translateY(-3px);
        }}
        
        .featured-quote {{
            margin-top: 3rem;
            font-size: 1.3rem;
            font-style: italic;
            opacity: 0.9;
        }}
        
        /* Sections */
        .section {{
            padding: 80px 20px;
        }}
        
        .section-title {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 50px;
            color: #333;
        }}
        
        .section-title:after {{
            content: '';
            display: block;
            width: 100px;
            height: 3px;
            background: #crimson;
            margin: 20px auto;
        }}
        
        /* Book Section */
        .book-content {{
            display: flex;
            flex-wrap: wrap;
            gap: 50px;
            align-items: center;
        }}
        
        .book-cover {{
            flex: 1;
            min-width: 300px;
            text-align: center;
        }}
        
        .book-details {{
            flex: 2;
            min-width: 300px;
        }}
        
        .book-title {{
            font-size: 2.5rem;
            color: #333;
            margin-bottom: 10px;
        }}
        
        .book-genre {{
            color: #666;
            font-size: 1.2rem;
            margin-bottom: 20px;
        }}
        
        .book-description {{
            font-size: 1.1rem;
            line-height: 1.8;
            color: #555;
            margin-bottom: 30px;
        }}
        
        .feature-list {{
            list-style: none;
            margin: 20px 0;
        }}
        
        .feature-item {{
            margin: 10px 0;
            font-size: 1.1rem;
        }}
        
        .purchase-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 30px;
        }}
        
        .purchase-link {{
            padding: 12px 30px;
            background: #crimson;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        .purchase-link.amazon {{
            background: #232f3e;
        }}
        
        .purchase-link.goodreads {{
            background: #372213;
        }}
        
        /* Reviews Grid */
        .reviews-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }}
        
        .review-card {{
            background: #f9f9f9;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        }}
        
        .review-text {{
            font-size: 1.1rem;
            font-style: italic;
            color: #555;
            margin-bottom: 20px;
            line-height: 1.8;
        }}
        
        .reviewer {{
            font-weight: bold;
            color: #crimson;
        }}
        
        /* Advocates Grid */
        .advocates-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }}
        
        .advocate-card {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            text-align: center;
            border: 1px solid #eee;
        }}
        
        .advocate-avatar {{
            width: 80px;
            height: 80px;
            background: #crimson;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2rem;
            font-weight: bold;
            margin: 0 auto 20px;
        }}
        
        .advocate-card h4 {{
            margin-bottom: 5px;
            color: #333;
        }}
        
        .platform {{
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 15px;
        }}
        
        .testimonial {{
            font-style: italic;
            color: #555;
            line-height: 1.6;
        }}
        
        /* About Section */
        .about-content {{
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .bio {{
            font-size: 1.2rem;
            line-height: 1.8;
            color: #555;
            margin-bottom: 30px;
        }}
        
        .facts-list {{
            list-style: none;
            margin-top: 30px;
        }}
        
        .fact-item {{
            margin: 15px 0;
            font-size: 1.1rem;
            color: #555;
        }}
        
        /* Contact Section */
        .contact-content {{
            text-align: center;
            max-width: 600px;
            margin: 0 auto;
        }}
        
        .contact-message {{
            font-size: 1.2rem;
            color: #555;
            margin-bottom: 30px;
        }}
        
        .social-links {{
            margin: 40px 0;
        }}
        
        .social-link {{
            display: inline-block;
            margin: 0 15px;
            padding: 12px 25px;
            background: #f0f0f0;
            color: #333;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
        }}
        
        .social-link:hover {{
            background: #crimson;
            color: white;
        }}
        
        .email-signup {{
            margin-top: 40px;
        }}
        
        .email-input {{
            padding: 15px;
            width: 300px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 1rem;
        }}
        
        .subscribe-button {{
            padding: 15px 30px;
            background: #crimson;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            margin-left: 10px;
        }}
        
        .subscribe-button:hover {{
            background: #a01c1c;
        }}
        
        /* Footer */
        footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 40px 20px;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .nav-links {{
                display: none;
            }}
            
            .hero h1 {{
                font-size: 2.5rem;
            }}
            
            .hero h2 {{
                font-size: 1.3rem;
            }}
            
            .book-content {{
                flex-direction: column;
                text-align: center;
            }}
            
            .purchase-links {{
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav>
        <div class="nav-container">
            <a href="#" class="logo">{profile.get('name', 'Author')}</a>
            <div class="nav-links">
                <a href="#home">Home</a>
                <a href="#book">Book</a>
                <a href="#reviews">Reviews</a>
                <a href="#about">About</a>
                <a href="#contact">Contact</a>
            </div>
        </div>
    </nav>
    
    <!-- Hero Section -->
    <section id="home" class="hero">
        <div class="container">
            {author_img_html if author_img_html else f'<div style="width:150px;height:150px;border-radius:50%;background:rgba(255,255,255,0.2);margin:0 auto 20px;display:flex;align-items:center;justify-content:center;font-size:3rem;">📸</div>'}
            <h1>{profile.get('name', home.get('hero_title', book.get('title', 'My Book')))}</h1>
            <h2>{home.get('hero_subtitle', f"A {book.get('genre', '')} Novel")}</h2>
            <a href="#book" class="cta-button">{home.get('hero_cta', 'Explore the Book')}</a>
            {f'<div class="featured-quote">"{home.get("featured_quote", "")}"</div>' if home.get('featured_quote') else ''}
        </div>
    </section>
    
    <!-- Book Section -->
    <section id="book" class="section">
        <div class="container">
            <h2 class="section-title">{book_page.get('title', 'The Book')}</h2>
            <div class="book-content">
                <div class="book-cover">
                    {book_cover_html if book_cover_html else f'<div class="cover-placeholder" style="width:300px;height:450px;background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);border-radius:10px;display:inline-flex;align-items:center;justify-content:center;color:white;font-size:1.5rem;margin:0 auto;">{book.get("title", "Book Cover")[:20]}</div>'}
                </div>
                <div class="book-details">
                    <h3 class="book-title">{book.get('title', '')}</h3>
                    <p class="book-genre">{book.get('genre', '')}</p>
                    <p class="book-description">{book_page.get('full_description', book.get('description', ''))}</p>
                    
                    {f'<ul class="feature-list">{features_html}</ul>' if features_html else ''}
                    
                    <div class="purchase-links">
                        <a href="#" class="purchase-link amazon">Amazon</a>
                        <a href="#" class="purchase-link goodreads">Goodreads</a>
                        <a href="#" class="purchase-link">Barnes & Noble</a>
                    </div>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Reviews Section -->
    <section id="reviews" class="section" style="background: #f5f5f5;">
        <div class="container">
            <h2 class="section-title">{reviews_page.get('title', 'Reviews & Praise')}</h2>
            
            {f'<div class="reviews-grid">{reviews_html}</div>' if reviews_html else ''}
            
            {f'''
            <h3 style="text-align: center; margin: 60px 0 30px;">Our Amazing Advocates</h3>
            <div class="advocates-grid">{advocate_html}</div>
            ''' if advocate_html else ''}
        </div>
    </section>
    
    <!-- About Section -->
    <section id="about" class="section">
        <div class="container">
            <h2 class="section-title">{about.get('title', f'About {profile.get("name", "the Author")}')}</h2>
            <div class="about-content">
                <p class="bio">{about.get('full_bio', profile.get('bio', ''))}</p>
                
                {f'<p class="bio">{about.get("writing_philosophy", "")}</p>' if about.get('writing_philosophy') else ''}
                
                {f'<ul class="facts-list">{facts_html}</ul>' if facts_html else ''}
            </div>
        </div>
    </section>
    
    <!-- Contact Section -->
    <section id="contact" class="section" style="background: #f5f5f5;">
        <div class="container">
            <h2 class="section-title">{contact.get('title', 'Get in Touch')}</h2>
            <div class="contact-content">
                <p class="contact-message">{contact.get('contact_message', "I'd love to hear from you!")}</p>
                
                <div class="social-links">
                    <a href="#" class="social-link">Twitter</a>
                    <a href="#" class="social-link">Instagram</a>
                    <a href="#" class="social-link">Facebook</a>
                    <a href="#" class="social-link">TikTok</a>
                </div>
                
                <div class="email-signup">
                    <h3>Join the Newsletter</h3>
                    <p style="margin: 20px 0;">Get updates on new releases and exclusive content</p>
                    <input type="email" class="email-input" placeholder="Your email address">
                    <button class="subscribe-button">Subscribe</button>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Footer -->
    <footer>
        <div class="container">
            <p>© {datetime.now().year} {profile.get('name', 'Author')}. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>"""
    
    return html

# ============================================================================
# MAIN WEBSITE BUILDER UI - WITH MANUAL QUESTIONNAIRE
# ============================================================================
def show_website_builder():
    """Main function to display the website builder"""
    
    st.title("🌐 Complete Author Website Generator")
    st.markdown("""
    ### Generate a COMPLETE website using your:
    - ✅ Book Analyzer data (title, genre, description)
    - ✅ Marketing Assets (blurbs, reviews, press kit)
    - ✅ Saved Advocates (ARC readers and influencers)
    - ✅ Author Profile (bio, social media)
    
    **YOUR BOOK COVER WILL SHOW IN THE WEBSITE!**
    """)
    
    # ========================================================================
    # API Key for AI generation (ALREADY HERE - NOT CHANGED)
    # ========================================================================
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    
    if not st.session_state.openai_api_key:
        with st.container():
            st.markdown("### 🔑 OpenAI API Key (for AI-powered content)")
            api_key = st.text_input("Enter your API key", type="password", key="website_api_key")
            if api_key:
                st.session_state.openai_api_key = api_key
                st.rerun()
        return
    
    # ========================================================================
    # Load all data
    # ========================================================================
    with st.spinner("Loading your data..."):
        author_data = get_complete_author_data()
        client = OpenAI(api_key=st.session_state.openai_api_key)
    
    # ========================================================================
    # MANUAL IMAGE UPLOAD SECTION - ADDED
    # ========================================================================
    st.markdown("---")
    st.markdown("### 📸 Upload Your Images (They WILL appear in the website)")
    
    col1, col2 = st.columns(2)
    with col1:
        author_photo = st.file_uploader(
            "Your Photo (optional)", 
            type=['jpg', 'jpeg', 'png'],
            help="Upload a professional headshot"
        )
        if author_photo:
            st.image(author_photo, width=150, caption="Preview")
    
    with col2:
        book_cover = st.file_uploader(
            "Book Cover *", 
            type=['jpg', 'jpeg', 'png'],
            help="Upload your book cover image"
        )
        if book_cover:
            st.image(book_cover, width=150, caption="Preview")
    
    # ========================================================================
    # MANUAL QUESTIONNAIRE SECTION - ADDED
    # ========================================================================
    st.markdown("---")
    st.markdown("### 📝 Manual Override - Fill in What's Missing")
    
    with st.expander("✏️ Edit Your Data Manually", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Author Information**")
            manual_name = st.text_input("Your Name", value=author_data['profile'].get('name', ''))
            manual_bio = st.text_area("Your Bio", value=author_data['profile'].get('bio', ''), height=100)
            
            if manual_name:
                author_data['profile']['name'] = manual_name
            if manual_bio:
                author_data['profile']['bio'] = manual_bio
        
        with col2:
            st.markdown("**Book Information**")
            manual_title = st.text_input("Book Title", value=author_data['book_analysis'].get('title', ''))
            manual_genre = st.text_input("Genre", value=author_data['book_analysis'].get('genre', ''))
            manual_desc = st.text_area("Description", value=author_data['book_analysis'].get('description', ''), height=100)
            
            if manual_title:
                author_data['book_analysis']['title'] = manual_title
            if manual_genre:
                author_data['book_analysis']['genre'] = manual_genre
            if manual_desc:
                author_data['book_analysis']['description'] = manual_desc
        
        st.markdown("**Social Media Links**")
        soc = author_data['profile'].get('social_media', {})
        col1, col2 = st.columns(2)
        with col1:
            twitter = st.text_input("Twitter/X", value=soc.get('twitter', ''))
            instagram = st.text_input("Instagram", value=soc.get('instagram', ''))
        with col2:
            facebook = st.text_input("Facebook", value=soc.get('facebook', ''))
            tiktok = st.text_input("TikTok", value=soc.get('tiktok', ''))
        
        # Update social media
        author_data['profile']['social_media'] = {
            'twitter': twitter,
            'instagram': instagram,
            'facebook': facebook,
            'tiktok': tiktok
        }
    
    # ========================================================================
    # Show data summary (KEEPING YOUR EXISTING CODE)
    # ========================================================================
    with st.expander("📊 View Data Being Used", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📚 Book Data:**")
            book = author_data.get('book_analysis', {})
            st.markdown(f"- Title: {book.get('title', 'Not found')}")
            st.markdown(f"- Genre: {book.get('genre', 'Not found')}")
            st.markdown(f"- Description: {'✅' if book.get('description') else '❌'}")
        
        with col2:
            st.markdown("**🎨 Marketing Assets:**")
            assets = author_data.get('marketing_assets', {})
            st.markdown(f"- Blurbs: {len(assets.get('blurbs', []))}")
            st.markdown(f"- Reviews: {len(assets.get('press_kit_options', []))}")
            st.markdown(f"- Email Sequences: {len(assets.get('email_sequences', []))}")
        
        with col3:
            st.markdown("**👥 Advocates:**")
            advocates = author_data.get('advocates', [])
            st.markdown(f"- Total: {len(advocates)}")
            if advocates:
                st.markdown(f"- Sample: @{advocates[0].get('username', '')}")
    
    st.markdown("---")
    
    # ========================================================================
    # Generate button (YOUR EXISTING CODE)
    # ========================================================================
    if st.button("🚀 GENERATE COMPLETE WEBSITE", type="primary", use_container_width=True):
        if not book_cover:
            st.warning("Book cover is optional but recommended")
            
        with st.spinner("AI is creating your website content... (30-45 seconds)"):
            try:
                # Step 1: Generate AI content from all data
                ai_content = generate_website_content(client, author_data)
                
                if ai_content:
                    # Step 2: Generate complete HTML with REAL images
                    html_content = generate_complete_website(
                        author_data, 
                        ai_content, 
                        author_photo, 
                        book_cover
                    )
                    
                    st.success("✅ Website generated successfully! Your book cover is now visible.")
                    
                    # Display preview
                    st.markdown("### 👁️ Preview - Your Images Are Here!")
                    st.components.v1.html(html_content, height=600, scrolling=True)
                    
                    # Download button
                    book = author_data.get('book_analysis', {})
                    title = book.get('title', 'MyBook').replace(' ', '_')
                    filename = f"{title}_website.html"
                    
                    b64 = base64.b64encode(html_content.encode()).decode()
                    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; padding: 12px 30px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 20px;">📥 Download Complete Website HTML</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                    st.info("""
                    **📋 Next Steps:**
                    1. Download the HTML file
                    2. Upload to Netlify Drop (or your web host)
                    3. Your book cover is already in the file!
                    """)
                else:
                    st.error("Failed to generate website content")
                    
            except Exception as e:
                st.error(f"Website generation failed: {str(e)}")

# For backward compatibility
def render_questionnaire():
    show_website_builder()

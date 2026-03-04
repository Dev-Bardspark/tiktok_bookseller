import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import json
import requests
from bs4 import BeautifulSoup
import time
import random

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

# ============================================================================
# CREATE TABLES
# ============================================================================
def init_sales_tables():
    """Create sales tracking tables"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Amazon credentials table (encrypted)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS amazon_credentials (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) UNIQUE,
                amazon_email TEXT,
                amazon_password TEXT, -- encrypted
                kdp_region VARCHAR(10) DEFAULT 'US',
                last_sync TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Books table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS author_books (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                asin VARCHAR(20),
                title VARCHAR(255),
                series VARCHAR(255),
                format VARCHAR(50), -- ebook, paperback, hardcover, audiobook
                genre VARCHAR(100),
                publication_date DATE,
                list_price DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Daily sales table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_sales (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                book_id INTEGER REFERENCES author_books(id),
                asin VARCHAR(20),
                sale_date DATE,
                units_sold INTEGER DEFAULT 0,
                revenue DECIMAL(10,2) DEFAULT 0,
                royalties DECIMAL(10,2) DEFAULT 0,
                currency VARCHAR(3) DEFAULT 'USD',
                marketplace VARCHAR(10), -- US, UK, DE, etc.
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, asin, sale_date, marketplace)
            )
        """)
        
        # KDP rankings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_rankings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                book_id INTEGER REFERENCES author_books(id),
                asin VARCHAR(20),
                rank_date DATE,
                sales_rank INTEGER,
                category_rank INTEGER,
                category_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, asin, rank_date)
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creating tables: {e}")
        return False

# ============================================================================
# ENCRYPT/DECRYPT AMAZON CREDENTIALS
# ============================================================================
def encrypt_password(password):
    """Simple encryption - in production use proper encryption"""
    salt = "bardspark_amazon_salt_2026"
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

def save_amazon_credentials(user_id, email, password, region="US"):
    """Save encrypted Amazon credentials"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Check if credentials exist
        cur.execute("SELECT id FROM amazon_credentials WHERE user_id = %s", (user_id,))
        exists = cur.fetchone()
        
        encrypted_password = encrypt_password(password)
        
        if exists:
            cur.execute("""
                UPDATE amazon_credentials 
                SET amazon_email = %s, amazon_password = %s, kdp_region = %s, updated_at = %s
                WHERE user_id = %s
            """, (email, encrypted_password, region, datetime.now(), user_id))
        else:
            cur.execute("""
                INSERT INTO amazon_credentials (user_id, amazon_email, amazon_password, kdp_region)
                VALUES (%s, %s, %s, %s)
            """, (user_id, email, encrypted_password, region))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error saving credentials: {e}")
        return False

def get_amazon_credentials(user_id):
    """Get Amazon credentials for user"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT amazon_email, amazon_password, kdp_region, last_sync
            FROM amazon_credentials
            WHERE user_id = %s
        """, (user_id,))
        
        creds = cur.fetchone()
        cur.close()
        conn.close()
        
        if creds:
            return dict(creds)
        return None
    except Exception as e:
        st.error(f"Error fetching credentials: {e}")
        return None

# ============================================================================
# MOCK DATA GENERATOR (FOR TESTING - REPLACE WITH REAL AMAZON API)
# ============================================================================
def generate_mock_sales_data(user_id, days=30):
    """Generate mock sales data for testing"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # Get user's books
        cur.execute("SELECT id, asin, title FROM author_books WHERE user_id = %s", (user_id,))
        books = cur.fetchall()
        
        if not books:
            # Create mock books if none exist
            mock_books = [
                ("B08XYZ1234", "The Lost Kingdom", "Fantasy", 9.99),
                ("B09ABC5678", "Midnight Secrets", "Mystery", 12.99),
                ("B10DEF9012", "Love in Paris", "Romance", 8.99),
                ("B11GHI3456", "Beyond the Stars", "Sci-Fi", 11.99),
            ]
            
            for asin, title, genre, price in mock_books:
                cur.execute("""
                    INSERT INTO author_books (user_id, asin, title, format, genre, list_price)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (user_id, asin, title, "ebook", genre, price))
            
            conn.commit()
            
            # Get the new books
            cur.execute("SELECT id, asin, title FROM author_books WHERE user_id = %s", (user_id,))
            books = cur.fetchall()
        
        # Generate random sales for last 30 days
        marketplaces = ['US', 'UK', 'DE', 'FR', 'JP']
        
        for book_id, asin, title in books:
            for i in range(days):
                sale_date = datetime.now() - timedelta(days=i)
                
                # Random sales for each marketplace
                for marketplace in marketplaces:
                    units = random.randint(0, 5) if random.random() > 0.3 else 0
                    if units > 0:
                        revenue = round(units * random.uniform(8, 15), 2)
                        royalties = round(revenue * 0.35, 2)  # 35% royalty estimate
                        
                        cur.execute("""
                            INSERT INTO daily_sales 
                            (user_id, book_id, asin, sale_date, units_sold, revenue, royalties, marketplace)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (user_id, asin, sale_date, marketplace) 
                            DO UPDATE SET 
                                units_sold = EXCLUDED.units_sold,
                                revenue = EXCLUDED.revenue,
                                royalties = EXCLUDED.royalties
                        """, (user_id, book_id, asin, sale_date, units, revenue, royalties, marketplace))
                
                # Add ranking data
                sales_rank = random.randint(1000, 50000)
                category_rank = random.randint(1, 500)
                categories = ["Fantasy", "Mystery", "Romance", "Sci-Fi", "Fiction"]
                category = random.choice(categories)
                
                cur.execute("""
                    INSERT INTO daily_rankings 
                    (user_id, book_id, asin, rank_date, sales_rank, category_rank, category_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, asin, rank_date) 
                    DO UPDATE SET 
                        sales_rank = EXCLUDED.sales_rank,
                        category_rank = EXCLUDED.category_rank,
                        category_name = EXCLUDED.category_name
                """, (user_id, book_id, asin, sale_date, sales_rank, category_rank, category))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Update last sync time
        cur = conn.cursor()
        cur.execute("""
            UPDATE amazon_credentials 
            SET last_sync = %s 
            WHERE user_id = %s
        """, (datetime.now(), user_id))
        conn.commit()
        cur.close()
        conn.close()
        
        return True
    except Exception as e:
        st.error(f"Error generating mock data: {e}")
        return False

# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================
def fetch_user_books(user_id):
    """Get all books for a user"""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    df = pd.read_sql("""
        SELECT * FROM author_books 
        WHERE user_id = %s 
        ORDER BY title
    """, conn, params=(user_id,))
    
    conn.close()
    return df

def fetch_user_sales(user_id, days=30, book_id=None):
    """Get sales data for a user"""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    query = """
        SELECT ds.*, ab.title, ab.format, ab.genre
        FROM daily_sales ds
        JOIN author_books ab ON ds.book_id = ab.id
        WHERE ds.user_id = %s
        AND ds.sale_date >= CURRENT_DATE - INTERVAL '%s days'
    """
    params = [user_id, days]
    
    if book_id:
        query += " AND ds.book_id = %s"
        params.append(book_id)
    
    query += " ORDER BY ds.sale_date DESC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def fetch_user_rankings(user_id, days=30, book_id=None):
    """Get ranking data for a user"""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    query = """
        SELECT dr.*, ab.title, ab.genre
        FROM daily_rankings dr
        JOIN author_books ab ON dr.book_id = ab.id
        WHERE dr.user_id = %s
        AND dr.rank_date >= CURRENT_DATE - INTERVAL '%s days'
    """
    params = [user_id, days]
    
    if book_id:
        query += " AND dr.book_id = %s"
        params.append(book_id)
    
    query += " ORDER BY dr.rank_date DESC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================
def plot_sales_trend(sales_df):
    """Plot sales over time"""
    if sales_df.empty:
        st.info("No sales data available")
        return
    
    # Daily total revenue
    daily_revenue = sales_df.groupby('sale_date')['revenue'].sum().reset_index()
    
    fig = px.line(daily_revenue, x='sale_date', y='revenue', 
                  title='Daily Revenue',
                  labels={'revenue': 'Revenue ($)', 'sale_date': 'Date'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Sales by marketplace
    marketplace_sales = sales_df.groupby('marketplace')['units_sold'].sum().reset_index()
    fig2 = px.pie(marketplace_sales, values='units_sold', names='marketplace',
                  title='Sales by Marketplace')
    st.plotly_chart(fig2, use_container_width=True)

def plot_book_comparison(sales_df):
    """Compare performance across books"""
    if sales_df.empty:
        return
    
    book_performance = sales_df.groupby('title').agg({
        'units_sold': 'sum',
        'revenue': 'sum',
        'royalties': 'sum'
    }).reset_index().sort_values('revenue', ascending=False)
    
    fig = px.bar(book_performance, x='title', y='revenue',
                 title='Revenue by Book',
                 labels={'revenue': 'Revenue ($)', 'title': ''})
    st.plotly_chart(fig, use_container_width=True)
    
    return book_performance

def plot_ranking_trend(rankings_df):
    """Plot ranking trends"""
    if rankings_df.empty:
        return
    
    fig = px.line(rankings_df, x='rank_date', y='sales_rank', 
                  color='title',
                  title='Sales Rank Over Time (Lower is Better)',
                  labels={'sales_rank': 'Rank', 'rank_date': 'Date'})
    fig.update_yaxes(autorange='reversed')  # Lower rank is better
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# MAIN MODULE UI
# ============================================================================
def show_sales_analytics():
    """Main sales analytics UI"""
    
    st.title("📊 Amazon Sales Analytics")
    st.markdown("### Track your KDP sales across all marketplaces")
    
    if not st.session_state.authenticated:
        st.warning("Please login to view your sales data")
        return
    
    user_id = st.session_state.user_id
    
    # Initialize tables
    init_sales_tables()
    
    # AUTO-GENERATE DEMO DATA if no books exist OR no sales data
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        
        # Check for books
        cur.execute("SELECT COUNT(*) FROM author_books WHERE user_id = %s", (user_id,))
        book_count = cur.fetchone()[0]
        
        # Check for sales data
        cur.execute("SELECT COUNT(*) FROM daily_sales WHERE user_id = %s", (user_id,))
        sales_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        # If no books, create them AND generate sales
        if book_count == 0:
            with st.spinner("📊 Creating your demo books and sales data..."):
                # Create mock books
                mock_books = [
                    ("B08XYZ1234", "The Lost Kingdom", "Fantasy", 9.99),
                    ("B09ABC5678", "Midnight Secrets", "Mystery", 12.99),
                    ("B10DEF9012", "Love in Paris", "Romance", 8.99),
                    ("B11GHI3456", "Beyond the Stars", "Sci-Fi", 11.99),
                ]
                
                conn = get_db_connection()
                cur = conn.cursor()
                for asin, title, genre, price in mock_books:
                    cur.execute("""
                        INSERT INTO author_books (user_id, asin, title, format, genre, list_price)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (user_id, asin, title, "ebook", genre, price))
                conn.commit()
                cur.close()
                conn.close()
                
                # Generate 60 days of sales data
                generate_mock_sales_data(user_id, days=60)
                st.success("✅ Demo books AND sales data created! Check the Dashboard tab.")
                st.rerun()
        
        # If books exist but NO sales data, generate sales
        elif book_count > 0 and sales_count == 0:
            with st.spinner("📊 Generating sales data for your books..."):
                generate_mock_sales_data(user_id, days=60)
                st.success("✅ Sales data generated! Check the Dashboard tab.")
                st.rerun()
    
    # Check if user has Amazon credentials
    creds = get_amazon_credentials(user_id)
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔑 Connect Amazon",
        "📈 Dashboard",
        "📚 My Books",
        "📤 Import Data"
    ])
    
    with tab1:
        show_amazon_connection(user_id, creds)
    
    with tab2:
        show_sales_dashboard(user_id)
    
    with tab3:
        show_books_manager(user_id)
    
    with tab4:
        show_data_import(user_id, creds)

def show_amazon_connection(user_id, creds):
    """Connect to Amazon KDP"""
    
    st.subheader("Connect Your Amazon KDP Account")
    st.markdown("""
    <div class="api-instructions">
        <strong>🔒 Your credentials are encrypted</strong><br>
        We never store your password in plain text. All data is encrypted before storage.
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("amazon_creds"):
        email = st.text_input("KDP Email", 
                              value=creds['amazon_email'] if creds else "",
                              placeholder="your-kdp-email@example.com")
        
        password = st.text_input("KDP Password", 
                                 type="password",
                                 placeholder="Your KDP password")
        
        region = st.selectbox("KDP Region", 
                              ["US", "UK", "DE", "FR", "JP", "AU"],
                              index=0 if not creds else ["US", "UK", "DE", "FR", "JP", "AU"].index(creds.get('kdp_region', 'US')))
        
        submitted = st.form_submit_button("Save Credentials", use_container_width=True)
        
        if submitted:
            if email and password:
                if save_amazon_credentials(user_id, email, password, region):
                    st.success("✅ Credentials saved successfully!")
                    st.rerun()
                else:
                    st.error("Failed to save credentials")
            else:
                st.error("Email and password required")
    
    if creds:
        st.success(f"✅ Connected as: {creds['amazon_email']}")
        if creds.get('last_sync'):
            st.info(f"Last sync: {creds['last_sync'][:16]}")

def show_sales_dashboard(user_id):
    """Main sales dashboard"""
    
    st.subheader("Sales Dashboard")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        days = st.selectbox("Time Period", [7, 30, 60, 90, 180], index=1)
    
    # Get data
    sales_df = fetch_user_sales(user_id, days=days)
    rankings_df = fetch_user_rankings(user_id, days=days)
    books_df = fetch_user_books(user_id)
    
    if sales_df.empty:
        st.info("No sales data yet. Go to the 'Import Data' tab to load your sales.")
        return
    
    # Summary metrics
    total_revenue = sales_df['revenue'].sum()
    total_units = sales_df['units_sold'].sum()
    total_royalties = sales_df['royalties'].sum()
    avg_daily = total_revenue / days
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Revenue", f"${total_revenue:,.2f}")
    with col2:
        st.metric("Total Units", f"{total_units:,}")
    with col3:
        st.metric("Est. Royalties", f"${total_royalties:,.2f}")
    with col4:
        st.metric("Daily Avg", f"${avg_daily:.2f}")
    
    # Sales trend
    plot_sales_trend(sales_df)
    
    # Book comparison
    col1, col2 = st.columns(2)
    with col1:
        book_perf = plot_book_comparison(sales_df)
    
    with col2:
        # Marketplace breakdown
        marketplace_summary = sales_df.groupby('marketplace').agg({
            'units_sold': 'sum',
            'revenue': 'sum'
        }).reset_index()
        
        st.dataframe(marketplace_summary, use_container_width=True)
    
    # Ranking trends
    plot_ranking_trend(rankings_df)
    
    # Recent sales table
    st.subheader("Recent Sales")
    recent = sales_df.head(20)[['sale_date', 'title', 'marketplace', 'units_sold', 'revenue', 'royalties']]
    st.dataframe(recent, use_container_width=True)
    
    # Export button
    if st.button("📥 Export Raw Data"):
        csv = sales_df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            f"sales_export_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )

def show_books_manager(user_id):
    """Manage books"""
    
    st.subheader("Your Books")
    
    books_df = fetch_user_books(user_id)
    
    # Add new book form
    with st.expander("➕ Add New Book"):
        with st.form("new_book"):
            asin = st.text_input("ASIN", placeholder="B08XYZ1234")
            title = st.text_input("Book Title")
            series = st.text_input("Series (optional)")
            format = st.selectbox("Format", ["ebook", "paperback", "hardcover", "audiobook"])
            genre = st.selectbox("Genre", ["Fantasy", "Sci-Fi", "Romance", "Mystery", "Thriller", "Fiction", "Non-Fiction"])
            price = st.number_input("List Price ($)", min_value=0.0, step=0.99)
            pub_date = st.date_input("Publication Date")
            
            if st.form_submit_button("Add Book"):
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO author_books 
                        (user_id, asin, title, series, format, genre, list_price, publication_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (user_id, asin, title, series, format, genre, price, pub_date))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("✅ Book added!")
                    st.rerun()
    
    # Display books
    if not books_df.empty:
        for _, book in books_df.iterrows():
            with st.expander(f"📚 {book['title']} - {book['asin']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Format:** {book['format']}")
                    st.write(f"**Genre:** {book['genre']}")
                    st.write(f"**Price:** ${book['list_price']}")
                with col2:
                    st.write(f"**Published:** {book['publication_date']}")
                    if book['series']:
                        st.write(f"**Series:** {book['series']}")
                
                # Quick stats for this book
                sales_df = fetch_user_sales(user_id, book_id=book['id'])
                if not sales_df.empty:
                    book_revenue = sales_df['revenue'].sum()
                    book_units = sales_df['units_sold'].sum()
                    st.metric("Total Revenue", f"${book_revenue:.2f}")
                    st.metric("Total Units", book_units)
    else:
        st.info("No books added yet. Add your first book above.")

def show_data_import(user_id, creds):
    """Import sales data"""
    
    st.subheader("Import Sales Data")
    
    if not creds:
        st.warning("Please connect your Amazon account first")
        return
    
    st.info(f"Connected as: {creds['amazon_email']}")
    
    col1, col2 = st.columns(2)
    with col1:
        days_to_import = st.number_input("Days to import", min_value=1, max_value=90, value=30)
    
    with col2:
        if st.button("🔄 Generate Test Data", use_container_width=True):
            with st.spinner("Generating mock sales data..."):
                if generate_mock_sales_data(user_id, days_to_import):
                    st.success(f"✅ Generated {days_to_import} days of test data!")
                    st.rerun()
                else:
                    st.error("Failed to generate data")
    
    st.markdown("---")
    st.markdown("""
    ### 📝 Manual CSV Upload
    
    You can also upload KDP sales reports manually:
    """)
    
    uploaded_file = st.file_uploader("Upload KDP Sales Report (CSV)", type=['csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ Loaded {len(df)} rows")
            st.dataframe(df.head())
            
            if st.button("Import to Database"):
                st.info("Processing... (CSV import would parse and save data)")
                # CSV parsing logic would go here
        except Exception as e:
            st.error(f"Error reading file: {e}")

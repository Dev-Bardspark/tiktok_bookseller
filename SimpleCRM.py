# SimpleCRM.py
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
# CONTACT FUNCTIONS
# ============================================================================
def save_contact(user_id, contact_data):
    """Save a contact to CRM"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        
        # Check if contact already exists by email
        if contact_data.get('email'):
            cur.execute("""
                SELECT id FROM crm_contacts 
                WHERE user_id = %s AND email = %s
            """, (user_id, contact_data['email']))
            existing = cur.fetchone()
            if existing:
                # Update existing
                cur.execute("""
                    UPDATE crm_contacts 
                    SET first_name = %s, last_name = %s, social_handle = %s, 
                        notes = %s, updated_at = %s
                    WHERE id = %s
                """, (
                    contact_data.get('first_name'),
                    contact_data.get('last_name'),
                    contact_data.get('social_handle'),
                    contact_data.get('notes'),
                    datetime.now(),
                    existing[0]
                ))
                conn.commit()
                return existing[0]
        
        # Insert new contact
        cur.execute("""
            INSERT INTO crm_contacts 
            (user_id, contact_type, first_name, last_name, email, social_handle, source, notes, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            contact_data.get('contact_type', 'arc_reader'),
            contact_data.get('first_name'),
            contact_data.get('last_name'),
            contact_data.get('email'),
            contact_data.get('social_handle'),
            contact_data.get('source', 'Manual Entry'),
            contact_data.get('notes', ''),
            datetime.now(),
            datetime.now()
        ))
        
        contact_id = cur.fetchone()[0]
        conn.commit()
        return contact_id
        
    except Exception as e:
        st.error(f"Error saving contact: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_contacts(user_id, contact_type=None):
    """Get all contacts for a user"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if contact_type and contact_type != "All":
            cur.execute("""
                SELECT * FROM crm_contacts 
                WHERE user_id = %s AND contact_type = %s
                ORDER BY created_at DESC
            """, (user_id, contact_type))
        else:
            cur.execute("""
                SELECT * FROM crm_contacts 
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Error loading contacts: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_contact(user_id, contact_id):
    """Get a single contact"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM crm_contacts 
            WHERE user_id = %s AND id = %s
        """, (user_id, contact_id))
        
        return cur.fetchone()
    except Exception as e:
        st.error(f"Error loading contact: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def update_contact(user_id, contact_id, updates):
    """Update a contact"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        
        set_clause = []
        params = []
        for key, value in updates.items():
            if value is not None:
                set_clause.append(f"{key} = %s")
                params.append(value)
        
        if not set_clause:
            return False
        
        set_clause.append("updated_at = %s")
        params.append(datetime.now())
        params.append(user_id)
        params.append(contact_id)
        
        cur.execute(f"""
            UPDATE crm_contacts 
            SET {', '.join(set_clause)}
            WHERE user_id = %s AND id = %s
        """, params)
        
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        st.error(f"Error updating contact: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def delete_contact(user_id, contact_id):
    """Delete a contact"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM crm_contacts 
            WHERE user_id = %s AND id = %s
        """, (user_id, contact_id))
        
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        st.error(f"Error deleting contact: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ============================================================================
# LIST FUNCTIONS
# ============================================================================
def create_list(user_id, list_name):
    """Create a new contact list"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO crm_lists (user_id, list_name, created_at)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (user_id, list_name, datetime.now()))
        
        list_id = cur.fetchone()[0]
        conn.commit()
        return list_id
    except Exception as e:
        st.error(f"Error creating list: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_lists(user_id):
    """Get all lists for a user"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT l.*, COUNT(ml.contact_id) as contact_count
            FROM crm_lists l
            LEFT JOIN crm_list_members ml ON l.id = ml.list_id
            WHERE l.user_id = %s
            GROUP BY l.id
            ORDER BY l.created_at DESC
        """, (user_id,))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Error loading lists: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def add_to_list(user_id, contact_id, list_id):
    """Add a contact to a list"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO crm_list_members (contact_id, list_id, added_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (contact_id, list_id) DO NOTHING
        """, (contact_id, list_id, datetime.now()))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error adding to list: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def remove_from_list(user_id, contact_id, list_id):
    """Remove a contact from a list"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM crm_list_members 
            WHERE contact_id = %s AND list_id = %s
        """, (contact_id, list_id))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error removing from list: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ============================================================================
# EMAIL FUNCTIONS
# ============================================================================
def send_email(to_email, subject, html_content):
    """Send email using SMTP (configure with your email provider)"""
    try:
        # You'll need to add these to your secrets
        smtp_server = st.secrets.get("email", {}).get("smtp_server", "smtp.gmail.com")
        smtp_port = st.secrets.get("email", {}).get("smtp_port", 587)
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False

def log_email(user_id, contact_id, subject, content):
    """Log an email in history"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO crm_email_history (user_id, contact_id, subject, content, sent_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, contact_id, subject, content, datetime.now()))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error logging email: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_email_history(user_id, contact_id):
    """Get email history for a contact"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM crm_email_history 
            WHERE user_id = %s AND contact_id = %s
            ORDER BY sent_at DESC
        """, (user_id, contact_id))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Error loading email history: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ============================================================================
# CRM UI PAGES
# ============================================================================
def render_contacts_page():
    """Main contacts list view"""
    st.title("📇 My Contacts")
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.warning("Please login to view contacts")
        return
    
    # Contact type filter
    col1, col2 = st.columns([3, 1])
    with col1:
        contact_type = st.selectbox(
            "Filter by type",
            options=["All", "arc_reader", "influencer", "press", "author", "beta_reader"],
            format_func=lambda x: {
                "All": "📋 All Contacts",
                "arc_reader": "📚 ARC Readers",
                "influencer": "📢 Influencers",
                "press": "📰 Press",
                "author": "✍️ Authors",
                "beta_reader": "🔍 Beta Readers"
            }.get(x, x)
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add New", use_container_width=True):
            st.session_state.crm_page = "add_contact"
            st.rerun()
    
    # Load contacts
    contacts = get_contacts(user_id, None if contact_type == "All" else contact_type)
    
    if not contacts:
        st.info("No contacts yet. Add some from the ARC Finder or click 'Add New' above.")
        return
    
    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Contacts", len(contacts))
    with col2:
        arc_count = sum(1 for c in contacts if c['contact_type'] == 'arc_reader')
        st.metric("ARC Readers", arc_count)
    with col3:
        inf_count = sum(1 for c in contacts if c['contact_type'] == 'influencer')
        st.metric("Influencers", inf_count)
    with col4:
        press_count = sum(1 for c in contacts if c['contact_type'] == 'press')
        st.metric("Press", press_count)
    
    st.markdown("---")
    
    # Contacts table
    for contact in contacts:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
            
            with col1:
                name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                if not name:
                    name = contact.get('email', 'No name')[:20]
                st.markdown(f"**{name}**")
                if contact.get('social_handle'):
                    st.caption(f"@{contact['social_handle']}")
            
            with col2:
                contact_type_display = {
                    "arc_reader": "📚 ARC Reader",
                    "influencer": "📢 Influencer",
                    "press": "📰 Press",
                    "author": "✍️ Author",
                    "beta_reader": "🔍 Beta Reader"
                }.get(contact['contact_type'], contact['contact_type'])
                st.markdown(contact_type_display)
            
            with col3:
                if contact.get('email'):
                    st.markdown(f"📧 {contact['email'][:20]}...")
                else:
                    st.markdown("—")
            
            with col4:
                if st.button("👁️ View", key=f"view_{contact['id']}", use_container_width=True):
                    st.session_state.crm_contact_id = contact['id']
                    st.session_state.crm_page = "view_contact"
                    st.rerun()
            
            with col5:
                if st.button("🗑️", key=f"del_{contact['id']}", use_container_width=True):
                    if delete_contact(user_id, contact['id']):
                        st.success("Contact deleted")
                        st.rerun()
            
            st.markdown("---")

def render_add_contact_page():
    """Add a new contact manually"""
    st.title("➕ Add New Contact")
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.warning("Please login to add contacts")
        return
    
    with st.form("add_contact_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            contact_type = st.selectbox(
                "Contact Type *",
                options=["arc_reader", "influencer", "press", "author", "beta_reader"],
                format_func=lambda x: {
                    "arc_reader": "📚 ARC Reader",
                    "influencer": "📢 Influencer",
                    "press": "📰 Press",
                    "author": "✍️ Author",
                    "beta_reader": "🔍 Beta Reader"
                }[x]
            )
            
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            email = st.text_input("Email")
        
        with col2:
            social_handle = st.text_input("Social Handle (without @)")
            source = st.text_input("Source", value="Manual Entry")
            notes = st.text_area("Notes", height=100)
        
        submitted = st.form_submit_button("💾 Save Contact", use_container_width=True)
        
        if submitted:
            if not contact_type:
                st.error("Contact type is required")
                return
            
            contact_data = {
                'contact_type': contact_type,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'social_handle': social_handle,
                'source': source,
                'notes': notes
            }
            
            contact_id = save_contact(user_id, contact_data)
            if contact_id:
                st.success("Contact saved successfully!")
                st.session_state.crm_page = "contacts"
                st.rerun()
    
    if st.button("← Back to Contacts"):
        st.session_state.crm_page = "contacts"
        st.rerun()

def render_view_contact_page():
    """View and edit a single contact"""
    user_id = st.session_state.get('user_id')
    contact_id = st.session_state.get('crm_contact_id')
    
    if not user_id or not contact_id:
        st.session_state.crm_page = "contacts"
        st.rerun()
        return
    
    contact = get_contact(user_id, contact_id)
    if not contact:
        st.error("Contact not found")
        st.session_state.crm_page = "contacts"
        st.rerun()
        return
    
    st.title(f"👤 {contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or "Contact Details")
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📋 Details", "📧 Email History", "📝 Lists"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Contact Information**")
            st.markdown(f"**Type:** {contact['contact_type']}")
            st.markdown(f"**Email:** {contact.get('email', '—')}")
            st.markdown(f"**Social:** @{contact.get('social_handle', '—')}")
            st.markdown(f"**Source:** {contact.get('source', '—')}")
        
        with col2:
            st.markdown("**Additional Info**")
            st.markdown(f"**Added:** {contact['created_at'].strftime('%Y-%m-%d') if contact.get('created_at') else '—'}")
            st.markdown(f"**Last Updated:** {contact['updated_at'].strftime('%Y-%m-%d') if contact.get('updated_at') else '—'}")
            st.markdown(f"**Notes:** {contact.get('notes', '—')}")
        
        # Edit form
        with st.expander("✏️ Edit Contact"):
            with st.form("edit_contact_form"):
                new_first = st.text_input("First Name", value=contact.get('first_name', ''))
                new_last = st.text_input("Last Name", value=contact.get('last_name', ''))
                new_email = st.text_input("Email", value=contact.get('email', ''))
                new_social = st.text_input("Social Handle", value=contact.get('social_handle', ''))
                new_notes = st.text_area("Notes", value=contact.get('notes', ''))
                
                if st.form_submit_button("Update Contact"):
                    updates = {}
                    if new_first != contact.get('first_name'):
                        updates['first_name'] = new_first
                    if new_last != contact.get('last_name'):
                        updates['last_name'] = new_last
                    if new_email != contact.get('email'):
                        updates['email'] = new_email
                    if new_social != contact.get('social_handle'):
                        updates['social_handle'] = new_social
                    if new_notes != contact.get('notes'):
                        updates['notes'] = new_notes
                    
                    if updates:
                        if update_contact(user_id, contact_id, updates):
                            st.success("Contact updated")
                            st.rerun()
    
    with tab2:
        # Email history
        history = get_email_history(user_id, contact_id)
        if history:
            for email in history:
                with st.expander(f"📧 {email['subject']} - {email['sent_at'].strftime('%Y-%m-%d %H:%M')}"):
                    st.markdown(email['content'])
        else:
            st.info("No emails sent to this contact yet")
        
        # Send email
        with st.expander("✉️ Send Email"):
            with st.form("send_email_form"):
                subject = st.text_input("Subject")
                content = st.text_area("Message", height=200)
                
                if st.form_submit_button("Send Email"):
                    if contact.get('email'):
                        if send_email(contact['email'], subject, content):
                            log_email(user_id, contact_id, subject, content)
                            st.success("Email sent!")
                            st.rerun()
                    else:
                        st.error("This contact has no email address")
    
    with tab3:
        # List management
        lists = get_lists(user_id)
        
        if lists:
            current_list_ids = []
            # TODO: Get current list memberships
            
            for lst in lists:
                is_member = False  # Check if contact is in this list
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{lst['list_name']}** ({lst['contact_count']} contacts)")
                with col2:
                    if is_member:
                        if st.button("Remove", key=f"remove_{lst['id']}"):
                            remove_from_list(user_id, contact_id, lst['id'])
                            st.rerun()
                    else:
                        if st.button("Add", key=f"add_{lst['id']}"):
                            add_to_list(user_id, contact_id, lst['id'])
                            st.rerun()
        else:
            st.info("No lists created yet")
            
            with st.expander("➕ Create New List"):
                list_name = st.text_input("List Name")
                if st.button("Create List"):
                    if list_name:
                        create_list(user_id, list_name)
                        st.rerun()
    
    if st.button("← Back to Contacts"):
        st.session_state.crm_page = "contacts"
        st.rerun()

def render_lists_page():
    """Manage contact lists"""
    st.title("📋 Contact Lists")
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.warning("Please login to manage lists")
        return
    
    # Create new list
    with st.form("new_list_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            list_name = st.text_input("New List Name", placeholder="e.g., Book Launch Team")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Create List", use_container_width=True)
        
        if submitted and list_name:
            list_id = create_list(user_id, list_name)
            if list_id:
                st.success(f"List '{list_name}' created!")
                st.rerun()
    
    st.markdown("---")
    
    # Show existing lists
    lists = get_lists(user_id)
    
    if not lists:
        st.info("No lists yet. Create one above!")
        return
    
    for lst in lists:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{lst['list_name']}**")
                st.caption(f"{lst['contact_count']} contacts")
            
            with col2:
                if st.button("👁️ View", key=f"view_list_{lst['id']}"):
                    st.session_state.crm_list_id = lst['id']
                    st.session_state.crm_page = "view_list"
                    st.rerun()
            
            with col3:
                # TODO: Delete list functionality
                st.button("🗑️", key=f"del_list_{lst['id']}")
            
            st.markdown("---")

# ============================================================================
# MAIN CRM RENDER FUNCTION
# ============================================================================
def render_crm():
    """Main CRM router"""
    
    # Initialize CRM page state
    if 'crm_page' not in st.session_state:
        st.session_state.crm_page = "contacts"
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 📇 CRM")
        
        if st.button("📋 Contacts", use_container_width=True):
            st.session_state.crm_page = "contacts"
            st.rerun()
        
        if st.button("📋 Lists", use_container_width=True):
            st.session_state.crm_page = "lists"
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Quick Add")
        
        # Quick add from sidebar
        with st.form("quick_add"):
            quick_type = st.selectbox(
                "Type",
                options=["arc_reader", "influencer", "press", "author", "beta_reader"],
                format_func=lambda x: {
                    "arc_reader": "📚 ARC Reader",
                    "influencer": "📢 Influencer",
                    "press": "📰 Press",
                    "author": "✍️ Author",
                    "beta_reader": "🔍 Beta Reader"
                }[x],
                label_visibility="collapsed"
            )
            quick_email = st.text_input("Email", placeholder="Email", label_visibility="collapsed")
            quick_name = st.text_input("Name", placeholder="Name", label_visibility="collapsed")
            
            if st.form_submit_button("➕ Quick Add", use_container_width=True):
                if quick_email and quick_name:
                    name_parts = quick_name.split(' ', 1)
                    first = name_parts[0]
                    last = name_parts[1] if len(name_parts) > 1 else ''
                    
                    contact_data = {
                        'contact_type': quick_type,
                        'first_name': first,
                        'last_name': last,
                        'email': quick_email,
                        'source': 'Quick Add'
                    }
                    
                    contact_id = save_contact(st.session_state.user_id, contact_data)
                    if contact_id:
                        st.success("Contact added!")
                        st.rerun()
    
    # Route to appropriate page
    if st.session_state.crm_page == "contacts":
        render_contacts_page()
    elif st.session_state.crm_page == "add_contact":
        render_add_contact_page()
    elif st.session_state.crm_page == "view_contact":
        render_view_contact_page()
    elif st.session_state.crm_page == "lists":
        render_lists_page()
    else:
        render_contacts_page()

# For direct testing
if __name__ == "__main__":
    render_crm()

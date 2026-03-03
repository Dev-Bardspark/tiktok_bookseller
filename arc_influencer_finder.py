# ============================================================================
# SAVE BUTTON - Saves to both Saved Readers AND CRM
# ============================================================================
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 3])
with col1:
    if st.button("❤️ Save", key=f"save_{advocate['id']}"):
        if st.session_state.get('authenticated'):
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                try:
                    # 1. Save to saved_readers table
                    cur.execute("""
                        INSERT INTO user_saved_arc_readers (user_id, reader_id, saved_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, reader_id) DO NOTHING
                    """, (st.session_state.user_id, advocate['id'], datetime.now()))
                    
                    # 2. Save to CRM contacts table
                    # Parse name from display_name
                    first_name = ''
                    last_name = ''
                    if advocate.get('display_name'):
                        name_parts = advocate['display_name'].split()
                        first_name = name_parts[0] if name_parts else ''
                        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                    
                    cur.execute("""
                        INSERT INTO crm_contacts 
                        (user_id, contact_type, first_name, last_name, email, social_handle, source, notes, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, email) DO UPDATE SET
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            social_handle = EXCLUDED.social_handle,
                            updated_at = EXCLUDED.updated_at
                        WHERE crm_contacts.email IS NOT NULL
                    """, (
                        st.session_state.user_id,
                        'arc_reader',
                        first_name,
                        last_name,
                        advocate.get('email'),
                        advocate.get('username'),
                        f"ARC Finder - {advocate.get('username', '')}",
                        f"Bio: {advocate.get('bio', '')[:200]}",
                        datetime.now(),
                        datetime.now()
                    ))
                    
                    conn.commit()
                    
                    # Update session state for saved_readers
                    if 'saved_readers' not in st.session_state:
                        st.session_state.saved_readers = []
                    if not any(r['id'] == advocate['id'] for r in st.session_state.saved_readers):
                        st.session_state.saved_readers.append(advocate)
                    
                    st.success(f"✅ @{advocate['username']} saved to CRM and Your List!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    cur.close()
                    conn.close()
        else:
            st.warning("Please login to save readers")

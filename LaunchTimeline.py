# LaunchTimeline.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

def show_timeline_widget():
    """Display the launch timeline widget on the dashboard"""
    
    # Initialize session state for timeline
    if 'launch_date' not in st.session_state:
        # Default to 6 months from now
        st.session_state.launch_date = datetime.now().date() + timedelta(days=180)
    
    if 'timeline_tasks' not in st.session_state:
        st.session_state.timeline_tasks = {}
    
    # Timeline header with launch date picker
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("### 📅 Your Book Launch Timeline")
    
    with col2:
        # Launch date picker
        new_launch_date = st.date_input(
            "Launch Date",
            value=st.session_state.launch_date,
            min_value=datetime.now().date() + timedelta(days=30),
            key="launch_date_picker"
        )
        if new_launch_date != st.session_state.launch_date:
            st.session_state.launch_date = new_launch_date
            st.rerun()
    
    with col3:
        # Days until launch
        days_until = (st.session_state.launch_date - datetime.now().date()).days
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 10px; border-radius: 10px; text-align: center;">
            <h3 style="color: white; margin: 0;">{days_until}</h3>
            <p style="color: white; margin: 0;">Days to Go</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Calculate phase dates based on launch date
    phases = calculate_phases(st.session_state.launch_date)
    
    # Display phase progress
    display_phase_progress(phases)
    
    # Quick task view (collapsible)
    with st.expander("📋 View All Tasks by Phase", expanded=False):
        display_all_tasks(phases)


def calculate_phases(launch_date):
    """Calculate all phase dates based on launch date"""
    today = datetime.now().date()
    
    phases = {
        "Build Audience": {
            "start": launch_date - timedelta(days=180),
            "end": launch_date - timedelta(days=90),
            "color": "#667eea",
            "tasks": [
                "Post 3-5x/week about books you love",
                "Save trending sounds in your genre",
                "Engage with other BookTokers daily"
            ]
        },
        "ARC Recruitment": {
            "start": launch_date - timedelta(days=120),
            "end": launch_date - timedelta(days=60),
            "color": "#764ba2",
            "tasks": [
                "Open ARC reader applications",
                "Start your email list",
                "Research competitor launches"
            ]
        },
        "Teaser Phase": {
            "start": launch_date - timedelta(days=90),
            "end": launch_date - timedelta(days=30),
            "color": "#f093fb",
            "tasks": [
                "First teaser content",
                "Send ARCs to readers",
                "Create content bank (20-30 videos)"
            ]
        },
        "Influencer Outreach": {
            "start": launch_date - timedelta(days=60),
            "end": launch_date - timedelta(days=30),
            "color": "#f5576c",
            "tasks": [
                "Contact 50+ influencers",
                "Send books to interested influencers",
                "Schedule pre-launch posts"
            ]
        },
        "Pre-Launch Push": {
            "start": launch_date - timedelta(days=30),
            "end": launch_date,
            "color": "#4facfe",
            "tasks": [
                "Open pre-orders",
                "Track ARC reviews",
                "Create launch week content",
                "Email your list weekly"
            ]
        },
        "Launch Week": {
            "start": launch_date,
            "end": launch_date + timedelta(days=7),
            "color": "#43e97b",
            "tasks": [
                "Post launch day video",
                "Email your list",
                "DM influencers",
                "Engage with comments"
            ]
        },
        "Post-Launch": {
            "start": launch_date + timedelta(days=7),
            "end": launch_date + timedelta(days=30),
            "color": "#38f9d7",
            "tasks": [
                "Share reviews",
                "Thank you video",
                "Week 1 wrap-up",
                "Plan next launch"
            ]
        }
    }
    
    # Add status to each phase
    for phase, data in phases.items():
        if today > data["end"]:
            data["status"] = "✅ Complete"
            data["progress"] = 1.0
        elif today < data["start"]:
            data["status"] = "⏳ Upcoming"
            data["progress"] = 0.0
        else:
            # Currently in this phase - calculate rough progress
            total_days = (data["end"] - data["start"]).days
            days_in = (today - data["start"]).days
            data["progress"] = min(days_in / total_days, 1.0)
            data["status"] = "🚀 In Progress"
    
    return phases


def display_phase_progress(phases):
    """Show visual timeline and current phase"""
    
    # Create dataframe for timeline visualization
    df = pd.DataFrame([
        {
            "Phase": phase,
            "Start": data["start"],
            "End": data["end"],
            "Status": data["status"],
            "Progress": data["progress"]
        }
        for phase, data in phases.items()
    ])
    
    # Create horizontal bar chart timeline
    fig = px.timeline(
        df, 
        x_start="Start", 
        x_end="End", 
        y="Phase",
        color="Status",
        color_discrete_map={
            "✅ Complete": "#00C851",
            "🚀 In Progress": "#ffbb33",
            "⏳ Upcoming": "#33b5e5"
        },
        title="Your Launch Timeline"
    )
    
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=30, b=0),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Current phase highlight
    current_phase = next((phase for phase, data in phases.items() if data["status"] == "🚀 In Progress"), None)
    
    if current_phase:
        st.info(f"🎯 **Currently in:** {current_phase}")
        
        # Show progress bar for current phase
        phase_data = phases[current_phase]
        st.progress(phase_data["progress"])
        st.caption(f"Phase progress: {int(phase_data['progress'] * 100)}%")
    else:
        # Check if all done or not started
        if all(data["status"] == "✅ Complete" for data in phases.values()):
            st.success("🎉 Congratulations! You've completed all launch phases!")
        else:
            st.info("⏳ Your launch journey hasn't started yet. First phase begins soon!")


def display_all_tasks(phases):
    """Show all tasks with checkboxes"""
    
    # Create tabs for each phase
    phase_names = list(phases.keys())
    tabs = st.tabs(phase_names)
    
    for i, (phase_name, tab) in enumerate(zip(phase_names, tabs)):
        with tab:
            phase_data = phases[phase_name]
            
            # Phase header
            st.markdown(f"### {phase_name}")
            st.caption(f"{phase_data['start'].strftime('%b %d')} - {phase_data['end'].strftime('%b %d')}")
            
            # Tasks with checkboxes
            for j, task in enumerate(phase_data["tasks"]):
                task_key = f"task_{phase_name}_{j}"
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{task}**")
                with col2:
                    # Initialize task state if not exists
                    if task_key not in st.session_state.timeline_tasks:
                        st.session_state.timeline_tasks[task_key] = False
                    
                    # Checkbox
                    completed = st.checkbox(
                        "Done", 
                        value=st.session_state.timeline_tasks[task_key],
                        key=f"cb_{task_key}"
                    )
                    st.session_state.timeline_tasks[task_key] = completed
            
            # Phase completion summary
            phase_tasks = [st.session_state.timeline_tasks.get(f"task_{phase_name}_{j}", False) 
                          for j in range(len(phase_data["tasks"]))]
            if phase_tasks:
                phase_complete = sum(phase_tasks) / len(phase_tasks)
                st.progress(phase_complete)
                st.caption(f"Phase completion: {int(phase_complete * 100)}%")


def get_upcoming_tasks(phases, days=7):
    """Get tasks due in the next X days"""
    today = datetime.now().date()
    upcoming = []
    
    for phase_name, phase_data in phases.items():
        if phase_data["start"] <= today + timedelta(days=days) and phase_data["end"] >= today:
            # This phase is active or starting soon
            for j, task in enumerate(phase_data["tasks"]):
                task_key = f"task_{phase_name}_{j}"
                if not st.session_state.timeline_tasks.get(task_key, False):
                    upcoming.append({
                        "phase": phase_name,
                        "task": task,
                        "due": phase_data["end"]
                    })
    
    return upcoming[:5]  # Return top 5


# Optional: Mini widget for dashboard sidebar
def show_upcoming_widget():
    """Show upcoming tasks in a small widget"""
    phases = calculate_phases(st.session_state.launch_date)
    upcoming = get_upcoming_tasks(phases)
    
    if upcoming:
        st.markdown("### ⏰ Coming Up This Week")
        for item in upcoming:
            days_left = (item["due"] - datetime.now().date()).days
            st.markdown(f"- {item['task']} _({days_left} days left)_")
    else:
        st.markdown("### ✅ All caught up!")
        st.caption("No pending tasks this week")

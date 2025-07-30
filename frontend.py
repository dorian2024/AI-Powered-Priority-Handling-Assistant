import streamlit as st
from datetime import datetime
from google_integration import get_calendar_service, get_existing_schedule
from app import process_task

#---------------------------------------------------------
# Page Config
#---------------------------------------------------------
st.set_page_config(page_title="Priority ToDo + Google Calendar", layout="centered")

#---------------------------------------------------------
# Custom Styling
#---------------------------------------------------------
st.markdown(
    """
    <style>
        body {
            background-color: #0d1b2a;
            color: #e0e0e0;
            font-family: 'Segoe UI', sans-serif;
        }
        .main-title {
            text-align: center;
            font-size: 2.8rem;
            font-weight: bold;
            background: linear-gradient(90deg, #a7c7e7, #ffd6a5, #caffbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }
        .subtitle {
            text-align: center;
            font-size: 1.2rem;
            opacity: 0.85;
            margin-bottom: 2rem;
        }
        /* Event cards */
        .event-item {
            background: #1b263b;
            color: #f0f0f0;
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            border-left: 5px solid #444;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            transition: 0.2s;
        }
        .event-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }
        /* Pastel Priority Colors */
        .high-priority { border-left-color: #ffadad; }
        .medium-priority { border-left-color: #ffd6a5; }
        .low-priority { border-left-color: #a7c7e7; }
        
        /* Task panel */
        .task-panel {
            background: #1b263b;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            margin-bottom: 2rem;
        }
        input, textarea {
            background-color: #0d1b2a !important;
            color: #f5f5f5 !important;
            border: 1px solid #444 !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

#---------------------------------------------------------
# Header
#---------------------------------------------------------
st.markdown('<div class="main-title">Prioritise Yourself</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Your personal priority handling AI agent</div>', unsafe_allow_html=True)

#---------------------------------------------------------
# Task Input Section (FIRST)
#---------------------------------------------------------
#st.markdown('<div class="task-panel">', unsafe_allow_html=True)
st.subheader("Add a New Task")

task_title = st.text_input("Enter task:", placeholder="What needs to be done?")

if st.button("Process Task"):
    if not task_title.strip():
        st.error("Please enter a task first!")
    else:
        with st.spinner("Analyzing task and scheduling..."):
            response = process_task(task_title)

        event_status = response.get("event_status", {})
        if event_status.get("success"):
            st.success(f"Event created! [Open in Calendar]({event_status.get('link')})")
        else:
            st.warning(f"Could not create event: {event_status.get('error', 'Unknown error')}")

st.markdown('</div>', unsafe_allow_html=True)

#---------------------------------------------------------
# Upcoming Events Section (SECOND)
#---------------------------------------------------------
st.subheader("Upcoming Events")

try:
    service = get_calendar_service()
    calendar_events = get_existing_schedule(service, lookahead_days=7)
except:
    st.warning("Unable to connect to Google Calendar.")
    calendar_events = []

if not calendar_events:
    st.info("No upcoming events found.")
else:
    def get_priority(event):
        title = event["title"].lower()
        if any(word in title for word in ["urgent", "important", "meeting", "exam", "assignment", "tonight", "boss"]):
            return "high"
        elif any(word in title for word in ["review", "call", "discussion"]):
            return "medium"
        return "low"
    
    priorities = {
        "high": "High Priority",
        "medium": "Medium Priority",
        "low": "Low Priority"
    }

    for priority_level, priority_name in priorities.items():
        events = [e for e in calendar_events if get_priority(e) == priority_level]
        if events:
            st.markdown(f"### {priority_name}")
            for event in events:
                start_time = event["start"].strftime("%b %d, %I:%M %p")
                end_time = event["end"].strftime("%I:%M %p")
                st.markdown(f"""
                <div class="event-item {priority_level}-priority">
                    <strong>{event['title']}</strong><br>
                    <small>{start_time} - {end_time}</small>
                </div>
                """, unsafe_allow_html=True)

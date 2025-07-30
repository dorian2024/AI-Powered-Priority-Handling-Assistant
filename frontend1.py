import streamlit as st
from datetime import datetime
from google_integration import (
    get_calendar_service,
    get_existing_schedule,
    add_task_to_calendar
)
from app import process_task

#---------------------------------------------------------
# Page Config
#---------------------------------------------------------
st.set_page_config(page_title="Priority AI Assistant", layout="wide")

#---------------------------------------------------------
# Custom Styling with Animated Gradient
#---------------------------------------------------------
st.markdown(
    """
    <style>
        body {
            background-color: #0d1b2a;
            color: #e0e0e0;
            font-family: 'Segoe UI', sans-serif;
        }

        /* Animated Gradient Title */
        .main-title {
            text-align: center;
            font-size: 3rem;
            font-weight: bold;
            background: linear-gradient(270deg, #9bbcff, #ffd6a5, #baffc9);
            background-size: 600% 600%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientShift 12s ease infinite;
            margin-bottom: 0.3rem;
        }
        @keyframes gradientShift {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }

        .subtitle {
            text-align: center;
            font-size: 1.1rem;
            opacity: 0.85;
            margin-bottom: 2rem;
        }

        /* Event Cards */
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
        .high-priority { border-left-color: #ffadad; }   /* Pastel red */
        .medium-priority { border-left-color: #ffd6a5; } /* Pastel yellow */
        .low-priority { border-left-color: #a7c7e7; }    /* Pastel blue */

        /* Right Panel Inputs */
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
st.markdown('<div class="subtitle">Your personal AI assistant for tasks and scheduling</div>', unsafe_allow_html=True)

#---------------------------------------------------------
# Layout: Two Panels
#---------------------------------------------------------
col1, col2 = st.columns([2, 1])

# =============================
# LEFT PANEL: Upcoming Events
# =============================
with col1:
    st.subheader("Upcoming Events")

    try:
        service = get_calendar_service()
        calendar_events = get_existing_schedule(service, lookahead_days=7)
    except:
        calendar_events = []

    if not calendar_events:
        st.info("No upcoming events found.")
    else:
        def get_priority(event):
            title = event["title"].lower()
            if any(word in title for word in ["urgent", "important", "meeting", "exam"]):
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

# =============================
# RIGHT PANEL: Task Input & Quick Stats
# =============================
with col2:
    st.subheader("Create New Task")

    task_title = st.text_input("Task Title", placeholder="Describe the task here...")

    if st.button("Add Task"):
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

    # Quick Stats Section
    if calendar_events:
        st.markdown("---")
        st.subheader("Quick Stats")
        total_events = len(calendar_events)
        next_event = calendar_events[0]["start"].strftime("%b %d, %I:%M %p")
        col_a, col_b = st.columns(2)
        col_a.metric("Total Events", total_events)
        col_b.metric("Next Event", next_event)

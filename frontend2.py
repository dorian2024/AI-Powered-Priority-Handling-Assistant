import streamlit as st
from datetime import datetime, timedelta
from google_integration import (
    get_calendar_service,
    get_existing_schedule,
    add_task_to_calendar
)
from app import process_task, smart_reasoning_engine

st.set_page_config(page_title="Ascend", layout="centered")

# --- Custom CSS for Perfect Centering ---
st.markdown(
    """
    <style>
        /* Remove default Streamlit padding */
        .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
        }
        /* Center the whole page */
        body, html, [data-testid="stAppViewContainer"] {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        /* Nice central box */
        .center-box {
            text-align: center;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            width: 450px;
            max-width: 90%;
        }
        /* Center text in input */
        .stTextInput > div > div > input {
            text-align: center;
            font-size: 18px;
        }
        div.stButton > button {
            display: block;
            margin: 15px auto;
            font-size: 18px;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

with st.container():
    st.markdown('<div class="center-box">', unsafe_allow_html=True)
    st.title("Ascend.")
    st.subheader("Where your priorities take flight")

    task_title = st.text_input("Enter a new task:")
    submit = st.button("Process Task")
    st.markdown('</div>', unsafe_allow_html=True)

if submit:
    if not task_title.strip():
        st.error("⚠️ Please enter a task first!")
    else:
        with st.spinner("Analyzing and scheduling your task..."):
            # 1️⃣ Get calendar events
            service = get_calendar_service()
            calendar_events = get_existing_schedule(service, lookahead_days=7)

            # 2️⃣ Process the task
            task_data = process_task(task_title)
            intent = task_data.get("intent")
            entities = task_data.get("entities", {})

            # 3️⃣ Compute reasoning
            reasoning_result = smart_reasoning_engine(intent, entities, calendar_events)
            st.subheader("🔍 Reasoning")
            st.write(reasoning_result["reasoning"])

            # 4️⃣ Schedule if needed
            if reasoning_result["schedule_on_calendar"]:
                event_status = add_task_to_calendar(service, task_title)
                if event_status.get("success"):
                    st.success(f"✅ Event created! [Open in Calendar]({event_status.get('link')})")
                else:
                    st.warning(f"⚠️ Could not create event: {event_status.get('error', 'Unknown error')}")
            else:
                st.info("ℹ️ Task logged but not scheduled on calendar (priority too low).")

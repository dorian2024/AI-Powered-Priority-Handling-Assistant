
#this file contains the API code to connect the models and the front end 

#---------------------------------------------------------
#import libraries
#---------------------------------------------------------
from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import spacy
import sqlite3
from db_management import save_to_db, process_user_command
import re
from datetime import datetime, timedelta
import dateparser
from google_integration import get_calendar_service, list_upcoming_events, add_task_to_calendar, get_existing_schedule
#---------------------------------------------------------
# connect to database
#---------------------------------------------------------
DB_NAME = "tasks.db"
# Connect to the database
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Create the table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT,
    deadline TEXT,
    priority TEXT,
    location TEXT,
    recurrence TEXT,
    duration TEXT,
    intent TEXT
)
""")
conn.commit()
conn.close()


#---------------------------------------------------------
# load models
#---------------------------------------------------------
intent_clf = joblib.load("models/intent_classifier.pkl")
entity_clf = spacy.load("models/entity_clf")


#---------------------------------------------------------
# Initialize FastAPI
#---------------------------------------------------------
app = FastAPI(title="Task NLP API")

#---------------------------------------------------------
# Input schema
#---------------------------------------------------------
class UserCommand(BaseModel):
    command: str


#---------------------------------------------------------
# helper functions
#---------------------------------------------------------
#extract priority
def extract_priority_fallback(text):
    priorities = ["high", "low", "urgent", "critical", "medium"]
    for p in priorities:
        if p in text.lower():
            return p
    return None

# infer priority in case its not given in statement
def infer_priority(task_description):
    score = 0
    task_lower = task_description.lower()

    # 1. Detect explicit times (e.g., 11pm, 7:30am) 
    time_match = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s?(am|pm)\b', task_lower)
    if time_match:
        score += 50  # Time-bound = high priority

    # 2. Detect dates / deadlines
    date_obj = dateparser.parse(task_lower, settings={'PREFER_DATES_FROM': 'future'})
    if date_obj:
        delta = date_obj - datetime.now()
        if delta.days < 1:
            score += 30  # Due within 24 hours
        elif delta.days < 3:
            score += 20

    # 3. Detect critical keywords
    critical_keywords = ["meeting", "submit", "exam", "deadline", "presentation", "midnight", "assignment"]
    if any(word in task_lower for word in critical_keywords):
        score += 20

    # Map score to priority
    if score >= 70:
        priority = "high"
    elif score >= 40:
        priority = "medium"
    else:
        priority = "low"

    return priority, score

from datetime import datetime
import pytz

def is_conflicting(new_start, new_end, schedule):
    """Check if new task conflicts with existing schedule (timezone-safe)."""
    # Force new times to be timezone-aware (Asia/Karachi here)
    if new_start.tzinfo is None:
        new_start = new_start.replace(tzinfo=pytz.timezone("Asia/Karachi"))
    if new_end.tzinfo is None:
        new_end = new_end.replace(tzinfo=pytz.timezone("Asia/Karachi"))

    for event in schedule:
        start = event["start"]
        end = event["end"]

        # Convert existing events to timezone-aware if needed
        if start.tzinfo is None:
            start = start.replace(tzinfo=pytz.timezone("Asia/Karachi"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=pytz.timezone("Asia/Karachi"))

        if new_start < end and new_end > start:
            return True

    return False


def infer_priority_with_conflict(task_description, duration_minutes=60):
    score = 0
    task_lower = task_description.lower()

    # 1. Extract time from task
    time_match = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s?(am|pm)\b', task_lower)
    start_time = None
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridian = time_match.group(3)
        if meridian == 'pm' and hour != 12:
            hour += 12
        elif meridian == 'am' and hour == 12:
            hour = 0
        today = datetime.now()
        if today: 
            start_time = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if start_time < today:  # If time already passed today, assume tomorrow
                start_time += timedelta(days=1)
            score += 50  # Time-bound tasks are high priority

    # 2. Check deadline words
    date_obj = dateparser.parse(task_lower, settings={'PREFER_DATES_FROM': 'future'})
    if date_obj:
        delta = date_obj - datetime.now()
        if delta.days < 1:
            score += 30
        elif delta.days < 3:
            score += 20

    # 3. Critical keyword detection
    critical_keywords = ["meeting", "submit", "exam", "deadline", "presentation"]
    if any(word in task_lower for word in critical_keywords):
        score += 20
    
    service = get_calendar_service()
    


    existing_schedule = get_existing_schedule(service, lookahead_days=7)


    # 4. Conflict detection
    conflict_bonus = 0
    if start_time:
        end_time = start_time + timedelta(minutes=duration_minutes)
        if is_conflicting(start_time, end_time, existing_schedule):
            conflict_bonus = 20
            score += conflict_bonus

    # 5. Determine final priority
    if score >= 70:
        priority = "high"
    elif score >= 40:
        priority = "medium"
    else:
        priority = "low"

    return priority, score
from datetime import timedelta
import dateparser

def smart_reasoning_engine(intent, entities, calendar_events, event_status=None, duration_minutes=60):
    task = entities.get("task", "")
    user_priority = entities.get("priority")
    deadline = entities.get("deadline") or entities.get("time")

    # --- Initialize ---
    score = 0
    reasoning_steps = []
    start_time = None

    # --- Expanded Keyword Categories ---
    critical_keywords = {
        "meeting": ["meeting", "call", "sync", "discussion"],
        "deadline": ["submit", "deadline", "due", "turn in"],
        "urgent": ["urgent", "important", "critical", "asap", "immediately"],
        "exam": ["exam", "test", "quiz", "assessment"],
        "presentation": ["presentation", "slides", "demo", "pitch"]
    }

    # -------------------------------------------------------
    # 1️⃣ Direct User Priority
    # -------------------------------------------------------
    if user_priority:
        priority_map = {"low": 20, "medium": 50, "high": 80}
        score += priority_map.get(user_priority.lower(), 40)
        reasoning_steps.append(f"**Priority:** User specified `{user_priority.upper()}` → score {score}.")
    else:
        reasoning_steps.append("**Priority:** No user priority specified, inferring logically...")

    # -------------------------------------------------------
    # 2️⃣ Deadline / Time Sensitivity
    # -------------------------------------------------------
    if deadline:
        parsed_time = dateparser.parse(deadline, settings={'PREFER_DATES_FROM':'future'})
        if parsed_time:
            start_time = parsed_time
            hours_until_deadline = (start_time - timedelta()).total_seconds() / 3600

            # Deadline-based scoring
            if hours_until_deadline <= 24:
                score += 50
                urgency_label = "urgent (<24h)"
            elif hours_until_deadline <= 48:
                score += 30
                urgency_label = "soon (<48h)"
            else:
                score += 10
                urgency_label = "distant"
            reasoning_steps.append(f"**Deadline:** `{parsed_time}` → {urgency_label}, score {score}.")

    # -------------------------------------------------------
    # 3️⃣ Keyword-Based Importance
    # -------------------------------------------------------
    if task:
        for category, words in critical_keywords.items():
            if any(word in task.lower() for word in words):
                weight = 30 if category == "urgent" else 15
                score += weight
                reasoning_steps.append(f"**Keyword:** Task mentions `{category}` → +{weight} points, score {score}.")
                break

    # -------------------------------------------------------
    # 4️⃣ Calendar Conflict Detection
    # -------------------------------------------------------
    conflict_detected = False
    if start_time and calendar_events:
        end_time = start_time + timedelta(minutes=duration_minutes)
        for event in calendar_events:
            if start_time < event["end"] and end_time > event["start"]:
                score += 20
                conflict_detected = True
                reasoning_steps.append(f"**Conflict:** Overlaps with `{event['title']}` → urgency increased, score {score}.")
                break

    # -------------------------------------------------------
    # 5️⃣ Compute Final Priority
    # -------------------------------------------------------
    if score >= 60:
        final_priority = "high"
    elif score >= 40:
        final_priority = "medium"
    else:
        final_priority = "low"

    reasoning_steps.append(f"**Final Decision:** `{final_priority.upper()}` priority (score: {score}).")

    # -------------------------------------------------------
    # 6️⃣ Reflect Actual Calendar Action
    # -------------------------------------------------------
    schedule_on_calendar = (
        intent in ["Add Task", "Set Priority", "Set Deadline"]
        and final_priority in ["high", "medium"]
    )

    # Reflect backend status if provided
    if event_status and event_status.get("success"):
        reasoning_steps.append("**Action:** Task successfully added to Google Calendar ✅")
    elif schedule_on_calendar:
        reasoning_steps.append("**Action:** Task will be added to Google Calendar.")
    else:
        reasoning_steps.append("**Action:** Task not added to calendar automatically.")

    # --- Format reasoning for Streamlit ---
    formatted_reasoning = "\n".join([f"- {step}" for step in reasoning_steps])

    return {
        "task": task,
        "final_priority": final_priority,
        "reasoning": formatted_reasoning,
        "schedule_on_calendar": schedule_on_calendar,
        "score": score
    }

import re
from datetime import datetime, timedelta
import dateparser

def resolve_start_time(time_str):
    """
    Converts a time or deadline string like '11pm', 'tomorrow 5am', 'August 5th', or '8th September'
    into a Python datetime object.
    """
    if not time_str:
        # Default: schedule in next available hour
        dt = datetime.now().replace(minute=0, second=0, microsecond=0)
        return dt

    # Remove ordinal suffixes like 1st, 2nd, 3rd, 4th, etc.
    # Example: "5th August" -> "5 August"
    time_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', time_str, flags=re.IGNORECASE)

    # Use dateparser to handle natural language time expressions
    parsed_time = dateparser.parse(time_str, settings={'PREFER_DATES_FROM': 'future'})
    
    if parsed_time:
        return parsed_time
    else:
        # If parsing fails, fallback to scheduling 1 hour from now
        return datetime.now() + timedelta(hours=24)


#---------------------------------------------------------
# API calls
#---------------------------------------------------------

@app.get("/")
def home():
    return {"message": "Task NLP API is running!"}

# get all tasks
@app.get("/get_tasks/")
def get_tasks():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT * FROM tasks")
    rows = c.fetchall()
    conn.close()
    
    # Convert rows to list of dictionaries
    tasks = []
    for row in rows:
        tasks.append({
            "id": row[0],
            "task": row[1],
            "deadline": row[2],
            "priority": row[3],
            "location": row[4],
            "recurrence": row[5],
            "duration": row[6],
            "intent": row[7]
        })
    
    return {"tasks": tasks}


from datetime import datetime, timedelta
from fastapi import APIRouter

@app.post("/process_task/")
def process_task(user_input: str):

    # Step 1: Get intent as string
    intent = intent_clf.predict([user_input])[0]
    print(f"Intent: {intent}")

    # Step 2: Extract entities
    doc = entity_clf(user_input)           
    entities_dict = {ent.label_: ent.text for ent in doc.ents}
    print("Extracted entities:", entities_dict)

    # Step 3: Safely get entity values with fallbacks
    task = entities_dict.get("TASK") or user_input  
    priority = entities_dict.get("PRIORITY")
    deadline = entities_dict.get("DEADLINE")
    location = entities_dict.get("LOCATION")
    recurrence = entities_dict.get("RECURRENCE")
    duration = entities_dict.get("DURATION")

    # Step 4: Infer priority if missing
    if not priority:
        priority, score = infer_priority_with_conflict(user_input, duration_minutes=60)
        print(f"Priority inferred as : {priority}")
    else:
        score = {"low":20, "medium":50, "high":80}.get(priority, 40)

    # Step 5: Build task data
    task_data = {
        "task": task,
        "priority": priority,
        "score": score,
        "deadline": deadline
    }

    # Step 6: Create event if intent is task-related
    start_time = resolve_start_time(deadline) or datetime.now() + timedelta(hours=1)
    print("DEBUG: Preparing to add event:", task, deadline)
    try:
        event_status = add_task_to_calendar(get_calendar_service(), {
            "title": task,
            "priority": priority or "medium",
            "start_time": start_time,
            "duration_minutes": 60
        })
        task_data["event_status"] = event_status
        print(f"Event '{task}' created at {start_time}")
    except Exception as e:
        print("Error adding event to Google Calendar:", e)
    return task_data




@app.delete("/delete_task/{task_id}")
def delete_task(task_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    if not row:
        conn.close()

    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": f"Task {task_id} deleted"}

@app.put("/update_task/{task_id}")
def update_task(task_id: int, data: dict):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Dynamically update columns based on keys in 'data'
    updates = []
    values = []
    for key, value in data.items():
        updates.append(f"{key} = ?")
        values.append(value)
    
    if updates:
        values.append(task_id)
        c.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()
    
    conn.close()
    return {"status": "success", "message": f"Task {task_id} updated"}


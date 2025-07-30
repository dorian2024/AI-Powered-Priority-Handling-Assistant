
# -----------------------
# import libraries
# -----------------------
from __future__ import print_function
import os.path
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pickle
import streamlit as st

# -----------------------
# Google Calendar Setup
# -----------------------
SCOPES = ['https://www.googleapis.com/auth/calendar']

@st.cache_resource
def get_calendar_service():
    creds = None
    # 1. Load saved token if available
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # 2. Refresh or authenticate if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)

            try:
                # Try local server first
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print("⚠ Local server auth failed, falling back to console:", e)
                creds = flow.run_console()

        # 3. Save credentials to token.json for future runs
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # 4. Build and return the Calendar service
    return build("calendar", "v3", credentials=creds)


# -----------------------
# List Upcoming Events
# -----------------------
def list_upcoming_events(service, max_results=5):
    """List upcoming events from primary calendar."""
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=max_results, singleEvents=True,
        orderBy='startTime').execute()

    events = events_result.get('items', [])
    if not events:
        print('No upcoming events found.')
    else:
        print('Upcoming events:')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])
    return events

# -----------------------
# Add a Task to Calendar
# -----------------------
def add_task_to_calendar(service, task):
    """
    Add a task to Google Calendar as an event.
    Returns a dict: {"success": True/False, "link": event_link or None, "error": message or None}
    """
    try:
        # Compute event times
        start_time = task.get("start_time") #uses get to avoid crashing
        if not start_time: #if its none 
            raise ValueError("Missing start_time for calendar event.")

        duration = task.get("duration_minutes", 60) #60 is the default value
        end_time = start_time + timedelta(minutes=duration)
        print(f"start time before creating event: {start_time.isoformat()}")
        print(f"end time before creating event: {end_time.isoformat()}")
        # Build Google Calendar event
        event = {
            'summary': f'Task: {task.get("title") or "Untitled Task"}',
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Karachi'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Karachi'},
        }

        # Attempt to create event
        print("Sending event to Google Calendar:", event)
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print("Google response:", created_event)


        link = created_event.get('htmlLink')
        print(f"✅ Event created: {link}")
        return {"success": True, "link": link, "error": None}

    except Exception as e:
        print("❌ Error adding event to Google Calendar:", e)
        return {"success": False, "link": None, "error": str(e)}



def get_existing_schedule(service, lookahead_days=7):
    """
    Fetches upcoming Google Calendar events within the next `lookahead_days`.
    Returns a list like:
    [
        {"title": "Meeting", "start": datetime, "end": datetime},
        {"title": "Doctor Appointment", "start": datetime, "end": datetime}
    ]
    """
    now = datetime.utcnow().isoformat() + 'Z'  # current UTC time
    max_time = (datetime.utcnow() + timedelta(days=lookahead_days)).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        timeMax=max_time,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    schedule = []

    for event in events:
        start = event['start'].get('dateTime')
        end = event['end'].get('dateTime')
        if start and end:
            schedule.append({
                "title": event['summary'],
                "start": datetime.fromisoformat(start.replace("Z","")),
                "end": datetime.fromisoformat(end.replace("Z",""))
            })

    return schedule

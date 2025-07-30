from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            try:
                creds = flow.run_local_server(port=0)
            except:
                creds = flow.run_console()
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

if __name__ == "__main__":
    service = get_calendar_service()

    event = {
        'summary': 'Umaima Testing GC',
        'start': {'dateTime': datetime.now().isoformat(), 'timeZone': 'Asia/Karachi'},
        'end': {'dateTime': (datetime.now() + timedelta(hours=1)).isoformat(), 'timeZone': 'Asia/Karachi'},
    }

    created_event = service.events().insert(calendarId='primary', body=event).execute()
    print("✅ Event created:", created_event.get('htmlLink'))

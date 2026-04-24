"""
Google Meet integration via Google Calendar API.
Uses service account with Domain-Wide Delegation (Google Workspace).
Falls back gracefully to mock link if credentials are not configured.
"""
import uuid


def create_meet_link(booking_id: str, job_title: str,
                     candidate_name: str, candidate_email: str,
                     interviewer_name: str, interviewer_email: str,
                     date_str: str, start_time: str, end_time: str,
                     timezone: str = "Asia/Dubai") -> tuple[str, bool]:
    """
    Returns (meet_link, is_real).
    is_real=True  → actual Google Meet link created via Calendar API
    is_real=False → mock link (credentials not configured)
    """
    try:
        import streamlit as st
        creds_data = st.secrets.get("GOOGLE_SERVICE_ACCOUNT", None)
        if not creds_data:
            return _mock_link(), False

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        # Support both dict (TOML table) and JSON string
        if isinstance(creds_data, str):
            import json
            creds_info = json.loads(creds_data)
        else:
            creds_info = dict(creds_data)

        scopes      = ["https://www.googleapis.com/auth/calendar"]
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=scopes
        )
        # Impersonate the interviewer so the event appears on their calendar
        delegated   = credentials.with_subject(interviewer_email)
        service     = build("calendar", "v3", credentials=delegated, cache_discovery=False)

        start_dt = f"{date_str}T{start_time}:00"
        end_dt   = f"{date_str}T{end_time}:00"

        event_body = {
            "summary": f"Interview – {job_title}",
            "description": (
                f"Interview scheduled via noon Interview Scheduling System\n\n"
                f"Candidate  : {candidate_name} ({candidate_email})\n"
                f"Interviewer: {interviewer_name}\n"
                f"Role       : {job_title}"
            ),
            "start": {"dateTime": start_dt, "timeZone": timezone},
            "end":   {"dateTime": end_dt,   "timeZone": timezone},
            "attendees": [
                {"email": interviewer_email, "responseStatus": "accepted"},
                {"email": candidate_email},
            ],
            "conferenceData": {
                "createRequest": {
                    "requestId": booking_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        result = service.events().insert(
            calendarId="primary",
            body=event_body,
            conferenceDataVersion=1,
            sendUpdates="all",   # sends Google Calendar invites to attendees
        ).execute()

        # Extract video entry point
        for ep in result.get("conferenceData", {}).get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                return ep["uri"], True

        return _mock_link(), False

    except ImportError:
        # google packages not installed
        return _mock_link(), False
    except Exception as e:
        print(f"[google_meet] Calendar API error: {e}")
        return _mock_link(), False


def _mock_link() -> str:
    a = uuid.uuid4().hex[:3]
    b = uuid.uuid4().hex[:4]
    c = uuid.uuid4().hex[:3]
    return f"https://meet.google.com/{a}-{b}-{c}"

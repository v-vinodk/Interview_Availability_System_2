"""Shared helpers — email generation, formatting."""

def make_candidate_email(booking, slot, interviewer_name, job_title, candidate_name, candidate_email):
    date_str  = slot["date"]           # YYYY-MM-DD
    start     = slot["start_time"]     # HH:MM
    end       = slot["end_time"]
    meet      = booking["meeting_link"]

    # Pretty date
    from datetime import datetime
    try:
        pretty_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %d %B %Y")
    except Exception:
        pretty_date = date_str

    subject = f"✅ Interview Confirmed — {job_title}"
    body = f"""Hi {candidate_name},

Great news! Your interview has been successfully scheduled.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  INTERVIEW DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📅  Date       : {pretty_date}
  🕐  Time       : {start} – {end} IST
  💼  Role       : {job_title}
  👤  Interviewer: {interviewer_name}
  🔗  Google Meet: {meet}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please join the Google Meet link 5 minutes before the scheduled time.
Keep your camera and microphone ready.

If you need to reschedule or have any questions, please reach out to hr@company.com

All the best!
HR Team | Interview Scheduling System"""

    return {"to": candidate_email, "subject": subject, "body": body}


def make_interviewer_email(booking, slot, interviewer_name, interviewer_email,
                           job_title, candidate_name, candidate_email, candidate_phone):
    date_str = slot["date"]
    start    = slot["start_time"]
    end      = slot["end_time"]
    meet     = booking["meeting_link"]

    from datetime import datetime
    try:
        pretty_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %d %B %Y")
    except Exception:
        pretty_date = date_str

    subject = f"📅 New Interview Scheduled — {candidate_name} ({job_title})"
    body = f"""Hi {interviewer_name},

You have a new interview scheduled.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  INTERVIEW DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📅  Date        : {pretty_date}
  🕐  Time        : {start} – {end} IST
  💼  Role        : {job_title}
  👤  Candidate   : {candidate_name}
  📧  Email       : {candidate_email}
  📱  Phone       : {candidate_phone or 'Not provided'}
  🔗  Google Meet : {meet}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please be available on the Google Meet link at the scheduled time.
Review the candidate's profile before the interview.

Interview Scheduling System"""

    return {"to": interviewer_email, "subject": subject, "body": body}


def format_slot_label(slot):
    """Human-readable slot label."""
    from datetime import datetime
    try:
        d = datetime.strptime(slot["date"], "%Y-%m-%d").strftime("%a, %d %b")
    except Exception:
        d = slot["date"]
    return f"{d}  |  {slot['start_time']} – {slot['end_time']} IST"

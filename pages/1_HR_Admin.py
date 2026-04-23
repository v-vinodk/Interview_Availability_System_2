"""
HR Admin Dashboard — All slots, all bookings, job openings management.
"""
import streamlit as st
import pandas as pd
from database import (init_db, get_stats, get_all_slots, get_all_bookings,
                      get_jobs, create_job, toggle_job,
                      get_all_emails, register_user)

st.set_page_config(page_title="HR Admin", page_icon="👔", layout="wide")
init_db()

# ── Auth Guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("user") or st.session_state.user["role"] != "HR_ADMIN":
    st.warning("🔐 HR Admin access only.")
    st.page_link("app.py", label="→ Login here", icon="🔐")
    st.stop()

user = st.session_state.user
st.title("👔 HR Admin Dashboard")
st.caption(f"Logged in as **{user['name']}**")

if st.sidebar.button("🚪 Logout"):
    st.session_state.user = None
    st.rerun()

# ── Stats ─────────────────────────────────────────────────────────────────────
stats = get_stats()
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("📋 Active Jobs",       stats["active_jobs"])
c2.metric("📅 Total Slots",       stats["total_slots"])
c3.metric("🟢 Available",         stats["available_slots"])
c4.metric("🔵 Booked",            stats["booked_slots"])
c5.metric("✅ Total Bookings",    stats["total_bookings"])
c6.metric("👤 Candidates",        stats["total_candidates"])

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🔵 All Bookings",
    "🟢 Available Slots",
    "💼 Job Openings",
    "📧 Email Logs",
])

# ════════════════════════════════════════════════
# TAB 1 — ALL BOOKINGS
# ════════════════════════════════════════════════
with tab1:
    bookings = get_all_bookings()
    st.subheader(f"All Bookings ({len(bookings)})")
    if not bookings:
        st.info("No bookings yet.")
    else:
        # Filter
        jobs_in_bookings = sorted(set(b["job_title"] for b in bookings))
        ivs_in_bookings  = sorted(set(b["interviewer_name"] for b in bookings))
        fc1, fc2 = st.columns(2)
        with fc1:
            jf = st.multiselect("Filter by Role", jobs_in_bookings, default=jobs_in_bookings, key="jf1")
        with fc2:
            ivf = st.multiselect("Filter by Interviewer", ivs_in_bookings, default=ivs_in_bookings, key="ivf1")

        filtered = [b for b in bookings if b["job_title"] in jf and b["interviewer_name"] in ivf]

        for b in filtered:
            with st.container(border=True):
                r1, r2, r3, r4 = st.columns([2, 2, 2, 2])
                with r1:
                    st.markdown(f"**👤 {b['candidate_name']}**")
                    st.caption(f"📧 {b['candidate_email']}")
                    st.caption(f"📱 {b['candidate_phone'] or '—'}")
                with r2:
                    st.markdown(f"**💼 {b['job_title']}**")
                    st.caption(f"🏢 {b['department']}")
                with r3:
                    st.markdown(f"**📅 {b['date']}**")
                    st.caption(f"🕐 {b['start_time']} – {b['end_time']} IST")
                    st.caption(f"👤 {b['interviewer_name']}")
                with r4:
                    if b.get("meeting_link"):
                        st.link_button("🎥 Google Meet", b["meeting_link"], use_container_width=True)
                    st.caption(f"Booked: {b['created_at'][:10]}")

# ════════════════════════════════════════════════
# TAB 2 — AVAILABLE SLOTS
# ════════════════════════════════════════════════
with tab2:
    all_slots = get_all_slots()
    available = [s for s in all_slots if s["status"] == "AVAILABLE"]
    booked    = [s for s in all_slots if s["status"] == "BOOKED"]

    st.subheader(f"Available Slots ({len(available)})")

    if not available:
        st.info("No available slots. Ask interviewers to add their availability.")
    else:
        # Group by job
        from collections import defaultdict
        by_job = defaultdict(list)
        for s in available:
            by_job[s["job_title"]].append(s)

        for job_title, slots in by_job.items():
            with st.expander(f"💼 {job_title}  ({len(slots)} slots available)", expanded=True):
                df = pd.DataFrame([{
                    "Date":        s["date"],
                    "Time":        f"{s['start_time']} – {s['end_time']}",
                    "Interviewer": s["interviewer_name"],
                    "Department":  s["department"],
                    "Status":      "🟢 Available",
                } for s in slots])
                st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader(f"Booked Slots ({len(booked)})")
    if booked:
        df2 = pd.DataFrame([{
            "Date":        s["date"],
            "Time":        f"{s['start_time']} – {s['end_time']}",
            "Interviewer": s["interviewer_name"],
            "Role":        s["job_title"],
            "Status":      "🔵 Booked",
        } for s in booked])
        st.dataframe(df2, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════
# TAB 3 — JOB OPENINGS
# ════════════════════════════════════════════════
with tab3:
    jl, jr = st.columns([2, 1])

    with jl:
        st.subheader("Active Job Openings")
        jobs = get_jobs(active_only=False)
        for j in jobs:
            with st.container(border=True):
                jc1, jc2, jc3 = st.columns([3, 2, 1])
                with jc1:
                    status_icon = "🟢" if j["is_active"] else "🔴"
                    st.markdown(f"{status_icon} **{j['title']}**")
                    st.caption(f"🏢 {j['department'] or '—'}  |  {j.get('description','')}")
                with jc2:
                    # Count available/booked slots for this job
                    all_s = get_all_slots()
                    avail = sum(1 for s in all_s if s["job_id"] == j["id"] and s["status"] == "AVAILABLE")
                    bkd   = sum(1 for s in all_s if s["job_id"] == j["id"] and s["status"] == "BOOKED")
                    st.metric("🟢 Available", avail)
                    st.metric("🔵 Booked", bkd)
                with jc3:
                    label = "Deactivate" if j["is_active"] else "Activate"
                    if st.button(label, key=f"tog_{j['id']}"):
                        toggle_job(j["id"], not j["is_active"])
                        st.rerun()

    with jr:
        st.subheader("➕ Add Job Opening")
        with st.form("add_job_form", clear_on_submit=True):
            j_title = st.text_input("Job Title *", placeholder="e.g. Backend Engineer")
            j_dept  = st.text_input("Department",  placeholder="e.g. Engineering")
            j_desc  = st.text_area("Description",  height=80)
            j_sub   = st.form_submit_button("Create Job", type="primary", use_container_width=True)
        if j_sub:
            if not j_title.strip():
                st.error("Job title is required.")
            else:
                create_job(j_title.strip(), j_dept.strip(), j_desc.strip())
                st.success(f"✅ '{j_title}' created!")
                st.rerun()

        st.divider()
        st.subheader("➕ Add Interviewer Account")
        with st.form("add_interviewer_form", clear_on_submit=True):
            iv_name  = st.text_input("Full Name *")
            iv_email = st.text_input("Email *")
            iv_pw    = st.text_input("Password *", type="password")
            iv_sub   = st.form_submit_button("Create Account", type="primary", use_container_width=True)
        if iv_sub:
            if not all([iv_name, iv_email, iv_pw]):
                st.error("All fields required.")
            else:
                uid = register_user(iv_name, iv_email, iv_pw, "INTERVIEWER")
                if uid:
                    st.success(f"✅ Interviewer account created for {iv_name}")
                else:
                    st.error("Email already exists.")

# ════════════════════════════════════════════════
# TAB 4 — EMAIL LOGS
# ════════════════════════════════════════════════
with tab4:
    emails = get_all_emails()
    st.subheader(f"Email Notifications Sent ({len(emails)} total)")
    st.caption("These are mock emails — in production these would be delivered via SendGrid/SES.")

    if not emails:
        st.info("No emails logged yet. Emails are logged when candidates book a slot.")
    else:
        for e in emails:
            icon = "👤" if e["role"] == "CANDIDATE" else "🎯"
            with st.expander(f"{icon} **{e['subject']}**  →  {e['to_email']}  |  {e['sent_at'][:16]}", expanded=False):
                st.code(e["body"], language=None)

"""
HR Admin Dashboard — Manage candidates, slots, bookings, job openings.
"""
import streamlit as st
import pandas as pd
from database import (init_db, get_stats, get_all_slots, get_all_bookings,
                      get_jobs, create_job, toggle_job, get_all_emails,
                      register_user, add_candidate, remove_candidate,
                      get_all_applications)

st.set_page_config(page_title="HR Admin", page_icon="👔", layout="wide")
init_db()

# ── Auth Guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("user") or st.session_state.user["role"] != "HR_ADMIN":
    st.warning("🔐 HR Admin access only.")
    st.page_link("app.py", label="→ Login here", icon="🔐")
    st.stop()

user = st.session_state.user

st.markdown("""
<div style='background:linear-gradient(135deg,#FFE000 0%,#FFF176 100%);
            padding:1rem 1.5rem; border-radius:10px; margin-bottom:1rem'>
  <h2 style='margin:0; color:#1A1A1A'>👔 HR Admin Dashboard</h2>
  <p style='margin:0; color:#333; font-size:0.9rem'>noon · Interview Scheduling System</p>
</div>
""", unsafe_allow_html=True)
st.caption(f"Logged in as **{user['name']}**")

if st.sidebar.button("🚪 Logout"):
    st.session_state.user = None
    st.rerun()

# ── Stats ─────────────────────────────────────────────────────────────────────
stats = get_stats()
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("💼 Active Jobs",        stats["active_jobs"])
c2.metric("👥 Candidates",         stats["total_candidates"])
c3.metric("⏳ Pending Booking",    stats["pending"])
c4.metric("📅 Total Slots",        stats["total_slots"])
c5.metric("🟢 Available",          stats["available_slots"])
c6.metric("🔵 Booked Slots",       stats["booked_slots"])
c7.metric("✅ Total Bookings",     stats["total_bookings"])

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "👥 Manage Candidates",
    "🔵 All Bookings",
    "🟢 Available Slots",
    "💼 Job Openings",
    "📧 Email Logs",
])

# ══════════════════════════════════════════════════
# TAB 1 — MANAGE CANDIDATES (NEW — CORE SECURITY)
# ══════════════════════════════════════════════════
with tab1:
    cl, cr = st.columns([2, 1], gap="large")

    with cl:
        st.subheader("📋 Registered Candidates")
        st.caption("Only candidates listed here can book interview slots.")

        apps = get_all_applications()
        if not apps:
            st.info("No candidates registered yet. Add candidates using the form →")
        else:
            # Filter
            jobs_list = sorted(set(a["job_title"] for a in apps))
            status_list = sorted(set(a["status"] for a in apps))
            fc1, fc2 = st.columns(2)
            with fc1:
                jf = st.multiselect("Filter by Role", jobs_list, default=jobs_list)
            with fc2:
                sf = st.multiselect("Filter by Status", status_list,
                                    default=[s for s in status_list if s != "REMOVED"])

            filtered = [a for a in apps if a["job_title"] in jf and a["status"] in sf]
            st.caption(f"**{len(filtered)}** candidates shown")

            for a in filtered:
                status_color = {"ACTIVE": "🟢", "BOOKED": "🔵", "REMOVED": "🔴"}.get(a["status"], "⚪")
                with st.container(border=True):
                    ac1, ac2, ac3, ac4 = st.columns([2, 2, 2, 1])
                    with ac1:
                        st.markdown(f"**👤 {a['name']}**")
                        st.caption(f"📧 {a['email']}")
                        st.caption(f"📱 {a['phone'] or '—'}")
                    with ac2:
                        st.markdown(f"**💼 {a['job_title']}**")
                        st.caption(f"🏢 {a['department']}")
                    with ac3:
                        st.markdown(f"{status_color} **{a['status']}**")
                        st.caption(f"Added: {a['created_at'][:10]}")
                        if a.get("added_by_name"):
                            st.caption(f"By: {a['added_by_name']}")
                    with ac4:
                        if a["status"] == "ACTIVE":
                            if st.button("❌ Remove", key=f"rm_{a['id']}", use_container_width=True):
                                remove_candidate(a["id"])
                                st.toast(f"{a['name']} removed from selection list.")
                                st.rerun()

    with cr:
        st.subheader("➕ Add Candidate")
        st.caption("Add a candidate to the selection list for a specific role. Only added candidates can book slots.")

        jobs = get_jobs(active_only=True)
        if not jobs:
            st.warning("Create a job opening first.")
        else:
            job_map = {j["title"]: j["id"] for j in jobs}
            with st.form("add_cand_form", clear_on_submit=True):
                c_name  = st.text_input("Full Name *",  placeholder="Rahul Verma")
                c_email = st.text_input("Email *",      placeholder="rahul@example.com")
                c_phone = st.text_input("Phone",        placeholder="+91-9876543210")
                c_job   = st.selectbox("💼 Role Applied For *", list(job_map.keys()))
                c_sub   = st.form_submit_button("➕ Add to Selection List",
                                                type="primary", use_container_width=True)

            if c_sub:
                if not c_name.strip() or not c_email.strip() or "@" not in c_email:
                    st.error("Name and valid email are required.")
                else:
                    cid, err = add_candidate(c_name, c_email, c_phone,
                                             job_map[c_job], user["id"])
                    if err:
                        st.error(f"❌ {err}")
                    else:
                        st.success(f"✅ **{c_name}** added for **{c_job}**")
                        st.rerun()

        st.divider()
        st.info("""
**🔒 How security works:**

1. HR adds candidate email here
2. Candidate visits the booking page
3. They enter their email
4. System checks if email is registered
5. ✅ Match → they see available slots
6. ❌ No match → access denied

No outsider can book without HR adding them first.
""")

# ══════════════════════════════════════════════════
# TAB 2 — ALL BOOKINGS
# ══════════════════════════════════════════════════
with tab2:
    bookings = get_all_bookings()
    st.subheader(f"All Bookings ({len(bookings)})")

    if not bookings:
        st.info("No bookings yet.")
    else:
        jobs_in_b = sorted(set(b["job_title"] for b in bookings))
        ivs_in_b  = sorted(set(b["interviewer_name"] for b in bookings))
        fc1, fc2  = st.columns(2)
        with fc1:
            jf2 = st.multiselect("Filter by Role", jobs_in_b, default=jobs_in_b)
        with fc2:
            ivf = st.multiselect("Filter by Interviewer", ivs_in_b, default=ivs_in_b)

        filtered2 = [b for b in bookings if b["job_title"] in jf2 and b["interviewer_name"] in ivf]

        for b in filtered2:
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
                        st.link_button("🎥 Google Meet", b["meeting_link"],
                                       use_container_width=True)
                    st.caption(f"Booked: {b['created_at'][:10]}")

# ══════════════════════════════════════════════════
# TAB 3 — AVAILABLE SLOTS
# ══════════════════════════════════════════════════
with tab3:
    all_slots = get_all_slots()
    available = [s for s in all_slots if s["status"] == "AVAILABLE"]
    booked    = [s for s in all_slots if s["status"] == "BOOKED"]

    st.subheader(f"🟢 Available Slots ({len(available)})")
    if not available:
        st.info("No available slots. Ask interviewers to add availability.")
    else:
        from collections import defaultdict
        by_job = defaultdict(list)
        for s in available:
            by_job[s["job_title"]].append(s)

        for job_title, slots in by_job.items():
            with st.expander(f"💼 {job_title}  —  {len(slots)} slots", expanded=True):
                df = pd.DataFrame([{
                    "Date":        s["date"],
                    "Time (IST)":  f"{s['start_time']} – {s['end_time']}",
                    "Interviewer": s["interviewer_name"],
                    "Department":  s["department"],
                } for s in slots])
                st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader(f"🔵 Booked Slots ({len(booked)})")
    if booked:
        df2 = pd.DataFrame([{
            "Date":        s["date"],
            "Time (IST)":  f"{s['start_time']} – {s['end_time']}",
            "Interviewer": s["interviewer_name"],
            "Role":        s["job_title"],
        } for s in booked])
        st.dataframe(df2, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════
# TAB 4 — JOB OPENINGS
# ══════════════════════════════════════════════════
with tab4:
    jl, jr = st.columns([2, 1], gap="large")

    with jl:
        st.subheader("Active Job Openings")
        jobs = get_jobs(active_only=False)
        all_s = get_all_slots()
        for j in jobs:
            with st.container(border=True):
                jc1, jc2, jc3 = st.columns([3, 2, 1])
                with jc1:
                    icon = "🟢" if j["is_active"] else "🔴"
                    st.markdown(f"{icon} **{j['title']}**")
                    st.caption(f"🏢 {j['department'] or '—'}  |  {j.get('description','')}")
                with jc2:
                    avail = sum(1 for s in all_s if s["job_id"] == j["id"] and s["status"] == "AVAILABLE")
                    bkd   = sum(1 for s in all_s if s["job_id"] == j["id"] and s["status"] == "BOOKED")
                    st.caption(f"🟢 {avail} available  |  🔵 {bkd} booked")
                with jc3:
                    label = "Deactivate" if j["is_active"] else "Activate"
                    if st.button(label, key=f"tog_{j['id']}", use_container_width=True):
                        toggle_job(j["id"], not j["is_active"])
                        st.rerun()

    with jr:
        st.subheader("➕ New Job Opening")
        with st.form("add_job_form", clear_on_submit=True):
            j_title = st.text_input("Job Title *", placeholder="Backend Engineer")
            j_dept  = st.text_input("Department",  placeholder="Engineering")
            j_desc  = st.text_area("Description",  height=80)
            if st.form_submit_button("Create Job", type="primary", use_container_width=True):
                if j_title.strip():
                    create_job(j_title.strip(), j_dept.strip(), j_desc.strip())
                    st.success(f"✅ '{j_title}' created!")
                    st.rerun()
                else:
                    st.error("Job title required.")

        st.divider()
        st.subheader("➕ Add Interviewer Account")
        with st.form("add_iv_form", clear_on_submit=True):
            iv_name  = st.text_input("Full Name *")
            iv_email = st.text_input("Email *")
            iv_pw    = st.text_input("Password *", type="password")
            if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                if all([iv_name, iv_email, iv_pw]):
                    uid = register_user(iv_name, iv_email, iv_pw, "INTERVIEWER")
                    st.success(f"✅ Account created for {iv_name}") if uid else st.error("Email already exists.")
                else:
                    st.error("All fields required.")

# ══════════════════════════════════════════════════
# TAB 5 — EMAIL LOGS
# ══════════════════════════════════════════════════
with tab5:
    emails = get_all_emails()
    st.subheader(f"Email Notifications ({len(emails)} sent)")
    st.caption("Mocked emails — configure SendGrid in secrets.toml to send real emails.")
    if not emails:
        st.info("No emails logged yet.")
    else:
        for e in emails:
            icon = "👤" if e["role"] == "CANDIDATE" else "🎯"
            with st.expander(
                f"{icon} **{e['subject']}**  →  {e['to_email']}  |  {e['sent_at'][:16]}",
                expanded=False
            ):
                st.code(e["body"], language=None)

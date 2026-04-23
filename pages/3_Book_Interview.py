"""
Candidate Booking Page — Fully public, no login required.
Step 1: Enter details  →  Step 2: Pick slot  →  Step 3: Confirmed 🎉
"""
import streamlit as st
from collections import defaultdict
from database import init_db, get_jobs, get_available_slots_for_job, book_slot, log_email
from utils import make_candidate_email, make_interviewer_email, format_slot_label

st.set_page_config(page_title="Book Interview", page_icon="📅", layout="centered")
init_db()

# ── State init ────────────────────────────────────────────────────────────────
for k, v in [("bk_step", 1), ("bk_info", None), ("bk_job", None),
              ("bk_slot", None), ("bk_result", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; padding:1.2rem 0 0.5rem'>
  <h2 style='margin-bottom:0.2rem'>📅 Book Your Interview</h2>
  <p style='color:#6B7280'>No account needed — just fill in your details and pick a time.</p>
</div>
""", unsafe_allow_html=True)

# ── Progress Bar ──────────────────────────────────────────────────────────────
step  = st.session_state.bk_step
steps = ["Your Details", "Pick a Slot", "Confirmed!"]

progress_cols = st.columns(3)
for i, (col, label) in enumerate(zip(progress_cols, steps), start=1):
    if i < step:
        col.markdown(f"<div style='text-align:center; color:#059669; font-weight:bold'>✅ {label}</div>", unsafe_allow_html=True)
    elif i == step:
        col.markdown(f"<div style='text-align:center; color:#1A56DB; font-weight:bold'>🔵 {label}</div>", unsafe_allow_html=True)
    else:
        col.markdown(f"<div style='text-align:center; color:#9CA3AF'>○ {label}</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:0.8rem 0'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# STEP 1 — Candidate Details
# ══════════════════════════════════════════════════
if step == 1:
    st.subheader("Step 1: Your Details")

    jobs = get_jobs(active_only=True)
    if not jobs:
        st.error("No active job openings at the moment. Please check back later.")
        st.stop()

    job_map = {j["title"]: j for j in jobs}

    with st.form("candidate_form"):
        name  = st.text_input("Full Name *",    placeholder="e.g. Rahul Verma")
        email = st.text_input("Email *",        placeholder="e.g. rahul@example.com")
        phone = st.text_input("Phone (optional)", placeholder="e.g. +91-9876543210")

        st.markdown("---")
        job_title = st.selectbox(
            "💼 Which role did you apply for? *",
            list(job_map.keys()),
            help="Select the job opening you applied for to see relevant interview slots."
        )

        go = st.form_submit_button("View Available Slots →", type="primary", use_container_width=True)

    if go:
        if not name.strip():
            st.error("Please enter your full name.")
        elif not email.strip() or "@" not in email:
            st.error("Please enter a valid email address.")
        else:
            st.session_state.bk_info = {
                "name": name.strip(),
                "email": email.strip().lower(),
                "phone": phone.strip(),
            }
            st.session_state.bk_job  = job_map[job_title]
            st.session_state.bk_step = 2
            st.rerun()

# ══════════════════════════════════════════════════
# STEP 2 — Pick a Slot
# ══════════════════════════════════════════════════
elif step == 2:
    info = st.session_state.bk_info
    job  = st.session_state.bk_job

    st.subheader(f"Step 2: Pick a Slot for **{job['title']}**")
    st.caption(f"Hi **{info['name']}**, here are available slots for this role. Click to book.")

    slots = get_available_slots_for_job(job["id"])

    if not slots:
        st.warning("😔 No available slots for this role right now. Please check back soon or contact HR.")
        if st.button("← Back"):
            st.session_state.bk_step = 1
            st.rerun()
        st.stop()

    # Group by date
    by_date = defaultdict(list)
    for s in slots:
        by_date[s["date"]].append(s)

    from datetime import datetime
    selected_slot_id = None

    for date_str, date_slots in list(by_date.items())[:14]:
        try:
            pretty = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %d %B %Y")
        except Exception:
            pretty = date_str

        st.markdown(f"#### 📆 {pretty}")

        cols = st.columns(min(len(date_slots), 3))
        for i, s in enumerate(date_slots):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**🕐 {s['start_time']} – {s['end_time']}**")
                    st.caption(f"👤 {s['interviewer_name']}")
                    if st.button("Book This Slot", key=f"bk_{s['id']}",
                                 type="primary", use_container_width=True):
                        selected_slot_id = s["id"]
                        st.session_state.bk_slot = s

    if selected_slot_id:
        st.session_state.bk_step = 3
        st.rerun()

    st.markdown("---")
    if st.button("← Change Details"):
        st.session_state.bk_step = 1
        st.rerun()

# ══════════════════════════════════════════════════
# STEP 3 — Confirm & Show Email
# ══════════════════════════════════════════════════
elif step == 3:
    info = st.session_state.bk_info
    job  = st.session_state.bk_job
    slot = st.session_state.bk_slot

    # Only run booking once
    if st.session_state.bk_result is None:
        booking, err = book_slot(
            slot["id"],
            info["name"], info["email"], info["phone"]
        )
        if err:
            st.error(f"❌ {err}")
            if st.button("← Try Another Slot"):
                st.session_state.bk_step   = 2
                st.session_state.bk_result = None
            st.stop()

        # Build mock emails
        cand_email = make_candidate_email(
            booking, slot, slot["interviewer_name"],
            job["title"], info["name"], info["email"]
        )
        iv_email = make_interviewer_email(
            booking, slot, slot["interviewer_name"], "",
            job["title"], info["name"], info["email"], info["phone"]
        )

        # Log emails
        log_email(booking["id"], info["email"],        "CANDIDATE",   cand_email["subject"], cand_email["body"])
        log_email(booking["id"], slot["interviewer_name"], "INTERVIEWER", iv_email["subject"],  iv_email["body"])

        booking["cand_email"] = cand_email
        booking["iv_email"]   = iv_email
        st.session_state.bk_result = booking

    booking = st.session_state.bk_result

    # ── Confirmation UI ───────────────────────────────────────────────────────
    st.balloons()

    st.markdown("""
    <div style='text-align:center; padding:1rem 0'>
      <h2 style='color:#059669'>🎉 Interview Booked Successfully!</h2>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        d1, d2 = st.columns(2)
        with d1:
            st.markdown(f"**👤 Name:** {info['name']}")
            st.markdown(f"**📧 Email:** {info['email']}")
            st.markdown(f"**📱 Phone:** {info.get('phone') or '—'}")
            st.markdown(f"**💼 Role:** {job['title']}")
        with d2:
            st.markdown(f"**📅 Date:** {slot['date']}")
            st.markdown(f"**🕐 Time:** {slot['start_time']} – {slot['end_time']} IST")
            st.markdown(f"**👤 Interviewer:** {slot['interviewer_name']}")
            if booking.get("meeting_link"):
                st.markdown(f"**🔗 Meet:** [Join Google Meet]({booking['meeting_link']})")

    if booking.get("meeting_link"):
        st.link_button("🎥 Join Google Meet", booking["meeting_link"],
                       type="primary", use_container_width=True)

    # ── Email Previews ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("✉️ Confirmation Emails (Mocked)")
    st.caption("In production these would be delivered via SendGrid / AWS SES automatically.")

    tab_c, tab_iv = st.tabs(["📧 Email to You (Candidate)", "📧 Email to Interviewer"])

    with tab_c:
        ce = booking["cand_email"]
        st.markdown(f"**To:** {ce['to']}  \n**Subject:** {ce['subject']}")
        st.code(ce["body"], language=None)

    with tab_iv:
        ie = booking["iv_email"]
        st.markdown(f"**To:** {ie['to']}  \n**Subject:** {ie['subject']}")
        st.code(ie["body"], language=None)

    # ── Book Another ──────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("📅 Book Another Interview", use_container_width=True):
        for k in ["bk_step","bk_info","bk_job","bk_slot","bk_result"]:
            st.session_state[k] = None if k != "bk_step" else 1
        st.rerun()

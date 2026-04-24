"""
Candidate Booking Page — Secure, pre-registration required.
Step 1: Email verification  →  Step 2: Pick slot  →  Step 3: Confirmed 🎉
"""
import streamlit as st
from collections import defaultdict
from datetime import datetime
from database import (init_db, verify_candidate_email,
                      get_available_slots_for_job, book_slot, log_email)
from utils import make_candidate_email, make_interviewer_email
from google_meet import create_meet_link

st.set_page_config(page_title="Book Interview", page_icon="📅", layout="centered")
init_db()

# ── State init ────────────────────────────────────────────────────────────────
for k, v in [("bk_step", 1), ("bk_app", None),
              ("bk_slot", None), ("bk_result", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; padding:1.2rem 1rem 1rem;
            background:linear-gradient(135deg,#FFE000 0%,#FFF176 100%);
            border-radius:12px; margin-bottom:1rem'>
  <h2 style='margin-bottom:0.2rem; color:#1A1A1A'>📅 Book Your Interview</h2>
  <p style='color:#333; margin:0'>noon · Candidate Portal</p>
</div>
""", unsafe_allow_html=True)

# ── Progress Steps ────────────────────────────────────────────────────────────
step  = st.session_state.bk_step
steps = ["Verify Email", "Pick a Slot", "Confirmed! 🎉"]

cols = st.columns(3)
for i, (col, label) in enumerate(zip(cols, steps), start=1):
    if i < step:
        col.markdown(
            f"<div style='text-align:center;color:#1A1A1A;font-weight:bold;"
            f"background:#FFE000;border-radius:6px;padding:4px'>✅ {label}</div>",
            unsafe_allow_html=True)
    elif i == step:
        col.markdown(
            f"<div style='text-align:center;color:#fff;font-weight:bold;"
            f"background:#1A1A1A;border-radius:6px;padding:4px'>● {label}</div>",
            unsafe_allow_html=True)
    else:
        col.markdown(
            f"<div style='text-align:center;color:#9CA3AF;"
            f"border:1px solid #E5E7EB;border-radius:6px;padding:4px'>○ {label}</div>",
            unsafe_allow_html=True)

st.markdown("<hr style='margin:0.8rem 0'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════
# STEP 1 — Email Verification (Security Gate)
# ══════════════════════════════════════════════════
if step == 1:
    st.subheader("Step 1: Enter Your Email")

    st.info(
        "🔒 **Access is restricted.** Only candidates who have been shortlisted "
        "and registered by HR can book interview slots.\n\n"
        "Enter the email address you used when you applied."
    )

    with st.form("email_verify_form"):
        email = st.text_input(
            "Your Email Address *",
            placeholder="e.g. rahul@example.com",
            help="Use the same email you gave HR during your application."
        )
        go = st.form_submit_button("Verify & Continue →", type="primary", use_container_width=True)

    if go:
        if not email.strip() or "@" not in email:
            st.error("Please enter a valid email address.")
        else:
            with st.spinner("Verifying..."):
                application = verify_candidate_email(email.strip())

            if application:
                st.session_state.bk_app  = application
                st.session_state.bk_step = 2
                st.rerun()
            else:
                st.error(
                    "❌ **Email not found in our system.**\n\n"
                    "Your email is either not registered or your application is not active. "
                    "Please contact HR at hr@noon.com to get registered."
                )

    # Demo helper
    with st.expander("🎯 Demo — test emails you can use"):
        st.markdown("""
| Name | Email | Role |
|------|-------|------|
| Rahul Verma | `rahul@example.com` | Software Engineer – Backend |
| Sneha Patel | `sneha@example.com` | Software Engineer – Frontend |
| Amit Sharma | `amit@example.com` | Product Manager |
| Demo Candidate | `demo@candidate.com` | Software Engineer – Backend |
""")
        st.caption("These are pre-registered by HR in the demo. Anyone else gets access denied. ✅")


# ══════════════════════════════════════════════════
# STEP 2 — Pick a Slot
# ══════════════════════════════════════════════════
elif step == 2:
    app = st.session_state.bk_app

    # Welcome strip
    st.markdown(
        f"<div style='background:#FFFDE7;border-left:4px solid #FFE000;"
        f"padding:0.7rem 1rem;border-radius:6px;margin-bottom:1rem'>"
        f"✅ Verified: <strong>{app['name']}</strong> &nbsp;|&nbsp; "
        f"Role: <strong>{app['job_title']}</strong></div>",
        unsafe_allow_html=True
    )

    st.subheader(f"Step 2: Pick Your Interview Slot")
    st.caption(f"Available slots for **{app['job_title']}** — all times in IST")

    slots = get_available_slots_for_job(app["job_id"])

    if not slots:
        st.warning(
            "😔 No available slots for your role right now. "
            "Please check back later or contact HR."
        )
        if st.button("← Back"):
            st.session_state.bk_step = 1
            st.rerun()
        st.stop()

    # Group by date
    by_date = defaultdict(list)
    for s in slots:
        by_date[s["date"]].append(s)

    for date_str, date_slots in list(by_date.items())[:14]:
        try:
            pretty = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %d %B %Y")
        except Exception:
            pretty = date_str

        st.markdown(f"#### 📆 {pretty}")
        grid_cols = st.columns(min(len(date_slots), 3))

        for i, s in enumerate(date_slots):
            with grid_cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**🕐 {s['start_time']} – {s['end_time']}**")
                    st.caption(f"👤 {s['interviewer_name']}")
                    if st.button(
                        "Book This Slot",
                        key=f"bk_{s['id']}",
                        type="primary",
                        use_container_width=True
                    ):
                        st.session_state.bk_slot = s
                        st.session_state.bk_step = 3
                        st.rerun()

    st.markdown("---")
    if st.button("← Change Email"):
        st.session_state.bk_step = 1
        st.session_state.bk_app  = None
        st.rerun()


# ══════════════════════════════════════════════════
# STEP 3 — Confirm + Google Meet + Email
# ══════════════════════════════════════════════════
elif step == 3:
    app  = st.session_state.bk_app
    slot = st.session_state.bk_slot

    # Only run booking logic once
    if st.session_state.bk_result is None:
        with st.spinner("Creating your interview and Google Meet link..."):

            # Generate Meet link (real if Google credentials set, mock otherwise)
            meet_link, is_real = create_meet_link(
                booking_id        = f"booking-{app['id']}-{slot['id']}",
                job_title         = app["job_title"],
                candidate_name    = app["name"],
                candidate_email   = app["email"],
                interviewer_name  = slot["interviewer_name"],
                interviewer_email = slot["interviewer_email"],
                date_str          = slot["date"],
                start_time        = slot["start_time"],
                end_time          = slot["end_time"],
            )

            booking, err = book_slot(slot["id"], app["id"], meet_link)

        if err:
            st.error(f"❌ {err}")
            if st.button("← Try Another Slot"):
                st.session_state.bk_step   = 2
                st.session_state.bk_result = None
            st.stop()

        # Build emails
        cand_email = make_candidate_email(
            booking, slot, slot["interviewer_name"],
            app["job_title"], app["name"], app["email"]
        )
        iv_email = make_interviewer_email(
            booking, slot, slot["interviewer_name"], slot["interviewer_email"],
            app["job_title"], app["name"], app["email"], app["phone"]
        )

        log_email(booking["id"], app["email"],          "CANDIDATE",   cand_email["subject"], cand_email["body"])
        log_email(booking["id"], slot["interviewer_email"], "INTERVIEWER", iv_email["subject"],  iv_email["body"])

        booking["cand_email"]  = cand_email
        booking["iv_email"]    = iv_email
        booking["meet_is_real"]= is_real
        booking["meet_link"]   = meet_link
        st.session_state.bk_result = booking

    booking = st.session_state.bk_result
    is_real = booking.get("meet_is_real", False)

    # ── Confirmation Banner ───────────────────────────────────────────────────
    st.balloons()
    st.markdown("""
    <div style='text-align:center; padding:1rem;
                background:linear-gradient(135deg,#FFE000 0%,#FFF176 100%);
                border-radius:12px; margin-bottom:1rem'>
      <h2 style='color:#1A1A1A; margin:0'>🎉 Interview Booked Successfully!</h2>
      <p style='color:#333; margin:0.3rem 0 0'>
        You'll receive a confirmation email with all details.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Booking Details Card ──────────────────────────────────────────────────
    with st.container(border=True):
        d1, d2 = st.columns(2)
        with d1:
            st.markdown(f"**👤 Name:** {app['name']}")
            st.markdown(f"**📧 Email:** {app['email']}")
            st.markdown(f"**📱 Phone:** {app.get('phone') or '—'}")
            st.markdown(f"**💼 Role:** {app['job_title']}")
        with d2:
            st.markdown(f"**📅 Date:** {slot['date']}")
            st.markdown(f"**🕐 Time:** {slot['start_time']} – {slot['end_time']} IST")
            st.markdown(f"**👤 Interviewer:** {slot['interviewer_name']}")
            meet_label = "🟢 Real Google Meet" if is_real else "🔗 Google Meet (mock)"
            st.markdown(f"**{meet_label}:** [Join Meeting]({booking['meet_link']})")

    # ── Join Button ───────────────────────────────────────────────────────────
    st.link_button(
        "🎥 Join Google Meet",
        booking["meet_link"],
        type="primary",
        use_container_width=True
    )

    if not is_real:
        st.caption(
            "ℹ️ This is a mock Meet link. "
            "To generate real Google Meet links, configure `GOOGLE_SERVICE_ACCOUNT` "
            "in your Streamlit secrets. See the README for setup guide."
        )

    # ── Email Previews ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("✉️ Confirmation Emails")
    st.caption("These emails have been logged. Configure SendGrid to deliver them automatically.")

    tab_c, tab_iv = st.tabs(["📧 Your Email (Candidate)", "📧 Interviewer's Email"])
    with tab_c:
        ce = booking["cand_email"]
        st.markdown(f"**To:** {ce['to']}  \n**Subject:** {ce['subject']}")
        st.code(ce["body"], language=None)
    with tab_iv:
        ie = booking["iv_email"]
        st.markdown(f"**To:** {ie['to']}  \n**Subject:** {ie['subject']}")
        st.code(ie["body"], language=None)

    # ── Done ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("🔄 Book Another Interview", use_container_width=True):
        for k, v in [("bk_step", 1), ("bk_app", None),
                     ("bk_slot", None), ("bk_result", None)]:
            st.session_state[k] = v
        st.rerun()

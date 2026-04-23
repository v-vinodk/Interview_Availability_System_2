"""
Interview Availability System — Landing Page
Choose your role to get started.
"""
import streamlit as st
from database import init_db, login

st.set_page_config(
    page_title="Interview Availability System",
    page_icon="📅",
    layout="centered",
    initial_sidebar_state="expanded",
)
init_db()

# Session defaults
for key, val in [("user", None), ("booking_step", "form"), ("candidate_info", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Already logged in ─────────────────────────────────────────────────────────
if st.session_state.user:
    u    = st.session_state.user
    role = u["role"]
    st.success(f"✅ Logged in as **{u['name']}** ({role})")
    if role == "HR_ADMIN":
        st.page_link("pages/1_HR_Admin.py",      label="→ Go to HR Dashboard",       icon="👔")
    else:
        st.page_link("pages/2_Interviewer.py",   label="→ Go to My Availability",    icon="🎯")
    if st.button("🚪 Logout"):
        st.session_state.user = None
        st.rerun()
    st.stop()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; padding: 2rem 0 1.5rem'>
  <h1 style='font-size:2.6rem; margin-bottom:0.3rem'>📅 Interview Scheduler</h1>
  <p style='color:#6B7280; font-size:1.1rem'>Simple. Fast. No confusion.</p>
</div>
""", unsafe_allow_html=True)

# ── Role Cards ────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.markdown("### 👔 HR Admin")
        st.caption("View all slots & bookings. Manage job openings.")
with c2:
    with st.container(border=True):
        st.markdown("### 🎯 Interviewer")
        st.caption("Add your available time slots for open roles.")
with c3:
    with st.container(border=True):
        st.markdown("### 🙋 Candidate")
        st.caption("Book your interview slot — no account needed.")
        st.page_link("pages/3_Book_Interview.py", label="Book Now →", icon="📅")

st.divider()

# ── Login Form ────────────────────────────────────────────────────────────────
st.subheader("🔐 HR / Interviewer Login")

with st.form("login_form"):
    email    = st.text_input("Email",    placeholder="e.g. john@demo.com")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

if submitted:
    if not email or not password:
        st.error("Please enter email and password.")
    else:
        user = login(email, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("❌ Invalid email or password.")

# ── Demo Credentials ──────────────────────────────────────────────────────────
with st.expander("🎯 Demo Credentials"):
    st.markdown("""
| Role | Email | Password |
|------|-------|----------|
| 👔 HR Admin | `hr@demo.com` | `hr123` |
| 🎯 Interviewer 1 | `john@demo.com` | `demo123` |
| 🎯 Interviewer 2 | `priya@demo.com` | `demo123` |
| 🎯 Interviewer 3 | `arjun@demo.com` | `demo123` |
""")
    st.caption("Candidate booking requires no login → click **Book Interview** in sidebar")

"""
Interviewer Page — Add availability slots for open job roles.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta, time, datetime
from database import (init_db, get_slots_for_interviewer, get_jobs,
                      add_slot, delete_slot, get_all_bookings)

st.set_page_config(page_title="Interviewer", page_icon="🎯", layout="wide")
init_db()

# ── Auth Guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("user") or st.session_state.user["role"] != "INTERVIEWER":
    st.warning("🎯 Interviewer access only. Please log in.")
    st.page_link("app.py", label="→ Login here", icon="🔐")
    st.stop()

user = st.session_state.user

if st.sidebar.button("🚪 Logout"):
    st.session_state.user = None
    st.rerun()

st.title(f"🎯 My Availability")
st.caption(f"**{user['name']}** — Add your available slots for interview roles below.")

# ── Load data ─────────────────────────────────────────────────────────────────
slots    = get_slots_for_interviewer(user["id"])
jobs     = get_jobs(active_only=True)
bookings = get_all_bookings()
my_bookings = [b for b in bookings if b["interviewer_email"] == user["email"]]

today = date.today()
available_slots = [s for s in slots if s["status"] == "AVAILABLE" and s["date"] >= str(today)]
booked_slots    = [s for s in slots if s["status"] == "BOOKED"]

# ── Quick Stats ───────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("🟢 Available Slots",  len(available_slots))
c2.metric("🔵 Booked Slots",     len(booked_slots))
c3.metric("📅 Upcoming Interviews", len([b for b in my_bookings if b["date"] >= str(today)]))

st.divider()

# ── Layout ────────────────────────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

# ════════════════════════════════════════════════
# LEFT — Add Availability
# ════════════════════════════════════════════════
with left:
    st.subheader("➕ Add Availability Slot")

    if not jobs:
        st.warning("No active job openings. Ask HR Admin to create job openings first.")
    else:
        job_map = {j["title"]: j["id"] for j in jobs}

        with st.form("add_slot_form", clear_on_submit=True):
            sel_job    = st.selectbox("💼 Job Role *", list(job_map.keys()))
            slot_date  = st.date_input("📅 Date *",
                                       min_value=today + timedelta(days=1),
                                       value=today + timedelta(days=1))
            tc1, tc2   = st.columns(2)
            with tc1:
                start_t = st.time_input("⏰ Start Time", value=time(10, 0))
            with tc2:
                end_t   = st.time_input("⏰ End Time",   value=time(11, 0))

            submitted = st.form_submit_button("✅ Add Slot", type="primary", use_container_width=True)

        if submitted:
            if start_t >= end_t:
                st.error("End time must be after start time.")
            else:
                sid, err = add_slot(
                    user["id"],
                    job_map[sel_job],
                    str(slot_date),
                    start_t.strftime("%H:%M"),
                    end_t.strftime("%H:%M"),
                )
                if err:
                    st.error(f"❌ Could not add slot: overlapping slot already exists for this date/time.")
                else:
                    st.success(f"✅ Slot added: **{slot_date}** | {start_t.strftime('%H:%M')} – {end_t.strftime('%H:%M')} | {sel_job}")
                    st.rerun()

        # ── Batch Add ──────────────────────────────────────────────────────
        st.divider()
        st.subheader("📆 Batch Add (Multiple Days)")

        with st.form("batch_form", clear_on_submit=False):
            b_job      = st.selectbox("💼 Job Role *", list(job_map.keys()), key="b_job")
            bc1, bc2   = st.columns(2)
            with bc1:
                b_from = st.date_input("From", value=today + timedelta(days=1),
                                       min_value=today + timedelta(days=1))
            with bc2:
                b_to   = st.date_input("To",   value=today + timedelta(days=5),
                                       min_value=today + timedelta(days=2))
            btc1, btc2 = st.columns(2)
            with btc1:
                b_st   = st.time_input("Start", value=time(10, 0), key="b_st")
            with btc2:
                b_et   = st.time_input("End",   value=time(11, 0), key="b_et")
            skip_wknd  = st.checkbox("Skip weekends", value=True)
            b_sub      = st.form_submit_button("📆 Add All Slots", type="primary", use_container_width=True)

        if b_sub:
            if b_st >= b_et:
                st.error("End time must be after start time.")
            elif b_from >= b_to:
                st.error("End date must be after start date.")
            else:
                created = 0
                cur     = b_from
                while cur <= b_to:
                    if not (skip_wknd and cur.weekday() >= 5):
                        _, err = add_slot(user["id"], job_map[b_job], str(cur),
                                         b_st.strftime("%H:%M"), b_et.strftime("%H:%M"))
                        if not err:
                            created += 1
                    cur += timedelta(days=1)
                st.success(f"✅ Created **{created}** slots!")
                st.rerun()

# ════════════════════════════════════════════════
# RIGHT — My Slots & Upcoming Interviews
# ════════════════════════════════════════════════
with right:
    st.subheader("📅 My Available Slots")

    if not available_slots:
        st.info("No upcoming available slots. Add slots using the form on the left.")
    else:
        for s in available_slots:
            with st.container(border=True):
                sc1, sc2, sc3 = st.columns([3, 3, 1])
                with sc1:
                    st.markdown(f"**📅 {s['date']}**  |  {s['start_time']} – {s['end_time']}")
                with sc2:
                    st.caption(f"💼 {s['job_title']}")
                with sc3:
                    if st.button("🗑️", key=f"del_{s['id']}", help="Delete slot"):
                        delete_slot(s["id"], user["id"])
                        st.toast("Slot deleted.")
                        st.rerun()

    st.divider()
    st.subheader("🔵 My Upcoming Interviews")

    upcoming = [b for b in my_bookings if b["date"] >= str(today)]
    if not upcoming:
        st.info("No upcoming interviews yet.")
    else:
        for b in upcoming:
            with st.container(border=True):
                ic1, ic2 = st.columns([3, 2])
                with ic1:
                    st.markdown(f"**👤 {b['candidate_name']}**")
                    st.caption(f"📧 {b['candidate_email']}")
                    st.caption(f"📱 {b['candidate_phone'] or '—'}")
                    st.caption(f"💼 {b['job_title']}")
                with ic2:
                    st.markdown(f"**📅 {b['date']}**")
                    st.caption(f"🕐 {b['start_time']} – {b['end_time']} IST")
                    if b.get("meeting_link"):
                        st.link_button("🎥 Join Meet", b["meeting_link"],
                                       type="primary", use_container_width=True)

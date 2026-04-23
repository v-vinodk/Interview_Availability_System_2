"""
Database — SQLite schema, seed data, and all queries.
Three roles: HR_ADMIN, INTERVIEWER, CANDIDATE (public)
"""
import sqlite3, uuid, hashlib, os
from datetime import datetime, timedelta, timezone
import pytz

DB_PATH = "interview.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

# ─── Schema ───────────────────────────────────────────────────────────────────
def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id            TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        email         TEXT UNIQUE NOT NULL,
        role          TEXT NOT NULL,          -- HR_ADMIN | INTERVIEWER
        password_hash TEXT NOT NULL,
        created_at    TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS job_openings (
        id          TEXT PRIMARY KEY,
        title       TEXT NOT NULL,
        department  TEXT,
        description TEXT,
        is_active   INTEGER DEFAULT 1,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS availability_slots (
        id             TEXT PRIMARY KEY,
        interviewer_id TEXT NOT NULL,
        job_id         TEXT NOT NULL,
        date           TEXT NOT NULL,   -- YYYY-MM-DD
        start_time     TEXT NOT NULL,   -- HH:MM  (IST stored as-is)
        end_time       TEXT NOT NULL,
        status         TEXT DEFAULT 'AVAILABLE',  -- AVAILABLE | BOOKED
        created_at     TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (interviewer_id) REFERENCES users(id),
        FOREIGN KEY (job_id)         REFERENCES job_openings(id)
    );

    CREATE TABLE IF NOT EXISTS candidates (
        id         TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        email      TEXT NOT NULL,
        phone      TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id             TEXT PRIMARY KEY,
        slot_id        TEXT UNIQUE NOT NULL,
        candidate_id   TEXT NOT NULL,
        meeting_link   TEXT,
        created_at     TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (slot_id)      REFERENCES availability_slots(id),
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    );

    CREATE TABLE IF NOT EXISTS email_logs (
        id         TEXT PRIMARY KEY,
        booking_id TEXT,
        to_email   TEXT,
        role       TEXT,   -- CANDIDATE | INTERVIEWER
        subject    TEXT,
        body       TEXT,
        sent_at    TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_slots_job    ON availability_slots(job_id, status);
    CREATE INDEX IF NOT EXISTS idx_slots_iv     ON availability_slots(interviewer_id, status);
    CREATE INDEX IF NOT EXISTS idx_bookings_sl  ON bookings(slot_id);
    """)
    conn.commit()
    _seed(conn)
    conn.close()

# ─── Seed ─────────────────────────────────────────────────────────────────────
def _seed(conn):
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return

    # Users
    users = [
        (str(uuid.uuid4()), "HR Manager",   "hr@demo.com",     "HR_ADMIN",    _hash("hr123")),
        ("iv-001",           "John Doe",     "john@demo.com",   "INTERVIEWER", _hash("demo123")),
        ("iv-002",           "Priya Sharma", "priya@demo.com",  "INTERVIEWER", _hash("demo123")),
        ("iv-003",           "Arjun Singh",  "arjun@demo.com",  "INTERVIEWER", _hash("demo123")),
    ]
    conn.executemany("INSERT INTO users (id,name,email,role,password_hash) VALUES (?,?,?,?,?)", users)

    # Job Openings
    jobs = [
        ("job-001", "Software Engineer – Backend",  "Engineering",  "Python, Node.js, PostgreSQL"),
        ("job-002", "Software Engineer – Frontend", "Engineering",  "React, TypeScript, Tailwind"),
        ("job-003", "Product Manager",              "Product",      "0-3 years PM experience"),
        ("job-004", "Data Scientist",               "Data & AI",    "ML, Python, SQL"),
        ("job-005", "DevOps Engineer",              "Infrastructure","AWS, Docker, Kubernetes"),
    ]
    conn.executemany("INSERT INTO job_openings (id,title,department,description) VALUES (?,?,?,?)", jobs)

    # Availability Slots (next 5 working days for each interviewer)
    today = datetime.now(timezone.utc).date()
    times = [("09:00","10:00"), ("10:30","11:30"), ("14:00","15:00"), ("15:30","16:30")]
    iv_job_map = {
        "iv-001": ["job-001","job-002"],
        "iv-002": ["job-003","job-004"],
        "iv-003": ["job-001","job-005"],
    }
    rows = []
    for iv_id, jobs_list in iv_job_map.items():
        day_count = 0
        check_date = today + timedelta(days=1)
        while day_count < 5:
            if check_date.weekday() < 5:  # Mon–Fri
                for job_id in jobs_list:
                    for st, et in times[:2]:
                        rows.append((str(uuid.uuid4()), iv_id, job_id,
                                     str(check_date), st, et, "AVAILABLE"))
                day_count += 1
            check_date += timedelta(days=1)
    conn.executemany(
        "INSERT INTO availability_slots (id,interviewer_id,job_id,date,start_time,end_time,status) VALUES (?,?,?,?,?,?,?)",
        rows
    )

    # One demo booking
    cid = str(uuid.uuid4())
    conn.execute("INSERT INTO candidates (id,name,email,phone) VALUES (?,?,?,?)",
                 (cid, "Rahul Verma", "rahul@example.com", "+91-9876543210"))
    slot = conn.execute("SELECT id FROM availability_slots WHERE interviewer_id='iv-001' LIMIT 1").fetchone()
    if slot:
        meet = f"https://meet.google.com/{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:3]}"
        bid  = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO bookings (id,slot_id,candidate_id,meeting_link) VALUES (?,?,?,?)",
            (bid, slot["id"], cid, meet)
        )
        conn.execute("UPDATE availability_slots SET status='BOOKED' WHERE id=?", (slot["id"],))
    conn.commit()

# ─── AUTH ─────────────────────────────────────────────────────────────────────
def login(email, password):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    conn.close()
    if row and row["password_hash"] == _hash(password):
        return dict(row)
    return None

def register_user(name, email, password, role):
    uid = str(uuid.uuid4())
    conn = get_conn()
    try:
        conn.execute("INSERT INTO users (id,name,email,role,password_hash) VALUES (?,?,?,?,?)",
                     (uid, name, email.lower(), role, _hash(password)))
        conn.commit()
        return uid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

# ─── JOB OPENINGS ─────────────────────────────────────────────────────────────
def get_jobs(active_only=True):
    conn = get_conn()
    q = "SELECT * FROM job_openings" + (" WHERE is_active=1" if active_only else "") + " ORDER BY title"
    rows = [dict(r) for r in conn.execute(q).fetchall()]
    conn.close()
    return rows

def create_job(title, department, description):
    jid = str(uuid.uuid4())
    conn = get_conn()
    conn.execute("INSERT INTO job_openings (id,title,department,description) VALUES (?,?,?,?)",
                 (jid, title, department, description))
    conn.commit()
    conn.close()
    return jid

def toggle_job(job_id, active):
    conn = get_conn()
    conn.execute("UPDATE job_openings SET is_active=? WHERE id=?", (1 if active else 0, job_id))
    conn.commit()
    conn.close()

# ─── SLOTS ────────────────────────────────────────────────────────────────────
def get_slots_for_interviewer(interviewer_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.*, j.title as job_title, j.department
        FROM availability_slots s
        JOIN job_openings j ON s.job_id = j.id
        WHERE s.interviewer_id = ?
        ORDER BY s.date, s.start_time
    """, (interviewer_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_available_slots_for_job(job_id):
    conn = get_conn()
    today = str(datetime.now(timezone.utc).date())
    rows = conn.execute("""
        SELECT s.*, u.name as interviewer_name, j.title as job_title
        FROM availability_slots s
        JOIN users u ON s.interviewer_id = u.id
        JOIN job_openings j ON s.job_id = j.id
        WHERE s.job_id = ? AND s.status = 'AVAILABLE' AND s.date >= ?
        ORDER BY s.date, s.start_time
    """, (job_id, today)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_slots():
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.*, u.name as interviewer_name, j.title as job_title, j.department
        FROM availability_slots s
        JOIN users u ON s.interviewer_id = u.id
        JOIN job_openings j ON s.job_id = j.id
        ORDER BY s.date DESC, s.start_time
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_slot(interviewer_id, job_id, date, start_time, end_time):
    # Check overlap
    conn = get_conn()
    overlap = conn.execute("""
        SELECT id FROM availability_slots
        WHERE interviewer_id=? AND date=? AND status='AVAILABLE'
          AND NOT (end_time <= ? OR start_time >= ?)
    """, (interviewer_id, date, start_time, end_time)).fetchone()
    if overlap:
        conn.close()
        return None, "overlapping slot exists"
    sid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO availability_slots (id,interviewer_id,job_id,date,start_time,end_time) VALUES (?,?,?,?,?,?)",
        (sid, interviewer_id, job_id, date, start_time, end_time)
    )
    conn.commit()
    conn.close()
    return sid, None

def delete_slot(slot_id, interviewer_id):
    conn = get_conn()
    conn.execute("DELETE FROM availability_slots WHERE id=? AND interviewer_id=? AND status='AVAILABLE'",
                 (slot_id, interviewer_id))
    conn.commit()
    conn.close()

# ─── BOOKINGS ─────────────────────────────────────────────────────────────────
def book_slot(slot_id, cand_name, cand_email, cand_phone):
    conn = get_conn()
    # Verify still available
    slot = conn.execute(
        "SELECT * FROM availability_slots WHERE id=? AND status='AVAILABLE'", (slot_id,)
    ).fetchone()
    if not slot:
        conn.close()
        return None, "Slot no longer available — please choose another."

    # Upsert candidate
    existing = conn.execute("SELECT id FROM candidates WHERE email=?", (cand_email,)).fetchone()
    if existing:
        cid = existing["id"]
    else:
        cid = str(uuid.uuid4())
        conn.execute("INSERT INTO candidates (id,name,email,phone) VALUES (?,?,?,?)",
                     (cid, cand_name, cand_email, cand_phone))

    # Mock Meet link
    meet = f"https://meet.google.com/{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:3]}"

    # Create booking + mark slot booked
    bid = str(uuid.uuid4())
    conn.execute("INSERT INTO bookings (id,slot_id,candidate_id,meeting_link) VALUES (?,?,?,?)",
                 (bid, slot_id, cid, meet))
    conn.execute("UPDATE availability_slots SET status='BOOKED' WHERE id=?", (slot_id,))
    conn.commit()

    booking = {
        "id": bid, "slot_id": slot_id,
        "meeting_link": meet,
        "slot": dict(slot),
    }
    conn.close()
    return booking, None

def get_all_bookings():
    conn = get_conn()
    rows = conn.execute("""
        SELECT b.id, b.meeting_link, b.created_at,
               c.name  as candidate_name, c.email as candidate_email, c.phone as candidate_phone,
               s.date, s.start_time, s.end_time,
               u.name  as interviewer_name, u.email as interviewer_email,
               j.title as job_title, j.department
        FROM bookings b
        JOIN availability_slots s ON b.slot_id = s.id
        JOIN candidates c ON b.candidate_id = c.id
        JOIN users u ON s.interviewer_id = u.id
        JOIN job_openings j ON s.job_id = j.id
        ORDER BY s.date DESC, s.start_time
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── EMAIL LOGS ───────────────────────────────────────────────────────────────
def log_email(booking_id, to_email, role, subject, body):
    conn = get_conn()
    conn.execute("INSERT INTO email_logs (id,booking_id,to_email,role,subject,body) VALUES (?,?,?,?,?,?)",
                 (str(uuid.uuid4()), booking_id, to_email, role, subject, body))
    conn.commit()
    conn.close()

def get_all_emails():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM email_logs ORDER BY sent_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── STATS ────────────────────────────────────────────────────────────────────
def get_stats():
    conn = get_conn()
    return {
        "total_slots":     conn.execute("SELECT COUNT(*) FROM availability_slots").fetchone()[0],
        "available_slots": conn.execute("SELECT COUNT(*) FROM availability_slots WHERE status='AVAILABLE'").fetchone()[0],
        "booked_slots":    conn.execute("SELECT COUNT(*) FROM availability_slots WHERE status='BOOKED'").fetchone()[0],
        "total_bookings":  conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        "total_candidates":conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
        "active_jobs":     conn.execute("SELECT COUNT(*) FROM job_openings WHERE is_active=1").fetchone()[0],
    }

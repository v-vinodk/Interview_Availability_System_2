"""
Database — SQLite schema, seed data, and all queries.
Three roles: HR_ADMIN, INTERVIEWER, CANDIDATE (pre-registered by HR)
"""
import sqlite3, uuid, hashlib, os, tempfile
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(tempfile.gettempdir(), "interview_v3.db")


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
        role          TEXT NOT NULL,
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

    -- HR pre-registers candidates for specific roles
    CREATE TABLE IF NOT EXISTS candidate_applications (
        id         TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        email      TEXT NOT NULL,
        phone      TEXT,
        job_id     TEXT NOT NULL,
        status     TEXT DEFAULT 'ACTIVE',   -- ACTIVE | BOOKED | REMOVED
        added_by   TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (job_id)   REFERENCES job_openings(id),
        FOREIGN KEY (added_by) REFERENCES users(id),
        UNIQUE(email, job_id)
    );

    CREATE TABLE IF NOT EXISTS availability_slots (
        id             TEXT PRIMARY KEY,
        interviewer_id TEXT NOT NULL,
        job_id         TEXT NOT NULL,
        date           TEXT NOT NULL,
        start_time     TEXT NOT NULL,
        end_time       TEXT NOT NULL,
        status         TEXT DEFAULT 'AVAILABLE',
        created_at     TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (interviewer_id) REFERENCES users(id),
        FOREIGN KEY (job_id)         REFERENCES job_openings(id)
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id             TEXT PRIMARY KEY,
        slot_id        TEXT UNIQUE NOT NULL,
        application_id TEXT NOT NULL,
        meeting_link   TEXT,
        created_at     TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (slot_id)        REFERENCES availability_slots(id),
        FOREIGN KEY (application_id) REFERENCES candidate_applications(id)
    );

    CREATE TABLE IF NOT EXISTS email_logs (
        id         TEXT PRIMARY KEY,
        booking_id TEXT,
        to_email   TEXT,
        role       TEXT,
        subject    TEXT,
        body       TEXT,
        sent_at    TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_slots_job    ON availability_slots(job_id, status);
    CREATE INDEX IF NOT EXISTS idx_app_email    ON candidate_applications(email);
    CREATE INDEX IF NOT EXISTS idx_app_job      ON candidate_applications(job_id, status);
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
        (str(uuid.uuid4()), "HR Manager",   "hr@demo.com",    "HR_ADMIN",    _hash("hr123")),
        ("iv-001",           "John Doe",     "john@demo.com",  "INTERVIEWER", _hash("demo123")),
        ("iv-002",           "Priya Sharma", "priya@demo.com", "INTERVIEWER", _hash("demo123")),
        ("iv-003",           "Arjun Singh",  "arjun@demo.com", "INTERVIEWER", _hash("demo123")),
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

    # Pre-registered candidates (HR added them)
    hr_id = conn.execute("SELECT id FROM users WHERE role='HR_ADMIN'").fetchone()["id"]
    apps = [
        (str(uuid.uuid4()), "Rahul Verma",   "rahul@example.com",  "+91-9876543210", "job-001", "ACTIVE", hr_id),
        (str(uuid.uuid4()), "Sneha Patel",   "sneha@example.com",  "+91-9123456780", "job-002", "ACTIVE", hr_id),
        (str(uuid.uuid4()), "Amit Sharma",   "amit@example.com",   "+91-9988776655", "job-003", "ACTIVE", hr_id),
        (str(uuid.uuid4()), "Kavya Reddy",   "kavya@example.com",  "+91-9845123456", "job-004", "ACTIVE", hr_id),
        (str(uuid.uuid4()), "Demo Candidate","demo@candidate.com", "+91-9000000001", "job-001", "ACTIVE", hr_id),
    ]
    conn.executemany(
        "INSERT INTO candidate_applications (id,name,email,phone,job_id,status,added_by) VALUES (?,?,?,?,?,?,?)",
        apps
    )

    # Availability slots (next 5 working days)
    today = datetime.now(timezone.utc).date()
    times = [("09:00","10:00"), ("10:30","11:30"), ("14:00","15:00"), ("15:30","16:30")]
    iv_job_map = {
        "iv-001": ["job-001", "job-002"],
        "iv-002": ["job-003", "job-004"],
        "iv-003": ["job-001", "job-005"],
    }
    rows = []
    for iv_id, job_list in iv_job_map.items():
        day_count, check = 0, today + timedelta(days=1)
        while day_count < 5:
            if check.weekday() < 5:
                for jid in job_list:
                    for st, et in times[:2]:
                        rows.append((str(uuid.uuid4()), iv_id, jid, str(check), st, et, "AVAILABLE"))
                day_count += 1
            check += timedelta(days=1)
    conn.executemany(
        "INSERT INTO availability_slots (id,interviewer_id,job_id,date,start_time,end_time,status) VALUES (?,?,?,?,?,?,?)",
        rows
    )
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
    conn.commit(); conn.close()
    return jid

def toggle_job(job_id, active):
    conn = get_conn()
    conn.execute("UPDATE job_openings SET is_active=? WHERE id=?", (1 if active else 0, job_id))
    conn.commit(); conn.close()


# ─── CANDIDATE APPLICATIONS (HR manages) ──────────────────────────────────────
def add_candidate(name, email, phone, job_id, hr_user_id):
    """HR adds a candidate to the selection list for a specific role."""
    conn = get_conn()
    try:
        cid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO candidate_applications (id,name,email,phone,job_id,status,added_by) VALUES (?,?,?,?,?,?,?)",
            (cid, name.strip(), email.strip().lower(), phone.strip(), job_id, "ACTIVE", hr_user_id)
        )
        conn.commit()
        return cid, None
    except sqlite3.IntegrityError:
        return None, "This candidate is already registered for this role."
    finally:
        conn.close()

def remove_candidate(app_id):
    conn = get_conn()
    conn.execute("UPDATE candidate_applications SET status='REMOVED' WHERE id=?", (app_id,))
    conn.commit(); conn.close()

def get_all_applications():
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.*, j.title as job_title, j.department, u.name as added_by_name
        FROM candidate_applications a
        JOIN job_openings j ON a.job_id = j.id
        LEFT JOIN users u ON a.added_by = u.id
        ORDER BY a.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def verify_candidate_email(email):
    """Security gate: check if email is pre-registered by HR. Returns application or None."""
    conn = get_conn()
    row = conn.execute("""
        SELECT a.*, j.title as job_title, j.department, j.id as job_id
        FROM candidate_applications a
        JOIN job_openings j ON a.job_id = j.id
        WHERE LOWER(a.email) = LOWER(?) AND a.status = 'ACTIVE'
        LIMIT 1
    """, (email.strip(),)).fetchone()
    conn.close()
    return dict(row) if row else None


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
    today = str(datetime.now(timezone.utc).date())
    conn  = get_conn()
    rows  = conn.execute("""
        SELECT s.*, u.name as interviewer_name, u.email as interviewer_email, j.title as job_title
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
    conn = get_conn()
    overlap = conn.execute("""
        SELECT id FROM availability_slots
        WHERE interviewer_id=? AND date=? AND status='AVAILABLE'
          AND NOT (end_time <= ? OR start_time >= ?)
    """, (interviewer_id, date, start_time, end_time)).fetchone()
    if overlap:
        conn.close()
        return None, "overlapping slot"
    sid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO availability_slots (id,interviewer_id,job_id,date,start_time,end_time) VALUES (?,?,?,?,?,?)",
        (sid, interviewer_id, job_id, date, start_time, end_time)
    )
    conn.commit(); conn.close()
    return sid, None

def delete_slot(slot_id, interviewer_id):
    conn = get_conn()
    conn.execute("DELETE FROM availability_slots WHERE id=? AND interviewer_id=? AND status='AVAILABLE'",
                 (slot_id, interviewer_id))
    conn.commit(); conn.close()


# ─── BOOKINGS ─────────────────────────────────────────────────────────────────
def book_slot(slot_id, application_id, meet_link):
    """Atomically book a slot. meet_link already generated before calling this."""
    conn = get_conn()
    slot = conn.execute(
        "SELECT * FROM availability_slots WHERE id=? AND status='AVAILABLE'", (slot_id,)
    ).fetchone()
    if not slot:
        conn.close()
        return None, "Slot no longer available — please choose another."
    bid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO bookings (id,slot_id,application_id,meeting_link) VALUES (?,?,?,?)",
        (bid, slot_id, application_id, meet_link)
    )
    conn.execute("UPDATE availability_slots SET status='BOOKED' WHERE id=?", (slot_id,))
    conn.execute("UPDATE candidate_applications SET status='BOOKED' WHERE id=?", (application_id,))
    conn.commit()
    booking = dict(conn.execute("SELECT * FROM bookings WHERE id=?", (bid,)).fetchone())
    conn.close()
    return booking, None

def get_all_bookings():
    conn = get_conn()
    rows = conn.execute("""
        SELECT b.id, b.meeting_link, b.created_at,
               a.name  as candidate_name, a.email as candidate_email, a.phone as candidate_phone,
               s.date, s.start_time, s.end_time,
               u.name  as interviewer_name, u.email as interviewer_email,
               j.title as job_title, j.department
        FROM bookings b
        JOIN availability_slots s ON b.slot_id = s.id
        JOIN candidate_applications a ON b.application_id = a.id
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
    conn.commit(); conn.close()

def get_all_emails():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM email_logs ORDER BY sent_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── STATS ────────────────────────────────────────────────────────────────────
def get_stats():
    conn = get_conn()
    s = {
        "total_slots":      conn.execute("SELECT COUNT(*) FROM availability_slots").fetchone()[0],
        "available_slots":  conn.execute("SELECT COUNT(*) FROM availability_slots WHERE status='AVAILABLE'").fetchone()[0],
        "booked_slots":     conn.execute("SELECT COUNT(*) FROM availability_slots WHERE status='BOOKED'").fetchone()[0],
        "total_bookings":   conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        "total_candidates": conn.execute("SELECT COUNT(*) FROM candidate_applications WHERE status!='REMOVED'").fetchone()[0],
        "active_jobs":      conn.execute("SELECT COUNT(*) FROM job_openings WHERE is_active=1").fetchone()[0],
        "pending":          conn.execute("SELECT COUNT(*) FROM candidate_applications WHERE status='ACTIVE'").fetchone()[0],
    }
    conn.close()
    return s

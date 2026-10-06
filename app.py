"""SchoolWeb - har school ki apni website + online admission system.
Run:  venv/bin/python app.py   ->  http://localhost:5000
DB:   schoolweb.db (SQLite, auto-created)
"""
import os, re, sqlite3, smtplib, secrets
from email.mime.text import MIMEText
from datetime import datetime
from flask import Flask, request, session, redirect, url_for, render_template, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "schoolweb.db")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # photo max 4MB

# student photos: static/uploads/ (Flask khud serve karta hai)
UPLOAD_DIR = os.path.join(BASE, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}

# secret key: pehli dafa generate karke file me save (sessions secure rahen)
KEYFILE = os.path.join(BASE, "secret.key")
if os.path.exists(KEYFILE):
    app.secret_key = open(KEYFILE, "rb").read()
else:
    app.secret_key = secrets.token_bytes(32)
    open(KEYFILE, "wb").write(app.secret_key)

SLUG_RE = re.compile(r"^[a-z0-9-]{3,40}$")

# ---------- DB ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_e=None):
    d = g.pop("db", None)
    if d is not None:
        d.close()

def init_db():
    d = sqlite3.connect(DB)
    d.row_factory = sqlite3.Row
    d.executescript("""
    CREATE TABLE IF NOT EXISTS schools(
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL,
        phone TEXT DEFAULT '', address TEXT DEFAULT '',
        intro TEXT DEFAULT '', principal_msg TEXT DEFAULT '',
        smtp_host TEXT DEFAULT '', smtp_port INTEGER DEFAULT 587,
        smtp_user TEXT DEFAULT '', smtp_pass TEXT DEFAULT '',
        smtp_tls INTEGER DEFAULT 1, notify_email TEXT DEFAULT '',
        created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS notices(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        title TEXT NOT NULL, body TEXT DEFAULT '', created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS applications(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        student_name TEXT NOT NULL, father_name TEXT DEFAULT '',
        dob TEXT DEFAULT '', gender TEXT DEFAULT '',
        class_applying TEXT DEFAULT '', prev_school TEXT DEFAULT '',
        phone TEXT DEFAULT '', address TEXT DEFAULT '',
        app_id TEXT DEFAULT '', photo TEXT DEFAULT '',
        status TEXT DEFAULT 'pending', created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        name TEXT NOT NULL, father_name TEXT DEFAULT '', gender TEXT DEFAULT '',
        dob TEXT DEFAULT '', class TEXT DEFAULT '', section TEXT DEFAULT '',
        phone TEXT DEFAULT '', address TEXT DEFAULT '',
        photo TEXT DEFAULT '', app_id TEXT DEFAULT '',
        admission_date TEXT DEFAULT '', status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS fee_heads(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        name TEXT NOT NULL, amount REAL DEFAULT 0,
        classes TEXT DEFAULT 'all', freq TEXT DEFAULT 'monthly',
        created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS invoices(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL, month TEXT NOT NULL,
        items TEXT DEFAULT '', total REAL DEFAULT 0, paid REAL DEFAULT 0,
        status TEXT DEFAULT 'unpaid', receipt_no TEXT DEFAULT '',
        created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL,
        amount REAL DEFAULT 0, pay_date TEXT DEFAULT '',
        method TEXT DEFAULT 'cash', note TEXT DEFAULT '',
        created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL, date TEXT NOT NULL,
        status TEXT DEFAULT 'present',
        UNIQUE(school_id, student_id, date));
    CREATE TABLE IF NOT EXISTS exams(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        name TEXT NOT NULL, year INTEGER DEFAULT 0,
        subjects TEXT DEFAULT '', created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS marks(
        id INTEGER PRIMARY KEY, exam_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL, subject TEXT NOT NULL,
        obtained REAL DEFAULT 0, total REAL DEFAULT 100,
        UNIQUE(exam_id, student_id, subject));
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        name TEXT NOT NULL, email TEXT NOT NULL, pw_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'teacher', active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT '',
        UNIQUE(school_id, email));
    CREATE TABLE IF NOT EXISTS staff(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        name TEXT NOT NULL, father_name TEXT DEFAULT '',
        phone TEXT DEFAULT '', address TEXT DEFAULT '',
        designation TEXT DEFAULT 'Teacher', salary_monthly REAL DEFAULT 0,
        join_date TEXT DEFAULT '', status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS staff_attendance(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        staff_id INTEGER NOT NULL, date TEXT NOT NULL,
        status TEXT DEFAULT 'present',
        UNIQUE(school_id, staff_id, date));
    CREATE TABLE IF NOT EXISTS salary_slips(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        staff_id INTEGER NOT NULL, month TEXT NOT NULL,
        basic REAL DEFAULT 0, allowances REAL DEFAULT 0,
        deductions REAL DEFAULT 0, advance REAL DEFAULT 0,
        net REAL DEFAULT 0, paid INTEGER DEFAULT 0,
        pay_date TEXT DEFAULT '', created_at TEXT DEFAULT '',
        UNIQUE(school_id, staff_id, month));
    CREATE TABLE IF NOT EXISTS diary(
        id INTEGER PRIMARY KEY, school_id INTEGER NOT NULL,
        class TEXT NOT NULL, date TEXT NOT NULL,
        subject TEXT DEFAULT '', text TEXT NOT NULL,
        teacher TEXT DEFAULT '', created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS parent_tokens(
        student_id INTEGER PRIMARY KEY, token TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT '');
    """)
    # migration: purani DB me naye columns add karo + khali IDs backfill
    cols = [r[1] for r in d.execute("PRAGMA table_info(applications)")]
    if "app_id" not in cols:
        d.execute("ALTER TABLE applications ADD COLUMN app_id TEXT DEFAULT ''")
    if "photo" not in cols:
        d.execute("ALTER TABLE applications ADD COLUMN photo TEXT DEFAULT ''")
    # v4 migrations: fee discount + payment proof
    inv_cols = [r[1] for r in d.execute("PRAGMA table_info(invoices)")]
    if inv_cols and "discount" not in inv_cols:
        d.execute("ALTER TABLE invoices ADD COLUMN discount REAL DEFAULT 0")
    pay_cols = [r[1] for r in d.execute("PRAGMA table_info(payments)")]
    if pay_cols and "proof" not in pay_cols:
        d.execute("ALTER TABLE payments ADD COLUMN proof TEXT DEFAULT ''")
    if pay_cols and "verified" not in pay_cols:
        d.execute("ALTER TABLE payments ADD COLUMN verified INTEGER DEFAULT 1")
    year = datetime.now().year
    for s in d.execute("SELECT id, name FROM schools").fetchall():
        prefix = "".join(w[0] for w in (s["name"] or "").split() if w and w[0].isalpha())[:4].upper() or "SW"
        have = d.execute(
            "SELECT COUNT(*) FROM applications WHERE school_id=? AND app_id LIKE ?",
            (s["id"], f"{prefix}-{year}-%")).fetchone()[0]
        rows = d.execute(
            "SELECT id FROM applications WHERE school_id=? AND (app_id IS NULL OR app_id='') ORDER BY id",
            (s["id"],)).fetchall()
        for i, r in enumerate(rows, start=have + 1):
            d.execute("UPDATE applications SET app_id=? WHERE id=?",
                      (f"{prefix}-{year}-{i:04d}", r["id"]))
    d.commit(); d.close()

def make_app_id(school_id, school_name):
    """Naya unique application ID: PREFIX-YEAR-0001 (misal FIS-2026-0001)."""
    d = db(); year = datetime.now().year
    prefix = "".join(w[0] for w in (school_name or "").split() if w and w[0].isalpha())[:4].upper() or "SW"
    n = d.execute("SELECT COUNT(*) c FROM applications WHERE school_id=?",
                  (school_id,)).fetchone()["c"] + 1
    app_id = f"{prefix}-{year}-{n:04d}"
    while d.execute("SELECT 1 FROM applications WHERE app_id=?",
                    (app_id,)).fetchone():
        n += 1; app_id = f"{prefix}-{year}-{n:04d}"
    return app_id

def school_prefix(name):
    return "".join(w[0] for w in (name or "").split() if w and w[0].isalpha())[:4].upper() or "SW"

def student_classes(school_id):
    rows = db().execute(
        "SELECT DISTINCT class FROM students WHERE school_id=? AND status='active' AND class!='' ORDER BY class",
        (school_id,)).fetchall()
    return [r["class"] for r in rows]

def wa_link(phone, msg):
    """Free WhatsApp: wa.me link with prefilled message (koi paid API nahi)."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("0"):
        digits = "92" + digits[1:]
    if not digits:
        return ""
    from urllib.parse import quote
    return f"https://wa.me/{digits}?text={quote(msg)}"

def grade_of(pct):
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    return "F"

def fmt(n):
    return ("%.0f" % n) if float(n) == int(float(n)) else ("%.1f" % n)

# ---------- Urdu/English strings (public site) ----------
STR = {
 "en": {"home":"Home","apply":"Online Admission","notices":"Notices","principal":"Principal's Message",
        "about":"About Us","contact":"Contact","welcome":"Welcome to","fill":"Fill the admission form below.",
        "sname":"Student Name","fname":"Father Name","dob":"Date of Birth","gender":"Gender",
        "male":"Male","female":"Female","class":"Class Applying For","pschool":"Previous School",
        "phone":"Phone","address":"Address","submit":"Submit Application",
        "done":"Application submitted! The school will contact you soon.",
        "your_app_id":"Your Application ID",
        "save_id":"Note this number down — you'll need it when asking about your application.",
        "photo":"Photo","id_card":"Student ID Card","print":"🖨️ Print Card",
        "back_dash":"Back to Dashboard",
        "no_notices":"No notices yet.","read_more":"",
        "tag_admission":"Admissions Open 2026–27","quick":"Quick Links",
        "online100":"100% Online Admission","bilingual":"Urdu + English",
        "view_notices":"See Notices","cta_title":"Want admission?",
        "cta_text":"Fill the online form — it takes 2 minutes. The school will contact you soon."},
 "ur": {"home":"ہوم","apply":"آن لائن داخلہ","notices":"نوٹسز","principal":"پرنسپل کا پیغام",
        "about":"ہمارے بارے میں","contact":"رابطہ","welcome":"خوش آمدید",
        "fill":"نیچے داخلہ فارم پُر کریں۔",
        "sname":"طالب علم کا نام","fname":"والد کا نام","dob":"تاریخ پیدائش","gender":"صنف",
        "male":"لڑکا","female":"لڑکی","class":"داخلے کی جماعت","pschool":"پچھلا اسکول",
        "phone":"فون","address":"پتہ","submit":"درخواست جمع کرائیں",
        "done":"درخواست جمع ہو گئی! اسکول جلد رابطہ کرے گا۔",
        "your_app_id":"آپ کی درخواست کا نمبر",
        "save_id":"یہ نمبر نوٹ کر لیں — درخواست کے بارے میں پوچھنے کے لیے اس کی ضرورت ہوگی۔",
        "photo":"تصویر","id_card":"طالب علم کا شناختی کارڈ","print":"🖨️ کارڈ پرنٹ کریں",
        "back_dash":"ڈیش بورڈ پر واپس",
        "no_notices":"ابھی کوئی نوٹس نہیں۔","read_more":"",
        "tag_admission":"داخلے جاری ہیں 2026–27","quick":"فوری لنکس",
        "online100":"100% آن لائن داخلہ","bilingual":"اردو + English",
        "view_notices":"نوٹسز دیکھیں","cta_title":"داخلہ چاہیے؟",
        "cta_text":"آن لائن فارم پُر کریں — صرف 2 منٹ لگیں گے۔ اسکول جلد رابطہ کرے گا۔"},
}
def T(key):
    lang = session.get("lang", "en")
    return STR.get(lang, STR["en"]).get(key, key)

@app.context_processor
def inject():
    lang = session.get("lang", "en")
    return {"T": T, "lang": lang, "rtl": lang == "ur"}

# ---------- helpers ----------
def current_school():
    sid = session.get("school_id")
    if not sid: return None
    return db().execute("SELECT * FROM schools WHERE id=?", (sid,)).fetchone()

def current_role():
    """'owner' | 'teacher' | 'accountant' | None"""
    if not current_school(): return None
    return session.get("role", "owner")

def current_user_name():
    return session.get("user_name", "")

def require_role(*roles):
    from functools import wraps
    def deco(fn):
        @wraps(fn)
        def w(*a, **k):
            if current_role() not in roles:
                flash("⛔ Is page ki permission nahi hai.")
                return redirect(url_for("dashboard"))
            return fn(*a, **k)
        return w
    return deco

# payment proof uploads
PROOF_DIR = os.path.join(BASE, "static", "uploads", "proofs")
os.makedirs(PROOF_DIR, exist_ok=True)

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def w(*a, **k):
        if not current_school(): return redirect(url_for("login"))
        return fn(*a, **k)
    return w

def get_school_or_404(slug):
    s = db().execute("SELECT * FROM schools WHERE slug=?", (slug,)).fetchone()
    if not s:
        return None
    return s

def send_email(school, subject, body):
    """Admission notification. Fail hua to khamoshi se skip (form nahi toot'ta)."""
    if not school["notify_email"] or not school["smtp_host"] or not school["smtp_user"]:
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"], msg["From"], msg["To"] = subject, school["smtp_user"], school["notify_email"]
        if school["smtp_tls"]:
            srv = smtplib.SMTP(school["smtp_host"], school["smtp_port"], timeout=15)
            srv.starttls()
        else:
            srv = smtplib.SMTP_SSL(school["smtp_host"], school["smtp_port"], timeout=15)
        srv.login(school["smtp_user"], school["smtp_pass"])
        srv.send_message(msg); srv.quit()
        return True
    except Exception:
        return False

# ---------- Landing / auth ----------
@app.route("/")
def index():
    n = db().execute("SELECT COUNT(*) c FROM schools").fetchone()["c"]
    return render_template("landing.html", school_count=n)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        if not (name and slug and email and pw):
            flash("Saray fields zaroori hain."); return render_template("register.html")
        if not SLUG_RE.match(slug):
            flash("Slug me sirf a-z, 0-9 aur - (3-40 chars)."); return render_template("register.html")
        d = db()
        if d.execute("SELECT 1 FROM schools WHERE slug=? OR email=?", (slug, email)).fetchone():
            flash("Ye slug ya email pehle se registered hai."); return render_template("register.html")
        d.execute("""INSERT INTO schools(name,slug,email,pw_hash,created_at)
                     VALUES(?,?,?,?,?)""",
                  (name, slug, email, generate_password_hash(pw), datetime.now().isoformat()))
        d.commit()
        sid = d.execute("SELECT id FROM schools WHERE slug=?", (slug,)).fetchone()["id"]
        session["school_id"] = sid
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        s = db().execute("SELECT * FROM schools WHERE email=?", (email,)).fetchone()
        if s and check_password_hash(s["pw_hash"], pw):
            session["school_id"] = s["id"]
            session["role"] = "owner"
            session["user_name"] = "Owner"
            return redirect(url_for("dashboard"))
        # team logins: teacher / accountant
        u = db().execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
        if u and check_password_hash(u["pw_hash"], pw):
            session["school_id"] = u["school_id"]
            session["role"] = u["role"]
            session["user_name"] = u["name"]
            return redirect(url_for("dashboard"))
        flash("Email ya password ghalat.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("school_id", None)
    session.pop("role", None)
    session.pop("user_name", None)
    return redirect(url_for("index"))

# ---------- Dashboard ----------
@app.route("/dashboard")
@login_required
def dashboard():
    s = current_school(); d = db()
    month = datetime.now().strftime("%Y-%m")
    today = datetime.now().date().isoformat()
    stats = {
        "total": d.execute("SELECT COUNT(*) c FROM applications WHERE school_id=?", (s["id"],)).fetchone()["c"],
        "pending": d.execute("SELECT COUNT(*) c FROM applications WHERE school_id=? AND status='pending'", (s["id"],)).fetchone()["c"],
        "approved": d.execute("SELECT COUNT(*) c FROM applications WHERE school_id=? AND status='approved'", (s["id"],)).fetchone()["c"],
        "notices": d.execute("SELECT COUNT(*) c FROM notices WHERE school_id=?", (s["id"],)).fetchone()["c"],
        "students": d.execute("SELECT COUNT(*) c FROM students WHERE school_id=? AND status='active'", (s["id"],)).fetchone()["c"],
        "fee_due": d.execute("SELECT COALESCE(SUM(total-COALESCE(discount,0)-paid),0) t FROM invoices WHERE school_id=? AND month=? AND status!='paid'", (s["id"], month)).fetchone()["t"],
        "absent_today": d.execute("SELECT COUNT(*) c FROM attendance WHERE school_id=? AND date=? AND status='absent'", (s["id"], today)).fetchone()["c"],
    }
    recent = d.execute("SELECT * FROM applications WHERE school_id=? ORDER BY id DESC LIMIT 8", (s["id"],)).fetchall()
    return render_template("dashboard.html", school=s, stats=stats, recent=recent)

@app.route("/dashboard/applications", methods=["GET", "POST"])
@login_required
@require_role("owner")
def applications():
    s = current_school(); d = db()
    if request.method == "POST":
        aid = request.form.get("id"); st = request.form.get("status")
        if st in ("pending", "approved", "rejected"):
            d.execute("UPDATE applications SET status=? WHERE id=? AND school_id=?", (st, aid, s["id"]))
            d.commit(); flash("Status update ho gaya.")
        return redirect(url_for("applications"))
    f = request.args.get("status", "")
    q = "SELECT * FROM applications WHERE school_id=?"
    args = [s["id"]]
    if f in ("pending", "approved", "rejected"):
        q += " AND status=?"; args.append(f)
    apps = d.execute(q + " ORDER BY id DESC", args).fetchall()
    return render_template("applications.html", school=s, apps=apps, f=f)

@app.route("/dashboard/applications/<int:aid>/card")
@login_required
@require_role("owner")
def app_card(aid):
    """Student ID card — print-friendly."""
    s = current_school()
    a = db().execute("SELECT * FROM applications WHERE id=? AND school_id=?",
                     (aid, s["id"])).fetchone()
    if not a:
        return "Application nahi mili.", 404
    return render_template("id_card.html", school=s, a=a)

@app.route("/dashboard/content", methods=["GET", "POST"])
@login_required
@require_role("owner")
def content():
    s = current_school(); d = db()
    if request.method == "POST":
        d.execute("""UPDATE schools SET intro=?, principal_msg=?, phone=?, address=? WHERE id=?""",
                  (request.form.get("intro", ""), request.form.get("principal_msg", ""),
                   request.form.get("phone", ""), request.form.get("address", ""), s["id"]))
        d.commit(); flash("Website content save ho gaya.")
        return redirect(url_for("content"))
    return render_template("content.html", school=s)

@app.route("/dashboard/notices", methods=["GET", "POST"])
@login_required
@require_role("owner")
def notices():
    s = current_school(); d = db()
    if request.method == "POST":
        if request.form.get("delete"):
            d.execute("DELETE FROM notices WHERE id=? AND school_id=?", (request.form["delete"], s["id"]))
        else:
            t = request.form.get("title", "").strip()
            if t:
                d.execute("INSERT INTO notices(school_id,title,body,created_at) VALUES(?,?,?,?)",
                          (s["id"], t, request.form.get("body", ""), datetime.now().isoformat()))
        d.commit()
        return redirect(url_for("notices"))
    ns = d.execute("SELECT * FROM notices WHERE school_id=? ORDER BY id DESC", (s["id"],)).fetchall()
    return render_template("notices.html", school=s, notices=ns)

@app.route("/dashboard/settings", methods=["GET", "POST"])
@login_required
@require_role("owner")
def settings():
    s = current_school(); d = db()
    if request.method == "POST":
        d.execute("""UPDATE schools SET smtp_host=?, smtp_port=?, smtp_user=?, smtp_pass=?,
                     smtp_tls=?, notify_email=? WHERE id=?""",
                  (request.form.get("smtp_host", "").strip(),
                   int(request.form.get("smtp_port", "587") or 587),
                   request.form.get("smtp_user", "").strip(),
                   request.form.get("smtp_pass", ""),
                   1 if request.form.get("smtp_tls") else 0,
                   request.form.get("notify_email", "").strip(), s["id"]))
        d.commit(); flash("Email settings save ho gayin.")
        return redirect(url_for("settings"))
    return render_template("settings.html", school=s)

# ---------- Public school website ----------
@app.route("/s/<slug>/")
def school_home(slug):
    if request.args.get("lang") in ("en", "ur"):
        session["lang"] = request.args["lang"]
    s = get_school_or_404(slug)
    if not s: return "School nahi mila.", 404
    ns = db().execute("SELECT * FROM notices WHERE school_id=? ORDER BY id DESC LIMIT 10", (s["id"],)).fetchall()
    return render_template("site_home.html", school=s, notices=ns)

@app.route("/s/<slug>/apply", methods=["GET", "POST"])
def school_apply(slug):
    if request.args.get("lang") in ("en", "ur"):
        session["lang"] = request.args["lang"]
    s = get_school_or_404(slug)
    if not s: return "School nahi mila.", 404
    if request.method == "POST":
        name = request.form.get("student_name", "").strip()
        if not name:
            flash("Student ka naam zaroori hai."); return render_template("apply.html", school=s)
        d = db()
        app_id = make_app_id(s["id"], s["name"])
        # student photo (optional): app_id ke naam se save
        photo_name = ""
        pf = request.files.get("photo")
        if pf and pf.filename:
            ext = pf.filename.rsplit(".", 1)[-1].lower() if "." in pf.filename else ""
            if ext in ALLOWED_EXT:
                photo_name = secure_filename(f"{app_id}.{ext}")
                ppath = os.path.join(UPLOAD_DIR, photo_name)
                pf.save(ppath)
                try:  # Pillow ho to photo halki kar do (disk bachao)
                    from PIL import Image
                    im = Image.open(ppath)
                    im.thumbnail((800, 800))
                    im.save(ppath)
                except Exception:
                    pass
        d.execute("""INSERT INTO applications(school_id,student_name,father_name,dob,gender,
                     class_applying,prev_school,phone,address,app_id,photo,created_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (s["id"], name, request.form.get("father_name", ""), request.form.get("dob", ""),
                   request.form.get("gender", ""), request.form.get("class_applying", ""),
                   request.form.get("prev_school", ""), request.form.get("phone", ""),
                   request.form.get("address", ""), app_id, photo_name, datetime.now().isoformat()))
        d.commit()
        send_email(s, f"New admission {app_id}: {name}",
                   f"Application ID: {app_id}\nStudent: {name}\nFather: {request.form.get('father_name')}\n"
                   f"Class: {request.form.get('class_applying')}\nPhone: {request.form.get('phone')}")
        return render_template("apply.html", school=s, done=True, app_id=app_id)
    return render_template("apply.html", school=s)

# ---------- Students ----------
@app.route("/dashboard/students")
@login_required
@require_role("owner", "teacher")
def students():
    s = current_school(); d = db()
    f = request.args.get("class", "")
    q = "SELECT * FROM students WHERE school_id=? AND status='active'"
    args = [s["id"]]
    if f:
        q += " AND class=?"; args.append(f)
    studs = d.execute(q + " ORDER BY class, name", args).fetchall()
    host = request.host_url.rstrip("/")
    out = []
    for st in studs:
        tok = parent_token_for(st["id"])
        out.append((st, f"{host}/p/{tok}", tok))
    return render_template("students.html", school=s, students=out,
                           classes=student_classes(s["id"]), f=f)

@app.route("/dashboard/students/admit/<int:aid>", methods=["POST"])
@login_required
@require_role("owner")
def admit_student(aid):
    s = current_school(); d = db()
    a = d.execute("SELECT * FROM applications WHERE id=? AND school_id=?",
                  (aid, s["id"])).fetchone()
    if not a or a["status"] != "approved":
        flash("Sirf approved application admit ho sakti hai.")
        return redirect(url_for("applications"))
    if a["app_id"] and d.execute("SELECT 1 FROM students WHERE school_id=? AND app_id=?",
                                 (s["id"], a["app_id"])).fetchone():
        flash("Ye student pehle se admitted hai.")
        return redirect(url_for("students"))
    d.execute("""INSERT INTO students(school_id,name,father_name,gender,dob,class,phone,address,
                 photo,app_id,admission_date,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
              (s["id"], a["student_name"], a["father_name"], a["gender"], a["dob"],
               a["class_applying"], a["phone"], a["address"], a["photo"], a["app_id"],
               datetime.now().date().isoformat(), datetime.now().isoformat()))
    d.commit()
    flash(f"🎉 {a['student_name']} admitted!")
    return redirect(url_for("students"))

# ---------- Fees ----------
@app.route("/dashboard/fees", methods=["GET", "POST"])
@login_required
@require_role("owner", "accountant")
def fees():
    s = current_school(); d = db()
    if request.method == "POST":
        if current_role() != "owner":
            flash("⛔ Fee heads sirf owner change kar sakta hai.")
            return redirect(url_for("fees"))
        if request.form.get("del_head"):
            d.execute("DELETE FROM fee_heads WHERE id=? AND school_id=?",
                      (request.form["del_head"], s["id"]))
        else:
            name = request.form.get("name", "").strip()
            try:
                amount = float(request.form.get("amount", "0") or 0)
            except ValueError:
                amount = 0
            if name:
                d.execute("""INSERT INTO fee_heads(school_id,name,amount,classes,freq,created_at)
                             VALUES(?,?,?,?,?,?)""",
                          (s["id"], name, amount, request.form.get("classes", "all").strip() or "all",
                           request.form.get("freq", "monthly"), datetime.now().isoformat()))
        d.commit()
        return redirect(url_for("fees"))
    heads = d.execute("SELECT * FROM fee_heads WHERE school_id=? ORDER BY id", (s["id"],)).fetchall()
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    inv = d.execute("""SELECT invoices.*, students.name sname, students.class sclass
                       FROM invoices JOIN students ON students.id=invoices.student_id
                       WHERE invoices.school_id=? AND invoices.month=?
                       ORDER BY students.class, students.name""",
                    (s["id"], month)).fetchall()
    tot = sum(r["total"] or 0 for r in inv)
    paid = sum(r["paid"] or 0 for r in inv)
    disc = sum(r["discount"] or 0 for r in inv)
    pending_proofs = d.execute("""SELECT payments.*, students.name sname, invoices.month
                                  FROM payments
                                  JOIN invoices ON invoices.id=payments.invoice_id
                                  JOIN students ON students.id=invoices.student_id
                                  WHERE invoices.school_id=? AND payments.verified=0
                                  ORDER BY payments.id DESC""", (s["id"],)).fetchall()
    return render_template("fees.html", school=s, heads=heads, invoices=inv, month=month,
                           tot=tot, paid=paid, disc=disc, due=tot - disc - paid,
                           pending_proofs=pending_proofs, fmt=fmt)

@app.route("/dashboard/fees/generate", methods=["POST"])
@login_required
@require_role("owner", "accountant")
def gen_invoices():
    s = current_school(); d = db()
    month = request.form.get("month", "").strip() or datetime.now().strftime("%Y-%m")
    heads = d.execute("SELECT * FROM fee_heads WHERE school_id=? AND freq='monthly'",
                      (s["id"],)).fetchall()
    studs = d.execute("SELECT * FROM students WHERE school_id=? AND status='active'",
                      (s["id"],)).fetchall()
    made = 0
    for st in studs:
        if d.execute("SELECT 1 FROM invoices WHERE school_id=? AND student_id=? AND month=?",
                     (s["id"], st["id"], month)).fetchone():
            continue
        use = [h for h in heads if h["classes"] == "all"
               or st["class"] in [c.strip() for c in (h["classes"] or "").split(",")]]
        if not use:
            continue
        arrears = d.execute("""SELECT COALESCE(SUM(total - COALESCE(discount,0) - COALESCE(paid,0)),0) t
                               FROM invoices
                               WHERE school_id=? AND student_id=? AND status!='paid' AND month<?""",
                            (s["id"], st["id"], month)).fetchone()["t"] or 0
        total = arrears + sum(h["amount"] or 0 for h in use)
        items = ("Arrears " + fmt(arrears) + ", " if arrears > 0 else "") + \
                ", ".join(f"{h['name']} {fmt(h['amount'] or 0)}" for h in use)
        d.execute("""INSERT INTO invoices(school_id,student_id,month,items,total,created_at)
                     VALUES(?,?,?,?,?,?)""",
                  (s["id"], st["id"], month, items, total, datetime.now().isoformat()))
        made += 1
    d.commit()
    flash(f"✅ {made} invoices ban gayin ({month}).")
    return redirect(url_for("fees", month=month))

@app.route("/dashboard/fees/collect/<int:inv>", methods=["GET", "POST"])
@login_required
@require_role("owner", "accountant")
def collect_fee(inv):
    s = current_school(); d = db()
    r = d.execute("""SELECT invoices.*, students.name sname, students.class sclass, students.father_name
                     FROM invoices JOIN students ON students.id=invoices.student_id
                     WHERE invoices.id=? AND invoices.school_id=?""", (inv, s["id"])).fetchone()
    if not r:
        return "Invoice nahi mili.", 404
    if request.method == "POST":
        # discount / concession (owner only)
        if request.form.get("set_discount") is not None:
            if current_role() != "owner":
                flash("⛔ Discount sirf owner de sakta hai.")
                return redirect(url_for("collect_fee", inv=inv))
            try:
                disc = float(request.form.get("discount", "0") or 0)
            except ValueError:
                disc = 0
            payable = (r["total"] or 0) - disc
            paid = r["paid"] or 0
            status = "paid" if payable > 0 and paid >= payable else ("partial" if paid > 0 else "unpaid")
            d.execute("UPDATE invoices SET discount=?, status=? WHERE id=?", (disc, status, inv))
            d.commit()
            flash(f"✅ Discount Rs {fmt(disc)} lag gaya.")
            return redirect(url_for("collect_fee", inv=inv))
        try:
            amt = float(request.form.get("amount", "0") or 0)
        except ValueError:
            amt = 0
        if amt > 0:
            pf = request.files.get("proof")
            pname = ""
            if pf and pf.filename:
                ext = pf.filename.rsplit(".", 1)[-1].lower() if "." in pf.filename else ""
                if ext in ALLOWED_EXT | {"pdf"}:
                    pname = secure_filename(f"proof_{inv}_{int(datetime.now().timestamp())}.{ext}")
                    pf.save(os.path.join(PROOF_DIR, pname))
            d.execute("""INSERT INTO payments(invoice_id,amount,pay_date,method,note,proof,verified,created_at)
                         VALUES(?,?,?,?,?,?,1,?)""",
                      (inv, amt, request.form.get("pay_date") or datetime.now().date().isoformat(),
                       request.form.get("method", "cash"), request.form.get("note", ""),
                       pname, datetime.now().isoformat()))
            new_paid = (r["paid"] or 0) + amt
            payable = (r["total"] or 0) - (r["discount"] or 0)
            status = "paid" if new_paid >= payable else "partial"
            rcpt = r["receipt_no"]
            if not rcpt:
                px = school_prefix(s["name"])
                n = d.execute("SELECT COUNT(*) c FROM invoices WHERE school_id=? AND receipt_no!=''",
                              (s["id"],)).fetchone()["c"] + 1
                rcpt = f"RCP-{px}-{n:04d}"
            d.execute("UPDATE invoices SET paid=?, status=?, receipt_no=? WHERE id=?",
                      (new_paid, status, rcpt, inv))
            d.commit()
            return redirect(url_for("fee_receipt", inv=inv))
        flash("Amount 0 se zyada likhein.")
    pays = d.execute("SELECT * FROM payments WHERE invoice_id=? ORDER BY id", (inv,)).fetchall()
    return render_template("collect.html", school=s, inv=r, pays=pays, fmt=fmt)

@app.route("/dashboard/fees/receipt/<int:inv>")
@login_required
@require_role("owner", "accountant")
def fee_receipt(inv):
    s = current_school(); d = db()
    r = d.execute("""SELECT invoices.*, students.name sname, students.class sclass, students.father_name
                     FROM invoices JOIN students ON students.id=invoices.student_id
                     WHERE invoices.id=? AND invoices.school_id=?""", (inv, s["id"])).fetchone()
    if not r:
        return "Invoice nahi mili.", 404
    pays = d.execute("SELECT * FROM payments WHERE invoice_id=? ORDER BY id", (inv,)).fetchall()
    return render_template("receipt.html", school=s, inv=r, pays=pays, fmt=fmt)

@app.route("/dashboard/fees/defaulters")
@login_required
@require_role("owner", "accountant")
def defaulters():
    s = current_school(); d = db()
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    rows = d.execute("""SELECT invoices.*, students.name sname, students.class sclass, students.phone
                        FROM invoices JOIN students ON students.id=invoices.student_id
                        WHERE invoices.school_id=? AND invoices.month=? AND invoices.status!='paid'
                        ORDER BY students.class, students.name""", (s["id"], month)).fetchall()
    out = []
    for r in rows:
        due = (r["total"] or 0) - (r["discount"] or 0) - (r["paid"] or 0)
        msg = (f"Assalam-o-Alaikum! {s['name']} — {r['sname']} (Class {r['sclass']}) "
               f"ki {month} ki fee me se Rs {fmt(due)} baqi hai. "
               f"Meherbani kar ke jald jama karwayein.")
        out.append((r, wa_link(r["phone"], msg)))
    return render_template("defaulters.html", school=s, rows=out, month=month, fmt=fmt)

# ---------- Attendance ----------
@app.route("/dashboard/attendance", methods=["GET", "POST"])
@login_required
@require_role("owner", "teacher")
def attendance():
    s = current_school(); d = db()
    classes = student_classes(s["id"])
    cls = request.values.get("class", classes[0] if classes else "")
    day = request.values.get("date", datetime.now().date().isoformat())
    studs = d.execute("SELECT * FROM students WHERE school_id=? AND class=? AND status='active' ORDER BY name",
                      (s["id"], cls)).fetchall() if cls else []
    marked = {r["student_id"]: r["status"] for r in d.execute(
        "SELECT student_id, status FROM attendance WHERE school_id=? AND date=?", (s["id"], day))}
    absent = []
    if request.method == "POST" and studs:
        for st in studs:
            stt = request.form.get(f"st_{st['id']}", "present")
            if stt not in ("present", "absent", "late", "leave"):
                stt = "present"
            d.execute("""INSERT INTO attendance(school_id,student_id,date,status) VALUES(?,?,?,?)
                         ON CONFLICT(school_id,student_id,date)
                         DO UPDATE SET status=excluded.status""",
                      (s["id"], st["id"], day, stt))
        d.commit()
        marked = {r["student_id"]: r["status"] for r in d.execute(
            "SELECT student_id, status FROM attendance WHERE school_id=? AND date=?", (s["id"], day))}
        for st in studs:
            if marked.get(st["id"]) == "absent":
                msg = (f"Assalam-o-Alaikum! {s['name']} — aapke bache {st['name']} "
                       f"(Class {st['class']}) aaj {day} ko school hazir nahi huay.")
                absent.append((st, wa_link(st["phone"], msg)))
        flash(f"✅ Attendance save ({day}, {cls}).")
    counts = {"present": 0, "absent": 0, "late": 0, "leave": 0}
    for v in marked.values():
        if v in counts:
            counts[v] += 1
    return render_template("attendance.html", school=s, classes=classes, cls=cls, day=day,
                           students=studs, marked=marked, absent=absent, counts=counts)

# ---------- Exams & Results ----------
@app.route("/dashboard/exams", methods=["GET", "POST"])
@login_required
@require_role("owner", "teacher")
def exams():
    s = current_school(); d = db()
    if request.method == "POST":
        if current_role() != "owner":
            flash("⛔ Exam sirf owner bana/delete kar sakta hai.")
            return redirect(url_for("exams"))
        if request.form.get("del"):
            eid = request.form["del"]
            d.execute("DELETE FROM marks WHERE exam_id=?", (eid,))
            d.execute("DELETE FROM exams WHERE id=? AND school_id=?", (eid, s["id"]))
        else:
            name = request.form.get("name", "").strip()
            subs = ",".join(x.strip() for x in request.form.get("subjects", "").split(",") if x.strip())
            if name and subs:
                d.execute("INSERT INTO exams(school_id,name,year,subjects,created_at) VALUES(?,?,?,?,?)",
                          (s["id"], name, int(request.form.get("year") or datetime.now().year),
                           subs, datetime.now().isoformat()))
        d.commit()
        return redirect(url_for("exams"))
    exs = d.execute("SELECT * FROM exams WHERE school_id=? ORDER BY id DESC", (s["id"],)).fetchall()
    return render_template("exams.html", school=s, exams=exs,
                           year=datetime.now().year, classes=student_classes(s["id"]))

@app.route("/dashboard/exams/<int:eid>/marks", methods=["GET", "POST"])
@login_required
@require_role("owner", "teacher")
def enter_marks(eid):
    s = current_school(); d = db()
    ex = d.execute("SELECT * FROM exams WHERE id=? AND school_id=?", (eid, s["id"])).fetchone()
    if not ex:
        return "Exam nahi mila.", 404
    subjects = [x.strip() for x in (ex["subjects"] or "").split(",") if x.strip()]
    classes = student_classes(s["id"])
    cls = request.values.get("class", classes[0] if classes else "")
    studs = d.execute("SELECT * FROM students WHERE school_id=? AND class=? AND status='active' ORDER BY name",
                      (s["id"], cls)).fetchall() if cls else []
    if request.method == "POST" and studs:
        for st in studs:
            for i, sub in enumerate(subjects):
                try:
                    ob = float(request.form.get(f"m_{st['id']}_{i}", "") or 0)
                except ValueError:
                    ob = 0
                d.execute("""INSERT INTO marks(exam_id,student_id,subject,obtained,total)
                             VALUES(?,?,?,?,100)
                             ON CONFLICT(exam_id,student_id,subject)
                             DO UPDATE SET obtained=excluded.obtained""",
                          (eid, st["id"], sub, ob))
        d.commit()
        flash(f"✅ Marks save ({ex['name']}, {cls}).")
        return redirect(url_for("exam_merit", eid=eid, cls=cls))
    old = {}
    for r in d.execute("SELECT student_id, subject, obtained FROM marks WHERE exam_id=?", (eid,)):
        old[(r["student_id"], r["subject"])] = r["obtained"]
    return render_template("marks.html", school=s, exam=ex, subjects=subjects,
                           classes=classes, cls=cls, students=studs, old=old, fmt=fmt)

@app.route("/dashboard/exams/<int:eid>/merit")
@login_required
@require_role("owner", "teacher")
def exam_merit(eid):
    s = current_school(); d = db()
    ex = d.execute("SELECT * FROM exams WHERE id=? AND school_id=?", (eid, s["id"])).fetchone()
    if not ex:
        return "Exam nahi mila.", 404
    classes = student_classes(s["id"])
    cls = request.args.get("class", classes[0] if classes else "")
    studs = d.execute("SELECT * FROM students WHERE school_id=? AND class=? AND status='active' ORDER BY name",
                      (s["id"], cls)).fetchall() if cls else []
    totals = []
    for st in studs:
        rows = d.execute("SELECT obtained, total FROM marks WHERE exam_id=? AND student_id=?",
                         (eid, st["id"])).fetchall()
        ob = sum(r["obtained"] or 0 for r in rows)
        mx = sum(r["total"] or 0 for r in rows)
        pct = (ob / mx * 100) if mx else 0
        totals.append({"st": st, "ob": ob, "mx": mx, "pct": pct, "grade": grade_of(pct)})
    totals.sort(key=lambda x: x["ob"], reverse=True)
    return render_template("merit.html", school=s, exam=ex, classes=classes, cls=cls,
                           totals=totals, fmt=fmt)

@app.route("/dashboard/exams/<int:eid>/report/<int:sid>")
@login_required
@require_role("owner", "teacher")
def report_card(eid, sid):
    s = current_school(); d = db()
    ex = d.execute("SELECT * FROM exams WHERE id=? AND school_id=?", (eid, s["id"])).fetchone()
    st = d.execute("SELECT * FROM students WHERE id=? AND school_id=?", (sid, s["id"])).fetchone()
    if not ex or not st:
        return "Nahi mila.", 404
    subjects = [x.strip() for x in (ex["subjects"] or "").split(",") if x.strip()]
    rows = []
    for sub in subjects:
        r = d.execute("SELECT obtained, total FROM marks WHERE exam_id=? AND student_id=? AND subject=?",
                      (eid, sid, sub)).fetchone()
        rows.append({"sub": sub, "ob": r["obtained"] if r else 0, "mx": r["total"] if r else 100})
    ob = sum(r["ob"] for r in rows)
    mx = sum(r["mx"] for r in rows)
    pct = (ob / mx * 100) if mx else 0
    mates = d.execute("SELECT id FROM students WHERE school_id=? AND class=? AND status='active'",
                      (s["id"], st["class"])).fetchall()
    scores = []
    for m in mates:
        rr = d.execute("SELECT SUM(obtained) t FROM marks WHERE exam_id=? AND student_id=?",
                       (eid, m["id"])).fetchone()
        scores.append(rr["t"] or 0)
    scores.sort(reverse=True)
    pos = scores.index(ob) + 1 if ob in scores else "-"
    return render_template("report.html", school=s, exam=ex, st=st, rows=rows,
                           ob=ob, mx=mx, pct=pct, grade=grade_of(pct), pos=pos,
                           total_students=len(mates), fmt=fmt)

# ---------- Team (role-based logins) ----------
@app.route("/dashboard/team", methods=["GET", "POST"])
@login_required
@require_role("owner")
def team():
    s = current_school(); d = db()
    if request.method == "POST":
        if request.form.get("del"):
            d.execute("DELETE FROM users WHERE id=? AND school_id=?", (request.form["del"], s["id"]))
            flash("Login delete ho gaya.")
        else:
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            pw = request.form.get("password", "")
            role = request.form.get("role", "teacher")
            if role not in ("teacher", "accountant"):
                role = "teacher"
            if name and email and len(pw) >= 4:
                exists = d.execute("SELECT 1 FROM users WHERE school_id=? AND email=?",
                                   (s["id"], email)).fetchone() or \
                         d.execute("SELECT 1 FROM schools WHERE id=? AND email=?",
                                   (s["id"], email)).fetchone()
                if exists:
                    flash("Ye email pehle se use me hai.")
                else:
                    d.execute("""INSERT INTO users(school_id,name,email,pw_hash,role,created_at)
                                 VALUES(?,?,?,?,?,?)""",
                              (s["id"], name, email, generate_password_hash(pw), role,
                               datetime.now().isoformat()))
                    flash(f"✅ {name} ({role}) ka login ban gaya.")
            else:
                flash("Naam, email aur kam-az-kam 4 harf ka password zaroori hai.")
        d.commit()
        return redirect(url_for("team"))
    members = d.execute("SELECT * FROM users WHERE school_id=? ORDER BY role, name",
                        (s["id"],)).fetchall()
    return render_template("team.html", school=s, members=members)

# ---------- Staff & payroll ----------
@app.route("/dashboard/staff", methods=["GET", "POST"])
@login_required
@require_role("owner")
def staff():
    s = current_school(); d = db()
    if request.method == "POST":
        if request.form.get("del"):
            d.execute("DELETE FROM staff WHERE id=? AND school_id=?", (request.form["del"], s["id"]))
        else:
            name = request.form.get("name", "").strip()
            if name:
                try:
                    sal = float(request.form.get("salary", "0") or 0)
                except ValueError:
                    sal = 0
                d.execute("""INSERT INTO staff(school_id,name,father_name,phone,address,designation,
                             salary_monthly,join_date,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                          (s["id"], name, request.form.get("father_name", ""),
                           request.form.get("phone", ""), request.form.get("address", ""),
                           request.form.get("designation", "Teacher") or "Teacher",
                           sal, request.form.get("join_date", ""), datetime.now().isoformat()))
                flash(f"✅ {name} add ho gaye.")
        d.commit()
        return redirect(url_for("staff"))
    rows = d.execute("SELECT * FROM staff WHERE school_id=? AND status='active' ORDER BY name",
                     (s["id"],)).fetchall()
    return render_template("staff.html", school=s, staff=rows, fmt=fmt)

@app.route("/dashboard/staff/attendance", methods=["GET", "POST"])
@login_required
@require_role("owner")
def staff_attendance():
    s = current_school(); d = db()
    day = request.values.get("date", datetime.now().date().isoformat())
    rows = d.execute("SELECT * FROM staff WHERE school_id=? AND status='active' ORDER BY name",
                     (s["id"],)).fetchall()
    if request.method == "POST":
        for st in rows:
            v = request.form.get(f"s_{st['id']}", "present")
            if v not in ("present", "absent", "leave"):
                v = "present"
            d.execute("""INSERT INTO staff_attendance(school_id,staff_id,date,status)
                         VALUES(?,?,?,?)
                         ON CONFLICT(school_id,staff_id,date)
                         DO UPDATE SET status=excluded.status""",
                      (s["id"], st["id"], day, v))
        d.commit()
        flash(f"✅ Staff attendance save ({day}).")
        return redirect(url_for("staff_attendance", date=day))
    marked = {r["staff_id"]: r["status"] for r in d.execute(
        "SELECT staff_id, status FROM staff_attendance WHERE school_id=? AND date=?", (s["id"], day))}
    return render_template("staff_att.html", school=s, staff=rows, marked=marked, day=day)

@app.route("/dashboard/payroll", methods=["GET", "POST"])
@login_required
@require_role("owner", "accountant")
def payroll():
    s = current_school(); d = db()
    month = request.values.get("month", datetime.now().strftime("%Y-%m"))
    if request.method == "POST":
        if current_role() != "owner":
            flash("⛔ Salary slip sirf owner bana sakta hai.")
            return redirect(url_for("payroll", month=month))
        if request.form.get("mark_paid"):
            d.execute("UPDATE salary_slips SET paid=1, pay_date=? WHERE id=? AND school_id=?",
                      (datetime.now().date().isoformat(), request.form["mark_paid"], s["id"]))
            flash("✅ Salary paid mark ho gayi.")
        elif request.form.get("del"):
            d.execute("DELETE FROM salary_slips WHERE id=? AND school_id=?",
                      (request.form["del"], s["id"]))
        else:
            st = d.execute("SELECT * FROM staff WHERE id=? AND school_id=?",
                           (request.form.get("staff_id"), s["id"])).fetchone()
            if st:
                def num(k):
                    try:
                        return float(request.form.get(k, "0") or 0)
                    except ValueError:
                        return 0
                basic, allow, deduct, adv = num("basic"), num("allowances"), num("deductions"), num("advance")
                net = basic + allow - deduct - adv
                d.execute("""INSERT INTO salary_slips(school_id,staff_id,month,basic,allowances,
                             deductions,advance,net,created_at) VALUES(?,?,?,?,?,?,?,?,?)
                             ON CONFLICT(school_id,staff_id,month)
                             DO UPDATE SET basic=excluded.basic, allowances=excluded.allowances,
                               deductions=excluded.deductions, advance=excluded.advance,
                               net=excluded.net""",
                          (s["id"], st["id"], month, basic, allow, deduct, adv, net,
                           datetime.now().isoformat()))
                flash(f"✅ {st['name']} ki salary slip ban gayi (Net Rs {fmt(net)}).")
        d.commit()
        return redirect(url_for("payroll", month=month))
    staff = d.execute("SELECT * FROM staff WHERE school_id=? AND status='active' ORDER BY name",
                      (s["id"],)).fetchall()
    slips = d.execute("""SELECT salary_slips.*, staff.name sname, staff.designation
                         FROM salary_slips JOIN staff ON staff.id=salary_slips.staff_id
                         WHERE salary_slips.school_id=? AND salary_slips.month=?
                         ORDER BY staff.name""", (s["id"], month)).fetchall()
    tot = sum(r["net"] or 0 for r in slips)
    return render_template("payroll.html", school=s, staff=staff, slips=slips,
                           month=month, tot=tot, fmt=fmt)

@app.route("/dashboard/payroll/slip/<int:pid>")
@login_required
@require_role("owner", "accountant")
def payslip(pid):
    s = current_school(); d = db()
    r = d.execute("""SELECT salary_slips.*, staff.name sname, staff.designation, staff.phone
                     FROM salary_slips JOIN staff ON staff.id=salary_slips.staff_id
                     WHERE salary_slips.id=? AND salary_slips.school_id=?""",
                  (pid, s["id"])).fetchone()
    if not r:
        return "Slip nahi mili.", 404
    return render_template("payslip.html", school=s, r=r, fmt=fmt)

# ---------- Digital diary / homework ----------
@app.route("/dashboard/diary", methods=["GET", "POST"])
@login_required
@require_role("owner", "teacher")
def diary():
    s = current_school(); d = db()
    if request.method == "POST":
        cls = request.form.get("class", "").strip()
        text = request.form.get("text", "").strip()
        if cls and text:
            d.execute("""INSERT INTO diary(school_id,class,date,subject,text,teacher,created_at)
                         VALUES(?,?,?,?,?,?,?)""",
                      (s["id"], cls, request.form.get("date") or datetime.now().date().isoformat(),
                       request.form.get("subject", ""), text,
                       current_user_name() or current_role(), datetime.now().isoformat()))
            d.commit()
            flash("✅ Diary post ho gayi — parents portal pe dekh sakte hain.")
        else:
            flash("Class aur diary text zaroori hai.")
        return redirect(url_for("diary"))
    f = request.args.get("class", "")
    q = "SELECT * FROM diary WHERE school_id=?"
    args = [s["id"]]
    if f:
        q += " AND class=?"; args.append(f)
    rows = d.execute(q + " ORDER BY date DESC, id DESC LIMIT 60", args).fetchall()
    return render_template("diary.html", school=s, rows=rows, classes=student_classes(s["id"]),
                           f=f, day=datetime.now().date().isoformat())

# ---------- Parent portal (QR token, no login) ----------
def parent_token_for(student_id):
    import secrets as _secrets
    d = db()
    r = d.execute("SELECT token FROM parent_tokens WHERE student_id=?", (student_id,)).fetchone()
    if r:
        return r["token"]
    tok = _secrets.token_urlsafe(12)
    d.execute("INSERT INTO parent_tokens(student_id,token,created_at) VALUES(?,?,?)",
              (student_id, tok, datetime.now().isoformat()))
    d.commit()
    return tok

@app.route("/p/<token>", methods=["GET", "POST"])
def parent_portal(token):
    d = db()
    t = d.execute("SELECT * FROM parent_tokens WHERE token=?", (token,)).fetchone()
    if not t:
        return "Ghalat ya purana link hai.", 404
    st = d.execute("SELECT * FROM students WHERE id=?", (t["student_id"],)).fetchone()
    if not st:
        return "Student nahi mila.", 404
    s = d.execute("SELECT * FROM schools WHERE id=?", (st["school_id"],)).fetchone()
    if request.method == "POST":
        inv = d.execute("SELECT * FROM invoices WHERE id=? AND student_id=?",
                        (request.form.get("invoice_id"), st["id"])).fetchone()
        try:
            amt = float(request.form.get("amount", "0") or 0)
        except ValueError:
            amt = 0
        pf = request.files.get("proof")
        pname = ""
        if pf and pf.filename:
            ext = pf.filename.rsplit(".", 1)[-1].lower() if "." in pf.filename else ""
            if ext in ALLOWED_EXT | {"pdf"}:
                pname = secure_filename(
                    f"proof_{inv['id'] if inv else 0}_{int(datetime.now().timestamp())}.{ext}")
                pf.save(os.path.join(PROOF_DIR, pname))
        if inv and amt > 0:
            d.execute("""INSERT INTO payments(invoice_id,amount,pay_date,method,note,proof,verified,created_at)
                         VALUES(?,?,?,?,?,?,0,?)""",
                      (inv["id"], amt, datetime.now().date().isoformat(),
                       request.form.get("method", "easypaisa"), request.form.get("note", ""),
                       pname, datetime.now().isoformat()))
            d.commit()
            flash("✅ Payment proof bhej diya — school verify kar ke receipt dega.")
        else:
            flash("Amount aur invoice theek likhein.")
        return redirect(url_for("parent_portal", token=token))
    att = d.execute("""SELECT status, COUNT(*) c FROM attendance WHERE student_id=?
                       AND date >= date('now','-30 days') GROUP BY status""", (st["id"],)).fetchall()
    invs = d.execute("SELECT * FROM invoices WHERE student_id=? ORDER BY month DESC", (st["id"],)).fetchall()
    pays = d.execute("""SELECT payments.* FROM payments
                        JOIN invoices ON invoices.id=payments.invoice_id
                        WHERE invoices.student_id=? ORDER BY payments.id DESC LIMIT 20""",
                     (st["id"],)).fetchall()
    diary_rows = d.execute("""SELECT * FROM diary WHERE school_id=? AND class=?
                              ORDER BY date DESC, id DESC LIMIT 10""",
                           (s["id"], st["class"])).fetchall()
    results = []
    for ex in d.execute("SELECT * FROM exams WHERE school_id=? ORDER BY id DESC", (s["id"],)):
        rr = d.execute("SELECT obtained, total FROM marks WHERE exam_id=? AND student_id=?",
                       (ex["id"], st["id"])).fetchall()
        if rr:
            ob = sum(x["obtained"] or 0 for x in rr); mx = sum(x["total"] or 0 for x in rr)
            pct = (ob / mx * 100) if mx else 0
            results.append({"ex": ex, "ob": ob, "mx": mx, "pct": pct, "grade": grade_of(pct)})
    due = sum((i["total"] or 0) - (i["discount"] or 0) - (i["paid"] or 0)
              for i in invs if i["status"] != "paid")
    return render_template("portal.html", school=s, st=st, att=att, invs=invs, pays=pays,
                           diary_rows=diary_rows, results=results, due=due, fmt=fmt)

# ---------- Fee challan + discount + proof verify ----------
@app.route("/dashboard/fees/challan/<int:inv>")
@login_required
@require_role("owner", "accountant")
def fee_challan(inv):
    s = current_school(); d = db()
    r = d.execute("""SELECT invoices.*, students.name sname, students.class sclass,
                     students.father_name, students.app_id
                     FROM invoices JOIN students ON students.id=invoices.student_id
                     WHERE invoices.id=? AND invoices.school_id=?""", (inv, s["id"])).fetchone()
    if not r:
        return "Invoice nahi mili.", 404
    return render_template("challan.html", school=s, inv=r, fmt=fmt,
                           due=(r["total"] or 0) - (r["discount"] or 0) - (r["paid"] or 0))

@app.route("/dashboard/fees/verify/<int:pid>", methods=["POST"])
@login_required
@require_role("owner", "accountant")
def verify_payment(pid):
    s = current_school(); d = db()
    p = d.execute("""SELECT payments.*, invoices.school_id, invoices.id AS inv_id
                     FROM payments JOIN invoices ON invoices.id=payments.invoice_id
                     WHERE payments.id=?""", (pid,)).fetchone()
    if not p or p["school_id"] != s["id"]:
        return "Nahi mila.", 404
    if request.form.get("action") == "verify":
        inv = d.execute("SELECT * FROM invoices WHERE id=?", (p["inv_id"],)).fetchone()
        new_paid = (inv["paid"] or 0) + (p["amount"] or 0)
        payable = (inv["total"] or 0) - (inv["discount"] or 0)
        status = "paid" if new_paid >= payable else "partial"
        rcpt = inv["receipt_no"]
        if not rcpt:
            px = school_prefix(s["name"])
            n = d.execute("SELECT COUNT(*) c FROM invoices WHERE school_id=? AND receipt_no!=''",
                          (s["id"],)).fetchone()["c"] + 1
            rcpt = f"RCP-{px}-{n:04d}"
        d.execute("UPDATE payments SET verified=1 WHERE id=?", (pid,))
        d.execute("UPDATE invoices SET paid=?, status=?, receipt_no=? WHERE id=?",
                  (new_paid, status, rcpt, inv["id"]))
        flash("✅ Payment verify — receipt ban gayi.")
    else:
        d.execute("DELETE FROM payments WHERE id=?", (pid,))
        flash("Proof reject kar diya.")
    d.commit()
    return redirect(url_for("fees", month=request.form.get("month", "")))

if __name__ == "__main__":
    init_db()
    print("SchoolWeb running: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)

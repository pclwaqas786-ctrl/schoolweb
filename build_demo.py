"""SchoolWeb live demo builder — real Flask templates ko static HTML me render karta hai.
Usage: venv/bin/python build_demo.py   ->  /tmp/schoolweb_demo/ me demo site
"""
import os, sys, sqlite3, shutil, re
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)

TMPDB = "/tmp/demo_schoolweb.db"
TMPUP = "/tmp/demo_uploads"
OUT = "/tmp/schoolweb_demo"
LIVE = "https://pclwaqas786-ctrl.github.io/schoolweb"

for p in (TMPDB,):
    if os.path.exists(p): os.remove(p)
shutil.rmtree(TMPUP, ignore_errors=True); os.makedirs(TMPUP)
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)

import app as A
A.DB = TMPDB
A.UPLOAD_DIR = TMPUP
A.init_db()

from werkzeug.security import generate_password_hash
from PIL import Image, ImageDraw, ImageFont

# ---------- avatars ----------
COLORS = [(23,162,184),(255,107,94),(142,91,214),(47,191,113),(255,193,7),(0,57,79)]
names = ["Ahmed Raza","Fatima Khan","Bilal Ahmed","Ayesha Malik","Usman Tariq","Zainab Ali"]
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
except Exception:
    FONT = ImageFont.load_default()
for i, nm in enumerate(names):
    im = Image.new("RGB", (200, 240), COLORS[i % len(COLORS)])
    d = ImageDraw.Draw(im)
    ch = nm[0]
    bb = d.textbbox((0, 0), ch, font=FONT)
    d.text(((200-(bb[2]-bb[0]))/2, (240-(bb[3]-bb[1]))/2 - 10), ch, fill="white", font=FONT)
    im.save(os.path.join(TMPUP, f"av{i}.png"))

d = sqlite3.connect(TMPDB); d.row_factory = sqlite3.Row
now = datetime.now().isoformat(); today = datetime.now().date().isoformat()

d.execute("""INSERT INTO schools(name,slug,email,pw_hash,phone,address,intro,principal_msg,created_at)
             VALUES(?,?,?,?,?,?,?,?,?)""",
          ("Demo Public School", "demo-school", "demo@demo.com",
           generate_password_hash("demo123"), "0300-1234567",
           "Gulshan-e-Iqbal, Karachi",
           "Demo Public School me khush amdeed! Yahan taleem ke sath tarbiyat par bhi tawajjo di jati hai.",
           "Pyare waldein! Hamara maqsad har bache ko behtareen taleem dena hai. — Principal",
           now))
sid = 1
d.execute("INSERT INTO notices(school_id,title,body,created_at) VALUES(?,?,?,?)",
          (sid, "📢 Admissions Open 2026-27", "Naye session ke dakhle jari hain. Online form bharein!", now))
d.execute("INSERT INTO notices(school_id,title,body,created_at) VALUES(?,?,?,?)",
          (sid, "📝 First Term Exams", "First Term exams 15 October se shuru honge. Date sheet jald.", now))

# applications
apps = [("New Apply One", "Father One", "Class 2", "pending"),
        ("New Apply Two", "Father Two", "Class 3", "pending"),
        ("Old Student", "Father Three", "Class 4", "approved")]
for i, (nm, fn, cl, stt) in enumerate(apps):
    d.execute("""INSERT INTO applications(school_id,student_name,father_name,class_applying,phone,
                 app_id,status,created_at) VALUES(?,?,?,?,?,?,?,?)""",
              (sid, nm, fn, cl, "0300123456%d" % i, f"DPS-2026-000{i+1}", stt, now))

# students
students = [("Ahmed Raza","Rashid Raza","Class 4","av0.png","03001111111","DPS-2026-0101"),
            ("Fatima Khan","Imran Khan","Class 4","av1.png","03002222222","DPS-2026-0102"),
            ("Bilal Ahmed","Naseer Ahmed","Class 4","av2.png","03003333333","DPS-2026-0103"),
            ("Ayesha Malik","Tariq Malik","Class 5","av3.png","03004444444","DPS-2026-0104"),
            ("Usman Tariq","Khalid Tariq","Class 5","av4.png","03005555555","DPS-2026-0105"),
            ("Zainab Ali","Aslam Ali","Class 3","av5.png","03006666666","DPS-2026-0106")]
sids = []
for nm, fn, cl, ph, phone, aid in students:
    d.execute("""INSERT INTO students(school_id,name,father_name,class,phone,photo,app_id,
                 admission_date,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
              (sid, nm, fn, cl, phone, ph, aid, "2026-04-01", now))
    sids.append(d.execute("SELECT last_insert_rowid()").fetchone()[0])

# fee heads + invoices
d.execute("INSERT INTO fee_heads(school_id,name,amount,classes,freq,created_at) VALUES(?,?,?,?,?,?)",
          (sid, "Tuition Fee", 1500, "all", "monthly", now))
d.execute("INSERT INTO fee_heads(school_id,name,amount,classes,freq,created_at) VALUES(?,?,?,?,?,?)",
          (sid, "Exam Fee", 300, "all", "monthly", now))
inv_ids = {}
for m in ("2026-09", "2026-10"):
    for i, stid in enumerate(sids):
        items = "Tuition Fee 1500, Exam Fee 300"; total = 1800.0
        paid, status, rcpt, disc = 0.0, "unpaid", "", 0.0
        if m == "2026-09":
            if i < 3: paid, status, rcpt = 1800.0, "paid", f"RCP-DPS-000{i+1}"
            elif i == 3: paid, status, rcpt = 1000.0, "partial", "RCP-DPS-0004"
            if i == 4: disc, status = 300.0, "unpaid"
        d.execute("""INSERT INTO invoices(school_id,student_id,month,items,total,paid,discount,
                     status,receipt_no,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                  (sid, stid, m, items, total, paid, disc, status, rcpt, now))
        if m == "2026-10":
            inv_ids[stid] = d.execute("SELECT last_insert_rowid()").fetchone()[0]
d.execute("""INSERT INTO payments(invoice_id,amount,pay_date,method,note,verified,created_at)
             VALUES((SELECT id FROM invoices WHERE month='2026-09' LIMIT 1),1800,?,?,?,1,?)""",
          (today, "cash", "", now))

# attendance today (Class 4)
for i, stid in enumerate(sids[:3]):
    stt = ["present", "absent", "late"][i]
    d.execute("INSERT INTO attendance(school_id,student_id,date,status) VALUES(?,?,?,?)",
              (sid, stid, today, stt))

# exam + marks
d.execute("INSERT INTO exams(school_id,name,year,subjects,created_at) VALUES(?,?,?,?,?)",
          (sid, "First Term 2026", 2026, "Urdu,English,Math,Science", now))
eid = 1
marks = {0: [85, 90, 78, 88], 1: [92, 88, 95, 90], 2: [70, 65, 72, 68]}
subs = ["Urdu", "English", "Math", "Science"]
for si, vals in marks.items():
    for j, sub in enumerate(subs):
        d.execute("INSERT INTO marks(exam_id,student_id,subject,obtained,total) VALUES(?,?,?,?,100)",
                  (eid, sids[si], sub, vals[j]))

# staff + slip
d.execute("""INSERT INTO staff(school_id,name,designation,phone,salary_monthly,join_date,created_at)
             VALUES(?,?,?,?,?,?,?)""",
          (sid, "Sir Kashif", "Teacher", "03007777777", 40000, "2024-04-01", now))
d.execute("""INSERT INTO staff(school_id,name,designation,phone,salary_monthly,join_date,created_at)
             VALUES(?,?,?,?,?,?,?)""",
          (sid, "Rafiq Peon", "Peon", "03008888888", 25000, "2023-06-01", now))
d.execute("""INSERT INTO salary_slips(school_id,staff_id,month,basic,allowances,deductions,advance,
             net,paid,pay_date,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
          (sid, 1, "2026-10", 40000, 2000, 500, 1000, 40500, 1, today, now))

# diary
d.execute("INSERT INTO diary(school_id,class,date,subject,text,teacher,created_at) VALUES(?,?,?,?,?,?,?)",
          (sid, "Class 4", today, "Math", "Page 44 exercise 5 (Q1-Q10) yaad karke ayen.", "Sir Kashif", now))
d.execute("INSERT INTO diary(school_id,class,date,subject,text,teacher,created_at) VALUES(?,?,?,?,?,?,?)",
          (sid, "Class 4", today, "Urdu", "Sabaq 6 ki khulasa likhna hai.", "Sir Kashif", now))

# team member
d.execute("INSERT INTO users(school_id,name,email,pw_hash,role,created_at) VALUES(?,?,?,?,?,?)",
          (sid, "Sir Kashif", "teacher@demo.com", generate_password_hash("demo123"), "teacher", now))
d.commit(); d.close()

# ---------- render pages ----------
A.app.config["SERVER_NAME"] = None
client = A.app.test_client()
client.post("/login", data={"email": "demo@demo.com", "password": "demo123"})

dd = sqlite3.connect(TMPDB)
tok = None
inv1 = dd.execute("SELECT id FROM invoices WHERE month='2026-10' LIMIT 1").fetchone()[0]
card_aid = dd.execute("SELECT id FROM applications LIMIT 1").fetchone()[0]
slip_id = dd.execute("SELECT id FROM salary_slips LIMIT 1").fetchone()[0]
rep_sid = sids[0]

PAGES = [
    ("/", "index.html"),
    ("/s/demo-school/", "school.html"),
    ("/s/demo-school/apply", "apply.html"),
    ("/login", "login.html"),
    ("/dashboard", "dashboard.html"),
    ("/dashboard/applications", "applications.html"),
    (f"/dashboard/applications/{card_aid}/card", "idcard.html"),
    ("/dashboard/students", "students.html"),
    ("/dashboard/fees", "fees.html"),
    (f"/dashboard/fees/receipt/{inv1}", "receipt.html"),
    (f"/dashboard/fees/challan/{inv1}", "challan.html"),
    ("/dashboard/attendance?class=Class+4&date=" + today, "attendance.html"),
    ("/dashboard/exams", "exams.html"),
    ("/dashboard/exams/1/merit?class=Class+4", "merit.html"),
    (f"/dashboard/exams/1/report/{rep_sid}", "report.html"),
    ("/dashboard/diary", "diary.html"),
    ("/dashboard/staff", "staff.html"),
    ("/dashboard/payroll", "payroll.html"),
    ("/dashboard/team", "team.html"),
    ("/dashboard/notices", "notices.html"),
    ("/dashboard/content", "content.html"),
]
for url, fn in PAGES:
    r = client.get(url)
    assert r.status_code == 200, f"{url} -> {r.status_code}"
    open(os.path.join(OUT, fn), "w").write(r.get_data(as_text=True))
    print("rendered", fn)

# parent portal (token banta hai students page visit pe)
dd2 = sqlite3.connect(TMPDB)
tok = dd2.execute("SELECT token FROM parent_tokens LIMIT 1").fetchone()
dd2.close()
if tok:
    r = client.get(f"/p/{tok[0]}")
    assert r.status_code == 200
    open(os.path.join(OUT, "portal.html"), "w").write(r.get_data(as_text=True))
    print("rendered portal.html")

# ---------- post-process ----------
LINKMAP = [
    ("/dashboard/applications/", "idcard.html"),
    ("/dashboard/fees/receipt/", "receipt.html"),
    ("/dashboard/fees/challan/", "challan.html"),
    ("/dashboard/fees/collect/", "fees.html"),
    ("/dashboard/exams/", "merit.html"),
    ("/dashboard/fees/verify/", "fees.html"),
    ("/dashboard/students/admit/", "students.html"),
    ("/dashboard/payroll/slip/", "payroll.html"),
    ("/p/", "portal.html"),
    ("/s/demo-school/apply", "apply.html"),
    ("/s/demo-school/", "school.html"),
    ("/dashboard/applications", "applications.html"),
    ("/dashboard/students", "students.html"),
    ("/dashboard/attendance", "attendance.html"),
    ("/dashboard/diary", "diary.html"),
    ("/dashboard/payroll", "payroll.html"),
    ("/dashboard/staff", "staff.html"),
    ("/dashboard/team", "team.html"),
    ("/dashboard/fees", "fees.html"),
    ("/dashboard/exams", "exams.html"),
    ("/dashboard/notices", "notices.html"),
    ("/dashboard/content", "content.html"),
    ("/dashboard/settings", "dashboard.html"),
    ("/dashboard", "dashboard.html"),
    ("/login", "login.html"),
    ("/logout", "index.html"),
    ("/", "index.html"),
]

def rewrite_url(u):
    u = u.split("?")[0].split("#")[0]
    if "/report/" in u:
        return "report.html"
    if "/marks" in u:
        return "exams.html"
    if "/merit" in u:
        return "merit.html"
    for prefix, fn in LINKMAP:
        if u == prefix or u.startswith(prefix):
            return fn
    return None

BANNER = """<div style="position:fixed;bottom:14px;left:50%;transform:translateX(-50%);background:#00394F;color:#fff;padding:10px 22px;border-radius:999px;z-index:99999;font-family:sans-serif;font-weight:700;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.3);white-space:nowrap">👀 Live Demo Preview · <a style="color:#FFC107" href="https://github.com/pclwaqas786-ctrl/schoolweb">GitHub pe code</a></div>
<script>document.querySelectorAll('form').forEach(function(f){f.addEventListener('submit',function(e){e.preventDefault();alert('Ye demo preview hai — yahan save nahi hota 🙂');});});</script>
</body>"""

for fn in os.listdir(OUT):
    if not fn.endswith(".html"): continue
    p = os.path.join(OUT, fn)
    h = open(p).read()
    # static assets -> relative
    h = h.replace('"/static/', '"static/').replace("'/static/", "'static/")
    h = h.replace("http://localhost:5000", LIVE).replace("http://127.0.0.1:5000", LIVE)
    # page links (double-quoted href/action)
    h = re.sub(r'((?:href|action)=)"(/[^"]*)"', lambda m: m.group(1) + '"' + (rewrite_url(m.group(2)) or "#") + '"', h)
    h = h.replace("</body>", BANNER)
    open(p, "w").write(h)

# copy static + uploads
shutil.copytree(os.path.join(BASE, "static"), os.path.join(OUT, "static"), dirs_exist_ok=True)
for f in os.listdir(TMPUP):
    shutil.copy(os.path.join(TMPUP, f), os.path.join(OUT, "static", "uploads", f))
print("DONE ->", OUT, "| pages:", len([f for f in os.listdir(OUT) if f.endswith('.html')]))

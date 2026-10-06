SchoolWeb — har school ki apni website + online admission
=====================================================
PakEducate jesa concept, Python (Flask) me. PC pe chalta hai,
chaaho to baad me online bhi kar sakte ho.

CHALANA (PC pe):
1. Python 3 install karo (python.org se)
2. Is folder me terminal kholo:
     python -m venv venv
     venv\Scripts\activate        (Windows)
     pip install flask
     python app.py
3. Browser me kholo: http://localhost:5000

KYA KYA HAI:
- Landing page (/)
- School register (/register) -> apni website slug ke sath
- Public school website (/s/<slug>/) — Urdu/English toggle, RTL
- Online admission form (/s/<slug>/apply)
- Dashboard: applications (approve/reject), website content,
  notices, email settings

EMAIL (tumhara sawal):
- Ghar ke PC se DIRECT email nahi jata — ISP port 25 block karte hain.
- Is liye Gmail SMTP ka option hai (free):
  Dashboard -> Email Settings me smtp.gmail.com, port 587 (STARTTLS),
  apna Gmail + App Password dalo (Google Account > Security >
  2-Step Verification > App passwords).
- "https wali email" = TLS/SSL wali secure sending — yehi use hota hai
  (STARTTLS port 587 ya SSL port 465). Dono options settings me hain.
- Email configure na ho to bhi form kaam karta hai — application
  dashboard me save rehti hai, email sirf notification hai.

HTTPS (online karne pe):
- Local PC pe http://localhost kaafi hai (HTTPS ki zaroorat nahi).
- Online jana ho to: domain + Caddy server (auto HTTPS, free) ya
  PythonAnywhere/Render jesi free hosting. Us waqt bata dena,
  deploy steps de dunga.

SECURITY:
- Passwords hashed (werkzeug), sessions ke liye random secret key
  (secret.key file me auto-generate).
- Har school sirf apna data dekh sakta hai.

NOTE: Ye v1 hai — website + admission. Attendance/fees/results
(PakEducate wale full features) baad me module ki tarah add ho sakte hain.

v2 COLORFUL UPDATE (29 Sep 2026):
- Poora naya kid-friendly design: teal/navy/coral/amber/green/purple
  palette (KidKinder/Sprout style), Handlee + Nunito fonts (Urdu me
  Noto Nastaliq/Naskh fallback), RTL me bhi perfect.
- Landing page: animated hero (blobs + confetti dots), floating cards,
  wave divider, navy stats strip (animated counters), 6 feature cards,
  4-step "kese kaam karta hai", gradient CTA banner, navy footer.
- School website: hero + floating trust cards, stats strip, colorful
  quick tiles, principal message card, notices (date badges), contact
  chips, admission CTA banner.
- Admission form: colorful 2-column card, mobile friendly.
- Dashboard: colorful stat cards, pill tabs, status badges.
- static/site.js: scroll-reveal + count-up animation (no dependencies).
- Demo school ready: /s/demo-school/ (Roshan Public School) — login
  demo@x.com / demo1234 se dashboard bhi dekh sakte ho.

v2.1 APPLICATION ID (29 Sep 2026):
- Har admission pe unique Application ID: SCHOOL-YEAR-0001
  (misal Faizan Islamic School → FIS-2026-0001, Roshan Public → RPS-2026-0001).
- Student ko success page pe bara ID card dikhta hai (Urdu/English dono me)
  — "ye number note kar lein".
- Dashboard ki recent table aur Applications page pe har student ke sath
  uska ID. Email notification me bhi ID shamil.
- Purani DB khud upgrade ho jati hai (app.py chalate hi migration).

v2.2 PHOTO + STUDENT ID CARD (29 Sep 2026):
- Admission form me photo upload (JPG/PNG/WebP, max 4MB, live preview).
  Photo app_id ke naam se static/uploads/ me save hoti hai.
- Dashboard → Applications me har student ke sath 🪪 ID Card button —
  printable school ID card khulta hai: school header, photo, naam,
  walid, class, DOB, phone, bara ID number, session year. Print button
  se seedha print (card size me).
- Email notification me ab ID shamil hai.
- Pillow ho to photo auto-resize (optional): pip install pillow.

v3.0 TEENO MODULES (29 Sep 2026) — sab free, koi paid SMS/API nahi:
- STUDENTS: approved application → "Admit as Student" → student record
  (photo/ID/class/phone). Students page pe class filter.
- FEES: fee heads (per-class ya all, monthly/one-time) → month ki invoices
  auto-generate → Collect (partial/full, receipt no RCP-XXXX) → printable
  receipt → Defaulters list.
- ATTENDANCE: class+date select → P/A/Late/Leave mark → absent students ke
  liye FREE WhatsApp alert button (wa.me link, message ready — bas Send;
  phone 03xx → 92xx auto-convert). Koi paid SMS gateway nahi.
- EXAMS/RESULTS: exam banayein (subjects comma se) → marks entry grid →
  merit list (position, grade A+..F) → printable bilingual report card
  (Urdu labels, %/position/grade, teacher+principal sign lines).
- Dashboard pe 4 module tiles + live stats (students, fee due, absent today).

v4.0 PROFESSIONAL (6 Oct 2026) — duniya ke bare school systems jaisa:
- ROLE-BASED LOGINS: owner (sab kuch), teacher (Students/Attendance/Exams/Diary),
  accountant (Fees/Payroll). Dashboard → Team me naye logins banayein.
- STAFF & PAYROLL: staff record, staff attendance, monthly salary slips
  (basic+allowances-deductions-advance), printable payslip, paid mark.
- DIGITAL DIARY: teacher roz ka homework post kare → parents portal pe dekhein
  + WhatsApp share button.
- PARENT PORTAL (QR): har student ka QR code → bina login/app ke portal:
  attendance, fee dues + history, diary, results, aur JazzCash/EasyPaisa
  payment PROOF upload (school verify kar ke receipt dega). Sab free!
- FEE CHALLAN: printable bank challan (Bank/School/Parent copy).
  Discount/concession (sirf owner), pichle baqaya auto-arrears agli invoice me.
- Purani DB auto-migrate (naye tables + discount/proof columns).

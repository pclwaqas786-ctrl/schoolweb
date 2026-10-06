# 🏫 SchoolWeb — School Management System

Bare schools jaisa professional school management software — **bilkul free**, koi paid SMS/API nahi.

## ✨ Modules

| Module | Kya karta hai |
|---|---|
| 🌐 Bilingual Website | School ki public website (Urdu + English, RTL) |
| 📝 Online Admissions | Admission form, auto Application ID (`FIS-2026-0001`), photo upload |
| 🪪 Student ID Cards | Photo + ID ke sath printable school ID card |
| 🎒 Students | Approved application → ek click pe admitted student |
| 💰 Fees | Fee heads, auto monthly invoices, raseed, **bank challan**, discount/concession, arrears roll-forward, defaulters + **free WhatsApp reminders** |
| 📋 Attendance | Rozana hazri + ghair-hazir pe **free WhatsApp alert** walid ko |
| 📊 Exams & Results | Marks entry, merit list, **bilingual report card** (Urdu labels) |
| 👥 Role-based Logins | Owner / Teacher / Accountant — har kisi ki apni screen |
| 👔 Staff & Payroll | Staff record, staff attendance, monthly salary slips + printable payslip |
| 📝 Digital Diary | Teacher ka roz ka homework → parents dekhein, WhatsApp share |
| 📱 Parent Portal | Har student ka **QR code** → bina login/app ke attendance, fee, diary, results + JazzCash/EasyPaisa proof upload |

## 🚀 Chalayein

```bash
pip install flask
python app.py
```

Browser me kholein: **http://localhost:5000**

- Pehli dafa: **Register** se school banayein (wahi owner login hai)
- Teacher/Accountant: Dashboard → **Team** me login banayein
- Purani `schoolweb.db` ho to wahi rakhein — database **auto-migrate** ho jati hai, data safe

## 📸 Screenshots

Fee challan, report card, ID card, payslip — sab **print-ready** hain (Print dabayein, "Background graphics" on rakhein).

## 💡 Note

WhatsApp reminders **free** `wa.me` links se hain — koi paid SMS gateway nahi chahiye. Parent portal ke QR codes online QR API se bante hain.

Made for Pakistani private schools 🇵🇰

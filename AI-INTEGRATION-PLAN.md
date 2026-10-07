# SchoolWeb AI Integration Plan
**Goal:** SchoolWeb ko AI-powered school management system banao — taake Claude for Startups ($7,000 bundle: 1 saal Team free + $1,000 API credits) ke liye eligible applicant bano.
**Rule:** Build cost $0. Dev/testing free Groq key par; production Claude credits par.

## AI Features (priority order)

### 1. AI Parent Assistant (sab se valuable)
Parent apni zubaan me puche (Urdu/Roman/English): "mere bache ki fees kitni baqi hai?", "kal diary me kya aya tha?", "result kab ayega?"
- Jawab school ke **apne data** se (SQLite: fees, attendance, diary, exams tables)
- Grounding: sirf us parent ke bache ka data (parent portal QR token se auth — pehle se bana hua hai)
- Bilingual: Urdu + English

### 2. AI Diary / Notice Writer
Teacher rough points likhe → AI polished bilingual diary entry ya notice banaye.
- Input: "kal test hai chapter 5 ka, fees ki last date 20 hai"
- Output: proper Urdu + English diary entry, school letterhead tone

### 3. AI Report Card Comments
Marks data se har bache ke liye personalized comment:
- Input: Ahmed, Class 5, Math 92%, Science 78%, overall trend up
- Output: "Ahmed has shown excellent progress in Mathematics... needs attention in Science..."

## Technical Design

**New module:** `ai_engine.py` (provider-agnostic)
```
ask_ai(prompt, context) → response
- Provider order: Claude API (prod, jab credits milen) → Groq (dev/free fallback)
- API key env var se: CLAUDE_API_KEY / GROQ_API_KEY
- SQLite se context pull karke prompt me inject (grounding)
```

**Data grounding (hallucination se bachao):**
- Parent assistant: SQL query → facts → LLM sirf wording ke liye
- Kabhi raw DB dump prompt me nahi; sirf zaroori rows
- System prompt: "Sirf diye gaye facts se jawab do. Maloom na ho to kaho."

**Safety:**
- Parent sirf apne bache ka data dekhe (existing QR-token auth reuse)
- Fees/numbers hamesha DB se, LLM se calculate nahi karwao

## Build Phases

| Phase | Kaam | Status |
|-------|------|--------|
| 1 | `ai_engine.py` + Diary/Notice Writer (dashboard me button) | ✅ DONE 7 Oct 2026 — tested: generate (bilingual EN+UR) + save, regression OK |
| 2 | Parent Assistant (parent portal me chat UI) | ✅ DONE 7 Oct 2026 — tested: fees/attendance/diary/results grounded answers, bad-token 404, chat UI renders |
| 3 | Report Card Comments (exams module me) | ✅ DONE 7 Oct 2026 — tested: per-student bilingual comments, shown on report card |
| 4 | Demo video + Claude for Startups application | ⬜ PENDING (tumhare side: demo video, Claude Console account, application) |

**Branch:** `ai-integration` (master se). Merge: `git checkout master && git merge ai-integration` (jab tum kaho).

## Claude for Startups Application Checklist
- [x] AI features built: `ai_engine.py` (Claude→Groq), AI Diary Writer, Parent Assistant, Report Comments
- [x] Groq↔Claude switch: `ai_engine.py` me — `CLAUDE_API_KEY` env var set karo, restart karo. Bas. (Groq vault surrogate se, koi key file me nahi)
- [ ] AI features live demo par (HF Space ya GitHub Pages demo me "AI" badge)
- [ ] Company email + website domain (GitHub Pages site chalega: pclwaqas786-ctrl.github.io/schoolweb)
- [ ] Claude Console account banao
- [ ] Application: "AI-powered school management for Pakistani schools — parent assistant, AI diary writer, report comments, Claude-powered"
- [ ] Card ready rakho (Team offer ke liye) + calendar reminder (cancel karne ke liye)
- [ ] Credits milne ke baad: Groq se Claude par switch (ai_engine.py me 1 line)

## Test evidence (7 Oct 2026, Groq free tier)
- `/tmp/test_phase1.py` — AI diary generate+save, bilingual output verified (Urdu script present)
- `/tmp/test_phase2.py` — parent assistant: Rs 3000 due grounded, attendance 25/30, diary + results correct, unknown question honestly declined, bad token → 404
- `/tmp/test_phase3.py` — 2 students personalized bilingual comments, shown on report card
- Regression: register, login, dashboard, fees, diary, merit, portal — all 200 OK

## Ehtiyatein
- API credits 6 mahine me expire — pehle features ready karo, phir claim karo
- Team seats ka card auto-charge kar sakta hai — reminder lagana mat bhulna
- Application me jhoot nahi — jo built hai wahi likho

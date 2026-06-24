# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This is a **graduation thesis project that has not yet been implemented**. The repository currently contains only the assignment brief (`任务书.doc` / `任务书.docx` / `任务书.md`) and an empty `docs/` folder. No source code, dependency manifest, or build configuration exists yet — they need to be created as work begins.

Communicate with the user in **Chinese (简体中文)**. The thesis, code comments, and UI copy are all expected to be in Chinese.

## What is being built

**基于Web的健身房会员信息管理系统** — a web-based gym membership management system with two surfaces:

- **Web 用户端** (member-facing): members browse, book classes, view their own card/booking history.
- **后台管理端** (admin): staff perform CRUD on member profiles, membership cards, class catalog, bookings; run queries; print and aggregate statistics.

Required tech stack (mandated by `任务书.md` §二.2):

- **Backend**: Python + **Flask 3.x**, with Flask-SQLAlchemy + Flask-Migrate, Flask-Login, Flask-WTF (CSRF), Marshmallow
- **Database**: **SQLite** (Alembic migrations, file at `backend/instance/webgym.db`)
- **Frontend**: **Vue 3 + Vite + Element Plus + Pinia + Vue Router 4** (前后端分离 SPA, dev server proxies `/api` to Flask on :5000)

The participating reference bibliography is Spring-Boot-heavy ([1][2][7][9][10]), but 任务书 §二.2 is a hard constraint. Implementation stays on Flask; the thesis uses Spring as a **comparative reference frame** in tech-selection / architecture / security chapters so every cited work appears in the body. See `docs/设计方案.md` §1 for the章节↔文献 mapping.

Non-negotiable requirements from the brief:

- Access control: prevent non-authorized users from modifying stored records (§二.3) — implement auth + role checks (member vs. admin) from the start, not as an afterthought.
- Aesthetically polished, interactive UI (§二.4).
- Test coverage sufficient to catch obvious holes (§二.5).
- The thesis writeup must be ≥ 8000 Chinese characters with a 300–500 character abstract (§三.1).

Deadline: **2026-07-08 → 2026-11-08** (task assigned 2026-07-08, due 2026-11-08).

## Working in this repo

The approved design is locked in `docs/设计方案.md` — **read it before making scope, architecture, or model decisions**. The repo is split into `backend/` (Flask app, application-factory layout) and `frontend/` (Vite + Vue 3). Neither has been scaffolded yet; W1 of the plan creates them.

Implementation milestones live in `docs/设计方案.md` §10 (12-week schedule). Each week's deliverable maps to a thesis chapter via `docs/设计方案.md` §9.

## Reference materials

- `docs/设计方案.md` — **the approved design**. Single source of truth for architecture, data model, routes, milestones.
- `任务书.md` — authoritative source for scope, requirements, deadlines, and the reference bibliography. **Re-read it before making scope decisions** — don't infer requirements from memory.
- `docs/` — design documents, requirement analysis, ER diagrams, test reports (thesis raw material).

## Environment notes

- Platform is **Windows 11** with **bash** (Git Bash / MSYS). Use Unix shell syntax in commands but forward-slash paths, and remember Python is invoked as `python` (not `python3`) on this machine.
- Microsoft Word is installed and reachable via `win32com.client` — useful for `.doc` ↔ `.docx` conversion when handling Chinese-language source documents (MarkItDown only accepts `.docx`).
- LibreOffice is **not** installed; don't suggest `soffice` as a conversion path.


import os
import sqlite3
import json
import base64
from flask import Flask, request, jsonify, send_file, g
from flask_cors import CORS
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "labour_portal.db"
ADMIN_PIN = "9999"

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_NAME)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Core tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS labours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            location TEXT,
            skill TEXT,
            experience TEXT,
            daily_wage TEXT,
            status TEXT DEFAULT 'Available',
            assigned_contractor TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS contractor_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractor_name TEXT,
            phone TEXT,
            location TEXT,
            work_type TEXT,
            workers_needed INTEGER,
            wage_offered TEXT,
            requirements TEXT,
            photo_data TEXT DEFAULT '',
            status TEXT DEFAULT 'Open',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Schema migrations (safe ALTER TABLE)
    existing_cols = [r[1] for r in c.execute("PRAGMA table_info(labours)").fetchall()]
    if 'assigned_contractor' not in existing_cols:
        c.execute("ALTER TABLE labours ADD COLUMN assigned_contractor TEXT DEFAULT ''")
    if 'status' not in existing_cols:
        c.execute("ALTER TABLE labours ADD COLUMN status TEXT DEFAULT 'Available'")

    job_cols = [r[1] for r in c.execute("PRAGMA table_info(contractor_jobs)").fetchall()]
    if 'photo_data' not in job_cols:
        c.execute("ALTER TABLE contractor_jobs ADD COLUMN photo_data TEXT DEFAULT ''")
    if 'status' not in job_cols:
        c.execute("ALTER TABLE contractor_jobs ADD COLUMN status TEXT DEFAULT 'Open'")

    # New v5 tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            worker_id INTEGER NOT NULL,
            worker_name TEXT,
            worker_phone TEXT,
            status TEXT DEFAULT 'Pending',
            applied_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(job_id) REFERENCES contractor_jobs(id),
            FOREIGN KEY(worker_id) REFERENCES labours(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS worker_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL,
            reviewer_name TEXT,
            rating INTEGER,
            comment TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(worker_id) REFERENCES labours(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL,
            amount REAL,
            type TEXT,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(worker_id) REFERENCES labours(id)
        )
    """)

    # Seed data
    count = c.execute("SELECT COUNT(*) FROM labours").fetchone()[0]
    if count == 0:
        seed = [
            ("రాజు కుమార్", "9876543210", "Hyderabad", "Mason", "5 years", "700"),
            ("सुरेश यादव", "9123456789", "Mumbai", "Electrician", "3 years", "800"),
            ("Ramesh Kumar", "9988776655", "Bangalore", "Plumber", "7 years", "750"),
            ("అర్జున్ రెడ్డి", "9871234560", "Hyderabad", "Painter", "4 years", "600"),
            ("Priya Singh", "9765432100", "Delhi", "Carpenter", "6 years", "850"),
            ("మహేష్ బాబు", "9654321098", "Vijayawada", "Welder", "8 years", "900"),
        ]
        for s in seed:
            try:
                c.execute("""INSERT INTO labours (name,phone,location,skill,experience,daily_wage)
                             VALUES (?,?,?,?,?,?)""", s)
            except:
                pass

    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────────
# HTML TEMPLATE  (v5.0 — Startup Redesign)
# ─────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0"/>
<title>ShramikLink — Work. Connect. Grow.</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Noto+Sans+Devanagari:wght@400;600;700&family=Noto+Sans+Telugu:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
/* ══════════════════════════════════════════
   DESIGN TOKENS
══════════════════════════════════════════ */
:root {
  --brand-primary: #f97316;
  --brand-dark:    #c2410c;
  --brand-light:   #fff7ed;
  --brand-accent:  #0ea5e9;
  --success:       #22c55e;
  --error:         #ef4444;
  --warn:          #eab308;

  --bg-page:       #f8fafc;
  --bg-card:       #ffffff;
  --bg-dark:       #0f172a;

  --text-primary:  #0f172a;
  --text-secondary:#475569;
  --text-muted:    #94a3b8;
  --text-white:    #ffffff;

  --border:        #e2e8f0;
  --border-focus:  #f97316;

  --radius-sm:     8px;
  --radius-md:     12px;
  --radius-lg:     16px;
  --radius-xl:     24px;
  --radius-full:   9999px;

  --shadow-sm:     0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06);
  --shadow-md:     0 4px 16px rgba(0,0,0,.10);
  --shadow-lg:     0 10px 40px rgba(0,0,0,.14);
  --shadow-brand:  0 8px 24px rgba(249,115,22,.30);

  --nav-h:         64px;
  --bottom-nav-h:  68px;
  --font-main:     'Inter', 'Noto Sans Devanagari', 'Noto Sans Telugu', sans-serif;
}

*,*::before,*::after { box-sizing:border-box; margin:0; padding:0; }
html { scroll-behavior:smooth; }
body {
  font-family: var(--font-main);
  background: var(--bg-page);
  color: var(--text-primary);
  min-height: 100vh;
  overflow-x: hidden;
}

/* ══════════════════════════════════════════
   ENTRY GATE OVERLAY
══════════════════════════════════════════ */
#roleGateOverlay {
  position: fixed;
  inset: 0;
  z-index: 99999;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  transition: opacity .5s ease;
}
#roleGateOverlay.hidden {
  opacity: 0;
  pointer-events: none;
}
.gate-card {
  background: rgba(255,255,255,.06);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: var(--radius-xl);
  padding: 40px 32px;
  max-width: 420px;
  width: 90%;
  text-align: center;
  animation: gateIn .6s ease;
}
@keyframes gateIn {
  from { opacity:0; transform:translateY(30px) scale(.96); }
  to   { opacity:1; transform:translateY(0) scale(1); }
}
.gate-logo {
  font-size: 2.2rem;
  font-weight: 900;
  color: #fff;
  letter-spacing: -1px;
  margin-bottom: 4px;
}
.gate-logo span { color: var(--brand-primary); }
.gate-tagline {
  font-size: .875rem;
  color: rgba(255,255,255,.6);
  margin-bottom: 36px;
}
.gate-title {
  font-size: 1.1rem;
  color: rgba(255,255,255,.85);
  font-weight: 600;
  margin-bottom: 24px;
}
.gate-btns { display: flex; flex-direction: column; gap: 12px; }
.gate-btn {
  padding: 16px 24px;
  border-radius: var(--radius-lg);
  border: none;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all .2s;
  font-family: var(--font-main);
}
.gate-btn-user {
  background: var(--brand-primary);
  color: #fff;
  box-shadow: var(--shadow-brand);
}
.gate-btn-user:hover { background: var(--brand-dark); transform: translateY(-2px); }
.gate-btn-admin {
  background: rgba(255,255,255,.1);
  color: rgba(255,255,255,.9);
  border: 1px solid rgba(255,255,255,.2);
}
.gate-btn-admin:hover { background: rgba(255,255,255,.18); transform: translateY(-2px); }
#adminPinSection { display: none; margin-top: 20px; }
#adminPinSection.visible { display: block; }
.pin-dots {
  display: flex;
  justify-content: center;
  gap: 14px;
  margin: 16px 0 20px;
}
.pin-dot {
  width: 18px; height: 18px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,.5);
  background: transparent;
  transition: all .2s;
}
.pin-dot.filled { background: var(--brand-primary); border-color: var(--brand-primary); }
.pin-keypad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  max-width: 240px;
  margin: 0 auto 16px;
}
.pin-key {
  padding: 14px;
  background: rgba(255,255,255,.1);
  border: 1px solid rgba(255,255,255,.15);
  border-radius: var(--radius-md);
  color: #fff;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s;
  font-family: var(--font-main);
}
.pin-key:hover { background: rgba(255,255,255,.22); transform: scale(1.04); }
.pin-key:active { transform: scale(.96); }
.pin-error {
  color: #fca5a5;
  font-size: .85rem;
  min-height: 20px;
  margin-bottom: 8px;
}
.pin-back { grid-column: 3; }

/* ══════════════════════════════════════════
   TOP NAVIGATION
══════════════════════════════════════════ */
#topNav {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 1000;
  height: var(--nav-h);
  background: rgba(255,255,255,.9);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 16px;
}
.nav-logo {
  font-size: 1.4rem;
  font-weight: 900;
  color: var(--text-primary);
  letter-spacing: -1px;
  text-decoration: none;
  cursor: pointer;
}
.nav-logo span { color: var(--brand-primary); }
.nav-links {
  display: flex;
  gap: 4px;
  margin-left: 20px;
}
.nav-link {
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: .875rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  border: none;
  background: none;
  transition: all .2s;
  font-family: var(--font-main);
}
.nav-link:hover, .nav-link.active { color: var(--brand-primary); background: var(--brand-light); }
.nav-spacer { flex: 1; }
.nav-lang {
  display: flex;
  gap: 4px;
  background: var(--bg-page);
  border-radius: var(--radius-full);
  padding: 4px;
}
.lang-btn {
  padding: 5px 12px;
  border-radius: var(--radius-full);
  border: none;
  background: none;
  font-size: .8rem;
  font-weight: 600;
  cursor: pointer;
  color: var(--text-muted);
  transition: all .2s;
  font-family: var(--font-main);
}
.lang-btn.active { background: var(--brand-primary); color: #fff; }
.nav-cta {
  padding: 9px 20px;
  background: var(--brand-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-full);
  font-size: .875rem;
  font-weight: 700;
  cursor: pointer;
  transition: all .2s;
  font-family: var(--font-main);
}
.nav-cta:hover { background: var(--brand-dark); transform: translateY(-1px); }

/* Mobile nav burger */
.nav-burger { display: none; flex-direction: column; gap: 5px; cursor: pointer; padding: 8px; }
.nav-burger span { display: block; width: 22px; height: 2px; background: var(--text-primary); border-radius: 2px; transition: .3s; }
@media(max-width:768px) {
  .nav-links, .nav-lang, .nav-cta { display: none; }
  .nav-burger { display: flex; }
  .nav-logo { font-size: 1.2rem; }
}

/* ══════════════════════════════════════════
   MOBILE BOTTOM NAVIGATION
══════════════════════════════════════════ */
#bottomNav {
  display: none;
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: var(--bottom-nav-h);
  background: #fff;
  border-top: 1px solid var(--border);
  z-index: 999;
  padding: 0 8px 8px;
  align-items: center;
}
@media(max-width:768px) { #bottomNav { display: flex; } }
.bottom-nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 6px 4px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  border: none;
  background: none;
  color: var(--text-muted);
  font-size: .65rem;
  font-weight: 500;
  transition: all .2s;
  font-family: var(--font-main);
}
.bottom-nav-item.active { color: var(--brand-primary); }
.bottom-nav-item svg { width: 22px; height: 22px; }
.bnav-post {
  background: var(--brand-primary) !important;
  color: #fff !important;
  border-radius: 14px !important;
  padding: 10px 4px !important;
  box-shadow: var(--shadow-brand);
}

/* ══════════════════════════════════════════
   PAGE LAYOUT
══════════════════════════════════════════ */
#appContent {
  padding-top: var(--nav-h);
  min-height: 100vh;
}
@media(max-width:768px) { #appContent { padding-bottom: var(--bottom-nav-h); } }

.page { display: none; }
.page.active { display: block; }

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
@media(max-width:640px) { .container { padding: 0 16px; } }

/* ══════════════════════════════════════════
   HERO SECTION
══════════════════════════════════════════ */
.hero {
  position: relative;
  min-height: 540px;
  display: flex;
  align-items: center;
  overflow: hidden;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0f172a 100%);
}
.hero-bg {
  position: absolute;
  inset: 0;
  background-image: url('https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=1600&q=80');
  background-size: cover;
  background-position: center;
  opacity: .22;
}
.hero-content {
  position: relative;
  z-index: 1;
  padding: 80px 0;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(249,115,22,.18);
  border: 1px solid rgba(249,115,22,.4);
  color: #fdba74;
  padding: 6px 16px;
  border-radius: var(--radius-full);
  font-size: .8rem;
  font-weight: 600;
  margin-bottom: 24px;
}
.hero-title {
  font-size: clamp(2rem, 5vw, 3.5rem);
  font-weight: 900;
  color: #fff;
  line-height: 1.15;
  letter-spacing: -1px;
  margin-bottom: 20px;
}
.hero-title span { color: var(--brand-primary); }
.hero-sub {
  font-size: clamp(.95rem, 2vw, 1.2rem);
  color: rgba(255,255,255,.72);
  max-width: 560px;
  line-height: 1.65;
  margin-bottom: 40px;
}
.hero-search {
  display: flex;
  gap: 10px;
  max-width: 580px;
  background: #fff;
  border-radius: var(--radius-xl);
  padding: 8px 8px 8px 20px;
  box-shadow: var(--shadow-lg);
}
.hero-search input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 1rem;
  font-family: var(--font-main);
  color: var(--text-primary);
  background: none;
}
.hero-search input::placeholder { color: var(--text-muted); }
.hero-search button {
  padding: 12px 24px;
  background: var(--brand-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-lg);
  font-size: .9rem;
  font-weight: 700;
  cursor: pointer;
  transition: .2s;
  white-space: nowrap;
  font-family: var(--font-main);
}
.hero-search button:hover { background: var(--brand-dark); }
.hero-stats {
  display: flex;
  gap: 40px;
  margin-top: 48px;
  flex-wrap: wrap;
}
.hero-stat { text-align: left; }
.hero-stat-num {
  font-size: 1.8rem;
  font-weight: 800;
  color: #fff;
  line-height: 1;
}
.hero-stat-label {
  font-size: .8rem;
  color: rgba(255,255,255,.55);
  margin-top: 3px;
}
@media(max-width:640px) {
  .hero-search { flex-direction: column; padding: 12px; }
  .hero-stats { gap: 24px; }
}

/* ══════════════════════════════════════════
   SECTION COMMON
══════════════════════════════════════════ */
.section { padding: 64px 0; }
.section-sm { padding: 40px 0; }
.section-dark { background: var(--bg-dark); color: #fff; }
.section-brand { background: linear-gradient(135deg, var(--brand-primary), var(--brand-dark)); color: #fff; }

.section-header { text-align: center; margin-bottom: 48px; }
.section-eyebrow {
  font-size: .8rem;
  font-weight: 700;
  color: var(--brand-primary);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  margin-bottom: 12px;
}
.section-title {
  font-size: clamp(1.6rem, 3.5vw, 2.4rem);
  font-weight: 800;
  letter-spacing: -0.5px;
  margin-bottom: 14px;
}
.section-sub {
  font-size: 1rem;
  color: var(--text-secondary);
  max-width: 520px;
  margin: 0 auto;
  line-height: 1.65;
}
.section-dark .section-sub { color: rgba(255,255,255,.6); }

/* ══════════════════════════════════════════
   CATEGORY CARDS (Home Page)
══════════════════════════════════════════ */
.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
}
.cat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all .25s;
  box-shadow: var(--shadow-sm);
}
.cat-card:hover {
  border-color: var(--brand-primary);
  box-shadow: var(--shadow-brand);
  transform: translateY(-4px);
}
.cat-icon { font-size: 2.2rem; margin-bottom: 10px; }
.cat-name { font-size: .9rem; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.cat-count { font-size: .78rem; color: var(--text-muted); }

/* ══════════════════════════════════════════
   HOW IT WORKS
══════════════════════════════════════════ */
.how-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 32px;
}
.how-step {
  text-align: center;
  padding: 32px 24px;
  background: rgba(255,255,255,.05);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255,255,255,.1);
}
.how-num {
  width: 52px; height: 52px;
  background: var(--brand-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  font-weight: 800;
  color: #fff;
  margin: 0 auto 20px;
}
.how-step h3 { font-size: 1.05rem; font-weight: 700; color: #fff; margin-bottom: 10px; }
.how-step p { font-size: .875rem; color: rgba(255,255,255,.6); line-height: 1.6; }

/* ══════════════════════════════════════════
   WORKER CARDS
══════════════════════════════════════════ */
.filters-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 28px;
  align-items: center;
}
.filter-input {
  flex: 1;
  min-width: 200px;
  padding: 11px 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  font-size: .9rem;
  font-family: var(--font-main);
  background: var(--bg-card);
  transition: .2s;
}
.filter-input:focus { border-color: var(--border-focus); outline: none; box-shadow: 0 0 0 3px rgba(249,115,22,.12); }
.filter-select {
  padding: 11px 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  font-size: .9rem;
  font-family: var(--font-main);
  background: var(--bg-card);
  cursor: pointer;
  transition: .2s;
}
.filter-select:focus { border-color: var(--border-focus); outline: none; }

.workers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.worker-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-sm);
  transition: all .25s;
  position: relative;
  overflow: hidden;
}
.worker-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.worker-card-top { display: flex; align-items: flex-start; gap: 16px; margin-bottom: 16px; }
.worker-avatar {
  width: 56px; height: 56px;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-dark));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  flex-shrink: 0;
}
.worker-info { flex: 1; }
.worker-name { font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.worker-skill {
  display: inline-block;
  background: var(--brand-light);
  color: var(--brand-primary);
  border-radius: var(--radius-full);
  padding: 3px 10px;
  font-size: .75rem;
  font-weight: 600;
  margin-bottom: 6px;
}
.worker-loc { font-size: .82rem; color: var(--text-muted); display: flex; align-items: center; gap: 4px; }
.worker-status-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: .72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .5px;
}
.status-available { background: #dcfce7; color: #15803d; }
.status-busy { background: #fee2e2; color: #b91c1c; }

.worker-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 16px;
  padding: 14px;
  background: var(--bg-page);
  border-radius: var(--radius-md);
}
.meta-item { }
.meta-label { font-size: .72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; margin-bottom: 2px; }
.meta-value { font-size: .9rem; font-weight: 600; color: var(--text-primary); }

.busy-tag {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: .8rem;
  color: #c2410c;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.worker-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.btn {
  padding: 9px 16px;
  border-radius: var(--radius-md);
  font-size: .85rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all .2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-main);
  white-space: nowrap;
}
.btn-primary { background: var(--brand-primary); color: #fff; flex: 1; justify-content: center; }
.btn-primary:hover { background: var(--brand-dark); }
.btn-wa { background: #25d366; color: #fff; flex: 1; justify-content: center; }
.btn-wa:hover { background: #128c3e; }
.btn-outline { background: none; border: 1.5px solid var(--border); color: var(--text-secondary); }
.btn-outline:hover { border-color: var(--brand-primary); color: var(--brand-primary); }
.btn-danger { background: var(--error); color: #fff; }
.btn-danger:hover { background: #dc2626; }
.btn-success { background: var(--success); color: #fff; }
.btn-success:hover { background: #16a34a; }
.btn-sm { padding: 7px 12px; font-size: .8rem; }
.btn-lg { padding: 14px 28px; font-size: 1rem; border-radius: var(--radius-lg); }
.btn-full { width: 100%; justify-content: center; }

/* Admin-only elements */
.admin-only { display: none; }
body.is-admin .admin-only { display: inline-flex; }

/* ══════════════════════════════════════════
   REGISTER WIZARD
══════════════════════════════════════════ */
.wizard-card {
  max-width: 600px;
  margin: 0 auto;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}
.wizard-header {
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-dark));
  padding: 32px 36px;
  color: #fff;
}
.wizard-header h2 { font-size: 1.5rem; font-weight: 800; margin-bottom: 6px; }
.wizard-header p { font-size: .875rem; opacity: .8; }
.wizard-progress-bar {
  height: 4px;
  background: rgba(255,255,255,.25);
  border-radius: 2px;
  margin-top: 20px;
  overflow: hidden;
}
.wizard-progress-fill {
  height: 100%;
  background: #fff;
  border-radius: 2px;
  transition: width .4s ease;
}
.wizard-steps-indicator {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
.ws-dot {
  height: 4px;
  border-radius: 2px;
  background: rgba(255,255,255,.35);
  flex: 1;
  transition: .3s;
}
.ws-dot.active { background: #fff; }

.wizard-body { padding: 36px; }
.wizard-step { display: none; }
.wizard-step.active { display: block; }

.form-group { margin-bottom: 20px; }
.form-label {
  display: block;
  font-size: .85rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  font-size: .95rem;
  font-family: var(--font-main);
  transition: .2s;
  background: var(--bg-page);
}
.form-input:focus { border-color: var(--border-focus); outline: none; box-shadow: 0 0 0 3px rgba(249,115,22,.12); background: #fff; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media(max-width:480px) { .form-row { grid-template-columns: 1fr; } }

.wizard-nav {
  display: flex;
  justify-content: space-between;
  margin-top: 28px;
  gap: 12px;
}

/* ══════════════════════════════════════════
   JOB CARDS
══════════════════════════════════════════ */
.jobs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}
.job-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-sm);
  transition: all .25s;
  position: relative;
}
.job-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.job-header { margin-bottom: 16px; }
.job-type-badge {
  display: inline-block;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-dark));
  color: #fff;
  border-radius: var(--radius-full);
  padding: 4px 12px;
  font-size: .75rem;
  font-weight: 700;
  margin-bottom: 10px;
}
.job-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.job-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: 14px 0;
}
.job-meta-item {
  background: var(--bg-page);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-size: .82rem;
}
.job-meta-item strong { display: block; color: var(--text-muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 2px; font-weight: 600; }
.job-photo { width: 100%; border-radius: var(--radius-md); margin: 12px 0; cursor: zoom-in; object-fit: cover; max-height: 180px; }
.job-actions { display: flex; gap: 8px; margin-top: 14px; }

/* ══════════════════════════════════════════
   POST JOB FORM
══════════════════════════════════════════ */
.post-card {
  max-width: 680px;
  margin: 0 auto;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  padding: 40px;
  box-shadow: var(--shadow-lg);
}
@media(max-width:640px) { .post-card { padding: 24px; } }
.photo-upload-zone {
  border: 2px dashed var(--border);
  border-radius: var(--radius-lg);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: .2s;
  margin-bottom: 20px;
}
.photo-upload-zone:hover { border-color: var(--brand-primary); background: var(--brand-light); }
.photo-upload-zone.has-photo { border-style: solid; border-color: var(--success); }
.upload-icon { font-size: 2rem; margin-bottom: 8px; }
.upload-text { font-size: .875rem; color: var(--text-muted); }
#photoPreview { max-width: 100%; border-radius: var(--radius-md); display: none; margin-top: 12px; }

/* ══════════════════════════════════════════
   TOAST NOTIFICATIONS
══════════════════════════════════════════ */
#toastContainer {
  position: fixed;
  top: 80px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.toast {
  min-width: 280px;
  max-width: 380px;
  padding: 14px 20px;
  border-radius: var(--radius-md);
  color: #fff;
  font-size: .875rem;
  font-weight: 500;
  box-shadow: var(--shadow-lg);
  animation: toastIn .3s ease;
  display: flex;
  align-items: center;
  gap: 10px;
}
@keyframes toastIn {
  from { opacity:0; transform:translateX(30px); }
  to   { opacity:1; transform:translateX(0); }
}
.toast.success { background: #16a34a; }
.toast.error   { background: var(--error); }
.toast.info    { background: var(--brand-accent); }
.toast.warn    { background: var(--warn); }

/* ══════════════════════════════════════════
   MODALS
══════════════════════════════════════════ */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.55);
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
}
.modal-backdrop.hidden { display: none; }
.modal {
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  padding: 32px;
  max-width: 480px;
  width: 100%;
  box-shadow: var(--shadow-lg);
  animation: modalIn .3s ease;
  max-height: 90vh;
  overflow-y: auto;
}
@keyframes modalIn {
  from { opacity:0; transform:scale(.94) translateY(20px); }
  to   { opacity:1; transform:scale(1) translateY(0); }
}
.modal-title { font-size: 1.3rem; font-weight: 800; margin-bottom: 20px; }
.modal-close {
  float: right;
  background: none;
  border: none;
  font-size: 1.4rem;
  cursor: pointer;
  color: var(--text-muted);
  margin-top: -4px;
}
.modal-close:hover { color: var(--error); }

/* ══════════════════════════════════════════
   HIRE MODAL / ASSIGN CONTRACTOR
══════════════════════════════════════════ */
#hireModal, #reviewModal { }

/* ══════════════════════════════════════════
   LIGHTBOX
══════════════════════════════════════════ */
#lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.9);
  z-index: 8000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
#lightbox.hidden { display: none; }
#lightbox img { max-width: 100%; max-height: 90vh; border-radius: var(--radius-lg); }
#lightboxClose {
  position: absolute;
  top: 20px; right: 24px;
  color: #fff;
  font-size: 2rem;
  cursor: pointer;
  background: none;
  border: none;
}

/* ══════════════════════════════════════════
   ADMIN PANEL PAGE
══════════════════════════════════════════ */
#adminPage { display: none; }
body.is-admin #adminPage.active { display: block; }
.admin-section-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 28px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border);
}
.admin-section-card h3 { font-size: 1.1rem; font-weight: 700; margin-bottom: 16px; }

/* ══════════════════════════════════════════
   TRUST SECTION
══════════════════════════════════════════ */
.trust-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
}
.trust-item {
  text-align: center;
  padding: 28px 20px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}
.trust-icon { font-size: 2rem; margin-bottom: 12px; }
.trust-item h4 { font-size: .95rem; font-weight: 700; margin-bottom: 6px; }
.trust-item p { font-size: .82rem; color: var(--text-muted); }

/* ══════════════════════════════════════════
   FOOTER
══════════════════════════════════════════ */
footer {
  background: var(--bg-dark);
  color: rgba(255,255,255,.6);
  padding: 48px 0 32px;
}
.footer-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 40px;
  margin-bottom: 40px;
}
@media(max-width:768px) { .footer-grid { grid-template-columns: 1fr 1fr; } }
@media(max-width:480px) { .footer-grid { grid-template-columns: 1fr; } }
.footer-brand-name { font-size: 1.3rem; font-weight: 900; color: #fff; margin-bottom: 10px; }
.footer-brand-name span { color: var(--brand-primary); }
.footer-desc { font-size: .85rem; line-height: 1.65; max-width: 280px; }
.footer-col h4 { font-size: .9rem; font-weight: 700; color: #fff; margin-bottom: 16px; }
.footer-col ul { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.footer-col ul li a { font-size: .83rem; color: rgba(255,255,255,.5); text-decoration: none; transition: .2s; }
.footer-col ul li a:hover { color: var(--brand-primary); }
.footer-bottom {
  border-top: 1px solid rgba(255,255,255,.08);
  padding-top: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  font-size: .8rem;
}
.footer-bottom a { color: var(--brand-primary); text-decoration: none; }

/* ══════════════════════════════════════════
   FLOATING WA BUTTON
══════════════════════════════════════════ */
.float-wa {
  position: fixed;
  bottom: calc(var(--bottom-nav-h) + 16px);
  right: 20px;
  z-index: 900;
  width: 54px; height: 54px;
  background: #25d366;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(37,211,102,.4);
  text-decoration: none;
  transition: .25s;
  font-size: 1.6rem;
}
@media(min-width:769px) { .float-wa { bottom: 24px; } }
.float-wa:hover { transform: scale(1.12); }

/* ══════════════════════════════════════════
   UTILITIES
══════════════════════════════════════════ */
.text-center { text-align: center; }
.mt-8 { margin-top: 8px; }
.mt-16 { margin-top: 16px; }
.mt-24 { margin-top: 24px; }
.mb-8 { margin-bottom: 8px; }
.mb-16 { margin-bottom: 16px; }
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}
.empty-state .empty-icon { font-size: 3.5rem; margin-bottom: 16px; }
.empty-state p { font-size: 1rem; }
.chip {
  display: inline-block;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: .78rem;
  font-weight: 600;
}
.chip-orange { background: var(--brand-light); color: var(--brand-primary); }
.chip-blue { background: #e0f2fe; color: #0369a1; }
.chip-green { background: #dcfce7; color: #15803d; }

/* Page transitions */
.page { animation: fadeIn .3s ease; }
@keyframes fadeIn { from { opacity:0; } to { opacity:1; } }

/* Loading spinner */
.spinner {
  width: 40px; height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--brand-primary);
  border-radius: 50%;
  animation: spin .7s linear infinite;
  margin: 40px auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Rating stars */
.stars { color: var(--warn); font-size: 1.1rem; letter-spacing: 1px; }
</style>
</head>
<body>

<!-- ══════════════════════════════════════════
     ENTRY GATE
══════════════════════════════════════════ -->
<div id="roleGateOverlay">
  <div class="gate-card">
    <div class="gate-logo">Shramik<span>Link</span></div>
    <div class="gate-tagline">Work. Connect. Grow.</div>

    <div id="gateRoleSection">
      <div class="gate-title">Who are you?</div>
      <div class="gate-btns">
        <button class="gate-btn gate-btn-user" onclick="enterAsUser()">
          👷 I am a User / Public
        </button>
        <button class="gate-btn gate-btn-admin" onclick="showAdminPinEntry()">
          🔐 I am an Admin
        </button>
      </div>
    </div>

    <div id="adminPinSection">
      <div class="gate-title" style="color:rgba(255,255,255,.85)">Enter Admin PIN</div>
      <div class="pin-dots" id="pinDots">
        <div class="pin-dot" id="dot0"></div>
        <div class="pin-dot" id="dot1"></div>
        <div class="pin-dot" id="dot2"></div>
        <div class="pin-dot" id="dot3"></div>
      </div>
      <div class="pin-keypad" id="pinKeypad">
        <button class="pin-key" onclick="pinPress('1')">1</button>
        <button class="pin-key" onclick="pinPress('2')">2</button>
        <button class="pin-key" onclick="pinPress('3')">3</button>
        <button class="pin-key" onclick="pinPress('4')">4</button>
        <button class="pin-key" onclick="pinPress('5')">5</button>
        <button class="pin-key" onclick="pinPress('6')">6</button>
        <button class="pin-key" onclick="pinPress('7')">7</button>
        <button class="pin-key" onclick="pinPress('8')">8</button>
        <button class="pin-key" onclick="pinPress('9')">9</button>
        <button class="pin-key" onclick="pinClear()" style="font-size:.85rem">CLR</button>
        <button class="pin-key" onclick="pinPress('0')">0</button>
        <button class="pin-key pin-back" onclick="pinBackspace()">⌫</button>
      </div>
      <div class="pin-error" id="pinError"></div>
      <button class="gate-btn gate-btn-admin" style="width:100%;font-size:.85rem" onclick="showRoleSection()">← Back</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════
     TOAST CONTAINER
══════════════════════════════════════════ -->
<div id="toastContainer"></div>

<!-- ══════════════════════════════════════════
     LIGHTBOX
══════════════════════════════════════════ -->
<div id="lightbox" class="hidden">
  <button id="lightboxClose" onclick="closeLightbox()">✕</button>
  <img id="lightboxImg" src="" alt=""/>
</div>

<!-- ══════════════════════════════════════════
     HIRE / ASSIGN MODAL
══════════════════════════════════════════ -->
<div id="hireModalBackdrop" class="modal-backdrop hidden">
  <div class="modal">
    <button class="modal-close" onclick="closeHireModal()">✕</button>
    <div class="modal-title">📋 Assign Worker</div>
    <p style="font-size:.875rem;color:var(--text-secondary);margin-bottom:20px">Enter contractor name to assign this worker. They will show as <strong>Busy</strong>.</p>
    <div class="form-group">
      <label class="form-label">Contractor Name (can write in Hindi / Telugu)</label>
      <input class="form-input" type="text" id="contractorNameInput" placeholder="e.g. రాహుల్ కాంట్రాక్టర్"/>
    </div>
    <div style="display:flex;gap:10px">
      <button class="btn btn-primary btn-full" onclick="confirmAssign()">✔ Assign Worker</button>
      <button class="btn btn-outline" onclick="closeHireModal()">Cancel</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════
     REVIEW MODAL
══════════════════════════════════════════ -->
<div id="reviewModalBackdrop" class="modal-backdrop hidden">
  <div class="modal">
    <button class="modal-close" onclick="closeReviewModal()">✕</button>
    <div class="modal-title">⭐ Rate this Worker</div>
    <div class="form-group">
      <label class="form-label">Your Name</label>
      <input class="form-input" type="text" id="reviewerName" placeholder="Your name"/>
    </div>
    <div class="form-group">
      <label class="form-label">Rating</label>
      <select class="form-input" id="reviewRating">
        <option value="5">⭐⭐⭐⭐⭐ Excellent (5)</option>
        <option value="4">⭐⭐⭐⭐ Good (4)</option>
        <option value="3">⭐⭐⭐ Average (3)</option>
        <option value="2">⭐⭐ Poor (2)</option>
        <option value="1">⭐ Very Poor (1)</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">Your Review</label>
      <textarea class="form-input" id="reviewComment" rows="3" placeholder="Describe your experience..."></textarea>
    </div>
    <div style="display:flex;gap:10px">
      <button class="btn btn-primary btn-full" onclick="submitReview()">Submit Review</button>
      <button class="btn btn-outline" onclick="closeReviewModal()">Cancel</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════
     TOP NAVIGATION
══════════════════════════════════════════ -->
<nav id="topNav">
  <div class="nav-logo" onclick="showPage('home')">Shramik<span>Link</span></div>
  <div class="nav-links">
    <button class="nav-link" onclick="showPage('home')" id="nl-home">Home</button>
    <button class="nav-link" onclick="showPage('workers')" id="nl-workers">Find Workers</button>
    <button class="nav-link" onclick="showPage('jobs')" id="nl-jobs">Jobs</button>
    <button class="nav-link" onclick="showPage('register')" id="nl-register">Register</button>
    <button class="nav-link" onclick="showPage('post')" id="nl-post">Post a Job</button>
    <button class="nav-link admin-only" onclick="showPage('admin')" id="nl-admin">⚙ Admin</button>
  </div>
  <div class="nav-spacer"></div>
  <div class="nav-lang">
    <button class="lang-btn active" onclick="setLang('en')" id="lb-en">EN</button>
    <button class="lang-btn" onclick="setLang('hi')" id="lb-hi">हिन्दी</button>
    <button class="lang-btn" onclick="setLang('te')" id="lb-te">తెలుగు</button>
  </div>
  <button class="nav-cta" onclick="showPage('register')" id="nav-join-btn">Join as Worker</button>
  <div class="nav-burger" onclick="toggleMobileMenu()">
    <span></span><span></span><span></span>
  </div>
</nav>

<!-- Mobile Menu Drawer (simple) -->
<div id="mobileMenu" style="display:none;position:fixed;top:64px;left:0;right:0;background:#fff;border-bottom:1px solid var(--border);z-index:998;padding:16px;">
  <div style="display:flex;flex-direction:column;gap:4px">
    <button class="nav-link" onclick="showPage('home');toggleMobileMenu()">🏠 Home</button>
    <button class="nav-link" onclick="showPage('workers');toggleMobileMenu()">👷 Find Workers</button>
    <button class="nav-link" onclick="showPage('jobs');toggleMobileMenu()">💼 Jobs</button>
    <button class="nav-link" onclick="showPage('register');toggleMobileMenu()">📝 Register</button>
    <button class="nav-link" onclick="showPage('post');toggleMobileMenu()">📮 Post a Job</button>
    <button class="nav-link admin-only" onclick="showPage('admin');toggleMobileMenu()">⚙ Admin Panel</button>
  </div>
  <div style="display:flex;gap:6px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
    <button class="lang-btn active" onclick="setLang('en')" style="flex:1;padding:10px;border-radius:8px;border:1.5px solid var(--border);cursor:pointer;font-family:var(--font-main)">EN</button>
    <button class="lang-btn" onclick="setLang('hi')" style="flex:1;padding:10px;border-radius:8px;border:1.5px solid var(--border);cursor:pointer;font-family:var(--font-main)">हिन्दी</button>
    <button class="lang-btn" onclick="setLang('te')" style="flex:1;padding:10px;border-radius:8px;border:1.5px solid var(--border);cursor:pointer;font-family:var(--font-main)">తెలుగు</button>
  </div>
</div>

<!-- ══════════════════════════════════════════
     BOTTOM NAV (Mobile)
══════════════════════════════════════════ -->
<nav id="bottomNav">
  <button class="bottom-nav-item active" onclick="showPage('home')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
    <span id="bn-home">Home</span>
  </button>
  <button class="bottom-nav-item" onclick="showPage('workers')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
    <span id="bn-workers">Workers</span>
  </button>
  <button class="bottom-nav-item bnav-post" onclick="showPage('post')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
    <span id="bn-post">Post</span>
  </button>
  <button class="bottom-nav-item" onclick="showPage('jobs')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/></svg>
    <span id="bn-jobs">Jobs</span>
  </button>
  <button class="bottom-nav-item" onclick="showPage('register')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
    <span id="bn-register">Join</span>
  </button>
</nav>

<!-- ══════════════════════════════════════════
     MAIN CONTENT
══════════════════════════════════════════ -->
<div id="appContent">

  <!-- ── HOME PAGE ───────────────────────── -->
  <div id="page-home" class="page active">

    <!-- Hero -->
    <section class="hero">
      <div class="hero-bg"></div>
      <div class="container hero-content">
        <div class="hero-badge">🏆 India's Local Labour Marketplace</div>
        <h1 class="hero-title" id="h-hero-title">Find <span>Skilled Workers</span><br/>Near You, Instantly</h1>
        <p class="hero-sub" id="h-hero-sub">Connect with verified masons, electricians, plumbers and more. Trusted by homeowners and contractors across India.</p>
        <div class="hero-search">
          <input type="text" id="heroSearch" placeholder="Search skill, location..." oninput="heroSearchFilter()"/>
          <button onclick="heroSearchGo()" id="h-search-btn">🔍 Search Workers</button>
        </div>
        <div class="hero-stats">
          <div class="hero-stat">
            <div class="hero-stat-num" id="stat-workers">—</div>
            <div class="hero-stat-label" id="h-stat-workers">Skilled Workers</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat-num" id="stat-jobs">—</div>
            <div class="hero-stat-label" id="h-stat-jobs">Active Jobs</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat-num" id="stat-cities">—</div>
            <div class="hero-stat-label" id="h-stat-cities">Cities</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Categories -->
    <section class="section">
      <div class="container">
        <div class="section-header">
          <div class="section-eyebrow" id="h-cats-eyebrow">Popular Services</div>
          <h2 class="section-title" id="h-cats-title">What service do you need?</h2>
          <p class="section-sub" id="h-cats-sub">Browse skilled workers by trade category</p>
        </div>
        <div class="category-grid" id="categoryGrid">
          <!-- Filled by JS -->
        </div>
      </div>
    </section>

    <!-- How It Works -->
    <section class="section section-dark">
      <div class="container">
        <div class="section-header">
          <div class="section-eyebrow" style="color:#fdba74" id="h-how-eyebrow">Simple & Fast</div>
          <h2 class="section-title" id="h-how-title">How ShramikLink Works</h2>
          <p class="section-sub" id="h-how-sub">Get skilled workers at your doorstep in 3 simple steps</p>
        </div>
        <div class="how-grid">
          <div class="how-step">
            <div class="how-num">1</div>
            <h3 id="h-how1-title">Search & Filter</h3>
            <p id="h-how1-desc">Browse workers by skill, location, and experience. Use our powerful search to find exactly who you need.</p>
          </div>
          <div class="how-step">
            <div class="how-num">2</div>
            <h3 id="h-how2-title">Connect Directly</h3>
            <p id="h-how2-desc">Call or WhatsApp the worker directly. No middleman, no commission. Direct and transparent.</p>
          </div>
          <div class="how-step">
            <div class="how-num">3</div>
            <h3 id="h-how3-title">Get the Work Done</h3>
            <p id="h-how3-desc">Hire with confidence. Leave a review after work is complete to help future customers.</p>
          </div>
          <div class="how-step">
            <div class="how-num">4</div>
            <h3 id="h-how4-title">Post a Job</h3>
            <p id="h-how4-desc">Can't find someone? Post your job requirement with a photo. Workers will see and reach out.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Trust Section -->
    <section class="section">
      <div class="container">
        <div class="section-header">
          <div class="section-eyebrow" id="h-trust-eyebrow">Why ShramikLink</div>
          <h2 class="section-title" id="h-trust-title">Trusted by thousands across India</h2>
        </div>
        <div class="trust-grid">
          <div class="trust-item">
            <div class="trust-icon">✅</div>
            <h4 id="h-t1-title">Verified Workers</h4>
            <p id="h-t1-desc">All workers are manually listed with real phone numbers and skills verified.</p>
          </div>
          <div class="trust-item">
            <div class="trust-icon">💬</div>
            <h4 id="h-t2-title">Direct Communication</h4>
            <p id="h-t2-desc">Call or WhatsApp workers directly. No apps needed for workers to respond.</p>
          </div>
          <div class="trust-item">
            <div class="trust-icon">🌐</div>
            <h4 id="h-t3-title">Multilingual</h4>
            <p id="h-t3-desc">Available in English, Hindi, and Telugu. Workers can register in their own language.</p>
          </div>
          <div class="trust-item">
            <div class="trust-icon">🆓</div>
            <h4 id="h-t4-title">100% Free</h4>
            <p id="h-t4-desc">No registration fees, no commission. Completely free for workers and customers.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Band -->
    <section class="section section-brand">
      <div class="container text-center">
        <h2 style="font-size:clamp(1.5rem,3vw,2.2rem);font-weight:800;margin-bottom:14px" id="h-cta-title">Are you a skilled worker? Join Today!</h2>
        <p style="font-size:1rem;opacity:.85;margin-bottom:28px;max-width:480px;margin-left:auto;margin-right:auto" id="h-cta-sub">Register for free and get connected with customers and contractors near you.</p>
        <button class="btn btn-lg" style="background:#fff;color:var(--brand-primary);font-weight:800;" onclick="showPage('register')" id="h-cta-btn">Register as Worker →</button>
      </div>
    </section>

  </div><!-- /page-home -->

  <!-- ── WORKERS PAGE ─────────────────────── -->
  <div id="page-workers" class="page">
    <div class="container" style="padding-top:36px;padding-bottom:60px">
      <div style="margin-bottom:32px">
        <h1 style="font-size:1.8rem;font-weight:800;margin-bottom:8px" id="w-title">Find Skilled Workers</h1>
        <p style="color:var(--text-secondary)" id="w-sub">Browse and connect with workers in your area</p>
      </div>

      <div class="filters-bar">
        <input class="filter-input" type="text" id="filterSearch" placeholder="Search name, skill, location..." oninput="applyWorkerFilters()"/>
        <select class="filter-select" id="filterStatus" onchange="applyWorkerFilters()">
          <option value="">All Status</option>
          <option value="Available">✅ Available</option>
          <option value="Busy">🔴 Busy</option>
        </select>
        <select class="filter-select" id="filterSkill" onchange="applyWorkerFilters()">
          <option value="">All Skills</option>
        </select>
      </div>

      <div id="workersGrid" class="workers-grid">
        <div class="spinner"></div>
      </div>
    </div>
  </div>

  <!-- ── REGISTER PAGE ────────────────────── -->
  <div id="page-register" class="page">
    <div class="container" style="padding-top:40px;padding-bottom:80px">
      <div class="wizard-card">
        <div class="wizard-header">
          <h2 id="reg-wizard-title">Register as a Skilled Worker</h2>
          <p id="reg-wizard-sub">Join thousands of workers finding work near them</p>
          <div class="wizard-progress-bar">
            <div class="wizard-progress-fill" id="wizardProgressFill" style="width:25%"></div>
          </div>
          <div class="wizard-steps-indicator">
            <div class="ws-dot active" id="wsd0"></div>
            <div class="ws-dot" id="wsd1"></div>
            <div class="ws-dot" id="wsd2"></div>
            <div class="ws-dot" id="wsd3"></div>
          </div>
        </div>
        <div class="wizard-body">

          <!-- Step 1 -->
          <div class="wizard-step active" id="wstep0">
            <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:4px" id="ws1-title">Personal Information</h3>
            <p style="font-size:.85rem;color:var(--text-secondary);margin-bottom:24px" id="ws1-sub">Tell us your name and contact number</p>
            <div class="form-group">
              <label class="form-label" id="lbl-name">Full Name (can type in Hindi or Telugu)</label>
              <input class="form-input" type="text" id="reg_name" placeholder="e.g. రాజు కుమార్ or सुरेश यादव"/>
            </div>
            <div class="form-group">
              <label class="form-label" id="lbl-phone">Mobile Number (10 digits, unique)</label>
              <input class="form-input" type="tel" id="reg_phone" maxlength="10" placeholder="9876543210"/>
            </div>
            <div class="form-group">
              <label class="form-label" id="lbl-location">City / Area</label>
              <input class="form-input" type="text" id="reg_location" placeholder="e.g. Hyderabad, Anantapur"/>
            </div>
          </div>

          <!-- Step 2 -->
          <div class="wizard-step" id="wstep1">
            <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:4px" id="ws2-title">Work Details</h3>
            <p style="font-size:.85rem;color:var(--text-secondary);margin-bottom:24px" id="ws2-sub">Tell us about your trade and experience</p>
            <div class="form-group">
              <label class="form-label" id="lbl-skill">Primary Skill / Trade</label>
              <input class="form-input" type="text" id="reg_skill" placeholder="e.g. Mason, Electrician, Plumber..."/>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" id="lbl-exp">Experience</label>
                <input class="form-input" type="text" id="reg_experience" placeholder="e.g. 5 years"/>
              </div>
              <div class="form-group">
                <label class="form-label" id="lbl-wage">Daily Wage (₹)</label>
                <input class="form-input" type="number" id="reg_wage" placeholder="e.g. 700"/>
              </div>
            </div>
          </div>

          <!-- Step 3: Review -->
          <div class="wizard-step" id="wstep2">
            <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:20px" id="ws3-title">Review Your Details</h3>
            <div id="regReviewCard" style="background:var(--bg-page);border-radius:var(--radius-md);padding:20px;font-size:.9rem;line-height:2">
            </div>
          </div>

          <!-- Step 4: Success -->
          <div class="wizard-step" id="wstep3" style="text-align:center;padding:20px 0">
            <div style="font-size:4rem;margin-bottom:16px">🎉</div>
            <h3 style="font-size:1.3rem;font-weight:800;margin-bottom:10px" id="ws4-title">Registration Successful!</h3>
            <p style="color:var(--text-secondary);margin-bottom:28px" id="ws4-sub">You are now listed on ShramikLink. Contractors and customers can find you.</p>
            <button class="btn btn-primary btn-full" onclick="showPage('workers')">View Workers Directory →</button>
          </div>

          <div class="wizard-nav" id="wizardNav">
            <button class="btn btn-outline" id="wizardBackBtn" onclick="wizardBack()" style="display:none">← Back</button>
            <button class="btn btn-primary" id="wizardNextBtn" onclick="wizardNext()">Next Step →</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── POST JOB PAGE ─────────────────────── -->
  <div id="page-post" class="page">
    <div class="container" style="padding-top:40px;padding-bottom:80px">
      <div class="post-card">
        <div style="margin-bottom:28px">
          <h1 style="font-size:1.6rem;font-weight:800;margin-bottom:6px" id="post-title">Post a Job / Work Requirement</h1>
          <p style="color:var(--text-secondary)" id="post-sub">Describe what you need — workers and contractors will reach out</p>
        </div>

        <div class="form-group">
          <label class="form-label" id="lbl-cname">Your Name (Contractor / Customer)</label>
          <input class="form-input" type="text" id="post_cname" placeholder="e.g. రాహుల్ రెడ్డి or Rahul Singh"/>
        </div>
        <div class="form-group">
          <label class="form-label" id="lbl-cphone">Your Mobile Number</label>
          <input class="form-input" type="tel" id="post_cphone" maxlength="10" placeholder="9876543210"/>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label" id="lbl-jloc">Work Location</label>
            <input class="form-input" type="text" id="post_location" placeholder="e.g. Hyderabad"/>
          </div>
          <div class="form-group">
            <label class="form-label" id="lbl-wtype">Type of Work</label>
            <input class="form-input" type="text" id="post_work_type" placeholder="e.g. Construction"/>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label" id="lbl-wneeded">Workers Needed</label>
            <input class="form-input" type="number" id="post_workers_needed" placeholder="e.g. 5" min="1"/>
          </div>
          <div class="form-group">
            <label class="form-label" id="lbl-jwage">Wage Offered (₹/day)</label>
            <input class="form-input" type="number" id="post_wage" placeholder="e.g. 700"/>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label" id="lbl-req">Requirements / Description</label>
          <textarea class="form-input" id="post_requirements" rows="3" placeholder="Describe the work, skills needed, duration..."></textarea>
        </div>

        <!-- Photo Upload -->
        <label class="form-label" id="lbl-photo">Upload Work Photo (Optional)</label>
        <div class="photo-upload-zone" id="photoUploadZone" onclick="document.getElementById('photoFileInput').click()">
          <div class="upload-icon">📷</div>
          <div class="upload-text" id="upload-text-hint">Click to upload a photo of the work site or problem</div>
          <img id="photoPreview" src="" alt="Preview"/>
        </div>
        <input type="file" id="photoFileInput" accept="image/*" style="display:none" onchange="handlePhotoUpload(this)"/>

        <button class="btn btn-primary btn-full btn-lg" onclick="submitJob()" id="post-submit-btn">📮 Post Job Now</button>
      </div>
    </div>
  </div>

  <!-- ── JOBS PAGE ──────────────────────────── -->
  <div id="page-jobs" class="page">
    <div class="container" style="padding-top:36px;padding-bottom:80px">
      <div style="margin-bottom:32px">
        <h1 style="font-size:1.8rem;font-weight:800;margin-bottom:8px" id="jobs-title">Job Board</h1>
        <p style="color:var(--text-secondary)" id="jobs-sub">Open job postings from contractors and homeowners</p>
      </div>
      <div id="jobsGrid" class="jobs-grid">
        <div class="spinner"></div>
      </div>
    </div>
  </div>

  <!-- ── ADMIN PAGE ─────────────────────────── -->
  <div id="page-admin" class="page admin-only" style="display:none">
    <div class="container" style="padding-top:36px;padding-bottom:80px">
      <h1 style="font-size:1.8rem;font-weight:800;margin-bottom:28px">⚙ Admin Panel</h1>

      <div class="admin-section-card">
        <h3>📊 Platform Statistics</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px" id="adminStatsGrid">
          <div class="spinner"></div>
        </div>
      </div>

      <div class="admin-section-card">
        <h3>💾 Database Backup & Restore</h3>
        <p style="font-size:.875rem;color:var(--text-secondary);margin-bottom:16px">Download a full backup of all data or restore from a previous backup file.</p>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <button class="btn btn-primary" onclick="downloadBackup()">⬇ Download Backup</button>
          <label class="btn btn-outline" style="cursor:pointer">
            ⬆ Restore from Backup
            <input type="file" id="restoreFile" accept=".json" style="display:none" onchange="restoreBackup(this)"/>
          </label>
        </div>
      </div>

      <div class="admin-section-card">
        <h3>👷 All Workers (Admin View)</h3>
        <div id="adminWorkersTable" style="overflow-x:auto"></div>
      </div>

      <div class="admin-section-card">
        <h3>💼 All Jobs (Admin View)</h3>
        <div id="adminJobsTable" style="overflow-x:auto"></div>
      </div>
    </div>
  </div>

</div><!-- /appContent -->

<!-- ══════════════════════════════════════════
     FOOTER
══════════════════════════════════════════ -->
<footer>
  <div class="container">
    <div class="footer-grid">
      <div>
        <div class="footer-brand-name">Shramik<span>Link</span></div>
        <p class="footer-desc">India's trusted platform connecting skilled workers with customers and contractors. Empowering local labour, one connection at a time.</p>
        <div style="margin-top:16px;display:flex;gap:12px;align-items:center">
          <a href="mailto:support.shramiklink@gmail.com" style="color:var(--brand-primary);font-size:.83rem;text-decoration:none">✉ support.shramiklink@gmail.com</a>
        </div>
      </div>
      <div class="footer-col">
        <h4>Platform</h4>
        <ul>
          <li><a href="#" onclick="showPage('workers')">Find Workers</a></li>
          <li><a href="#" onclick="showPage('jobs')">Job Board</a></li>
          <li><a href="#" onclick="showPage('register')">Register as Worker</a></li>
          <li><a href="#" onclick="showPage('post')">Post a Job</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Trades</h4>
        <ul>
          <li><a href="#">Mason / Mistri</a></li>
          <li><a href="#">Electrician</a></li>
          <li><a href="#">Plumber</a></li>
          <li><a href="#">Carpenter</a></li>
          <li><a href="#">Painter</a></li>
          <li><a href="#">Welder</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Support</h4>
        <ul>
          <li><a href="mailto:support.shramiklink@gmail.com">Contact Us</a></li>
          <li><a href="https://wa.me/91XXXXXXXXXX" target="_blank">WhatsApp Support</a></li>
          <li><a href="#">Privacy Policy</a></li>
          <li><a href="#">Terms of Use</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <span>© 2025 ShramikLink. All rights reserved. Made with ❤ for Indian workers.</span>
      <span>EN | हिन्दी | తెలుగు</span>
    </div>
  </div>
</footer>

<!-- Floating WhatsApp Support Button -->
<a href="https://wa.me/918886000000?text=Hello%20ShramikLink%20support%2C%20I%20need%20help." target="_blank" class="float-wa" title="WhatsApp Support">💬</a>

<!-- ══════════════════════════════════════════
     JAVASCRIPT
══════════════════════════════════════════ -->
<script>
// ─── STATE ──────────────────────────────
let currentLang = 'en';
let allWorkers = [];
let allJobs = [];
let activeHireWorkerId = null;
let activeReviewWorkerId = null;
let currentWizardStep = 0;
let regPhotoData = '';
let postPhotoData = '';

const ADMIN_PIN = '9999';
const CATEGORIES = [
  { icon: '🧱', name: { en: 'Mason', hi: 'राजमिस्त्री', te: 'మేసన్' }, skill: 'Mason' },
  { icon: '⚡', name: { en: 'Electrician', hi: 'बिजली मिस्त्री', te: 'ఎలెక్ట్రీషియన్' }, skill: 'Electrician' },
  { icon: '🔧', name: { en: 'Plumber', hi: 'पाइप मिस्त्री', te: 'ప్లంబర్' }, skill: 'Plumber' },
  { icon: '🪵', name: { en: 'Carpenter', hi: 'बढ़ई', te: 'కార్పెంటర్' }, skill: 'Carpenter' },
  { icon: '🎨', name: { en: 'Painter', hi: 'पेंटर', te: 'పెయింటర్' }, skill: 'Painter' },
  { icon: '🔩', name: { en: 'Welder', hi: 'वेल्डर', te: 'వెల్డర్' }, skill: 'Welder' },
  { icon: '🏗️', name: { en: 'Labour', hi: 'मजदूर', te: 'కూలీ' }, skill: '' },
  { icon: '🌿', name: { en: 'Gardener', hi: 'माली', te: 'తోటమాలి' }, skill: 'Gardener' },
];

// ─── i18n ────────────────────────────────
const i18n = {
  en: {
    'h-hero-title': 'Find <span style="color:var(--brand-primary)">Skilled Workers</span><br/>Near You, Instantly',
    'h-hero-sub': 'Connect with verified masons, electricians, plumbers and more. Trusted by homeowners and contractors across India.',
    'h-search-btn': '🔍 Search Workers',
    'h-stat-workers': 'Skilled Workers',
    'h-stat-jobs': 'Active Jobs',
    'h-stat-cities': 'Cities',
    'h-cats-eyebrow': 'Popular Services',
    'h-cats-title': 'What service do you need?',
    'h-cats-sub': 'Browse skilled workers by trade category',
    'h-how-eyebrow': 'Simple & Fast',
    'h-how-title': 'How ShramikLink Works',
    'h-how-sub': 'Get skilled workers at your doorstep in 3 simple steps',
    'h-how1-title': 'Search & Filter',
    'h-how1-desc': 'Browse workers by skill, location, and experience. Use our powerful search to find exactly who you need.',
    'h-how2-title': 'Connect Directly',
    'h-how2-desc': 'Call or WhatsApp the worker directly. No middleman, no commission. Direct and transparent.',
    'h-how3-title': 'Get the Work Done',
    'h-how3-desc': 'Hire with confidence. Leave a review after work is complete to help future customers.',
    'h-how4-title': 'Post a Job',
    'h-how4-desc': "Can't find someone? Post your job requirement with a photo. Workers will see and reach out.",
    'h-trust-eyebrow': 'Why ShramikLink',
    'h-trust-title': 'Trusted by thousands across India',
    'h-t1-title': 'Verified Workers',
    'h-t1-desc': 'All workers are manually listed with real phone numbers and skills verified.',
    'h-t2-title': 'Direct Communication',
    'h-t2-desc': 'Call or WhatsApp workers directly. No apps needed for workers to respond.',
    'h-t3-title': 'Multilingual',
    'h-t3-desc': 'Available in English, Hindi, and Telugu. Workers can register in their own language.',
    'h-t4-title': '100% Free',
    'h-t4-desc': 'No registration fees, no commission. Completely free for workers and customers.',
    'h-cta-title': 'Are you a skilled worker? Join Today!',
    'h-cta-sub': 'Register for free and get connected with customers and contractors near you.',
    'h-cta-btn': 'Register as Worker →',
    'w-title': 'Find Skilled Workers',
    'w-sub': 'Browse and connect with workers in your area',
    'jobs-title': 'Job Board',
    'jobs-sub': 'Open job postings from contractors and homeowners',
    'post-title': 'Post a Job / Work Requirement',
    'post-sub': 'Describe what you need — workers and contractors will reach out',
    'lbl-cname': 'Your Name (Contractor / Customer)',
    'lbl-cphone': 'Your Mobile Number',
    'lbl-jloc': 'Work Location',
    'lbl-wtype': 'Type of Work',
    'lbl-wneeded': 'Workers Needed',
    'lbl-jwage': 'Wage Offered (₹/day)',
    'lbl-req': 'Requirements / Description',
    'lbl-photo': 'Upload Work Photo (Optional)',
    'upload-text-hint': 'Click to upload a photo of the work site or problem',
    'post-submit-btn': '📮 Post Job Now',
    'reg-wizard-title': 'Register as a Skilled Worker',
    'reg-wizard-sub': 'Join thousands of workers finding work near them',
    'ws1-title': 'Personal Information',
    'ws1-sub': 'Tell us your name and contact number',
    'lbl-name': 'Full Name (can type in Hindi or Telugu)',
    'lbl-phone': 'Mobile Number (10 digits, unique)',
    'lbl-location': 'City / Area',
    'ws2-title': 'Work Details',
    'ws2-sub': 'Tell us about your trade and experience',
    'lbl-skill': 'Primary Skill / Trade',
    'lbl-exp': 'Experience',
    'lbl-wage': 'Daily Wage (₹)',
    'ws3-title': 'Review Your Details',
    'ws4-title': 'Registration Successful!',
    'ws4-sub': 'You are now listed on ShramikLink. Contractors and customers can find you.',
    'bn-home': 'Home', 'bn-workers': 'Workers', 'bn-post': 'Post', 'bn-jobs': 'Jobs', 'bn-register': 'Join',
    'nav-join-btn': 'Join as Worker',
  },
  hi: {
    'h-hero-title': '<span style="color:var(--brand-primary)">कुशल मजदूर</span> खोजें<br/>अपने पास, तुरंत',
    'h-hero-sub': 'सत्यापित राजमिस्त्री, बिजली मिस्त्री, पाइप मिस्त्री और अधिक के साथ जुड़ें।',
    'h-search-btn': '🔍 मजदूर खोजें',
    'h-stat-workers': 'कुशल मजदूर',
    'h-stat-jobs': 'सक्रिय काम',
    'h-stat-cities': 'शहर',
    'h-cats-eyebrow': 'लोकप्रिय सेवाएं',
    'h-cats-title': 'आपको कौनसी सेवा चाहिए?',
    'h-cats-sub': 'व्यापार श्रेणी के अनुसार कुशल मजदूर देखें',
    'h-how-eyebrow': 'सरल और तेज़',
    'h-how-title': 'श्रमिक लिंक कैसे काम करता है',
    'h-how-sub': '3 आसान चरणों में अपने दरवाजे पर कुशल मजदूर पाएं',
    'h-how1-title': 'खोजें और फ़िल्टर करें',
    'h-how1-desc': 'कौशल, स्थान और अनुभव के अनुसार मजदूर देखें।',
    'h-how2-title': 'सीधे जुड़ें',
    'h-how2-desc': 'मजदूर को सीधे कॉल या WhatsApp करें। कोई बिचौलिया नहीं।',
    'h-how3-title': 'काम पूरा कराएं',
    'h-how3-desc': 'आत्मविश्वास के साथ काम कराएं। काम पूरा होने के बाद समीक्षा छोड़ें।',
    'h-how4-title': 'काम पोस्ट करें',
    'h-how4-desc': 'नहीं मिला? काम की जरूरत फोटो के साथ पोस्ट करें।',
    'h-trust-eyebrow': 'श्रमिक लिंक क्यों',
    'h-trust-title': 'भारत भर में हजारों लोगों का भरोसा',
    'h-t1-title': 'सत्यापित मजदूर',
    'h-t1-desc': 'सभी मजदूर असली फोन नंबर और कौशल के साथ सूचीबद्ध हैं।',
    'h-t2-title': 'सीधी बातचीत',
    'h-t2-desc': 'मजदूरों को सीधे कॉल या WhatsApp करें।',
    'h-t3-title': 'बहुभाषी',
    'h-t3-desc': 'अंग्रेजी, हिंदी और तेलुगु में उपलब्ध।',
    'h-t4-title': '100% मुफ्त',
    'h-t4-desc': 'कोई पंजीकरण शुल्क नहीं, कोई कमीशन नहीं।',
    'h-cta-title': 'क्या आप एक कुशल मजदूर हैं? आज जुड़ें!',
    'h-cta-sub': 'मुफ्त में पंजीकरण करें और अपने पास के ग्राहकों से जुड़ें।',
    'h-cta-btn': 'मजदूर के रूप में पंजीकरण करें →',
    'w-title': 'कुशल मजदूर खोजें',
    'w-sub': 'अपने क्षेत्र में मजदूरों को देखें और जुड़ें',
    'jobs-title': 'काम बोर्ड',
    'jobs-sub': 'ठेकेदारों और गृहस्वामियों से खुले काम के पोस्ट',
    'post-title': 'काम पोस्ट करें',
    'post-sub': 'बताएं आपको क्या चाहिए — मजदूर और ठेकेदार आपसे संपर्क करेंगे',
    'lbl-cname': 'आपका नाम (ठेकेदार / ग्राहक)',
    'lbl-cphone': 'आपका मोबाइल नंबर',
    'lbl-jloc': 'काम का स्थान',
    'lbl-wtype': 'काम का प्रकार',
    'lbl-wneeded': 'आवश्यक मजदूर',
    'lbl-jwage': 'दैनिक मजदूरी (₹)',
    'lbl-req': 'आवश्यकताएं / विवरण',
    'lbl-photo': 'काम की फोटो अपलोड करें (वैकल्पिक)',
    'upload-text-hint': 'काम की जगह या समस्या की फोटो अपलोड करें',
    'post-submit-btn': '📮 काम पोस्ट करें',
    'reg-wizard-title': 'कुशल मजदूर के रूप में पंजीकरण करें',
    'reg-wizard-sub': 'हजारों मजदूरों के साथ जुड़ें जो पास में काम पाते हैं',
    'ws1-title': 'व्यक्तिगत जानकारी',
    'ws1-sub': 'अपना नाम और संपर्क नंबर बताएं',
    'lbl-name': 'पूरा नाम (हिंदी या तेलुगु में लिख सकते हैं)',
    'lbl-phone': 'मोबाइल नंबर (10 अंक, अद्वितीय)',
    'lbl-location': 'शहर / क्षेत्र',
    'ws2-title': 'काम का विवरण',
    'ws2-sub': 'अपने व्यापार और अनुभव के बारे में बताएं',
    'lbl-skill': 'मुख्य कौशल / व्यापार',
    'lbl-exp': 'अनुभव',
    'lbl-wage': 'दैनिक मजदूरी (₹)',
    'ws3-title': 'अपनी जानकारी जांचें',
    'ws4-title': 'पंजीकरण सफल!',
    'ws4-sub': 'आप अब श्रमिक लिंक पर सूचीबद्ध हैं।',
    'bn-home': 'होम', 'bn-workers': 'मजदूर', 'bn-post': 'पोस्ट', 'bn-jobs': 'काम', 'bn-register': 'जुड़ें',
    'nav-join-btn': 'मजदूर बनें',
  },
  te: {
    'h-hero-title': '<span style="color:var(--brand-primary)">నైపుణ్యమైన కూలీలు</span><br/>మీ దగ్గర, వెంటనే',
    'h-hero-sub': 'నిర్ధారిత మేసన్లు, ఎలెక్ట్రీషియన్లు, ప్లంబర్లు మరియు మరిన్నింటితో కనెక్ట్ అవ్వండి.',
    'h-search-btn': '🔍 కూలీలను వెతకండి',
    'h-stat-workers': 'నైపుణ్యమైన కూలీలు',
    'h-stat-jobs': 'చురుకైన పనులు',
    'h-stat-cities': 'నగరాలు',
    'h-cats-eyebrow': 'ప్రముఖ సేవలు',
    'h-cats-title': 'మీకు ఏ సేవ కావాలి?',
    'h-cats-sub': 'వ్యాపార వర్గం ద్వారా నైపుణ్యమైన కూలీలను చూడండి',
    'h-how-eyebrow': 'సులభం మరియు వేగంగా',
    'h-how-title': 'శ్రమిక్ లింక్ ఎలా పని చేస్తుంది',
    'h-how-sub': '3 సులభమైన దశల్లో మీ తలుపు దగ్గర నైపుణ్యమైన కూలీలను పొందండి',
    'h-how1-title': 'వెతకండి & ఫిల్టర్ చేయండి',
    'h-how1-desc': 'నైపుణ్యం, స్థానం మరియు అనుభవం ప్రకారం కూలీలను చూడండి.',
    'h-how2-title': 'నేరుగా కనెక్ట్ అవ్వండి',
    'h-how2-desc': 'కూలీకి నేరుగా కాల్ చేయండి లేదా WhatsApp చేయండి.',
    'h-how3-title': 'పని పూర్తి చేయండి',
    'h-how3-desc': 'నమ్మకంతో పని చేయించుకోండి. పని పూర్తయిన తర్వాత సమీక్ష రాయండి.',
    'h-how4-title': 'పని పోస్ట్ చేయండి',
    'h-how4-desc': 'కనుగొనలేదా? ఫోటోతో మీ పని అవసరాన్ని పోస్ట్ చేయండి.',
    'h-trust-eyebrow': 'శ్రమిక్ లింక్ ఎందుకు',
    'h-trust-title': 'భారతదేశం అంతటా వేలాది మంది నమ్మిన వేదిక',
    'h-t1-title': 'నిర్ధారిత కూలీలు',
    'h-t1-desc': 'అన్ని కూలీలు నిజమైన ఫోన్ నంబర్లు మరియు నైపుణ్యాలతో జాబితా చేయబడ్డారు.',
    'h-t2-title': 'నేరుగా సంభాషించండి',
    'h-t2-desc': 'కూలీలకు నేరుగా కాల్ చేయండి లేదా WhatsApp చేయండి.',
    'h-t3-title': 'బహుభాషీయ',
    'h-t3-desc': 'ఇంగ్లీష్, హిందీ మరియు తెలుగులో అందుబాటులో ఉంది.',
    'h-t4-title': '100% ఉచితం',
    'h-t4-desc': 'నమోదు రుసుము లేదు, కమీషన్ లేదు.',
    'h-cta-title': 'మీరు నైపుణ్యమైన కూలీయా? ఈరోజే చేరండి!',
    'h-cta-sub': 'ఉచితంగా నమోదు చేసుకోండి మరియు మీ దగ్గరి కస్టమర్లతో కనెక్ట్ అవ్వండి.',
    'h-cta-btn': 'కూలీగా నమోదు చేసుకోండి →',
    'w-title': 'నైపుణ్యమైన కూలీలను కనుగొనండి',
    'w-sub': 'మీ ప్రాంతంలో కూలీలను చూడండి మరియు కనెక్ట్ అవ్వండి',
    'jobs-title': 'జాబ్ బోర్డ్',
    'jobs-sub': 'కాంట్రాక్టర్లు మరియు గృహ యజమానుల నుండి తెరిచిన పని పోస్టులు',
    'post-title': 'పని పోస్ట్ చేయండి',
    'post-sub': 'మీకు ఏమి కావాలో వివరించండి — కూలీలు మరియు కాంట్రాక్టర్లు సంప్రదిస్తారు',
    'lbl-cname': 'మీ పేరు (కాంట్రాక్టర్ / కస్టమర్)',
    'lbl-cphone': 'మీ మొబైల్ నంబర్',
    'lbl-jloc': 'పని స్థానం',
    'lbl-wtype': 'పని రకం',
    'lbl-wneeded': 'అవసరమైన కూలీలు',
    'lbl-jwage': 'రోజు వేతనం (₹)',
    'lbl-req': 'అవసరాలు / వివరణ',
    'lbl-photo': 'పని ఫోటో అప్‌లోడ్ చేయండి (ఐచ్ఛికం)',
    'upload-text-hint': 'పని స్థలం లేదా సమస్య ఫోటో అప్‌లోడ్ చేయండి',
    'post-submit-btn': '📮 పని పోస్ట్ చేయండి',
    'reg-wizard-title': 'నైపుణ్యమైన కూలీగా నమోదు చేసుకోండి',
    'reg-wizard-sub': 'దగ్గర పని కనుగొంటున్న వేలాది కూలీలతో చేరండి',
    'ws1-title': 'వ్యక్తిగత సమాచారం',
    'ws1-sub': 'మీ పేరు మరియు సంప్రదింపు నంబర్ చెప్పండి',
    'lbl-name': 'పూర్తి పేరు (తెలుగు లేదా హిందీలో టైప్ చేయవచ్చు)',
    'lbl-phone': 'మొబైల్ నంబర్ (10 అంకెలు, ప్రత్యేకమైనది)',
    'lbl-location': 'నగరం / ప్రాంతం',
    'ws2-title': 'పని వివరాలు',
    'ws2-sub': 'మీ వ్యాపారం మరియు అనుభవం గురించి చెప్పండి',
    'lbl-skill': 'ప్రాథమిక నైపుణ్యం / వ్యాపారం',
    'lbl-exp': 'అనుభవం',
    'lbl-wage': 'రోజు వేతనం (₹)',
    'ws3-title': 'మీ వివరాలు తనిఖీ చేయండి',
    'ws4-title': 'నమోదు విజయవంతమైంది!',
    'ws4-sub': 'మీరు ఇప్పుడు శ్రమిక్ లింక్‌లో జాబితా చేయబడ్డారు.',
    'bn-home': 'హోమ్', 'bn-workers': 'కూలీలు', 'bn-post': 'పోస్ట్', 'bn-jobs': 'పనులు', 'bn-register': 'చేరు',
    'nav-join-btn': 'కూలీగా చేరండి',
  }
};

// ─── ENTRY GATE ──────────────────────────
let pinBuffer = '';

function enterAsUser() {
  const overlay = document.getElementById('roleGateOverlay');
  overlay.style.opacity = '0';
  overlay.style.transition = 'opacity 0.5s ease';
  setTimeout(() => {
    overlay.style.display = 'none';
  }, 500);
  loadInitialData();
}

function showAdminPinEntry() {
  document.getElementById('gateRoleSection').style.display = 'none';
  document.getElementById('adminPinSection').classList.add('visible');
  pinBuffer = '';
  updatePinDots();
}

function showRoleSection() {
  document.getElementById('gateRoleSection').style.display = 'block';
  document.getElementById('adminPinSection').classList.remove('visible');
  pinBuffer = '';
  updatePinDots();
  document.getElementById('pinError').textContent = '';
}

function pinPress(digit) {
  if (pinBuffer.length >= 4) return;
  pinBuffer += digit;
  updatePinDots();
  if (pinBuffer.length === 4) {
    setTimeout(checkPin, 200);
  }
}

function pinBackspace() {
  pinBuffer = pinBuffer.slice(0, -1);
  updatePinDots();
}

function pinClear() {
  pinBuffer = '';
  updatePinDots();
}

function updatePinDots() {
  for (let i = 0; i < 4; i++) {
    document.getElementById('dot' + i).classList.toggle('filled', i < pinBuffer.length);
  }
}

function checkPin() {
  if (pinBuffer === ADMIN_PIN) {
    document.body.classList.add('is-admin');
    const overlay = document.getElementById('roleGateOverlay');
    overlay.style.opacity = '0';
    overlay.style.transition = 'opacity 0.5s ease';
    setTimeout(() => { overlay.style.display = 'none'; }, 500);
    loadInitialData();
    showPage('admin');
    showToast('Admin access granted!', 'success');
  } else {
    document.getElementById('pinError').textContent = '❌ Wrong PIN. Please try again.';
    pinBuffer = '';
    updatePinDots();
    // shake animation
    const keypad = document.getElementById('pinKeypad');
    keypad.style.animation = 'none';
    keypad.offsetHeight;
    keypad.style.animation = 'shake .4s ease';
  }
}

// ─── LANGUAGE ────────────────────────────
function setLang(lang) {
  currentLang = lang;
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('lb-' + lang).classList.add('active');
  const t = i18n[lang];
  for (const [id, val] of Object.entries(t)) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = val;
  }
  // Update category grid labels
  renderCategories();
}

// ─── PAGE NAVIGATION ─────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const page = document.getElementById('page-' + name);
  if (page) page.classList.add('active');

  // Bottom nav active
  document.querySelectorAll('.bottom-nav-item').forEach(b => b.classList.remove('active'));

  // Top nav active
  document.querySelectorAll('.nav-link').forEach(b => b.classList.remove('active'));
  const nl = document.getElementById('nl-' + name);
  if (nl) nl.classList.add('active');

  // Load data as needed
  if (name === 'workers') loadWorkers();
  if (name === 'jobs') loadJobs();
  if (name === 'admin' && document.body.classList.contains('is-admin')) loadAdminData();

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function toggleMobileMenu() {
  const m = document.getElementById('mobileMenu');
  m.style.display = m.style.display === 'none' ? 'block' : 'none';
}

// ─── LOAD STATS ──────────────────────────
async function loadStats() {
  try {
    const [wRes, jRes] = await Promise.all([
      fetch('/api/labours'),
      fetch('/api/jobs')
    ]);
    const workers = await wRes.json();
    const jobs = await jRes.json();
    const cities = new Set(workers.map(w => w.location?.trim()).filter(Boolean)).size;
    document.getElementById('stat-workers').textContent = workers.length + '+';
    document.getElementById('stat-jobs').textContent = jobs.length + '+';
    document.getElementById('stat-cities').textContent = cities + '+';
  } catch(e) {
    console.warn('Stats error', e);
  }
}

// ─── CATEGORIES ──────────────────────────
function renderCategories() {
  const grid = document.getElementById('categoryGrid');
  if (!grid) return;
  grid.innerHTML = CATEGORIES.map(cat => `
    <div class="cat-card" onclick="filterByCategory('${cat.skill}')">
      <div class="cat-icon">${cat.icon}</div>
      <div class="cat-name">${cat.name[currentLang] || cat.name.en}</div>
      <div class="cat-count">${countWorkersBySkill(cat.skill)} workers</div>
    </div>
  `).join('');
}

function countWorkersBySkill(skill) {
  if (!skill) return allWorkers.length;
  return allWorkers.filter(w => w.skill && w.skill.toLowerCase().includes(skill.toLowerCase())).length;
}

function filterByCategory(skill) {
  showPage('workers');
  setTimeout(() => {
    const f = document.getElementById('filterSearch');
    if (f) { f.value = skill; applyWorkerFilters(); }
  }, 100);
}

function heroSearchGo() {
  const q = document.getElementById('heroSearch').value.trim();
  showPage('workers');
  setTimeout(() => {
    const f = document.getElementById('filterSearch');
    if (f) { f.value = q; applyWorkerFilters(); }
  }, 100);
}

function heroSearchFilter() {
  // live filter not needed on hero, just allow enter key
}

// ─── WORKERS ─────────────────────────────
async function loadWorkers() {
  const grid = document.getElementById('workersGrid');
  grid.innerHTML = '<div class="spinner"></div>';
  try {
    const res = await fetch('/api/labours');
    allWorkers = await res.json();
    populateSkillFilter();
    renderCategories();
    applyWorkerFilters();
  } catch(e) {
    grid.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Could not load workers. Please refresh.</p></div>';
  }
}

function populateSkillFilter() {
  const sel = document.getElementById('filterSkill');
  if (!sel) return;
  const skills = [...new Set(allWorkers.map(w => w.skill).filter(Boolean))].sort();
  const current = sel.value;
  sel.innerHTML = '<option value="">All Skills</option>' + skills.map(s => `<option value="${s}"${s===current?' selected':''}>${s}</option>`).join('');
}

function applyWorkerFilters() {
  const q = (document.getElementById('filterSearch')?.value || '').toLowerCase();
  const status = document.getElementById('filterStatus')?.value || '';
  const skill = document.getElementById('filterSkill')?.value || '';
  const filtered = allWorkers.filter(w => {
    const matchQ = !q || [w.name, w.skill, w.location, w.phone].some(f => f && f.toLowerCase().includes(q));
    const matchStatus = !status || w.status === status;
    const matchSkill = !skill || w.skill === skill;
    return matchQ && matchStatus && matchSkill;
  });
  renderWorkers(filtered);
}

function cleanPhone(phone) {
  let p = (phone || '').replace(/\D/g, '');
  if (p.length === 10) p = '91' + p;
  return p;
}

function renderWorkers(list) {
  const grid = document.getElementById('workersGrid');
  if (!list.length) {
    grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🔍</div><p>No workers found matching your search.</p></div>';
    return;
  }
  grid.innerHTML = list.map(w => {
    const busy = w.status === 'Busy';
    const busyTag = busy && w.assigned_contractor ? `
      <div class="busy-tag">🔴 Currently working with: <strong>${w.assigned_contractor}</strong></div>
    ` : '';
    const availableBadge = busy
      ? `<span class="worker-status-badge status-busy">Busy</span>`
      : `<span class="worker-status-badge status-available">Available</span>`;
    const waPhone = cleanPhone(w.phone);
    const waMsg = encodeURIComponent(`Hello ${w.name}, I found you on ShramikLink. Are you available for work?`);
    const adminDeleteBtn = `<button class="btn btn-danger btn-sm admin-only" onclick="deleteWorker(${w.id})" style="display:none">🗑 Delete</button>`;
    const assignBtn = busy
      ? `<button class="btn btn-success btn-sm admin-only" style="display:none" onclick="markAvailable(${w.id})">🟢 Mark Available</button>`
      : `<button class="btn btn-outline btn-sm" onclick="openHireModal(${w.id})">📋 Assign</button>`;
    return `
      <div class="worker-card">
        ${availableBadge}
        <div class="worker-card-top">
          <div class="worker-avatar">👷</div>
          <div class="worker-info">
            <div class="worker-name">${w.name}</div>
            <div class="worker-skill">${w.skill || 'General'}</div>
            <div class="worker-loc">📍 ${w.location || 'Unknown'}</div>
          </div>
        </div>
        ${busyTag}
        <div class="worker-meta">
          <div class="meta-item">
            <div class="meta-label">Experience</div>
            <div class="meta-value">${w.experience || '—'}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Daily Wage</div>
            <div class="meta-value">₹${w.daily_wage || '—'}/day</div>
          </div>
        </div>
        <div class="worker-actions">
          <a href="tel:${w.phone}" class="btn btn-primary">📞 Call</a>
          <a href="https://wa.me/${waPhone}?text=${waMsg}" target="_blank" class="btn btn-wa">💬 WhatsApp</a>
          ${assignBtn}
          ${adminDeleteBtn}
        </div>
        <div style="margin-top:10px">
          <button class="btn btn-outline btn-sm btn-full" onclick="openReviewModal(${w.id}, '${w.name.replace(/'/g,"\\'")}')">⭐ Rate Worker</button>
        </div>
      </div>
    `;
  }).join('');
  // Re-apply admin visibility
  if (document.body.classList.contains('is-admin')) {
    document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'inline-flex');
  }
}

// ─── HIRE / ASSIGN ───────────────────────
function openHireModal(workerId) {
  activeHireWorkerId = workerId;
  document.getElementById('contractorNameInput').value = '';
  document.getElementById('hireModalBackdrop').classList.remove('hidden');
}
function closeHireModal() {
  document.getElementById('hireModalBackdrop').classList.add('hidden');
  activeHireWorkerId = null;
}
async function confirmAssign() {
  const name = document.getElementById('contractorNameInput').value.trim();
  if (!name) { showToast('Please enter contractor name', 'error'); return; }
  try {
    const res = await fetch(`/api/labours/${activeHireWorkerId}/assign`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contractor_name: name, status: 'Busy' })
    });
    if (res.ok) {
      closeHireModal();
      showToast('Worker assigned to ' + name, 'success');
      loadWorkers();
    } else {
      showToast('Failed to assign worker', 'error');
    }
  } catch(e) {
    showToast('Network error', 'error');
  }
}
async function markAvailable(workerId) {
  try {
    const res = await fetch(`/api/labours/${workerId}/assign`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contractor_name: '', status: 'Available' })
    });
    if (res.ok) { showToast('Worker marked as Available', 'success'); loadWorkers(); }
  } catch(e) { showToast('Error', 'error'); }
}

// ─── DELETE WORKER (Admin only) ──────────
async function deleteWorker(id) {
  if (!confirm('Delete this worker permanently?')) return;
  try {
    const res = await fetch(`/api/labours/${id}`, {
      method: 'DELETE',
      headers: { 'X-Admin-PIN': ADMIN_PIN }
    });
    if (res.ok) { showToast('Worker deleted', 'success'); loadWorkers(); if (document.body.classList.contains('is-admin')) loadAdminData(); }
    else showToast('Delete failed', 'error');
  } catch(e) { showToast('Network error', 'error'); }
}

// ─── REVIEWS ─────────────────────────────
function openReviewModal(workerId, workerName) {
  activeReviewWorkerId = workerId;
  document.getElementById('reviewerName').value = '';
  document.getElementById('reviewRating').value = '5';
  document.getElementById('reviewComment').value = '';
  document.getElementById('reviewModalBackdrop').classList.remove('hidden');
}
function closeReviewModal() {
  document.getElementById('reviewModalBackdrop').classList.add('hidden');
  activeReviewWorkerId = null;
}
async function submitReview() {
  const name = document.getElementById('reviewerName').value.trim();
  const rating = parseInt(document.getElementById('reviewRating').value);
  const comment = document.getElementById('reviewComment').value.trim();
  if (!name) { showToast('Please enter your name', 'error'); return; }
  try {
    const res = await fetch(`/api/workers/${activeReviewWorkerId}/reviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer_name: name, rating, comment })
    });
    if (res.ok) {
      closeReviewModal();
      showToast('Review submitted! Thank you.', 'success');
    } else {
      showToast('Failed to submit review', 'error');
    }
  } catch(e) { showToast('Network error', 'error'); }
}

// ─── REGISTRATION WIZARD ─────────────────
function wizardNext() {
  if (!validateWizardStep(currentWizardStep)) return;
  if (currentWizardStep === 1) {
    fillReviewCard();
  }
  if (currentWizardStep === 2) {
    submitRegistration();
    return;
  }
  currentWizardStep++;
  updateWizardUI();
}

function wizardBack() {
  currentWizardStep = Math.max(0, currentWizardStep - 1);
  updateWizardUI();
}

function updateWizardUI() {
  document.querySelectorAll('.wizard-step').forEach((s, i) => s.classList.toggle('active', i === currentWizardStep));
  for (let i = 0; i < 4; i++) {
    document.getElementById('wsd' + i).classList.toggle('active', i <= currentWizardStep);
  }
  const pct = ((currentWizardStep + 1) / 4 * 100).toFixed(0);
  document.getElementById('wizardProgressFill').style.width = pct + '%';
  const backBtn = document.getElementById('wizardBackBtn');
  const nextBtn = document.getElementById('wizardNextBtn');
  const nav = document.getElementById('wizardNav');
  backBtn.style.display = currentWizardStep > 0 && currentWizardStep < 3 ? 'inline-flex' : 'none';
  if (currentWizardStep === 2) {
    nextBtn.textContent = '✅ Confirm & Register';
  } else if (currentWizardStep === 3) {
    nav.style.display = 'none';
  } else {
    nextBtn.textContent = 'Next Step →';
  }
}

function validateWizardStep(step) {
  if (step === 0) {
    const name = document.getElementById('reg_name').value.trim();
    const phone = document.getElementById('reg_phone').value.trim();
    const loc = document.getElementById('reg_location').value.trim();
    if (!name) { showToast('Please enter your name', 'error'); return false; }
    if (!/^\d{10}$/.test(phone)) { showToast('Please enter a valid 10-digit mobile number', 'error'); return false; }
    if (!loc) { showToast('Please enter your location', 'error'); return false; }
  }
  if (step === 1) {
    const skill = document.getElementById('reg_skill').value.trim();
    if (!skill) { showToast('Please enter your skill/trade', 'error'); return false; }
  }
  return true;
}

function fillReviewCard() {
  const card = document.getElementById('regReviewCard');
  card.innerHTML = `
    <div><strong>Name:</strong> ${document.getElementById('reg_name').value}</div>
    <div><strong>Phone:</strong> ${document.getElementById('reg_phone').value}</div>
    <div><strong>Location:</strong> ${document.getElementById('reg_location').value}</div>
    <div><strong>Skill:</strong> ${document.getElementById('reg_skill').value}</div>
    <div><strong>Experience:</strong> ${document.getElementById('reg_experience').value || '—'}</div>
    <div><strong>Daily Wage:</strong> ₹${document.getElementById('reg_wage').value || '—'}/day</div>
  `;
}

async function submitRegistration() {
  const data = {
    name: document.getElementById('reg_name').value.trim(),
    phone: document.getElementById('reg_phone').value.trim(),
    location: document.getElementById('reg_location').value.trim(),
    skill: document.getElementById('reg_skill').value.trim(),
    experience: document.getElementById('reg_experience').value.trim(),
    daily_wage: document.getElementById('reg_wage').value.trim(),
  };
  try {
    const res = await fetch('/api/labours', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (res.ok) {
      currentWizardStep = 3;
      updateWizardUI();
      allWorkers = [];
    } else if (res.status === 409) {
      showToast('This phone number is already registered! / यह नंबर पहले से पंजीकृत है! / ఈ నంబర్ ఇప్పటికే నమోదు చేయబడింది!', 'error');
    } else {
      showToast('Registration failed. Please try again.', 'error');
    }
  } catch(e) {
    showToast('Network error. Please try again.', 'error');
  }
}

// ─── JOBS ─────────────────────────────────
async function loadJobs() {
  const grid = document.getElementById('jobsGrid');
  grid.innerHTML = '<div class="spinner"></div>';
  try {
    const res = await fetch('/api/jobs');
    allJobs = await res.json();
    renderJobs(allJobs);
  } catch(e) {
    grid.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Could not load jobs. Please refresh.</p></div>';
  }
}

function renderJobs(list) {
  const grid = document.getElementById('jobsGrid');
  if (!list.length) {
    grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">💼</div><p>No open jobs right now. Be the first to post one!</p><br/><button class="btn btn-primary" onclick="showPage(\'post\')">Post a Job</button></div>';
    return;
  }
  grid.innerHTML = list.map(j => {
    const waPhone = cleanPhone(j.phone);
    const waMsg = encodeURIComponent(`Hello ${j.contractor_name}, I saw your job on ShramikLink for ${j.work_type} work. I am interested.`);
    const photoHtml = j.photo_data ? `<img class="job-photo" src="${j.photo_data}" alt="Work photo" onclick="openLightbox('${j.photo_data}')"/>` : '';
    const adminDeleteBtn = `<button class="btn btn-danger btn-sm admin-only" onclick="deleteJob(${j.id})" style="display:none">🗑 Delete</button>`;
    return `
      <div class="job-card">
        <div class="job-header">
          <div class="job-type-badge">${j.work_type || 'General Work'}</div>
          <div class="job-title">Posted by: ${j.contractor_name}</div>
          <div style="font-size:.78rem;color:var(--text-muted)">📅 ${j.created_at ? j.created_at.split(' ')[0] : 'Recently'}</div>
        </div>
        ${photoHtml}
        <div class="job-meta-grid">
          <div class="job-meta-item"><strong>📍 Location</strong>${j.location || '—'}</div>
          <div class="job-meta-item"><strong>👷 Workers</strong>${j.workers_needed || '—'} needed</div>
          <div class="job-meta-item"><strong>💰 Wage</strong>₹${j.wage_offered || '—'}/day</div>
          <div class="job-meta-item"><strong>📋 Status</strong>${j.status || 'Open'}</div>
        </div>
        ${j.requirements ? `<p style="font-size:.85rem;color:var(--text-secondary);line-height:1.55;margin-bottom:12px">${j.requirements}</p>` : ''}
        <div class="job-actions">
          <a href="tel:${j.phone}" class="btn btn-primary">📞 Call</a>
          <a href="https://wa.me/${waPhone}?text=${waMsg}" target="_blank" class="btn btn-wa">💬 WhatsApp</a>
          ${adminDeleteBtn}
        </div>
      </div>
    `;
  }).join('');
  if (document.body.classList.contains('is-admin')) {
    document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'inline-flex');
  }
}

// ─── DELETE JOB (Admin only) ─────────────
async function deleteJob(id) {
  if (!confirm('Delete this job permanently?')) return;
  try {
    const res = await fetch(`/api/jobs/${id}`, {
      method: 'DELETE',
      headers: { 'X-Admin-PIN': ADMIN_PIN }
    });
    if (res.ok) { showToast('Job deleted', 'success'); loadJobs(); if (document.body.classList.contains('is-admin')) loadAdminData(); }
    else showToast('Delete failed', 'error');
  } catch(e) { showToast('Network error', 'error'); }
}

// ─── POST JOB ────────────────────────────
function handlePhotoUpload(input) {
  const file = input.files[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) { showToast('Photo must be under 5MB', 'error'); return; }
  const reader = new FileReader();
  reader.onload = e => {
    postPhotoData = e.target.result;
    const preview = document.getElementById('photoPreview');
    preview.src = postPhotoData;
    preview.style.display = 'block';
    document.getElementById('photoUploadZone').classList.add('has-photo');
    document.getElementById('upload-text-hint').textContent = '✅ Photo selected! Click to change.';
  };
  reader.readAsDataURL(file);
}

async function submitJob() {
  const data = {
    contractor_name: document.getElementById('post_cname').value.trim(),
    phone: document.getElementById('post_cphone').value.trim(),
    location: document.getElementById('post_location').value.trim(),
    work_type: document.getElementById('post_work_type').value.trim(),
    workers_needed: parseInt(document.getElementById('post_workers_needed').value) || 1,
    wage_offered: document.getElementById('post_wage').value.trim(),
    requirements: document.getElementById('post_requirements').value.trim(),
    photo_data: postPhotoData,
  };
  if (!data.contractor_name) { showToast('Please enter your name', 'error'); return; }
  if (!/^\d{10}$/.test(data.phone)) { showToast('Please enter a valid 10-digit mobile number', 'error'); return; }
  if (!data.location) { showToast('Please enter work location', 'error'); return; }
  if (!data.work_type) { showToast('Please enter work type', 'error'); return; }
  const btn = document.getElementById('post-submit-btn');
  btn.disabled = true; btn.textContent = 'Posting...';
  try {
    const res = await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (res.ok) {
      showToast('Job posted successfully! Workers will contact you.', 'success');
      // Reset form
      ['post_cname','post_cphone','post_location','post_work_type','post_workers_needed','post_wage','post_requirements'].forEach(id => document.getElementById(id).value = '');
      postPhotoData = '';
      document.getElementById('photoPreview').style.display = 'none';
      document.getElementById('photoUploadZone').classList.remove('has-photo');
      document.getElementById('upload-text-hint').textContent = 'Click to upload a photo of the work site or problem';
      showPage('jobs');
    } else {
      showToast('Failed to post job. Please try again.', 'error');
    }
  } catch(e) { showToast('Network error', 'error'); }
  finally { btn.disabled = false; btn.textContent = '📮 Post Job Now'; }
}

// ─── LIGHTBOX ────────────────────────────
function openLightbox(src) {
  document.getElementById('lightboxImg').src = src;
  document.getElementById('lightbox').classList.remove('hidden');
}
function closeLightbox() {
  document.getElementById('lightbox').classList.add('hidden');
  document.getElementById('lightboxImg').src = '';
}
document.getElementById('lightbox').addEventListener('click', e => { if (e.target.id === 'lightbox') closeLightbox(); });

// ─── ADMIN ───────────────────────────────
async function loadAdminData() {
  loadStats();
  // Stats grid
  try {
    const [wRes, jRes] = await Promise.all([fetch('/api/labours'), fetch('/api/jobs')]);
    const workers = await wRes.json();
    const jobs = await jRes.json();
    const available = workers.filter(w => w.status === 'Available').length;
    const busy = workers.filter(w => w.status === 'Busy').length;
    const cities = new Set(workers.map(w => w.location?.trim()).filter(Boolean)).size;
    document.getElementById('adminStatsGrid').innerHTML = [
      { label: 'Total Workers', value: workers.length, icon: '👷' },
      { label: 'Available', value: available, icon: '✅' },
      { label: 'Busy', value: busy, icon: '🔴' },
      { label: 'Total Jobs', value: jobs.length, icon: '💼' },
      { label: 'Open Jobs', value: jobs.filter(j=>j.status==='Open').length, icon: '📋' },
      { label: 'Cities', value: cities, icon: '🏙️' },
    ].map(s => `
      <div style="background:var(--bg-page);padding:16px;border-radius:var(--radius-md);text-align:center">
        <div style="font-size:1.6rem;margin-bottom:6px">${s.icon}</div>
        <div style="font-size:1.5rem;font-weight:800;color:var(--brand-primary)">${s.value}</div>
        <div style="font-size:.78rem;color:var(--text-muted)">${s.label}</div>
      </div>
    `).join('');

    // Workers table
    document.getElementById('adminWorkersTable').innerHTML = `
      <table style="width:100%;border-collapse:collapse;font-size:.85rem">
        <thead><tr style="background:var(--bg-page)">${['ID','Name','Phone','Location','Skill','Status','Action'].map(h=>`<th style="padding:10px 12px;text-align:left;border-bottom:1px solid var(--border);white-space:nowrap">${h}</th>`).join('')}</tr></thead>
        <tbody>${workers.map(w=>`
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:10px 12px">${w.id}</td>
            <td style="padding:10px 12px;font-weight:600">${w.name}</td>
            <td style="padding:10px 12px">${w.phone}</td>
            <td style="padding:10px 12px">${w.location||'—'}</td>
            <td style="padding:10px 12px">${w.skill||'—'}</td>
            <td style="padding:10px 12px"><span class="chip ${w.status==='Available'?'chip-green':'chip-orange'}">${w.status}</span></td>
            <td style="padding:10px 12px"><button class="btn btn-danger btn-sm" onclick="deleteWorker(${w.id})">🗑</button></td>
          </tr>
        `).join('')}</tbody>
      </table>`;

    // Jobs table
    document.getElementById('adminJobsTable').innerHTML = `
      <table style="width:100%;border-collapse:collapse;font-size:.85rem">
        <thead><tr style="background:var(--bg-page)">${['ID','Posted By','Phone','Location','Type','Workers','Wage','Action'].map(h=>`<th style="padding:10px 12px;text-align:left;border-bottom:1px solid var(--border);white-space:nowrap">${h}</th>`).join('')}</tr></thead>
        <tbody>${jobs.map(j=>`
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:10px 12px">${j.id}</td>
            <td style="padding:10px 12px;font-weight:600">${j.contractor_name}</td>
            <td style="padding:10px 12px">${j.phone}</td>
            <td style="padding:10px 12px">${j.location||'—'}</td>
            <td style="padding:10px 12px">${j.work_type||'—'}</td>
            <td style="padding:10px 12px">${j.workers_needed||'—'}</td>
            <td style="padding:10px 12px">₹${j.wage_offered||'—'}</td>
            <td style="padding:10px 12px"><button class="btn btn-danger btn-sm" onclick="deleteJob(${j.id})">🗑</button></td>
          </tr>
        `).join('')}</tbody>
      </table>`;
  } catch(e) { console.error('Admin load error', e); }
}

// ─── BACKUP / RESTORE ────────────────────
async function downloadBackup() {
  try {
    const res = await fetch('/api/backup');
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'shramiklink_backup_' + new Date().toISOString().slice(0,10) + '.json';
    a.click();
    showToast('Backup downloaded!', 'success');
  } catch(e) { showToast('Backup failed', 'error'); }
}

async function restoreBackup(input) {
  const file = input.files[0];
  if (!file) return;
  if (!confirm('This will REPLACE all current data. Are you sure?')) { input.value=''; return; }
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch('/api/restore', { method: 'POST', body: fd });
    if (res.ok) { showToast('Restore successful! Reloading...', 'success'); setTimeout(()=>location.reload(), 1500); }
    else showToast('Restore failed', 'error');
  } catch(e) { showToast('Network error', 'error'); }
}

// ─── TOAST ───────────────────────────────
function showToast(msg, type = 'info') {
  const icons = { success:'✅', error:'❌', info:'ℹ️', warn:'⚠️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `${icons[type]||''} ${msg}`;
  document.getElementById('toastContainer').appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ─── SHAKE CSS (for wrong PIN) ───────────
const shakeStyle = document.createElement('style');
shakeStyle.textContent = `@keyframes shake { 0%,100%{transform:translateX(0)} 20%{transform:translateX(-8px)} 40%{transform:translateX(8px)} 60%{transform:translateX(-5px)} 80%{transform:translateX(5px)} }`;
document.head.appendChild(shakeStyle);

// ─── INITIAL LOAD ─────────────────────────
function loadInitialData() {
  loadStats();
  // Pre-load workers in background
  fetch('/api/labours').then(r=>r.json()).then(d=>{
    allWorkers=d;
    renderCategories();
    loadStats();
  }).catch(()=>{});
}
</script>
</body>
</html>"""

# ─────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return HTML_TEMPLATE

# ── WORKERS ──────────────────────────────────

@app.route('/api/labours', methods=['GET'])
def get_labours():
    conn = get_db()
    rows = conn.execute("SELECT * FROM labours ORDER BY created_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/labours', methods=['POST'])
def add_labour():
    data = request.json or {}
    name  = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    location   = data.get('location', '').strip()
    skill      = data.get('skill', '').strip()
    experience = data.get('experience', '').strip()
    daily_wage = data.get('daily_wage', '').strip()

    if not name or not phone:
        return jsonify({'error': 'Name and phone are required'}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO labours (name,phone,location,skill,experience,daily_wage) VALUES (?,?,?,?,?,?)",
            (name, phone, location, skill, experience, daily_wage)
        )
        conn.commit()
        return jsonify({'message': 'Worker registered successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({
            'error': 'Phone number already registered! / यह नंबर पहले से पंजीकृत है! / ఈ నంబర్ ఇప్పటికే నమోదు చేయబడింది!'
        }), 409

@app.route('/api/labours/<int:labour_id>', methods=['DELETE'])
def delete_labour(labour_id):
    pin = request.headers.get('X-Admin-PIN', '')
    if pin != ADMIN_PIN:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("DELETE FROM labours WHERE id=?", (labour_id,))
    conn.commit()
    return jsonify({'message': 'Worker deleted'})

@app.route('/api/labours/<int:labour_id>/assign', methods=['PATCH'])
def assign_labour(labour_id):
    data = request.json or {}
    contractor_name = data.get('contractor_name', '')
    status = data.get('status', 'Busy')
    conn = get_db()
    conn.execute(
        "UPDATE labours SET assigned_contractor=?, status=? WHERE id=?",
        (contractor_name, status, labour_id)
    )
    conn.commit()
    return jsonify({'message': 'Worker updated'})

# ── JOBS ─────────────────────────────────────

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM contractor_jobs ORDER BY created_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/jobs', methods=['POST'])
def add_job():
    data = request.json or {}
    conn = get_db()
    conn.execute("""
        INSERT INTO contractor_jobs
          (contractor_name, phone, location, work_type, workers_needed, wage_offered, requirements, photo_data)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        data.get('contractor_name', ''),
        data.get('phone', ''),
        data.get('location', ''),
        data.get('work_type', ''),
        data.get('workers_needed', 1),
        data.get('wage_offered', ''),
        data.get('requirements', ''),
        data.get('photo_data', ''),
    ))
    conn.commit()
    return jsonify({'message': 'Job posted successfully'}), 201

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    pin = request.headers.get('X-Admin-PIN', '')
    if pin != ADMIN_PIN:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("DELETE FROM contractor_jobs WHERE id=?", (job_id,))
    conn.commit()
    return jsonify({'message': 'Job deleted'})

# ── REVIEWS ──────────────────────────────────

@app.route('/api/workers/<int:worker_id>/reviews', methods=['POST'])
def add_review(worker_id):
    data = request.json or {}
    conn = get_db()
    conn.execute(
        "INSERT INTO worker_reviews (worker_id, reviewer_name, rating, comment) VALUES (?,?,?,?)",
        (worker_id, data.get('reviewer_name',''), data.get('rating', 5), data.get('comment',''))
    )
    conn.commit()
    return jsonify({'message': 'Review submitted'}), 201

@app.route('/api/workers/<int:worker_id>/reviews', methods=['GET'])
def get_reviews(worker_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM worker_reviews WHERE worker_id=? ORDER BY created_at DESC",
        (worker_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])

# ── STATS ─────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    workers_count = conn.execute("SELECT COUNT(*) FROM labours").fetchone()[0]
    jobs_count = conn.execute("SELECT COUNT(*) FROM contractor_jobs WHERE status='Open'").fetchone()[0]
    cities_count = conn.execute("SELECT COUNT(DISTINCT location) FROM labours WHERE location != ''").fetchone()[0]
    return jsonify({
        'workers': workers_count,
        'jobs': jobs_count,
        'cities': cities_count,
    })

# ── BACKUP / RESTORE ─────────────────────────

@app.route('/api/backup', methods=['GET'])
def backup():
    conn = get_db()
    labours = [dict(r) for r in conn.execute("SELECT * FROM labours").fetchall()]
    jobs    = [dict(r) for r in conn.execute("SELECT * FROM contractor_jobs").fetchall()]
    reviews = [dict(r) for r in conn.execute("SELECT * FROM worker_reviews").fetchall()]
    data = json.dumps({'labours': labours, 'contractor_jobs': jobs, 'worker_reviews': reviews}, ensure_ascii=False, indent=2)
    buf = BytesIO(data.encode('utf-8'))
    buf.seek(0)
    return send_file(buf, mimetype='application/json',
                     download_name='shramiklink_backup.json', as_attachment=True)

@app.route('/api/restore', methods=['POST'])
def restore():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400
    try:
        data = json.loads(file.read().decode('utf-8'))
    except Exception as e:
        return jsonify({'error': 'Invalid JSON: ' + str(e)}), 400

    conn = get_db()
    if 'labours' in data:
        conn.execute("DELETE FROM labours")
        for row in data['labours']:
            conn.execute("""
                INSERT OR IGNORE INTO labours
                  (id, name, phone, location, skill, experience, daily_wage, status, assigned_contractor, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (row.get('id'), row.get('name'), row.get('phone'), row.get('location'),
                  row.get('skill'), row.get('experience'), row.get('daily_wage'),
                  row.get('status','Available'), row.get('assigned_contractor',''), row.get('created_at','')))
    if 'contractor_jobs' in data:
        conn.execute("DELETE FROM contractor_jobs")
        for row in data['contractor_jobs']:
            conn.execute("""
                INSERT OR IGNORE INTO contractor_jobs
                  (id, contractor_name, phone, location, work_type, workers_needed, wage_offered, requirements, photo_data, status, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (row.get('id'), row.get('contractor_name'), row.get('phone'), row.get('location'),
                  row.get('work_type'), row.get('workers_needed'), row.get('wage_offered'),
                  row.get('requirements'), row.get('photo_data',''), row.get('status','Open'), row.get('created_at','')))
    if 'worker_reviews' in data:
        conn.execute("DELETE FROM worker_reviews")
        for row in data['worker_reviews']:
            conn.execute("""
                INSERT OR IGNORE INTO worker_reviews
                  (id, worker_id, reviewer_name, rating, comment, created_at)
                VALUES (?,?,?,?,?,?)
            """, (row.get('id'), row.get('worker_id'), row.get('reviewer_name'),
                  row.get('rating'), row.get('comment'), row.get('created_at','')))
    conn.commit()
    return jsonify({'message': 'Restore successful'})

# ─────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

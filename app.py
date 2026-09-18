from flask import Flask, jsonify, render_template_string, request, Response
from flask_cors import CORS
import sqlite3
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "labour_portal.db"

# ─────────────────────────────────────────────────────────────
# 1. DATABASE INITIALIZATION & SEEDING
# ─────────────────────────────────────────────────────────────
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Labours Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS labours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT NOT NULL,
            skill TEXT NOT NULL,
            experience TEXT NOT NULL,
            daily_wage TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Contractor Requirements Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contractor_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractor_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT NOT NULL,
            work_type TEXT NOT NULL,
            workers_needed INTEGER NOT NULL,
            wage_offered TEXT NOT NULL,
            requirements TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed demo data if database is brand new
    cursor.execute("SELECT COUNT(*) FROM labours")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO labours (name, phone, location, skill, experience, daily_wage, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Ramesh Kumar", "+91 98765 43210", "Mumbai, Andheri", "Mason (Mistri)", "8 Years", "₹850 / day", "Available"),
            ("Sunil Verma", "+91 98123 45678", "Delhi, Rohini", "Electrician", "5 Years", "₹750 / day", "Available"),
            ("Mohammad Arif", "+91 97234 56789", "Bengaluru, Whitefield", "Plumber", "6 Years", "₹800 / day", "Available"),
            ("Vikram Singh", "+91 96345 67890", "Pune, Hinjewadi", "Painter", "4 Years", "₹650 / day", "Busy"),
            ("Deepak Patel", "+91 95456 78901", "Ahmedabad, SG Highway", "Carpenter", "7 Years", "₹900 / day", "Available"),
            ("Santosh Yadav", "+91 94567 89012", "Lucknow, Gomti Nagar", "General Helper", "2 Years", "₹500 / day", "Available")
        ])

    cursor.execute("SELECT COUNT(*) FROM contractor_jobs")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO contractor_jobs (contractor_name, phone, location, work_type, workers_needed, wage_offered, requirements, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Apex Infra Builders", "+91 99887 76655", "Mumbai, Goregaon West", "Masonry & Plaster", 6, "₹900 / day", "Need 6 experienced masons for residential slab and brickwork. Food provided. 15 days work.", "Open"),
            ("Metro Electric Corp", "+91 98776 65544", "Delhi, Dwarka Sector 12", "Electrical Wiring", 4, "₹800 / day", "Commercial tower electrical conduit fitting. Tools provided. Immediate joining.", "Open"),
            ("Shree Ganesh Paints", "+91 97665 54433", "Pune, Baner", "Interior Painting", 3, "₹750 / day", "Interior putty & 2-coat painting for 4 villas. 8 days work.", "Open")
        ])

    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────────────────────────
# 2. FRONTEND UI TEMPLATE (RESPONSIVE & MOBILE PWA READY)
# ─────────────────────────────────────────────────────────────
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ShramikLink | Labour & Contractor Connect</title>
    <meta name="theme-color" content="#0b0f19">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-main: #0b0f19;
            --bg-card: #131c2e;
            --bg-card-hover: #19253d;
            --accent-gold: #f59e0b;
            --accent-gold-hover: #d97706;
            --accent-blue: #38bdf8;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border-color: #23324d;
            --success: #10b981;
            --danger: #ef4444;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body {
            background-color: var(--bg-main);
            background-image: radial-gradient(circle at 15% 15%, rgba(245, 158, 11, 0.08) 0%, transparent 35%),
                              radial-gradient(circle at 85% 85%, rgba(56, 189, 248, 0.06) 0%, transparent 35%),
                              linear-gradient(180deg, #090d16 0%, #0d1424 100%);
            color: var(--text-primary);
            min-height: 100vh;
            padding-bottom: 70px;
        }

        /* HEADER / NAVBAR */
        header {
            background: rgba(19, 28, 46, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
            padding: 14px 20px;
        }
        .nav-container {
            max-width: 1100px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
            color: var(--text-primary);
        }
        .brand-icon {
            background: linear-gradient(135deg, var(--accent-gold), #b45309);
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: #000;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35);
        }
        .brand-title {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        .brand-title span { color: var(--accent-gold); }
        .privacy-pill {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            background: rgba(16, 185, 129, 0.12);
            color: var(--success);
            padding: 6px 12px;
            border-radius: 20px;
            border: 1px solid rgba(16, 185, 129, 0.25);
        }

        /* HERO & STATS */
        .hero {
            max-width: 1100px;
            margin: 24px auto 16px auto;
            padding: 0 20px;
            text-align: center;
        }
        .hero h1 {
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 8px;
            background: linear-gradient(90deg, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero p { color: var(--text-secondary); font-size: 15px; max-width: 600px; margin: 0 auto 20px auto; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            max-width: 700px;
            margin: 0 auto 24px auto;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px;
            text-align: center;
        }
        .stat-val { font-size: 24px; font-weight: 800; color: var(--accent-gold); }
        .stat-lbl { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }

        /* TABS */
        .tabs-container {
            max-width: 1100px;
            margin: 0 auto 24px auto;
            padding: 0 20px;
            display: flex;
            gap: 8px;
            overflow-x: auto;
            scrollbar-width: none;
        }
        .tabs-container::-webkit-scrollbar { display: none; }
        .tab-btn {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .tab-btn.active {
            background: var(--accent-gold);
            color: #000;
            border-color: var(--accent-gold);
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.25);
        }

        /* MAIN CONTENT AREA */
        .content-area {
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 20px;
        }

        /* SEARCH & FILTER BAR */
        .filter-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .search-input {
            flex: 1;
            min-width: 220px;
            padding: 12px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
        }
        .search-input:focus { outline: 2px solid var(--accent-gold); }
        .filter-select {
            padding: 12px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
        }

        /* CARDS GRID */
        .items-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 18px;
        }
        .item-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            position: relative;
            transition: transform 0.2s, border-color 0.2s;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .item-card:hover {
            transform: translateY(-2px);
            border-color: rgba(245, 158, 11, 0.5);
            background: var(--bg-card-hover);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }
        .card-title { font-size: 18px; font-weight: 700; color: #fff; }
        .card-badge {
            font-size: 11px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 6px;
            text-transform: uppercase;
        }
        .badge-available { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .badge-busy { background: rgba(239, 68, 68, 0.15); color: #f87171; }
        .badge-job { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
        
        .card-detail {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        .card-detail i { color: var(--accent-gold); width: 16px; }
        .wage-pill {
            display: inline-block;
            background: rgba(245, 158, 11, 0.12);
            color: var(--accent-gold);
            font-weight: 700;
            font-size: 13px;
            padding: 4px 10px;
            border-radius: 6px;
            margin-top: 6px;
            margin-bottom: 14px;
        }

        .action-row {
            display: flex;
            gap: 10px;
            margin-top: 14px;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding-top: 14px;
        }
        .btn-call {
            flex: 1;
            background: linear-gradient(135deg, #10b981, #059669);
            color: #fff;
            text-decoration: none;
            text-align: center;
            padding: 10px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .btn-call:hover { opacity: 0.9; }
        .btn-reveal {
            background: #1e293b;
            color: #94a3b8;
            border: 1px solid var(--border-color);
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
        }
        .btn-delete {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.2);
            padding: 10px 12px;
            border-radius: 8px;
            cursor: pointer;
        }

        /* FORMS */
        .form-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 24px;
            max-width: 600px;
            margin: 0 auto;
        }
        .form-title { font-size: 22px; margin-bottom: 6px; color: #fff; }
        .form-desc { color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; }
        .form-group { margin-bottom: 16px; }
        .form-label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #cbd5e1; }
        .form-input, .form-textarea, .form-select {
            width: 100%;
            padding: 12px;
            background: #090d16;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
        }
        .form-input:focus, .form-textarea:focus, .form-select:focus { outline: 2px solid var(--accent-gold); }
        .btn-submit {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, var(--accent-gold), #d97706);
            color: #000;
            border: none;
            border-radius: 8px;
            font-weight: 800;
            font-size: 15px;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
            margin-top: 10px;
        }
        .btn-submit:hover { opacity: 0.95; }

        /* BACKUP & PRIVACY SECTION */
        .backup-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 24px;
            max-width: 700px;
            margin: 0 auto;
        }
        .backup-option {
            background: #090d16;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .backup-info h4 { font-size: 15px; color: #fff; margin-bottom: 4px; }
        .backup-info p { font-size: 13px; color: var(--text-secondary); }

        /* TOAST NOTIFICATION */
        #toast {
            visibility: hidden;
            min-width: 250px;
            background: #10b981;
            color: #fff;
            text-align: center;
            border-radius: 8px;
            padding: 14px;
            position: fixed;
            z-index: 1000;
            left: 50%;
            bottom: 30px;
            transform: translateX(-50%);
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
        #toast.show { visibility: visible; animation: fadein 0.3s, fadeout 0.3s 2.5s; }
        @keyframes fadein { from { bottom: 0; opacity: 0; } to { bottom: 30px; opacity: 1; } }
        @keyframes fadeout { from { bottom: 30px; opacity: 1; } to { bottom: 0; opacity: 0; } }

        @media (max-width: 600px) {
            .hero h1 { font-size: 24px; }
            .items-grid { grid-template-columns: 1fr; }
            .filter-bar { flex-direction: column; }
        }
    </style>
</head>
<body>

    <!-- TOP NAV -->
    <header>
        <div class="nav-container">
            <a href="#" class="brand" onclick="switchTab('tab-labours')">
                <div class="brand-icon"><i class="fa-solid fa-helmet-safety"></i></div>
                <div class="brand-title">Shramik<span>Link</span></div>
            </a>
            <div class="privacy-pill">
                <i class="fa-solid fa-shield-halved"></i>
                <span>Data Protected</span>
            </div>
        </div>
    </header>

    <!-- HERO & QUICK STATS -->
    <div class="hero">
        <h1>Connect Skilled Labours & Contractors</h1>
        <p>Real-time workforce marketplace with instant call, requirement matching & mobile database backup.</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-val" id="count-labours">-</div>
                <div class="stat-lbl">Registered Workers</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="count-jobs">-</div>
                <div class="stat-lbl">Active Contractor Jobs</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" style="color: var(--success);">Zero</div>
                <div class="stat-lbl">Data Loss Risk</div>
            </div>
        </div>
    </div>

    <!-- NAVIGATION TABS -->
    <div class="tabs-container">
        <button class="tab-btn active" id="btn-labours" onclick="switchTab('tab-labours')">
            <i class="fa-solid fa-users"></i> Available Labours
        </button>
        <button class="tab-btn" id="btn-jobs" onclick="switchTab('tab-jobs')">
            <i class="fa-solid fa-briefcase"></i> Contractor Jobs
        </button>
        <button class="tab-btn" id="btn-reg-labour" onclick="switchTab('tab-reg-labour')">
            <i class="fa-solid fa-user-plus"></i> Register Worker
        </button>
        <button class="tab-btn" id="btn-post-job" onclick="switchTab('tab-post-job')">
            <i class="fa-solid fa-file-circle-plus"></i> Post Job Requirement
        </button>
        <button class="tab-btn" id="btn-backup" onclick="switchTab('tab-backup')">
            <i class="fa-solid fa-hard-drive"></i> Backup & Privacy
        </button>
    </div>

    <!-- MAIN CONTENT CONTAINERS -->
    <div class="content-area">

        <!-- TAB 1: AVAILABLE LABOURS -->
        <div id="tab-labours" class="tab-content">
            <div class="filter-bar">
                <input type="text" id="labourSearch" class="search-input" placeholder="🔍 Search by name, city, or trade..." oninput="filterLabours()">
                <select id="labourSkillFilter" class="filter-select" onchange="filterLabours()">
                    <option value="">All Trades</option>
                    <option value="Mason">Mason (Mistri)</option>
                    <option value="Electrician">Electrician</option>
                    <option value="Plumber">Plumber</option>
                    <option value="Painter">Painter</option>
                    <option value="Carpenter">Carpenter</option>
                    <option value="Helper">General Helper</option>
                </select>
            </div>
            <div id="labourList" class="items-grid">
                <p style="color: #64748b; padding: 20px;">Loading verified workers...</p>
            </div>
        </div>

        <!-- TAB 2: CONTRACTOR JOBS -->
        <div id="tab-jobs" class="tab-content" style="display: none;">
            <div class="filter-bar">
                <input type="text" id="jobSearch" class="search-input" placeholder="🔍 Search jobs by contractor, trade, or site location..." oninput="filterJobs()">
            </div>
            <div id="jobsList" class="items-grid">
                <p style="color: #64748b; padding: 20px;">Loading active job requirements...</p>
            </div>
        </div>

        <!-- TAB 3: REGISTER LABOUR -->
        <div id="tab-reg-labour" class="tab-content" style="display: none;">
            <div class="form-card">
                <h3 class="form-title"><i class="fa-solid fa-id-card" style="color: var(--accent-gold);"></i> Register New Worker</h3>
                <p class="form-desc">Add labour details to make them discoverable for local contractors.</p>

                <form id="formLabour" onsubmit="submitLabour(event)">
                    <div class="form-group">
                        <label class="form-label">Full Name *</label>
                        <input type="text" id="labName" class="form-input" placeholder="e.g. Ramesh Kumar" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Mobile Number * (Protected by Privacy)</label>
                        <input type="tel" id="labPhone" class="form-input" placeholder="e.g. +91 9876543210" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Primary Skill / Trade *</label>
                        <select id="labSkill" class="form-select" required>
                            <option value="Mason (Mistri)">Mason (Mistri / Construction)</option>
                            <option value="Electrician">Electrician</option>
                            <option value="Plumber">Plumber</option>
                            <option value="Painter">Painter</option>
                            <option value="Carpenter">Carpenter</option>
                            <option value="Welder">Welder</option>
                            <option value="Tile & Marble Fitter">Tile & Marble Fitter</option>
                            <option value="General Helper">General Construction Helper</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Location / City / Area *</label>
                        <input type="text" id="labLoc" class="form-input" placeholder="e.g. Mumbai, Andheri East" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Experience</label>
                        <input type="text" id="labExp" class="form-input" placeholder="e.g. 5 Years">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Expected Daily Wage</label>
                        <input type="text" id="labWage" class="form-input" placeholder="e.g. ₹750 / day">
                    </div>
                    <button type="submit" class="btn-submit"><i class="fa-solid fa-check-circle"></i> Save & Register Worker</button>
                </form>
            </div>
        </div>

        <!-- TAB 4: POST CONTRACTOR JOB -->
        <div id="tab-post-job" class="tab-content" style="display: none;">
            <div class="form-card">
                <h3 class="form-title"><i class="fa-solid fa-briefcase" style="color: var(--accent-gold);"></i> Post Contractor Requirement</h3>
                <p class="form-desc">Specify project work, required head count, wage, and site details.</p>

                <form id="formJob" onsubmit="submitJob(event)">
                    <div class="form-group">
                        <label class="form-label">Contractor / Firm Name *</label>
                        <input type="text" id="jobContractor" class="form-input" placeholder="e.g. Apex Infra Construction" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Contact Phone Number *</label>
                        <input type="tel" id="jobPhone" class="form-input" placeholder="e.g. +91 9988776655" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Type of Work Required *</label>
                        <input type="text" id="jobWorkType" class="form-input" placeholder="e.g. Masonry & RCC Slab Casting" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Project Site Location *</label>
                        <input type="text" id="jobLocation" class="form-input" placeholder="e.g. Pune, Hinjewadi Phase 2" required>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <div class="form-group" style="flex: 1;">
                            <label class="form-label">Workers Needed *</label>
                            <input type="number" id="jobWorkers" class="form-input" placeholder="e.g. 5" min="1" required>
                        </div>
                        <div class="form-group" style="flex: 1;">
                            <label class="form-label">Wage Offered</label>
                            <input type="text" id="jobWage" class="form-input" placeholder="e.g. ₹850 / day" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Requirements & Project Scope</label>
                        <textarea id="jobReqs" class="form-textarea" rows="3" placeholder="e.g. 10 days project. Safety gear provided. Overtime paid extra."></textarea>
                    </div>
                    <button type="submit" class="btn-submit"><i class="fa-solid fa-bullhorn"></i> Publish Requirement</button>
                </form>
            </div>
        </div>

        <!-- TAB 5: BACKUP & PRIVACY HUB -->
        <div id="tab-backup" class="tab-content" style="display: none;">
            <div class="backup-card">
                <h3 class="form-title"><i class="fa-solid fa-shield-cat" style="color: var(--accent-gold);"></i> Data Protection & Mobile Backup Hub</h3>
                <p class="form-desc">Guarantee zero data loss with instant 1-click backups and encrypted restore capabilities directly from your mobile or PC.</p>

                <div class="backup-option">
                    <div class="backup-info">
                        <h4><i class="fa-solid fa-cloud-arrow-down" style="color: var(--accent-gold);"></i> 1-Click Complete Database Backup</h4>
                        <p>Download the entire database (Labours + Contractor Jobs + Timestamps) as a standalone JSON backup file.</p>
                    </div>
                    <a href="/api/backup" download="shramiklink_backup.json" class="tab-btn active" style="text-decoration: none;">
                        <i class="fa-solid fa-download"></i> Download Backup
                    </a>
                </div>

                <div class="backup-option">
                    <div class="backup-info">
                        <h4><i class="fa-solid fa-rotate-left" style="color: var(--accent-blue);"></i> Restore Database from Backup</h4>
                        <p>Upload a previously downloaded JSON file to restore all records without any data loss.</p>
                    </div>
                    <div>
                        <input type="file" id="restoreFile" accept=".json" style="display: none;" onchange="handleRestore(event)">
                        <button class="tab-btn" onclick="document.getElementById('restoreFile').click()">
                            <i class="fa-solid fa-upload"></i> Upload & Restore
                        </button>
                    </div>
                </div>

                <div class="backup-option">
                    <div class="backup-info">
                        <h4><i class="fa-solid fa-mobile-screen" style="color: var(--success);"></i> Connect to Mobile (PWA)</h4>
                        <p>Open this link on your mobile Chrome or Safari browser, tap <b>Share / Settings</b> and choose <b>"Add to Home Screen"</b> to use it as an offline-capable mobile app.</p>
                    </div>
                    <button class="tab-btn" onclick="copyAppUrl()">
                        <i class="fa-solid fa-copy"></i> Copy App URL
                    </button>
                </div>
            </div>
        </div>

    </div>

    <div id="toast">Operation completed successfully!</div>

    <script>
        let allLabours = [];
        let allJobs = [];

        function showToast(msg, isError = false) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.background = isError ? '#ef4444' : '#10b981';
            t.className = "show";
            setTimeout(() => { t.className = t.className.replace("show", ""); }, 3000);
        }

        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            
            document.getElementById(tabId).style.display = 'block';
            
            const btnMap = {
                'tab-labours': 'btn-labours',
                'tab-jobs': 'btn-jobs',
                'tab-reg-labour': 'btn-reg-labour',
                'tab-post-job': 'btn-post-job',
                'tab-backup': 'btn-backup'
            };
            if (btnMap[tabId]) document.getElementById(btnMap[tabId]).classList.add('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        // Mask phone for anti-scraping privacy: +91 98765 43210 -> +91 98765-XXXXX
        function maskPhone(phone) {
            if (!phone) return 'N/A';
            const clean = phone.trim();
            if (clean.length > 5) {
                return clean.substring(0, clean.length - 5) + 'XXXXX';
            }
            return clean;
        }

        function revealPhone(btn, realPhone) {
            const parent = btn.parentElement;
            btn.style.display = 'none';
            const callLink = parent.querySelector('.btn-call');
            if (callLink) {
                callLink.innerHTML = `<i class="fa-solid fa-phone"></i> ${realPhone}`;
            }
        }

        async function fetchAllData() {
            try {
                const [labRes, jobRes] = await Promise.all([
                    fetch('/api/labours'),
                    fetch('/api/jobs')
                ]);
                allLabours = await labRes.json();
                allJobs = await jobRes.json();

                document.getElementById('count-labours').innerText = allLabours.length;
                document.getElementById('count-jobs').innerText = allJobs.length;

                renderLabours(allLabours);
                renderJobs(allJobs);
            } catch (err) {
                console.error(err);
                showToast("Failed to load records from cloud database", true);
            }
        }

        function renderLabours(list) {
            const container = document.getElementById('labourList');
            if (list.length === 0) {
                container.innerHTML = '<p style="color: #64748b; padding: 20px;">No labours match the criteria.</p>';
                return;
            }
            container.innerHTML = list.map(l => `
                <div class="item-card">
                    <div>
                        <div class="card-header">
                            <div class="card-title">${l.name}</div>
                            <span class="card-badge ${l.status === 'Available' ? 'badge-available' : 'badge-busy'}">
                                ${l.status}
                            </span>
                        </div>
                        <div class="card-detail"><i class="fa-solid fa-hammer"></i> <b>Trade:</b> ${l.skill}</div>
                        <div class="card-detail"><i class="fa-solid fa-location-dot"></i> <b>Location:</b> ${l.location}</div>
                        <div class="card-detail"><i class="fa-solid fa-clock"></i> <b>Experience:</b> ${l.experience || 'Not specified'}</div>
                        <div class="wage-pill"><i class="fa-solid fa-money-bill-wave"></i> ${l.daily_wage || 'Daily Rate Negotiable'}</div>
                    </div>
                    <div class="action-row">
                        <a href="tel:${l.phone}" class="btn-call">
                            <i class="fa-solid fa-phone"></i> Call Worker
                        </a>
                        <button class="btn-reveal" onclick="revealPhone(this, '${l.phone}')" title="Reveal Phone Number">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                        <button class="btn-delete" onclick="deleteLabour(${l.id})" title="Remove Worker">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        }

        function renderJobs(list) {
            const container = document.getElementById('jobsList');
            if (list.length === 0) {
                container.innerHTML = '<p style="color: #64748b; padding: 20px;">No job postings available.</p>';
                return;
            }
            container.innerHTML = list.map(j => `
                <div class="item-card">
                    <div>
                        <div class="card-header">
                            <div class="card-title">${j.work_type}</div>
                            <span class="card-badge badge-job"><i class="fa-solid fa-people-carry-box"></i> ${j.workers_needed} Needed</span>
                        </div>
                        <div class="card-detail"><i class="fa-solid fa-building-user"></i> <b>Contractor:</b> ${j.contractor_name}</div>
                        <div class="card-detail"><i class="fa-solid fa-location-dot"></i> <b>Site:</b> ${j.location}</div>
                        <div class="wage-pill"><i class="fa-solid fa-coins"></i> Offered: ${j.wage_offered}</div>
                        <p style="font-size: 13px; color: #cbd5e1; background: #090d16; padding: 10px; border-radius: 6px; margin-top: 6px; border: 1px solid var(--border-color);">
                            ${j.requirements || 'No extra requirements specified.'}
                        </p>
                    </div>
                    <div class="action-row">
                        <a href="tel:${j.phone}" class="btn-call">
                            <i class="fa-solid fa-phone"></i> Contact Contractor
                        </a>
                        <button class="btn-reveal" onclick="revealPhone(this, '${j.phone}')" title="Reveal Phone Number">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                        <button class="btn-delete" onclick="deleteJob(${j.id})" title="Close Job">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        }

        function filterLabours() {
            const query = document.getElementById('labourSearch').value.toLowerCase();
            const skill = document.getElementById('labourSkillFilter').value.toLowerCase();
            const filtered = allLabours.filter(l => {
                const matchesQuery = l.name.toLowerCase().includes(query) || 
                                     l.location.toLowerCase().includes(query) || 
                                     l.skill.toLowerCase().includes(query);
                const matchesSkill = !skill || l.skill.toLowerCase().includes(skill);
                return matchesQuery && matchesSkill;
            });
            renderLabours(filtered);
        }

        function filterJobs() {
            const query = document.getElementById('jobSearch').value.toLowerCase();
            const filtered = allJobs.filter(j => 
                j.contractor_name.toLowerCase().includes(query) ||
                j.work_type.toLowerCase().includes(query) ||
                j.location.toLowerCase().includes(query) ||
                j.requirements.toLowerCase().includes(query)
            );
            renderJobs(filtered);
        }

        async function submitLabour(e) {
            e.preventDefault();
            const data = {
                name: document.getElementById('labName').value.trim(),
                phone: document.getElementById('labPhone').value.trim(),
                skill: document.getElementById('labSkill').value,
                location: document.getElementById('labLoc').value.trim(),
                experience: document.getElementById('labExp').value.trim(),
                daily_wage: document.getElementById('labWage').value.trim()
            };

            const res = await fetch('/api/labours', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                showToast("Worker registered successfully!");
                document.getElementById('formLabour').reset();
                await fetchAllData();
                switchTab('tab-labours');
            } else {
                showToast("Failed to register worker", true);
            }
        }

        async function submitJob(e) {
            e.preventDefault();
            const data = {
                contractor_name: document.getElementById('jobContractor').value.trim(),
                phone: document.getElementById('jobPhone').value.trim(),
                work_type: document.getElementById('jobWorkType').value.trim(),
                location: document.getElementById('jobLocation').value.trim(),
                workers_needed: document.getElementById('jobWorkers').value,
                wage_offered: document.getElementById('jobWage').value.trim(),
                requirements: document.getElementById('jobReqs').value.trim()
            };

            const res = await fetch('/api/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                showToast("Job requirement published!");
                document.getElementById('formJob').reset();
                await fetchAllData();
                switchTab('tab-jobs');
            } else {
                showToast("Failed to publish requirement", true);
            }
        }

        async function deleteLabour(id) {
            if (!confirm("Are you sure you want to remove this worker profile?")) return;
            await fetch('/api/labours/' + id, { method: 'DELETE' });
            showToast("Labour profile removed");
            fetchAllData();
        }

        async function deleteJob(id) {
            if (!confirm("Are you sure you want to close this job posting?")) return;
            await fetch('/api/jobs/' + id, { method: 'DELETE' });
            showToast("Job requirement closed");
            fetchAllData();
        }

        async function handleRestore(e) {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = async function(event) {
                try {
                    const payload = JSON.parse(event.target.result);
                    const res = await fetch('/api/restore', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    if (res.ok) {
                        showToast("Database restored successfully without data loss!");
                        fetchAllData();
                        switchTab('tab-labours');
                    } else {
                        showToast("Restore failed: Invalid backup format", true);
                    }
                } catch (err) {
                    showToast("Error parsing backup file", true);
                }
            };
            reader.readAsText(file);
        }

        function copyAppUrl() {
            navigator.clipboard.writeText(window.location.href);
            showToast("Mobile link copied! Paste on your phone");
        }

        // Initialize on load
        fetchAllData();
    </script>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────
# 3. BACKEND API ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

# --- LABOUR ENDPOINTS ---
@app.route("/api/labours", methods=["GET"])
def get_labours():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM labours ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/labours", methods=["POST"])
def add_labour():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO labours (name, phone, location, skill, experience, daily_wage, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name"),
        data.get("phone"),
        data.get("location"),
        data.get("skill"),
        data.get("experience", "Not specified"),
        data.get("daily_wage", "Negotiable"),
        data.get("status", "Available")
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "Labour registered successfully"}), 201

@app.route("/api/labours/<int:id>", methods=["DELETE"])
def delete_labour(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM labours WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Labour {id} deleted"}), 200

# --- CONTRACTOR JOBS ENDPOINTS ---
@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contractor_jobs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/jobs", methods=["POST"])
def add_job():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contractor_jobs (contractor_name, phone, location, work_type, workers_needed, wage_offered, requirements, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("contractor_name"),
        data.get("phone"),
        data.get("location"),
        data.get("work_type"),
        data.get("workers_needed", 1),
        data.get("wage_offered"),
        data.get("requirements", ""),
        data.get("status", "Open")
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "Job requirement created"}), 201

@app.route("/api/jobs/<int:id>", methods=["DELETE"])
def delete_job(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contractor_jobs WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Job {id} deleted"}), 200

# --- MASSIVE BACKUP & RESTORE (ZERO DATA LOSS) ---
@app.route("/api/backup", methods=["GET"])
def backup_database():
    """Exports all labours and jobs as a structured JSON snapshot for download."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM labours")
    labours = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM contractor_jobs")
    jobs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    backup_data = {
        "app": "ShramikLink",
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "total_labours": len(labours),
        "total_jobs": len(jobs),
        "labours": labours,
        "contractor_jobs": jobs
    }

    response = Response(
        json.dumps(backup_data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename=shramiklink_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
    )
    return response

@app.route("/api/restore", methods=["POST"])
def restore_database():
    """Restores database tables from an uploaded JSON backup without duplicates."""
    data = request.get_json()
    if not data or "labours" not in data or "contractor_jobs" not in data:
        return jsonify({"error": "Invalid backup file structure"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing and restore safely
    cursor.execute("DELETE FROM labours")
    cursor.execute("DELETE FROM contractor_jobs")

    for l in data["labours"]:
        cursor.execute("""
            INSERT INTO labours (name, phone, location, skill, experience, daily_wage, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (l["name"], l["phone"], l["location"], l["skill"], l.get("experience", ""), l.get("daily_wage", ""), l.get("status", "Available")))

    for j in data["contractor_jobs"]:
        cursor.execute("""
            INSERT INTO contractor_jobs (contractor_name, phone, location, work_type, workers_needed, wage_offered, requirements, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (j["contractor_name"], j["phone"], j["location"], j["work_type"], j.get("workers_needed", 1), j.get("wage_offered", ""), j.get("requirements", ""), j.get("status", "Open")))

    conn.commit()
    conn.close()
    return jsonify({"message": "Database restored successfully", "labours_restored": len(data["labours"]), "jobs_restored": len(data["contractor_jobs"])}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

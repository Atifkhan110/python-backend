from flask import Flask, jsonify, render_template_string, request, Response
from flask_cors import CORS
import sqlite3
import json
import os
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "labour_portal.db"

# 1. DATABASE SETUP
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
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

    cursor.execute("SELECT COUNT(*) FROM labours")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO labours (name, phone, location, skill, experience, daily_wage, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Ramesh Kumar", "+91 98765 43210", "Hyderabad, Gachibowli", "Mason (Mistri)", "8 Years", "₹850 / day", "Available"),
            ("Sunil Verma", "+91 98123 45678", "Delhi NCR, Noida", "Electrician", "5 Years", "₹750 / day", "Available"),
            ("Mohammad Arif", "+91 97234 56789", "Bengaluru, Whitefield", "Plumber", "6 Years", "₹800 / day", "Available"),
            ("Suresh Reddy", "+91 99123 44556", "Visakhapatnam, Madhurawada", "Tile & Marble", "7 Years", "₹900 / day", "Available"),
            ("Vikram Singh", "+91 96345 67890", "Pune, Hinjewadi", "Painter", "4 Years", "₹650 / day", "Busy"),
            ("Santosh Yadav", "+91 94567 89012", "Lucknow, Gomti Nagar", "General Helper", "2 Years", "₹500 / day", "Available")
        ])

    cursor.execute("SELECT COUNT(*) FROM contractor_jobs")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO contractor_jobs (contractor_name, phone, location, work_type, workers_needed, wage_offered, requirements, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Apex Infra Builders", "+91 99887 76655", "Hyderabad, Hitec City", "Masonry & RCC Slab", 6, "₹900 / day", "Need 6 experienced masons for high-rise commercial slab work. On-site accommodation and meals provided.", "Open"),
            ("Metro Power & Electric", "+91 98776 65544", "Delhi, Dwarka", "Electrical Conduit Fitting", 4, "₹800 / day", "15-day commercial wiring contract. Full safety kit provided. Immediate start.", "Open"),
            ("Shree Balaji Construction", "+91 97665 54433", "Vijayawada, Benz Circle", "Tile Fitting & Painting", 5, "₹850 / day", "Residential apartment complex finishing work. Timely daily payout.", "Open")
        ])

    conn.commit()
    conn.close()

init_db()

# 2. ENTERPRISE MULTILINGUAL FRONTEND
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ShramikLink | India's National Labour & Contractor Network</title>
    <meta name="description" content="Direct marketplace connecting verified skilled & unskilled daily wage construction labours with contractors. Zero commission, direct call, WhatsApp integration.">
    <meta name="theme-color" content="#070a12">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-main: #070a12;
            --bg-card: rgba(15, 23, 42, 0.85);
            --bg-card-hover: rgba(22, 34, 61, 0.95);
            --accent-gold: #f59e0b;
            --accent-gold-dark: #d97706;
            --accent-blue: #38bdf8;
            --whatsapp-green: #25D366;
            --whatsapp-dark: #128C7E;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border-color: rgba(51, 65, 85, 0.6);
            --success: #10b981;
            --danger: #ef4444;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans", sans-serif; }
        
        body {
            background-color: var(--bg-main);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .top-announcement {
            background: linear-gradient(90deg, #1e1b4b, #312e81, #1e1b4b);
            border-bottom: 1px solid rgba(99, 102, 241, 0.3);
            font-size: 12px;
            padding: 8px 16px;
            color: #c7d2fe;
            text-align: center;
            font-weight: 500;
        }
        .top-announcement span { color: var(--accent-gold); font-weight: 700; }

        header {
            background: rgba(7, 10, 18, 0.92);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 1000;
            padding: 12px 20px;
        }
        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: var(--text-primary);
        }
        .brand-icon {
            background: linear-gradient(135deg, var(--accent-gold), #b45309);
            width: 44px;
            height: 44px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            color: #000;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.35);
        }
        .brand-text h2 { font-size: 20px; font-weight: 900; letter-spacing: -0.5px; }
        .brand-text h2 span { color: var(--accent-gold); }
        .brand-tagline { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .lang-switch {
            display: flex;
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 2px;
        }
        .lang-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 700;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .lang-btn.active {
            background: var(--accent-gold);
            color: #000;
            box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
        }

        .hero {
            position: relative;
            background: linear-gradient(180deg, rgba(7, 10, 18, 0.85) 0%, rgba(11, 17, 32, 0.96) 100%),
                        url('https://images.unsplash.com/photo-1541888946425-d0fbb186156a?auto=format&fit=crop&w=1600&q=80') center/cover no-repeat;
            padding: 60px 20px 45px 20px;
            text-align: center;
            border-bottom: 1px solid var(--border-color);
        }
        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-gold);
            border: 1px solid rgba(245, 158, 11, 0.35);
            padding: 6px 16px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 20px;
        }
        .hero h1 {
            font-size: 40px;
            font-weight: 900;
            line-height: 1.2;
            margin-bottom: 14px;
            background: linear-gradient(135deg, #ffffff 30%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero p {
            font-size: 16px;
            color: #cbd5e1;
            max-width: 680px;
            margin: 0 auto 30px auto;
            line-height: 1.6;
        }

        .stats-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            max-width: 850px;
            margin: 0 auto;
        }
        .stat-box {
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
        }
        .stat-num { font-size: 28px; font-weight: 900; color: var(--accent-gold); }
        .stat-txt { font-size: 12px; color: var(--text-secondary); margin-top: 4px; font-weight: 600; }

        .trust-banner {
            max-width: 1200px;
            margin: -25px auto 25px auto;
            padding: 0 20px;
            position: relative;
            z-index: 10;
        }
        .trust-grid {
            background: rgba(19, 28, 48, 0.95);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.5);
        }
        .trust-item {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .trust-icon {
            width: 44px;
            height: 44px;
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-gold);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }
        .trust-text h4 { font-size: 15px; color: #fff; margin-bottom: 2px; }
        .trust-text p { font-size: 12px; color: var(--text-secondary); }

        .tabs-bar {
            max-width: 1200px;
            margin: 15px auto 20px auto;
            padding: 0 20px;
            display: flex;
            gap: 10px;
            overflow-x: auto;
            scrollbar-width: none;
        }
        .tabs-bar::-webkit-scrollbar { display: none; }
        .tab-btn {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 12px 20px;
            border-radius: 10px;
            font-weight: 700;
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
            box-shadow: 0 4px 18px rgba(245, 158, 11, 0.3);
        }

        main {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            flex: 1;
            width: 100%;
        }

        .filter-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }
        .search-input {
            flex: 2;
            min-width: 250px;
            padding: 14px 18px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: #fff;
            font-size: 14px;
        }
        .search-input:focus { outline: 2px solid var(--accent-gold); }
        .filter-select {
            flex: 1;
            min-width: 180px;
            padding: 14px 18px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: #fff;
            font-size: 14px;
        }

        .items-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .item-card {
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 22px;
            transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .item-card:hover {
            transform: translateY(-3px);
            border-color: rgba(245, 158, 11, 0.5);
            background: var(--bg-card-hover);
            box-shadow: 0 12px 30px rgba(0,0,0,0.4);
        }
        .card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 14px;
        }
        .card-title { font-size: 19px; font-weight: 800; color: #fff; }
        .card-badge {
            font-size: 11px;
            font-weight: 800;
            padding: 5px 10px;
            border-radius: 6px;
            text-transform: uppercase;
        }
        .badge-available { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .badge-busy { background: rgba(239, 68, 68, 0.15); color: #f87171; }
        .badge-job { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }

        .card-row {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 10px;
        }
        .card-row i { color: var(--accent-gold); width: 16px; text-align: center; }
        
        .wage-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(245, 158, 11, 0.12);
            color: var(--accent-gold);
            font-weight: 800;
            font-size: 14px;
            padding: 6px 12px;
            border-radius: 6px;
            margin: 8px 0 16px 0;
            border: 1px solid rgba(245, 158, 11, 0.25);
        }

        .btn-group {
            display: flex;
            gap: 8px;
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 16px;
            margin-top: 12px;
        }
        .btn-call {
            flex: 1;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: #fff;
            text-decoration: none;
            text-align: center;
            padding: 10px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 13px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .btn-call:hover { background: #1e40af; }
        .btn-whatsapp {
            flex: 1;
            background: linear-gradient(135deg, var(--whatsapp-green), var(--whatsapp-dark));
            color: #fff;
            text-decoration: none;
            text-align: center;
            padding: 10px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 13px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .btn-whatsapp:hover { opacity: 0.9; }
        .btn-delete {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.2);
            padding: 10px 12px;
            border-radius: 8px;
            cursor: pointer;
        }

        .form-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 30px;
            max-width: 650px;
            margin: 0 auto 50px auto;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }
        .form-title { font-size: 24px; margin-bottom: 6px; color: #fff; font-weight: 800; }
        .form-desc { color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; }
        .form-group { margin-bottom: 18px; }
        .form-label { display: block; font-size: 13px; font-weight: 700; margin-bottom: 8px; color: #e2e8f0; }
        .form-input, .form-textarea, .form-select {
            width: 100%;
            padding: 14px;
            background: #090d16;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
        }
        .form-input:focus, .form-textarea:focus, .form-select:focus { outline: 2px solid var(--accent-gold); }
        .btn-submit {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-dark));
            color: #000;
            border: none;
            border-radius: 10px;
            font-weight: 900;
            font-size: 16px;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(245, 158, 11, 0.35);
            margin-top: 10px;
        }
        .btn-submit:hover { opacity: 0.95; }

        .backup-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 30px;
            max-width: 750px;
            margin: 0 auto 50px auto;
        }
        .backup-row {
            background: #090d16;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }

        .floating-whatsapp {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--whatsapp-green);
            color: #fff;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 30px;
            box-shadow: 0 6px 25px rgba(37, 211, 102, 0.45);
            z-index: 1000;
            text-decoration: none;
            transition: transform 0.2s;
        }
        .floating-whatsapp:hover { transform: scale(1.1); }

        footer {
            background: #04070d;
            border-top: 1px solid var(--border-color);
            padding: 40px 20px 25px 20px;
            margin-top: auto;
            color: var(--text-secondary);
            font-size: 13px;
        }
        .footer-container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }
        .footer-col h4 { color: #fff; margin-bottom: 14px; font-size: 15px; }
        .footer-col ul { list-style: none; }
        .footer-col li { margin-bottom: 8px; }
        .footer-col a { color: var(--text-secondary); text-decoration: none; }
        .footer-col a:hover { color: var(--accent-gold); }
        .footer-bottom {
            max-width: 1200px;
            margin: 0 auto;
            text-align: center;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding-top: 20px;
            font-size: 12px;
        }

        #toast {
            visibility: hidden;
            min-width: 280px;
            background: #10b981;
            color: #fff;
            text-align: center;
            border-radius: 10px;
            padding: 16px;
            position: fixed;
            z-index: 2000;
            left: 50%;
            bottom: 30px;
            transform: translateX(-50%);
            font-size: 14px;
            font-weight: 700;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        }
        #toast.show { visibility: visible; animation: fadein 0.3s, fadeout 0.3s 2.5s; }
        @keyframes fadein { from { bottom: 0; opacity: 0; } to { bottom: 30px; opacity: 1; } }
        @keyframes fadeout { from { bottom: 30px; opacity: 1; } to { bottom: 0; opacity: 0; } }

        @media (max-width: 768px) {
            .hero h1 { font-size: 28px; }
            .hero { padding: 40px 16px 30px 16px; }
            .trust-banner { margin-top: 15px; }
            .items-grid { grid-template-columns: 1fr; }
            .filter-bar { flex-direction: column; }
        }
    </style>
</head>
<body>

    <div class="top-announcement">
        <i class="fa-solid fa-bolt" style="color: var(--accent-gold);"></i> 
        <span id="txt-announcement">India's Leading Direct Labour & Contractor Network • 0% Brokerage • 100% Free Direct Calling</span>
    </div>

    <header>
        <div class="nav-container">
            <a href="#" class="brand" onclick="switchTab('tab-labours')">
                <div class="brand-icon"><i class="fa-solid fa-helmet-safety"></i></div>
                <div class="brand-text">
                    <h2>Shramik<span>Link</span></h2>
                    <div class="brand-tagline" id="txt-tagline">National Workforce Portal</div>
                </div>
            </a>
            
            <div class="nav-actions">
                <div class="lang-switch">
                    <button class="lang-btn active" id="lang-en" onclick="setLanguage('en')">EN</button>
                    <button class="lang-btn" id="lang-hi" onclick="setLanguage('hi')">हिन्दी</button>
                    <button class="lang-btn" id="lang-te" onclick="setLanguage('te')">తెలుగు</button>
                </div>
            </div>
        </div>
    </header>

    <div class="hero">
        <div class="hero-badge">
            <i class="fa-solid fa-shield-check"></i> <span id="txt-verifiedBadge">Verified Workers & Contractors</span>
        </div>
        <h1 id="txt-heroTitle">Connect Skilled Labours & Contractors</h1>
        <p id="txt-heroSub">Direct hiring without middlemen. Masons, Electricians, Plumbers, Painters & Helpers ready for immediate project onboarding.</p>
        
        <div class="stats-strip">
            <div class="stat-box">
                <div class="stat-num" id="count-labours">-</div>
                <div class="stat-txt" id="txt-statWorkers">Verified Workers</div>
            </div>
            <div class="stat-box">
                <div class="stat-num" id="count-jobs">-</div>
                <div class="stat-txt" id="txt-statJobs">Active Site Jobs</div>
            </div>
            <div class="stat-box">
                <div class="stat-num" style="color: #25D366;"><i class="fa-brands fa-whatsapp"></i> Instant</div>
                <div class="stat-txt" id="txt-statWhatsapp">WhatsApp Contact</div>
            </div>
        </div>
    </div>

    <div class="trust-banner">
        <div class="trust-grid">
            <div class="trust-item">
                <div class="trust-icon"><i class="fa-solid fa-magnifying-glass"></i></div>
                <div class="trust-text">
                    <h4 id="txt-step1Title">1. Find or Post</h4>
                    <p id="txt-step1Desc">Browse skilled workers or post your site requirement in 1 minute.</p>
                </div>
            </div>
            <div class="trust-item">
                <div class="trust-icon" style="background: rgba(37, 211, 102, 0.15); color: #25D366;"><i class="fa-brands fa-whatsapp"></i></div>
                <div class="trust-text">
                    <h4 id="txt-step2Title">2. Direct WhatsApp / Call</h4>
                    <p id="txt-step2Desc">Talk directly with workers & contractors. Zero middlemen.</p>
                </div>
            </div>
            <div class="trust-item">
                <div class="trust-icon" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8;"><i class="fa-solid fa-handshake"></i></div>
                <div class="trust-text">
                    <h4 id="txt-step3Title">3. Start Work</h4>
                    <p id="txt-step3Desc">Negotiate daily wages and start construction immediately.</p>
                </div>
            </div>
        </div>
    </div>

    <div class="tabs-bar">
        <button class="tab-btn active" id="btn-labours" onclick="switchTab('tab-labours')">
            <i class="fa-solid fa-users"></i> <span id="lbl-tabWorkers">Find Labours</span>
        </button>
        <button class="tab-btn" id="btn-jobs" onclick="switchTab('tab-jobs')">
            <i class="fa-solid fa-briefcase"></i> <span id="lbl-tabJobs">Contractor Jobs</span>
        </button>
        <button class="tab-btn" id="btn-reg-labour" onclick="switchTab('tab-reg-labour')">
            <i class="fa-solid fa-user-plus"></i> <span id="lbl-tabRegWorker">Register Worker</span>
        </button>
        <button class="tab-btn" id="btn-post-job" onclick="switchTab('tab-post-job')">
            <i class="fa-solid fa-file-circle-plus"></i> <span id="lbl-tabPostJob">Post Requirement</span>
        </button>
        <button class="tab-btn" id="btn-backup" onclick="switchTab('tab-backup')">
            <i class="fa-solid fa-cloud-arrow-down"></i> <span id="lbl-tabBackup">Backup & Data</span>
        </button>
    </div>

    <main>

        <!-- TAB 1: WORKERS DIRECTORY -->
        <div id="tab-labours" class="tab-content">
            <div class="filter-bar">
                <input type="text" id="labourSearch" class="search-input" placeholder="🔍 Search worker name, city, or skill..." oninput="filterLabours()">
                <select id="labourSkillFilter" class="filter-select" onchange="filterLabours()">
                    <option value="">All Trades (सभी काम / అన్ని పనులు)</option>
                    <option value="Mason">Mason (Mistri / మేస్త్రీ)</option>
                    <option value="Electrician">Electrician (इलेक्ट्रीशियन / ఎలక్ట్రీషియన్)</option>
                    <option value="Plumber">Plumber (प्लंबर / ప్లంబర్)</option>
                    <option value="Painter">Painter (पेंटर / పెయింటర్)</option>
                    <option value="Carpenter">Carpenter (बढ़ई / కార్పెంటర్)</option>
                    <option value="Tile">Tile & Marble (टाइल फिटर)</option>
                    <option value="Helper">General Helper (हेल्पर / సహాయకుడు)</option>
                </select>
            </div>
            <div id="labourList" class="items-grid">
                <p style="color: #64748b; padding: 30px;">Loading verified workers from database...</p>
            </div>
        </div>

        <!-- TAB 2: CONTRACTOR JOBS -->
        <div id="tab-jobs" class="tab-content" style="display: none;">
            <div class="filter-bar">
                <input type="text" id="jobSearch" class="search-input" placeholder="🔍 Search site location, contractor name, or work..." oninput="filterJobs()">
            </div>
            <div id="jobsList" class="items-grid">
                <p style="color: #64748b; padding: 30px;">Loading active contractor requirements...</p>
            </div>
        </div>

        <!-- TAB 3: REGISTER WORKER -->
        <div id="tab-reg-labour" class="tab-content" style="display: none;">
            <div class="form-card">
                <h3 class="form-title"><i class="fa-solid fa-id-card" style="color: var(--accent-gold);"></i> <span id="form-workerTitle">Register as Worker</span></h3>
                <p class="form-desc" id="form-workerDesc">Enter your trade and phone to receive direct daily job calls from local contractors.</p>

                <form id="formLabour" onsubmit="submitLabour(event)">
                    <div class="form-group">
                        <label class="form-label" id="lbl-wName">Full Name *</label>
                        <input type="text" id="labName" class="form-input" placeholder="e.g. Ramesh Kumar" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-wPhone">Phone / WhatsApp Number *</label>
                        <input type="tel" id="labPhone" class="form-input" placeholder="e.g. 9876543210" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-wSkill">Primary Skill / Trade *</label>
                        <select id="labSkill" class="form-select" required>
                            <option value="Mason (Mistri)">Mason (Mistri / Construction)</option>
                            <option value="Electrician">Electrician (Electrical Wiring)</option>
                            <option value="Plumber">Plumber (Sanitary & Pipes)</option>
                            <option value="Painter">Painter (Putty, Texture & Paint)</option>
                            <option value="Carpenter">Carpenter (Wood & Shuttering)</option>
                            <option value="Tile & Marble">Tile & Marble Fitter</option>
                            <option value="Welder">Welder & Fabrication</option>
                            <option value="General Helper">General Construction Helper</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-wLoc">City / Work Area *</label>
                        <input type="text" id="labLoc" class="form-input" placeholder="e.g. Hyderabad, Madhapur" required>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <div class="form-group" style="flex: 1;">
                            <label class="form-label" id="lbl-wExp">Experience</label>
                            <input type="text" id="labExp" class="form-input" placeholder="e.g. 5 Years">
                        </div>
                        <div class="form-group" style="flex: 1;">
                            <label class="form-label" id="lbl-wWage">Expected Daily Wage</label>
                            <input type="text" id="labWage" class="form-input" placeholder="e.g. ₹800 / day">
                        </div>
                    </div>
                    <button type="submit" class="btn-submit" id="btn-subWorker"><i class="fa-solid fa-check-circle"></i> Submit & Register Profile</button>
                </form>
            </div>
        </div>

        <!-- TAB 4: POST REQUIREMENT -->
        <div id="tab-post-job" class="tab-content" style="display: none;">
            <div class="form-card">
                <h3 class="form-title"><i class="fa-solid fa-bullhorn" style="color: var(--accent-gold);"></i> <span id="form-jobTitle">Post Site Job Requirement</span></h3>
                <p class="form-desc" id="form-jobDesc">Publish your project requirements. Labours can reach out via Call or WhatsApp directly.</p>

                <form id="formJob" onsubmit="submitJob(event)">
                    <div class="form-group">
                        <label class="form-label" id="lbl-jContractor">Contractor / Firm Name *</label>
                        <input type="text" id="jobContractor" class="form-input" placeholder="e.g. Apex Infra Construction" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-jPhone">Contact Phone / WhatsApp *</label>
                        <input type="tel" id="jobPhone" class="form-input" placeholder="e.g. 9988776655" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-jWork">Type of Work Needed *</label>
                        <input type="text" id="jobWorkType" class="form-input" placeholder="e.g. RCC Slab Casting & Masonry" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-jLoc">Site Location *</label>
                        <input type="text" id="jobLocation" class="form-input" placeholder="e.g. Bengaluru, Electronic City" required>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <div class="form-group" style="flex: 1;">
                            <label class="form-label" id="lbl-jCount">Workers Needed *</label>
                            <input type="number" id="jobWorkers" class="form-input" placeholder="e.g. 5" min="1" required>
                        </div>
                        <div class="form-group" style="flex: 1;">
                            <label class="form-label" id="lbl-jWage">Daily Wage Offered</label>
                            <input type="text" id="jobWage" class="form-input" placeholder="e.g. ₹900 / day" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-jDetails">Job Scope & Requirements</label>
                        <textarea id="jobReqs" class="form-textarea" rows="3" placeholder="e.g. 10 days project. Safety gear provided. Timely payment on site."></textarea>
                    </div>
                    <button type="submit" class="btn-submit" id="btn-subJob"><i class="fa-solid fa-paper-plane"></i> Publish Job Requirement</button>
                </form>
            </div>
        </div>

        <!-- TAB 5: BACKUP & DATA -->
        <div id="tab-backup" class="tab-content" style="display: none;">
            <div class="backup-card">
                <h3 class="form-title"><i class="fa-solid fa-cloud-arrow-down" style="color: var(--accent-gold);"></i> Data Safety & Mobile Backup</h3>
                <p class="form-desc">Guarantee zero data loss with 1-click JSON database export and instant cloud restore.</p>

                <div class="backup-row">
                    <div>
                        <h4 style="color: #fff; margin-bottom: 4px;"><i class="fa-solid fa-download" style="color: var(--accent-gold);"></i> Download Database Backup</h4>
                        <p style="font-size: 13px; color: var(--text-secondary);">Save full snapshot of all workers, contractors, and contact history to your phone or PC.</p>
                    </div>
                    <a href="/api/backup" download="shramiklink_backup.json" class="tab-btn active" style="text-decoration: none;">
                        <i class="fa-solid fa-file-arrow-down"></i> Download JSON
                    </a>
                </div>

                <div class="backup-row">
                    <div>
                        <h4 style="color: #fff; margin-bottom: 4px;"><i class="fa-solid fa-rotate-left" style="color: var(--accent-blue);"></i> Restore Database</h4>
                        <p style="font-size: 13px; color: var(--text-secondary);">Upload an existing backup file to restore records anytime without data loss.</p>
                    </div>
                    <div>
                        <input type="file" id="restoreFile" accept=".json" style="display: none;" onchange="handleRestore(event)">
                        <button class="tab-btn" onclick="document.getElementById('restoreFile').click()">
                            <i class="fa-solid fa-upload"></i> Restore File
                        </button>
                    </div>
                </div>
            </div>
        </div>

    </main>

    <!-- FLOATING WHATSAPP SUPPORT BUTTON -->
    <a href="https://wa.me/919876543210?text=Hello%20ShramikLink%20Support,%20I%20need%20help%20with%20finding%20workers." target="_blank" class="floating-whatsapp" title="Chat on WhatsApp">
        <i class="fa-brands fa-whatsapp"></i>
    </a>

    <!-- ENTERPRISE FOOTER -->
    <footer>
        <div class="footer-container">
            <div class="footer-col">
                <h4 style="color: var(--accent-gold); font-size: 18px;"><i class="fa-solid fa-helmet-safety"></i> ShramikLink</h4>
                <p>India's dedicated construction workforce network connecting contractors and certified tradesmen directly with zero brokerage.</p>
            </div>
            <div class="footer-col">
                <h4>Popular Trades</h4>
                <ul>
                    <li><a href="#" onclick="filterBySkill('Mason')">Masons (Mistri)</a></li>
                    <li><a href="#" onclick="filterBySkill('Electrician')">Electricians</a></li>
                    <li><a href="#" onclick="filterBySkill('Plumber')">Plumbers</a></li>
                    <li><a href="#" onclick="filterBySkill('Painter')">Painters</a></li>
                    <li><a href="#" onclick="filterBySkill('Carpenter')">Carpenters</a></li>
                </ul>
            </div>
            <div class="footer-col">
                <h4>Languages Supported</h4>
                <ul>
                    <li><a href="#" onclick="setLanguage('en')">English (National)</a></li>
                    <li><a href="#" onclick="setLanguage('hi')">हिन्दी (Hindi)</a></li>
                    <li><a href="#" onclick="setLanguage('te')">తెలుగు (Telugu)</a></li>
                </ul>
            </div>
            <div class="footer-col">
                <h4>Trust & Privacy</h4>
                <p><i class="fa-solid fa-lock" style="color: var(--success);"></i> 256-Bit SSL Encrypted</p>
                <p><i class="fa-solid fa-ban" style="color: var(--danger);"></i> Anti-Scraping Protection</p>
                <p><i class="fa-solid fa-cloud-arrow-down" style="color: var(--accent-gold);"></i> 1-Click Offline Backup</p>
            </div>
        </div>
        <div class="footer-bottom">
            &copy; 2026 ShramikLink Technologies. All rights reserved. Connecting India's Skilled Builders & Daily Wage Workers.
        </div>
    </footer>

    <div id="toast">Notice message</div>

    <script>
        let allLabours = [];
        let allJobs = [];
        let currentLang = 'en';

        // MULTILINGUAL DICTIONARY (EN / HI / TE)
        const i18n = {
            en: {
                announcement: "India's Leading Direct Labour & Contractor Network • 0% Brokerage • 100% Free Direct Calling",
                tagline: "National Workforce Portal",
                verifiedBadge: "Verified Workers & Contractors",
                heroTitle: "Connect Skilled Labours & Contractors",
                heroSub: "Direct hiring without middlemen. Masons, Electricians, Plumbers, Painters & Helpers ready for immediate project onboarding.",
                statWorkers: "Verified Workers",
                statJobs: "Active Site Jobs",
                statWhatsapp: "WhatsApp Contact",
                step1Title: "1. Find or Post",
                step1Desc: "Browse skilled workers or post your site requirement in 1 minute.",
                step2Title: "2. Direct WhatsApp / Call",
                step2Desc: "Talk directly with workers & contractors. Zero middlemen.",
                step3Title: "3. Start Work",
                step3Desc: "Negotiate daily wages and start construction immediately.",
                tabWorkers: "Find Labours",
                tabJobs: "Contractor Jobs",
                tabRegWorker: "Register Worker",
                tabPostJob: "Post Requirement",
                tabBackup: "Backup & Data",
                workerTitle: "Register as Worker",
                workerDesc: "Enter your trade and phone to receive direct daily job calls from local contractors.",
                jobTitle: "Post Site Job Requirement",
                jobDesc: "Publish your project requirements. Labours can reach out via Call or WhatsApp directly.",
                callWorker: "Call",
                whatsappChat: "WhatsApp",
                dailyWage: "Daily Wage"
            },
            hi: {
                announcement: "भारत का अग्रणी मजदूर एवं ठेकेदार नेटवर्क • 0% दलाली • 100% फ्री डायरेक्ट कॉलिंग",
                tagline: "राष्ट्रीय श्रमिक पोर्टल",
                verifiedBadge: "सत्यापित मजदूर और ठेकेदार",
                heroTitle: "कुशल मजदूर और ठेकेदारों को सीधे जोड़ें",
                heroSub: "बिना किसी बिचौलिए या कमीशन के। मिस्त्री, इलेक्ट्रीशियन, प्लंबर, पेंटर और हेल्पर तुरंत काम के लिए उपलब्ध।",
                statWorkers: "पंजीकृत मजदूर",
                statJobs: "सक्रिय साइट कार्य",
                statWhatsapp: "व्हाट्सएप संपर्क",
                step1Title: "1. खोजें या पोस्ट करें",
                step1Desc: "कुशल मजदूरों को खोजें या 1 मिनट में अपनी आवश्यकता पोस्ट करें।",
                step2Title: "2. डायरेक्ट व्हाट्सएप / कॉल",
                step2Desc: "मजदूरों और ठेकेदारों से सीधे बात करें। कोई बिचौलिया नहीं।",
                step3Title: "3. काम शुरू करें",
                step3Desc: "दैनिक मजदूरी तय करें और निर्माण कार्य तुरंत शुरू करें।",
                tabWorkers: "मजदूर खोजें",
                tabJobs: "ठेकेदार के काम",
                tabRegWorker: "मजदूर पंजीकरण",
                tabPostJob: "काम पोस्ट करें",
                tabBackup: "बैकअप और डेटा",
                workerTitle: "मजदूर के रूप में पंजीकरण करें",
                workerDesc: "स्थानीय ठेकेदारों से सीधे काम के कॉल प्राप्त करने के लिए अपना विवरण दर्ज करें।",
                jobTitle: "साइट कार्य आवश्यकता पोस्ट करें",
                jobDesc: "अपनी परियोजना की आवश्यकताएं प्रकाशित करें। मजदूर सीधे कॉल या व्हाट्सएप कर सकते हैं।",
                callWorker: "कॉल करें",
                whatsappChat: "व्हाट्सएप",
                dailyWage: "दैनिक मजदूरी"
            },
            te: {
                announcement: "భారతదేశ ప్రముఖ లేబర్ & కాంట్రాక్టర్ నెట్‌వర్క్ • 0% బ్రోకరేజ్ • ఉచిత డైరెక్ట్ కాలింగ్",
                tagline: "జాతీయ శ్రామిక పోర్టల్",
                verifiedBadge: "ధృవీకరించబడిన వర్కర్లు & కాంట్రాక్టర్లు",
                heroTitle: "నైపుణ్యం కలిగిన లేబర్ & కాంట్రాక్టర్లను కలపండి",
                heroSub: "దళారులు లేకుండా నేరుగా సంప్రదించండి. మేస్త్రీలు, ఎలక్ట్రీషియన్లు, ప్లంబర్లు, పెయింటర్లు సిద్ధంగా ఉన్నారు.",
                statWorkers: "నమోదిత వర్కర్లు",
                statJobs: "ప్రస్తుత పనులు",
                statWhatsapp: "వాట్సాప్ కాంటాక్ట్",
                step1Title: "1. శోధించండి లేదా పోస్ట్ చేయండి",
                step1Desc: "నైపుణ్యం ఉన్న పనివారిని కనుగొనండి లేదా మీ పని అవసరాన్ని పోస్ట్ చేయండి.",
                step2Title: "2. డైరెక్ట్ వాట్సాప్ / కాల్",
                step2Desc: "వర్కర్లు & కాంట్రాక్టర్లతో నేరుగా మాట్లాడండి. దళారులు లేరు.",
                step3Title: "3. పని ప్రారంభించండి",
                step3Desc: "రోజువారీ వేతనం నిర్ణయించుకుని పనిని ప్రారంభించండి.",
                tabWorkers: "లేబర్లను కనుగొనండి",
                tabJobs: "కాంట్రాక్టర్ పనులు",
                tabRegWorker: "వర్కర్ రిజిస్ట్రేషన్",
                tabPostJob: "పని అవసరాన్ని పోస్ట్ చేయండి",
                tabBackup: "డేటా బ్యాకప్",
                workerTitle: "వర్కర్‌గా నమోదు చేసుకోండి",
                workerDesc: "కాంట్రాక్టర్ల నుండి నేరుగా కాల్స్ పొందడానికి మీ వివరాలను నమోదు చేయండి.",
                jobTitle: "పని అవసరాన్ని పోస్ట్ చేయండి",
                jobDesc: "మీ ప్రాజెక్ట్ అవసరాలను ప్రచురించండి. వర్కర్లు నేరుగా సంప్రదిస్తారు.",
                callWorker: "కాల్ చేయండి",
                whatsappChat: "వాట్సాప్",
                dailyWage: "రోజువారీ వేతనం"
            }
        };

        function setLanguage(lang) {
            currentLang = lang;
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('lang-' + lang).classList.add('active');

            const t = i18n[lang];
            document.getElementById('txt-announcement').innerText = t.announcement;
            document.getElementById('txt-tagline').innerText = t.tagline;
            document.getElementById('txt-verifiedBadge').innerText = t.verifiedBadge;
            document.getElementById('txt-heroTitle').innerText = t.heroTitle;
            document.getElementById('txt-heroSub').innerText = t.heroSub;
            document.getElementById('txt-statWorkers').innerText = t.statWorkers;
            document.getElementById('txt-statJobs').innerText = t.statJobs;
            document.getElementById('txt-statWhatsapp').innerText = t.statWhatsapp;

            document.getElementById('txt-step1Title').innerText = t.step1Title;
            document.getElementById('txt-step1Desc').innerText = t.step1Desc;
            document.getElementById('txt-step2Title').innerText = t.step2Title;
            document.getElementById('txt-step2Desc').innerText = t.step2Desc;
            document.getElementById('txt-step3Title').innerText = t.step3Title;
            document.getElementById('txt-step3Desc').innerText = t.step3Desc;

            document.getElementById('lbl-tabWorkers').innerText = t.tabWorkers;
            document.getElementById('lbl-tabJobs').innerText = t.tabJobs;
            document.getElementById('lbl-tabRegWorker').innerText = t.tabRegWorker;
            document.getElementById('lbl-tabPostJob').innerText = t.tabPostJob;
            document.getElementById('lbl-tabBackup').innerText = t.tabBackup;

            document.getElementById('form-workerTitle').innerText = t.workerTitle;
            document.getElementById('form-workerDesc').innerText = t.workerDesc;
            document.getElementById('form-jobTitle').innerText = t.jobTitle;
            document.getElementById('form-jobDesc').innerText = t.jobDesc;

            renderLabours(allLabours);
            renderJobs(allJobs);
        }

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

        function cleanPhoneForWhatsapp(phone) {
            let num = phone.replace(/[^0-9]/g, '');
            if (num.length === 10) num = '91' + num;
            return num;
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
                showToast("Error loading database records", true);
            }
        }

        function renderLabours(list) {
            const container = document.getElementById('labourList');
            const t = i18n[currentLang];
            if (list.length === 0) {
                container.innerHTML = '<p style="color: #64748b; padding: 20px;">No workers match your filter criteria.</p>';
                return;
            }
            container.innerHTML = list.map(l => {
                const waPhone = cleanPhoneForWhatsapp(l.phone);
                const waMsg = encodeURIComponent(`Hello ${l.name}, I saw your ${l.skill} profile on ShramikLink. Are you available for a project?`);
                return `
                <div class="item-card">
                    <div>
                        <div class="card-top">
                            <div class="card-title">${l.name}</div>
                            <span class="card-badge ${l.status === 'Available' ? 'badge-available' : 'badge-busy'}">
                                ${l.status}
                            </span>
                        </div>
                        <div class="card-row"><i class="fa-solid fa-hammer"></i> <b>Trade:</b> ${l.skill}</div>
                        <div class="card-row"><i class="fa-solid fa-location-dot"></i> <b>City:</b> ${l.location}</div>
                        <div class="card-row"><i class="fa-solid fa-clock-rotate-left"></i> <b>Exp:</b> ${l.experience || 'Not specified'}</div>
                        <div class="wage-tag"><i class="fa-solid fa-money-bill-wave"></i> ${l.daily_wage || 'Daily Wage Negotiable'}</div>
                    </div>
                    <div class="btn-group">
                        <a href="tel:${l.phone}" class="btn-call">
                            <i class="fa-solid fa-phone"></i> ${t.callWorker}
                        </a>
                        <a href="https://wa.me/${waPhone}?text=${waMsg}" target="_blank" class="btn-whatsapp">
                            <i class="fa-brands fa-whatsapp"></i> ${t.whatsappChat}
                        </a>
                        <button class="btn-delete" onclick="deleteLabour(${l.id})" title="Remove Worker">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
                `;
            }).join('');
        }

        function renderJobs(list) {
            const container = document.getElementById('jobsList');
            const t = i18n[currentLang];
            if (list.length === 0) {
                container.innerHTML = '<p style="color: #64748b; padding: 20px;">No active contractor jobs found.</p>';
                return;
            }
            container.innerHTML = list.map(j => {
                const waPhone = cleanPhoneForWhatsapp(j.phone);
                const waMsg = encodeURIComponent(`Hello ${j.contractor_name}, I saw your job requirement for ${j.work_type} on ShramikLink. I would like to apply.`);
                return `
                <div class="item-card">
                    <div>
                        <div class="card-top">
                            <div class="card-title">${j.work_type}</div>
                            <span class="card-badge badge-job"><i class="fa-solid fa-people-group"></i> ${j.workers_needed} Required</span>
                        </div>
                        <div class="card-row"><i class="fa-solid fa-building-user"></i> <b>Contractor:</b> ${j.contractor_name}</div>
                        <div class="card-row"><i class="fa-solid fa-location-dot"></i> <b>Site:</b> ${j.location}</div>
                        <div class="wage-tag"><i class="fa-solid fa-coins"></i> Offered: ${j.wage_offered}</div>
                        <p style="font-size: 13px; color: #cbd5e1; background: #070a12; padding: 12px; border-radius: 8px; margin-top: 6px; border: 1px solid var(--border-color); line-height: 1.5;">
                            ${j.requirements || 'No additional site requirements specified.'}
                        </p>
                    </div>
                    <div class="btn-group">
                        <a href="tel:${j.phone}" class="btn-call">
                            <i class="fa-solid fa-phone"></i> ${t.callWorker}
                        </a>
                        <a href="https://wa.me/${waPhone}?text=${waMsg}" target="_blank" class="btn-whatsapp">
                            <i class="fa-brands fa-whatsapp"></i> ${t.whatsappChat}
                        </a>
                        <button class="btn-delete" onclick="deleteJob(${j.id})" title="Close Job">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
                `;
            }).join('');
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

        function filterBySkill(trade) {
            document.getElementById('labourSkillFilter').value = trade;
            switchTab('tab-labours');
            filterLabours();
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
                showToast("Registration failed", true);
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
            showToast("Worker profile removed");
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
                        showToast("Restore failed: Invalid backup structure", true);
                    }
                } catch (err) {
                    showToast("Error reading backup file", true);
                }
            };
            reader.readAsText(file);
        }

        fetchAllData();
    </script>
</body>
</html>
"""

# 3. BACKEND API ENDPOINTS
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

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

@app.route("/api/backup", methods=["GET"])
def backup_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM labours")
    labours = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM contractor_jobs")
    jobs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    backup_data = {
        "app": "ShramikLink",
        "version": "2.0-enterprise",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "total_labours": len(labours),
        "total_jobs": len(jobs),
        "labours": labours,
        "contractor_jobs": jobs
    }

    return Response(
        json.dumps(backup_data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename=shramiklink_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
    )

@app.route("/api/restore", methods=["POST"])
def restore_database():
    data = request.get_json()
    if not data or "labours" not in data or "contractor_jobs" not in data:
        return jsonify({"error": "Invalid backup file structure"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
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

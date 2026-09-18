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
ADMIN_PIN = "9999"  # Admin security password

# ─────────────────────────────────────────────────────────────
# 1. DATABASE SETUP & AUTOMATIC SCHEMA MIGRATION
# ─────────────────────────────────────────────────────────────
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
            phone TEXT NOT NULL UNIQUE,
            location TEXT NOT NULL,
            skill TEXT NOT NULL,
            experience TEXT NOT NULL,
            daily_wage TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            assigned_contractor TEXT DEFAULT '',
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
            photo_data TEXT DEFAULT '',
            status TEXT DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Schema migration safety
    cursor.execute("PRAGMA table_info(labours)")
    labour_cols = [c[1] for c in cursor.fetchall()]
    if "assigned_contractor" not in labour_cols:
        cursor.execute("ALTER TABLE labours ADD COLUMN assigned_contractor TEXT DEFAULT ''")

    cursor.execute("PRAGMA table_info(contractor_jobs)")
    job_cols = [c[1] for c in cursor.fetchall()]
    if "photo_data" not in job_cols:
        cursor.execute("ALTER TABLE contractor_jobs ADD COLUMN photo_data TEXT DEFAULT ''")

    # Seed demo data if database is empty
    cursor.execute("SELECT COUNT(*) FROM labours")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO labours (name, phone, location, skill, experience, daily_wage, status, assigned_contractor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Ramesh Kumar (రమేష్)", "+91 98765 43210", "Hyderabad, Gachibowli", "Mason (Mistri)", "8 Years", "₹850 / day", "Busy", "Apex Infra Builders"),
            ("Sunil Verma (सुनील)", "+91 98123 45678", "Delhi NCR, Noida", "Electrician", "5 Years", "₹750 / day", "Available", ""),
            ("Mohammad Arif", "+91 97234 56789", "Bengaluru, Whitefield", "Plumber", "6 Years", "₹800 / day", "Available", ""),
            ("Suresh Reddy (సురేష్)", "+91 99123 44556", "Visakhapatnam, Madhurawada", "Tile & Marble", "7 Years", "₹900 / day", "Available", ""),
            ("Vikram Singh (विक्रम)", "+91 96345 67890", "Pune, Hinjewadi", "Painter", "4 Years", "₹650 / day", "Available", ""),
            ("Santosh Yadav", "+91 94567 89012", "Lucknow, Gomti Nagar", "General Helper", "2 Years", "₹500 / day", "Available", "")
        ])

    cursor.execute("SELECT COUNT(*) FROM contractor_jobs")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO contractor_jobs (contractor_name, phone, location, work_type, workers_needed, wage_offered, requirements, photo_data, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Apex Infra Builders", "+91 99887 76655", "Hyderabad, Hitec City", "Masonry & RCC Slab", 6, "₹900 / day", "Need 6 experienced masons for high-rise commercial slab work. On-site accommodation and meals provided.", "", "Open"),
            ("Home Renovation - Amit", "+91 98776 65544", "Delhi, Dwarka Sector 12", "Bathroom Tile Leakage Repair", 2, "₹850 / day", "Tile leakage in 2 bathrooms. Need master plumber and tile fitter. Immediate work.", "", "Open")
        ])

    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────────────────────────
# 2. FRONTEND APPLICATION WITH ROLE-BASED ENTRY GATE
# ─────────────────────────────────────────────────────────────
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ShramikLink | National Labour & Contractor Network</title>
    <meta name="theme-color" content="#070a12">
    <meta name="apple-mobile-web-app-capable" content="yes">
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
            --busy-orange: #fb923c;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans", sans-serif; }
        body { background-color: var(--bg-main); color: var(--text-primary); min-height: 100vh; display: flex; flex-direction: column; }

        /* ─────────────────────────────────────────────────────────────
           FULL-SCREEN ENTRY GATE (USER VS ADMIN SELECTION)
        ───────────────────────────────────────────────────────────── */
        #roleGateOverlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(180deg, rgba(7, 10, 18, 0.94) 0%, rgba(11, 17, 32, 0.98) 100%),
                        url('https://images.unsplash.com/photo-1541888946425-d0fbb186156a?auto=format&fit=crop&w=1600&q=80') center/cover no-repeat;
            z-index: 20000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .gate-card {
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            max-width: 520px;
            width: 100%;
            padding: 40px 30px;
            text-align: center;
            box-shadow: 0 25px 60px rgba(0,0,0,0.8);
        }
        .gate-icon {
            width: 64px;
            height: 64px;
            background: linear-gradient(135deg, var(--accent-gold), #b45309);
            color: #000;
            border-radius: 16px;
            font-size: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px auto;
            box-shadow: 0 8px 25px rgba(245, 158, 11, 0.4);
        }
        .gate-title { font-size: 26px; font-weight: 900; margin-bottom: 6px; }
        .gate-title span { color: var(--accent-gold); }
        .gate-subtitle { font-size: 14px; color: var(--text-secondary); margin-bottom: 30px; }
        
        .role-options {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .role-btn {
            background: #090d16;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            cursor: pointer;
            text-align: left;
            display: flex;
            align-items: center;
            gap: 18px;
            transition: all 0.2s;
        }
        .role-btn:hover {
            border-color: var(--accent-gold);
            transform: translateY(-2px);
            background: #111a2e;
        }
        .role-icon-box {
            width: 48px;
            height: 48px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }
        .role-info h3 { font-size: 17px; color: #fff; margin-bottom: 4px; }
        .role-info p { font-size: 12px; color: var(--text-secondary); line-height: 1.4; }

        /* ADMIN PASSWORD MODAL / FORM */
        #adminPinView {
            display: none;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            text-align: center;
        }
        .pin-mask-input {
            width: 180px;
            letter-spacing: 12px;
            font-size: 28px;
            text-align: center;
            padding: 12px;
            background: #070a12;
            border: 2px solid var(--accent-gold);
            border-radius: 10px;
            color: #fff;
            margin-bottom: 16px;
        }
        .pin-mask-input:focus { outline: none; box-shadow: 0 0 15px rgba(245, 158, 11, 0.4); }

        /* ─────────────────────────────────────────────────────────────
           MAIN PORTAL STYLING
        ───────────────────────────────────────────────────────────── */
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
            background: rgba(7, 10, 18, 0.94);
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

        .nav-actions { display: flex; align-items: center; gap: 12px; }

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

        .admin-badge {
            display: none;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 700;
        }

        .hero {
            position: relative;
            background: linear-gradient(180deg, rgba(7, 10, 18, 0.88) 0%, rgba(11, 17, 32, 0.97) 100%),
                        url('https://images.unsplash.com/photo-1541888946425-d0fbb186156a?auto=format&fit=crop&w=1600&q=80') center/cover no-repeat;
            padding: 55px 20px 40px 20px;
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
            margin-bottom: 16px;
        }
        .hero h1 {
            font-size: 38px;
            font-weight: 900;
            line-height: 1.2;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #ffffff 30%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero p {
            font-size: 15px;
            color: #cbd5e1;
            max-width: 680px;
            margin: 0 auto 24px auto;
            line-height: 1.6;
        }

        .stats-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 14px;
            max-width: 850px;
            margin: 0 auto;
        }
        .stat-box {
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px;
        }
        .stat-num { font-size: 26px; font-weight: 900; color: var(--accent-gold); }
        .stat-txt { font-size: 12px; color: var(--text-secondary); margin-top: 4px; font-weight: 600; }

        .tabs-bar {
            max-width: 1200px;
            margin: 20px auto 16px auto;
            padding: 0 20px;
            display: flex;
            gap: 8px;
            overflow-x: auto;
            scrollbar-width: none;
        }
        .tabs-bar::-webkit-scrollbar { display: none; }
        .tab-btn {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 12px 18px;
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

        /* ADMIN TAB: HIDDEN FOR USERS BY DEFAULT */
        #btn-backup { display: none; }

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
            margin-bottom: 12px;
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
        .badge-busy { background: rgba(251, 146, 60, 0.18); color: var(--busy-orange); border: 1px solid rgba(251, 146, 60, 0.35); }
        .badge-job { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }

        .contractor-tag {
            display: block;
            background: rgba(251, 146, 60, 0.1);
            color: #fed7aa;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 10px;
            border-left: 3px solid var(--busy-orange);
        }

        .card-row {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        .card-row i { color: var(--accent-gold); width: 16px; text-align: center; }

        .wage-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(245, 158, 11, 0.12);
            color: var(--accent-gold);
            font-weight: 800;
            font-size: 13px;
            padding: 5px 10px;
            border-radius: 6px;
            margin: 6px 0 12px 0;
            border: 1px solid rgba(245, 158, 11, 0.25);
        }

        .job-photo-preview {
            width: 100%;
            height: 160px;
            object-fit: cover;
            border-radius: 8px;
            margin: 10px 0;
            border: 1px solid var(--border-color);
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .job-photo-preview:hover { opacity: 0.9; }

        .btn-group {
            display: flex;
            gap: 8px;
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 14px;
            margin-top: 12px;
            flex-wrap: wrap;
        }
        .btn-call {
            flex: 1;
            min-width: 100px;
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
            min-width: 110px;
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

        .btn-hire {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-gold);
            border: 1px solid rgba(245, 158, 11, 0.35);
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            margin-top: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .btn-hire:hover { background: rgba(245, 158, 11, 0.25); }

        .btn-release {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            margin-top: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }

        /* ADMIN DELETE BUTTONS: TOTALLY HIDDEN UNLESS ADMIN MODE IS ACTIVE */
        .btn-admin-delete {
            display: none;
            background: rgba(239, 68, 68, 0.12);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 8px 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            width: 100%;
            margin-top: 6px;
            text-align: center;
        }
        body.is-admin .btn-admin-delete { display: block; }
        body.is-admin .admin-badge { display: flex; }
        body.is-admin #btn-backup { display: flex; }

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

        .photo-preview-box {
            display: none;
            margin-top: 10px;
            border-radius: 8px;
            max-height: 200px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }
        .photo-preview-box img { width: 100%; height: 180px; object-fit: cover; }

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

        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 5000;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .modal-content {
            background: #131c2e;
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 24px;
            max-width: 480px;
            width: 100%;
            position: relative;
        }
        .modal-title { font-size: 20px; font-weight: 800; margin-bottom: 8px; color: #fff; }
        .btn-modal-close {
            position: absolute;
            top: 16px;
            right: 16px;
            background: transparent;
            border: none;
            color: #94a3b8;
            font-size: 18px;
            cursor: pointer;
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
            z-index: 99999;
            left: 50%;
            bottom: 30px;
            transform: translateX(-50%);
            font-size: 14px;
            font-weight: 700;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        }
        #toast.show { visibility: visible; animation: fadein 0.3s, fadeout 0.3s 3.5s; }
        @keyframes fadein { from { bottom: 0; opacity: 0; } to { bottom: 30px; opacity: 1; } }
        @keyframes fadeout { from { bottom: 30px; opacity: 1; } to { bottom: 0; opacity: 0; } }

        @media (max-width: 768px) {
            .hero h1 { font-size: 26px; }
            .hero { padding: 35px 16px 25px 16px; }
            .items-grid { grid-template-columns: 1fr; }
            .filter-bar { flex-direction: column; }
        }
    </style>
</head>
<body>

    <!-- ─────────────────────────────────────────────────────────────
         FULL SCREEN ENTRY GATE
    ───────────────────────────────────────────────────────────── -->
    <div id="roleGateOverlay">
        <div class="gate-card">
            <div class="gate-icon"><i class="fa-solid fa-helmet-safety"></i></div>
            <h2 class="gate-title">Welcome to Shramik<span>Link</span></h2>
            <p class="gate-subtitle">Please select your access profile to continue</p>

            <div class="role-options" id="roleSelectionView">
                <!-- USER BUTTON: ENTERS DIRECTLY WITHOUT ASKING ANYTHING -->
                <div class="role-btn" onclick="enterAsUser()">
                    <div class="role-icon-box" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8;">
                        <i class="fa-solid fa-users"></i>
                    </div>
                    <div class="role-info">
                        <h3>I am a User / Public</h3>
                        <p>Find skilled labours, post job requirements & direct WhatsApp / Call. (No password required)</p>
                    </div>
                </div>

                <!-- ADMIN BUTTON: OPENS PASSWORD INPUT -->
                <div class="role-btn" onclick="showAdminPinPrompt()">
                    <div class="role-icon-box" style="background: rgba(245, 158, 11, 0.15); color: var(--accent-gold);">
                        <i class="fa-solid fa-user-shield"></i>
                    </div>
                    <div class="role-info">
                        <h3>I am an Admin</h3>
                        <p>Authorized personnel management, profile deletion & database backup controls.</p>
                    </div>
                </div>
            </div>

            <!-- MASKED ADMIN PIN PROMPT (BULLET MASKED ••••) -->
            <div id="adminPinView">
                <h3 style="font-size: 18px; margin-bottom: 8px; color: #fff;"><i class="fa-solid fa-lock" style="color: var(--accent-gold);"></i> Enter Admin Security PIN</h3>
                <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 16px;">Digits are masked with bullets for screen and keyboard privacy.</p>
                
                <input type="password" id="gateAdminPin" class="pin-mask-input" maxlength="4" placeholder="••••" autocomplete="off">
                
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button class="tab-btn" onclick="cancelAdminLogin()"><i class="fa-solid fa-arrow-left"></i> Back</button>
                    <button class="tab-btn active" onclick="submitAdminPin()"><i class="fa-solid fa-unlock"></i> Login as Admin</button>
                </div>
            </div>
        </div>
    </div>

    <!-- ANNOUNCEMENT BAR -->
    <div class="top-announcement">
        <i class="fa-solid fa-bolt" style="color: var(--accent-gold);"></i> 
        <span id="txt-announcement">National Direct Labour & Contractor Network • 0% Brokerage • 100% Free Direct Calling</span>
    </div>

    <!-- MAIN NAVBAR -->
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
                <div class="admin-badge"><i class="fa-solid fa-user-shield"></i> Admin Logged In</div>
                <div class="lang-switch">
                    <button class="lang-btn active" id="lang-en" onclick="setLanguage('en')">EN</button>
                    <button class="lang-btn" id="lang-hi" onclick="setLanguage('hi')">हिन्दी</button>
                    <button class="lang-btn" id="lang-te" onclick="setLanguage('te')">తెలుగు</button>
                </div>
            </div>
        </div>
    </header>

    <!-- HERO SECTION -->
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

    <!-- NAVIGATION TABS -->
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
            <i class="fa-solid fa-camera"></i> <span id="lbl-tabPostJob">Post Requirement & Photo</span>
        </button>
        <!-- ADMIN ONLY TAB: TOTALLY HIDDEN FOR USERS -->
        <button class="tab-btn" id="btn-backup" onclick="switchTab('tab-backup')">
            <i class="fa-solid fa-user-shield"></i> <span id="lbl-tabBackup">Admin Management</span>
        </button>
    </div>

    <!-- MAIN CONTAINER -->
    <main>

        <!-- TAB 1: WORKERS DIRECTORY -->
        <div id="tab-labours" class="tab-content">
            <div class="filter-bar">
                <input type="text" id="labourSearch" class="search-input" placeholder="🔍 Search worker name (Telugu/Hindi/English), city, or trade..." oninput="filterLabours()">
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

        <!-- TAB 2: CONTRACTOR & HOMEOWNER REQUIREMENTS -->
        <div id="tab-jobs" class="tab-content" style="display: none;">
            <div class="filter-bar">
                <input type="text" id="jobSearch" class="search-input" placeholder="🔍 Search site location, contractor/homeowner name, or work..." oninput="filterJobs()">
            </div>
            <div id="jobsList" class="items-grid">
                <p style="color: #64748b; padding: 30px;">Loading active requirements...</p>
            </div>
        </div>

        <!-- TAB 3: REGISTER WORKER -->
        <div id="tab-reg-labour" class="tab-content" style="display: none;">
            <div class="form-card">
                <h3 class="form-title"><i class="fa-solid fa-id-card" style="color: var(--accent-gold);"></i> <span id="form-workerTitle">Register as Worker</span></h3>
                <p class="form-desc" id="form-workerDesc">Enter your trade and phone to receive direct daily job calls from local contractors.</p>

                <form id="formLabour" onsubmit="submitLabour(event)">
                    <div class="form-group">
                        <label class="form-label" id="lbl-wName">Full Name * (Accepts English, हिन्दी, తెలుగు)</label>
                        <input type="text" id="labName" class="form-input" placeholder="e.g. Ramesh Kumar / రమేష్ కుమార్" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-wPhone">Phone / WhatsApp Number * (One Number Only)</label>
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
                <h3 class="form-title"><i class="fa-solid fa-camera" style="color: var(--accent-gold);"></i> <span id="form-jobTitle">Post Job Requirement with Photo</span></h3>
                <p class="form-desc" id="form-jobDesc">Contractors or homeowners can post requirements and upload a photo of the work site or problem.</p>

                <form id="formJob" onsubmit="submitJob(event)">
                    <div class="form-group">
                        <label class="form-label" id="lbl-jContractor">Contractor / Homeowner Name *</label>
                        <input type="text" id="jobContractor" class="form-input" placeholder="e.g. Apex Infra / Homeowner Suresh" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-jPhone">Contact Phone / WhatsApp *</label>
                        <input type="tel" id="jobPhone" class="form-input" placeholder="e.g. 9988776655" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-jWork">Type of Work Needed *</label>
                        <input type="text" id="jobWorkType" class="form-input" placeholder="e.g. Bathroom Tile Leakage / RCC Slab" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-jLoc">Site Location *</label>
                        <input type="text" id="jobLocation" class="form-input" placeholder="e.g. Hyderabad, Kukatpally" required>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <div class="form-group" style="flex: 1;">
                            <label class="form-label" id="lbl-jCount">Workers Needed *</label>
                            <input type="number" id="jobWorkers" class="form-input" placeholder="e.g. 3" min="1" required>
                        </div>
                        <div class="form-group" style="flex: 1;">
                            <label class="form-label" id="lbl-jWage">Daily Wage Offered</label>
                            <input type="text" id="jobWage" class="form-input" placeholder="e.g. ₹900 / day" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">📷 Upload Photo of Work / Problem (Optional)</label>
                        <input type="file" id="jobPhotoInput" accept="image/*" class="form-input" onchange="previewJobPhoto(event)">
                        <div id="jobPhotoPreviewBox" class="photo-preview-box">
                            <img id="jobPhotoPreviewImg" src="" alt="Work Photo Preview">
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label" id="lbl-jDetails">Job Scope & Requirements</label>
                        <textarea id="jobReqs" class="form-textarea" rows="3" placeholder="e.g. 4 days work. Safety gear provided. Timely payment on site."></textarea>
                    </div>
                    <button type="submit" class="btn-submit" id="btn-subJob"><i class="fa-solid fa-paper-plane"></i> Publish Job Requirement</button>
                </form>
            </div>
        </div>

        <!-- TAB 5: ADMIN MANAGEMENT (ACCESSIBLE ONLY TO ADMIN) -->
        <div id="tab-backup" class="tab-content" style="display: none;">
            <div class="backup-card">
                <h3 class="form-title"><i class="fa-solid fa-user-shield" style="color: var(--accent-gold);"></i> Admin Control Center</h3>
                <p class="form-desc">Full administrative authority unlocked. You can remove spam records or download complete snapshots.</p>

                <div class="backup-row">
                    <div>
                        <h4 style="color: #fff; margin-bottom: 4px;"><i class="fa-solid fa-download" style="color: var(--accent-gold);"></i> 1-Click Database Backup</h4>
                        <p style="font-size: 13px; color: var(--text-secondary);">Download complete snapshot of all labours, contractor jobs, and photos to your phone or PC.</p>
                    </div>
                    <a href="/api/backup" download="shramiklink_backup.json" class="tab-btn" style="text-decoration: none;">
                        <i class="fa-solid fa-file-arrow-down"></i> Download JSON
                    </a>
                </div>

                <div class="backup-row">
                    <div>
                        <h4 style="color: #fff; margin-bottom: 4px;"><i class="fa-solid fa-rotate-left" style="color: var(--accent-blue);"></i> Restore Database</h4>
                        <p style="font-size: 13px; color: var(--text-secondary);">Restore records anytime without data loss.</p>
                    </div>
                    <div>
                        <input type="file" id="restoreFile" accept=".json" style="display: none;" onchange="handleRestore(event)">
                        <button class="tab-btn" onclick="document.getElementById('restoreFile').click()">
                            <i class="fa-solid fa-upload"></i> Restore File
                        </button>
                    </div>
                </div>

                <div class="backup-row" style="background: rgba(30, 41, 59, 0.5); border-color: rgba(56, 189, 248, 0.4);">
                    <div>
                        <h4 style="color: #fff; margin-bottom: 4px;"><i class="fa-solid fa-envelope" style="color: var(--accent-blue);"></i> Help & Team Support (Gmail)</h4>
                        <p style="font-size: 13px; color: var(--text-secondary);">Send team inquiry to official support mailbox.</p>
                    </div>
                    <a href="mailto:support.shramiklink@gmail.com?subject=ShramikLink%20Inquiry%20from%20Website" class="tab-btn active" style="text-decoration: none;">
                        <i class="fa-solid fa-paper-plane"></i> Email via Gmail
                    </a>
                </div>
            </div>
        </div>

    </main>

    <!-- HIRE MODAL -->
    <div id="hireModal" class="modal-overlay">
        <div class="modal-content">
            <button class="btn-modal-close" onclick="closeHireModal()">&times;</button>
            <h3 class="modal-title"><i class="fa-solid fa-building-user" style="color: var(--accent-gold);"></i> Assign Worker to Contractor</h3>
            <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">This will mark the worker as <b>Busy</b> and display that they are currently working with this contractor.</p>
            <div class="form-group">
                <label class="form-label">Contractor / Firm Name *</label>
                <input type="text" id="hireContractorName" class="form-input" placeholder="e.g. Apex Infra Builders" required>
            </div>
            <button class="btn-submit" onclick="confirmHire()"><i class="fa-solid fa-check"></i> Confirm Assignment</button>
        </div>
    </div>

    <!-- LIGHTBOX -->
    <div id="imageLightbox" class="modal-overlay" onclick="closeLightbox()">
        <div style="max-width: 90%; max-height: 90%;">
            <img id="lightboxImg" src="" style="width: 100%; height: auto; max-height: 80vh; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.8);">
        </div>
    </div>

    <!-- FLOATING WHATSAPP -->
    <a href="https://wa.me/919876543210?text=Hello%20ShramikLink%20Support,%20I%20need%20help%20with%20finding%20workers." target="_blank" class="floating-whatsapp" title="Chat on WhatsApp">
        <i class="fa-brands fa-whatsapp"></i>
    </a>

    <!-- FOOTER -->
    <footer>
        <div class="footer-container">
            <div class="footer-col">
                <h4 style="color: var(--accent-gold); font-size: 18px;"><i class="fa-solid fa-helmet-safety"></i> ShramikLink</h4>
                <p>India's dedicated construction workforce network connecting contractors, homeowners, and certified tradesmen directly with zero brokerage.</p>
            </div>
            <div class="footer-col">
                <h4>Popular Trades</h4>
                <ul>
                    <li><a href="#" onclick="filterBySkill('Mason')">Masons (Mistri / మేస్త్రీ)</a></li>
                    <li><a href="#" onclick="filterBySkill('Electrician')">Electricians (ఇంటి వైరింగ్)</a></li>
                    <li><a href="#" onclick="filterBySkill('Plumber')">Plumbers (పైపులు, లీకేజీ)</a></li>
                    <li><a href="#" onclick="filterBySkill('Painter')">Painters (రంగులు, పుట్టీ)</a></li>
                    <li><a href="#" onclick="filterBySkill('Carpenter')">Carpenters (కార్పెంటర్)</a></li>
                </ul>
            </div>
            <div class="footer-col">
                <h4>Help & Contact</h4>
                <ul>
                    <li><a href="mailto:support.shramiklink@gmail.com"><i class="fa-solid fa-envelope"></i> support.shramiklink@gmail.com</a></li>
                    <li><a href="https://wa.me/919876543210"><i class="fa-brands fa-whatsapp"></i> WhatsApp Help Line</a></li>
                </ul>
            </div>
            <div class="footer-col">
                <h4>Trust & Privacy</h4>
                <p><i class="fa-solid fa-lock" style="color: var(--success);"></i> 256-Bit SSL Encrypted</p>
                <p><i class="fa-solid fa-ban" style="color: var(--danger);"></i> One Number per Person</p>
                <p><i class="fa-solid fa-user-shield" style="color: var(--accent-gold);"></i> Admin Password Protected</p>
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
        let currentAdminPin = '';
        let activeHireLabourId = null;
        let jobPhotoBase64 = '';
        let userRole = 'none';

        // ─────────────────────────────────────────────
        // ROLE GATEWAY FUNCTIONS
        // ─────────────────────────────────────────────
        function enterAsUser() {
            userRole = 'user';
            // Hide the gateway overlay
            document.getElementById('roleGateOverlay').style.display = 'none';
            // Ensure no admin elements are visible
            document.body.classList.remove('is-admin');
            document.getElementById('btn-backup').style.display = 'none';
            showToast("Welcome to ShramikLink!");
        }

        function showAdminPinPrompt() {
            document.getElementById('roleSelectionView').style.display = 'none';
            document.getElementById('adminPinView').style.display = 'block';
            document.getElementById('gateAdminPin').focus();
        }

        function cancelAdminLogin() {
            document.getElementById('adminPinView').style.display = 'none';
            document.getElementById('roleSelectionView').style.display = 'flex';
            document.getElementById('gateAdminPin').value = '';
        }

        function submitAdminPin() {
            const pin = document.getElementById('gateAdminPin').value.trim();
            if (pin === "9999") {
                userRole = 'admin';
                currentAdminPin = pin;
                document.body.classList.add('is-admin');
                document.getElementById('roleGateOverlay').style.display = 'none';
                showToast("Admin access granted! Management tools unlocked 🛡️");
                renderLabours(allLabours);
                renderJobs(allJobs);
            } else {
                showToast("Incorrect Password! Access denied.", true);
                document.getElementById('gateAdminPin').value = '';
            }
        }

        // MULTILINGUAL DICTIONARY
        const i18n = {
            en: {
                announcement: "National Direct Labour & Contractor Network • 0% Brokerage • 100% Free Direct Calling",
                tagline: "National Workforce Portal",
                verifiedBadge: "Verified Workers & Contractors",
                heroTitle: "Connect Skilled Labours & Contractors",
                heroSub: "Direct hiring without middlemen. Masons, Electricians, Plumbers, Painters & Helpers ready for immediate project onboarding.",
                statWorkers: "Verified Workers",
                statJobs: "Active Site Jobs",
                statWhatsapp: "WhatsApp Contact",
                tabWorkers: "Find Labours",
                tabJobs: "Contractor Jobs",
                tabRegWorker: "Register Worker",
                tabPostJob: "Post Requirement & Photo",
                tabBackup: "Admin Management",
                workerTitle: "Register as Worker",
                workerDesc: "Enter your trade and phone to receive direct daily job calls from local contractors.",
                jobTitle: "Post Job Requirement with Photo",
                jobDesc: "Contractors or homeowners can post requirements and upload a photo of the work site or problem.",
                callWorker: "Call",
                whatsappChat: "WhatsApp",
                hireBtn: "🏢 Assign Contractor",
                releaseBtn: "🟢 Mark Available",
                busyWith: "Busy with"
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
                tabWorkers: "मजदूर खोजें",
                tabJobs: "ठेकेदार के काम",
                tabRegWorker: "मजदूर पंजीकरण",
                tabPostJob: "काम व फोटो पोस्ट करें",
                tabBackup: "एडमिन प्रबंधन",
                workerTitle: "मजदूर के रूप में पंजीकरण करें",
                workerDesc: "स्थानीय ठेकेदारों से सीधे काम के कॉल प्राप्त करने के लिए अपना विवरण दर्ज करें।",
                jobTitle: "फोटो के साथ काम पोस्ट करें",
                jobDesc: "ठेकेदार या घर के मालिक काम की आवश्यकता और फोटो अपलोड कर सकते हैं।",
                callWorker: "कॉल करें",
                whatsappChat: "व्हाट्सएप",
                hireBtn: "🏢 ठेकेदार नियुक्त करें",
                releaseBtn: "🟢 काम पूरा (उपलब्ध करें)",
                busyWith: "काम पर व्यस्त:"
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
                tabWorkers: "లేబర్లను కనుగొనండి",
                tabJobs: "కాంట్రాక్టర్ పనులు",
                tabRegWorker: "వర్కర్ రిజిస్ట్రేషన్",
                tabPostJob: "పని & ఫోటో పోస్ట్ చేయండి",
                tabBackup: "అడ్మిన్ మేనేజ్‌మెంట్",
                workerTitle: "వర్కర్‌గా నమోదు చేసుకోండి",
                workerDesc: "కాంట్రాక్టర్ల నుండి నేరుగా కాల్స్ పొందడానికి మీ వివరాలను నమోదు చేయండి.",
                jobTitle: "ఫోటోతో పని అవసరాన్ని పోస్ట్ చేయండి",
                jobDesc: "కాంట్రాక్టర్లు లేదా ఇంటి యజమానులు పని ఫోటోను అప్‌లోడ్ చేయవచ్చు.",
                callWorker: "కాల్ చేయండి",
                whatsappChat: "వాట్సాప్",
                hireBtn: "🏢 కాంట్రాక్టర్‌కు కేటాయించండి",
                releaseBtn: "🟢 అందుబాటులోకి మార్చండి",
                busyWith: "పనిలో ఉన్నారు:"
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
            setTimeout(() => { t.className = t.className.replace("show", ""); }, 3500);
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

        function previewJobPhoto(e) {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(event) {
                jobPhotoBase64 = event.target.result;
                document.getElementById('jobPhotoPreviewImg').src = jobPhotoBase64;
                document.getElementById('jobPhotoPreviewBox').style.display = 'block';
            };
            reader.readAsDataURL(file);
        }

        function openLightbox(src) {
            document.getElementById('lightboxImg').src = src;
            document.getElementById('imageLightbox').style.display = 'flex';
        }

        function closeLightbox() {
            document.getElementById('imageLightbox').style.display = 'none';
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
                const isBusy = l.status === 'Busy';
                
                return `
                <div class="item-card">
                    <div>
                        <div class="card-top">
                            <div class="card-title">${l.name}</div>
                            <span class="card-badge ${isBusy ? 'badge-busy' : 'badge-available'}">
                                ${isBusy ? '🔴 Busy' : '🟢 Available'}
                            </span>
                        </div>
                        
                        ${isBusy && l.assigned_contractor ? `
                            <div class="contractor-tag">
                                <i class="fa-solid fa-building"></i> ${t.busyWith} <b>${l.assigned_contractor}</b>
                            </div>
                        ` : ''}

                        <div class="card-row"><i class="fa-solid fa-hammer"></i> <b>Trade:</b> ${l.skill}</div>
                        <div class="card-row"><i class="fa-solid fa-location-dot"></i> <b>City:</b> ${l.location}</div>
                        <div class="card-row"><i class="fa-solid fa-clock-rotate-left"></i> <b>Exp:</b> ${l.experience || 'Not specified'}</div>
                        <div class="wage-tag"><i class="fa-solid fa-money-bill-wave"></i> ${l.daily_wage || 'Daily Wage Negotiable'}</div>
                    </div>

                    <div>
                        <div class="btn-group">
                            <a href="tel:${l.phone}" class="btn-call">
                                <i class="fa-solid fa-phone"></i> ${t.callWorker}
                            </a>
                            <a href="https://wa.me/${waPhone}?text=${waMsg}" target="_blank" class="btn-whatsapp">
                                <i class="fa-brands fa-whatsapp"></i> ${t.whatsappChat}
                            </a>
                        </div>

                        ${isBusy ? `
                            <button class="btn-release" onclick="releaseLabour(${l.id})">
                                <i class="fa-solid fa-circle-check"></i> ${t.releaseBtn}
                            </button>
                        ` : `
                            <button class="btn-hire" onclick="openHireModal(${l.id})">
                                <i class="fa-solid fa-briefcase"></i> ${t.hireBtn}
                            </button>
                        `}

                        <!-- ADMIN-ONLY DELETE BUTTON -->
                        <button class="btn-admin-delete" onclick="adminDeleteLabour(${l.id})">
                            <i class="fa-solid fa-trash"></i> Admin Delete
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
                const waMsg = encodeURIComponent(`Hello ${j.contractor_name}, I saw your job requirement for ${j.work_type} on ShramikLink. I would like to discuss.`);
                
                return `
                <div class="item-card">
                    <div>
                        <div class="card-top">
                            <div class="card-title">${j.work_type}</div>
                            <span class="card-badge badge-job"><i class="fa-solid fa-people-group"></i> ${j.workers_needed} Required</span>
                        </div>
                        <div class="card-row"><i class="fa-solid fa-building-user"></i> <b>Posted By:</b> ${j.contractor_name}</div>
                        <div class="card-row"><i class="fa-solid fa-location-dot"></i> <b>Site:</b> ${j.location}</div>
                        <div class="wage-tag"><i class="fa-solid fa-coins"></i> Offered: ${j.wage_offered}</div>
                        
                        ${j.photo_data ? `
                            <div style="font-size: 11px; color: var(--accent-gold); font-weight: 700; margin-top: 6px;">📷 Work / Problem Photo (Click to zoom):</div>
                            <img src="${j.photo_data}" class="job-photo-preview" onclick="openLightbox('${j.photo_data}')" alt="Work Photo">
                        ` : ''}

                        <p style="font-size: 13px; color: #cbd5e1; background: #070a12; padding: 12px; border-radius: 8px; margin-top: 6px; border: 1px solid var(--border-color); line-height: 1.5;">
                            ${j.requirements || 'No additional site requirements specified.'}
                        </p>
                    </div>

                    <div>
                        <div class="btn-group">
                            <a href="tel:${j.phone}" class="btn-call">
                                <i class="fa-solid fa-phone"></i> ${t.callWorker}
                            </a>
                            <a href="https://wa.me/${waPhone}?text=${waMsg}" target="_blank" class="btn-whatsapp">
                                <i class="fa-brands fa-whatsapp"></i> ${t.whatsappChat}
                            </a>
                        </div>

                        <!-- ADMIN-ONLY DELETE BUTTON -->
                        <button class="btn-admin-delete" onclick="adminDeleteJob(${j.id})">
                            <i class="fa-solid fa-trash"></i> Admin Close Job
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
            const phone = document.getElementById('labPhone').value.trim();
            const data = {
                name: document.getElementById('labName').value.trim(),
                phone: phone,
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

            const result = await res.json();

            if (res.ok) {
                showToast("Worker registered successfully!");
                document.getElementById('formLabour').reset();
                await fetchAllData();
                switchTab('tab-labours');
            } else {
                showToast(result.error || "This mobile number is already registered!", true);
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
                requirements: document.getElementById('jobReqs').value.trim(),
                photo_data: jobPhotoBase64
            };

            const res = await fetch('/api/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                showToast("Job requirement published with photo!");
                document.getElementById('formJob').reset();
                jobPhotoBase64 = '';
                document.getElementById('jobPhotoPreviewBox').style.display = 'none';
                await fetchAllData();
                switchTab('tab-jobs');
            } else {
                showToast("Failed to publish requirement", true);
            }
        }

        function openHireModal(labourId) {
            activeHireLabourId = labourId;
            document.getElementById('hireModal').style.display = 'flex';
        }

        function closeHireModal() {
            document.getElementById('hireModal').style.display = 'none';
            document.getElementById('hireContractorName').value = '';
            activeHireLabourId = null;
        }

        async function confirmHire() {
            const contractor = document.getElementById('hireContractorName').value.trim();
            if (!contractor) {
                alert("Please enter Contractor or Company name");
                return;
            }

            const res = await fetch(`/api/labours/${activeHireLabourId}/assign`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ contractor_name: contractor })
            });

            if (res.ok) {
                showToast(`Worker successfully assigned to ${contractor}!`);
                closeHireModal();
                fetchAllData();
            } else {
                showToast("Failed to assign worker", true);
            }
        }

        async function releaseLabour(id) {
            const res = await fetch(`/api/labours/${id}/assign`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: "release" })
            });

            if (res.ok) {
                showToast("Worker is now marked Available!");
                fetchAllData();
            }
        }

        async function adminDeleteLabour(id) {
            if (!confirm("Admin Action: Remove this worker profile permanently?")) return;
            const res = await fetch('/api/labours/' + id, {
                method: 'DELETE',
                headers: { 'X-Admin-PIN': currentAdminPin }
            });
            if (res.ok) {
                showToast("Worker removed by Admin");
                fetchAllData();
            } else {
                showToast("Admin authorization failed! Password required.", true);
            }
        }

        async function adminDeleteJob(id) {
            if (!confirm("Admin Action: Close and remove this job posting?")) return;
            const res = await fetch('/api/jobs/' + id, {
                method: 'DELETE',
                headers: { 'X-Admin-PIN': currentAdminPin }
            });
            if (res.ok) {
                showToast("Job closed by Admin");
                fetchAllData();
            } else {
                showToast("Admin authorization failed! Password required.", true);
            }
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

# ─────────────────────────────────────────────────────────────
# 3. BACKEND API ENDPOINTS
# ─────────────────────────────────────────────────────────────

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
    phone = data.get("phone", "").strip()
    clean_phone = re.sub(r'[^0-9+]', '', phone)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM labours WHERE phone = ? OR phone LIKE ?", (clean_phone, f"%{clean_phone[-10:]}%"))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return jsonify({
            "error": f"This mobile number is already registered for worker '{existing['name']}'! Please use another number. / यह नंबर पहले से उपयोग में है।"
        }), 409

    cursor.execute("""
        INSERT INTO labours (name, phone, location, skill, experience, daily_wage, status, assigned_contractor)
        VALUES (?, ?, ?, ?, ?, ?, 'Available', '')
    """, (
        data.get("name"),
        clean_phone,
        data.get("location"),
        data.get("skill"),
        data.get("experience", "Not specified"),
        data.get("daily_wage", "Negotiable")
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "Labour registered successfully"}), 201

@app.route("/api/labours/<int:id>/assign", methods=["PATCH"])
def assign_labour(id):
    data = request.get_json()
    action = data.get("action")
    contractor = data.get("contractor_name", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    if action == "release":
        cursor.execute("UPDATE labours SET status = 'Available', assigned_contractor = '' WHERE id = ?", (id,))
    else:
        cursor.execute("UPDATE labours SET status = 'Busy', assigned_contractor = ? WHERE id = ?", (contractor, id))

    conn.commit()
    conn.close()
    return jsonify({"message": "Worker assignment updated"}), 200

@app.route("/api/labours/<int:id>", methods=["DELETE"])
def delete_labour(id):
    admin_pin = request.headers.get("X-Admin-PIN")
    if admin_pin != ADMIN_PIN:
        return jsonify({"error": "Unauthorized. Admin Password required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM labours WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Labour {id} deleted by Admin"}), 200

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
        INSERT INTO contractor_jobs (contractor_name, phone, location, work_type, workers_needed, wage_offered, requirements, photo_data, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open')
    """, (
        data.get("contractor_name"),
        data.get("phone"),
        data.get("location"),
        data.get("work_type"),
        data.get("workers_needed", 1),
        data.get("wage_offered"),
        data.get("requirements", ""),
        data.get("photo_data", "")
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "Job requirement created"}), 201

@app.route("/api/jobs/<int:id>", methods=["DELETE"])
def delete_job(id):
    admin_pin = request.headers.get("X-Admin-PIN")
    if admin_pin != ADMIN_PIN:
        return jsonify({"error": "Unauthorized. Admin Password required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contractor_jobs WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Job {id} closed by Admin"}), 200

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
        "version": "4.0-enterprise",
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
            INSERT INTO labours (name, phone, location, skill, experience, daily_wage, status, assigned_contractor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (l["name"], l["phone"], l["location"], l["skill"], l.get("experience", ""), l.get("daily_wage", ""), l.get("status", "Available"), l.get("assigned_contractor", "")))

    for j in data["contractor_jobs"]:
        cursor.execute("""
            INSERT INTO contractor_jobs (contractor_name, phone, location, work_type, workers_needed, wage_offered, requirements, photo_data, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (j["contractor_name"], j["phone"], j["location"], j["work_type"], j.get("workers_needed", 1), j.get("wage_offered", ""), j.get("requirements", ""), j.get("photo_data", ""), j.get("status", "Open")))

    conn.commit()
    conn.close()
    return jsonify({"message": "Database restored successfully", "labours_restored": len(data["labours"]), "jobs_restored": len(data["contractor_jobs"])}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

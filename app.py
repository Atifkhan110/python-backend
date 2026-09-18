from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_NAME = "users.db"

# 1. DATABASE SETUP: Create SQL table and seed initial data
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    # Check if empty, add default records
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO users (name, role) VALUES (?, ?)",
            [
                ("Atif", "Full-Stack Developer"),
                ("Alex", "UI/UX Designer"),
                ("Sarah", "Cloud Architect")
            ]
        )
    conn.commit()
    conn.close()

# Initialize the database immediately
init_db()

# Frontend HTML + CSS + JavaScript
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python + SQL Full-Stack App</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f172a; color: #f8fafc; display: flex; justify-content: center; padding: 40px 20px; min-height: 100vh; }
        .container { width: 100%; max-width: 650px; }
        .card { background: #1e293b; border-radius: 12px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); margin-bottom: 24px; border: 1px solid #334155; }
        h1 { font-size: 26px; color: #38bdf8; margin-bottom: 8px; }
        p.subtitle { color: #94a3b8; font-size: 14px; margin-bottom: 20px; }
        .status-badge { display: inline-flex; align-items: center; gap: 6px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-bottom: 16px; }
        .dot { width: 8px; height: 8px; background: #38bdf8; border-radius: 50%; box-shadow: 0 0 8px #38bdf8; }
        
        .form-row { display: flex; gap: 10px; margin-bottom: 12px; }
        input { flex: 1; padding: 10px 14px; background: #0f172a; border: 1px solid #475569; color: #fff; border-radius: 6px; font-size: 14px; }
        input:focus { outline: 2px solid #38bdf8; }
        button.btn-add { background: #0284c7; color: #fff; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; cursor: pointer; }
        button.btn-add:hover { background: #0369a1; }
        
        .user-list { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }
        .user-item { display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 12px 16px; border-radius: 8px; border: 1px solid #334155; }
        .user-info { display: flex; align-items: center; gap: 12px; }
        .user-id { font-size: 12px; color: #64748b; font-weight: bold; }
        .user-name { font-weight: 600; color: #f1f5f9; }
        .user-role { font-size: 13px; color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 4px 8px; border-radius: 4px; }
        .btn-delete { background: #ef4444; color: #fff; border: none; padding: 6px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; }
        .btn-delete:hover { background: #dc2626; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="status-badge"><span class="dot"></span> SQLite Database Connected</div>
            <h1>Team Directory (SQL Powered)</h1>
            <p class="subtitle">Every action executes real <b>SQL queries</b> on your Python cloud server.</p>

            <form id="addUserForm" class="form-row">
                <input type="text" id="nameInput" placeholder="Name (e.g. John)" required>
                <input type="text" id="roleInput" placeholder="Role (e.g. Developer)" required>
                <button type="submit" class="btn-add">+ Add Record</button>
            </form>
        </div>

        <div class="card">
            <h2 style="font-size: 18px; margin-bottom: 12px; color: #e2e8f0;">Database Records (SELECT * FROM users)</h2>
            <div id="usersContainer" class="user-list">
                <p style="color: #64748b;">Loading records from SQL database...</p>
            </div>
        </div>
    </div>

    <script>
        async function loadUsers() {
            try {
                const res = await fetch('/api/users');
                const users = await res.json();
                const container = document.getElementById('usersContainer');
                
                if (users.length === 0) {
                    container.innerHTML = '<p style="color: #64748b;">No records in database. Add one above!</p>';
                    return;
                }

                container.innerHTML = users.map(user => `
                    <div class="user-item">
                        <div class="user-info">
                            <span class="user-id">#${user.id}</span>
                            <span class="user-name">${user.name}</span>
                            <span class="user-role">${user.role}</span>
                        </div>
                        <button class="btn-delete" onclick="deleteUser(${user.id})">Delete</button>
                    </div>
                `).join('');
            } catch (err) {
                console.error(err);
                document.getElementById('usersContainer').innerHTML = '<p style="color: #ef4444;">Error fetching from database.</p>';
            }
        }

        document.getElementById('addUserForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('nameInput').value.trim();
            const role = document.getElementById('roleInput').value.trim();
            if (!name || !role) return;

            await fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, role })
            });

            document.getElementById('nameInput').value = '';
            document.getElementById('roleInput').value = '';
            loadUsers();
        });

        async function deleteUser(id) {
            await fetch('/api/users/' + id, { method: 'DELETE' });
            loadUsers();
        }

        loadUsers();
    </script>
</body>
</html>
"""

# Route 1: Serve Webpage
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

# Route 2: SQL SELECT (Read all records)
@app.route("/api/users", methods=["GET"])
def get_users():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    users_list = [dict(row) for row in rows]
    conn.close()
    return jsonify(users_list)

# Route 3: SQL INSERT (Add new record)
@app.route("/api/users", methods=["POST"])
def add_user():
    data = request.get_json()
    name = data.get("name")
    role = data.get("role")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, role) VALUES (?, ?)", (name, role))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return jsonify({"id": new_id, "name": name, "role": role}), 201

# Route 4: SQL DELETE (Delete a record by ID)
@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"User {user_id} deleted successfully"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

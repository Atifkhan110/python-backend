from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Allows other frontends to access your API

# In-memory user database
users = [
    {"id": 1, "name": "Atif", "role": "Full-Stack Developer"},
    {"id": 2, "name": "Alex", "role": "UI/UX Designer"},
    {"id": 3, "name": "Sarah", "role": "Cloud Architect"}
]

# Frontend HTML + CSS + JavaScript template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Full-Stack App</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f172a; color: #f8fafc; display: flex; justify-content: center; padding: 40px 20px; min-height: 100vh; }
        .container { width: 100%; max-width: 650px; }
        .card { background: #1e293b; border-radius: 12px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); margin-bottom: 24px; border: 1px solid #334155; }
        h1 { font-size: 26px; color: #38bdf8; margin-bottom: 8px; }
        p.subtitle { color: #94a3b8; font-size: 14px; margin-bottom: 20px; }
        .status-badge { display: inline-flex; align-items: center; gap: 6px; background: rgba(34, 197, 94, 0.15); color: #4ade80; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-bottom: 16px; }
        .dot { width: 8px; height: 8px; background: #22c55e; border-radius: 50%; box-shadow: 0 0 8px #22c55e; }
        
        .form-row { display: flex; gap: 10px; margin-bottom: 12px; }
        input { flex: 1; padding: 10px 14px; background: #0f172a; border: 1px solid #475569; color: #fff; border-radius: 6px; font-size: 14px; }
        input:focus { outline: 2px solid #38bdf8; }
        button { background: #0284c7; color: #fff; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #0369a1; }
        
        .user-list { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }
        .user-item { display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 12px 16px; border-radius: 8px; border: 1px solid #334155; }
        .user-name { font-weight: 600; color: #f1f5f9; }
        .user-role { font-size: 13px; color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 4px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="status-badge"><span class="dot"></span> Python Backend Connected</div>
            <h1>Team Directory</h1>
            <p class="subtitle">Frontend communicating with Render Flask API via JavaScript <code>fetch()</code></p>

            <form id="addUserForm" class="form-row">
                <input type="text" id="nameInput" placeholder="Name (e.g. John)" required>
                <input type="text" id="roleInput" placeholder="Role (e.g. Developer)" required>
                <button type="submit">+ Add User</button>
            </form>
        </div>

        <div class="card">
            <h2 style="font-size: 18px; margin-bottom: 12px; color: #e2e8f0;">Users from Backend API</h2>
            <div id="usersContainer" class="user-list">
                <p style="color: #64748b;">Loading users from Python backend...</p>
            </div>
        </div>
    </div>

    <script>
        // Function to fetch and display users from backend
        async function loadUsers() {
            try {
                const response = await fetch('/api/users');
                const users = await response.json();
                const container = document.getElementById('usersContainer');
                
                if (users.length === 0) {
                    container.innerHTML = '<p style="color: #64748b;">No users found.</p>';
                    return;
                }

                container.innerHTML = users.map(user => `
                    <div class="user-item">
                        <span class="user-name">${user.name}</span>
                        <span class="user-role">${user.role}</span>
                    </div>
                `).join('');
            } catch (err) {
                console.error("Error loading users:", err);
                document.getElementById('usersContainer').innerHTML = '<p style="color: #ef4444;">Failed to load data from backend.</p>';
            }
        }

        // Handle adding a new user via POST request
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
            loadUsers(); // Refresh the list
        });

        // Load users on initial page load
        loadUsers();
    </script>
</body>
</html>
"""

# Route 1: Serves the Webpage
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

# Route 2: GET API endpoint (Fetch all users)
@app.route("/api/users", methods=["GET"])
def get_users():
    return jsonify(users)

# Route 3: POST API endpoint (Add a new user)
@app.route("/api/users", methods=["POST"])
def add_user():
    data = request.get_json()
    new_user = {
        "id": len(users) + 1,
        "name": data.get("name"),
        "role": data.get("role")
    }
    users.append(new_user)
    return jsonify(new_user), 201

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

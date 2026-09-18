from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "Hello from your Render Python Backend!"
    })

@app.route("/api/users")
def get_users():
    return jsonify([
        {"id": 1, "name": "Atif", "role": "Developer"},
        {"id": 2, "name": "Alex", "role": "Designer"}
    ])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

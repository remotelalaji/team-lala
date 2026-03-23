from flask import Flask, render_template, request, redirect, session, jsonify
import random
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "secret123"

PASSWORD = "669900"

# Dummy data (replace with Google Drive later)
def get_recordings():
    data = []
    for i in range(1000):
        data.append({
            "name": f"{random.randint(10,99)} UserNameLongExample {i}",
            "date": (datetime.now() - timedelta(days=random.randint(0,5))).strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%I:%M %p"),
            "audio": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        })
    return data


@app.route("/", methods=["GET"])
def home():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect("/")
    return render_template("login.html")


@app.route("/api/recordings")
def api_recordings():
    page = int(request.args.get("page", 1))
    date = request.args.get("date")

    per_page = 200
    data = get_recordings()

    if date:
        data = [d for d in data if d["date"] == date]

    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        "data": data[start:end],
        "has_more": end < len(data)
    })


if __name__ == "__main__":
    app.run(debug=True)

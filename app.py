from flask import Flask, redirect, render_template, request, session, flash
from flask_session import Session
from cs50 import SQL
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///roadmap.db")

@app.route("/")
def index():
    """Shows homepage"""
    if session.get("user_id") is None:
        return redirect("/login")
    else:
        rows = db.execute(
            "SELECT * FROM users WHERE id = ?", session["user_id"]
        )
        roadmaps = db.execute(
            "SELECT * FROM roadmaps WHERE user_id = ?", session["user_id"]
        )
        return render_template("index.html", username=rows[0]["username"], logged_in=True, roadmaps=roadmaps)
    

@app.route("/about")
def about():
    """Shows an about page for the website"""
    if session.get("user_id") is None:
        return render_template("about.html")
    else:
        rows = db.execute(
            "SELECT * FROM users WHERE id = ?", session["user_id"]
        )
        return render_template("about.html", username=rows[0]["username"], logged_in=True)
    

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    if session.get("user_id") is None:
        session.clear()

        if request.method == "POST":
            rows = db.execute(
                "SELECT * FROM users WHERE username = ?", request.form.get("username")
            )

            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
                return render_template("error.html", message="invalid username and/or password")

            session["user_id"] = rows[0]["id"]
            return redirect("/")

        elif request.method == "GET":
            return render_template("login.html")
    else:
        rows = db.execute(
            "SELECT * FROM users WHERE id = ?", session["user_id"]
        )
        return render_template("error.html", message="you cannot login while already being logged in", username=rows[0]["username"], logged_in=True)
    

@app.route("/logout")
def logout():
    """Log user out"""
    if session.get("user_id") is None:
        return render_template("error.html", message="you cannot logout without logging in first")
    else:
        session.clear()
        return redirect("/")
    

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        if session.get("user_id") is None:
            return render_template("register.html")
        else:
            rows = db.execute(
                "SELECT * FROM users WHERE id = ?", session["user_id"]
            )
            return render_template("register.html", username=rows[0]["username"], logged_in=True)
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        try:
            if (password == confirmation):
                hashed = generate_password_hash(password)
                db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hashed)
                return redirect("/")
            else:
                if session.get("user_id") is None:
                    return render_template("error.html", message="password and confirmation are different")
                else:
                    rows = db.execute(
                        "SELECT * FROM users WHERE id = ?", session["user_id"]
                    )
                    return render_template("error.html", message="password and confirmation are different", username=rows[0]["username"], logged_in=True)
        except ValueError:
            if session.get("user_id") is None:
                return render_template("error.html", message="username already exists")
            else:
                rows = db.execute(
                    "SELECT * FROM users WHERE id = ?", session["user_id"]
                )
                return render_template("error.html", message="username already exists", username=rows[0]["username"], logged_in=True)
            
@app.route("/create")
def create():
    """Creates unamed roadmap"""
    if session.get("user_id") is None:
        return render_template("error.html", message="must be logged in first")
    else:
        db.execute("INSERT INTO roadmaps (user_id, color) VALUES (?, ?)", session["user_id"], "white")
        roadmap_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        roadmap_name = db.execute("SELECT name FROM roadmaps WHERE id = ?", roadmap_id)[0]["name"]
        roadmap_color = db.execute("SELECT color FROM roadmaps WHERE id = ?", roadmap_id)[0]["color"]
        rows = db.execute(
            "SELECT * FROM users WHERE id = ?", session["user_id"]
        )
        return render_template("roadmap_view.html", roadmap_name=roadmap_name, roadmap_color=roadmap_color, username=rows[0]["username"], logged_in=True) # This will change to hand over nodes once rendering is added.


@app.route("/view")
def view():
    """Opens roadmap for viewing"""
    if session.get("user_id") is None:
        return render_template("error.html", message="must be logged in first")
    else:
        roadmap_id = request.args.get('id')
        roadmap_name = db.execute("SELECT name FROM roadmaps WHERE id = ?", roadmap_id)[0]["name"]
        roadmap_color = db.execute("SELECT color FROM roadmaps WHERE id = ?", roadmap_id)[0]["color"]
        rows = db.execute(
            "SELECT * FROM users WHERE id = ?", session["user_id"]
        )
        return render_template("roadmap_view.html", roadmap_name=roadmap_name, roadmap_color=roadmap_color, username=rows[0]["username"], logged_in=True) # This will change to hand over nodes once rendering is added.
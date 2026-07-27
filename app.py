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
        return render_template("index.html", username=rows[0]["username"], logged_in=True)

@app.route("/about")
def about():
     """Shows an about page for the website"""
     return render_template("about.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("error.html", message="invalid username and/or password")

        session["user_id"] = rows[0]["id"]
        return redirect("/")

    else:
        return render_template("login.html")

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
        # shows registering page
        return render_template("register.html")
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
                return render_template("error.html", message="password and confirmation are different")
        except ValueError:
            return render_template("error.html", message="username already exists")

# USE THIS FOR PAGES THAT REQUIRE A LOGGED IN ACCOUNT

#     if session.get("user_id") is None:
#            return redirect("/login")
#     else:
#            *the rest of your code*
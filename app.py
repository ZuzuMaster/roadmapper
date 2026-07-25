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
    return render_template("index.html")

@app.route("/about")
def about():
     return render_template("about.html")

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
                flash("Password and confirmation are different")
                return redirect("/")
        except ValueError:
            flash("Username already exists")
            return redirect("/")

# USE THIS FOR PAGES THAT REQUIRE A LOGGED IN ACCOUNT

#     if session.get("user_id") is None:
#            return redirect("/login")
#     else:
#            *the rest of your code*
from flask import Flask, redirect, render_template, request, session, flash
from flask_session import Session
from cs50 import SQL
from werkzeug.security import check_password_hash, generate_password_hash
import requests

app = Flask(__name__)
if __name__ == "__main__":
    app.run(debug=True)

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

        if not username or not password:
            return render_template("error.html", message="username or password empty")

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
        db.execute("INSERT INTO roadmaps (user_id) VALUES (?)", session["user_id"])
        return redirect("/")


@app.route("/create_node")
def create_node():
    """Creates an unnamed and autoconnected node"""
    if session.get("user_id") is None:
        return render_template("error.html", message="must be logged in first")
    
    roadmap_id = request.args.get('id')
    if not roadmap_id:
        return render_template("error.html", message="missing roadmap ID")
    if not db.execute("SELECT * FROM users WHERE id = ?", roadmap_id):
        return render_template("error.html", message="wrong user")
    recent_row = db.execute("SELECT * FROM nodes WHERE map_id = ? ORDER BY created DESC LIMIT 1;")
    if not recent_row:
        db.execute(
            "INSERT INTO nodes (map_id, next, previous, title, link, x, y) VALUES (?, NULL, NULL, NULL, NULL, ?, ?)",
            roadmap_id, 0, 0
        )
        return redirect(f"/view?id={roadmap_id}")
    most_recent = recent_row[0]
    most_recent_y = most_recent["y"]
    most_recent_x = most_recent["x"]
    x = 2 if most_recent_x == 2 else most_recent_x + 1
    y = most_recent_y + 1
    db.execute(
        "INSERT INTO nodes (map_id, next, previous, title, link, x, y) VALUES (?, NULL, NULL, NULL, NULL, ?, ?)",
        roadmap_id, x, y
    )
    return redirect(f"/view?id={roadmap_id}")


@app.route("/view")
def view():
    """Opens roadmap for viewing and renders nodes using a linked-list style system"""
    if session.get("user_id") is None:
        return render_template("error.html", message="must be logged in first")
    roadmap_id = request.args.get('id')
    if not roadmap_id:
        return render_template("error.html", message="missing roadmap ID")
    roadmaps = db.execute(
        "SELECT * FROM roadmaps WHERE id = ? AND user_id = ?", 
        roadmap_id, session["user_id"]
    )
    if not roadmaps:
        return render_template("error.html", message="roadmap not found")
    roadmap = roadmaps[0]
    user = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]
    nodes = db.execute("SELECT * FROM nodes WHERE map_id = ?", roadmap_id)
    connections = db.execute("SELECT * FROM connections WHERE map_id = ?", roadmap_id)
    return render_template("roadmap_view.html", roadmap_name=roadmap["name"], username=user["username"], logged_in=True, roadmap=roadmap,nodes=nodes, connections=connections)


@app.route("/customize", methods=["GET", "POST"])
def customize():
    """Changes name of roadmap"""
    if request.method == "GET":
        if session.get("user_id") is None:
            return render_template("error.html", message="must be logged in first")
        else:
            roadmap_id = request.args.get('id')
            rows_user = db.execute(
                "SELECT * FROM users WHERE id = ?", session["user_id"]
            )
            rows_map = db.execute("SELECT * FROM roadmaps WHERE id = ? AND user_id = ?", roadmap_id, session["user_id"])
            if not rows_map:
                return render_template("error.html", message="roadmap not found")
            else:
                roadmap = rows_map[0]
                return render_template("customize.html", username=rows_user[0]["username"], logged_in=True, roadmap=roadmap)
    elif request.method == "POST":
        if session.get("user_id") is None:
            return render_template("error.html", message="must be logged in first")
        else:
            name = request.form.get("name")
            roadmap_id = request.args.get('id')
            db.execute("UPDATE roadmaps SET name = ? WHERE id = ? AND user_id = ?", name, roadmap_id, session["user_id"])
            return redirect(f"/view?id={roadmap_id}")


@app.route("/customize_node", methods=["GET", "POST"])
def customize_node():
    """Changes the info/metadata on a node"""
    if request.method == "GET":
        if session.get("user_id") is None:
            return render_template("error.html", message="must be logged in first")
        else:
            node_id = request.args.get('id')
            if not node_id:
                return render_template("error.html", message="missing node ID")
            nodes = db.execute(
                "SELECT nodes.*, roadmaps.id AS roadmap_id FROM nodes JOIN roadmaps ON nodes.map_id = roadmaps.id WHERE nodes.id = ? AND roadmaps.user_id = ?",
                node_id, session["user_id"]
            )
            roadmap_id = nodes[0]["map_id"]
            node = nodes[0]
            rows_user = db.execute(
                "SELECT * FROM users WHERE id = ?", session["user_id"]
            )
            return render_template("customize_node.html", username=rows_user[0]["username"], logged_in=True, node=node)
    elif request.method == "POST":
        if session.get("user_id") is None:
            return render_template("error.html", message="must be logged in first")
        else:
            title = request.form.get("title")
            link = (request.form.get("link") or "").strip()
            if not link:
                return render_template("error.html", message="missing link")
            if not link.startswith(("http://", "https://")):
                link = "https://" + link
            try:
                if requests.get(link, timeout=5).status_code != 200:
                    return render_template("error.html", message="invalid link")
            except requests.exceptions.RequestException as e:
                return render_template("error.html", message="invalid link")
            node_id = request.args.get('id')
            nodes = db.execute(
                "SELECT nodes.*, roadmaps.id AS roadmap_id FROM nodes JOIN roadmaps ON nodes.map_id = roadmaps.id WHERE nodes.id = ? AND roadmaps.user_id = ?",
                node_id, session["user_id"]
            )
            roadmap_id = nodes[0]["map_id"]
            if not nodes:
                return render_template("error.html", message="node not found or unauthorized")
            db.execute("UPDATE nodes SET title = ?, link = ? WHERE id = ? AND map_id = ?", title, link, node_id, roadmap_id)
            return redirect(f"/view?id={roadmap_id}")


@app.route("/complete")
def complete():
        """Completes a node"""
        if session.get("user_id") is None:
            return render_template("error.html", message="must be logged in first")
        else:
            node_id = request.args.get('id')
            if not node_id:
                return render_template("error.html", message="missing node ID")
            nodes = db.execute(
                "SELECT nodes.*, roadmaps.id AS roadmap_id FROM nodes JOIN roadmaps ON nodes.map_id = roadmaps.id WHERE nodes.id = ? AND roadmaps.user_id = ?",
                node_id, session["user_id"]
            )
            roadmap_id = nodes[0]["map_id"]
            if not nodes:
                return render_template("error.html", message="node not found or unauthorized")
            db.execute("UPDATE nodes SET completed = ? WHERE id = ?", 1, node_id)
            return redirect(f"/view?id={roadmap_id}")


@app.route("/uncomplete")
def uncomplete():
        """Completes a node"""
        if session.get("user_id") is None:
            return render_template("error.html", message="must be logged in first")
        else:
            node_id = request.args.get('id')
            if not node_id:
                return render_template("error.html", message="missing node ID")
            nodes = db.execute(
                "SELECT nodes.*, roadmaps.id AS roadmap_id FROM nodes JOIN roadmaps ON nodes.map_id = roadmaps.id WHERE nodes.id = ? AND roadmaps.user_id = ?",
                node_id, session["user_id"]
            )
            roadmap_id = nodes[0]["map_id"]
            if not nodes:
                return render_template("error.html", message="node not found or unauthorized")
            db.execute("UPDATE nodes SET completed = ? WHERE id = ?", 0, node_id)
            return redirect(f"/view?id={roadmap_id}")


@app.route("/delete")
def delete():
    """Deletes chosen roadmap"""
    if session.get("user_id") is None:
        return render_template("error.html", message="must be logged in first")
    roadmap_id = request.args.get('id')
    if not db.execute("SELECT * FROM users WHERE id = ?", roadmap_id):
        return render_template("error.html", message="wrong user")
    db.execute("DELETE FROM nodes WHERE map_id = ?", roadmap_id)
    db.execute("DELETE FROM roadmaps WHERE id = ? AND user_id = ?", roadmap_id, session["user_id"])
    return redirect("/")

    
@app.route("/delete_node")
def delete_node():
    """Deletes chosen node"""
    if session.get("user_id") is None:
        return render_template("error.html", message="must be logged in first")
    
    node_id = request.args.get('id')
    if not node_id:
        return render_template("error.html", message="missing node ID")
    nodes = db.execute(
        "SELECT nodes.*, roadmaps.id AS roadmap_id FROM nodes JOIN roadmaps ON nodes.map_id = roadmaps.id WHERE nodes.id = ? AND roadmaps.user_id = ?",
        node_id, session["user_id"]
    )
    if not nodes:
        return render_template("error.html", message="node not found or unauthorized")
    else:
        roadmap_id = nodes[0]["map_id"]
        db.execute("DELETE FROM nodes WHERE id = ?", node_id)
        return redirect(f"/view?id={roadmap_id}")
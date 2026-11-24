from functools import wraps
from urllib.parse import urlparse

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


@app.context_processor
def inject_user_stats():
    """Globally injects user session, stats, and roadmaps into all templates"""
    if session.get("user_id") is None:
        return dict(logged_in=False)
    
    user_id = session["user_id"]
    user_rows = db.execute("SELECT username FROM users WHERE id = ?", user_id)
    username = user_rows[0]["username"] if user_rows else ""
    
    roadmaps = db.execute("SELECT * FROM roadmaps WHERE user_id = ?", user_id)
    total_roadmaps = len(roadmaps)
    
    total_nodes = 0
    completed_nodes = 0
    if roadmaps:
        roadmap_ids = [r["id"] for r in roadmaps]
        placeholders = ",".join(["?"] * len(roadmap_ids))
        nodes = db.execute(f"SELECT completed FROM nodes WHERE map_id IN ({placeholders})", *roadmap_ids)
        total_nodes = len(nodes)
        completed_nodes = sum(1 for n in nodes if n["completed"] == 1)
        
    return dict(
        logged_in=True,
        username=username,
        roadmaps=roadmaps,
        stat_roadmaps=total_roadmaps,
        stat_nodes=total_nodes,
        stat_completed=completed_nodes
    )


def login_required(f):
    """Requires login for a page"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            return render_template("error.html", message="must be logged in first")
        return f(*args, **kwargs)
    return wrapped


def get_username():
    """Gets the current user's username"""
    rows = db.execute(
        "SELECT * FROM users WHERE id = ?", session["user_id"]
    )
    return rows[0]["username"]


def render_error(message):
    """Renders an error message"""
    if session.get("user_id") is None:
        return render_template("error.html", message=message)
    return render_template("error.html", message=message, username=get_username(), logged_in=True)


def get_owned_roadmap(roadmap_id):
    """Gets the indicated roadmap using the user and map ids"""
    return db.execute(
        "SELECT * FROM roadmaps WHERE id = ? AND user_id = ?", roadmap_id, session["user_id"]
    )


def get_owned_node(node_id):
    """Gets the indicated node using the user, map, and node ids"""
    return db.execute(
        "SELECT nodes.*, roadmaps.id AS roadmap_id FROM nodes JOIN roadmaps ON nodes.map_id = roadmaps.id WHERE nodes.id = ? AND roadmaps.user_id = ?",
        node_id, session["user_id"]
    )


def insert_node(roadmap_id, x, y):
    """Creates a new blank node"""
    db.execute(
        "INSERT INTO nodes (map_id, title, link, x, y) VALUES (?, NULL, NULL, ?, ?)",
        roadmap_id, x, y
    )


def redirect_to_roadmap(roadmap_id):
    """Redirects to roadmap"""
    return redirect(f"/view?id={roadmap_id}")


def set_node_completed(completed):
    """Sets a node either completed or uncompleted depending on the argument"""
    node_id = request.args.get('id')
    if not node_id:
        return render_error("missing node ID")
    nodes = get_owned_node(node_id)
    if not nodes:
        return render_error("node not found or unauthorized")
    roadmap_id = nodes[0]["map_id"]
    db.execute("UPDATE nodes SET completed = ? WHERE id = ?", completed, node_id)
    return redirect_to_roadmap(roadmap_id)

def set_node_optional(optional):
    """Sets a node either optional or unoptional depending on the argument"""
    node_id = request.args.get('id')
    if not node_id:
        return render_error("missing node ID")
    nodes = get_owned_node(node_id)
    if not nodes:
        return render_error("node not found or unauthorized")
    roadmap_id = nodes[0]["map_id"]
    db.execute("UPDATE nodes SET optional = ? WHERE id = ?", optional, node_id)
    return redirect_to_roadmap(roadmap_id)


def get_connection_nodes():
    """Validates nodes for connection"""
    try:
        connecter_id = int(request.form.get("connecter_id"))
        connectee_id = int(request.form.get("connectee_id"))
    except (TypeError, ValueError):
        return None, None, render_error("invalid node ids")
    if connecter_id == connectee_id:
        return None, None, render_error("a node can't connect to itself")

    connecter = get_owned_node(connecter_id)
    connectee = get_owned_node(connectee_id)
    if not connecter or not connectee:
        return None, None, render_error("node not found or unauthorized")

    if connecter[0]["map_id"] != connectee[0]["map_id"]:
        return None, None, render_error("nodes must be on the same roadmap")

    return connecter[0], connectee[0], None


@app.route("/")
def index():
    """Shows homepage"""
    if session.get("user_id") is None:
        return redirect("/login")
    else:
        roadmaps = db.execute(
            "SELECT * FROM roadmaps WHERE user_id = ?", session["user_id"]
        )
        return render_template("index.html", username=get_username(), logged_in=True, roadmaps=roadmaps)
    

@app.route("/about")
def about():
    """Shows an about page for the website"""
    if session.get("user_id") is None:
        return render_template("about.html")
    else:
        return render_template("about.html", username=get_username(), logged_in=True)
    

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
                return render_error("invalid username and/or password")
            session["user_id"] = rows[0]["id"]
            return redirect("/")
        elif request.method == "GET":
            return render_template("login.html")
    else:
        return render_error("you cannot login while already being logged in")
    

@app.route("/logout")
@login_required
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")
    

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        if session.get("user_id") is None:
            return render_template("register.html")
        else:
            return render_template("register.html", username=get_username(), logged_in=True)
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username or not password:
            return render_error("username or password empty")
        try:
            if (password == confirmation):
                hashed = generate_password_hash(password)
                db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hashed)
                return redirect("/")
            else:
                return render_error("password and confirmation are different")
        except ValueError:
            return render_error("username already exists")

            
@app.route("/create")
@login_required
def create():
    """Creates unamed roadmap"""
    db.execute("INSERT INTO roadmaps (user_id) VALUES (?)", session["user_id"])
    return redirect("/")


@app.route("/create_node")
@login_required
def create_node():
    """Creates an unnamed and autoconnected node"""
    roadmap_id = request.args.get('id')
    if not roadmap_id:
        return render_error("missing roadmap ID")
    if not get_owned_roadmap(roadmap_id):
        return render_error("wrong user")
    recent_row = db.execute("SELECT * FROM nodes WHERE map_id = ? ORDER BY created DESC, id DESC LIMIT 1;", roadmap_id)
    if not recent_row:
        insert_node(roadmap_id, 0, 0)
        return redirect_to_roadmap(roadmap_id)
    most_recent = recent_row[0]
    most_recent_y = most_recent["y"]
    most_recent_x = most_recent["x"]
    if most_recent_x == 2:
        x = 0
        y = most_recent_y + 1
    else:
        x = most_recent_x + 1
        y = most_recent_y
    insert_node(roadmap_id, x, y)
    return redirect_to_roadmap(roadmap_id)


@app.route("/view")
@login_required
def view():
    """Opens roadmap for viewing and renders nodes using a linked-list style system"""
    roadmap_id = request.args.get('id')
    if not roadmap_id:
        return render_error("missing roadmap ID")
    roadmaps = get_owned_roadmap(roadmap_id)
    if not roadmaps:
        return render_error("roadmap not found")
    roadmap = roadmaps[0]
    nodes = db.execute("SELECT * FROM nodes WHERE map_id = ?", roadmap_id)
    connections = db.execute("SELECT * FROM connections WHERE map_id = ?", roadmap_id)
    return render_template("roadmap_view.html", roadmap_name=roadmap["name"], username=get_username(), logged_in=True, roadmap=roadmap,nodes=nodes, connections=connections)


@app.route("/customize", methods=["GET", "POST"])
@login_required
def customize():
    """Changes name of roadmap"""
    if request.method == "GET":
        roadmap_id = request.args.get('id')
        rows_map = get_owned_roadmap(roadmap_id)
        if not rows_map:
            return render_error("roadmap not found")
        else:
            roadmap = rows_map[0]
            return render_template("customize.html", username=get_username(), logged_in=True, roadmap=roadmap)
    elif request.method == "POST":
        name = request.form.get("name")
        roadmap_id = request.args.get('id')
        db.execute("UPDATE roadmaps SET name = ? WHERE id = ? AND user_id = ?", name, roadmap_id, session["user_id"])
        return redirect_to_roadmap(roadmap_id)


@app.route("/customize_node", methods=["GET", "POST"])
@login_required
def customize_node():
    """Changes the info/metadata on a node"""
    node_id = request.args.get('id')
    if not node_id:
        return render_error("missing node ID")
    nodes = get_owned_node(node_id)
    if not nodes:
        return render_error("node not found or unauthorized")
    node = nodes[0]
    roadmap_id = node["map_id"]
    if request.method == "GET":
        return render_template("customize_node.html", username=get_username(), logged_in=True, node=node)
    title = request.form.get("title")
    link = (request.form.get("link") or "").strip()
    if link:
        if not link.startswith(("http://", "https://")):
            link = "https://" + link
        parsed = urlparse(link)
        if not parsed.netloc:
            return render_error("invalid link format")
        db.execute("UPDATE nodes SET title = ?, link = ? WHERE id = ? AND map_id = ?", title, link, node_id, roadmap_id)
        return redirect_to_roadmap(roadmap_id)
    if not link:
        db.execute("UPDATE nodes SET title = ? WHERE id = ? AND map_id = ?", title, node_id, roadmap_id)
        return redirect_to_roadmap(roadmap_id)


@app.route("/complete")
@login_required
def complete():
    """Completes a node"""
    return set_node_completed(1)


@app.route("/uncomplete")
@login_required
def uncomplete():
    """Completes a node"""
    return set_node_completed(0)


@app.route("/set_optional")
@login_required
def set_optional():
    """Sets a node as optional"""
    return set_node_optional(1)


@app.route("/set_unoptional")
@login_required
def set_unoptional():
    """Sets a node as mandatory/unoptional"""
    return set_node_optional(0)


@app.route("/delete")
@login_required
def delete():
    """Deletes chosen roadmap"""
    roadmap_id = request.args.get('id')
    if not get_owned_roadmap(roadmap_id):
        return render_error("wrong user")
    db.execute("DELETE FROM nodes WHERE map_id = ?", roadmap_id)
    db.execute("DELETE FROM roadmaps WHERE id = ? AND user_id = ?", roadmap_id, session["user_id"])
    return redirect("/")


@app.route("/connect", methods=["GET", "POST"])
@login_required
def connect():
    if request.method == "GET":
        return render_template("connect.html")
    connecter, connectee, err = get_connection_nodes()
    if err:
        return err
    roadmap_id = connecter["map_id"]
    if db.execute(
        "SELECT 1 FROM connections WHERE connecter = ? AND connectee = ? AND map_id = ?",
        connecter["id"], connectee["id"], roadmap_id
    ):
        return render_error("already connected")
    db.execute(
        "INSERT INTO connections (connecter, connectee, map_id) VALUES (?, ?, ?)",
        connecter["id"], connectee["id"], roadmap_id
    )
    return redirect_to_roadmap(roadmap_id)
    

@app.route("/unconnect", methods=["GET", "POST"])
@login_required
def unconnect():
    if request.method == "GET":
        return render_template("unconnect.html")
    connecter, connectee, err = get_connection_nodes()
    if err:
        return err
    roadmap_id = connecter["map_id"]
    db.execute(
        "DELETE FROM connections WHERE connecter = ? AND connectee = ? AND map_id = ?",
        connecter["id"], connectee["id"], roadmap_id
    )
    return redirect_to_roadmap(roadmap_id)


@app.route("/delete_node")
@login_required
def delete_node():
    """Deletes chosen node"""
    node_id = request.args.get('id')
    if not node_id:
        return render_error("missing node ID")
    nodes = get_owned_node(node_id)
    if not nodes:
        return render_error("node not found or unauthorized")
    else:
        roadmap_id = nodes[0]["map_id"]
        db.execute("DELETE FROM nodes WHERE id = ?", node_id)
        return redirect_to_roadmap(roadmap_id)


@app.route("/move_node", methods=["GET", "POST"])
@login_required
def move_node():
    if request.method == "GET":
        node_id = request.args.get("id")
        if not node_id or not get_owned_node(node_id):
            return render_error("node not found or unauthorized")
        return render_template("move.html", id=node_id)
    node_id = request.form.get("id")
    node = get_owned_node(node_id)
    if not node:
        return render_error("node not found or unauthorized")
    roadmap_id = node[0]["map_id"]
    try:
        new_x = int(request.form.get("x")) - 1
        new_y = int(request.form.get("y")) - 1
    except (TypeError, ValueError):
        return render_error("row and column must be numbers")
    if not (0 <= new_x <= 2) or new_y < 0:
        return render_error("column must be 1-3 and row must be 1 or higher")
    if db.execute(
        "SELECT 1 FROM nodes WHERE map_id = ? AND x = ? AND y = ? AND id != ?",
        roadmap_id, new_x, new_y, node_id
    ):
        return render_error("another node is already in that spot")
    db.execute("UPDATE nodes SET x = ?, y = ? WHERE id = ?", new_x, new_y, node_id)
    return redirect_to_roadmap(roadmap_id)
import os
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from random import shuffle

app = Flask(__name__)

# Configuración de la base de datos
# Cargar las variables desde el archivo .env
load_dotenv()

# Obtener las variables de entorno
host = os.getenv("DB_HOST")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Conectarse a la base de datos
db_config = {
    'host': host,
    'user': user,
    'password': password,
    'database': database
}

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route('/')
@login_required
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        passwordConfirmation = request.form.get("confirmation")

        if not username:
            return render_template("register.html", alert=True, alertMsg="Por favor introduce un usuario")
        if not password:
            return render_template("register.html", alert=True, alertMsg="Por favor introduce una contraseña")
        if not passwordConfirmation:
            return render_template("register.html", alert=True, alertMsg="Please confirm your password")

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = %s", (username,))
        (sameUsernameCount,) = cursor.fetchone()

        cursor.close()
        connection.close()

        if sameUsernameCount != 0:
            return render_template("register.html", alert=True, alertMsg="El usuario ya existe")

        if password != passwordConfirmation:
            return render_template("register.html", alert=True, alertMsg="Las contraseñas no coinciden")

        hash = generate_password_hash(password)

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        cursor.execute("INSERT INTO usuarios (username, hash) VALUES (%s, %s)", (username, hash))
        connection.commit()

        cursor.close()
        connection.close()

        return redirect("/")

    else:
        return render_template("register.html")
    

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    username = request.form.get("username")
    password = request.form.get("password")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not username:
            return render_template("login.html", alert=True, alertMsg = "Introduce el usuario")

        # Ensure password was submitted
        elif not password:
            return render_template("login.html", alert=True, alertMsg = "Introduce la contraseña")

        # Query database for username
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        query = "SELECT id, username, hash FROM usuarios WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            storedId, storedUser, storedHash = result

            # Ensure username exists and password is correct
            if not check_password_hash(storedHash, password):
                return render_template("login.html", alert=True, alertMsg = "Invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = storedId

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/clients")
def clients():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
        
    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()

    
    cursor.close()
    connection.close()

    return render_template('clients.html', clientes=clientes)


if __name__ == '__main__':
    app.run(debug=True)

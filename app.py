import os
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from random import shuffle
import re

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

email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'

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
    return redirect("/clients")


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        passwordConfirmation = request.form.get("confirmation")

        if not username:
            return render_template("register.html", alert=True, alertMsg="Por favor introduce un usuario"), 400
        if not password:
            return render_template("register.html", alert=True, alertMsg="Por favor introduce una contraseña"), 400
        if not passwordConfirmation:
            return render_template("register.html", alert=True, alertMsg="Please confirm your password"), 400

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = %s", (username,))
        (sameUsernameCount,) = cursor.fetchone()

        cursor.close()
        connection.close()

        if sameUsernameCount != 0:
            return render_template("register.html", alert=True, alertMsg="El usuario ya existe"), 400

        if password != passwordConfirmation:
            return render_template("register.html", alert=True, alertMsg="Las contraseñas no coinciden"), 400

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
            return render_template("login.html", alert=True, alertMsg = "Introduce el usuario"), 400

        # Ensure password was submitted
        elif not password:
            return render_template("login.html", alert=True, alertMsg = "Introduce la contraseña"), 400

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
                return render_template("login.html", alert=True, alertMsg = "Invalid username and/or password"), 400

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


@app.route("/clients", methods=["GET"])
def clients():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
        
    cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()

    
    cursor.close()
    connection.close()

    return render_template('clients.html', clientes=clientes)


@app.route("/clients/add", methods=["GET", "POST"])
def addClient():
    if request.method == "GET":
        return render_template("addClients.html")
    else:
        nombre = request.form.get("nombre")
        telefono = request.form.get("telefono")
        correo = request.form.get("mail")
        instagram = request.form.get("ig")
        facebook = request.form.get("fb")
        direccion = request.form.get("direccion")
        razon = request.form.get("razon")
        condicion = request.form.get("condicion")
        cuit = request.form.get("cuit")
        notas = request.form.get("notas")

        if not nombre:
            return render_template("addClients.html", alert=True, alertMsg="Por favor introduce el nombre del cliente"), 400
        
        if not telefono:
            return render_template("addClients.html", alert=True, alertMsg="Por favor introduce el telefono del cliente"), 400
        
        if not correo:
            return render_template("addClients.html", alert=True, alertMsg="Por favor introduce el correo del cliente"), 400
        
        if not direccion:
            return render_template("addClients.html", alert=True, alertMsg="Por favor introduce la direccion del cliente"), 400
        
        if not razon:
            return render_template("addClients.html", alert=True, alertMsg="Por favor introduce la razon social del cliente"), 400
        
        if not condicion:
            return render_template("addClients.html", alert=True, alertMsg="Por favor introduce la condicion ante el IVA del cliente"), 400
        
        if not cuit:
            return render_template("addClients.html", alert=True, alertMsg="Por favor introduce el CUIT del cliente"), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

            # Consulta SQL para insertar datos
        sql = """
            INSERT INTO clientes (
                nombre, telefono, direccion, mail, instagram, facebook, 
                cuit, razon_social, condicion_iva, notas
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """

            # Ejecutar la consulta con los valores
        cursor.execute(sql, (nombre, telefono, direccion, correo, instagram, facebook, cuit, razon, condicion, notas))
        connection.commit()

        cursor.close()
        connection.close()
        
        return redirect("/clients")
    

@app.route("/clients/delete", methods=["POST"])
@login_required
def deleteClient():
    client_ID = request.form.get('id')

    if not client_ID:
        return redirect("/clients"), 400

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM clientes WHERE id = %s", (client_ID,))
    client = cursor.fetchone()

    if not client:
        cursor.close()
        connection.close()
        return redirect("/clients"), 400
    
    cursor.execute("DELETE FROM clientes WHERE id = %s", (client_ID,))
    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/clients")


@app.route("/articles")
@login_required
def articles():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM articulos")
    articulos = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template("articles.html", articulos = articulos)


@app.route("/articles/add", methods=["POST", "GET"])
@login_required
def addArticle():
    if request.method == "GET":
        return render_template("addarticles.html")
    elif request.method == "POST":
        descripcion = request.form.get("descripcion")
        cantidad = request.form.get("cantidad")
        color = request.form.get("color")
        costo = request.form.get("costo")
        valor = request.form.get("valor")

        if not descripcion or not cantidad or not costo or not valor:
            return render_template("addarticles.html", alert = True, alertMsg = "Por favor introduce todos los campos obligatorios"), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)


        sql = """
            INSERT INTO articulos (
                descripcion, cantidad, color, costo, valor
            )
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(sql, (descripcion, cantidad, color, costo, valor))
        connection.commit()

        cursor.close()
        connection.close()

        return redirect("/articles")
    
    
@app.route("/articles/delete", methods=["POST"])
@login_required
def deleteArticle():
    article_ID = request.form.get('id')

    if not article_ID:
        return redirect("/clients"), 400

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM articulos WHERE id = %s", (article_ID,))
    client = cursor.fetchone()

    if not client:
        cursor.close()
        connection.close()
        return redirect("/clients"), 400
    
    cursor.execute("DELETE FROM articulos WHERE id = %s", (article_ID,))
    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/articles")

if __name__ == '__main__':
    app.run(debug=True)

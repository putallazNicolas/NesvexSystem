import os
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from random import shuffle
import re
from urllib.parse import urlparse

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
    return redirect("/orders")


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
    

@app.route("/clients/delete/<int:id>", methods=["GET"])
@login_required
def deleteClient(id):
    if not id:
        return redirect("/clients"), 400

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM clientes WHERE id = %s", (id,))
    client = cursor.fetchone()

    if not client:
        cursor.close()
        connection.close()
        return redirect("/clients"), 400
    
    cursor.execute("DELETE FROM clientes WHERE id = %s", (id,))
    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/clients")


@app.route("/clients/edit/<int:client_id>", methods=["GET", "POST"])
def editClient(client_id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    if request.method == "GET":
        # Obtener los datos del cliente
        cursor.execute("SELECT * FROM clientes WHERE id = %s", (client_id,))
        cliente = cursor.fetchone()

        if not cliente:
            return "Cliente no encontrado", 404

        cursor.close()
        connection.close()
        return render_template("editClient.html", cliente=cliente)

    elif request.method == "POST":
        # Obtener datos del formulario
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

        # Validación de datos obligatorios
        if not nombre or not direccion or not razon or not condicion or not cuit:
            return render_template("editClient.html", cliente={"id": client_id, "nombre": nombre, "telefono": telefono, "mail": correo, "instagram": instagram, "facebook": facebook, "direccion": direccion, "razon_social": razon, "condicion_iva": condicion, "cuit": cuit, "notas": notas}, alert=True, alertMsg="Todos los campos obligatorios deben completarse"), 400

        # Actualizar el cliente en la base de datos
        sql = """
            UPDATE clientes 
            SET nombre = %s, telefono = %s, mail = %s, instagram = %s, facebook = %s, 
                direccion = %s, razon_social = %s, condicion_iva = %s, cuit = %s, notas = %s
            WHERE id = %s
        """
        cursor.execute(sql, (nombre, telefono, correo, instagram, facebook, direccion, razon, condicion, cuit, notas, client_id))
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
    
    
@app.route("/articles/delete/<int:id>", methods=["GET"])
@login_required
def deleteArticle(id):
    if not id:
        return redirect("/clients"), 400

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM articulos WHERE id = %s", (id,))
    client = cursor.fetchone()

    if not client:
        cursor.close()
        connection.close()
        return redirect("/clients"), 400
    
    cursor.execute("DELETE FROM articulos WHERE id = %s", (id,))
    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/articles")


@app.route("/articles/edit/<int:id>", methods=["GET", "POST"])
@login_required
def editArticle(id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    if request.method == "GET":
        cursor.execute("SELECT * FROM articulos WHERE id = %s", (id,))
        articulo = cursor.fetchone()
        cursor.close()
        connection.close()

        if not articulo:
            return "Artículo no encontrado", 404

        return render_template("editarticles.html", articulo=articulo)

    elif request.method == "POST":
        descripcion = request.form.get("descripcion")
        cantidad = request.form.get("cantidad")
        color = request.form.get("color")
        costo = request.form.get("costo")
        valor = request.form.get("valor")

        if not descripcion or not cantidad or not costo or not valor:
            return render_template("editarticles.html", articulo={"id": id, "descripcion": descripcion, "cantidad": cantidad, "color": color, "costo": costo, "valor": valor}, alert=True, alertMsg="Por favor introduce todos los campos obligatorios"), 400

        sql = """
            UPDATE articulos
            SET descripcion = %s, cantidad = %s, color = %s, costo = %s, valor = %s
            WHERE id = %s
        """
        cursor.execute(sql, (descripcion, cantidad, color, costo, valor, id))
        connection.commit()

        cursor.close()
        connection.close()

        return redirect("/articles")
    

@app.route("/orders", methods=["GET"])
@login_required
def orders():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    sql_pedidos = """
    SELECT * FROM pedidos
    ORDER BY FIELD(estado, 'Pendiente de Seña', 'En proceso', 'En entrega', 'Entregado', 'Cancelado') ASC;
    """

    sql_articulos_vendidos = """
    SELECT * FROM articulos_vendidos WHERE pedido_id = %s;
    """

    sql_articulos = """
    SELECT * FROM articulos WHERE id = %s;
    """

    sql_clientes = """
    SELECT * FROM clientes WHERE id = %s;
    """

    cursor.execute(sql_pedidos)
    pedidos = cursor.fetchall()

    for pedido in pedidos:
        cursor.execute(sql_articulos_vendidos, (pedido["id"], ))
        pedido["articulos_vendidos"] = cursor.fetchall()

        pedido["costo"] = 0

        cursor.execute(sql_clientes, (pedido["cliente_id"], ))
        pedido["cliente"] = cursor.fetchone()

        for articulo in pedido["articulos_vendidos"]:
            cursor.execute(sql_articulos, (articulo["id"], ))
            articulo["info"] = cursor.fetchone()
            pedido["costo"] += articulo["info"]["costo"]

    cursor.close()
    connection.close()

    return render_template("orders.html", pedidos=pedidos)
    #return jsonify(data)


@app.route("/orders/add", methods=["GET", "POST"])
@login_required
def createOrder():
    if request.method == "GET":
        # GET CLIENTS AND ARTICLES
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        sql_clients = """
        SELECT * FROM clientes;
        """

        cursor.execute(sql_clients)
        clientes = cursor.fetchall()

        sql_articles = """
        SELECT * FROM articulos;
        """

        cursor.execute(sql_articles)
        articulos = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template("addorders.html", clientes=clientes, articulos=articulos)
    else:
        cliente_id = request.form.get('cliente')
        fecha_entrega = request.form.get('fechaEntrega')

        articulos = []
        for key in request.form:
            if key.startswith("articulos[") and key.endswith("[id]"):
                index = key.split("[")[1].split("]")[0]  # Extraer el índice del artículo
                articulo_id = request.form.get(f"articulos[{index}][id]")
                cantidad = request.form.get(f"articulos[{index}][cantidad]")
                costo_total = request.form.get(f"articulos[{index}][costo_total]")

                articulos.append({
                    "id": articulo_id,
                    "cantidad": int(cantidad) if cantidad else 1,
                    "costo_total": float(costo_total) if costo_total else 0.0
                })

        total_costo = request.form.get('totalCostoPedido')
        total_precio = request.form.get('totalPrecioPedido')
        
        # GET CLIENTS AND ARTICLES
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        sql_pedidos = """
        INSERT INTO pedidos (cliente_id, costo, valor, fecha_de_entrega) VALUES (%s, %s, %s, %s)
        """

        cursor.execute(sql_pedidos, (cliente_id, total_costo, total_precio, fecha_entrega))
        connection.commit()

        pedido_id = cursor.lastrowid

        for articulo in articulos:
            sql_articulo = """
            INSERT INTO articulos_vendidos (articulo_id, pedido_id, cantidad, costo_total) VALUES (%s, %s, %s, %s)
            """

            cursor.execute(sql_articulo, (articulo["id"], pedido_id, articulo["cantidad"], articulo["costo_total"]))
            connection.commit()

        cursor.close()
        connection.close()

        return redirect("/orders")
    

@app.route("/orders/edit/state/<int:id>/next", methods=["GET"])
@login_required
def nextState(id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    sql_select = """
    SELECT estado FROM pedidos WHERE id = %s;
    """

    cursor.execute(sql_select, (id, ))
    pedido = cursor.fetchone()

    sql_update = """
        UPDATE pedidos
        SET estado = %s
        WHERE id = %s
        """

    if pedido["estado"] == "Pendiente de Seña":
        cursor.execute(sql_update, ("En proceso", id))
    elif pedido["estado"] == "En proceso":
        cursor.execute(sql_update, ("En entrega", id))
    elif pedido["estado"] == "En entrega":
        cursor.execute(sql_update, ("Entregado", id))
    elif pedido["estado"] == "Entregado":
        cursor.execute(sql_update, ("Cancelado", id))

    connection.commit()
    cursor.close()
    connection.close()

    referrer_path = urlparse(request.referrer).path  # Obtiene solo la ruta de la URL del referrer

    if referrer_path == "/orders" or referrer_path == "/orders#":
        return redirect("/orders")
    else:
        return redirect("/orders/finished")


@app.route("/orders/edit/state/<int:id>/prev", methods=["GET"])
@login_required
def prevState(id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    sql_select = """
    SELECT estado FROM pedidos WHERE id = %s;
    """

    cursor.execute(sql_select, (id, ))
    pedido = cursor.fetchone()

    sql_update = """
        UPDATE pedidos
        SET estado = %s
        WHERE id = %s
        """

    if pedido["estado"] == "En proceso":
        cursor.execute(sql_update, ("Pendiente de seña", id))
    elif pedido["estado"] == "En entrega":
        cursor.execute(sql_update, ("En proceso", id))
    elif pedido["estado"] == "Entregado":
        cursor.execute(sql_update, ("En entrega", id))
    elif pedido["estado"] == "Cancelado":
        cursor.execute(sql_update, ("Entregado", id))

    connection.commit()
    cursor.close()
    connection.close()

    referrer_path = urlparse(request.referrer).path  # Obtiene solo la ruta de la URL del referrer
    
    if referrer_path == "/orders" or referrer_path == "/orders#":
        return redirect("/orders")
    else:
        return redirect("/orders/finished")
    

if __name__ == '__main__':
    app.run(debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=True) # para celular


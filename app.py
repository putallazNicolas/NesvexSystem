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
database_url = os.getenv("DB_URL")
app.secret_key = os.getenv("FLASK_SECRET_KEY")

db_url = urlparse(database_url)

if database_url:
    host = db_url.hostname
    user = db_url.username
    password = db_url.password
    database = db_url.path[1:]

# Conectarse a la base de datos
db_config = {
    'host': host,
    'user': user,
    'password': password,
    'database': database,
    'charset': 'latin1'
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
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Obtener últimos movimientos
    sql_ultimos_movimientos = """
    SELECT m.*, p.estado as pedido_estado, c.nombre as cliente_nombre 
    FROM movimientos m
    LEFT JOIN pedidos p ON m.id_pedido = p.id
    LEFT JOIN clientes c ON p.cliente_id = c.id
    ORDER BY m.fecha DESC
    LIMIT 5;
    """
    cursor.execute(sql_ultimos_movimientos)
    ultimos_movimientos = cursor.fetchall()

    # Calcular balance, ingresos y egresos totales
    sql_totales = """
    SELECT 
        SUM(CASE WHEN movimiento = 'ingreso' THEN cantidad_dinero ELSE 0 END) as total_ingresos,
        SUM(CASE WHEN movimiento = 'egreso' THEN cantidad_dinero ELSE 0 END) as total_egresos
    FROM movimientos;
    """
    cursor.execute(sql_totales)
    totales = cursor.fetchone()
    balance = float(totales["total_ingresos"] or 0) - float(totales["total_egresos"] or 0)

    # Obtener pedidos pendientes
    sql_pedidos_pendientes = """
    SELECT p.*, c.nombre as cliente_nombre
    FROM pedidos p
    JOIN clientes c ON p.cliente_id = c.id
    WHERE p.estado NOT IN ('Entregado', 'Cancelado')
    ORDER BY p.fecha_de_inicio DESC
    LIMIT 5;
    """
    cursor.execute(sql_pedidos_pendientes)
    pedidos_pendientes = cursor.fetchall()

    # Obtener estadísticas de pedidos
    sql_stats_pedidos = """
    SELECT 
        COUNT(*) as total_pedidos,
        SUM(CASE WHEN estado = 'Pendiente de Seña' THEN 1 ELSE 0 END) as pendiente_sena,
        SUM(CASE WHEN estado = 'En proceso' THEN 1 ELSE 0 END) as en_proceso,
        SUM(CASE WHEN estado = 'En entrega' THEN 1 ELSE 0 END) as en_entrega,
        SUM(CASE WHEN estado = 'Entregado' THEN 1 ELSE 0 END) as entregados,
        SUM(CASE WHEN estado = 'Cancelado' THEN 1 ELSE 0 END) as cancelados
    FROM pedidos;
    """
    cursor.execute(sql_stats_pedidos)
    stats_pedidos = cursor.fetchone()

    # Obtener artículos con poco stock
    sql_stock_bajo = """
    SELECT *
    FROM articulos
    WHERE cantidad <= 5
    ORDER BY cantidad ASC
    LIMIT 5;
    """
    cursor.execute(sql_stock_bajo)
    stock_bajo = cursor.fetchall()

    # Obtener top clientes
    sql_top_clientes = """
    SELECT c.*, COUNT(p.id) as total_pedidos,
           SUM(CASE WHEN p.estado = 'Entregado' THEN p.valor ELSE 0 END) as total_gastado
    FROM clientes c
    LEFT JOIN pedidos p ON c.id = p.cliente_id
    GROUP BY c.id
    ORDER BY total_gastado DESC
    LIMIT 5;
    """
    cursor.execute(sql_top_clientes)
    top_clientes = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("index.html", 
                         ultimos_movimientos=ultimos_movimientos,
                         balance=balance,
                         total_ingresos=float(totales["total_ingresos"] or 0),
                         total_egresos=float(totales["total_egresos"] or 0),
                         pedidos_pendientes=pedidos_pendientes,
                         stats_pedidos=stats_pedidos,
                         stock_bajo=stock_bajo,
                         top_clientes=top_clientes)


@app.route("/register", methods=["GET", "POST"])
#@login_required # unavailable temporally because of first user
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
        return render_template("addclients.html")
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

        if not descripcion or not cantidad or not costo:
            return render_template("addarticles.html", alert = True, alertMsg = "Por favor introduce todos los campos obligatorios"), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        # valor is 0 because of no need of this column
        sql = """
            INSERT INTO articulos (
                descripcion, cantidad, color, costo, valor
            )
            VALUES (%s, %s, %s, %s, 0);
        """
        cursor.execute(sql, (descripcion, cantidad, color, costo))
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

        if not descripcion or not cantidad or not costo:
            return render_template("editarticles.html", articulo={"id": id, "descripcion": descripcion, "cantidad": cantidad, "color": color, "costo": costo}, alert=True, alertMsg="Por favor introduce todos los campos obligatorios"), 400

        sql = """
            UPDATE articulos
            SET descripcion = %s, cantidad = %s, color = %s, costo = %s
            WHERE id = %s
        """
        cursor.execute(sql, (descripcion, cantidad, color, costo, id))
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
        pedido["fecha_de_inicio"] = pedido["fecha_de_inicio"].strftime('%d/%m/%Y')
        pedido["fecha_de_entrega"] = pedido["fecha_de_entrega"].strftime('%d/%m/%Y')

        cursor.execute(sql_articulos_vendidos, (pedido["id"], ))
        pedido["articulos_vendidos"] = cursor.fetchall()

        pedido["costo"] = 0

        cursor.execute(sql_clientes, (pedido["cliente_id"], ))
        pedido["cliente"] = cursor.fetchone()

        for articulo in pedido["articulos_vendidos"]:
            cursor.execute(sql_articulos, (articulo["articulo_id"], ))
            articulo["info"] = cursor.fetchone()
            pedido["costo"] += articulo["info"]["costo"] * articulo["cantidad"]

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

        if not cliente_id or not fecha_entrega or not articulos or not total_precio or total_precio == '0.00':
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
            return render_template("addorders.html", alert=True, alertMsg = "Por favor introduce todos los campos", clientes=clientes, articulos=articulos)
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        sql_pedidos = """
        INSERT INTO pedidos (cliente_id, costo, valor, fecha_de_entrega) VALUES (%s, %s, %s, %s)
        """

        cursor.execute(sql_pedidos, (cliente_id, total_costo, total_precio, fecha_entrega))
        connection.commit()

        pedido_id = cursor.lastrowid

        sql_cliente = """
        UPDATE clientes SET cantidad_compras = cantidad_compras + 1 WHERE id = %s;
        """

        cursor.execute(sql_cliente, (cliente_id,))

        for articulo in articulos:
            sql_articulo = """
            INSERT INTO articulos_vendidos (articulo_id, pedido_id, cantidad, costo_total) VALUES (%s, %s, %s, %s)
            """

            cursor.execute(sql_articulo, (articulo["id"], pedido_id, articulo["cantidad"], articulo["costo_total"]))
            connection.commit()

            sql_stock = """
            UPDATE articulos
            SET cantidad = cantidad - %s
            WHERE id = %s;
            """

            cursor.execute(sql_stock, (articulo["cantidad"], articulo["id"]))
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
    SELECT estado, valor, costo, cliente_id FROM pedidos WHERE id = %s;
    """

    cursor.execute(sql_select, (id, ))
    pedido = cursor.fetchone()

    # Obtener el nombre del cliente para la descripción del movimiento
    cursor.execute("SELECT nombre FROM clientes WHERE id = %s", (pedido["cliente_id"],))
    cliente = cursor.fetchone()

    sql_update = """
        UPDATE pedidos
        SET estado = %s
        WHERE id = %s
        """

    if pedido["estado"] == "Pendiente de Seña":
        cursor.execute(sql_update, ("En proceso", id))
        # Crear movimiento de egreso por el costo
        sql_movimiento = """
        INSERT INTO movimientos (descripcion, movimiento, id_pedido, cantidad_dinero)
        VALUES (%s, 'egreso', %s, %s);
        """
        descripcion = f"Costo de producción - Pedido #{id} - Cliente: {cliente['nombre']}"
        cursor.execute(sql_movimiento, (descripcion, id, pedido["costo"]))

    elif pedido["estado"] == "En proceso":
        cursor.execute(sql_update, ("En entrega", id))
    elif pedido["estado"] == "En entrega":
        cursor.execute(sql_update, ("Entregado", id))
        # Crear movimiento de ingreso por el valor
        sql_movimiento = """
        INSERT INTO movimientos (descripcion, movimiento, id_pedido, cantidad_dinero)
        VALUES (%s, 'ingreso', %s, %s);
        """
        descripcion = f"Pago recibido - Pedido #{id} - Cliente: {cliente['nombre']}"
        cursor.execute(sql_movimiento, (descripcion, id, pedido["valor"]))

    elif pedido["estado"] == "Entregado":
        cursor.execute(sql_update, ("Cancelado", id))

    connection.commit()
    cursor.close()
    connection.close()

    referrer_path = urlparse(request.referrer).path  # Obtiene solo la ruta de la URL del referrer

    if referrer_path == "/orders" or referrer_path == "/orders#":
        return redirect("/orders")
    else:
        return redirect(f"/orders/see/{id}")


@app.route("/orders/edit/state/<int:id>/prev", methods=["GET"])
@login_required
def prevState(id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    sql_select = """
    SELECT estado, valor, costo, cliente_id FROM pedidos WHERE id = %s;
    """

    cursor.execute(sql_select, (id, ))
    pedido = cursor.fetchone()

    # Obtener el nombre del cliente para la descripción del movimiento
    cursor.execute("SELECT nombre FROM clientes WHERE id = %s", (pedido["cliente_id"],))
    cliente = cursor.fetchone()

    sql_update = """
        UPDATE pedidos
        SET estado = %s
        WHERE id = %s
        """

    if pedido["estado"] == "En proceso":
        cursor.execute(sql_update, ("Pendiente de seña", id))
        # Eliminar el movimiento de egreso si existe
        sql_delete_movimiento = """
        DELETE FROM movimientos 
        WHERE id_pedido = %s AND movimiento = 'egreso' 
        AND descripcion LIKE %s;
        """
        descripcion_pattern = f"Costo de producción - Pedido #{id}%"
        cursor.execute(sql_delete_movimiento, (id, descripcion_pattern))

    elif pedido["estado"] == "En entrega":
        cursor.execute(sql_update, ("En proceso", id))
    elif pedido["estado"] == "Entregado":
        cursor.execute(sql_update, ("En entrega", id))
        # Eliminar el movimiento de ingreso si existe
        sql_delete_movimiento = """
        DELETE FROM movimientos 
        WHERE id_pedido = %s AND movimiento = 'ingreso'
        AND descripcion LIKE %s;
        """
        descripcion_pattern = f"Pago recibido - Pedido #{id}%"
        cursor.execute(sql_delete_movimiento, (id, descripcion_pattern))

    elif pedido["estado"] == "Cancelado":
        cursor.execute(sql_update, ("Entregado", id))

    connection.commit()
    cursor.close()
    connection.close()

    referrer_path = urlparse(request.referrer).path  # Obtiene solo la ruta de la URL del referrer
    
    if referrer_path == "/orders" or referrer_path == "/orders#":
        return redirect("/orders")
    else:
        return redirect(f"/orders/see/{id}")
    

@app.route("/orders/edit/info/<int:order_id>", methods=["GET", "POST"])
@login_required
def editOrderInfo(order_id):    
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    sql_pedidos = """
    SELECT * FROM pedidos WHERE id = %s;
    """

    sql_clientes = """
    SELECT * FROM clientes;
    """

    cursor.execute(sql_pedidos, (order_id,))
    pedido = cursor.fetchone()

    cursor.execute(sql_clientes)
    clientes = cursor.fetchall()

    cursor.close()
    connection.close()
    if request.method == "GET":
        return render_template("editorder.html", order=pedido, clientes=clientes)
    elif (request.method == "POST"):
        cliente_id = request.form.get("cliente")
        fecha_de_entrega = request.form.get("fechaEntrega")
        valor = request.form.get("totalPrecioPedido")

        if not cliente_id or not fecha_de_entrega or not valor or valor == 0:
            return render_template("editorder.html", order=pedido, clientes=clientes, alert=True, alertMsg="Por favor introduce todos los campos")

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        sql = """
        UPDATE pedidos
        SET cliente_id = %s, valor = %s, fecha_de_entrega = %s
        WHERE id = %s;
        """

        cursor.execute(sql, (cliente_id, valor, fecha_de_entrega, order_id))
        connection.commit()

        cursor.close()
        connection.close()

        return redirect("/orders")


@app.route("/orders/see/<int:order_id>", methods=["GET"])
@login_required
def seeOrder(order_id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    sql_pedidos = """
    SELECT * FROM pedidos WHERE id = %s;
    """

    sql_clientes = """
    SELECT * FROM clientes WHERE id = %s;
    """

    sql_articulos = """
    SELECT 
        av.id AS articulo_vendido_id,
        av.pedido_id,
        a.id AS id_articulo,
        a.descripcion,
        a.color,
        a.costo,
        av.cantidad AS cantidad_vendida
    FROM articulos_vendidos av
    JOIN articulos a ON av.articulo_id = a.id
    WHERE av.pedido_id = %s;
    """

    cursor.execute(sql_pedidos, (order_id,))
    pedido = cursor.fetchone()

    cursor.execute(sql_clientes, (pedido["cliente_id"],))
    cliente = cursor.fetchone()

    cursor.execute(sql_articulos, (pedido["id"],))
    articulos = cursor.fetchall()

    cursor.close()
    connection.close()

    pedido["fecha_de_inicio"] = pedido["fecha_de_inicio"].strftime('%d/%m/%Y')
    pedido["fecha_de_entrega"] = pedido["fecha_de_entrega"].strftime('%d/%m/%Y')

    pedido["costo"] = 0

    for articulo in articulos:
        pedido["costo"] += articulo["costo"] * articulo["cantidad_vendida"]

    return render_template("order.html", pedido=pedido, cliente=cliente, articulos = articulos)


#@app.route("/CREATEDATABASE", methods=["GET"]) # Unable this route after creating the database
def createdb():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Crear tabla 'usuarios'
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT NOT NULL AUTO_INCREMENT,
            username VARCHAR(100) DEFAULT NULL,
            hash VARCHAR(255) DEFAULT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY unique_username (username)
        );
    """)

    # Crear tabla 'clientes'
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INT NOT NULL AUTO_INCREMENT,
            nombre VARCHAR(255) NOT NULL,
            telefono VARCHAR(20) DEFAULT NULL,
            direccion VARCHAR(255) DEFAULT NULL,
            mail VARCHAR(255) DEFAULT NULL,
            instagram VARCHAR(255) DEFAULT NULL,
            facebook VARCHAR(255) DEFAULT NULL,
            cuit VARCHAR(20) NOT NULL,
            razon_social VARCHAR(255) DEFAULT NULL,
            condicion_iva VARCHAR(255) DEFAULT NULL,
            cantidad_compras INT DEFAULT 0,
            notas TEXT,
            PRIMARY KEY (id)
        );
    """)

    # Crear tabla 'articulos'
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articulos (
            id INT NOT NULL AUTO_INCREMENT,
            descripcion VARCHAR(255) NOT NULL,
            cantidad INT NOT NULL DEFAULT 0,
            color VARCHAR(50) DEFAULT NULL,
            costo DECIMAL(10,2) NOT NULL,
            valor DECIMAL(10,2) NOT NULL,
            PRIMARY KEY (id)
        );
    """)

    # Crear tabla 'pedidos'
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INT NOT NULL AUTO_INCREMENT,
            cliente_id INT NOT NULL,
            estado ENUM('Pendiente de Seña', 'En proceso', 'En entrega', 'Entregado', 'Cancelado') NOT NULL DEFAULT 'Pendiente de Seña',
            costo DECIMAL(10,2) NOT NULL,
            valor DECIMAL(10,2) NOT NULL,
            fecha_de_inicio DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fecha_de_entrega DATETIME DEFAULT NULL,
            PRIMARY KEY (id),
            KEY cliente_id (cliente_id),
            CONSTRAINT pedidos_ibfk_1 FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE,
            CONSTRAINT pedidos_chk_1 CHECK (costo >= 0),
            CONSTRAINT pedidos_chk_2 CHECK (valor >= 0)
        );
    """)

    # Crear tabla 'articulos_vendidos'
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articulos_vendidos (
            id INT NOT NULL AUTO_INCREMENT,
            articulo_id INT NOT NULL,
            pedido_id INT NOT NULL,
            cantidad INT NOT NULL,
            costo_total DECIMAL(10,2) NOT NULL,
            PRIMARY KEY (id),
            KEY articulo_id (articulo_id),
            KEY pedido_id (pedido_id),
            CONSTRAINT articulos_vendidos_ibfk_1 FOREIGN KEY (articulo_id) REFERENCES articulos (id) ON DELETE CASCADE,
            CONSTRAINT articulos_vendidos_ibfk_2 FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE,
            CONSTRAINT articulos_vendidos_chk_1 CHECK (cantidad > 0)
        );
    """)

    connection.commit()
    cursor.close()
    connection.close()

    return redirect("/")
    

@app.route("/orders/delete/<int:order_id>", methods=["GET"])
@login_required
def deleteOrder(order_id):
    # check that order with that ID exists
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    sql_order = """
    SELECT id, cliente_id FROM pedidos WHERE id = %s;
    """

    cursor.execute(sql_order, (order_id,))
    order = cursor.fetchone()

    if not order:
        cursor.close()
        connection.close()

        return "No existe un pedido con esa ID", 404
    
    # delete order, as it exists

    sql_delete = """
    DELETE FROM pedidos WHERE id = %s;
    """

    cursor.execute(sql_delete, (order_id, ))
    connection.commit()

    sql_decrement_orders = """
    UPDATE clientes
    SET cantidad_compras = cantidad_compras - 1
    WHERE id = %s;
    """

    cursor.execute(sql_decrement_orders, (order["cliente_id"],))
    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/orders")


@app.route("/orders/article/delete/<int:article_id>")
@login_required
def deleteArticleFromOrder(article_id):
    #check if article sold exists
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    sql_articulos_vendidos = """
    SELECT id, articulo_id, cantidad, pedido_id FROM articulos_vendidos WHERE id = %s;
    """

    cursor.execute(sql_articulos_vendidos, (article_id,))
    articulo = cursor.fetchone()

    if not articulo:
        cursor.close()
        connection.close()

        return "no existe ese articulo en ese pedido"
    
    sql_delete = """
    DELETE FROM articulos_vendidos WHERE id = %s;
    """

    cursor.execute(sql_delete, (article_id,))
    connection.commit()

    sql_update_stock = """
    UPDATE articulos
    SET cantidad = cantidad + %s
    WHERE id = %s;
    """

    cursor.execute(sql_update_stock, (articulo["cantidad"], articulo["articulo_id"]))
    connection.commit()

    cursor.close()
    connection.close()

    return redirect(f"/orders/see/{articulo["pedido_id"]}")


@app.route("/orders/<int:order_id>/articles/add", methods=["GET", "POST"])
@login_required
def addArticleToOrder(order_id):
    if request.method == "GET":
        # check if order exists
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        sql_order = """
        SELECT p.*, c.nombre as cliente_nombre, c.telefono as cliente_telefono
        FROM pedidos p
        JOIN clientes c ON p.cliente_id = c.id
        WHERE p.id = %s;
        """

        cursor.execute(sql_order, (order_id,))
        pedido = cursor.fetchone()

        if not pedido:
            cursor.close()
            connection.close()
            flash("No existe un pedido con ese ID", "error")
            return redirect("/orders")
        
        # Obtener solo artículos con stock disponible
        sql_articulos = """
        SELECT a.*, 
               COALESCE(
                   (SELECT SUM(av.cantidad) 
                    FROM articulos_vendidos av 
                    WHERE av.articulo_id = a.id AND av.pedido_id = %s), 0
               ) as cantidad_en_pedido
        FROM articulos a
        WHERE a.cantidad > 0
        ORDER BY a.descripcion ASC;
        """

        cursor.execute(sql_articulos, (order_id,))
        articulos = cursor.fetchall()

        if not articulos:
            flash("No hay artículos disponibles con stock", "warning")

        cursor.close()
        connection.close()
        
        return render_template(
            "addArticleToOrder.html", 
            articulos=articulos, 
            order_id=order_id,
            pedido=pedido
        ), 200
    else:
        articulo = request.form.get("articulo")
        cantidad = request.form.get("cantidad")

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        if not articulo or not cantidad:
            sql_order = """
            SELECT id FROM pedidos WHERE id = %s;
            """

            cursor.execute(sql_order, (order_id,))
            pedido = cursor.fetchone()

            if not pedido:
                cursor.close()
                connection.close()

                return "no existe un pedido con esa ID"
            
            sql_articulos = """
            SELECT * FROM articulos;
            """

            cursor.execute(sql_articulos)
            articulos = cursor.fetchall()

            cursor.close()
            connection.close()
            
            return render_template("addArticleToOrder.html", articulos=articulos, order_id=order_id, alert=True, alertMsg="Por favor introduce todos los campos"), 400
        
        sql_articulo_vendido = """
        INSERT INTO articulos_vendidos
        (articulo_id, cantidad, pedido_id, costo_total)
        VALUES
        (%s, %s, %s, %s);
        """

        sql_articulo = """
        SELECT * FROM articulos WHERE id = %s;
        """

        cursor.execute(sql_articulo, (articulo,))
        articulo_info = cursor.fetchone()

        print(type(articulo_info["costo"]))
        print(type(cantidad))

        cursor.execute(sql_articulo_vendido, (articulo, cantidad, order_id, int(cantidad) * float(articulo_info["costo"])))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(f"/orders/see/{order_id}")


@app.route("/movements", methods=["GET"])
@login_required
def movements():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Obtener todos los movimientos ordenados por fecha descendente
    sql_movements = """
    SELECT * FROM movimientos 
    ORDER BY fecha DESC;
    """
    cursor.execute(sql_movements)
    movimientos = cursor.fetchall()

    # Calcular el balance total
    balance = 0
    for movimiento in movimientos:
        if movimiento["movimiento"] == "ingreso":
            balance += float(movimiento["cantidad_dinero"])
        else:
            balance -= float(movimiento["cantidad_dinero"])

    cursor.close()
    connection.close()

    return render_template("movements.html", movimientos=movimientos, balance=balance)


@app.route("/movements/add", methods=["GET", "POST"])
@login_required
def addMovement():
    if request.method == "GET":
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        # Obtener pedidos activos para el selector
        sql_pedidos = """
        SELECT p.id, p.estado, c.nombre as cliente_nombre
        FROM pedidos p
        JOIN clientes c ON p.cliente_id = c.id
        WHERE p.estado NOT IN ('Entregado', 'Cancelado')
        ORDER BY p.fecha_de_inicio DESC;
        """
        cursor.execute(sql_pedidos)
        pedidos = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template("addmovement.html", pedidos=pedidos)
    else:
        descripcion = request.form.get("descripcion")
        tipo = request.form.get("tipo")
        pedido = request.form.get("pedido")
        monto = request.form.get("monto")

        if not descripcion or not tipo or not monto:
            return render_template("addmovement.html", alert=True, alertMsg="Por favor completa todos los campos requeridos"), 400

        try:
            monto = float(monto)
            if monto <= 0:
                return render_template("addmovement.html", alert=True, alertMsg="El monto debe ser mayor a 0"), 400
        except ValueError:
            return render_template("addmovement.html", alert=True, alertMsg="El monto debe ser un número válido"), 400

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        sql = """
        INSERT INTO movimientos (descripcion, movimiento, id_pedido, cantidad_dinero)
        VALUES (%s, %s, %s, %s);
        """

        pedido_id = int(pedido) if pedido else None
        cursor.execute(sql, (descripcion, tipo, pedido_id, monto))
        connection.commit()

        cursor.close()
        connection.close()

        return redirect("/movements")


@app.route("/movements/delete/<int:movement_id>", methods=["GET"])
@login_required
def deleteMovement(movement_id):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Verificar si el movimiento existe
    cursor.execute("SELECT id FROM movimientos WHERE id = %s", (movement_id,))
    movement = cursor.fetchone()

    if not movement:
        cursor.close()
        connection.close()
        return "Movimiento no encontrado", 404

    # Eliminar el movimiento
    cursor.execute("DELETE FROM movimientos WHERE id = %s", (movement_id,))
    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/movements")


if __name__ == '__main__':
    app.run(debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=True) # para celular
    #los dos siguientes son para deployment
    #port = int(os.environ.get('PORT', 5000))  # Usa el puerto de Render o el 5000 por defecto
    #app.run(host='0.0.0.0', port=port)


# Sistema de Gestión - Consentido Visual

Sistema de gestión empresarial diseñado específicamente para Consentido Visual, que permite administrar pedidos, clientes, inventario y finanzas.

## Características Principales

### Panel de Control
- Vista general del estado financiero (ingresos, egresos y balance)
- Estadísticas de pedidos en tiempo real
- Últimos movimientos financieros
- Pedidos pendientes
- Alertas de stock bajo
- Ranking de mejores clientes

### Gestión de Pedidos
- Creación y seguimiento de pedidos
- Estados del pedido:
  - Pendiente de Seña
  - En proceso
  - En entrega
  - Entregado
  - Cancelado
- Asociación automática con clientes
- Cálculo automático de costos y precios
- Registro automático de movimientos financieros al cambiar estados

### Gestión de Clientes
- Base de datos completa de clientes
- Registro de datos de contacto
- Historial de pedidos por cliente
- Seguimiento de compras totales
- Información fiscal (CUIT, condición IVA)

### Control de Inventario
- Gestión de artículos y stock
- Alertas de stock bajo
- Registro de costos y precios
- Seguimiento de artículos vendidos

### Control Financiero
- Registro detallado de ingresos y egresos
- Vinculación de movimientos con pedidos
- Balance general
- Historial de transacciones
- Reportes financieros en tiempo real

## Requisitos Técnicos

### Dependencias Principales
- Python 3.x
- Flask
- MySQL
- Bootstrap 5
- Font Awesome

### Configuración del Entorno
1. Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:
```
DB_HOST=tu_host
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_NAME=nombre_base_de_datos
FLASK_SECRET_KEY=tu_clave_secreta
```

2. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

3. Inicializar la base de datos:
```bash
python app.py
```

## Estructura de la Base de Datos

### Tablas Principales
- `usuarios`: Gestión de accesos al sistema
- `clientes`: Información de clientes
- `articulos`: Inventario de productos
- `pedidos`: Registro de pedidos
- `articulos_vendidos`: Detalle de artículos por pedido
- `movimientos`: Registro financiero

## Uso del Sistema

1. **Acceso**
   - Ingresar con usuario y contraseña
   - Panel de control como página principal

2. **Gestión de Pedidos**
   - Crear nuevo pedido
   - Seleccionar cliente
   - Agregar artículos
   - Gestionar estado del pedido

3. **Control Financiero**
   - Registro automático al procesar pedidos
   - Ingreso manual de otros movimientos
   - Consulta de balance y movimientos

4. **Inventario**
   - Agregar nuevos artículos
   - Actualizar stock
   - Monitorear niveles de inventario

## Seguridad
- Autenticación requerida para todas las operaciones
- Contraseñas encriptadas
- Validación de datos en todas las operaciones
- Protección contra SQL injection

## Licencia

Todos los derechos reservados - Consentido Visual
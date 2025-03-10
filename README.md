# Nesvex System - Sistema de Gestión de Pedidos

Sistema web para la gestión de pedidos, clientes, artículos y movimientos financieros de un negocio de diseño visual.

## Características

- 🔐 Sistema de autenticación seguro con sesiones únicas por dispositivo
- 👥 Gestión de usuarios con roles de administrador
- 👥 Gestión de clientes con información detallada
- 📦 Control de inventario de artículos
- 🛍️ Gestión de pedidos con estados y seguimiento
- 💰 Control de movimientos financieros (ingresos/egresos)
- 📊 Dashboard con estadísticas y alertas
- ⚙️ Configuración personalizable

## Requisitos

- Python 3.8 o superior
- MySQL 5.7 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/putallazNicolas/NesvexSystem.git
cd NesvexSystem
```

2. Crear y activar un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Crear archivo `.env` con las siguientes variables:
```env
DB_HOST=localhost
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_NAME=el_nombre_de_tu_base_de_datos
DB_URL=mysql://usuario:contraseña@host:puerto/nombre_db
FLASK_SECRET_KEY=tu_clave_secreta
MAX_USERS=10  # Opcional: límite de usuarios
```

5. Iniciar la aplicación:
```bash
python app.py
```

## Estructura de la Base de Datos

El sistema utiliza las siguientes tablas:

- `usuarios`: Gestión de usuarios y autenticación
- `clientes`: Información de clientes
- `articulos`: Inventario de productos
- `pedidos`: Gestión de pedidos
- `articulos_vendidos`: Detalle de artículos en pedidos
- `movimientos`: Registro de transacciones financieras
- `configuracion`: Ajustes del sistema

## Características de Seguridad

- Autenticación mediante hash de contraseñas
- Sesiones únicas por dispositivo
- Protección contra inyección SQL
- Validación de datos de entrada
- Control de acceso basado en roles

## Uso

1. Acceder a `http://localhost:5000`
2. Iniciar sesión con las credenciales por defecto:
   - Usuario: admin
   - Contraseña: admin
3. Cambiar la contraseña del administrador en la primera sesión

## Despliegue

La aplicación está configurada para desplegarse en servicios como Railway. Para desplegar:

1. Configurar las variables de entorno en la plataforma
2. Conectar con el repositorio Git
3. Configurar la base de datos MySQL
4. Desplegar la aplicación

## Contribución

1. Fork el repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## Contacto

Nicolás Putallaz - nfputallaz@gmail.com

Si te interesa usar el sistema para tu negocio, no dudes en contactarme!

Link del Proyecto: [https://github.com/tu-usuario/NesvexSystem](https://github.com/putallazNicolas/NesvexSystem.git)

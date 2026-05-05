import sqlite3
import functools
from flask import Flask, request, jsonify, render_template_string, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DATABASE = "tareas.db"

HTML_TAREAS = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Mis Tareas</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; }
        h1 { color: #2c3e50; }
        ul { list-style: none; padding: 0; }
        li { background: #f4f4f4; margin: 8px 0; padding: 12px 16px; border-radius: 6px; display: flex; justify-content: space-between; }
        .vacio { color: #888; font-style: italic; }
        .usuario { color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>Bienvenido, {{ usuario }}!</h1>
    <p class="usuario">Tus tareas:</p>
    {% if tareas %}
    <ul>
        {% for tarea in tareas %}
        <li>
            <span>#{{ tarea.id }} — {{ tarea.descripcion }}</span>
            <span style="color:#999; font-size:0.8em;">{{ tarea.creada_en }}</span>
        </li>
        {% endfor %}
    </ul>
    {% else %}
    <p class="vacio">No tenés tareas registradas todavía.</p>
    {% endif %}
</body>
</html>
"""

HTML_NO_AUTORIZADO = """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>No autorizado</title></head>
<body>
    <h2>No estás logueado.</h2>
    <p>Debés autenticarte para acceder a tus tareas.</p>
</body>
</html>
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                descripcion TEXT NOT NULL,
                creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );
        """
        )
        db.commit()


def verificar_credenciales(usuario, password):
    db = get_db()
    fila = db.execute(
        "SELECT id, password_hash FROM usuarios WHERE usuario = ?", (usuario,)
    ).fetchone()
    if fila and check_password_hash(fila["password_hash"], password):
        return fila["id"]
    return None


def auth_required(f):
    @functools.wraps(f)
    def decorador(*args, **kwargs):
        auth = request.authorization
        if not auth:
            acepta_html = "text/html" in request.headers.get("Accept", "")
            if acepta_html:
                return (
                    HTML_NO_AUTORIZADO,
                    401,
                    {"WWW-Authenticate": 'Basic realm="Tareas"'},
                )
            return (
                jsonify(
                    {"error": "No estás logueado. Enviá credenciales via Basic Auth."}
                ),
                401,
            )

        usuario_id = verificar_credenciales(auth.username, auth.password)
        if usuario_id is None:
            return jsonify({"error": "Credenciales inválidas."}), 401

        g.usuario_id = usuario_id
        g.usuario_nombre = auth.username
        return f(*args, **kwargs)

    return decorador


@app.route("/registro", methods=["POST"])
def registro():
    datos = request.get_json()
    if not datos or not datos.get("usuario") or not datos.get("password"):
        return jsonify({"error": "Se requieren 'usuario' y 'password'."}), 400

    nombre = datos["usuario"].strip()
    password = datos["password"]
    # Agregué este chequeo para evitar que el usuario ingrese nombres de usuario o contraseñas vacíos
    if len(nombre) < 3:
        return jsonify({"error": "El usuario debe tener al menos 3 caracteres."}), 400
    if len(password) < 4:
        return (
            jsonify({"error": "La contraseña debe tener al menos 4 caracteres."}),
            400,
        )

    hash_pw = generate_password_hash(password)
    db = get_db()
    try:
        db.execute(
            "INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)",
            (nombre, hash_pw),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "El usuario ya existe."}), 409

    return jsonify({"mensaje": f"Usuario '{nombre}' registrado exitosamente."}), 201


@app.route("/login", methods=["POST"])
def login():
    datos = request.get_json()
    if not datos or not datos.get("usuario") or not datos.get("password"):
        return jsonify({"error": "Se requieren 'usuario' y 'password'."}), 400

    usuario_id = verificar_credenciales(datos["usuario"], datos["password"])
    if usuario_id is None:
        return jsonify({"error": "Credenciales inválidas."}), 401

    return jsonify({"mensaje": f"Bienvenido, {datos['usuario']}!"}), 200


@app.route("/tareas", methods=["GET"])
@auth_required
def get_tareas():
    db = get_db()
    filas = db.execute(
        "SELECT id, descripcion, creada_en FROM tareas WHERE usuario_id = ? ORDER BY id",
        (g.usuario_id,),
    ).fetchall()
    tareas = [dict(f) for f in filas]

    acepta_html = "text/html" in request.headers.get("Accept", "")
    if acepta_html:
        return render_template_string(
            HTML_TAREAS, usuario=g.usuario_nombre, tareas=tareas
        )

    return jsonify({"usuario": g.usuario_nombre, "tareas": tareas}), 200


@app.route("/tareas", methods=["POST"])
@auth_required
def crear_tarea():
    datos = request.get_json()
    if not datos or not datos.get("descripcion", "").strip():
        return jsonify({"error": "Se requiere 'descripcion'."}), 400

    descripcion = datos["descripcion"].strip()
    db = get_db()
    cursor = db.execute(
        "INSERT INTO tareas (usuario_id, descripcion) VALUES (?, ?)",
        (g.usuario_id, descripcion),
    )
    db.commit()
    return (
        jsonify(
            {
                "mensaje": "Tarea creada.",
                "id": cursor.lastrowid,
                "descripcion": descripcion,
            }
        ),
        201,
    )


@app.route("/tareas/<int:tarea_id>", methods=["DELETE"])
@auth_required
def eliminar_tarea(tarea_id):
    db = get_db()
    tarea = db.execute(
        "SELECT id FROM tareas WHERE id = ? AND usuario_id = ?",
        (tarea_id, g.usuario_id),
    ).fetchone()

    if tarea is None:
        return jsonify({"error": "Tarea no encontrada o no te pertenece."}), 404

    db.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
    db.commit()
    return jsonify({"mensaje": f"Tarea #{tarea_id} eliminada."}), 200


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)

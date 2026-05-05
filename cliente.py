import requests

BASE_URL = "http://127.0.0.1:5001"

sesion = {"usuario": None, "password": None}


def auth():
    return (sesion["usuario"], sesion["password"]) if sesion["usuario"] else None


def registrar():
    usuario = input("  Nombre de usuario: ").strip()
    password = input("  Contraseña: ").strip()
    try:
        r = requests.post(
            f"{BASE_URL}/registro", json={"usuario": usuario, "password": password}
        )
        datos = r.json()
        print(f"  [{r.status_code}] {datos.get('mensaje') or datos.get('error')}")
    except requests.ConnectionError:
        print("  Error: no se puede conectar al servidor.")


def login():
    usuario = input("  Usuario: ").strip()
    password = input("  Contraseña: ").strip()
    try:
        r = requests.post(
            f"{BASE_URL}/login", json={"usuario": usuario, "password": password}
        )
        datos = r.json()
        if r.status_code == 200:
            sesion["usuario"] = usuario
            sesion["password"] = password
        print(f"  [{r.status_code}] {datos.get('mensaje') or datos.get('error')}")
    except requests.ConnectionError:
        print("  Error: no se puede conectar al servidor.")


def ver_tareas():
    try:
        r = requests.get(f"{BASE_URL}/tareas", auth=auth())
        if r.status_code == 401:
            print("  No estás logueado.")
            return
        datos = r.json()
        tareas = datos.get("tareas", [])
        if not tareas:
            print("  No tenés tareas registradas.")
        else:
            print(f"  Tareas de {datos['usuario']}:")
            for t in tareas:
                print(f"    #{t['id']} — {t['descripcion']}  ({t['creada_en']})")
    except requests.ConnectionError:
        print("  Error: no se puede conectar al servidor.")


def crear_tarea():
    descripcion = input("  Descripción de la tarea: ").strip()
    if not descripcion:
        print("  La descripción no puede estar vacía.")
        return
    try:
        r = requests.post(
            f"{BASE_URL}/tareas", json={"descripcion": descripcion}, auth=auth()
        )
        datos = r.json()
        print(
            f"  [{r.status_code}] {datos.get('mensaje') or datos.get('error')}", end=""
        )
        if r.status_code == 201:
            print(f" (id: {datos['id']})", end="")
        print()
    except requests.ConnectionError:
        print("  Error: no se puede conectar al servidor.")


def eliminar_tarea():
    ver_tareas()
    try:
        tarea_id = int(input("  ID de la tarea a eliminar: ").strip())
    except ValueError:
        print("  ID inválido.")
        return
    try:
        r = requests.delete(f"{BASE_URL}/tareas/{tarea_id}", auth=auth())
        datos = r.json()
        print(f"  [{r.status_code}] {datos.get('mensaje') or datos.get('error')}")
    except requests.ConnectionError:
        print("  Error: no se puede conectar al servidor.")


def cerrar_sesion():
    sesion["usuario"] = None
    sesion["password"] = None
    print("  Sesión cerrada.")


MENU = [
    ("Registrar usuario", registrar),
    ("Iniciar sesión", login),
    ("Ver mis tareas", ver_tareas),
    ("Crear tarea", crear_tarea),
    ("Eliminar tarea", eliminar_tarea),
    ("Cerrar sesión", cerrar_sesion),
    ("Salir", None),
]


def main():
    print("=== Sistema de Gestión de Tareas ===")
    while True:
        logueado = (
            f"(logueado como {sesion['usuario']})"
            if sesion["usuario"]
            else "(sin sesión)"
        )
        print(f"\n{logueado}")
        for i, (nombre, _) in enumerate(MENU, 1):
            print(f"  {i}. {nombre}")

        opcion = input("Elegí una opción: ").strip()
        if not opcion.isdigit() or not (1 <= int(opcion) <= len(MENU)):
            print("  Opción inválida.")
            continue

        idx = int(opcion) - 1
        nombre, accion = MENU[idx]

        if accion is None:
            print("  ¡Hasta luego!")
            break

        if (
            accion in (ver_tareas, crear_tarea, eliminar_tarea, cerrar_sesion)
            and not sesion["usuario"]
        ):
            print("  Necesitás iniciar sesión primero.")
            continue

        print(f"\n--- {nombre} ---")
        accion()


if __name__ == "__main__":
    main()

from flask import Flask, request, send_file, render_template
from generar_factura import generar_factura_A, generar_factura_B
from datetime import datetime
import re
import os

# from flask_cors import CORS  # si sirves HTML desde otro dominio
app = Flask(__name__, static_folder="static", template_folder="templates")
# CORS(app)

CANTIDAD_MAP = {
    "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiuno": 21, "veintidós": 22, "veintitrés": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiséis": 26, "veintisiete": 27,
    "veintiocho": 28, "veintinueve": 29, "treinta": 30, "treinta y uno": 31,
    "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
    "ochenta": 80, "noventa": 90, "cien": 100
}

@app.route("/")
def home():
    return render_template("index.html")

def _safe_nombre_cliente(nombre: str) -> str:
    """
    Normaliza el nombre para usarlo en el filename:
    - trim
    - espacios -> guiones bajos
    - elimina caracteres inválidos para nombres de archivo
    """
    nombre = (nombre or "").strip()
    if not nombre:
        return "Cliente"
    nombre = nombre.replace(" ", "_")
    nombre = re.sub(r'[\\/:*?"<>|]+', "", nombre)
    return nombre or "Cliente"

@app.route("/generar_desde_texto", methods=["POST"])
def generar_desde_texto():
    mensaje = request.form.get("mensaje")
    plantilla = (request.form.get("plantilla") or "A").upper()
    if not mensaje:
        return "❌ No se recibió el texto", 400

    try:
        cliente, estado, fecha, productos = parsear_mensaje(mensaje)
        if not productos:
            return "❌ No se encontraron productos válidos.", 400

        productos.sort(key=lambda x: x[1].lower())
        fecha_valida = procesar_fecha(fecha)  # dd/mm/YYYY

        if plantilla == "B":
            pdf_stream = generar_factura_B(cliente, estado, fecha_valida, productos)
        else:
            pdf_stream = generar_factura_A(cliente, estado, fecha_valida, productos)

        # === Nombre de salida: [CLIENTE]_Comprobante[FECHA].pdf ===
        cliente_safe = _safe_nombre_cliente(cliente)
        fecha_filename = fecha_valida.replace("/", "-")  # dd-mm-YYYY
        filename = f"{cliente_safe}_Comprobante{fecha_filename}.pdf"

        return send_file(
            pdf_stream,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print("Error /generar_desde_texto:", e, flush=True)
        return f"❌ Error al procesar el mensaje: {e}", 500


def parsear_mensaje(mensaje):
    """
    Formato:
      cliente <nombre> estado <texto> fecha <dd/mm/yyyy|hoy> <cantidad> <descripcion...> a <precio> ...
    """
    tokens = mensaje.strip().split()
    cliente, estado, fecha = "", "", ""
    productos = []
    i = 0
    while i < len(tokens):
        token = tokens[i].lower()

        if token == "cliente":
            i, cliente = leer_seccion(tokens, i + 1, ["estado", "fecha"])

        elif token == "estado":
            i += 1
            if i < len(tokens):
                estado = tokens[i]
                i += 1

        elif token == "fecha":
            i += 1
            if i < len(tokens):
                fecha = tokens[i]
                i += 1

        elif re.match(r"^\d+$", token) or token in CANTIDAD_MAP:
            cantidad = int(token) if token.isdigit() else CANTIDAD_MAP.get(token, 1)
            i += 1

            desc_parts = []
            while i < len(tokens) and tokens[i].lower() != "a":
                desc_parts.append(tokens[i])
                i += 1

            if i < len(tokens) and tokens[i].lower() == "a":
                i += 1

            precio = 0.0
            if i < len(tokens):
                raw = tokens[i].replace(",", ".")
                try:
                    precio = float(raw)
                except:
                    precio = 0.0
                i += 1

            descripcion = " ".join(desc_parts).strip()
            total = cantidad * precio
            if descripcion:
                productos.append([cantidad, descripcion, precio, total])

        else:
            i += 1

    return cliente, estado, fecha, productos


def leer_seccion(tokens, start_index, stop_words):
    partes = []
    i = start_index
    while i < len(tokens) and tokens[i].lower() not in stop_words:
        partes.append(tokens[i])
        i += 1
    return i, " ".join(partes).strip()


def procesar_fecha(fecha_str):
    if not fecha_str:
        return datetime.today().strftime("%d/%m/%Y")
    if fecha_str.lower() == "hoy":
        return datetime.today().strftime("%d/%m/%Y")
    try:
        return datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%d/%m/%Y")
    except:
        return datetime.today().strftime("%d/%m/%Y")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

from flask import Flask, request, send_file, render_template
from generar_factura import (
    generar_factura_A,
    generar_factura_B,
)
from datetime import datetime
import re
import os
from typing import List, Tuple

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

class ValidacionError(ValueError):
    """Errores recuperables al analizar o validar el texto recibido."""


HEADER_PATTERNS = {
    "cliente": re.compile(r"^cliente\s*[:\-]?\s*(?P<valor>.+)$", re.IGNORECASE),
    "estado": re.compile(r"^estado\s*[:\-]?\s*(?P<valor>.+)$", re.IGNORECASE),
    "fecha": re.compile(r"^fecha\s*[:\-]?\s*(?P<valor>.+)$", re.IGNORECASE),
}

PRICE_PATTERN = re.compile(
    r"(?P<precio>[\$qQ]?\s*\d+(?:[.,]\d+)?)(?:\s*(?:c/u|cada\s+uno|unidad|u)?)\s*$",
    re.IGNORECASE,
)

CONNECTORES_TOTALES = {"a", "x", "por", "precio", "cada", "c/u"}
MAX_TOKENS_CANTIDAD = 4


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
    plantilla = (request.form.get("plantilla") or "A").upper()
    mensaje = request.form.get("mensaje")
    cliente_form = (request.form.get("cliente") or "").strip()
    estado_form = (request.form.get("estado") or "").strip()
    fecha_form = (request.form.get("fecha") or "").strip()
    productos_texto = request.form.get("productos")
    monto_parcial_raw = request.form.get("monto_parcial")

    modo_formulario = any([cliente_form, estado_form, fecha_form, productos_texto])

    try:
        if modo_formulario:
            cliente = cliente_form
            estado = estado_form
            fecha = fecha_form or "HOY"
            productos = parsear_productos(productos_texto)

            if not cliente:
                raise ValidacionError("Ingresa el nombre del cliente.")
            if not estado:
                raise ValidacionError("Selecciona un estado para el pedido.")
            if not fecha:
                raise ValidacionError("Selecciona una fecha válida.")

            fecha_valida = procesar_fecha(fecha)
            productos.sort(key=lambda x: x[1].lower())
            total_factura = sum(p[3] for p in productos)
            if total_factura <= 0:
                raise ValidacionError("El total calculado es 0. Revisa los productos ingresados.")

            pago_parcial = _interpretar_pago_parcial(estado, monto_parcial_raw)
            if pago_parcial and pago_parcial > total_factura:
                raise ValidacionError("El pago parcial no puede ser mayor al total calculado.")
        else:
            if not mensaje:
                return "❌ No se recibió el texto", 400

            cliente, estado, fecha, productos = parsear_mensaje(mensaje)

            if not cliente:
                raise ValidacionError("Falta el nombre del cliente (línea 'CLIENTE ...').")
            if not estado:
                raise ValidacionError("Falta el estado del pedido (línea 'ESTADO ...').")
            if not fecha:
                raise ValidacionError("Falta la fecha (línea 'FECHA dd/mm/aaaa' o 'FECHA HOY').")
            if not productos:
                raise ValidacionError("No se encontraron productos con el formato 'cantidad descripción a precio'.")

            productos.sort(key=lambda x: x[1].lower())
            fecha_valida = procesar_fecha(fecha)

            total_factura = sum(p[3] for p in productos)
            if total_factura <= 0:
                raise ValidacionError("El total calculado es 0. Revisa los precios ingresados.")

            pago_parcial = 0.0

        if plantilla == "B":
            pdf_stream = generar_factura_B(
                cliente,
                estado,
                fecha_valida,
                productos,
                pago_parcial=pago_parcial,
            )
        else:
            pdf_stream = generar_factura_A(
                cliente,
                estado,
                fecha_valida,
                productos,
                pago_parcial=pago_parcial,
            )

        # === Nombre de salida: [CLIENTE]_Comprobante[FECHA].pdf ===
        cliente_safe = _safe_nombre_cliente(cliente)
        fecha_filename = fecha_valida.replace("/", "-")  # dd-mm-YYYY
        filename = f"{cliente_safe}_Comprobante{fecha_filename}.pdf"

        pdf_stream.seek(0)
        return send_file(
            pdf_stream,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except ValidacionError as e:
        return f"❌ {e}", 422
    except Exception as e:
        print("Error /generar_desde_texto:", e, flush=True)
        return f"❌ Error al procesar el mensaje: {e}", 500


def parsear_mensaje(mensaje: str) -> Tuple[str, str, str, List[List[float]]]:
    """Analiza el bloque de texto línea a línea para extraer datos y productos."""
    if not mensaje or not mensaje.strip():
        raise ValidacionError("El mensaje está vacío.")

    cliente, estado, fecha = "", "", ""
    productos: List[List[float]] = []
    errores_producto = []

    lineas = [line.strip() for line in mensaje.splitlines()]
    for numero, linea in enumerate(lineas, start=1):
        if not linea:
            continue

        encabezado = _extraer_encabezado(linea)
        if encabezado:
            campo, valor = encabezado
            if campo == "cliente":
                cliente = valor
            elif campo == "estado":
                estado = valor
            elif campo == "fecha":
                fecha = valor
            continue

        if _parece_linea_producto(linea):
            try:
                productos.append(_parsear_linea_producto(linea))
            except ValidacionError as exc:
                errores_producto.append(f"Línea {numero}: {exc}")

    if errores_producto:
        raise ValidacionError("\n".join(errores_producto))

    return cliente.strip(), estado.strip(), fecha.strip(), productos


def parsear_productos(texto: str) -> List[List[float]]:
    """Analiza únicamente las líneas de productos.

    Está pensado para el nuevo formulario guiado que ya recibe los datos
    generales (cliente, estado, fecha) por separado.
    """
    if texto is None:
        raise ValidacionError("Agrega al menos un producto.")

    lineas = [line.strip() for line in texto.splitlines()]
    productos: List[List[float]] = []
    errores: List[str] = []
    for numero, linea in enumerate(lineas, start=1):
        if not linea:
            continue
        if not _linea_formulario_valida(linea):
            errores.append(
                f"Línea {numero}: Usa el formato '3 producto a 65', iniciando con la cantidad en números."
            )
            continue
        try:
            productos.append(_parsear_linea_producto(linea))
        except ValidacionError as exc:
            errores.append(f"Línea {numero}: {exc}")

    if errores:
        raise ValidacionError("\n".join(errores))
    if not productos:
        raise ValidacionError("Agrega al menos un producto con formato 'cantidad descripción a precio'.")
    return productos


def _extraer_encabezado(linea: str):
    for campo, patron in HEADER_PATTERNS.items():
        match = patron.match(linea)
        if match:
            valor = match.group("valor").strip()
            return campo, valor
    return None


def _linea_formulario_valida(linea: str) -> bool:
    tokens = linea.split()
    if not tokens:
        return False
    return tokens[0].isdigit()


def _parece_linea_producto(linea: str) -> bool:
    tokens = linea.split()
    if not tokens:
        return False
    primer = tokens[0].lower()
    if primer.isdigit():
        return True
    return primer in CANTIDAD_MAP


def _parsear_linea_producto(linea: str) -> List[float]:
    tokens = linea.split()
    cantidad, usados = _interpretar_cantidad(tokens)
    if cantidad is None:
        raise ValidacionError("No se reconoce la cantidad inicial.")

    resto = " ".join(tokens[usados:]).strip()
    if not resto:
        raise ValidacionError("Falta la descripción del producto.")

    precio_match = PRICE_PATTERN.search(resto)
    if not precio_match:
        raise ValidacionError("No se identificó el precio al final de la línea.")

    precio = _normalizar_precio(precio_match.group("precio"))
    descripcion = resto[:precio_match.start()].strip()
    descripcion = _limpiar_conectores(descripcion)

    if not descripcion:
        raise ValidacionError("Falta la descripción antes del precio.")

    total = cantidad * precio
    return [cantidad, descripcion, precio, total]


def _interpretar_cantidad(tokens: List[str]):
    if not tokens:
        return None, 0
    primer = tokens[0]
    if primer.isdigit():
        return int(primer), 1

    max_span = min(MAX_TOKENS_CANTIDAD, len(tokens))
    for span in range(max_span, 0, -1):
        candidato = " ".join(tokens[:span]).lower()
        if candidato in CANTIDAD_MAP:
            return CANTIDAD_MAP[candidato], span
    return None, 0


def _normalizar_precio(valor: str) -> float:
    valor = valor.strip()
    valor = valor.replace("Q", "").replace("q", "").replace("$", "")
    valor = valor.replace(" ", "")
    valor = valor.replace(",", ".")
    if valor.count(".") > 1:
        partes = valor.split(".")
        valor = "".join(partes[:-1]) + "." + partes[-1]
    try:
        precio = float(valor)
    except ValueError as exc:
        raise ValidacionError(f"Precio inválido: '{valor}'") from exc
    if precio < 0:
        raise ValidacionError("El precio no puede ser negativo.")
    return precio


def _limpiar_conectores(texto: str) -> str:
    texto = texto.strip().rstrip("-:")
    tokens = texto.split()
    while tokens and tokens[-1].lower() in CONNECTORES_TOTALES:
        tokens.pop()
    return " ".join(tokens).strip()


def procesar_fecha(fecha_str: str) -> str:
    if not fecha_str:
        raise ValidacionError("Debes indicar una fecha (por ejemplo, FECHA HOY).")
    fecha_str = fecha_str.strip()
    if fecha_str.lower() == "hoy":
        return datetime.today().strftime("%d/%m/%Y")

    formatos = ("%d/%m/%Y", "%Y-%m-%d")
    for formato in formatos:
        try:
            return datetime.strptime(fecha_str, formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValidacionError("La fecha debe tener el formato dd/mm/aaaa, yyyy-mm-dd o ser 'HOY'.")


def _interpretar_pago_parcial(estado: str, valor: str) -> float:
    if (estado or "").strip().upper() != "PAGO PARCIAL":
        return 0.0
    if valor is None or not valor.strip():
        raise ValidacionError("Ingresa el monto del pago parcial.")
    try:
        monto = float(valor)
    except ValueError as exc:
        raise ValidacionError("El monto del pago parcial no es válido.") from exc
    if monto <= 0:
        raise ValidacionError("El pago parcial debe ser mayor a 0.")
    return monto


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

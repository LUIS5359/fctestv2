# generar_factura.py
import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader, simpleSplit

# =========================
# CONFIGURACIÓN DE TEMAS
# =========================
THEMES = {
    "A": {
        "title": "Kim's Sports",
        "primary": colors.HexColor("#003366"),
        "accent":  colors.HexColor("#666666"),
        "note":    colors.HexColor("#444444"),
        "line":    colors.HexColor("#333333"),
        "address": "0Av Zona 2, San Francisco El Alto Totonicapan a 150 mts. del entronque",
        "phone":   "3256-6671 o 3738-5499",
        "logo":    "static/logo.png",
    },
    "B": {
        "title": "Kim's Sports",
        "primary": colors.HexColor("#0F766E"),
        "accent":  colors.HexColor("#14B8A6"),
        "note":    colors.HexColor("#475569"),
        "line":    colors.HexColor("#334155"),
        "address": "1a. Calle Barrio Xolve, 1 cuadra debajo de banco Banrural, Salida a Momostenango. San Francisco Totonicapán.",
        "phone":   "4654-6282",
        "logo":    "static/logo_b.png",
    },
}

# =========================
# Constantes de layout
# =========================
PAGE_WIDTH, PAGE_HEIGHT = letter
_TEXT_X = 150
_RIGHT_MARGIN = 36
_MAX_TEXT_WIDTH = PAGE_WIDTH - _RIGHT_MARGIN - _TEXT_X  # ancho disponible a la derecha del logo

# =========================
# Utilidades de dibujo
# =========================
def _cap(s):
    return s[0].upper() + s[1:] if s else s

def _try_logo(c, path, x=40, y=720, w=80, h=80):
    """Dibuja el logo si existe; de lo contrario, muestra un marcador."""
    def _placeholder():
        c.saveState()
        c.setStrokeColor(colors.Color(1, 1, 1, alpha=0.2))
        c.setLineWidth(1)
        c.rect(x, y, w, h)
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + w / 2, y + h / 2 - 4, "LOGO")
        c.restoreState()

    if not path:
        _placeholder()
        return

    try:
        if not os.path.exists(path):
            print(f"[factura] Logo no encontrado: {path}")
            _placeholder()
            return
        img = ImageReader(path)
        c.drawImage(img, x, y, width=w, height=h, mask='auto')
    except Exception as exc:
        print(f"[factura] Error al cargar logo '{path}': {exc}")
        _placeholder()

def _draw_wrapped(c, text, x, y, width, font="Helvetica", size=10, leading=14, color=colors.black, max_lines=None):
    """
    Dibuja 'text' con salto de línea automático dentro de 'width'.
    Devuelve la nueva coordenada y (la siguiente línea base disponible).
    """
    if not text:
        return y
    c.setFont(font, size)
    c.setFillColor(color)
    lines = simpleSplit(text, font, size, width)
    if max_lines:
        lines = lines[:max_lines]
    for i, line in enumerate(lines):
        c.drawString(x, y - i * leading, line)
    return y - leading * len(lines)

def _encabezado(c, theme):
    """
    Dibuja logo, título y contacto según theme con salto de línea para textos largos.
    """
    _try_logo(c, theme.get("logo"))

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(theme["primary"])
    c.drawString(_TEXT_X, 770, theme.get("title", ""))

    # Datos de contacto con wrap
    y = 750
    c.setFillColor(colors.black)

    # Dirección (si es muy larga, baja a 9pt)
    dir_text = f"Dirección: {theme.get('address','')}"
    if c.stringWidth(dir_text, "Helvetica", 10) > _MAX_TEXT_WIDTH:
        y = _draw_wrapped(c, dir_text, _TEXT_X, y, _MAX_TEXT_WIDTH, font="Helvetica", size=9, leading=13)
    else:
        y = _draw_wrapped(c, dir_text, _TEXT_X, y, _MAX_TEXT_WIDTH, font="Helvetica", size=10, leading=14)

    # Teléfono con wrap por consistencia
    tel_text = f"Teléfono: {theme.get('phone','')}"
    y -= 2
    _draw_wrapped(c, tel_text, _TEXT_X, y, _MAX_TEXT_WIDTH, font="Helvetica", size=10, leading=14)

def _datos_factura(c, theme, fecha, cliente, estado):
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(theme["accent"])
    c.drawString(50, 700, f"FECHA: {fecha}")
    c.drawString(50, 685, f"CLIENTE: {cliente}")
    c.drawString(50, 670, f"ESTADO: {estado}")
    c.setFillColor(colors.black)

def _cabecera_tabla(c, y, theme):
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(theme["primary"])
    c.drawString(50, y, "DESCRIPCIÓN")
    c.drawString(250, y, "CANTIDAD")
    c.drawString(350, y, "PRECIO")
    c.drawString(450, y, "TOTAL")
    c.setStrokeColor(theme["primary"])
    c.setLineWidth(1)
    c.line(50, y - 5, 500, y - 5)

def _filas(c, y, theme, productos):
    c.setFont("Helvetica", 10)
    total_factura = 0
    for cantidad, descripcion, precio, total in productos:
        if y < 100:
            c.showPage()
            y = 750
            _cabecera_tabla(c, y, theme)
            y -= 20

        desc_lines = simpleSplit(_cap(descripcion), "Helvetica", 10, 180)
        for idx, line in enumerate(desc_lines):
            c.setFillColor(colors.black)
            c.drawString(50, y, line)
            if idx == 0:
                c.drawRightString(300, y, str(cantidad))
                c.drawRightString(420, y, f"Q {precio:.2f}")
                c.drawRightString(500, y, f"Q {total:.2f}")
            y -= 18

        c.setStrokeColor(theme["line"])
        c.setLineWidth(0.8)
        c.line(50, y + 10, 500, y + 10)
        c.setLineWidth(0.5)
        total_factura += total
    return y, total_factura

def _totales_y_nota(c, y, theme, total_factura):
    if y < 120:
        c.showPage()
        y = 750
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(theme["primary"])
    c.drawString(350, y - 10, "TOTAL:")
    c.drawRightString(500, y - 10, f"Q {total_factura:,.2f}")
    c.line(350, y - 15, 500, y - 15)

    c.setFont("Times-Italic", 11)
    c.setFillColor(theme["note"])
    c.drawString(50, y - 50, "(Factura no contable con fines informativos.)")
    c.drawString(50, y - 65, "¡Gracias por su compra, vuelva pronto!")

# =========================
# Generadores
# =========================
def generar_factura(cliente, estado, fecha, productos, tema="A"):
    """
    Generador genérico. Cambia 'tema' a 'A' o 'B' (o agrega más en THEMES).
    """
    theme = THEMES.get(tema.upper(), THEMES["A"])
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    _encabezado(c, theme)
    _datos_factura(c, theme, fecha, cliente, estado)

    y = 640
    _cabecera_tabla(c, y, theme)
    y -= 20

    y, total_factura = _filas(c, y, theme, productos)
    _totales_y_nota(c, y, theme, total_factura)

    c.save()
    buffer.seek(0)
    return buffer

def generar_factura_A(cliente, estado, fecha, productos):
    return generar_factura(cliente, estado, fecha, productos, tema="A")

def generar_factura_B(cliente, estado, fecha, productos):
    return generar_factura(cliente, estado, fecha, productos, tema="B")

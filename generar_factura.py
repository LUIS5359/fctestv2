# generar_factura.py
import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader, simpleSplit
from PIL import Image, ImageDraw, ImageFont

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
# Escala de la versión PNG respecto a la carta (en puntos)
_PNG_SCALE = 2
_IMAGE_WIDTH = int(PAGE_WIDTH * _PNG_SCALE)
_IMAGE_HEIGHT = int(PAGE_HEIGHT * _PNG_SCALE)

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

def _totales_y_nota(c, y, theme, total_factura, pago_parcial=0.0):
    if y < 120:
        c.showPage()
        y = 750
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(theme["primary"])
    c.drawString(350, y - 10, "TOTAL:")
    c.drawRightString(500, y - 10, f"Q {total_factura:,.2f}")
    c.line(350, y - 15, 500, y - 15)

    if pago_parcial:
        saldo = max(total_factura - pago_parcial, 0)
        c.setFont("Helvetica", 10)
        c.setFillColor(theme["accent"])
        c.drawString(350, y - 30, "Pago parcial:")
        c.drawRightString(500, y - 30, f"Q {pago_parcial:,.2f}")
        c.drawString(350, y - 45, "Saldo pendiente:")
        c.drawRightString(500, y - 45, f"Q {saldo:,.2f}")
        y -= 20

    c.setFont("Times-Italic", 11)
    c.setFillColor(theme["note"])
    c.drawString(50, y - 50, "(Factura no contable con fines informativos.)")
    c.drawString(50, y - 65, "¡Gracias por su compra, vuelva pronto!")


# =========================
# Utilidades para imagen PNG
# =========================
def _color_to_rgb(color, default=(0, 0, 0)):
    if hasattr(color, "red"):
        return (
            int(color.red * 255),
            int(color.green * 255),
            int(color.blue * 255),
        )
    if isinstance(color, str):
        value = color.lstrip("#")
        if len(value) in (3, 6):
            if len(value) == 3:
                value = "".join(ch * 2 for ch in value)
            try:
                r = int(value[0:2], 16)
                g = int(value[2:4], 16)
                b = int(value[4:6], 16)
                return (r, g, b)
            except ValueError:
                pass
    return default


def _load_font(size=24, bold=False):
    base = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    paths = [
        f"/usr/share/fonts/truetype/dejavu/{base}",
        base,
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size=size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _draw_right(draw, text, x, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    draw.text((x - width, y), text, font=font, fill=fill)


def _wrap_for_width(draw, text, font, max_width):
    if not text:
        return []
    words = text.split()
    lines = []
    current = []
    for word in words:
        trial = " ".join(current + [word])
        length = draw.textlength(trial, font=font)
        if length <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines or [text]


def _text_height(font, extra=6):
    """Calcula la altura aproximada de una línea para el font indicado."""
    bbox = font.getbbox("Ag")
    return (bbox[3] - bbox[1]) + extra


def generar_imagen_factura(cliente, estado, fecha, productos, tema="A", pago_parcial=0.0):
    """Genera una imagen con composición similar al PDF para mantener consistencia."""

    theme = THEMES.get(tema.upper(), THEMES["A"])
    img = Image.new("RGB", (_IMAGE_WIDTH, _IMAGE_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    title_font = _load_font(42, bold=True)
    subtitle_font = _load_font(24)
    body_font = _load_font(24)
    bold_font = _load_font(24, bold=True)
    small_font = _load_font(20)

    primary = _color_to_rgb(theme.get("primary"), (15, 76, 129))
    accent = _color_to_rgb(theme.get("accent"), (51, 65, 85))
    note_color = _color_to_rgb(theme.get("note"), (55, 65, 81))

    padding = int(36 * _PNG_SCALE)
    col_desc = int(50 * _PNG_SCALE)
    col_qty = int(300 * _PNG_SCALE)
    col_price = int(420 * _PNG_SCALE)
    col_total = int(500 * _PNG_SCALE)
    table_right = _IMAGE_WIDTH - padding

    # Logo y cabecera
    logo_x = int(40 * _PNG_SCALE)
    logo_y = int(40 * _PNG_SCALE)
    logo_box = int(90 * _PNG_SCALE)
    text_x = logo_x + logo_box + int(32 * _PNG_SCALE)
    y = logo_y

    logo_path = theme.get("logo")
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((logo_box, logo_box), Image.LANCZOS)
            img.paste(logo, (logo_x, logo_y), logo)
        except Exception:
            pass
    else:
        draw.rectangle([logo_x, logo_y, logo_x + logo_box, logo_y + logo_box], outline=(210, 210, 210), width=3)

    draw.text((text_x, y), theme.get("title", ""), fill=primary, font=title_font)
    y += _text_height(title_font)

    info_width = _IMAGE_WIDTH - text_x - padding
    direccion = f"Dirección: {theme.get('address', '')}"
    telefono = f"Teléfono: {theme.get('phone', '')}"
    for line in _wrap_for_width(draw, direccion, subtitle_font, info_width):
        draw.text((text_x, y), line, fill=(55, 65, 81), font=subtitle_font)
        y += _text_height(subtitle_font, extra=4)
    for line in _wrap_for_width(draw, telefono, subtitle_font, info_width):
        draw.text((text_x, y), line, fill=(55, 65, 81), font=subtitle_font)
        y += _text_height(subtitle_font, extra=4)

    y = max(y, logo_y + logo_box) + int(32 * _PNG_SCALE)

    # Datos del cliente
    draw.text((col_desc, y), f"FECHA: {fecha}", font=bold_font, fill=accent)
    y += _text_height(bold_font, extra=6)
    draw.text((col_desc, y), f"CLIENTE: {cliente}", font=bold_font, fill=accent)
    y += _text_height(bold_font, extra=6)
    draw.text((col_desc, y), f"ESTADO: {estado}", font=bold_font, fill=accent)
    y += _text_height(bold_font, extra=12)

    # Cabecera tabla
    draw.line((col_desc, y, table_right, y), fill=primary, width=3)
    y += int(10 * _PNG_SCALE)
    draw.text((col_desc, y), "DESCRIPCIÓN", font=bold_font, fill=primary)
    _draw_right(draw, "CANTIDAD", col_qty + int(20 * _PNG_SCALE), y, bold_font, primary)
    _draw_right(draw, "PRECIO", col_price + int(50 * _PNG_SCALE), y, bold_font, primary)
    _draw_right(draw, "TOTAL", col_total + int(80 * _PNG_SCALE), y, bold_font, primary)
    y += _text_height(bold_font, extra=12)
    draw.line((col_desc, y, table_right, y), fill=primary, width=2)
    y += int(15 * _PNG_SCALE)

    total_factura = 0
    descripcion_ancho = col_qty - col_desc - int(20 * _PNG_SCALE)
    linea_altura = _text_height(body_font, extra=8)

    for cantidad, descripcion, precio, total in productos:
        lineas_desc = _wrap_for_width(draw, _cap(descripcion), body_font, descripcion_ancho)
        for idx, line in enumerate(lineas_desc):
            draw.text((col_desc, y), line, font=body_font, fill=(31, 41, 55))
            if idx == 0:
                _draw_right(draw, str(cantidad), col_qty, y, body_font, (31, 41, 55))
                _draw_right(draw, f"Q {precio:,.2f}", col_price + int(60 * _PNG_SCALE), y, body_font, (31, 41, 55))
                _draw_right(draw, f"Q {total:,.2f}", col_total + int(100 * _PNG_SCALE), y, body_font, (31, 41, 55))
            y += linea_altura
        total_factura += total
        draw.line((col_desc, y - 6, table_right, y - 6), fill=(226, 232, 240), width=2)
        y += int(4 * _PNG_SCALE)
        if y > _IMAGE_HEIGHT - int(200 * _PNG_SCALE):
            break

    # Totales
    y += int(10 * _PNG_SCALE)
    draw.text((col_desc, y), "TOTAL:", font=bold_font, fill=primary)
    _draw_right(draw, f"Q {total_factura:,.2f}", col_total + int(100 * _PNG_SCALE), y, bold_font, primary)
    y += _text_height(bold_font, extra=12)

    if pago_parcial:
        saldo = max(total_factura - pago_parcial, 0)
        draw.text((col_desc, y), "Pago parcial:", font=body_font, fill=accent)
        _draw_right(draw, f"Q {pago_parcial:,.2f}", col_total + int(100 * _PNG_SCALE), y, body_font, accent)
        y += linea_altura
        draw.text((col_desc, y), "Saldo pendiente:", font=body_font, fill=accent)
        _draw_right(draw, f"Q {saldo:,.2f}", col_total + int(100 * _PNG_SCALE), y, body_font, accent)
        y += linea_altura

    draw.text((col_desc, y), "(Factura no contable con fines informativos.)", font=small_font, fill=note_color)
    y += _text_height(small_font, extra=8)
    draw.text((col_desc, y), "¡Gracias por su compra, vuelva pronto!", font=small_font, fill=note_color)
    y += _text_height(small_font, extra=12)

    contenido_util = min(max(int(y + 40), int(520 * _PNG_SCALE)), _IMAGE_HEIGHT)
    if contenido_util < _IMAGE_HEIGHT:
        img = img.crop((0, 0, _IMAGE_WIDTH, contenido_util))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# =========================
# Generadores
# =========================
def generar_factura(cliente, estado, fecha, productos, tema="A", pago_parcial=0.0):
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
    _totales_y_nota(c, y, theme, total_factura, pago_parcial=pago_parcial)

    c.save()
    buffer.seek(0)
    return buffer

def generar_factura_A(cliente, estado, fecha, productos, pago_parcial=0.0):
    return generar_factura(cliente, estado, fecha, productos, tema="A", pago_parcial=pago_parcial)

def generar_factura_B(cliente, estado, fecha, productos, pago_parcial=0.0):
    return generar_factura(cliente, estado, fecha, productos, tema="B", pago_parcial=pago_parcial)

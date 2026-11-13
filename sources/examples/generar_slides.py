#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rellena una plantilla PowerPoint con datos de un Excel usando etiquetas {{...}}.

Uso:
    python generar_slides.py                                   (busca solo el Excel y la plantilla en su carpeta)
    python generar_slides.py datos.xlsx plantilla.pptx salida.pptx

Etiquetas que se pueden escribir en cualquier cuadro de texto de la plantilla:
    {{Hoja!B6}}                       celda completa (cada bloque separado por linea en blanco = un parrafo)
    {{Hoja!B8#3}}                     3er bloque de la celda
    {{Hoja!B7#2.1}}                   1a linea del 2o bloque  (p.ej. la cifra de una key figure)
    {{Hoja!B7#2.2}}                   resto del 2o bloque     (p.ej. el texto bajo la cifra)
    {{TABLA Hoja!D5:F10}}             tabla; la 1a fila del rango es la cabecera
    {{TABLA Hoja!E7:G8 CABECERA E4:G4}}   tabla con cabecera tomada de otra fila
    {{TABLA Hoja!E7:G8 SIN CABECERA}}     tabla sin cabecera
    {{LOGOS Hoja!B10}}                logos: nombres separados por ";" -> ficheros de la carpeta "logos" (p.ej. logos/THALES.png)
Listas: si una celda tiene lineas que empiezan por "- ", cada una sale como vineta "»" y las lineas
**EMPRESA** salen como titulo. El formato de la vineta se toma del parrafo "(formato viñeta)" del cuadro.
En el Excel, el texto entre **dobles asteriscos** sale en negrita.
La tabla ocupa el recuadro (rectangulo con borde) dentro del cual se ha puesto la etiqueta.
El formato (fuente, color, tamano) del texto insertado es el del texto de la etiqueta en la plantilla.

Requisitos (una sola vez):  pip install python-pptx openpyxl
Importante: guarde el Excel desde Excel antes de lanzar el script (las formulas se leen con su ultimo valor guardado).
"""
import copy, math, re, sys
import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter
from pptx import Presentation
from pptx.util import Emu, Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR
from lxml import etree

# ------------------------------------------------------------------ configuracion de estilo
NAVY, DARK = RGBColor(0x06, 0x3C, 0x67), RGBColor(0x00, 0x20, 0x60)
WHITE, TINT, BORDER = RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xEA, 0xF1, 0xFA), "D9E2F3"
TABLE_FONT_SIZES = [8, 7.5, 7]            # tamanos que se prueban en las tablas (de mayor a menor)
# Estilo de los textos de una celda completa (p.ej. la introduccion):
INTRO_STYLE = dict(size=9.5, color=RGBColor(0x00, 0x20, 0x60), bold_color=RGBColor(0x1D, 0x93, 0xC9), justify=True)
# Estilo de los bloques #n (p.ej. Added Value):
BLOCK_STYLE = dict(size=9, justify=False)
SHORT_BLOCK = 120                         # bloques mas cortos que esto se unen al parrafo anterior (p.ej. "**The result**: ...")
TEXT_MIN_SIZE = 8                         # tamano minimo al reducir texto que no cabe
STRIP_NUMBERING = True                    # quita "1.1  " del inicio de las celdas de tabla
CHAR_W = 0.43                             # ancho medio de caracter (en em) para estimar si el texto cabe
LOGO_MAX_H = 0.40                         # altura maxima de los logos (pulgadas)
LOGO_AREA = 0.30                          # superficie visual de cada logo (pulgadas cuadradas): todos se ven del mismo "peso"
BULLET_SAMPLE = "(formato viñeta)"         # texto del parrafo de muestra para las vinetas en la plantilla

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
EMU_IN = 914400
TAG_RE = re.compile(
    r"\{\{\s*(?P<table>TABLA\s+|LOGOS\s+)?(?P<sheet>[^!{}]+?)!(?P<ref>[A-Za-z]+\d+(?::[A-Za-z]+\d+)?)"
    r"(?:#(?P<blk>\d+)(?:\.(?P<part>\d+))?)?"
    r"(?:\s+CABECERA\s+(?P<hdr>[A-Za-z]+\d+:[A-Za-z]+\d+)|(?P<nohdr>\s+SIN\s+CABECERA))?\s*\}\}",
    re.I)
warnings = []
def warn(msg):
    if msg not in warnings: warnings.append(msg)

# ------------------------------------------------------------------ lectura del Excel
class Book:
    def __init__(self, path):
        self.wb = openpyxl.load_workbook(path, data_only=True)
    def sheet(self, name):
        name = name.strip()
        if name not in self.wb.sheetnames:
            raise KeyError(f"La hoja '{name}' no existe en el Excel")
        return self.wb[name]
    def cell(self, sheet, ref):
        v = self.sheet(sheet)[ref.upper()].value
        return "" if v is None else str(v)
    def rng(self, sheet, ref):
        ws = self.sheet(sheet)
        a, b = ref.upper().split(":")
        rows = ws[a:b]
        return [["" if c.value is None else str(c.value) for c in row] for row in rows]

def norm(s):
    s = (s or "").replace("\xa0", " ").replace("\r", "")
    s = re.sub(r"[ \t]+", " ", s)
    return "\n".join(l.strip() for l in s.split("\n")).strip()

def blocks(s):
    return [b for b in (norm(x) for x in re.split(r"\n\s*\n", s or "")) if b]

def merge_blocks(bl):
    """Un bloque todo en negrita se une al siguiente (titulo en linea); un bloque corto se une al anterior."""
    out, pending = [], ""
    for b in bl:
        plain = b.replace("**", "")
        if b.startswith("**") and b.endswith("**") and b.count("**") == 2:
            pending = (pending + " " + b).strip(); continue
        if pending:
            b = pending + " " + b; pending = ""
        elif out and len(plain) < SHORT_BLOCK:
            out[-1] = out[-1] + " " + b; continue
        out.append(b)
    if pending: out.append(pending)
    return out

def resolve(book, m, where):
    """Devuelve el texto que sustituye a una etiqueta de texto."""
    raw = book.cell(m["sheet"], m["ref"])
    if not raw.strip():
        warn(f"{where}: la celda {m['sheet'].strip()}!{m['ref']} esta vacia")
        return ""
    if not m["blk"]:
        return norm(raw)
    bl = blocks(raw); i = int(m["blk"])
    if i > len(bl):
        warn(f"{where}: {m['sheet'].strip()}!{m['ref']} no tiene bloque #{i} (solo {len(bl)})")
        return ""
    b = bl[i - 1]
    if not m["part"]:
        return b
    first, _, rest = b.partition("\n")
    return first if m["part"] == "1" else rest.replace("\n", " ")

# ------------------------------------------------------------------ utilidades de forma / texto
def iter_shapes(shapes, in_group=False):
    for sh in shapes:
        if sh.shape_type == 6:
            yield from iter_shapes(sh.shapes, True)
        else:
            yield sh, in_group

def geometry(slide):
    """Posicion real en la slide (pulgadas) de cada forma, aunque este dentro de grupos.
    Devuelve {id(elemento): (x0, y0, x1, y1, escala_x, escala_y, forma)}."""
    geo = {}
    def walk(shapes, T):
        for sh in shapes:
            x, y, w, h = sh.left or 0, sh.top or 0, sh.width or 0, sh.height or 0
            ax, ay = T(x, y); bx, by = T(x + w, y + h)
            geo[id(sh._element)] = (ax / EMU_IN, ay / EMU_IN, bx / EMU_IN, by / EMU_IN,
                                    (bx - ax) / w if w else 1, (by - ay) / h if h else 1, sh)
            if sh.shape_type == 6:
                xf = sh._element.grpSpPr.find(A + "xfrm")
                off, ext = xf.find(A + "off"), xf.find(A + "ext")
                cho, che = xf.find(A + "chOff"), xf.find(A + "chExt")
                ox, oy, ex, ey = int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))
                cx, cy = int(cho.get("x")), int(cho.get("y"))
                ccx, ccy = int(che.get("cx")) or 1, int(che.get("cy")) or 1
                def T2(px, py, T=T, ox=ox, oy=oy, ex=ex, ey=ey, cx=cx, cy=cy, ccx=ccx, ccy=ccy):
                    return T(ox + (px - cx) * ex / ccx, oy + (py - cy) * ey / ccy)
                walk(sh.shapes, T2)
    walk(slide.shapes, lambda x, y: (x, y))
    return geo

def abs_box(geo, sh):
    return geo[id(sh._element)][:4]

def container_of(geo, target):
    """Recuadro (rectangulo) mas pequeno que contiene el centro de target. Devuelve (x0,y0,x1,y1) en pulgadas."""
    a0, b0, a1, b1 = abs_box(geo, target); tx, ty = (a0 + a1) / 2, (b0 + b1) / 2; best = None
    parent = target._element.getparent()
    in_group = not parent.tag.endswith("}spTree")
    for x0, y0, x1, y1, _, _, sh in geo.values():
        if sh.shape_type != 1 or sh._element is target._element:
            continue
        if in_group and sh._element.getparent() is not parent:   # dentro de un grupo: solo su propio recuadro
            continue
        if x0 <= tx <= x1 and y0 <= ty <= y1 and (x1 - x0) > 1.5 and (y1 - y0) > 0.8:
            if best is None or (x1 - x0) * (y1 - y0) < (best[2] - best[0]) * (best[3] - best[1]):
                best = (x0, y0, x1, y1)
    return best

def md_runs(text):
    """'a **b** c' -> [('a ',False),('b',True),(' c',False)]"""
    parts, bold = [], False
    for i, chunk in enumerate(text.split("**")):
        if chunk: parts.append((chunk, bold))
        bold = not bold
    return parts

def est_lines(text, width_in, size_pt):
    cpl = max(1, int(width_in * 72 / (size_pt * CHAR_W)))
    return sum(max(1, math.ceil(len(line) / cpl)) for line in text.split("\n"))

def est_height(paras, width_in, size_pt, gap_pt=3):
    lines = sum(est_lines(p.replace("**", ""), width_in, size_pt) for p in paras)
    return lines * size_pt * 1.2 / 72 + max(0, len(paras) - 1) * gap_pt / 72

def run_size(r, default=10.0):
    return r.font.size.pt if r.font.size else default

# ------------------------------------------------------------------ texto
def fill_paragraph(p, book, where, is_textbox=True):
    runs = list(p.runs)
    full = "".join(r.text for r in runs)
    tags = list(TAG_RE.finditer(full))
    tags = [t for t in tags if not t["table"]]
    if not tags:
        return []
    # Caso 1: la etiqueta es todo el parrafo -> admite varios parrafos y **negrita**
    if len(tags) == 1 and full.strip() == tags[0].group(0):
        value = resolve(book, tags[0], where)
        tmpl_rpr = runs[0]._r.find(A + "rPr")
        whole = not tags[0]["blk"]
        part = bool(tags[0]["part"])
        if whole and re.search(r"^\s*[-•»]\s", value, re.M):
            return fill_list(p, value, tmpl_rpr)
        paras = merge_blocks(blocks(value)) if whole else [value]
        paras = paras or [""]
        is_intro = whole and len(value.replace("**", "")) > 100
        style = (INTRO_STYLE if is_intro else (None if (part or whole) else BLOCK_STYLE)) if is_textbox else None
        new_ps = [p]
        for _ in paras[1:]:
            np_ = copy.deepcopy(p._p); new_ps[-1]._p.addnext(np_)
            new_ps.append(type(p)(np_, p._parent))
        for para, text in zip(new_ps, paras):
            for r in list(para.runs): r._r.getparent().remove(r._r)
            has_md = "**" in text
            for chunk, b in md_runs(text.replace("\n", " ")):
                r = para.add_run()
                if tmpl_rpr is not None:
                    old = r._r.find(A + "rPr")
                    if old is not None: r._r.remove(old)
                    r._r.insert(0, copy.deepcopy(tmpl_rpr))
                r.text = chunk
                if has_md or (style and not part): r.font.bold = b
                rpr = r._r.find(A + "rPr")
                if rpr is not None:
                    rpr.attrib.pop("err", None)
                if part and rpr is not None:
                    rpr.attrib.pop("cap", None)               # key figures: se respeta mayusc./minusc. del Excel
                if style:
                    r.font.size = Pt(style["size"])
                    if style is INTRO_STYLE:
                        r.font.color.rgb = style["bold_color"] if b else style["color"]
                        for tag in ("latin", "ea", "cs"):          # usa la fuente del cuadro (como el resto del deck)
                            el = rpr.find(A + tag)
                            if el is not None: rpr.remove(el)
            if style:
                from pptx.enum.text import PP_ALIGN
                para.alignment = PP_ALIGN.JUSTIFY if style["justify"] else PP_ALIGN.LEFT
                if style is INTRO_STYLE: para.space_after = Pt(3)
        return new_ps
    # Caso 2: etiqueta dentro de un texto (p.ej. "OUR EXPERTISE IN {{...}}") -> sustitucion simple
    spans, pos = [], 0
    for r in runs:
        spans.append((pos, pos + len(r.text))); pos += len(r.text)
    for t in reversed(tags):
        value = resolve(book, t, where).replace("**", "").replace("\n", " ")
        literal = TAG_RE.sub("", full)
        if re.search("[A-Za-z]", literal) and literal == literal.upper():
            value = value.upper()
        s, e = t.span(); first = True
        for r, (a, b) in zip(runs, spans):
            if b <= s or a >= e: continue
            txt = r.text; ls, le = max(s, a) - a, min(e, b) - a
            r.text = txt[:ls] + (value if first else "") + txt[le:]
            first = False
        spans, pos = [], 0
        for r in runs:
            spans.append((pos, pos + len(r.text))); pos += len(r.text)
    return [p]

def fill_list(p, value, tmpl_rpr):
    """Celda con lineas '- ...' -> titulos (lineas sin guion) y vinetas (lineas con guion)."""
    # parrafo de muestra para las vinetas (se elimina)
    bullet_ppr = bullet_rpr = None
    sib = p._p.getnext()
    if sib is not None and "".join(t.text or "" for t in sib.iter(A + "t")).strip() == BULLET_SAMPLE:
        bullet_ppr = sib.find(A + "pPr"); r0 = sib.find(A + "r")
        bullet_rpr = r0.find(A + "rPr") if r0 is not None else None
        sib.getparent().remove(sib)
    head_ppr = p._p.find(A + "pPr")
    if bullet_ppr is None:                       # sin muestra: vineta derivada del titulo
        bullet_ppr = copy.deepcopy(head_ppr) if head_ppr is not None else etree.Element(A + "pPr")
        bullet_ppr.set("marL", "171450"); bullet_ppr.set("indent", "-171450")
        for t in ("buClr", "buClrTx", "buFont", "buFontTx", "buNone", "buChar", "buAutoNum"):
            for el in bullet_ppr.findall(A + t): bullet_ppr.remove(el)
        bu = [etree.Element(A + "buClr"), etree.Element(A + "buFont", typeface="Calibri"), etree.Element(A + "buChar", char="»")]
        etree.SubElement(bu[0], A + "schemeClr", val="accent4")
        nxt = None                               # los elementos de vineta van antes de tabLst/defRPr/extLst
        for t in ("tabLst", "defRPr", "extLst"):
            nxt = bullet_ppr.find(A + t)
            if nxt is not None: break
        for el in bu:
            if nxt is not None: nxt.addprevious(el)
            else: bullet_ppr.append(el)
    if bullet_rpr is None:
        bullet_rpr = copy.deepcopy(tmpl_rpr) if tmpl_rpr is not None else None
        if bullet_rpr is not None:
            bullet_rpr.set("b", "0")
            fill = bullet_rpr.find(A + "solidFill")
            if fill is not None:
                for ch in list(fill): fill.remove(ch)
                etree.SubElement(fill, A + "schemeClr", val="accent3")
    lines = [l.rstrip() for l in value.split("\n")]
    while lines and not lines[-1].strip(): lines.pop()
    parent, anchor = p._p.getparent(), p._p
    first = True
    for line in lines:
        m = re.match(r"^\s*[-•»]\s+(.*)$", line)
        is_bullet = bool(m); text = m.group(1) if m else line.strip()
        np_ = etree.Element(A + "p")
        ppr = bullet_ppr if is_bullet else head_ppr
        if ppr is not None: np_.append(copy.deepcopy(ppr))
        rpr_t = bullet_rpr if is_bullet else tmpl_rpr
        if text:
            md = "**" in text
            for chunk, b in md_runs(text) or [(text, False)]:
                r = etree.SubElement(np_, A + "r")
                if rpr_t is not None:
                    rp = copy.deepcopy(rpr_t); rp.attrib.pop("err", None)
                    if md or not is_bullet: rp.set("b", "1" if (b or not is_bullet) else "0")
                    r.append(rp)
                etree.SubElement(r, A + "t").text = chunk
        elif rpr_t is not None:
            end = copy.deepcopy(rpr_t); end.tag = A + "endParaRPr"; np_.append(end)
        if first:
            parent.replace(anchor, np_); anchor = np_; first = False
        else:
            anchor.addnext(np_); anchor = np_
    if first:                                   # celda vacia
        for r in list(p.runs): r._r.getparent().remove(r._r)
    return []

def needed_size(sh, geo):
    """Tamano de letra necesario para que el texto quepa. Devuelve ((tamano, original, cabe), recuadro)."""
    tf = sh.text_frame
    x0, y0, x1, y1 = abs_box(geo, sh)
    body = tf._txBody.find(A + "bodyPr")
    cont = None
    if body is not None and body.find(A + "spAutoFit") is not None:
        cont = container_of(geo, sh)
        if not cont: return None, None
        avail = cont[3] - y0 - 0.1
    else:
        avail = (y1 - y0) + 0.12
    paras = [p for p in tf.paragraphs if p.text.strip()]
    runs = [r for p in paras for r in p.runs]
    if not runs: return None, None
    size = max(run_size(r) for r in runs)
    width = (x1 - x0) - 0.2 - (0.19 if tf._txBody.find(".//" + A + "buChar") is not None else 0)
    texts = [p.text for p in paras]
    gaps = len(tf.paragraphs) - len(paras)
    def h(sz): return est_height(texts, width, sz, 0) + gaps * sz * 1.2 / 72
    sz = size
    while sz > TEXT_MIN_SIZE and h(sz) > avail: sz -= 0.5
    return (sz, size, h(sz) <= avail), cont

def apply_sizes(items, n):
    """items: [(shape, where, (sz, orig, ok), container)] -> los cuadros del mismo recuadro usan el mismo tamano."""
    groups = {}
    for sh, where, res, cont in items:
        groups.setdefault((cont or id(sh), res[1]), []).append((sh, where, res))
    for members in groups.values():
        sz = min(res[0] for _, _, res in members)
        orig = max(res[1] for _, _, res in members)
        if sz >= orig: continue
        for sh, where, res in members:
            for p in sh.text_frame.paragraphs:
                for r in p.runs: r.font.size = Pt(sz)
            if not res[2]:
                warn(f"{where}: el texto no cabe ni a {sz} pt - acorte el texto en el Excel")
        print(f"   · Slide {n}: texto de {', '.join(repr(m[0].name) for m in members)} reducido a {sz} pt para que quepa")

# ------------------------------------------------------------------ tablas
def set_cell(cell, text, size, color, bold, fill):
    cell.fill.solid(); cell.fill.fore_color.rgb = fill
    cell.margin_left = cell.margin_right = Inches(0.05)
    cell.margin_top = cell.margin_bottom = Inches(0.025)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf = cell.text_frame; tf.word_wrap = True
    lines = text.split("\n") or [""]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        for chunk, b in md_runs(line) or [("", False)]:
            r = p.add_run(); r.text = chunk
            r.font.size = Pt(size); r.font.bold = bold or b; r.font.color.rgb = color
    tcPr = cell._tc.get_or_add_tcPr()
    fill_el = tcPr.find(A + "solidFill")
    for tag in ("lnL", "lnR", "lnT", "lnB"):
        ln = etree.Element(A + tag, w="6350")
        sf = etree.SubElement(ln, A + "solidFill"); etree.SubElement(sf, A + "srgbClr", val=BORDER)
        fill_el.addprevious(ln)

def clean_cell(v):
    v = norm(v)
    if STRIP_NUMBERING: v = re.sub(r"^\d+(\.\d+)+\s+", "", v)
    return v

def inline(v):
    return "; ".join(l.lstrip("•-–· ").strip() for l in v.split("\n") if l.strip())

def build_table(slide, sh, m, book, where, geo):
    sheet = m["sheet"].strip()
    data = book.rng(sheet, m["ref"])
    if m["hdr"]:
        header = book.rng(sheet, m["hdr"])[0]
    elif m["nohdr"]:
        header = None
    else:
        header, data = data[0], data[1:]
    data = [r for r in data if any(str(c).strip() for c in r)]
    if header is not None and len(header) != len(data[0] if data else header):
        warn(f"{where}: la cabecera tiene {len(header)} columnas y los datos {len(data[0])}")
        return
    if not data:
        warn(f"{where}: el rango {sheet}!{m['ref']} esta vacio"); return
    header = [norm(h) for h in header] if header else None
    data = [[clean_cell(c) for c in r] for r in data]
    ncol = len(data[0])
    # posicion y tamano: el recuadro que contiene la etiqueta
    cont = container_of(geo, sh)
    x = sh.left + Inches(0.1)
    y = sh.top + Inches(0.08)
    if cont:
        w = Inches(cont[2]) - x - Inches(0.15); hmax = Inches(cont[3]) - y - Inches(0.1)
    else:
        w = sh.width - Inches(0.2); hmax = sh.height
    w_in, h_in = w / EMU_IN, hmax / EMU_IN
    # anchos de columna proporcionales al contenido
    weights = []
    for c in range(ncol):
        col = [r[c] for r in data] + ([header[c]] if header else [])
        weights.append(max(1.0, math.sqrt(sum(len(v) for v in col))))
    tot = sum(weights); widths = [max(0.12, wt / tot) * w_in for wt in weights]
    k = w_in / sum(widths); widths = [v * k for v in widths]

    def height(rows, size):
        hh = 0
        for r in ([header] if header else []) + rows:
            hh += max(est_height([v or " "], cw - 0.1, size, 0) for v, cw in zip(r, widths)) + 0.05
        return hh
    chosen = None
    for rows, mode in ((data, "lineas"), ([[inline(v) if "\n" in v else v for v in r] for r in data], "en linea")):
        for size in TABLE_FONT_SIZES:
            if height(rows, size) <= h_in:
                chosen = (rows, size, mode); break
        if chosen: break
    if not chosen:
        rows = [[inline(v) if "\n" in v else v for v in r] for r in data]
        chosen = (rows, TABLE_FONT_SIZES[-1], "en linea")
        warn(f"{where}: la tabla {sheet}!{m['ref']} puede no caber en su recuadro - reduzca filas o texto")
    rows, size, mode = chosen
    if mode == "en linea":
        print(f"   · {where}: viñetas de la tabla puestas en linea ('; ') para que quepa")

    nrows = len(rows) + (1 if header else 0)
    gf = slide.shapes.add_table(nrows, ncol, x, y, w, Inches(0.2 * nrows))
    gf.name = f"Tabla {sheet}!{m['ref']}"
    tbl = gf.table; tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "0"); tblPr.set("bandRow", "0")
    sid = tblPr.find(A + "tableStyleId")
    if sid is not None: sid.text = "{5940675A-B579-460E-94D1-54222C63F5DA}"
    for i, cw in enumerate(widths): tbl.columns[i].width = Inches(cw)
    ri = 0
    if header:
        tbl.rows[0].height = Inches(0.2)
        for c, v in enumerate(header): set_cell(tbl.cell(0, c), v, size, WHITE, True, NAVY)
        ri = 1
    for r in rows:
        tbl.rows[ri].height = Inches(0.18)
        for c, v in enumerate(r):
            set_cell(tbl.cell(ri, c), v, size, NAVY if c == 0 else DARK, c == 0, TINT if c == 0 else WHITE)
        ri += 1
    # el cuadro con la etiqueta se elimina
    sh._element.getparent().remove(sh._element)

# ------------------------------------------------------------------ logos
LOGO_DIRS = []

def find_logo(name):
    import os
    base = re.sub(r"[\\/:*?\"<>|]", "", name).strip()
    for d in LOGO_DIRS:
        if not os.path.isdir(d): continue
        for f in os.listdir(d):
            stem, ext = os.path.splitext(f)
            if stem.strip().lower() == base.lower() and ext.lower() in (".png", ".jpg", ".jpeg"):
                return os.path.join(d, f)
    return None

def build_logos(slide, sh, m, book, where, geo):
    from PIL import Image
    raw = book.cell(m["sheet"], m["ref"])
    names = [n.strip() for n in re.split(r"[;,\n]+", raw) if n.strip()]
    sh.text_frame.text = ""
    if not names:
        warn(f"{where}: {m['sheet'].strip()}!{m['ref']} sin logos -> se mantienen los de la plantilla")
        return
    bx0, by0, bx1, by1 = abs_box(geo, sh)
    start = bx0
    for x0, y0, x1, y1, _, _, o in list(geo.values()):
        if o._element is sh._element: continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        inside = bx0 - 0.2 <= cx <= bx1 and by0 - 0.1 <= cy <= by1 + 0.1
        if inside and o.shape_type == 13 and o._element.getparent() is slide.shapes._spTree:
            o._element.getparent().remove(o._element)            # logos antiguos
        elif inside and o.has_text_frame and o.text_frame.text.strip() and x0 <= bx0 + 1:
            start = max(start, x1)                               # etiqueta "TOP CUSTOMERS"
    ax0, ax1 = start + 0.15, bx1 - 0.15
    slot = (ax1 - ax0) / len(names)
    maxh = min(LOGO_MAX_H, (by1 - by0) - 0.15)
    for i, name in enumerate(names):
        f = find_logo(name)
        if not f:
            warn(f"{where}: no encuentro el logo '{name}' (ponga logos/{name}.png)"); continue
        data, w, h = trimmed_logo(f)
        r = w / h
        hh = math.sqrt(LOGO_AREA / r); ww = hh * r          # mismo peso visual para logos anchos y altos
        if hh > maxh: hh = maxh; ww = hh * r
        if ww > slot - 0.2: ww = slot - 0.2; hh = ww / r
        x = ax0 + i * slot + (slot - ww) / 2; y = by0 + (by1 - by0 - hh) / 2
        pic = slide.shapes.add_picture(data, Inches(x), Inches(y), Inches(ww), Inches(hh))
        pic.name = f"Logo {name}"

def trimmed_logo(path):
    """Quita los margenes vacios (transparentes o blancos) del logo. Devuelve (png_en_memoria, ancho, alto)."""
    import io
    from PIL import Image, ImageChops
    im = Image.open(path).convert("RGBA")
    alpha = im.split()[-1]
    box = alpha.point(lambda v: 255 if v > 10 else 0).getbbox()
    if box == (0, 0) + im.size or box is None:
        bg = Image.new("RGB", im.size, (255, 255, 255))
        diff = ImageChops.difference(im.convert("RGB"), bg).convert("L").point(lambda v: 255 if v > 25 else 0)
        box = diff.getbbox() or (0, 0) + im.size
    im = im.crop(box)
    buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
    return buf, im.size[0], im.size[1]

def fit_title_bars(slide, geo, filled):
    """Ajusta el ancho de las barras de resaltado bajo los titulos rellenados (centradas)."""
    for x0, y0, x1, y1, sx, sy, bar in list(geo.values()):
        is_line = bar.shape_type == 9 and (y1 - y0) < 0.05
        if not is_line and (bar.shape_type != 1 or (y1 - y0) > 0.16 or (x1 - x0) < 0.3): continue
        if bar.has_text_frame and bar.text_frame.text.strip(): continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for t in filled:
            tx0, ty0, tx1, ty1 = abs_box(geo, t)
            if not (tx0 <= cx <= tx1 and ty0 - 0.05 <= cy <= ty1 + 0.05): continue
            if t._element.getparent() is not bar._element.getparent() and bar._element.getparent().tag.endswith("}grpSp"): continue
            text = t.text_frame.text.strip()
            runs = [r for p in t.text_frame.paragraphs for r in p.runs if r.text.strip()]
            if not text or not runs: continue
            size = run_size(runs[0], 12)
            wn = max(0.6, len(text) * size * (0.6 if text.isupper() else 0.45) / 72 + 0.15)
            wn = min(wn, tx1 - tx0) * (0.94 if is_line else 1)
            new_w = int(wn / sx * EMU_IN)
            bar.left = int(bar.left + (bar.width - new_w) / 2); bar.width = new_w
            break

# ------------------------------------------------------------------ principal
def main(xlsx, tpl, out):
    import os
    book = Book(xlsx)
    for d in (os.path.dirname(os.path.abspath(xlsx)), os.path.dirname(os.path.abspath(__file__))):
        LOGO_DIRS.append(os.path.join(d, "logos"))
    prs = Presentation(tpl)
    for n, slide in enumerate(prs.slides, 1):
        print(f"Slide {n}")
        geo = geometry(slide)
        tables, fits, filled = [], [], []
        for sh, in_group in list(iter_shapes(slide.shapes)):
            if not sh.has_text_frame: continue
            where = f"Slide {n} / '{sh.name}'"
            m = TAG_RE.search(sh.text_frame.text)
            if m and m["table"]:
                tables.append((sh, m, where)); continue
            touched = False
            for p in list(sh.text_frame.paragraphs):
                if TAG_RE.search("".join(r.text for r in p.runs)):
                    try:
                        fill_paragraph(p, book, where, sh.shape_type == 17); touched = True
                    except KeyError as e:
                        warn(f"{where}: {e}")
            for p in list(sh.text_frame.paragraphs):          # muestra de vineta no usada
                if p.text.strip() == BULLET_SAMPLE and len(sh.text_frame.paragraphs) > 1:
                    p._p.getparent().remove(p._p)
            if touched:
                filled.append(sh)
                res, cont = needed_size(sh, geo)
                if res: fits.append((sh, where, res, cont))
        apply_sizes(fits, n)
        fit_title_bars(slide, geo, filled)
        for sh, m, where in tables:
            try:
                if m["table"].strip().upper() == "LOGOS":
                    build_logos(slide, sh, m, book, where, geo)
                else:
                    build_table(slide, sh, m, book, where, geo)
            except KeyError as e:
                warn(f"{where}: {e}")
    prs.save(out)
    print(f"\nGenerado: {out}")
    if warnings:
        print("\nAVISOS:")
        for w_ in warnings: print("  -", w_)
    else:
        print("Sin avisos.")

DEFAULT_OUT = "Blocks_generado.pptx"

def autodetect(folder):
    """Busca en la carpeta del script el Excel y la plantilla (si hay uno de cada)."""
    import glob, os
    def pick(pattern, exclude=()):
        files = [f for f in glob.glob(os.path.join(folder, pattern))
                 if not os.path.basename(f).startswith("~$") and os.path.basename(f) not in exclude]
        return files
    xl = pick("*.xlsx") + pick("*.xlsm")
    pp = pick("*.pptx", exclude=(DEFAULT_OUT,))
    def one(lst, kind):
        if len(lst) == 1: return lst[0]
        if not lst:
            sys.exit(f"ERROR: no hay ningun fichero {kind} en la carpeta {folder}")
        names = "\n   ".join(os.path.basename(f) for f in lst)
        sys.exit(f"ERROR: hay varios ficheros {kind} en la carpeta; deje solo uno o indique el nombre:\n   {names}")
    return one(xl, "Excel (.xlsx)"), one(pp, "PowerPoint (.pptx) de plantilla"), os.path.join(folder, DEFAULT_OUT)

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) == 4:
        args = sys.argv[1:4]
    elif len(sys.argv) == 1:
        args = autodetect(here)
    else:
        print(__doc__); sys.exit(1)
    for f, kind in ((args[0], "Excel"), (args[1], "plantilla")):
        if not os.path.isfile(f):
            sys.exit(f"ERROR: no encuentro el fichero {kind}: {f}\n"
                     f"Compruebe el nombre (incluidos espacios y guiones) o lance el script sin argumentos para que lo busque solo.")
    print(f"Excel:     {os.path.basename(args[0])}\nPlantilla: {os.path.basename(args[1])}\nSalida:    {os.path.basename(args[2])}\n")
    try:
        main(*args)
    except PermissionError:
        sys.exit(f"ERROR: no puedo escribir {args[2]}. Cierrelo en PowerPoint y vuelva a lanzar el script.")

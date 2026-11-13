#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera el informe HTML de ATEXIS Customer Services a partir del Excel.

Uso:
    python generar_informe.py                       (busca el Excel en su carpeta)
    python generar_informe.py datos.xlsx            (Excel indicado)
Resultado: ATEXIS_Customer_Services.html (un solo fichero, con imagenes incluidas, listo para enviar).

Carpeta esperada:
    generar_informe.py
    plantilla_informe.html   -> diseno de la pagina; las etiquetas {{...}} se rellenan con el Excel
    procesos.html            -> diagramas de procesos (HTML editable)
    img/hero.jpg, img/logo.png, img/frame.png
    logos/NOMBRE.png         -> logos de clientes (mismo nombre que en el Excel, fila 10 de 1_Customer_Map)
    un Excel (.xlsx)

Que lee del Excel (mismas celdas que la plantilla PowerPoint):
    1_Offer_Map_v0.1     fila 5 nombre del bloque, 6 introduccion, 7 key figures, 8 added value, 9+ familias
    1_Customer_Map_v0.1  filas 6-9 titulos y proyectos, fila 10 logos
    2_Commercial_Catalogue  familias, propuesta de valor y servicios (columnas A, D, E, F)
    B6_Detail_v0.1       soluciones Digital & AI por bloque (columna C = B1, B2...)
Un bloque sale con su seccion detallada en cuanto tiene introduccion y key figures en el Excel;
si no, solo aparece en el mapa de la oferta.

Requisitos (una sola vez):  pip install openpyxl
Guarde el Excel desde Excel antes de lanzar el script.
"""
import base64, glob, html, os, re, sys
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_NAME = "ATEXIS_Customer_Services.html"
# Facturacion del Grupo ALTEN (B EUR) para el grafico de "ATEXIS at a glance"
TURNOVER = [(2017, 1.98), (2018, 2.26), (2019, 2.62), (2020, 2.33), (2021, 2.93), (2022, 3.78), (2023, 4.07), (2024, 4.14)]
COLS = "BCDEFG"
warnings = []
esc = lambda s: html.escape(str(s or ""), quote=False)

# ------------------------------------------------------------------ utilidades
def md(s):
    s = esc(s).replace("\xa0", " ")
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
def paras(s):
    return [b.strip() for b in re.split(r"\n\s*\n", str(s or "")) if b.strip()]
def strip_num(s):
    return re.sub(r"^\d+\.\d+\s+", "", str(s or "").strip())
def num(s):
    m = re.match(r"^(\d+\.\d+)", str(s or "").strip()); return m.group(1) if m else ""
def data_uri(path):
    ext = os.path.splitext(path)[1].lower().strip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "svg": "svg+xml"}.get(ext, "png")
    with open(path, "rb") as f:
        return f"data:image/{mime};base64," + base64.b64encode(f.read()).decode()
def find_logo(name):
    d = os.path.join(HERE, "logos")
    if not os.path.isdir(d): return None
    for f in os.listdir(d):
        stem, ext = os.path.splitext(f)
        if stem.strip().lower() == name.strip().lower() and ext.lower() in (".png", ".jpg", ".jpeg", ".svg"):
            return os.path.join(d, f)
    return None

# ------------------------------------------------------------------ lectura del Excel
def read_excel(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    def sheet(n):
        if n not in wb.sheetnames: sys.exit(f"ERROR: falta la hoja '{n}' en el Excel")
        return wb[n]
    om, cm = sheet("1_Offer_Map_v0.1"), sheet("1_Customer_Map_v0.1")
    cat, b6 = sheet("2_Commercial_Catalogue"), sheet("B6_Detail_v0.1")
    v = lambda ws, ref: ws[ref].value
    blocks = []
    for i, c in enumerate(COLS):
        fams = [v(om, f"{c}{r}") for r in range(9, 20) if v(om, f"{c}{r}")]
        blocks.append(dict(n=i + 1, code=f"B{i+1}", name=v(om, f"{c}5") or f"Block {i+1}", intro=v(om, f"{c}6"),
                           kf=v(om, f"{c}7"), av=v(om, f"{c}8"), families=fams,
                           t1=v(cm, f"{c}6"), p1=v(cm, f"{c}7"), t2=v(cm, f"{c}8"), p2=v(cm, f"{c}9"), logos=v(cm, f"{c}10")))
    catalogue = []
    for r in range(5, cat.max_row + 1):
        row = [cat.cell(r, k).value for k in range(1, 8)]
        if row[0] and row[3]:
            catalogue.append(dict(block=row[0], id=num(row[3]) or row[2], name=strip_num(row[3]), vp=row[4] or "",
                                  services=[x.strip("•- ").strip() for x in str(row[5] or "").split("\n") if x.strip()]))
    digital = []
    for r in range(5, b6.max_row + 1):
        row = [b6.cell(r, k).value for k in range(1, 9)]
        if row[2] and row[4]:
            digital.append(dict(block=row[2], name=row[4], desc=row[5] or "", std=row[7] or "",
                                acts=[x.strip("•- ").strip() for x in str(row[6] or "").split("\n") if x.strip()]))
    return blocks, catalogue, digital

# ------------------------------------------------------------------ piezas HTML
def projects(text):
    out, cur = [], None
    for line in str(text or "").split("\n"):
        l = line.strip()
        if not l: continue
        m = re.match(r"^\*\*(.+)\*\*$", l)
        if m: cur = dict(client=m.group(1), items=[]); out.append(cur)
        elif cur is not None: cur["items"].append(l.lstrip("-•» ").strip())
    return out
def kfigs(s):
    out = []
    for b in paras(s):
        first, _, rest = b.partition("\n")
        out.append((first.replace("**", "").strip(), rest.strip()))
    return out
def logos_for(s, where):
    out = []
    for n in [x.strip() for x in re.split(r"[;,\n]", str(s or "")) if x.strip()]:
        f = find_logo(n)
        if f: out.append((n, data_uri(f)))
        else: warnings.append(f"{where}: no encuentro el logo '{n}' (ponga logos/{n}.png)")
    return out
def logo_strip(items):
    if not items: return ""
    li = "".join(f'<li><img src="{src}" alt="{esc(n)}"></li>' for n, src in items)
    return f'<div class="logos"><span class="logos-label">Top customers</span><ul>{li}</ul></div>'

def is_detailed(b):
    return bool(b["intro"] and len(str(b["intro"])) > 150 and b["kf"])

def block_section(b, fams, digi):
    anchor = f"block-{b['n']}"
    intro = paras(b["intro"])
    lead = intro[0] if intro and intro[0].startswith("**") and intro[0].endswith("**") else None
    body = intro[1:] if lead else intro
    h = [f'<div class="wrap"><section class="block" id="{anchor}" aria-labelledby="{anchor}-t">',
         f'<div class="block-head"><p class="eyebrow">Block {b["n"]}</p><h2 id="{anchor}-t">{esc(b["name"])}</h2>']
    if lead: h.append(f'<p class="tagline">{esc(lead.replace("**", ""))}</p>')
    h.append('</div><div class="block-intro"><div class="prose">' + "".join(f"<p>{md(p)}</p>" for p in body) + '</div>')
    h.append('<dl class="kf">' + "".join(f'<div><dt>{esc(a)}</dt><dd>{esc(c)}</dd></div>' for a, c in kfigs(b["kf"])) + '</dl></div>')
    if fams:
        h.append('<h3 class="sub">Service families</h3><div class="fam-grid">')
        for f in fams:
            chips = "".join(f"<li>{esc(s)}</li>" for s in f["services"])
            h.append(f'<article class="fam"><header><span class="fam-id">{esc(f["id"])}</span><h4>{esc(f["name"])}</h4></header>'
                     f'<p>{esc(f["vp"])}</p><ul class="chips">{chips}</ul></article>')
        h.append('</div>')
    av = paras(b["av"])
    if av or digi:
        h.append('<div class="two">')
        h.append('<div><h3 class="sub">Our added value</h3><ul class="value">' + "".join(f"<li>{md(a)}</li>" for a in av) + '</ul></div>' if av else '<div></div>')
        if digi:
            h.append('<div><h3 class="sub">Digital &amp; AI support solutions</h3><div class="digital">')
            for d in digi:
                acts = "".join(f"<li>{esc(a)}</li>" for a in d["acts"])
                std = f'<p class="std"><span>Standards</span> {esc(d["std"])}</p>' if d["std"] else ""
                h.append(f'<article class="dig"><h4>{esc(d["name"])}</h4><p>{esc(d["desc"])}</p><ul>{acts}</ul>{std}</article>')
            h.append('</div></div>')
        h.append('</div>')
    cols = [(str(t or "").replace("**", ""), projects(p)) for t, p in ((b["t1"], b["p1"]), (b["t2"], b["p2"])) if p]
    if cols:
        h.append(f'<h3 class="sub">Our projects in {esc(b["name"])}</h3><div class="proj">')
        for title, pr in cols:
            h.append(f'<div class="proj-col"><h4>{esc(title)}</h4>')
            for c in pr:
                h.append(f'<div class="client"><p class="client-name">{esc(c["client"])}</p><ul>' + "".join(f"<li>{esc(i)}</li>" for i in c["items"]) + '</ul></div>')
            h.append('</div>')
        h.append('</div>')
    h.append(logo_strip(logos_for(b["logos"], f"Bloque {b['n']}")))
    h.append('</section></div>')
    return "".join(h)

def offer_map(blocks):
    out = ['<div class="map">']
    for b in blocks:
        det = is_detailed(b)
        clean = lambda f: re.sub(r"\s*\[.*?\]", "", strip_num(f))
        fams = "".join(f'<li><span>{esc(num(f))}</span>{esc(clean(f))}</li>' for f in b["families"])
        desc = "" if det or not b["intro"] else f'<p class="map-desc">{esc(str(b["intro"]).replace("**", ""))}</p>'
        link = f'<a class="map-link" href="#block-{b["n"]}">See the detail</a>' if det else ""
        out.append(f'<article class="map-col{" is-detailed" if det else ""}"><p class="map-n">Block {b["n"]}</p><h3>{esc(b["name"])}</h3>{desc}<ul>{fams}</ul>{link}</article>')
    return "".join(out) + "</div>"

def chart():
    w, hgt, pl, pb, pt = 520, 230, 34, 26, 18
    maxv = max(5.0, max(v for _, v in TURNOVER) * 1.15); bw = (w - pl - 10) / len(TURNOVER)
    y = lambda v: pt + (hgt - pt - pb) * (1 - v / maxv)
    g = []
    for t in range(0, int(maxv) + 1):
        g.append(f'<line x1="{pl}" x2="{w-6}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="grid"/><text x="{pl-8}" y="{y(t)+4:.1f}" class="ax" text-anchor="end">{t}</text>')
    for i, (yr, v) in enumerate(TURNOVER):
        x = pl + i * bw + bw * 0.2; bwid = bw * 0.6; cls = "bar last" if i == len(TURNOVER) - 1 else "bar"
        g.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bwid:.1f}" height="{y(0)-y(v):.1f}" rx="2" class="{cls}"/>'
                 f'<text x="{x+bwid/2:.1f}" y="{y(v)-6:.1f}" class="val" text-anchor="middle">{str(v).replace(".", ",")}</text>'
                 f'<text x="{x+bwid/2:.1f}" y="{hgt-8}" class="ax" text-anchor="middle">{yr}</text>')
    a, b = TURNOVER[0], TURNOVER[-1]
    return (f'<figure class="chart"><svg viewBox="0 0 {w} {hgt}" role="img" aria-label="ALTEN Group turnover {a[0]} to {b[0]}, in billion euros">'
            + "".join(g) + f'</svg><figcaption>ALTEN Group turnover, B€, {a[0]}–{b[0]}.</figcaption></figure>')

# ------------------------------------------------------------------ principal
def main(xlsx):
    for f in ("plantilla_informe.html", "procesos.html"):
        if not os.path.isfile(os.path.join(HERE, f)): sys.exit(f"ERROR: falta {f} junto al script")
    blocks, catalogue, digital = read_excel(xlsx)
    tpl = open(os.path.join(HERE, "plantilla_informe.html"), encoding="utf-8").read()
    proc = open(os.path.join(HERE, "procesos.html"), encoding="utf-8").read()
    detailed = [b for b in blocks if is_detailed(b)]
    sections = "".join(block_section(b, [f for f in catalogue if f["block"] == b["code"]], [d for d in digital if d["block"] == b["code"]]) for b in detailed)
    nav = "".join(f'<a href="#block-{b["n"]}">{esc(b["name"])}</a>' for b in detailed)
    seen, all_logos = set(), []
    for b in blocks:
        for n in [x.strip() for x in re.split(r"[;,\n]", str(b["logos"] or "")) if x.strip()]:
            if n.lower() in seen: continue
            seen.add(n.lower()); f = find_logo(n)
            if f: all_logos.append(f'<li><img src="{data_uri(f)}" alt="{esc(n)}"></li>')
    img = lambda n: data_uri(os.path.join(HERE, "img", n)) if os.path.isfile(os.path.join(HERE, "img", n)) else ""
    rep = {"{{HERO}}": img("hero.jpg"), "{{LOGO}}": img("logo.png"), "{{FRAME}}": img("frame.png"),
           "{{MAP}}": offer_map(blocks), "{{CHART}}": chart(), "{{BLOCKS}}": sections, "{{NAV_BLOCKS}}": nav,
           "{{PROCESSES}}": proc, "{{ALL_LOGOS}}": "".join(all_logos)}
    for k, v in rep.items(): tpl = tpl.replace(k, v)
    out = os.path.join(HERE, OUT_NAME)
    with open(out, "w", encoding="utf-8") as f: f.write(tpl)
    print(f"Generado: {OUT_NAME}  ({os.path.getsize(out)//1024} KB)")
    print("Bloques con seccion detallada: " + (", ".join(f'{b["n"]} {b["name"]}' for b in detailed) or "ninguno"))
    for b in blocks:
        if not is_detailed(b): print(f"   - Bloque {b['n']} solo en el mapa (faltan introduccion o key figures en la columna {COLS[b['n']-1]})")
    if warnings:
        print("\nAVISOS:"); [print("  -", w) for w in dict.fromkeys(warnings)]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        xlsx = sys.argv[1]
    else:
        xl = [f for f in glob.glob(os.path.join(HERE, "*.xlsx")) if not os.path.basename(f).startswith("~$")]
        if len(xl) != 1:
            sys.exit("ERROR: deje un solo Excel en la carpeta o indique su nombre: python generar_informe.py datos.xlsx")
        xlsx = xl[0]
    if not os.path.isfile(xlsx): sys.exit(f"ERROR: no encuentro el Excel {xlsx}")
    print(f"Excel: {os.path.basename(xlsx)}")
    main(xlsx)

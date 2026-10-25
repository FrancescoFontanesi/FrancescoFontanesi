#!/usr/bin/env python3
"""Cyber Nihilism — GitHub profile asset builder.

Reads tokens.json (the design system's single source of colour) and
config.json (your content) and writes static, self-contained SVGs to
../assets/. Fonts are subset to the glyphs actually used and embedded as
WOFF2, because an SVG shown through <img> cannot load web fonts.

Usage:  pip install fonttools brotli numpy pillow
        python scripts/build.py          (add --embed-fonts for live <text>)
"""
import base64, io, json, math, random
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools import subset as ftsubset
from fontTools.varLib.instancer import instantiateVariableFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "assets"
FONTS = HERE / "fonts"
TOKENS = json.loads((HERE / "tokens.json").read_text())
CFG = json.loads((HERE / "config.json").read_text())

# ── tokens ──────────────────────────────────────────────────────────────
def palette(theme):
    return {t["name"]: (t["value"][theme] if isinstance(t["value"], dict) else t["value"])
            for t in TOKENS["color"]["tokens"]}

def tok(family, name):
    for t in TOKENS[family]["tokens"]:
        if t["name"] == name:
            return float(str(t["value"]).replace("px", "").replace("ms", ""))
    raise KeyError(name)

STEP = tok("tempo", "tempo-step")      # 60 ms
CHAR = tok("tempo", "tempo-char")      # 28 ms
BLINK = tok("tempo", "tempo-blink")    # 1000 ms
MARGIN = tok("spacing", "space-5")       # 40 px
GUTTER = tok("spacing", "space-4")       # 24 px
EXT = tok("layout", "layout-construct-ext")  # 32 px
CUT = tok("chamfer", "chamfer-lg")     # 24 px

# ── fonts ───────────────────────────────────────────────────────────────
_cache = {}

def load(path, wght=None):
    key = (path, wght)
    if key not in _cache:
        f = TTFont(FONTS / path)
        if wght is not None and "fvar" in f:
            f = instantiateVariableFont(f, {"wght": wght})
        _cache[key] = f
    return _cache[key]

def advance(font, text, size, tracking_em=0.0):
    """Width of text in px (no kerning), including SVG letter-spacing after each glyph."""
    cmap, hmtx, upm = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm
    w = sum(hmtx[cmap.get(ord(c), cmap.get(ord("?")))][0] for c in text)
    return w * size / upm + len(text) * tracking_em * size

def embed(path, text, family, wght=None):
    font = load(path, wght)
    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    f = TTFont(buf)
    opts = ftsubset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    opts.name_IDs = []
    opts.notdef_outline = True
    s = ftsubset.Subsetter(opts)
    s.populate(text="".join(sorted(set(text + " "))))
    s.subset(f)
    out = io.BytesIO()
    f.flavor = "woff2"
    f.save(out)
    b64 = base64.b64encode(out.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{b64}) format('woff2');}}"

# Text mode. "outline" (default) converts every glyph to a path: nothing to
# load, so it renders the same whatever CSP the image is served with.
# "embed" keeps live <text> with subset WOFF2 fonts (smaller to edit, but
# data: fonts can be blocked by the CSP some hosts send with SVG files).
import sys
MODE = "embed" if "--embed-fonts" in sys.argv else "outline"

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

def outline(font, text, size, x, y, tracking_em=0.0, anchor="start"):
    """Path data for text set at (x, baseline y)."""
    if anchor != "start":
        w = advance(font, text, size, tracking_em) - tracking_em * size
        x -= w if anchor == "end" else w / 2
    gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    k = size / font["head"].unitsPerEm
    pen = SVGPathPen(gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
    for ch in text:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        gs[g].draw(TransformPen(pen, (k, 0, 0, -k, x, y)))
        x += hmtx[g][0] * k + tracking_em * size
    return pen.getCommands()

def T(font_file, text, size, x, y, cls, tracking_em=0.0, anchor="start", attrs="", wght=None, idattr=""):
    """One run of text, as <path> (outline mode) or <text> (embed mode)."""
    if MODE == "outline":
        d = outline(load(font_file, wght), text, size, x, y, tracking_em, anchor)
        return f'<path {idattr}class="{cls}" {attrs} d="{d}"/>'
    USED.setdefault((font_file, wght), set()).add(text)
    fam = f"CN {Path(font_file).stem}"
    font_css = f"font-family:'{fam}',monospace;font-size:{size}px;letter-spacing:{tracking_em}em;font-weight:normal"
    attrs = attrs.replace('style="', f'style="{font_css};') if 'style="' in attrs else attrs + f' style="{font_css}"'
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    return f'<text {idattr}class="{cls}" {attrs} x="{x:.1f}" y="{y:.1f}"{a} xml:space="preserve">{esc(text)}</text>'

USED = {}

def fonts_css():
    """@font-face rules for every run T() emitted since the last call (embed mode)."""
    css = "".join(embed(f, "".join(t), f"CN {Path(f).stem}", wght) for (f, wght), t in USED.items())
    USED.clear()
    return css

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ── shared pieces ───────────────────────────────────────────────────────
BASE_CSS = """
.s{visibility:hidden;animation:cn-on 1ms linear forwards}
.d{stroke-dasharray:1;stroke-dashoffset:1;animation:cn-draw %(draw)dms steps(6) forwards}
.blink{animation:cn-blink %(blink)dms steps(1) infinite}
@keyframes cn-on{from,to{visibility:visible}}
@keyframes cn-draw{to{stroke-dashoffset:0}}
@keyframes cn-blink{50%%{visibility:hidden}}
@media (prefers-reduced-motion:reduce){
 .s{animation:none;visibility:visible}
 .d{animation:none;stroke-dashoffset:0}
 .blink{animation:none}
}
"""

def delay(ms):
    return f'style="animation-delay:{int(ms)}ms"'

# ── stipple sphere (Matter, stipple mode) ───────────────────────────────
def stipple_sphere(R, theme, seed, batches=8):
    """Seeded gaussian point cloud anchored on a lit sphere.
    Signal (dark) stipples the light; Print (light) stipples the shadow."""
    rng = random.Random(seed)
    L = (-0.55, -0.62, 0.56)
    n = math.sqrt(sum(c * c for c in L))
    L = tuple(c / n for c in L)
    dots = []

    def tone_at(nx, ny, nz):
        lam = max(0.0, nx * L[0] + ny * L[1] + nz * L[2])
        return lam ** 1.25 if theme == "dark" else (1 - lam) ** 1.15

    # body
    for _ in range(12000):
        r = math.sqrt(rng.random())
        a = rng.random() * math.tau
        nx, ny = r * math.cos(a), r * math.sin(a)
        nz = math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
        t = tone_at(nx, ny, nz)
        if rng.random() < t * 0.5:
            size = max(0.4, min(1.7, 0.45 + 1.0 * t + rng.gauss(0, 0.16)))
            dots.append((nx * R, ny * R, size, nx * L[0] + ny * L[1]))
    # silhouette: points gaussian-distributed just inside the edge (σ ≈ 0.026 R)
    for _ in range(900):
        a = rng.random() * math.tau
        r = 1 - abs(rng.gauss(0, 0.026))
        nx, ny = r * math.cos(a), r * math.sin(a)
        nz = math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
        t = tone_at(nx, ny, nz)
        if rng.random() < 0.28 + 0.6 * t:
            size = max(0.45, min(1.4, 0.55 + 0.6 * t + rng.gauss(0, 0.12)))
            dots.append((nx * R, ny * R, size, nx * L[0] + ny * L[1]))

    # reveal order: a soft front sweeping from the lit side, with noise
    groups = [[] for _ in range(batches)]
    for x, y, s, proj in dots:
        k = (-proj + 1) / 2 + rng.gauss(0, 0.12)
        groups[max(0, min(batches - 1, int(k * batches)))].append((x, y, s))
    return groups, len(dots)

# ── hero ────────────────────────────────────────────────────────────────
def hero(theme):
    c = palette(theme)
    signal = theme == "dark"
    W, H = 1200, 440
    top_rule, bot_rule = 72, 368
    inner = W - 2 * MARGIN
    col = (inner - 11 * GUTTER) / 12

    mono_size, mono_track = 16, 0.14
    handle = CFG["wordmark"].upper()
    role = CFG["role"] if signal else f"[ {CFG['role'].upper()} ]"

    disp_bold = "Rajdhani-Bold.ttf"
    role_font = "Rajdhani-Light.ttf" if signal else "Rajdhani-Bold.ttf"

    # wordmark fits columns 1–8
    wm_max = 8 * col + 7 * GUTTER
    wm_track = -0.04
    wm_size = min(196, wm_max / (advance(load(disp_bold), handle, 1, wm_track) or 1))
    wm_base = 252
    role_size = 44 if signal else 38
    role_base = 316
    role_track = 0.0 if signal else 0.01

    # mono strings
    header_left = "00 / PROFILE"
    header_right = CFG["header_right"].upper()
    footer = CFG["footer"]
    obj_label = CFG["object_label"]
    mono_text = header_left + header_right + obj_label + "|" + "".join(k + v for k, v in footer)

    css = "/*FONTS*/" + BASE_CSS % {"draw": 6 * STEP, "blink": BLINK}
    css += f"""
.mono{{font-family:'CN Mono',ui-monospace,monospace;font-size:{mono_size}px;letter-spacing:{mono_track}em;font-weight:500}}
.mu{{fill:{c['ink-muted']}}} .ink{{fill:{c['ink']}}}
.wm{{font-family:'CN Display Bold','Arial Narrow',sans-serif;font-weight:700;font-size:{wm_size:.1f}px;letter-spacing:{wm_track}em;fill:{c['ink']}}}
.role{{font-family:'CN Display Role','Arial Narrow',sans-serif;font-weight:{300 if signal else 700};font-size:{role_size}px;letter-spacing:{role_track}em;fill:{c['ink']}}}
"""
    MONO = ("JetBrainsMono-VF.ttf", mono_size, mono_track, 500)
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">')
    o.append(f'<title id="t">{esc(CFG["wordmark"])} — {esc(CFG["role"])}</title>')
    o.append(f"<style>{css}</style>")

    frame = f"M0.5 0.5H{W - CUT}L{W - 0.5} {CUT}V{H - 0.5}H0.5Z"
    o.append("<defs>")
    o.append(f'<clipPath id="fr"><path d="{frame}"/></clipPath>')
    if signal:  # CRT scanlines (Signal only)
        o.append(f'<pattern id="pt" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="{c["grid"]}"/></pattern>')
    else:       # dot grid (Print)
        o.append(f'<pattern id="pt" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="8" cy="8" r="0.9" fill="{c["line"]}"/></pattern>')
    # wordmark lands in four bands
    cap_top = wm_base - wm_size * 0.72
    band_h = (wm_base + 4 - cap_top) / 4
    for i in range(4):
        o.append(f'<clipPath id="b{i}"><rect x="0" y="{cap_top + i * band_h - (2 if i == 0 else 0):.1f}" width="{W}" height="{band_h + (2 if i == 0 else 0) + (40 if i == 3 else 0):.1f}"/></clipPath>')
    o.append(T(disp_bold, handle, wm_size, MARGIN - 4, wm_base, "wm", wm_track, idattr='id="wm" '))
    o.append("</defs>")

    # ground, texture, guides
    o.append(f'<path d="{frame}" fill="{c["ground"]}"/>')
    o.append(f'<g clip-path="url(#fr)"><rect width="{W}" height="{H}" fill="url(#pt)"/>')
    for i in range(12):
        x = MARGIN + i * (col + GUTTER) + 0.5
        o.append(f'<line x1="{x:.1f}" y1="{top_rule}" x2="{x:.1f}" y2="{bot_rule}" stroke="{c["line"]}" stroke-width="1"/>')
    xr = W - MARGIN - 0.5
    o.append(f'<line x1="{xr}" y1="{top_rule}" x2="{xr}" y2="{bot_rule}" stroke="{c["line"]}" stroke-width="1"/>')
    o.append("</g>")
    o.append(f'<path d="{frame}" fill="none" stroke="{c["line-strong"]}" stroke-width="1"/>')

    # header / footer rows
    if signal:
        o.append(f'<line x1="{MARGIN}" y1="{top_rule + .5}" x2="{W - MARGIN}" y2="{top_rule + .5}" stroke="{c["line"]}" stroke-width="1"/>')
        o.append(f'<line x1="{MARGIN}" y1="{bot_rule + .5}" x2="{W - MARGIN}" y2="{bot_rule + .5}" stroke="{c["line"]}" stroke-width="1"/>')
    else:  # Print: 2px ink rule opens the view
        o.append(f'<line x1="{MARGIN}" y1="{top_rule + 1}" x2="{W - MARGIN}" y2="{top_rule + 1}" stroke="{c["ink"]}" stroke-width="2"/>')
        o.append(f'<line x1="{MARGIN}" y1="{bot_rule + .5}" x2="{W - MARGIN}" y2="{bot_rule + .5}" stroke="{c["line"]}" stroke-width="1"/>')
    o.append(T(MONO[0], header_left, mono_size, MARGIN, 52, "mono ink", mono_track, wght=500))
    o.append(T(MONO[0], header_right, mono_size, W - MARGIN, 52, "mono mu", mono_track, anchor="end", wght=500))

    x = MARGIN
    mono = load("JetBrainsMono-VF.ttf", 500)
    parts = []
    for i, (k, v) in enumerate(footer):
        if i:
            parts.append((" | ", "mu"))
        parts.append((k + " ", "mu"))
        parts.append((v, "ink"))
    for s, cls in parts:
        o.append(T(MONO[0], s, mono_size, x, H - MARGIN, f"mono {cls}", mono_track, wght=500))
        x += advance(mono, s, mono_size, mono_track)

    # wordmark (4 bands, tempo-step apart) ───────────────────────────────
    t0 = 120
    for i in range(4):
        o.append(f'<g class="s" {delay(t0 + i * STEP)} clip-path="url(#b{i})"><use href="#wm"/></g>')
    # the landed wordmark, unclipped, covers the band seams
    o.append(f'<use class="s" {delay(t0 + 4 * STEP)} href="#wm"/>')

    # role line typed in, then the cursor stays and blinks ───────────────
    rf = load(role_font)
    t_role = t0 + 4 * STEP + 2 * STEP
    rx = MARGIN
    for i, ch in enumerate(role):
        if ch != " ":
            o.append(T(role_font, ch, role_size, rx, role_base, "role s", role_track, attrs=delay(t_role + i * CHAR)))
        rx += advance(rf, ch, role_size, role_track)
    t_end = t_role + len(role) * CHAR
    o.append(f'<g class="s" {delay(t_end)}>' + T(role_font, "_", role_size, rx + 4, role_base, "role blink", role_track) + '</g>')

    # object: construct + stipple sphere (cols 9–12) ─────────────────────
    R = 100
    cx = MARGIN + 8 * (col + GUTTER) + (4 * col + 3 * GUTTER) / 2
    cy = (top_rule + bot_rule) / 2
    l, r_, t, b = cx - R, cx + R, cy - R, cy + R
    ext_c, dim_c, cross_c = c["line"], c["line-strong"], c["ink"]

    def ln(x1, y1, x2, y2, col_, cls="d", d=0, dash=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        cl = f' class="{cls}" pathLength="1" {delay(d)}' if cls == "d" else ""
        return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col_}" stroke-width="1"{cl}{extra}/>'

    # extension lines overshooting by layout-construct-ext
    for yy in (t + .5, b - .5):
        o.append(ln(l - EXT, yy, r_ + EXT, yy, ext_c))
    for xx in (l + .5, r_ - .5):
        o.append(ln(xx, t - EXT + 8, xx, b + EXT - 16, ext_c))
    # circle, drawn in steps
    o.append(f'<circle class="d" pathLength="1" {delay(0)} cx="{cx:.1f}" cy="{cy}" r="{R}" fill="none" stroke="{dim_c}" stroke-width="1"/>')
    # dashed axes appear at the end of the draw
    o.append(f'<g class="s" {delay(6 * STEP)}>'
             + ln(l - 12, cy, r_ + 12, cy, dim_c, cls="", dash="6 4")
             + ln(cx, t - 12, cx, b + 12, dim_c, cls="", dash="6 4") + "</g>")
    # dimension line above the object
    dy = t - 22
    lw = advance(load(MONO[0], 500), obj_label, mono_size, mono_track) + 16
    o.append(f'<g class="s" {delay(6 * STEP)}>'
             + ln(l, dy, r_, dy, dim_c, cls="")
             + ln(l + .5, dy - 5, l + .5, dy + 5, dim_c, cls="")
             + ln(r_ - .5, dy - 5, r_ - .5, dy + 5, dim_c, cls="")
             + f'<rect x="{cx - lw / 2:.1f}" y="{dy - 9:.1f}" width="{lw:.1f}" height="18" fill="{c["ground"]}"/>'
             + T(MONO[0], obj_label, mono_size, cx, dy + 5, "mono ink", mono_track, anchor="middle", wght=500) + '</g>')
    # registration crosses at the corners
    cross = []
    for (xx, yy) in ((l, t), (r_, t), (l, b), (r_, b)):
        cross.append(f'<path d="M{xx - 7:.1f} {yy:.1f}H{xx + 7:.1f}M{xx:.1f} {yy - 7:.1f}V{yy + 7:.1f}" stroke="{cross_c}" stroke-width="1" fill="none"/>')
    o.append(f'<g class="s" {delay(6 * STEP)}>' + "".join(cross) + "</g>")

    # stipple, eight batches behind a soft front
    groups, count = stipple_sphere(R - 1.5, theme, CFG.get("seed", 7))
    t_st = 6 * STEP
    for i, g in enumerate(groups):
        pts = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s:.2f}"/>' for x, y, s in g)
        o.append(f'<g class="s" {delay(t_st + i * STEP)} fill="{c["ink"]}" transform="translate({cx:.1f} {cy:.1f})">{pts}</g>')

    o.append("</svg>")
    return finish(o), count

def finish(o):
    svg = "\n".join(o)
    return svg.replace("/*FONTS*/", fonts_css() if MODE == "embed" else "")

MONO_F = "JetBrainsMono-VF.ttf"

def main():
    import poster
    OUT.mkdir(exist_ok=True)
    for theme, name in (("dark", "signal"), ("light", "print")):
        svg = poster.poster(theme)
        p = OUT / f"profile-{name}.svg"
        p.write_text(svg)
        print(f"{p.relative_to(HERE.parent)}  {len(svg.encode()) / 1024:.0f} KB  [{MODE}]")

if __name__ == "__main__":
    main()

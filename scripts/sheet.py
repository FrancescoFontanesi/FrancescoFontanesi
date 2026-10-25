#!/usr/bin/env python3
"""The profile panel: an engineering sheet (Cyber Nihilism, L2).

Icosahedron as a gaussian stipple plate under a full construct (circle,
diagonals, dimensions), three vertex trackers, a wandering ASCII lens;
name, role tag, notes and a title block on the right; square lattice of
dots and crosses behind. Content comes from config.json.
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import build as B
import panel as Pn

STEP, CHAR, BLINK, MARGIN, GUTTER, EXT, CUT = B.STEP, B.CHAR, B.BLINK, B.MARGIN, B.GUTTER, B.EXT, B.CUT
MONO, RAMP = B.MONO_F, Pn.RAMP
FRAME_MS = B.tok("tempo", "tempo-frame")
PITCH = B.tok("spacing", "space-4")
BOLD, LIGHT = "Rajdhani-Bold.ttf", "Rajdhani-Light.ttf"
CW, CH, GS = 10.5, 18, 17.5            # readable ASCII cell (7 × 12 at README scale)

# ── document scaffolding ────────────────────────────────────────────────
class Doc:
    def __init__(self, W, H, theme, title):
        self.W, self.H, self.c = W, H, B.palette(theme)
        self.signal = theme == "dark"
        self.title, self.css, self.defs, self.o = title, "", [], []
        self.mono = B.load(MONO, 500)
        self.frame = f"M0.5 0.5H{W - CUT}L{W - 0.5} {CUT}V{H - 0.5}H0.5Z"
        self.defs.append(f'<clipPath id="fr"><path d="{self.frame}"/></clipPath>')
        self.gid = None

    def glyphs(self):
        if self.gid is None:
            self.gid = {}
            for i, chx in enumerate(sorted(set(RAMP[1:] + "-\\|/"))):
                self.gid[chx] = f"g{i}"
                self.defs.append(f'<path id="g{i}" d="{B.outline(self.mono, chx, GS, 0, 0)}"/>')
        return self.gid

    def render(self):
        c = self.c
        css = ("/*FONTS*/" + B.BASE_CSS % {"draw": 6 * STEP, "blink": BLINK}
               + f".mu{{fill:{c['ink-muted']}}}.ink{{fill:{c['ink']}}}.gr{{fill:{c['ground']}}}" + self.css)
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" width="{self.W}" height="{self.H}" role="img" aria-labelledby="t">',
               f'<title id="t">{B.esc(self.title)}</title>', f"<style>{css}</style>",
               "<defs>" + "".join(self.defs) + "</defs>",
               f'<path d="{self.frame}" fill="{c["ground"]}"/>',
               '<g clip-path="url(#fr)">'] + self.o + ["</g>",
               f'<path d="{self.frame}" fill="none" stroke="{c["line-strong"]}" stroke-width="1"/>', "</svg>"]
        return B.finish(out)

    # lattice: dot every PITCH, thin cross every fourth; returns a keep-out helper
    def lattice(self, x0, y0, x1, y1, ox, oy, clip=None):
        c, n = self.c, len(self.defs)
        self.defs.append(f'<pattern id="ld{n}" x="{ox - PITCH / 2}" y="{oy - PITCH / 2}" width="{PITCH}" height="{PITCH}" patternUnits="userSpaceOnUse">'
                         f'<circle cx="{PITCH / 2}" cy="{PITCH / 2}" r="1" fill="{c["line"]}"/></pattern>')
        self.defs.append(f'<pattern id="lx{n}" x="{ox - PITCH / 2}" y="{oy - PITCH / 2}" width="{4 * PITCH}" height="{4 * PITCH}" patternUnits="userSpaceOnUse">'
                         f'<path d="M{PITCH / 2 - 4} {PITCH / 2}H{PITCH / 2 + 4}M{PITCH / 2} {PITCH / 2 - 4}V{PITCH / 2 + 4}" stroke="{c["line-strong"]}" stroke-width="0.6" fill="none"/></pattern>')
        cp = f' clip-path="url(#{clip})"' if clip else ""
        self.o.append(f'<g{cp}><rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#ld{n})"/>'
                      f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#lx{n})"/></g>')
        def keep_out(a0, b0, a1, b1):
            a = ox + math.floor((a0 - ox) / PITCH - .5) * PITCH + PITCH / 2
            b = ox + math.ceil((a1 - ox) / PITCH + .5) * PITCH - PITCH / 2
            p = oy + math.floor((b0 - oy) / PITCH - .5) * PITCH + PITCH / 2
            q = oy + math.ceil((b1 - oy) / PITCH + .5) * PITCH - PITCH / 2
            self.o.append(f'<rect x="{a}" y="{p}" width="{b - a}" height="{q - p}" fill="{c["ground"]}"/>')
        return keep_out

    def knock(self, x, y, w, h):
        self.o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{self.c["ground"]}"/>')

    def line(self, x1, y1, x2, y2, col, draw_at=None, dash=None, width=1):
        a = f' class="d" pathLength="1" {B.delay(draw_at)}' if draw_at is not None else ""
        a += f' stroke-dasharray="{dash}"' if dash else ""
        return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{width}"{a}/>'

    def mono_t(self, s, x, y, cls, size=16, track=0.14, anchor="start", attrs="", wght=500):
        return B.T(MONO, s, size, x, y, cls, track, anchor=anchor, attrs=attrs, wght=wght)

    def adv(self, s, size=16, track=0.14):
        return B.advance(self.mono, s, size, track)

    def typed(self, font, text, size, x, y, cls, t, track=0.0, wght=None):
        """Characters land one per tempo-char. Returns the time the line ends."""
        f = B.load(font, wght)
        for chx in text:
            if chx != " ":
                self.o.append(B.T(font, chx, size, x, y, f"{cls} s", track, attrs=B.delay(t), wght=wght))
            x += B.advance(f, chx, size, track)
            t += CHAR
        return t, x

    def wordmark(self, text, size, x, base, t0, track=-0.04, transform=None):
        """Four bands, tempo-step apart, then the whole word (covers band seams)."""
        n = len(self.defs)
        cap_top = base - size * 0.72
        bh = (base + 4 - cap_top) / 4
        for i in range(4):
            self.defs.append(f'<clipPath id="b{n}_{i}"><rect x="-4000" y="{cap_top + i * bh - (2 if i == 0 else 0):.1f}" width="9000" height="{bh + (2 if i == 0 else 0) + (40 if i == 3 else 0):.1f}"/></clipPath>')
        self.defs.append(B.T(BOLD, text, size, x, base, "ink", track, idattr=f'id="wm{n}" '))
        tr = f' transform="{transform}"' if transform else ""
        g = [f"<g{tr}>"]
        for i in range(4):
            g.append(f'<g class="s" {B.delay(t0 + i * STEP)} clip-path="url(#b{n}_{i})"><use href="#wm{n}"/></g>')
        g.append(f'<use class="s" {B.delay(t0 + 4 * STEP)} href="#wm{n}"/></g>')
        self.o.append("".join(g))
        return t0 + 4 * STEP

    def lens_css(self, name, n, on_frac):
        self.css += (f".{name}{{visibility:hidden;animation-name:{name};animation-timing-function:linear;animation-iteration-count:infinite}}"
                     f"@keyframes {name}{{0%,{on_frac * 100 - 0.001:.3f}%{{visibility:visible}}{on_frac * 100:.3f}%,100%{{visibility:hidden}}}}"
                     f"@media (prefers-reduced-motion:reduce){{.{name}{{animation:none}}.{name}.rest{{visibility:visible}}}}")

    def lens_window(self, X0, Y0, cols, rows, ascii_at, chip, chip_below=False):
        """Ground knockout + ASCII cells + ink frame + corner pips + inverted chip."""
        c, gid = self.c, self.glyphs()
        w, h = cols * CW, rows * CH
        g = [f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{c["ground"]}"/>']
        for r in range(rows):
            for k in range(cols):
                chx = ascii_at(X0 + (k + .5) * CW, Y0 + (r + .5) * CH)
                if chx != " ":
                    g.append(f'<use href="#{gid[chx]}" x="{X0 + k * CW:.1f}" y="{Y0 + r * CH + CH - 4:.1f}"/>')
        g.append(f'<rect x="{X0 + .5:.1f}" y="{Y0 + .5:.1f}" width="{w - 1:.1f}" height="{h - 1:.1f}" fill="none" stroke="{c["ink"]}" stroke-width="1"/>')
        for qx, qy in ((X0, Y0), (X0 + w, Y0), (X0, Y0 + h), (X0 + w, Y0 + h)):
            g.append(f'<rect x="{qx - 2.5:.1f}" y="{qy - 2.5:.1f}" width="5" height="5" fill="{c["ink"]}"/>')
        cw_ = self.adv(chip, 13, 0.1) + 12
        cy = Y0 + h + 2 if chip_below else Y0 - 20
        g.append(f'<rect x="{X0:.1f}" y="{cy:.1f}" width="{cw_:.1f}" height="18" fill="{c["ink"]}"/>')
        g.append(self.mono_t(chip, X0 + 6, cy + 14, "gr", 13, 0.1))
        return "".join(g)

    def stipple(self, dots, cx, cy, t0, key, batches=8):
        rng = random.Random(5)
        groups = [[] for _ in range(batches)]
        for d in dots:
            x, y, s = d[:3]
            k = key(x, y) + rng.gauss(0, 0.1)
            groups[max(0, min(batches - 1, int(k * batches)))].append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s:.2f}"/>')
        for i, g in enumerate(groups):
            self.o.append(f'<g class="s" {B.delay(t0 + i * STEP)} fill="{self.c["ink"]}" transform="translate({cx:.1f} {cy:.1f})">{"".join(g)}</g>')

    def header(self, left, right, y=52, rule=72):
        c = self.c
        self.o.append(self.mono_t(left, MARGIN, y, "ink"))
        self.o.append(self.mono_t(right, self.W - MARGIN, y, "mu", anchor="end"))
        if self.signal:
            self.o.append(self.line(MARGIN, rule + .5, self.W - MARGIN, rule + .5, c["line"]))
        else:
            self.o.append(self.line(MARGIN, rule + 1, self.W - MARGIN, rule + 1, c["ink"], width=2))


CFG = B.CFG
PRINCIPLES = [t for k, t in CFG["terminal"]["lines"][2:] if k == "out"]
TITLE = (f"{CFG['wordmark']} {CFG['first_name']}. {CFG['role'].capitalize()}. "
         + " ".join(p.capitalize() for p in PRINCIPLES))

def snap(v, o):
    return o + round((v - o) / PITCH) * PITCH


# ═══ V1 · DRAWING ═══════════════════════════════════════════════════════
def v1(theme):
    W, H = 1200, 720
    d = Doc(W, H, theme, TITLE)
    c = d.c
    top, bot = 72, H - 40
    d.header("00 / PROFILE", "SHEET 01 / 01", rule=top)
    keep = d.lattice(MARGIN - PITCH / 2, top + PITCH / 2, W - MARGIN + PITCH / 2, bot, MARGIN, top)

    # right column: identity, notes, title block
    rx = 760
    rw = W - MARGIN - rx
    wm = CFG["wordmark"].upper()
    ws = rw / B.advance(B.load(BOLD), wm, 1, -0.04)
    wb = top + 32 + ws * 0.70
    first = CFG["first_name"] if d.signal else CFG["first_name"].upper()
    nf = LIGHT if d.signal else BOLD
    nb = wb + 52
    tag = f"[ {CFG['role'].upper()} ]"
    tb = nb + 46
    nl = tb + 70
    notes = [f"{i + 1}  {p}" for i, p in enumerate(PRINCIPLES)]
    tbx, tby, tbw, tbh = rx, bot - 156, rw, 132        # title block

    keep(rx, wb - ws * 0.72, rx + rw, wb)
    keep(rx, nb - 30, rx + B.advance(B.load(nf), first, 38), nb + 6)
    keep(rx, tb - 13, rx + d.adv(tag), tb + 3)
    keep(rx, nl - 14, rx + rw, nl + 2 * 30 + 6)
    keep(tbx, tby, tbx + tbw, tby + tbh)

    t = d.wordmark(wm, ws, rx - 3, wb, 120)
    t, _ = d.typed(nf, first, 38, rx, nb, "ink", t + 2 * STEP)
    d.o.append(d.mono_t(tag, rx, tb, "ink s", attrs=B.delay(t + 2 * STEP)))
    # notes: a section opener (notch + mono index), lines typed
    d.o.append(f'<rect x="{rx}" y="{nl - 30}" width="24" height="2" fill="{c["ink"]}"/>')
    d.o.append(d.mono_t("NOTES", rx + 34, nl - 23, "mu"))
    tn = t + 6 * STEP
    for i, line in enumerate(notes):
        tn, _ = d.typed(MONO, line, 18, rx, nl + 6 + i * 30, "ink", tn, wght=400)
        tn += 2 * STEP

    # title block: hairline cells, mono keys, ink values
    cells = [("DRAWN", "F. FONTANESI"), ("DATE", "2026.10"), ("SCALE", "1:1"),
             ("TITLE", CFG["object_label"]), ("REV", "01"), ("SHEET", "01/01")]
    colw = [tbw * 0.42, tbw * 0.31, tbw * 0.27]
    colx = [tbx, tbx + colw[0], tbx + colw[0] + colw[1]]
    ch2 = tbh / 2
    tt = tn
    g = [f'<g class="s" {B.delay(tt)}>']
    g.append(f'<rect x="{tbx + .5}" y="{tby + .5}" width="{tbw - 1}" height="{tbh - 1}" fill="none" stroke="{c["line-strong"]}" stroke-width="1"/>')
    for k in (1, 2):
        g.append(d.line(colx[k], tby, colx[k], tby + tbh, c["line-strong"]))
    g.append(d.line(tbx, tby + ch2, tbx + tbw, tby + ch2, c["line-strong"]))
    for i, (k_, v_) in enumerate(cells):
        cx_, cy_ = colx[i % 3] + 12, tby + (i // 3) * ch2
        g.append(d.mono_t(k_, cx_, cy_ + 22, "mu", 12, 0.14))
        g.append(d.mono_t(v_, cx_, cy_ + 50, "ink", 16, 0.1))
    g.append("</g>")
    d.o.append("".join(g))

    # object with full construct
    R = 196
    cx, cy = snap(MARGIN + 340, MARGIN), snap((top + bot) / 2 + 8, top)
    P, dots, hidden, ascii_at = Pn.build_object(R, theme, CFG.get("seed", 7))
    xs, ys = [p[0] for p in P], [p[1] for p in P]
    l, r_, tp, bt = cx + min(xs), cx + max(xs), cy + min(ys), cy + max(ys)
    for yy in (tp + .5, bt - .5):
        d.o.append(d.line(l - EXT, yy, r_ + EXT, yy, c["line"], draw_at=0))
    for xx in (l + .5, r_ - .5):
        d.o.append(d.line(xx, tp - EXT, xx, bt + EXT, c["line"], draw_at=0))
    d.o.append(d.line(l, tp, r_, bt, c["line"], draw_at=STEP))
    d.o.append(d.line(r_, tp, l, bt, c["line"], draw_at=STEP))
    d.o.append(f'<circle class="d" pathLength="1" {B.delay(0)} cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{c["line-strong"]}" stroke-width="1"/>')
    after = 6 * STEP
    dash = [d.line(l - 14, cy, r_ + 14, cy, c["line-strong"], dash="6 4"), d.line(cx, tp - 14, cx, bt + 14, c["line-strong"], dash="6 4")]
    # dimension lines: width above, height on the left
    dy, dx = tp - 26, l - 26
    lab = CFG["object_label"]; lw = d.adv(lab) + 16
    dash += [d.line(l, dy, r_, dy, c["line-strong"]), d.line(l + .5, dy - 5, l + .5, dy + 5, c["line-strong"]), d.line(r_ - .5, dy - 5, r_ - .5, dy + 5, c["line-strong"]),
             f'<rect x="{(l + r_) / 2 - lw / 2:.1f}" y="{dy - 9:.1f}" width="{lw:.1f}" height="18" fill="{c["ground"]}"/>',
             d.mono_t(lab, (l + r_) / 2, dy + 5, "ink", anchor="middle"),
             d.line(dx, tp, dx, bt, c["line-strong"]), d.line(dx - 5, tp + .5, dx + 5, tp + .5, c["line-strong"]), d.line(dx - 5, bt - .5, dx + 5, bt - .5, c["line-strong"])]
    hl = f"H {bt - tp:.0f}"
    dash.append(f'<g transform="translate({dx + 5:.1f} {(tp + bt) / 2:.1f}) rotate(-90)"><rect x="{-d.adv(hl) / 2 - 8:.1f}" y="-14" width="{d.adv(hl) + 16:.1f}" height="18" fill="{c["ground"]}"/>'
                + d.mono_t(hl, 0, 0, "ink", anchor="middle") + "</g>")
    dash += [f'<path d="M{a - 7:.1f} {b:.1f}H{a + 7:.1f}M{a:.1f} {b - 7:.1f}V{b + 7:.1f}" stroke="{c["ink"]}" stroke-width="1"/>' for a, b in ((l, tp), (r_, tp), (l, bt), (r_, bt))]
    d.o.append(f'<g class="s" {B.delay(after)}>' + "".join(dash) + "</g>")
    d.o.append(f'<g class="s" {B.delay(after)} transform="translate({cx} {cy})">' + "".join(
        d.line(P[i][0], P[i][1], P[j][0], P[j][1], c["line-strong"], dash="2 5") for i, j in hidden) + "</g>")
    d.stipple(dots, cx, cy, after, lambda x, y: ((x + y) / (2 * R) + 1) / 2)

    # vertex trackers (three silhouette vertices)
    sil = sorted(range(12), key=lambda i: math.hypot(*P[i][:2]), reverse=True)[:3]
    for n_, i in enumerate(sorted(sil, key=lambda i: P[i][0])):
        vx, vy = cx + P[i][0], cy + P[i][1]
        tt = after + 8 * STEP + n_ * 3 * STEP
        lab = f"V·{n_ + 1:02d}"
        xy = f"X {(vx - l) / (r_ - l):.2f} Y {(vy - tp) / (bt - tp):.2f}"
        lw, xw = d.adv(lab, 13, 0.1) + 12, d.adv(xy, 12, 0.1) + 10
        d.o.append(f'<g class="s" {B.delay(tt)}><rect class="d" pathLength="1" style="animation-delay:{tt}ms" x="{vx - 11}" y="{vy - 11}" width="22" height="22" fill="none" stroke="{c["ink"]}" stroke-width="1"/>'
                   f'<rect x="{vx - 11:.1f}" y="{vy - 31:.1f}" width="{lw:.1f}" height="18" fill="{c["ink"]}"/>'
                   + d.mono_t(lab, vx - 5, vy - 17, "gr", 13, 0.1)
                   + f'<rect x="{vx - 11:.1f}" y="{vy + 13:.1f}" width="{xw:.1f}" height="16" fill="{c["ground"]}"/>'
                   + d.mono_t(xy, vx - 6, vy + 25, "mu", 12, 0.1) + "</g>")

    # ASCII lens
    n, hold = 16, 4 * FRAME_MS
    d.lens_css("lens", n, 1 / n)
    tl = after + 8 * STEP + 10 * STEP
    for k in range(n):
        a = 2 * math.pi * k / n
        X0 = l + round((cx + 0.28 * (r_ - l) * math.sin(a) - 6.5 * CW - l) / CW) * CW
        Y0 = tp + round((cy + 0.24 * (bt - tp) * math.sin(2 * a) - 4 * CH - tp) / CH) * CH
        chip = f"ASCII X {(X0 + 6.5 * CW - l) / (r_ - l):.2f} Y {(Y0 + 4 * CH - tp) / (bt - tp):.2f}"
        body = d.lens_window(X0, Y0, 13, 8, lambda x, y: ascii_at(x - cx, y - cy, CW), chip, chip_below=Y0 - 20 < dy + 12)
        d.o.append(f'<g class="ink lens{" rest" if k == 0 else ""}" style="animation-duration:{int(n * hold)}ms;animation-delay:{int(tl + k * hold)}ms">{body}</g>')
    return d.render()



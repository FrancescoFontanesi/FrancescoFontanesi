#!/usr/bin/env python3
"""The profile as one panel (Cyber Nihilism, L1 page with an L2 object).

Left: wordmark, first name, role tag, a terminal (principles).
Ground: a square lattice of hairline dots and thin crosses.
Right: an icosahedron printed as a gaussian stipple plate, under Construct;
a square Lens wanders over it on a stepped path and reads it as ASCII.
(Objects are never ASCII on their own; the Lens is the system's way to show
both voices on one source.)

Used by sheet.py for the object (icosahedron, stipple, ASCII lookup).
"""
import math, random
import build as B

STEP, CHAR, BLINK, MARGIN, GUTTER, EXT, CUT = B.STEP, B.CHAR, B.BLINK, B.MARGIN, B.GUTTER, B.EXT, B.CUT
MONO = B.MONO_F
RAMP = " .`:-~=+*xo#%@"

LENS_CSS = """
.lens{visibility:hidden;animation-name:cn-lens;animation-timing-function:linear;animation-iteration-count:infinite}
@keyframes cn-lens{0%%,%(on).3f%%{visibility:visible}%(off).3f%%,100%%{visibility:hidden}}
@media (prefers-reduced-motion:reduce){.lens{animation:none}.lens.rest{visibility:visible}}
"""

# ── icosahedron ─────────────────────────────────────────────────────────
def icosahedron(R, ax, ay, az):
    p = (1 + 5 ** .5) / 2
    V = [(-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0), (0, -1, p), (0, 1, p),
         (0, -1, -p), (0, 1, -p), (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1)]
    n = math.sqrt(1 + p * p)
    V = [(x / n, y / n, z / n) for x, y, z in V]
    def rot(v):
        x, y, z = v
        y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
        x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
        x, y = x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az)
        return (x, y, z)
    V = [rot(v) for v in V]
    # faces: triples of mutually adjacent vertices (edge length on the unit sphere)
    e2 = min(sum((a - b) ** 2 for a, b in zip(V[0], V[j])) for j in range(1, 12))
    adj = lambda i, j: abs(sum((a - b) ** 2 for a, b in zip(V[i], V[j])) - e2) < 1e-6
    F = [(i, j, k) for i in range(12) for j in range(i + 1, 12) for k in range(j + 1, 12)
         if adj(i, j) and adj(j, k) and adj(i, k)]
    # screen space: x right, y down, z toward the viewer
    P = [(x * R, -y * R, z) for x, y, z in V]
    out = []
    for f in F:
        a, b, c = (V[i] for i in f)
        u = [b[t] - a[t] for t in range(3)]; w = [c[t] - a[t] for t in range(3)]
        nrm = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        cen = [(a[t] + b[t] + c[t]) / 3 for t in range(3)]
        if sum(nrm[t] * cen[t] for t in range(3)) < 0:
            nrm = [-v for v in nrm]
        L = math.sqrt(sum(v * v for v in nrm))
        nrm = [v / L for v in nrm]
        out.append({"v": f, "n": (nrm[0], -nrm[1], nrm[2])})   # flip y into screen space
    return P, out

def in_tri(px, py, a, b, c):
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    l1 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / d
    l2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / d
    return l1 >= 0 and l2 >= 0 and 1 - l1 - l2 >= 0

def seg_dist(px, py, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((px - a[0]) * vx + (py - a[1]) * vy) / (vx * vx + vy * vy)))
    return math.hypot(px - a[0] - t * vx, py - a[1] - t * vy)

def build_object(R, theme, seed, tagged=False):
    """tagged=True: each dot carries the index (in F) of the visible face it belongs to."""
    rng = random.Random(seed)
    P, F = icosahedron(R, math.radians(18), math.radians(-24), math.radians(8))
    L = (-0.52, -0.62, 0.59)
    n = math.sqrt(sum(v * v for v in L)); L = tuple(v / n for v in L)
    signal = theme == "dark"
    vis = [f for f in F if f["n"][2] > 0]
    for f in F:
        lam = max(0.0, sum(f["n"][t] * L[t] for t in range(3)))
        f["tone"] = (0.1 + 0.9 * lam ** 1.15) if signal else (0.08 + 0.92 * (1 - lam) ** 1.2)
    edges_vis, edges_all = {}, set()
    for f in F:
        i, j, k = f["v"]
        for e in ((i, j), (j, k), (i, k)):
            e = tuple(sorted(e)); edges_all.add(e)
            if f["n"][2] > 0:
                edges_vis[e] = edges_vis.get(e, 0) + 1
    hidden = [e for e in edges_all if e not in edges_vis]
    vverts = {v for e in edges_vis for v in e}

    dots = []
    # faces: density and dot size rise with tone (gaussian sizes)
    fidx = {id(f): n for n, f in enumerate(F)}
    tags = []
    for f in vis:
        a, b, c = (P[i] for i in f["v"])
        area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
        count = int(area * 0.085 * f["tone"] ** 1.5)
        for _ in range(count):
            r1, r2 = rng.random(), rng.random()
            if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
            x = a[0] + r1 * (b[0] - a[0]) + r2 * (c[0] - a[0])
            y = a[1] + r1 * (b[1] - a[1]) + r2 * (c[1] - a[1])
            s = max(0.4, min(1.8, 0.45 + 1.05 * f["tone"] + rng.gauss(0, 0.16)))
            dots.append((x, y, s)); tags.append(fidx[id(f)])
    # edges: gaussian band (σ ≈ 0.026 of the object), corners σ ≈ 0.06
    sig_e, sig_c = 0.026 * R * 0.32, 0.06 * R * 0.28
    owner = lambda vs: next(fidx[id(f)] for f in vis if set(vs) <= set(f["v"]))
    for (i, j) in edges_vis:
        a, b = P[i], P[j]
        fo = owner((i, j))
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        nx, ny = -(b[1] - a[1]) / ln, (b[0] - a[0]) / ln
        for _ in range(int(ln * 0.75)):
            u = rng.random(); o = rng.gauss(0, sig_e)
            dots.append((a[0] + u * (b[0] - a[0]) + nx * o, a[1] + u * (b[1] - a[1]) + ny * o,
                         max(0.4, min(1.2, 0.7 + rng.gauss(0, 0.15))))); tags.append(fo)
    for v in vverts:
        fo = owner((v,))
        for _ in range(18):
            tags.append(fo)
            dots.append((P[v][0] + rng.gauss(0, sig_c), P[v][1] + rng.gauss(0, sig_c),
                         max(0.4, min(1.4, 0.8 + rng.gauss(0, 0.2)))))

    def ascii_at(px, py, cw):
        """Glyph for a cell centred at (px, py) relative to the object centre."""
        best = None
        for (i, j) in edges_vis:
            d = seg_dist(px, py, P[i], P[j])
            if d < cw * 0.55 and (best is None or d < best[0]):
                best = (d, i, j)
        if best:
            _, i, j = best
            a = math.degrees(math.atan2(P[j][1] - P[i][1], P[j][0] - P[i][0])) % 180
            return "-" if a < 22 or a >= 158 else "\\" if a < 68 else "|" if a < 112 else "/"
        for f in vis:
            if in_tri(px, py, *(P[i] for i in f["v"])):
                k = f["tone"] * 13 + rng.gauss(0, 0.8)
                return RAMP[max(1, min(13, int(round(k))))]
        return " "
    if tagged:
        return P, F, [d + (t,) for d, t in zip(dots, tags)], hidden, ascii_at
    return P, dots, hidden, ascii_at

# ── panel ───────────────────────────────────────────────────────────────
def profile(theme):
    cfg = B.CFG
    c = B.palette(theme)
    signal = theme == "dark"
    W = 1200
    PITCH = B.tok("spacing", "space-4")          # 24 px: the lattice cell
    top_rule = 72
    col = (W - 2 * MARGIN - 11 * GUTTER) / 12
    mono = B.load(MONO, 500)

    wm = cfg["wordmark"].upper()
    first = cfg["first_name"] if signal else cfg["first_name"].upper()
    name_font = "Rajdhani-Light.ttf" if signal else "Rajdhani-Bold.ttf"
    tag = f"[ {cfg['role'].upper()} ]"
    bold = "Rajdhani-Bold.ttf"
    left_w = 7 * col + 6 * GUTTER
    wm_track = -0.04
    wm_size = min(220, left_w / B.advance(B.load(bold), wm, 1, wm_track))
    wm_base = top_rule + 24 + wm_size * 0.70
    name_size = 42 if signal else 36
    name_base = wm_base + 58
    tag_base = name_base + 50
    lines = [("cmd", "cat principles.txt")] + [l for l in cfg["terminal"]["lines"][2:] if l[0] == "out"]
    tsize, lh = 20, 36
    term_base = tag_base + 66
    last_base = term_base + len(lines) * lh             # the live prompt
    snap = lambda v: top_rule + math.ceil((v - top_rule) / PITCH) * PITCH
    bot_rule = snap(last_base + 40)
    H = bot_rule + 72

    title = (f"{cfg['wordmark']} {cfg['first_name']}. {cfg['role'].capitalize()}. "
             + " ".join(t.capitalize() for k, t in cfg["terminal"]["lines"][2:] if k == "out"))

    # lens path (computed first: its timing sets the CSS)
    lens_n, lens_hold = 16, 4 * B.tok("tempo", "tempo-frame")   # 332 ms per position
    cyc = lens_n * lens_hold
    css = ("/*FONTS*/" + B.BASE_CSS % {"draw": 6 * STEP, "blink": BLINK}
           + LENS_CSS % {"on": 100 / lens_n - 0.001, "off": 100 / lens_n}
           + f".mu{{fill:{c['ink-muted']}}}.ink{{fill:{c['ink']}}}.gr{{fill:{c['ground']}}}")
    frame = f"M0.5 0.5H{W - CUT}L{W - 0.5} {CUT}V{H - 0.5}H0.5Z"
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">',
         f'<title id="t">{B.esc(title)}</title>', f"<style>{css}</style>", "<defs>",
         f'<clipPath id="fr"><path d="{frame}"/></clipPath>']
    # square lattice: a dot at every 24 px intersection, a thin cross every fourth
    px0, py0 = MARGIN - PITCH / 2, top_rule - PITCH / 2
    o.append(f'<pattern id="ld" x="{px0}" y="{py0}" width="{PITCH}" height="{PITCH}" patternUnits="userSpaceOnUse">'
             f'<circle cx="{PITCH / 2}" cy="{PITCH / 2}" r="1" fill="{c["line"]}"/></pattern>')
    o.append(f'<pattern id="lx" x="{px0}" y="{py0}" width="{4 * PITCH}" height="{4 * PITCH}" patternUnits="userSpaceOnUse">'
             f'<path d="M{PITCH / 2 - 4} {PITCH / 2}H{PITCH / 2 + 4}M{PITCH / 2} {PITCH / 2 - 4}V{PITCH / 2 + 4}" stroke="{c["line-strong"]}" stroke-width="0.6" fill="none"/></pattern>')
    cap_top = wm_base - wm_size * 0.72
    band_h = (wm_base + 4 - cap_top) / 4
    for i in range(4):
        o.append(f'<clipPath id="b{i}"><rect x="0" y="{cap_top + i * band_h - (2 if i == 0 else 0):.1f}" width="{W}" height="{band_h + (2 if i == 0 else 0) + (40 if i == 3 else 0):.1f}"/></clipPath>')
    o.append(B.T(bold, wm, wm_size, MARGIN - 4, wm_base, "ink", wm_track, idattr='id="wm" '))
    # glyph outlines for the lens, defined once
    cw, chh, gsize = 10.5, 18, 17.5
    gid = {}
    for i, chx in enumerate(sorted(set(RAMP[1:] + "-\\|/"))):
        gid[chx] = f"g{i}"
        o.append(f'<path id="g{i}" d="{B.outline(mono, chx, gsize, 0, 0)}"/>')
    o.append("</defs>")

    # ground, texture, guides, frame
    o.append(f'<path d="{frame}" fill="{c["ground"]}"/>')
    # lattice inside the rules; it stops where text sits (patterns never run behind text)
    o.append('<g clip-path="url(#fr)">')
    lx0, lx1 = MARGIN - PITCH / 2, W - MARGIN + PITCH / 2
    ly0, ly1 = top_rule + PITCH / 2, bot_rule - PITCH / 2
    o.append(f'<rect x="{lx0}" y="{ly0}" width="{lx1 - lx0}" height="{ly1 - ly0}" fill="url(#ld)"/>')
    o.append(f'<rect x="{lx0}" y="{ly0}" width="{lx1 - lx0}" height="{ly1 - ly0}" fill="url(#lx)"/>')
    def keep_out(x0, y0, x1, y1):
        """Ground knockout snapped to half-cells: whole lattice points disappear, no edges."""
        a = MARGIN + math.floor((x0 - MARGIN) / PITCH - .5) * PITCH + PITCH / 2
        b = MARGIN + math.ceil((x1 - MARGIN) / PITCH + .5) * PITCH - PITCH / 2
        cc = top_rule + math.floor((y0 - top_rule) / PITCH - .5) * PITCH + PITCH / 2
        d = top_rule + math.ceil((y1 - top_rule) / PITCH + .5) * PITCH - PITCH / 2
        return f'<rect x="{a}" y="{cc}" width="{b - a}" height="{d - cc}" fill="{c["ground"]}"/>'
    wm_w = B.advance(B.load(bold), wm, wm_size, wm_track)
    o.append(keep_out(MARGIN, wm_base - wm_size * 0.72, MARGIN + wm_w, wm_base))
    o.append(keep_out(MARGIN, name_base - name_size * 0.72, MARGIN + B.advance(B.load(name_font), first, name_size), name_base + name_size * 0.2))
    o.append(keep_out(MARGIN, tag_base - 13, MARGIN + B.advance(mono, tag, 16, 0.14), tag_base + 3))
    term_w = max(B.advance(mono, ("> " if k == "cmd" else "") + t_, tsize) for k, t_ in lines)
    o.append(keep_out(MARGIN, term_base - 16, MARGIN + term_w, last_base + 4))
    o.append("</g>")
    o.append(f'<path d="{frame}" fill="none" stroke="{c["line-strong"]}" stroke-width="1"/>')

    # header / footer rows
    if signal:
        o.append(f'<line x1="{MARGIN}" y1="{top_rule + .5}" x2="{W - MARGIN}" y2="{top_rule + .5}" stroke="{c["line"]}" stroke-width="1"/>')
    else:
        o.append(f'<line x1="{MARGIN}" y1="{top_rule + 1}" x2="{W - MARGIN}" y2="{top_rule + 1}" stroke="{c["ink"]}" stroke-width="2"/>')
    o.append(f'<line x1="{MARGIN}" y1="{bot_rule + .5}" x2="{W - MARGIN}" y2="{bot_rule + .5}" stroke="{c["line"]}" stroke-width="1"/>')
    o.append(B.T(MONO, "00 / PROFILE", 16, MARGIN, 52, "ink", 0.14, wght=500))
    o.append(B.T(MONO, cfg["header_right"].upper(), 16, W - MARGIN, 52, "mu", 0.14, anchor="end", wght=500))
    x = MARGIN
    for i, (k, v) in enumerate(cfg["footer"]):
        for s_, cl in (((" | " if i else "") + k + " ", "mu"), (v, "ink")):
            o.append(B.T(MONO, s_, 16, x, H - MARGIN, cl, 0.14, wght=500))
            x += B.advance(mono, s_, 16, 0.14)

    # wordmark in four bands, then whole
    t0 = 120
    for i in range(4):
        o.append(f'<g class="s" {B.delay(t0 + i * STEP)} clip-path="url(#b{i})"><use href="#wm"/></g>')
    o.append(f'<use class="s" {B.delay(t0 + 4 * STEP)} href="#wm"/>')
    # first name typed, then the role lands as a tag, apart
    nf = B.load(name_font)
    t = t0 + 6 * STEP
    rx = MARGIN
    for chx in first:
        if chx != " ":
            o.append(B.T(name_font, chx, name_size, rx, name_base, "ink s", attrs=B.delay(t)))
        rx += B.advance(nf, chx, name_size)
        t += CHAR
    t += 2 * STEP
    o.append(B.T(MONO, tag, 16, MARGIN, tag_base, "ink s", 0.14, attrs=B.delay(t), wght=500))

    # terminal: principles
    y = term_base
    t += 3 * STEP
    px = B.advance(mono, "> ", tsize)
    for kind, text in lines:
        if kind == "cmd":
            o.append(B.T(MONO, ">", tsize, MARGIN, y, "mu s", attrs=B.delay(t), wght=500))
            xx = MARGIN + px
            for chx in text:
                if chx != " ":
                    o.append(B.T(MONO, chx, tsize, xx, y, "ink s", attrs=B.delay(t + 2 * STEP), wght=500))
                xx += B.advance(mono, chx, tsize)
                t += CHAR
            t += 3 * STEP
        else:
            o.append(B.T(MONO, text, tsize, MARGIN, y, "ink s", attrs=B.delay(t), wght=400))
            t += STEP
        y += lh
    o.append(B.T(MONO, ">", tsize, MARGIN, y, "mu s", attrs=B.delay(t), wght=500))
    o.append(f'<g class="s" {B.delay(t)}>' + B.T(MONO, "_", tsize, MARGIN + px, y, "ink blink", wght=500) + "</g>")

    # object ──────────────────────────────────────────────────────────────
    R = 168
    cx = MARGIN + 7 * (col + GUTTER) + (5 * col + 4 * GUTTER) / 2 + 10
    cy = (top_rule + bot_rule) / 2 + 6
    cx = MARGIN + round((cx - MARGIN) / PITCH) * PITCH        # the object sits on a lattice point
    cy = top_rule + round((cy - top_rule) / PITCH) * PITCH
    P, dots, hidden, ascii_at = build_object(R, theme, cfg.get("seed", 7))
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    l, r_, tp, bt = cx + min(xs), cx + max(xs), cy + min(ys), cy + max(ys)

    def ln(x1, y1, x2, y2, colr, cls=True, d=0, dash=None):
        a = f' class="d" pathLength="1" {B.delay(d)}' if cls else ""
        a += f' stroke-dasharray="{dash}"' if dash else ""
        return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{colr}" stroke-width="1"{a}/>'
    # Construct
    for yy in (tp + .5, bt - .5):
        o.append(ln(l - EXT, yy, r_ + EXT, yy, c["line"]))
    for xx in (l + .5, r_ - .5):
        o.append(ln(xx, tp - EXT + 8, xx, bt + EXT - 8, c["line"]))
    after = 6 * STEP
    o.append(f'<g class="s" {B.delay(after)}>' + ln(l - 12, cy, r_ + 12, cy, c["line-strong"], False, dash="6 4")
             + ln(cx, tp - 12, cx, bt + 12, c["line-strong"], False, dash="6 4") + "</g>")
    dy = tp - 22
    label = cfg["object_label"]
    lw = B.advance(mono, label, 16, 0.14) + 16
    o.append(f'<g class="s" {B.delay(after)}>' + ln(l, dy, r_, dy, c["line-strong"], False)
             + ln(l + .5, dy - 5, l + .5, dy + 5, c["line-strong"], False)
             + ln(r_ - .5, dy - 5, r_ - .5, dy + 5, c["line-strong"], False)
             + f'<rect x="{(l + r_) / 2 - lw / 2:.1f}" y="{dy - 9:.1f}" width="{lw:.1f}" height="18" fill="{c["ground"]}"/>'
             + B.T(MONO, label, 16, (l + r_) / 2, dy + 5, "ink", 0.14, anchor="middle", wght=500) + "</g>")
    o.append(f'<g class="s" {B.delay(after)}>' + "".join(
        f'<path d="M{a - 7:.1f} {b:.1f}H{a + 7:.1f}M{a:.1f} {b - 7:.1f}V{b + 7:.1f}" stroke="{c["ink"]}" stroke-width="1"/>'
        for a, b in ((l, tp), (r_, tp), (l, bt), (r_, bt))) + "</g>")
    # hidden edges, barely: dashed line-strong
    o.append(f'<g class="s" {B.delay(after)} transform="translate({cx:.1f} {cy:.1f})">' + "".join(
        f'<line x1="{P[i][0]:.1f}" y1="{P[i][1]:.1f}" x2="{P[j][0]:.1f}" y2="{P[j][1]:.1f}" stroke="{c["line-strong"]}" stroke-width="1" stroke-dasharray="2 5"/>'
        for i, j in hidden) + "</g>")
    # stipple plate, eight batches behind a soft front from the light
    rng = random.Random(3)
    batches = [[] for _ in range(8)]
    for x_, y_, s in dots:
        k = ((x_ + y_) / (2 * R) + 1) / 2 + rng.gauss(0, 0.1)
        batches[max(0, min(7, int(k * 8)))].append(f'<circle cx="{x_:.1f}" cy="{y_:.1f}" r="{s:.2f}"/>')
    for i, g in enumerate(batches):
        o.append(f'<g class="s" {B.delay(after + i * STEP)} fill="{c["ink"]}" transform="translate({cx:.1f} {cy:.1f})">{"".join(g)}</g>')

    # Lens: a square that wanders on a stepped path and reads the plate as ASCII
    lc, lr = 13, 8
    lwid, lhei = lc * cw, lr * chh
    gx0, gy0 = l, tp                       # ASCII grid anchored on the object box
    t_lens = after + 8 * STEP + 6 * STEP
    for k in range(lens_n):
        a = 2 * math.pi * k / lens_n
        ux = cx + 0.30 * (r_ - l) * math.sin(a) - lwid / 2
        uy = cy + 0.26 * (bt - tp) * math.sin(2 * a) - lhei / 2
        ci = round((ux - gx0) / cw); ri = round((uy - gy0) / chh)
        X0, Y0 = gx0 + ci * cw, gy0 + ri * chh
        g = [f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{lwid:.1f}" height="{lhei:.1f}" fill="{c["ground"]}"/>']
        for rr in range(lr):
            for cc in range(lc):
                gxx, gyy = X0 + (cc + .5) * cw, Y0 + (rr + .5) * chh
                chx = ascii_at(gxx - cx, gyy - cy, cw)
                if chx != " ":
                    g.append(f'<use href="#{gid[chx]}" x="{X0 + cc * cw:.1f}" y="{Y0 + rr * chh + chh - 4:.1f}"/>')
        g.append(f'<rect x="{X0 + .5:.1f}" y="{Y0 + .5:.1f}" width="{lwid - 1:.1f}" height="{lhei - 1:.1f}" fill="none" stroke="{c["ink"]}" stroke-width="1"/>')
        for (qx, qy) in ((X0, Y0), (X0 + lwid, Y0), (X0, Y0 + lhei), (X0 + lwid, Y0 + lhei)):
            g.append(f'<rect x="{qx - 2.5:.1f}" y="{qy - 2.5:.1f}" width="5" height="5" fill="{c["ink"]}"/>')
        chip = f"ASCII X {(X0 + lwid / 2 - l) / (r_ - l):.2f} Y {(Y0 + lhei / 2 - tp) / (bt - tp):.2f}"
        cwid = B.advance(mono, chip, 13, 0.1) + 12
        cyy = Y0 - 20 if Y0 - 20 > dy + 14 else Y0 + lhei + 2
        g.append(f'<rect x="{X0:.1f}" y="{cyy:.1f}" width="{cwid:.1f}" height="18" fill="{c["ink"]}"/>')
        g.append(B.T(MONO, chip, 13, X0 + 6, cyy + 14, "gr", 0.1, wght=500))
        rest = " rest" if k == 0 else ""
        o.append(f'<g class="ink lens{rest}" style="animation-duration:{int(cyc)}ms;animation-delay:{int(t_lens + k * lens_hold)}ms">{"".join(g)}</g>')

    o.append("</svg>")
    return B.finish(o)

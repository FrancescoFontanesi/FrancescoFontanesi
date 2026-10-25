#!/usr/bin/env python3
"""The profile panel: one poster, fluid motion.

Left : FRANCESCO / FONTANESI, then a terminal that runs `cat info.txt`
       (role + notes). Text is revealed by a continuous wipe with a riding caret.
Right: an icosahedron as a cloud of gaussian points spinning in 3D, continuously;
       an ASCII ring (a luminance ramp with NIHILISM set into it) turns around it,
       a tick ring counter-turns, the construct stays still.
Ground: square lattice of hairline dots and thin crosses.

Motion note: this panel deliberately leaves the system's stepped-motion law for
smooth CSS transforms (no opacity animation). Everything else is Cyber Nihilism.
"""
import math, random
from fontTools.pens.boundsPen import BoundsPen
import build as B
from sheet import Doc, PITCH, CW, CH, GS, BOLD, LIGHT, MONO, RAMP

EASE_SINE = "cubic-bezier(.37,0,.63,1)"     # ≈ −cos: alternate halves make a sinusoid
EASE_OUT = "cubic-bezier(.16,1,.3,1)"

# ── 3D point cloud of the icosahedron ───────────────────────────────────
def ico_cloud(seed, tilt_x=0.42, tilt_z=0.21):
    rng = random.Random(seed)
    p = (1 + 5 ** .5) / 2
    V = [(-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0), (0, -1, p), (0, 1, p),
         (0, -1, -p), (0, 1, -p), (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1)]
    n = math.sqrt(1 + p * p)
    def rot(v):
        x, y, z = (c / n for c in v)
        y, z = y * math.cos(tilt_x) - z * math.sin(tilt_x), y * math.sin(tilt_x) + z * math.cos(tilt_x)
        x, y = x * math.cos(tilt_z) - y * math.sin(tilt_z), x * math.sin(tilt_z) + y * math.cos(tilt_z)
        return (x, y, z)
    V = [rot(v) for v in V]
    d2 = lambda a, b: sum((a[i] - b[i]) ** 2 for i in range(3))
    e2 = min(d2(V[0], V[j]) for j in range(1, 12))
    adj = lambda i, j: abs(d2(V[i], V[j]) - e2) < 1e-6
    E = [(i, j) for i in range(12) for j in range(i + 1, 12) if adj(i, j)]
    F = [(i, j, k) for i, j in E for k in range(j + 1, 12) if adj(i, k) and adj(j, k)]
    pts = []
    def jit(s):
        return [rng.gauss(0, s) for _ in range(3)]
    for f in F:                                   # faces: sparse
        a, b, c = (V[i] for i in f)
        for _ in range(12):
            r1, r2 = rng.random(), rng.random()
            if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
            q = [a[t] + r1 * (b[t] - a[t]) + r2 * (c[t] - a[t]) for t in range(3)]
            pts.append((q, max(.45, min(1.1, .7 + rng.gauss(0, .15)))))
    for i, j in E:                                # edges: gaussian bands (σ ≈ 0.012 of the radius)
        a, b = V[i], V[j]
        for _ in range(42):
            u = rng.random(); o = jit(.009)
            pts.append(([a[t] + u * (b[t] - a[t]) + o[t] for t in range(3)], max(.9, min(1.9, 1.3 + rng.gauss(0, .22)))))
    for v in V:                                   # vertices: clusters (σ ≈ 0.03)
        for _ in range(16):
            o = jit(.028)
            pts.append(([v[t] + o[t] for t in range(3)], max(.9, min(2.1, 1.4 + rng.gauss(0, .25)))))
    return pts

def poster(theme):
    cfg = B.CFG
    W, H = 1200, 600
    title = (f"{cfg['first_name']} {cfg['wordmark'].title()}. {cfg['role'].capitalize()}. "
             + " ".join(t.capitalize() for k, t in cfg["terminal"]["lines"][2:] if k == "out"))
    d = Doc(W, H, theme, title)
    c, signal = d.c, d.signal
    M = B.MARGIN

    # ── layout ───────────────────────────────────────────────────────────
    first = cfg["first_name"] if signal else cfg["first_name"].upper()
    last = cfg["wordmark"].upper()
    first_font = LIGHT if signal else BOLD
    left_w = 560
    last_size = left_w / B.advance(B.load(BOLD), last, 1, -0.04)
    first_size = 84 if signal else 64
    first_base = 64 + first_size * 0.72
    last_base = first_base + 16 + last_size * 0.70
    tsize, lh = 28, 46
    cursor_top, cursor_height, cursor_width = tsize * .85, tsize * 1.1, tsize * .5
    notes = [t for k, t in cfg["terminal"]["lines"][2:] if k == "out"]
    rows = [("notes" if i == 0 else "", t) for i, t in enumerate(notes)]
    key_w = d.adv("notes   ", tsize, 0)

    R = 172
    cx = W - M - R - 82
    cy = H / 2
    cx = M + round((cx - M) / PITCH) * PITCH
    cy = 72 + round((cy - 72) / PITCH) * PITCH
    ring_r, tick_r = R + 42, R + 66
    term0 = cy + tick_r - (cursor_height - cursor_top) - (len(rows) + 1) * lh

    def vertical_bounds(font, text, size):
        glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
        pen = BoundsPen(glyphs)
        for char in text:
            glyphs[cmap[ord(char)]].draw(pen)
        scale = size / font["head"].unitsPerEm
        return pen.bounds[1] * scale, pen.bounds[3] * scale

    role_font, role_size = first_font, 48
    role_text = f"[ {cfg['role'].upper()}]"
    _, command_top = vertical_bounds(d.mono, "cat info.txt", tsize)
    last_bottom, _ = vertical_bounds(B.load(BOLD), last, last_size)
    role_bottom, role_top = vertical_bounds(B.load(role_font), role_text, role_size)
    title_bottom = last_base - last_bottom
    free_space = term0 - command_top - title_bottom - (role_top - role_bottom)
    # Leave twice as much space below the subtitle as above it.
    role_base = title_bottom + free_space / 3 + role_top

    # ── lattice, with keep-outs for text ─────────────────────────────────
    keep = d.lattice(M - PITCH / 2, 40 + PITCH / 2, W - M + PITCH / 2, H - 40, M, 72)
    fw = B.advance(B.load(first_font), first, first_size)
    keep(M, first_base - first_size * 0.72, M + fw, first_base + first_size * 0.2)
    keep(M, last_base - last_size * 0.72, M + left_w, last_base)
    # Reveal text through a growing clip so the lattice remains visible underneath.
    d.css += (f".wipe{{transform-box:fill-box;transform-origin:0% 50%;animation:wipe linear both}}"
              f"@keyframes wipe{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}"
              f".ride{{visibility:hidden;animation:ride linear forwards}}"
              f"@keyframes ride{{0%,99.9%{{visibility:visible}}0%{{transform:translateX(0)}}100%{{visibility:hidden;transform:translateX(var(--w))}}}}"
              f"@media (prefers-reduced-motion:reduce){{.wipe,.ride{{animation:none}}.wipe{{transform:none}}}}")

    def wipe(x, y_top, w, h, t0, dur, caret_w=3, text_count=1):
        clip_id = f"wipe{len(d.defs)}"
        d.defs.append(f'<clipPath id="{clip_id}"><rect class="wipe" style="animation-duration:{int(dur)}ms;animation-delay:{int(t0)}ms" x="{x - 2:.1f}" y="{y_top:.1f}" width="{w + 4:.1f}" height="{h:.1f}"/></clipPath>')
        text = "".join(d.o[-text_count:])
        del d.o[-text_count:]
        d.o.append(f'<g clip-path="url(#{clip_id})">{text}</g>')
        d.o.append(f'<rect class="ride" style="--w:{w:.1f}px;animation-duration:{int(dur)}ms;animation-delay:{int(t0)}ms" x="{x:.1f}" y="{y_top:.1f}" width="{caret_w}" height="{h:.1f}" fill="{c["ink"]}"/>')
        return t0 + dur

    # name
    d.o.append(B.T(first_font, first, first_size, M, first_base, "ink"))
    t = wipe(M, first_base - first_size * 0.76, fw, first_size * 0.98, 200, 520)
    d.o.append(B.T(BOLD, last, last_size, M - 4, last_base, "ink", -0.04))
    t = wipe(M - 4, last_base - last_size * 0.74, left_w + 6, last_size * 0.78, t - 160, 760, caret_w=4)

    d.o.append(B.T(role_font, role_text, role_size, M, role_base, "ink"))
    role_w = B.advance(B.load(role_font), role_text, role_size)
    t = wipe(M, role_base - role_top - 1, role_w, role_top - role_bottom + 2,
             t + 2 * B.STEP, 520)

    # terminal: > cat info.txt
    y = term0
    px = d.adv("> ", tsize, 0)
    t += 280
    cmd = "cat info.txt"
    d.o.append(d.mono_t(">", M, y, "mu s", tsize, 0, attrs=B.delay(t)))      # prompt appears, then the command types
    d.o.append(d.mono_t(cmd, M + px, y, "ink", tsize, 0))
    t = wipe(M + px, y - cursor_top, d.adv(cmd, tsize, 0), cursor_height,
             t + 200, len(cmd) * B.CHAR * 1.6, caret_w=cursor_width) + 220
    for k, v in rows:
        y += lh
        if k:
            d.o.append(d.mono_t(k, M, y, "mu", tsize, 0))
        d.o.append(d.mono_t(v, M + key_w, y, "ink", tsize, 0, wght=400))
        w = key_w + d.adv(v, tsize, 0)
        t = wipe(M, y - cursor_top, w, cursor_height, t, w * 1.25,
                 caret_w=cursor_width, text_count=2 if k else 1) + 120
    y += lh
    d.o.append(d.mono_t(">", M, y, "mu s", tsize, 0, attrs=B.delay(t)))
    d.o.append(f'<g class="s" {B.delay(t)}><rect class="blink" x="{M + px:.1f}" y="{y - cursor_top:.1f}" width="{cursor_width:.1f}" height="{cursor_height:.1f}" fill="{c["ink"]}"/></g>')

    # ── object ───────────────────────────────────────────────────────────
    spin = cfg.get("spin_ms", 14000)
    d.css += (f".q{{animation:qx {spin // 2}ms {EASE_SINE} infinite alternate both}}"
              f".q>circle{{transform-box:fill-box;transform-origin:center;animation:qz {spin // 2}ms {EASE_SINE} infinite alternate both}}"
              "@keyframes qx{from{transform:translateX(calc((var(--a) * -1 - var(--b)) * 1px))}to{transform:translateX(calc((var(--a) - var(--b)) * 1px))}}"
              "@keyframes qz{from{transform:scale(var(--s))}to{transform:scale(1)}}"
              f".grow{{transform-origin:{cx}px {cy}px;animation:grow 1100ms {EASE_OUT} 150ms both}}"
              "@keyframes grow{from{transform:scale(.0)}to{transform:scale(1)}}"
              f".cw{{transform-origin:{cx}px {cy}px;animation:turn 90s linear infinite}}"
              f".ccw{{transform-origin:{cx}px {cy}px;animation:turn 140s linear infinite reverse}}"
              "@keyframes turn{to{transform:rotate(360deg)}}"
              ".draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1200ms " + EASE_OUT + " both}"
              "@keyframes draw{to{stroke-dashoffset:0}}"
              "@media (prefers-reduced-motion:reduce){.q,.q>circle,.grow,.cw,.ccw,.draw{animation:none}.draw{stroke-dashoffset:0}}")

    # construct: still
    ln = lambda *a, **k: d.line(*a, **k)
    d.o.append(f'<g>{ln(cx - tick_r - 18, cy, cx + tick_r + 18, cy, c["line-strong"], dash="6 4")}'
               f'{ln(cx, cy - tick_r - 18, cx, cy + tick_r + 18, c["line-strong"], dash="6 4")}</g>')
    for (a, b) in ((cx - tick_r, cy - tick_r), (cx + tick_r, cy - tick_r),
                   (cx - tick_r, cy + tick_r), (cx + tick_r, cy + tick_r)):
        d.o.append(f'<path d="M{a - 7} {b}H{a + 7}M{a} {b - 7}V{b + 7}" stroke="{c["ink"]}" stroke-width="1"/>')
    d.o.append(f'<circle class="draw" pathLength="1" style="animation-delay:100ms" cx="{cx}" cy="{cy}" r="{R + 8}" fill="none" stroke="{c["line"]}" stroke-width="1"/>')
    d.o.append(f'<circle class="draw" pathLength="1" style="animation-delay:250ms" cx="{cx}" cy="{cy}" r="{tick_r}" fill="none" stroke="{c["line-strong"]}" stroke-width="1"/>')

    # tick ring: counter-turning
    ticks = []
    for i in range(72):
        a = math.radians(i * 5)
        L = 12 if i % 6 == 0 else 5
        x1, y1 = cx + tick_r * math.sin(a), cy - tick_r * math.cos(a)
        x2, y2 = cx + (tick_r - L) * math.sin(a), cy - (tick_r - L) * math.cos(a)
        ticks.append(f"M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}")
    d.o.append(f'<g class="ccw"><path d="{"".join(ticks)}" stroke="{c["line-strong"]}" stroke-width="1" fill="none"/></g>')
    # index mark at the top, still
    d.o.append(f'<path d="M{cx - 6} {cy - tick_r - 14}L{cx + 6} {cy - tick_r - 14}L{cx} {cy - tick_r - 4}Z" fill="{c["ink"]}"/>')

    # ASCII ring: a luminance ramp around the circle, NIHILISM set into it, turning
    mono = d.mono
    label = cfg["object_label"].upper()
    chars = set(RAMP[1:]) | set(label)
    gid = {}
    for i, chx in enumerate(sorted(chars)):
        gid[chx] = f"r{i}"
        d.defs.append(f'<path id="r{i}" d="{B.outline(mono, chx, 15, 0, 0)}"/>')
    step_deg = 360 / int(2 * math.pi * ring_r / 11.5)
    n = int(round(360 / step_deg))
    lab_slots = set(range(len(label)))
    uses = []
    for i in range(n):
        a = i * step_deg
        if i in lab_slots:
            chx = label[i]
        elif len(label) <= i < len(label) + 2:
            continue
        elif i >= n - 2:
            continue
        else:
            lum = 0.5 + 0.5 * math.cos(math.radians(a * 2 - 40))
            chx = RAMP[1 + int(lum * 12.99)]
        uses.append(f'<use href="#{gid[chx]}" transform="rotate({a:.2f} {cx} {cy}) translate({cx - 4.5:.1f} {cy - ring_r + 5:.1f})"/>')
    d.o.append(f'<g class="cw"><g class="ink">{"".join(uses)}</g></g>')

    # the cloud: every point turns on its own horizontal circle (x and depth as sinusoids)
    pts = ico_cloud(cfg.get("seed", 7))
    T = spin
    g = []
    for (x, y, z), r0 in pts:
        rho = math.hypot(x, z)
        th = math.atan2(z, x)
        tau = ((math.pi - th) / (2 * math.pi)) % 1 * T
        u = (tau + T / 4) % T
        a = rho * R
        b = rho * R * math.cos(th)
        f_back, f_front = 0.55 - 0.45 * rho, 0.55 + 0.45 * rho
        s = f_back / f_front
        rr = r0 * f_front * 1.25
        g.append(f'<g class="q" style="--a:{a:.1f};--b:{b:.1f};animation-delay:-{tau / 1000:.3f}s">'
                 f'<circle cx="{cx + b:.1f}" cy="{cy - y * R:.1f}" r="{rr:.2f}" style="--s:{s:.2f};animation-delay:-{u / 1000:.3f}s"/></g>')
    d.o.append(f'<g class="grow" fill="{c["ink"]}">{"".join(g)}</g>')

    return d.render()

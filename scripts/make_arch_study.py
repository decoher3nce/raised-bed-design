#!/usr/bin/env python3
"""Arch study for the Raised Bed Design hog-wire panel.

Reads data/model_extract.json (bed walls, posts, panel) and computes how high a
16 ft panel arches for a given foot spacing under three foot conditions:

  free feet        the panel ends are simply held d apart and can tilt (pinned
                   elastica: zero bending moment at the feet)
  feet held upright the panel ends are clamped vertical where they enter the
                   soil (clamped elastica; the sides bow out below the crown)
  legs on posts    straight legs held by posts with a semicircle above (the
                   2026-11-06 trellis-post design)

plus the catenary from a sketch the owner found, for reference.  A bent cattle
panel is an elastic rod, so its shape is an elastica (pendulum equation
theta'' = -lambda sin theta), integrated here with RK4 and a shooting method;
the pinned case is cross-checked against the closed form with complete
elliptic integrals.

Writes arch-study.html (the study page) and data/arch_study.json (numbers).
"""
import datetime
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACT = os.path.join(ROOT, 'data', 'model_extract.json')
OUT_HTML = os.path.join(ROOT, 'arch-study.html')
OUT_JSON = os.path.join(ROOT, 'data', 'arch_study.json')

ext = json.load(open(EXTRACT))
P = ext['params']
L = P['Hogwire_length']['value_in']                      # 192 in panel
WALL_H = P['Courses']['value_in'] * P['Board_Width']['value_in']   # 14.5 in
EMBED = 9.5                                              # post depth below grade (from the stakes)
PT, PW = 1.5, 3.5                                        # 2x4 actual
STICK8, STICK10 = 96.0, 120.0
TODAY = datetime.date.today().isoformat()

# ---------------------------------------------------------------- model geometry
def comp_bodies(prefix):
    return [b for b in ext['bodies'] if b['component'].startswith(prefix)]

def bed_x(prefix):
    bs = comp_bodies(prefix)
    return min(b['min'][0] for b in bs), max(b['max'][0] for b in bs)

AX0, AX1 = bed_x('Bed A')
BX0, BX1 = bed_x('Bed B')
XA, XB = (AX0 + AX1) / 2, (BX0 + BX1) / 2       # bed centrelines (the new feet)
XC = (XA + XB) / 2                               # arch centre = walkway centre
D = XB - XA                                      # end-point separation, 75 in
WALK0, WALK1 = AX1, BX0                          # walkway between the inside walls

def near_end_post(prefix, side):
    posts = [b for b in comp_bodies(prefix) if 'post' in b['body']]
    ymax = max(b['max'][1] for b in posts)
    near = [b for b in posts if abs(b['max'][1] - ymax) < 0.01]
    return max(near, key=lambda b: b['max'][0]) if side == 'E' else min(near, key=lambda b: b['min'][0])

PA = near_end_post('Bed A', 'E')   # bed A's inside (east) corner post at the near end
PB = near_end_post('Bed B', 'W')   # bed B's inside (west) corner post at the near end
POST_OFF = (XC - (PA['min'][0] + PA['max'][0]) / 2)      # post centreline offset from the arch centre
POST_IN = XC - PA['max'][0]                               # post inner edge offset (= walkway edge)
POST_OUT = XC - PA['min'][0]                              # post outer edge offset
assert abs(POST_OFF - ((PB['min'][0] + PB['max'][0]) / 2 - XC)) < 0.01

arch = [b for b in ext['bodies'] if b['component'] == 'Arch AB']
PANEL_Y1 = max(b['max'][1] for b in arch)       # -3.0  first wire against the post face
PANEL_Y0 = min(b['min'][1] for b in arch)       # -63.5 far edge
PANEL_W = PANEL_Y1 - PANEL_Y0
N_WIRES = len(arch)
OLD_X0 = min(b['min'][0] for b in arch)
OLD_X1 = max(b['max'][0] for b in arch)
OLD_CROWN = max(b['max'][2] for b in arch)

def inside_mid_post(prefix, side):
    posts = [b for b in comp_bodies(prefix) if 'post' in b['body'] and b['min'][2] < 0]
    edge = AX1 if side == 'E' else BX0
    wall = [b for b in posts if abs((b['max'][0] if side == 'E' else b['min'][0]) - (edge - PT if side == 'E' else edge + PT)) < 0.01]
    wall = [b for b in wall if b['max'][1] <= PANEL_Y1 + 0.01 and b['min'][1] >= PANEL_Y0 - 0.01]
    return max(wall, key=lambda b: b['max'][1]) if wall else None

MA = inside_mid_post('Bed A', 'E')
MB = inside_mid_post('Bed B', 'W')

# ---------------------------------------------------------------- elastica physics
def KE(k):
    """Complete elliptic integrals K(k), E(k) by the arithmetic-geometric mean."""
    a, b, c = 1.0, math.sqrt(1.0 - k * k), k
    s, pw = k * k / 2.0, 0.5
    while c > 1e-15:
        a, b, c = (a + b) / 2.0, math.sqrt(a * b), (a - b) / 2.0
        pw *= 2.0
        s += pw * c * c
    K = math.pi / (2.0 * a)
    return K, K * (1.0 - s)

def pinned_closed(d):
    """Pinned elastica of length L with chord d: (peak height, end angle from the chord in degrees)."""
    lo, hi = 1e-9, 1.0 - 1e-12
    for _ in range(200):
        k = (lo + hi) / 2.0
        K, E = KE(k)
        if 2.0 * E / K - 1.0 > d / L:
            lo = k
        else:
            hi = k
    K, E = KE(k)
    return k * L / K, 2.0 * math.degrees(math.asin(k))

def shoot(lam, mode):
    """Integrate the elastica from the crown (theta=0, curvature 1) toward one foot.

    theta is the tangent angle from the chord, s the arc length, both in the
    scaled units where the crown curvature is 1 and theta'' = -lam sin theta.
    Returns (s_f, x_f, y_f, theta_f, points) at the foot event:
      pinned  first point of zero curvature (theta' = 0)
      vert1   first crossing of theta = -90 deg
      vert2   second crossing of theta = -90 deg (the sides bow out first)
    """
    ds = 0.004 / math.sqrt(1.0 + 2.0 * abs(lam))
    th, om, x, y, s = 0.0, -1.0, 0.0, 0.0, 0.0
    pts = [(0.0, 0.0)]
    crossings = 0
    half = -math.pi / 2.0
    steps = 0
    while steps < 400000:
        steps += 1
        k1 = (om, -lam * math.sin(th), math.cos(th), math.sin(th))
        t2, o2 = th + ds / 2 * k1[0], om + ds / 2 * k1[1]
        k2 = (o2, -lam * math.sin(t2), math.cos(t2), math.sin(t2))
        t3, o3 = th + ds / 2 * k2[0], om + ds / 2 * k2[1]
        k3 = (o3, -lam * math.sin(t3), math.cos(t3), math.sin(t3))
        t4, o4 = th + ds * k3[0], om + ds * k3[1]
        k4 = (o4, -lam * math.sin(t4), math.cos(t4), math.sin(t4))
        nth = th + ds / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        nom = om + ds / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        nx = x + ds / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        ny = y + ds / 6 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
        frac = None
        if mode == 'pinned':
            if om < 0.0 <= nom:
                frac = om / (om - nom)
        else:
            if th > half >= nth:
                crossings += 1
                if mode == 'vert1':
                    frac = (th - half) / (th - nth)
            elif th < half <= nth:
                crossings += 1
                if mode == 'vert2':
                    frac = (half - th) / (nth - th)
        if frac is not None:
            sf = s + frac * ds
            xf = x + frac * (nx - x)
            yf = y + frac * (ny - y)
            tf = th + frac * (nth - th)
            pts.append((xf, yf))
            return sf, xf, yf, tf, pts
        th, om, x, y, s = nth, nom, nx, ny, s + ds
        if steps % 8 == 0:
            pts.append((x, y))
        if th < -math.pi or th > 0.5:
            break
    return None

def ratio(lam, mode):
    r = shoot(lam, mode)
    if r is None:
        return None
    return r[1] / r[0]

R90 = 2.0 * KE(math.sqrt(0.5))[1] / KE(math.sqrt(0.5))[0] - 1.0   # chord/length of the pinned 90-degree shape, 0.457
R_CIRCLE = 2.0 / math.pi                                           # semicircle, 0.637

def solve_profile(d, family):
    """Elastica of length L and chord d.  family: 'pinned' or 'vert'.

    Returns dict with the peak height above the feet, the half profile
    [(x, y)] in inches from the crown (y <= 0), the end angle (degrees from the
    chord), the widest half-width and the branch used.
    """
    target = d / L
    if family == 'pinned':
        mode, lo, hi, increasing = 'pinned', 0.2500001, 400.0, True
    elif target > R_CIRCLE:
        mode, lo, hi, increasing = 'vert1', -1.0e9, -1e-9, False       # tension: ratio falls as lam rises toward 0
    elif target > R90:
        mode, lo, hi, increasing = 'vert1', 1e-9, 0.5, False           # compression, no bulge
    else:
        mode, lo, hi, increasing = 'vert2', 0.2500001, 0.4999, True    # compression, sides bow out
    logspace = family != 'pinned' and target > R_CIRCLE
    def f(lam):
        return ratio(lam, mode)
    for _ in range(60):
        if logspace:
            mid = -math.sqrt(lo * hi)           # geometric mean of two negatives
        else:
            mid = (lo + hi) / 2.0
        val = f(mid)
        if val is None:
            # no event: treat as beyond the bracket on the far side
            val = -9.0 if increasing else 9.0
        if (val < target) == increasing:
            lo = mid
        else:
            hi = mid
    lam = mid
    sf, xf, yf, tf, pts = shoot(lam, mode)
    scale = (L / 2.0) / sf
    prof = [(px * scale, py * scale) for px, py in pts]
    return {'family': family, 'branch': mode, 'lam': lam, 'h': -yf * scale,
            'end_angle': math.degrees(tf), 'half_width': max(px for px, _ in prof),
            'crown_radius': scale, 'profile': prof, 'chord': d}

def height_at(prof_half, h, off):
    """Height above the feet of the half profile at horizontal offset off from the crown (first pass only)."""
    last = prof_half[0]
    for px, py in prof_half[1:]:
        if last[0] <= off <= px or px <= off <= last[0]:
            if px == last[0]:
                return h + py
            t = (off - last[0]) / (px - last[0])
            return h + last[1] + t * (py - last[1])
        last = (px, py)
    return None

def slope_at(prof_half, off):
    last = prof_half[0]
    for px, py in prof_half[1:]:
        if last[0] <= off <= px:
            return math.degrees(math.atan2(-(py - last[1]), px - last[0]))
        last = (px, py)
    return None

def posts_height(d):
    """Legs held straight by posts with a semicircle above (previous design); None past the semicircle limit."""
    if d > L * R_CIRCLE:
        return None
    return L / 2.0 - d * (math.pi / 4.0 - 0.5)

def catenary_height(d):
    lo, hi = 1e-3, 1e5
    for _ in range(200):
        a = (lo + hi) / 2.0
        if 2.0 * a * math.sinh(d / (2.0 * a)) > L:
            lo = a
        else:
            hi = a
    return a * (math.cosh(d / (2.0 * a)) - 1.0)

# ---------------------------------------------------------------- the curves
SPANS = list(range(24, 181, 6))
curves = {'free': [], 'vert': [], 'posts': [], 'cat': []}
for d in SPANS:
    hp, _ = pinned_closed(d)
    curves['free'].append(hp)
    curves['vert'].append(solve_profile(d, 'vert')['h'])
    curves['posts'].append(posts_height(d))
    curves['cat'].append(catenary_height(d))

# the plan: feet at the bed centrelines
free = solve_profile(D, 'pinned')
vert = solve_profile(D, 'vert')
hp_closed, ang_closed = pinned_closed(D)
print(f'pinned check: ODE h={free["h"]:.2f} angle={free["end_angle"]:.2f}  closed h={hp_closed:.2f} angle={-ang_closed:.2f}')
assert abs(free['h'] - hp_closed) < 0.05, 'pinned ODE and closed form disagree'

def plan_numbers(sol, feet_z):
    h = sol['h']
    prof = sol['profile']
    at_post = height_at(prof, h, POST_OFF)
    at_post_out = height_at(prof, h, POST_OUT)
    at_walk = height_at(prof, h, POST_IN)
    slope = slope_at(prof, POST_OFF)
    top_needed = at_post_out + 4.0                   # wire on the post face plus 4 in for the screws
    post_len = top_needed + feet_z + EMBED
    stick = 8 if post_len <= STICK8 else 10
    return {
        'feet_z': feet_z, 'crown_feet': h, 'crown_grade': h + feet_z,
        'at_post': at_post + feet_z, 'at_post_out': at_post_out + feet_z, 'at_walk': at_walk + feet_z,
        'slope_at_post': slope, 'post_top': top_needed + feet_z, 'post_len': post_len + 0.0, 'stick': stick,
        'widest': 2 * sol['half_width'], 'bulge': sol['half_width'] - D / 2,
        'end_lean': abs(sol['end_angle']) - 90.0, 'crown_radius': sol['crown_radius'],
    }

FEET_SURF = WALL_H            # panel feet at the wall-top / soil level
FEET_DOWN = WALL_H - 6.0      # panel feet pushed 6 in into the bed soil
plan = {
    'free_surf': plan_numbers(free, FEET_SURF), 'vert_surf': plan_numbers(vert, FEET_SURF),
    'free_down': plan_numbers(free, FEET_DOWN), 'vert_down': plan_numbers(vert, FEET_DOWN),
}
# the previous design for the table
old_h = posts_height(D)
plan['posts_old'] = {'crown_feet': old_h, 'crown_grade': old_h + WALL_H}

def ftin(v, frac=False):
    if v is None:
        return '–'
    tot = round(v * 2) / 2 if frac else round(v)
    ft, rem = int(tot // 12), tot - 12 * int(tot // 12)
    rem_s = f'{rem:g}'
    if ft == 0:
        return f'{rem_s} in'
    return f'{ft} ft {rem_s} in' if rem else f'{ft} ft'

def fin(v, nd=0):
    return '–' if v is None else (f'{v:.{nd}f} in')

# ---------------------------------------------------------------- SVG helpers
HALO = 'paint-order="stroke" stroke="var(--panel)" stroke-width="4" stroke-linejoin="round"'

def fmt(v):
    return f'{v:.1f}'

# --- chart 1: peak height vs end-point separation ---
CW, CH = 760, 440
PL, PR, PT_, PB_ = 58, 24, 26, 56
X0, X1 = 2.0, 15.0          # ft
Y0, Y1 = 0.0, 8.0           # ft
def cx(ft): return PL + (ft - X0) / (X1 - X0) * (CW - PL - PR)
def cy(ft): return PT_ + (Y1 - ft) / (Y1 - Y0) * (CH - PT_ - PB_)

def path(xs, ys):
    seg, out = [], []
    for x, y in zip(xs, ys):
        if y is None:
            if seg:
                out.append('M' + ' L'.join(seg)); seg = []
            continue
        seg.append(f'{cx(x / 12):.1f} {cy(y / 12):.1f}')
    if seg:
        out.append('M' + ' L'.join(seg))
    return ' '.join(out)

SERIES = [
    ('free', 'Free feet (pinned)', 'ser-free'),
    ('vert', 'Feet held upright in the soil', 'ser-vert'),
    ('posts', 'Legs held straight on posts (previous design)', 'ser-posts'),
    ('cat', 'Catenary from the sketch', 'ser-cat'),
]
c1 = [f'<svg viewBox="0 0 {CW} {CH}" role="img" aria-label="Peak height of a 16 ft panel against the distance between its feet, for free feet, feet held upright, legs on posts and a catenary" xmlns="http://www.w3.org/2000/svg">']
for ft in range(0, 9):
    c1.append(f'<line x1="{cx(X0):.1f}" y1="{cy(ft):.1f}" x2="{cx(X1):.1f}" y2="{cy(ft):.1f}" stroke="var(--line)" stroke-width="1"/>')
    c1.append(f'<text x="{cx(X0)-8:.1f}" y="{cy(ft)+4:.1f}" font-size="11" fill="var(--muted)" text-anchor="end">{ft} ft</text>')
for ft in range(2, 16, 2):
    c1.append(f'<line x1="{cx(ft):.1f}" y1="{cy(Y0):.1f}" x2="{cx(ft):.1f}" y2="{cy(Y0)+5:.1f}" stroke="var(--muted)" stroke-width="1"/>')
    c1.append(f'<text x="{cx(ft):.1f}" y="{cy(Y0)+20:.1f}" font-size="11" fill="var(--muted)" text-anchor="middle">{ft} ft</text>')
c1.append(f'<text x="{(cx(X0)+cx(X1))/2:.1f}" y="{CH-8}" font-size="12" fill="var(--muted)" text-anchor="middle">distance between the panel feet</text>')
c1.append(f'<text transform="translate(14 {(cy(Y0)+cy(Y1))/2:.1f}) rotate(-90)" font-size="12" fill="var(--muted)" text-anchor="middle">peak height above the feet</text>')
# the plan span
c1.append(f'<line x1="{cx(D/12):.1f}" y1="{cy(Y0):.1f}" x2="{cx(D/12):.1f}" y2="{cy(Y1):.1f}" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 4"/>')
c1.append(f'<text x="{cx(D/12)+6:.1f}" y="{cy(Y1)+12:.1f}" font-size="11" fill="var(--muted)">bed centre to bed centre, {D:g} in</text>')
for key, label, cls in SERIES:
    c1.append(f'<path class="{cls}" d="{path(SPANS, curves[key])}" fill="none" stroke-width="2.5" stroke-linejoin="round"/>')
# markers at the plan span
marks = {'free': free['h'], 'vert': vert['h'], 'posts': old_h, 'cat': catenary_height(D)}
order = sorted(marks.items(), key=lambda kv: -kv[1])
used = []
for key, h in order:
    cls = dict((k, c) for k, _, c in SERIES)[key]
    yy = cy(h / 12)
    c1.append(f'<circle cx="{cx(D/12):.1f}" cy="{yy:.1f}" r="5" class="{cls} dot" stroke-width="2" fill="var(--panel)"/>')
    ly = yy
    for u in used:
        if abs(ly - u) < 14:
            ly = u + 14
    used.append(ly)
    c1.append(f'<text x="{cx(D/12)+10:.1f}" y="{ly+4:.1f}" font-size="11.5" fill="var(--ink)" {HALO}>{ftin(h)}</text>')
# direct labels
def dl(key, ft_at, dy_px, anchor='start', label=None):
    i = SPANS.index(int(ft_at * 12))
    h = curves[key][i]
    label = label or dict((k, l) for k, l, _ in SERIES)[key]
    return f'<text x="{cx(ft_at)+(6 if anchor=="start" else -6):.1f}" y="{cy(h/12)+dy_px:.1f}" font-size="11.5" fill="var(--ink)" text-anchor="{anchor}" {HALO}>{label}</text>'
c1.append(dl('free', 15.0, -8, 'end'))
c1.append(dl('vert', 15.0, 16, 'end'))
c1.append(dl('posts', 10.0, 16, 'end', 'Legs held straight on posts'))
c1.append(dl('cat', 3.0, -12, 'start'))
c1.append(f'<line id="c1-cross" x1="0" y1="{cy(Y0):.1f}" x2="0" y2="{cy(Y1):.1f}" stroke="var(--ink)" stroke-width="1" opacity="0" />')
c1.append(f'<rect id="c1-hit" x="{cx(X0):.1f}" y="{cy(Y1):.1f}" width="{cx(X1)-cx(X0):.1f}" height="{cy(Y0)-cy(Y1):.1f}" fill="transparent"/>')
c1.append('</svg>')
CHART1 = '\n'.join(c1)

# --- chart 2: elevation at the plan span (front view, looking down the beds) ---
EK = 4.2
EX_LO, EX_HI = AX0 - 8, BX1 + 8
EZ_LO, EZ_HI = -14.0, max(plan['vert_surf']['crown_grade'], plan['free_surf']['crown_grade']) + 10
ex0, ez0 = 30, 18
def ex(xin): return ex0 + (xin - EX_LO) * EK
def ez(zin): return ez0 + (EZ_HI - zin) * EK
EW = ex(EX_HI) + 150
EH = ez(EZ_LO) + 26
el = []
el.append(f'<svg viewBox="0 0 {EW:.0f} {EH:.0f}" role="img" aria-label="Front view of beds A and B with the panel arched from the centre of one bed to the centre of the other, the inside corner posts reaching up to it, and headroom figures" xmlns="http://www.w3.org/2000/svg">')
el.append('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="currentColor" stroke-width="1"/></pattern></defs>')
# ground
el.append(f'<rect x="{ex(EX_LO):.1f}" y="{ez(0):.1f}" width="{(EX_HI-EX_LO)*EK:.1f}" height="{(0-EZ_LO)*EK:.1f}" fill="var(--lumber)" opacity="0.08"/>')
el.append(f'<line x1="{ex(EX_LO):.1f}" y1="{ez(0):.1f}" x2="{ex(EX_HI):.1f}" y2="{ez(0):.1f}" stroke="var(--muted)" stroke-width="1"/>')
el.append(f'<text x="{ex(EX_HI)-2:.1f}" y="{ez(0)+13:.1f}" font-size="10.5" fill="var(--muted)" text-anchor="end">grade</text>')
# beds: soil then boards
for (x0, x1) in ((AX0, AX1), (BX0, BX1)):
    el.append(f'<rect x="{ex(x0+PT):.1f}" y="{ez(WALL_H-1):.1f}" width="{(x1-x0-2*PT)*EK:.1f}" height="{(WALL_H-1)*EK:.1f}" fill="var(--lumber)" opacity="0.16"/>')
    for side in (x0, x1 - PT):
        for c in range(int(P['Courses']['value_in'])):
            bw = P['Board_Width']['value_in']
            el.append(f'<rect x="{ex(side):.1f}" y="{ez((c+1)*bw):.1f}" width="{PT*EK:.1f}" height="{bw*EK:.1f}" fill="var(--lumber)" opacity="0.6" stroke="var(--lumber)" stroke-width="1"/>')
# paver in the walkway
pv = (WALK0 + WALK1) / 2
el.append(f'<rect x="{ex(pv-6):.1f}" y="{ez(1.5):.1f}" width="{12*EK:.1f}" height="{1.5*EK:.1f}" fill="url(#hatch)" stroke="currentColor" stroke-width="0.8" opacity="0.7"/>')
# profiles (feet at the wall-top level)
def world_pts(sol, feet_z):
    h = sol['h']
    left = [(XC - px, feet_z + h + py) for px, py in sol['profile']]
    right = [(XC + px, feet_z + h + py) for px, py in sol['profile']]
    return list(reversed(left)) + right[1:]
def svgpath(pts):
    return 'M' + ' L'.join(f'{ex(x):.1f} {ez(z):.1f}' for x, z in pts)
# posts (free-feet case sets the drawn height)
ptop = plan['free_surf']['post_top']
for pb in (PA, PB):
    el.append(f'<rect x="{ex(pb["min"][0]):.1f}" y="{ez(ptop):.1f}" width="{PW*EK:.1f}" height="{(ptop-0)*EK:.1f}" fill="var(--lumber)" opacity="0.9" stroke="currentColor" stroke-width="0.8"/>')
    el.append(f'<rect x="{ex(pb["min"][0]):.1f}" y="{ez(0):.1f}" width="{PW*EK:.1f}" height="{EMBED*EK:.1f}" fill="none" stroke="currentColor" stroke-width="0.8" stroke-dasharray="3 2"/>')
el.append(f'<path d="{svgpath(world_pts(vert, FEET_SURF))}" fill="none" class="ser-vert" stroke-width="2.5" stroke-linejoin="round"/>')
el.append(f'<path d="{svgpath(world_pts(free, FEET_SURF))}" fill="none" class="ser-free" stroke-width="3" stroke-linejoin="round"/>')
# feet dots
for xf in (XA, XB):
    el.append(f'<circle cx="{ex(xf):.1f}" cy="{ez(FEET_SURF):.1f}" r="4" fill="var(--panel)" class="ser-free" stroke-width="2"/>')
# screw marks where the panel crosses the post faces
for sgn in (-1, 1):
    xx = XC + sgn * POST_OFF
    zz = plan['free_surf']['at_post']
    el.append(f'<circle cx="{ex(xx):.1f}" cy="{ez(zz):.1f}" r="3.2" fill="currentColor"/>')
# headroom markers
fs = plan['free_surf']
def vline(xw, z, label, dy=-6, anchor='middle'):
    el.append(f'<line x1="{ex(xw):.1f}" y1="{ez(0):.1f}" x2="{ex(xw):.1f}" y2="{ez(z):.1f}" stroke="var(--arch)" stroke-width="1" stroke-dasharray="2 3"/>')
    el.append(f'<text x="{ex(xw)+(5 if anchor=="start" else 0):.1f}" y="{ez(z)+dy:.1f}" font-size="11" fill="var(--ink)" text-anchor="{anchor}" {HALO}>{label}</text>')
vline(XC, fs['crown_grade'], f'crown {ftin(fs["crown_grade"])}', -8, 'start')
vline(WALK0 + 3, fs['at_walk'] - 1.2, f'{ftin(fs["at_walk"])} at the walls', 14, 'start')
# right-hand labels
LX = ex(EX_HI) + 10
def rlabel(z, text, cls='', extra=''):
    el.append(f'<line x1="{ex(EX_HI)-14:.1f}" y1="{ez(z):.1f}" x2="{LX-4:.1f}" y2="{ez(z):.1f}" stroke="var(--muted)" stroke-width="0.8" stroke-dasharray="2 2"/>')
    el.append(f'<text x="{LX:.1f}" y="{ez(z)+4:.1f}" font-size="11" fill="var(--ink)" {extra}>{text}</text>')
rlabel(fs['post_top'], f'post top, {ftin(fs["post_top"])} above grade')
rlabel(fs['at_post'], f'panel crosses the post, {ftin(fs["at_post"])}')
rlabel(FEET_SURF, f'panel feet on the soil, {fin(FEET_SURF, 1)}')
rlabel(-EMBED, f'post {fin(EMBED, 1)} in the ground')
# series labels on the curves
el.append(f'<text x="{ex(XC)-6:.1f}" y="{ez(plan["vert_surf"]["crown_grade"])-8:.1f}" font-size="11" fill="var(--ink)" text-anchor="end" {HALO}>feet held upright, crown {ftin(plan["vert_surf"]["crown_grade"])}</text>')
if plan['vert_surf']['bulge'] >= 1.0:
    el.append(f'<text x="{ex(XA-plan["vert_surf"]["bulge"]-2):.1f}" y="{ez(FEET_SURF+30):.1f}" font-size="10.5" fill="var(--ink)" text-anchor="end" {HALO}>bows out {fin(plan["vert_surf"]["bulge"], 1)}</text>')
# bed names
el.append(f'<text x="{ex((AX0+AX1)/2):.1f}" y="{ez(0)+13:.1f}" font-size="11" fill="var(--muted)" text-anchor="middle">bed A, feet at its centre</text>')
el.append(f'<text x="{ex((BX0+BX1)/2):.1f}" y="{ez(0)+13:.1f}" font-size="11" fill="var(--muted)" text-anchor="middle">bed B, feet at its centre</text>')
el.append(f'<text x="{ex((WALK0+WALK1)/2):.1f}" y="{ez(0)+13:.1f}" font-size="10.5" fill="var(--muted)" text-anchor="middle">walkway {WALK1-WALK0:g} in</text>')
el.append('</svg>')
ELEV_SVG = '\n'.join(el)

# --- chart 3: plan view of the panel footprint ---
PK = 3.0
PY_HI, PY_LO = 8.0, PANEL_Y0 - 14
px0, py0 = 26, 18
def pxx(xin): return px0 + (xin - EX_LO) * PK
def pyy(yin): return py0 + (PY_HI - yin) * PK
PWw = pxx(EX_HI) + 215
PHh = pyy(PY_LO) + 10
pl = []
pl.append(f'<svg viewBox="0 0 {PWw:.0f} {PHh:.0f}" role="img" aria-label="Plan view of the near ends of beds A and B: the panel footprint spans from the centre of bed A to the centre of bed B, its near edge rides on the two inside corner posts, and its feet run along the bed centrelines" xmlns="http://www.w3.org/2000/svg">')
for (x0, x1) in ((AX0, AX1), (BX0, BX1)):
    pl.append(f'<rect x="{pxx(x0):.1f}" y="{pyy(0):.1f}" width="{(x1-x0)*PK:.1f}" height="{(0-PY_LO)*PK:.1f}" fill="var(--lumber)" opacity="0.14" stroke="var(--lumber)" stroke-width="1.2"/>')
    pl.append(f'<rect x="{pxx(x0+PT):.1f}" y="{pyy(-PT):.1f}" width="{(x1-x0-2*PT)*PK:.1f}" height="{(-PT-PY_LO)*PK:.1f}" fill="none" stroke="var(--lumber)" stroke-width="0.8"/>')
# paver strip at the near end and the walkway pavers
pl.append(f'<rect x="{pxx(EX_LO):.1f}" y="{pyy(PY_HI):.1f}" width="{(EX_HI-EX_LO)*PK:.1f}" height="{(PY_HI-0)*PK:.1f}" fill="url(#hatch)" opacity="0.25"/>')
for yy in (-9, -27, -45, -63):
    pl.append(f'<rect x="{pxx(pv-6):.1f}" y="{pyy(yy+6):.1f}" width="{12*PK:.1f}" height="{12*PK:.1f}" fill="url(#hatch)" stroke="currentColor" stroke-width="0.6" opacity="0.6"/>')
# panel footprint
pl.append(f'<rect x="{pxx(XA):.1f}" y="{pyy(PANEL_Y1):.1f}" width="{(XB-XA)*PK:.1f}" height="{PANEL_W*PK:.1f}" fill="var(--arch)" fill-opacity="0.12" stroke="var(--arch)" stroke-width="1.5" stroke-dasharray="6 4"/>')
for xf in (XA, XB):
    pl.append(f'<line x1="{pxx(xf):.1f}" y1="{pyy(PANEL_Y1):.1f}" x2="{pxx(xf):.1f}" y2="{pyy(PANEL_Y0):.1f}" class="ser-free" stroke-width="3"/>')
# posts
for pb, tag in ((PA, 'A'), (PB, 'B')):
    pl.append(f'<rect x="{pxx(pb["min"][0]):.1f}" y="{pyy(pb["max"][1]):.1f}" width="{PW*PK:.1f}" height="{PT*PK:.1f}" fill="var(--lumber)" stroke="currentColor" stroke-width="0.8"/>')
for mb in (MA, MB):
    if mb:
        pl.append(f'<rect x="{pxx(mb["min"][0]):.1f}" y="{pyy(mb["max"][1]):.1f}" width="{PT*PK:.1f}" height="{PW*PK:.1f}" fill="none" stroke="currentColor" stroke-width="0.8" stroke-dasharray="2 2"/>')
# labels
LXp = pxx(EX_HI) + 10
def plabel(y, lines, color='var(--ink)'):
    pl.append(f'<line x1="{pxx(EX_HI)-6:.1f}" y1="{pyy(y):.1f}" x2="{LXp-4:.1f}" y2="{pyy(y):.1f}" stroke="var(--muted)" stroke-width="0.8" stroke-dasharray="2 2"/>')
    for i, t in enumerate(lines):
        pl.append(f'<text x="{LXp:.1f}" y="{pyy(y)+4+13*i-6*(len(lines)-1):.1f}" font-size="11" fill="{color}">{t}</text>')
plabel(PANEL_Y1 - 1, ['near edge of the panel rides on', 'the two inside corner posts'])
if MA:
    plabel((MA['min'][1] + MA['max'][1]) / 2, ['first inside mid-span posts', '(optional extra supports)'], 'var(--muted)')
plabel(PANEL_Y0, [f'far edge, {PANEL_W:g} in down the beds,', 'held only by its feet'])
pl.append(f'<text x="{pxx(XA)+4:.1f}" y="{pyy(PANEL_Y0)-6:.1f}" font-size="10.5" fill="var(--ink)" {HALO}>feet along the bed centreline</text>')
pl.append(f'<text x="{pxx((AX0+AX1)/2):.1f}" y="{pyy(PY_LO)+4:.1f}" font-size="11" fill="var(--muted)" text-anchor="middle">bed A</text>')
pl.append(f'<text x="{pxx((BX0+BX1)/2):.1f}" y="{pyy(PY_LO)+4:.1f}" font-size="11" fill="var(--muted)" text-anchor="middle">bed B</text>')
pl.append(f'<text x="{pxx(EX_LO)+2:.1f}" y="{pyy(PY_HI)+12:.1f}" font-size="10.5" fill="var(--muted)">near end, paver strip</text>')
pl.append('</svg>')
PLAN_SVG = '\n'.join(pl)

# ---------------------------------------------------------------- tables
TABLE_SPANS = [48, 60, 72, int(D) if D == int(D) else D, 84, 96, 120, 144, 168]
rows = []
for d in TABLE_SPANS:
    hp, ang = pinned_closed(d)
    hv = solve_profile(d, 'vert')['h']
    hpost = posts_height(d)
    hc = catenary_height(d)
    tag = ' <span class="src model">plan</span>' if d == D else ''
    rows.append(f'<tr><td><b>{ftin(d)}</b>{tag}</td><td>{ftin(hp)}</td><td>{ftin(hv)}</td><td>{ftin(hpost)}</td><td>{ftin(hc)}</td></tr>')
SPAN_TABLE = '\n'.join(rows)

def plan_row(name, key):
    p = plan[key]
    stick = '8 ft, no cut needed' if p['post_len'] <= STICK8 else f'10 ft, cut to {ftin(p["post_len"], True)}'
    return (f'<tr><td><b>{name}</b></td><td>{fin(p["feet_z"], 1)}</td><td>{ftin(p["crown_grade"])}</td>'
            f'<td>{ftin(p["at_walk"])}</td><td>{ftin(p["at_post"])}</td><td>{ftin(p["post_top"])}</td><td>{stick}</td></tr>')
PLAN_TABLE = '\n'.join([
    plan_row('Free feet, on the soil', 'free_surf'),
    plan_row('Feet held upright, on the soil', 'vert_surf'),
    plan_row('Free feet, 6 in into the soil', 'free_down'),
    plan_row('Feet held upright, 6 in into the soil', 'vert_down'),
])

fs, vs = plan['free_surf'], plan['vert_surf']
fd = plan['free_down']

# ---------------------------------------------------------------- page
CSS = open(os.path.join(ROOT, 'bom.html')).read()
CSS = CSS[CSS.index('<style>'):CSS.index('</style>') + 8]
CSS = CSS.replace('</style>', '''
.ser-free { stroke: var(--arch); }
.ser-vert { stroke: var(--lumber); }
.ser-posts { stroke: var(--ink); stroke-dasharray: 2 5; stroke-linecap: round; }
.ser-cat { stroke: var(--muted); stroke-dasharray: 9 6; }
.sw-line { width: 26px; height: 0; border-top: 3px solid var(--arch); }
.sw-line.vert { border-top-color: var(--lumber); }
.sw-line.posts { border-top: 3px dotted var(--ink); }
.sw-line.cat { border-top: 3px dashed var(--muted); }
figure.chart { max-width: 820px; }
figure.chart svg text { font-family: var(--font-body); }
.answer { font-size: 1.15rem; max-width: 62ch; }
.opts { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.opts .card { margin: 0; }
.opts h3 { margin-bottom: 8px; }
.kv { display: grid; grid-template-columns: auto 1fr; gap: 4px 14px; font-size: 0.95rem; margin: 8px 0 0; }
.kv dt { color: var(--muted); } .kv dd { margin: 0; font-variant-numeric: tabular-nums; }
</style>''')

LEGEND = ('<div class="legend">' + ''.join(
    f'<span><span class="sw-line {("" if k=="free" else k)}"></span>{lbl}</span>' for k, lbl, _ in SERIES) + '</div>')

JS_DATA = json.dumps({'spans': SPANS, 'curves': curves, 'labels': {k: l for k, l, _ in SERIES},
                      'x0': X0, 'x1': X1, 'pl': PL, 'pr': PR, 'cw': CW})

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hog-wire Arch Study</title>
<meta name="description" content="How high a 16 ft hog-wire panel arches between the raised beds for a given foot spacing, and whether the inside corner posts can carry it.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
{CSS}
</head>
<body>
<div class="wrap">
<header class="top">
  <div>
    <h1>Hog-wire arch study</h1>
    <div class="meta">16 ft panel between beds A and B · feet at the bed centres · generated {TODAY} from the Fusion extract</div>
  </div>
  <div class="toolbar">
    <a href="bom.html" class="src">Back to the BOM</a>
    <button id="themeBtn" type="button">Dark theme</button>
  </div>
</header>
<nav class="sticky" aria-label="Sections">
  <a href="#answer">Verdict</a><a href="#chart">Height vs span</a><a href="#layout">Your layout</a><a href="#numbers">Numbers</a><a href="#build">What to build</a><a href="#method">Method</a>
</nav>

<section id="answer">
  <div class="tiles">
    <div class="tile"><div class="n">{ftin(D)}</div><div class="l">between the feet, bed centre to bed centre</div></div>
    <div class="tile"><div class="n">{ftin(fs['crown_grade'])}</div><div class="l">crown above grade with free feet on the soil</div></div>
    <div class="tile"><div class="n">{ftin(fs['at_walk'])}</div><div class="l">headroom at the walkway walls</div></div>
    <div class="tile"><div class="n">{ftin(fs['at_post'])}</div><div class="l">where the panel crosses each inside corner post</div></div>
    <div class="tile"><div class="n">{fs['stick']} ft</div><div class="l">2x4 needed for those posts with the feet on the soil ({fd['stick']} ft if the feet go 6 in down)</div></div>
  </div>
  <div class="note"><b>Decision, 2026-11-06.</b> Modeled as option B with a bigger drop: the whole arch sits 13 in lower than drawn here, its feet on flat 2x4 sills lying on the ground at the bed centrelines, each sill staked at both panel edges. The inside corner posts are uncut 8 ft 2x4s set 20 in deep, so they stand 6 ft 4 in above grade, level with the crown. Headroom becomes about 6 ft 4 in at the walkway centre and 6 ft 2 in at the walls. The BOM page carries the built numbers.</div>
  <h2>Does it make sense?</h2>
  <p class="answer"><b>Yes.</b> Starting the arch at the middle of bed A and ending it at the middle of bed B gives a {ftin(D)} spread, and a 16 ft panel over that spread stands about {ftin(fs['crown_feet'])} above its feet. The two inside corner posts sit {fin(2*POST_OFF)} apart, right under the crown, so they are the natural place to hold the panel up: it crosses each post face only {fin(fs['crown_grade']-fs['at_post'])} below the crown, where the panel is nearly flat. Screw the edge wire to the post face there with washers and the arch is held at the top as well as at the feet.</p>
  <ul>
    <li><b>The posts must be taller than an 8 ft stick allows if the feet sit on the soil.</b> The panel crosses the posts {ftin(fs['at_post'])} above grade and you want about 4 in of post above the screws, so the post needs to stand {ftin(fs['post_top'])} tall plus {fin(EMBED,1)} in the ground: a {fs['stick']} ft 2x4 cut to {ftin(fs['post_len'], True)}. Push the panel feet 6 in into the bed soil instead and an uncut 8 ft 2x4 ({ftin(STICK8-EMBED)} above grade) has {fin(STICK8-EMBED-fd['at_post'])} of post above the crossing.</li>
    <li><b>How the feet are held hardly matters at this spacing.</b> Feet that can tilt (set on a sill, screwed with washers) give {ftin(fs['crown_feet'])} above the feet and lean {fs['end_lean']:.0f}° outward at the bottom. Feet clamped upright in the soil lift the crown only {fin(vs['crown_feet']-fs['crown_feet'],1)} more and bow the sides out {fin(vs['bulge'],1)}. Both are drawn below; the posts are sized for the lower one so the screws land in wood either way.</li>
    <li><b>Only the near edge of the panel is on the posts.</b> The panel is {PANEL_W:g} in wide and runs down the beds from the corner posts; its far edge is held only by its feet. A bent panel is stiff across its width, so that is fine for a trellis, and the first inside mid-span posts ({fin((MA['max'][1]+MA['min'][1])/-2) if MA else '–'} down bed A, {fin((MB['max'][1]+MB['min'][1])/-2) if MB else '–'} down bed B) can be extended the same way later if it ever racks.</li>
    <li><b>The feet want a sill, not loose soil.</b> With free feet the panel pushes its ends outward; a flat 2x4 sill across each bed on its centreline (buried flush, {fin(AX1-AX0-2*PT)} long between the side boards) with the bottom wire screwed to it holds that, and it keeps the two feet exactly {ftin(D)} apart so the arch comes out the height this page predicts.</li>
  </ul>
</section>

<section id="chart">
  <h2>Height against foot spacing, 16 ft panel</h2>
  <p>The sketch plots a catenary, which is the shape of a hanging chain. A galvanized panel is a stiff rod, not a chain, so its real shape is an elastica: the two solid curves. The catenary tracks the free-feet panel closely at wide spacings and overstates it at narrow ones, where a real panel bows out at the sides instead of rising further. Hover for the four heights at any spacing.</p>
  {LEGEND}
  <figure class="chart">
    <div class="scroll">{CHART1}</div>
    <figcaption>Peak height above the feet for a 16 ft panel whose feet are held a given distance apart. The dotted series ends where the legs run out: a semicircle of 16 ft of panel is {ftin(L*R_CIRCLE)} across.</figcaption>
  </figure>
</section>

<section id="layout">
  <h2>Your layout at {ftin(D)}</h2>
  <p>Front view from the near end. The panel feet are on the bed soil at the bed centrelines, {fin(FEET_SURF,1)} above grade. The thick blue arch has free feet; the orange one has its feet clamped upright in the soil. The inside corner posts are drawn at the height the free-feet case needs: {ftin(fs['post_top'])} above grade.</p>
  <figure class="chart">
    <div class="scroll">{ELEV_SVG}</div>
    <figcaption>Headroom on the walkway is {ftin(fs['at_walk'])} at the walls and {ftin(fs['crown_grade'])} at the centre. The black dots are where the edge wire crosses each post face and gets its screws and washers; the post continues {fin(fs['post_top']-fs['at_post'])} past them.</figcaption>
  </figure>
  <figure class="chart">
    <div class="scroll">{PLAN_SVG}</div>
    <figcaption>Plan of the near ends. The panel footprint (blue dashes) runs from one bed centreline to the other and {PANEL_W:g} in down the beds; the feet are the two thick lines. Only the near edge touches the corner posts.</figcaption>
  </figure>
</section>

<section id="numbers">
  <h2>Numbers</h2>
  <h3>Peak height above the feet <small>16 ft panel</small></h3>
  <div class="tablewrap"><table>
    <thead><tr><th>Feet apart</th><th>Free feet</th><th>Feet held upright</th><th>Legs on posts</th><th>Catenary (sketch)</th></tr></thead>
    <tbody>{SPAN_TABLE}</tbody>
  </table></div>
  <h3 style="margin-top:20px">The {ftin(D)} plan <small>heights above grade</small></h3>
  <div class="tablewrap"><table>
    <thead><tr><th>Feet</th><th>Feet above grade</th><th>Crown</th><th>At the walkway walls</th><th>Panel at the post</th><th>Post top needed</th><th>Stick</th></tr></thead>
    <tbody>{PLAN_TABLE}</tbody>
  </table></div>
  <p class="muted" style="margin-top:10px">Post top = panel crossing at the post's outer edge + 4 in; post length adds {fin(EMBED,1)} below grade. For comparison the 2026-11-06 design (legs held straight by {ftin(P['Trellis_Post_Length']['value_in'])} posts, semicircle above) crowns at {ftin(plan['posts_old']['crown_grade'])} with feet on the wall tops.</p>
</section>

<section id="build">
  <h2>What to build</h2>
  <div class="opts">
    <div class="card">
      <h3>A. Feet on the soil, 10 ft posts</h3>
      <p>Sill flush with the soil at each bed centreline; panel feet screwed to it. Inside corner posts from 10 ft 2x4s cut to {ftin(fs['post_len'], True)}.</p>
      <dl class="kv"><dt>Crown</dt><dd>{ftin(fs['crown_grade'])} to {ftin(vs['crown_grade'])}</dd><dt>Walkway walls</dt><dd>{ftin(fs['at_walk'])}</dd><dt>Post top</dt><dd>{ftin(fs['post_top'])}</dd><dt>Offcut</dt><dd>{ftin(STICK10-fs['post_len'], True)}, not a stake</dd></dl>
    </div>
    <div class="card">
      <h3>B. Feet 6 in down, 8 ft posts uncut</h3>
      <p>Sill buried 6 in below the soil surface (or the panel ends pushed 6 in in and wired to two stakes). Inside corner posts are plain 8 ft 2x4s, {ftin(STICK8-EMBED)} above grade.</p>
      <dl class="kv"><dt>Crown</dt><dd>{ftin(fd['crown_grade'])} to {ftin(plan['vert_down']['crown_grade'])}</dd><dt>Walkway walls</dt><dd>{ftin(fd['at_walk'])}</dd><dt>Post above the crossing</dt><dd>{fin(STICK8-EMBED-fd['at_post'])}</dd><dt>Offcut</dt><dd>none</dd></dl>
    </div>
  </div>
  <h3 style="margin-top:20px">Either way</h3>
  <ul>
    <li>Two tall posts per arch instead of four: bed A's inside corner post and bed B's inside corner post at the near end. The six other trellis posts from the previous design go back to being 24 in stakes and 14.5 in corner posts.</li>
    <li>Edge wire to each post face with 2 × #9 2.5 in screws and 1 in fender washers at the crossing; bottom wire to each sill with 3 screws and washers.</li>
    <li>The panel feet stay inside the beds, so nothing lands on the pavers and the walkway keeps its full {WALK1-WALK0:g} in.</li>
    <li>Arch BC at the far end is not part of this study; it can be moved to the same scheme (bed B centre to bed C centre) or dropped.</li>
  </ul>
</section>

<section id="method">
  <h2>Method</h2>
  <p>A bent cattle panel is a uniform elastic rod, so its centreline obeys the elastica equation (the pendulum equation in the tangent angle). Each curve is found by integrating that equation from the crown with a fourth-order Runge–Kutta scheme and shooting on the axial force until the chord comes out at the chosen spacing; the panel length then fixes the scale. Free feet means zero bending moment at the ends (pinned); held upright means the ends are forced vertical (clamped), which below {ftin(L*R90)} apart makes the sides bow outward before they rise. The pinned case was checked against its closed form in complete elliptic integrals (agreement within 0.05 in). The catenary is the hanging-chain curve of the same length, for comparison with the sketch. Self-weight and the panel's mesh are ignored; panel length {ftin(L)} and bed geometry come from the Fusion extract.</p>
</section>
</div>
<div id="tip" role="status"></div>
<script>
window.ARCH = {JS_DATA};
</script>
<script>
(function () {{
  var root = document.documentElement;
  function apply(t) {{
    if (t) root.setAttribute('data-theme', t); else root.removeAttribute('data-theme');
    var b = document.getElementById('themeBtn');
    if (b) b.textContent = (t === 'dark' || (!t && window.matchMedia('(prefers-color-scheme: dark)').matches)) ? 'Light theme' : 'Dark theme';
  }}
  var saved = null;
  try {{ saved = localStorage.getItem('fg-theme'); }} catch (e) {{}}
  apply(saved);
  document.getElementById('themeBtn').addEventListener('click', function () {{
    var cur = root.getAttribute('data-theme');
    var isDark = cur === 'dark' || (!cur && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var next = isDark ? 'light' : 'dark';
    apply(next);
    try {{ localStorage.setItem('fg-theme', next); }} catch (e) {{}}
  }});
  var tip = document.getElementById('tip');
  var hit = document.getElementById('c1-hit');
  var cross = document.getElementById('c1-cross');
  var A = window.ARCH;
  function ftin(v) {{
    if (v === null || v === undefined) return 'no legs left';
    var t = Math.round(v); var f = Math.floor(t / 12); var r = t - 12 * f;
    return f ? (f + ' ft' + (r ? ' ' + r + ' in' : '')) : (r + ' in');
  }}
  if (hit) {{
    var svg = hit.ownerSVGElement;
    hit.addEventListener('mousemove', function (e) {{
      var pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
      var p = pt.matrixTransform(svg.getScreenCTM().inverse());
      var ft = A.x0 + (p.x - A.pl) / (A.cw - A.pl - A.pr) * (A.x1 - A.x0);
      var inch = ft * 12, best = 0, bd = 1e9;
      for (var i = 0; i < A.spans.length; i++) {{ var d = Math.abs(A.spans[i] - inch); if (d < bd) {{ bd = d; best = i; }} }}
      var sx = A.pl + (A.spans[best] / 12 - A.x0) / (A.x1 - A.x0) * (A.cw - A.pl - A.pr);
      cross.setAttribute('x1', sx); cross.setAttribute('x2', sx); cross.setAttribute('opacity', '0.5');
      var html = '<b>' + ftin(A.spans[best]) + ' between the feet</b>';
      ['free', 'vert', 'posts', 'cat'].forEach(function (k) {{ html += '<br>' + A.labels[k].replace(' (previous design)', '') + ': ' + ftin(A.curves[k][best]); }});
      tip.innerHTML = html; tip.style.display = 'block';
      var x = e.clientX + 14, y = e.clientY + 14;
      if (x + 330 > window.innerWidth) x = e.clientX - 330;
      if (y + 110 > window.innerHeight) y = e.clientY - 110;
      tip.style.left = x + 'px'; tip.style.top = y + 'px';
    }});
    hit.addEventListener('mouseleave', function () {{ tip.style.display = 'none'; cross.setAttribute('opacity', '0'); }});
  }}
}})();
</script>
</body>
</html>
'''

with open(OUT_HTML, 'w') as f:
    f.write(HTML)
with open(OUT_JSON, 'w') as f:
    json.dump({'generated': TODAY, 'panel_in': L, 'span_in': D, 'feet_x': [XA, XB], 'post_offset_in': POST_OFF,
               'spans_in': SPANS, 'curves_in': curves, 'plan': plan,
               'free': {k: v for k, v in free.items() if k != 'profile'},
               'vert': {k: v for k, v in vert.items() if k != 'profile'}}, f, indent=1)
print(f'span={D} feet=({XA},{XB}) post_off={POST_OFF} walk={POST_IN} post_out={POST_OUT} panel_w={PANEL_W} wires={N_WIRES}')
for k, v in plan.items():
    print(k, {kk: (round(vv, 1) if isinstance(vv, float) else vv) for kk, vv in v.items()})
print('free: h=%.1f angle=%.1f widest=%.1f R=%.1f branch=%s' % (free['h'], free['end_angle'], 2*free['half_width'], free['crown_radius'], free['branch']))
print('vert: h=%.1f angle=%.1f widest=%.1f R=%.1f branch=%s lam=%.4f' % (vert['h'], vert['end_angle'], 2*vert['half_width'], vert['crown_radius'], vert['branch'], vert['lam']))
print('curves:', {k: [round(x, 1) if x is not None else None for x in v] for k, v in curves.items()})
print('wrote', OUT_HTML, os.path.getsize(OUT_HTML), 'bytes')

"""The layout asked for on 2026-11-15, applied to an extract of a model that does not have it yet.

make_bom.py calls apply() on data/model_extract.json before it counts anything. The extract itself stays what
scripts/fusion_extract_model.py wrote; the overlay edits the copy in memory and reports what it changed. Once the
live model has the same layout (scripts/fusion_stake_grid.py makes the change in Fusion) and has been extracted
again, apply() finds nothing left to do, returns no changes, and the "planned" notes drop out of the BOM.

What it does to the bed lumber:
  - Beds in SIDE_SPLITS (Bed B) get two side boards per course from 8 ft stock, like beds C and D: 96 + 48 in
    in course 1 and 48 + 96 in course 2, so the seams are staggered, with a 2x8 joint post behind every seam.
  - Every bed's 2x4 mid-span stakes move onto a STAKE_PITCH grid measured from the near end. All four beds are a
    whole number of pitches long and every seam falls on the grid, so a joint post takes the place of the stake
    at a seam and the last stake stands one pitch from the far end.

What it does to the drip risers (scripts/fusion_build_irrigation.py builds the same stack in Fusion):
  - A riser that still has the glued 2026-11-06 parts (a 3/4 x 1/2 in reducer tee and cut 1/2 in pipe in slip
    fittings) becomes a threaded stack: a 3/4 in slip tee on the main, a stub of 3/4 in pipe, a 3/4 in slip x
    1/2 in FPT reducing elbow, and threaded 1/2 in risers in bought lengths (DRIP_RISERS) through an FPT x FPT ball
    valve and two FPT elbows to the drip head. The riser keeps its place along the wall and the hole keeps its
    height; the riser axis moves to STANDOFF off the wall and the valve, clamps and head move with the new lengths.
  - The reference main drops to the depth the lower riser gives (6.5 in for an 8 in riser). Its real depth is the
    owner's to measure: hole height = lower riser + upper riser + 3.375 in - depth of the main's centre.
"""
import copy
import math

T = 1.5             # 2x lumber thickness (in)
PT, PW = 1.5, 3.5   # a 2x4 lying flat against the wall: 1.5 in into the bed, 3.5 in along it
JW = 7.25           # a 2x8 joint post lying flat: 7.25 in along the wall
STAKE_PITCH = 24.0  # centre to centre along each long wall, from the near end (in)
# beds whose one-piece side boards become two per course: letter -> {course: [seams, inches from the near end]}
SIDE_SPLITS = {'B': {1: [96.0], 2: [48.0]}}
DATE = '2026-11-15'

# ---- drip risers: the threaded stack (inches; scripts/fusion_build_irrigation.py has the same numbers) ----
OLD_TEE = '3/4 x 1/2 in reducer tee'   # a riser that still has this body is the glued 2026-11-06 build
OLD_STANDOFF = 1.25                    # that build's riser axis off the wall; used only if the bed's end board is not found
DRIP_RISERS = {'lower': 8.0, 'upper': 6.0, 'through wall': 3.0, 'head': 4.0}   # threaded 1/2 in risers, bought lengths
THREAD = 0.5                           # a riser end screws this far into a fitting
ELL = 1.125                            # 1/2 in FPT elbow: centre to hub end
RED = 1.25                             # 3/4 in slip x 1/2 in FPT reducing elbow: centre to hub end, both ways
TEE = 1.25                             # 3/4 in slip tee: centre to hub end
SOCKET = 0.75                          # 3/4 in slip socket depth
R12, HUB_R12 = 0.84 / 2, 1.30 / 2      # riser and threaded hub radii
R34, HUB_R34 = 1.05 / 2, 1.40 / 2      # 3/4 in pipe and hub radii
STANDOFF = ELL + 0.25                  # riser axis off the wall: the elbow hub stops 1/4 in short of the board
VALVE_LEN, VALVE_BODY_R, VALVE_BODY_LEN = 3.0, 0.8, 2.0
HEAD_R, HEAD_H, BARB_LEN = 0.625, 2.0, 0.6
CLAMP_Z = (5.5, 8.75)                  # clamp centres above grade: both on the upper riser, one on each board
CLAMP_W, CLAMP_H = 2.5, 1.0


def stake_stations(L, seams, pitch=STAKE_PITCH):
    """Stake centres along a wall L long, inches from the near end: every pitch, except where a joint post stands."""
    out = []
    k = 1
    while k * pitch < L - (T + PT + PW / 2.0) + 1e-6:      # stay clear of the far corner post
        s = k * pitch
        if not any(abs(s - j) < (JW + PW) / 2.0 for j in seams):
            out.append(s)
        k += 1
    return out


def _body(template, name, lo, hi):
    """A box body like `template` (same component, material and density) with new corners."""
    b = copy.deepcopy(template)
    dims = sorted(round(hi[i] - lo[i], 3) for i in range(3))
    vol = dims[0] * dims[1] * dims[2]
    dens = (template['mass_kg'] / template['volume_in3']) if template.get('mass_kg') and template.get('volume_in3') else None
    b.update({'body': name, 'dims_in': dims, 'min': [round(v, 3) for v in lo], 'max': [round(v, 3) for v in hi],
              'volume_in3': round(vol, 2), 'mass_kg': round(vol * dens, 4) if dens else None, 'visible': True})
    return b


def apply(model):
    """Returns (model, changes). `changes` is {'lumber': [...], 'drip': [...]}: sentences saying what the overlay
    changed in each part of the design, empty lists when the extract already has it. The input is not modified."""
    m = copy.deepcopy(model)
    return m, {'lumber': _lumber(m), 'drip': _drip(m)}


def _solid(template, name, lo, hi, vol):
    """_body() for a part that is not a box: the corners are its bounding box and its volume is given."""
    b = _body(template, name, lo, hi)
    dens = (template['mass_kg'] / template['volume_in3']) if template.get('mass_kg') and template.get('volume_in3') else None
    b.update({'volume_in3': round(vol, 2), 'mass_kg': round(vol * dens, 4) if dens else None})
    return b


def _riser_stack(x, wall, zh, main_y, pvc, steel, head):
    """One bed's threaded riser as bodies. x: the riser axis; wall: y of the far end board's outside face (the bed is
    toward +y, the main toward -y); zh: hole centre above grade; main_y: the main's axis. pvc, steel and head are
    bodies of the riser being replaced, copied for their component, path, material and density.
    Returns (bodies, z of the main's axis)."""
    grip = ELL - THREAD                                   # elbow centre to the end of the riser screwed into it
    yo = wall - STANDOFF                                  # riser axis outside the wall
    yi = yo + DRIP_RISERS['through wall'] + 2 * grip      # riser axis inside the bed
    up1 = zh - grip
    up0 = up1 - DRIP_RISERS['upper']
    v1 = up0 + THREAD                                     # valve faces
    v0 = v1 - VALVE_LEN
    lo1 = v0 + THREAD
    lo0 = lo1 - DRIP_RISERS['lower']
    zm = lo0 - (RED - THREAD)                             # reducing elbow centre = the main's axis
    hd0 = zh + grip
    hd1 = hd0 + DRIP_RISERS['head']
    h0 = hd1 - THREAD                                     # head base
    s0, s1 = main_y + TEE - SOCKET, yo - (RED - SOCKET)   # the stub, socket bottom to socket bottom

    def cyl(r, length):
        return math.pi * r * r * length

    def ell(r, hub):                                      # a ball and two hubs of one radius at right angles
        return 2 * math.pi * r * r * hub - 4 * r ** 3 / 3 + math.pi * r ** 3 / 3

    def riser(name, lo, hi):
        return _solid(pvc, name, lo, hi, cyl(R12, max(hi[i] - lo[i] for i in range(3))))

    head_r = HEAD_R + BARB_LEN
    clamp_d = STANDOFF + R12 + 0.2
    valve_vol = cyl(VALVE_BODY_R, VALVE_BODY_LEN) + cyl(HUB_R12, VALVE_LEN - VALVE_BODY_LEN) + cyl(0.2, 0.5) + 2.4 * 0.45 * 0.3
    out = [
        _solid(pvc, '3/4 in tee', [x - TEE, main_y - HUB_R34, zm - HUB_R34], [x + TEE, main_y + TEE, zm + HUB_R34],
               3 * cyl(HUB_R34, TEE) - 8 * HUB_R34 ** 3 / 3),
        _solid(pvc, '3/4 in pipe, stub', [x - R34, s0, zm - R34], [x + R34, s1, zm + R34], cyl(R34, s1 - s0)),
        _solid(pvc, '3/4 x 1/2 in reducing elbow', [x - HUB_R34, yo - RED, zm - HUB_R34], [x + HUB_R34, yo + HUB_R34, zm + RED], ell(HUB_R34, RED)),
        riser('1/2 in riser, lower', [x - R12, yo - R12, lo0], [x + R12, yo + R12, lo1]),
        _solid(pvc, '1/2 in ball valve', [x - 2.2, yo - VALVE_BODY_R - 0.95, v0], [x + VALVE_BODY_R, yo + VALVE_BODY_R, v1], valve_vol),   # lever west
        riser('1/2 in riser, upper', [x - R12, yo - R12, up0], [x + R12, yo + R12, up1]),
        _solid(pvc, '1/2 in elbow, outside', [x - HUB_R12, yo - HUB_R12, zh - ELL], [x + HUB_R12, yo + ELL, zh + HUB_R12], ell(HUB_R12, ELL)),
        riser('1/2 in riser, through wall', [x - R12, yo + grip, zh - R12], [x + R12, yi - grip, zh + R12]),
        _solid(pvc, '1/2 in elbow, inside', [x - HUB_R12, yi - ELL, zh - HUB_R12], [x + HUB_R12, yi + HUB_R12, zh + ELL], ell(HUB_R12, ELL)),
        riser('1/2 in riser, head', [x - R12, yi - R12, hd0], [x + R12, yi + R12, hd1]),
        _solid(head, head['body'], [x - head_r, yi - head_r, h0], [x + head_r, yi + head_r, h0 + HEAD_H], head['volume_in3']),
    ]
    for name, cz in zip(('1/2 in stand-off clamp, lower', '1/2 in stand-off clamp, upper'), CLAMP_Z):
        out.append(_solid(steel, name, [x - CLAMP_W / 2, wall - clamp_d, cz - CLAMP_H / 2], [x + CLAMP_W / 2, wall, cz + CLAMP_H / 2],
                          CLAMP_W * clamp_d * CLAMP_H - cyl(R12 + 0.03, CLAMP_H)))
    return out, zm


def _drip(m):
    """Threaded riser stacks in place of the glued ones, applied to m in place. Returns one sentence per change."""
    bodies = m['bodies']
    old = sorted({b['path'] for b in bodies if b['component'] == 'Drip riser' and b['body'] == OLD_TEE})
    if not old:
        return []
    new = {}
    was = now = None
    for p in old:
        parts = {b['body']: b for b in bodies if b['path'] == p}
        tee, up, thru = parts[OLD_TEE], parts['1/2 in pipe, upper riser'], parts['1/2 in pipe, through wall']
        x = (up['min'][0] + up['max'][0]) / 2.0
        ends = [b for b in bodies if b['component'].startswith('Bed ') and b['body'].startswith('End') and b['visible']
                and b['min'][0] - 1e-6 <= x <= b['max'][0] + 1e-6]
        # the far end board's outside face; the bed runs toward -y, so that is the lowest y of its end boards
        wall = min(b['min'][1] for b in ends) if ends else (up['min'][1] + up['max'][1]) / 2.0 + OLD_STANDOFF
        zh = (thru['min'][2] + thru['max'][2]) / 2.0
        main_y = tee['min'][1] + HUB_R34        # the tee's run is a 3/4 in hub along x: its low side is one hub radius from the axis
        clamps = sorted((b for k, b in parts.items() if 'clamp' in k), key=lambda b: b['min'][2])
        valve, head = parts['1/2 in ball valve'], next(b for k, b in parts.items() if 'drip head' in k)
        if was is None:
            was = {'main': -(tee['min'][2] + tee['max'][2]) / 2.0, 'valve': (valve['min'][2] + valve['max'][2]) / 2.0,
                   'standoff': wall - (up['min'][1] + up['max'][1]) / 2.0, 'head': head['max'][2],
                   'clamps': [(b['min'][2] + b['max'][2]) / 2.0 for b in clamps]}
        new[p], zm = _riser_stack(x, wall, zh, main_y, tee, clamps[0], head)
        if now is None:
            got = {b['body']: b for b in new[p]}
            now = {'main': -zm, 'valve': (got['1/2 in ball valve']['min'][2] + got['1/2 in ball valve']['max'][2]) / 2.0,
                   'head': got[head['body']]['max'][2], 'stub': got['3/4 in pipe, stub']['dims_in'][2]}
    out, seen = [], set()
    for b in bodies:                             # each new stack goes where the old riser's bodies were
        if b['path'] in new:
            if b['path'] not in seen:
                out += new[b['path']]
                seen.add(b['path'])
        else:
            out.append(b)
    dz = was['main'] - now['main']               # the main moves with the reducing elbow
    for b in out:
        if b['component'].startswith('3/4 in main') and abs(dz) > 1e-6:
            b['min'][2], b['max'][2] = round(b['min'][2] + dz, 3), round(b['max'][2] + dz, 3)
    m['bodies'] = out
    lengths = ', '.join(f'{v:g}' for v in DRIP_RISERS.values())
    stack = (f"3/4 in tee on the main ({now['main']:g} in deep), {now['stub']:g} in stub of 3/4 in pipe, 3/4 in slip x 1/2 in FPT reducing elbow, "
             f"threaded 1/2 in risers ({lengths} in), FPT x FPT ball valve {now['valve']:g} in above grade, two FPT elbows, drip head with its top at {now['head']:g} in, "
             f"clamps at {CLAMP_Z[0]:g} and {CLAMP_Z[1]:g} in, riser axis {STANDOFF:g} in off the wall")
    for c in m['components']:
        if c['name'] == 'Drip riser' and c.get('path') in new:
            c['bodyCount'] = len(new[c['path']])
            c['description'] = (c.get('description') or '') + f' Planned {DATE}, not in the model yet: {stack}.'
        elif c['name'].startswith('3/4 in main') and abs(dz) > 1e-6:
            c['description'] = (c.get('description') or '') + f" Planned {DATE}, not in the model yet: axis {now['main']:g} in below grade."
    changes = [f"Drip risers ({len(new)}): 3/4 in tees, {now['stub']:g} in stubs of 3/4 in pipe, 3/4 x 1/2 in reducing elbows and threaded 1/2 in risers "
               f"({lengths} in) through FPT fittings in place of reducer tees and cut schedule 40 pipe; riser axis {STANDOFF:g} in off the wall (was {was['standoff']:g}), "
               f"valve {now['valve']:g} in above grade (was {was['valve']:g}), clamps at {CLAMP_Z[0]:g} and {CLAMP_Z[1]:g} in "
               f"(were {' and '.join(f'{z:g}' for z in was['clamps'])}), head top {now['head']:g} in (was {was['head']:g})"]
    if abs(dz) > 1e-6:
        changes.append(f"3/4 in main (reference): drawn {now['main']:g} in deep instead of {was['main']:g} in, the depth an {DRIP_RISERS['lower']:g} in lower riser gives")
    return changes


def _lumber(m):
    """8 ft boards in Bed B and the stake grid, applied to m in place. Returns one sentence per bed changed."""
    params = m['params']
    BW = params['Board_Width']['value_in']
    H = int(round(params['Courses']['value_in'])) * BW
    below = params['Mid_Post_Length']['value_in'] - H         # how far a stake or joint post runs below grade
    changes = []
    names = sorted({b['component'] for b in m['bodies'] if b['component'].startswith('Bed ') and b['component'] != 'Bed Lumber'})
    for comp in names:
        letter = comp.split(' ')[1]
        mine = [b for b in m['bodies'] if b['component'] == comp and b['visible']]
        sides = [b for b in mine if b['body'].startswith('Side')]
        mids = [b for b in mine if 'mid' in b['body'].lower()]
        joints = [b for b in mine if 'joint' in b['body'].lower()]
        if not sides or not mids:
            continue
        xmin, xmax = min(b['min'][0] for b in sides), max(b['max'][0] for b in sides)
        near, far = max(b['max'][1] for b in sides), min(b['min'][1] for b in sides)
        L = near - far
        what = []
        drop, add = [], []

        # 1. two side boards per course where the bed still has one
        splits = SIDE_SPLITS.get(letter)
        whole = all(abs((b['max'][1] - b['min'][1]) - L) < 1e-3 for b in sides)
        if splits and whole:
            for b in sides:
                course = int(round(b['min'][2] / BW)) + 1
                pts = [0.0] + sorted(splits.get(course, [])) + [L]
                for a, c in zip(pts, pts[1:]):
                    add.append(_body(b, f'Side board {c - a:g} in', [b['min'][0], near - c, b['min'][2]], [b['max'][0], near - a, b['max'][2]]))
                drop.append(b)
            seams_new = sorted({s for ss in splits.values() for s in ss})
            tpl = joints[0] if joints else mids[0]
            for s in seams_new:
                for x0 in (xmax - T - T, xmin + T):
                    add.append(_body(tpl, '2x8 joint post', [x0, near - s - JW / 2.0, -below], [x0 + T, near - s + JW / 2.0, H]))
            layout = ', '.join(f"course {c}: {' + '.join(f'{y - x:g}' for x, y in zip([0.0] + sorted(ss), sorted(ss) + [L]))} in" for c, ss in sorted(splits.items()))
            what.append(f'side walls of two boards per course from 8 ft stock ({layout}) over {2 * len(seams_new)} 2x8 joint posts')

        # 2. mid-span stakes on the pitch grid
        seams = sorted({round(near - b['max'][1], 3) for b in [x for x in sides if x not in drop] + add
                        if b['body'].startswith('Side') and b['max'][1] < near - 1e-3})
        want = stake_stations(L, seams)
        have = sorted({round(near - (b['min'][1] + b['max'][1]) / 2.0, 2) for b in mids})
        if [round(w, 2) for w in want] != have:
            drop += mids
            for s in want:
                for x0 in (xmax - T - PT, xmin + T):
                    add.append(_body(mids[0], '2x4 mid post', [x0, near - s - PW / 2.0, -below], [x0 + PT, near - s + PW / 2.0, H]))
            what.append(f"{2 * len(want)} mid-span stakes every {STAKE_PITCH:g} in ({', '.join(f'{s:g}' for s in want)} in from the near end on both walls) in place of {len(mids)}")

        if not what:
            continue
        ids = {id(b) for b in drop}
        m['bodies'] = [b for b in m['bodies'] if id(b) not in ids] + add
        for c in m['components']:
            if c['name'] == comp:
                c['bodyCount'] = sum(1 for b in m['bodies'] if b['component'] == comp)
                c['description'] = (c.get('description') or '') + f" Planned {DATE}, not in the model yet: {'; '.join(what)}."
        changes.append(f"Bed {letter}: {'; '.join(what)}")
    return changes


if __name__ == '__main__':
    import json
    from pathlib import Path
    src = Path(__file__).resolve().parent.parent / 'data' / 'model_extract.json'
    _, done = apply(json.load(open(src)))
    for part, lines in done.items():
        print(part + ':', '\n  '.join(lines) if lines else 'the extract already has it')

#!/usr/bin/env python3
"""Generate BOM.md, BOM.csv, BOM-by-bed.csv and bom.html from data/model_extract.json.

Lumber is listed as store-length sticks to buy, chosen by scripts/cutstock.py from the
lengths and prices in STOCK_PRICES, with the cuts each stick becomes.

The extract is written by scripts/fusion_extract_model.py from the Fusion
design "Raised Bed Design". Everything with a quantity in the BOM is counted from
model bodies; hardware, base material and soil are derived estimates and are
labelled as such.
"""
import csv
import datetime
import html
import json
import math
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cutstock  # noqa: E402  (scripts/cutstock.py: least-cost cutting of a bed's pieces from store lengths)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'model_extract.json'
TODAY = datetime.date.today().isoformat()

d = json.load(open(DATA))
bodies = [b for b in d['bodies'] if b['visible']]
params = d['params']
BOARD_W = params['Board_Width']['value_in']
COURSES = int(round(params['Courses']['value_in']))
T = 1.5           # 2x actual thickness
KG2LB = 2.20462
ALT_BOARD_W = 9.25  # the 2x10 alternative
HOGWIRE_LEN = params['Hogwire_length']['value_in']
HOG_LEG = params['Hogwire_height']['value_in']
HOG_ARC = params['Hogwire_archlength']['value_in']
TRELLIS_LEN = params['Trellis_Post_Length']['value_in'] if 'Trellis_Post_Length' in params else None
# hog-wire panel fasteners (bed-centre arch of 2026-11-06): a short screw through a 1 in fender washer beside a wire traps the
# wire against the wood, and 1.25 in stays inside a 1.5 in thick post, stake or sill so no tip pokes out the back
PANEL_SCREW = '#9 x 1.25 in'
PANEL_SCREWS_PER_POST = 2   # at the crossing near the top of each trellis post, one each side of the edge wire
PANEL_SCREWS_PER_STAKE = 2  # edge wire to each arch-foot stake
PANEL_SCREWS_PER_SILL = 4   # bottom wire along each sill
STAKE_SILL_SCREWS = 2       # #9 x 3 in through each stake into the sill's end grain
WIRE_R = 0.25               # the model draws panel wires 1/2 in thick

# screw plan constants
SCREWS_PER_JOINT = 2        # per 2x8 board per post
TIES_PER_CORNER = 2         # per corner per course, through the side board into the end-board end grain
SCREW_HEIGHTS = (1.75, 5.5)  # in from the bottom edge of each board, post screws
TIE_HEIGHTS = (2.75, 4.5)    # in from the bottom edge, corner ties (staggered off the post screws)
MID_OFFSET = 0.75           # in either side of a mid-span post's centerline: its two screws per board are staggered across the 3.5 in face
PER_LB = {3.0: 70, 2.5: 90, 1.25: 180}  # about this many #9 screws per pound, by length
KERF = cutstock.KERF        # saw kerf, in

# Store lumber: the lengths stocked and single-stick prices before tax, used for the buy lists.
# The store is deliberately not named anywhere in the generated files (nor its city, nor its house brands).
PRICE_DATE = '2026-11-08'
PRICE_GRADE = '#1 ground-contact pressure-treated pine'
PRICE_SOURCE = f'single-stick prices for {PRICE_GRADE} at a big-box home center, checked {PRICE_DATE}'
STOCK_PRICES = {            # nominal -> {length ft: $ each}. No 14 ft 2x8 or 2x10 is stocked; 20 ft is delivery-only and left out.
    '2x4': {2: 1.98, 4: 4.78, 6: 5.28, 8: 7.08, 10: 8.98, 12: 10.88, 16: 16.78},
    '2x8': {8: 14.78, 10: 18.88, 12: 22.68, 16: 30.68},
    '2x10': {8: 21.08, 10: 26.88, 12: 32.78, 16: 43.08},
}
STOCK_IN_PRICES = {nom: {ft * 12.0: price for ft, price in d.items()} for nom, d in STOCK_PRICES.items()}
END_TOL = 0.25              # an end board may run this much short so two clear the kerf on one 8 ft board
CORNER_TOL = 0.5            # a corner post may run this much short of the wall height
POST_TOL = 1.0              # a mid-span post or arch stake may run this much short (it comes out of the ground, not the wall)
OPTION_MIN_FT = 6           # 'buy only this length' comparisons start here; 2 ft and 4 ft sticks stay available to the solver


def buy_text(n, length):
    per = PER_LB[length]
    k = math.ceil(n * 1.1 / per)   # 1 lb boxes with 10 percent spare
    if k <= 2:
        return f'{k} x 1 lb box{"es" if k > 1 else ""} (about {k * per}), or one 5 lb box (about {5 * per}) for plenty of spares'
    return f'one 5 lb box (about {5 * per}); 1 lb boxes hold only about {per}'


def nominal(width):
    return {5.5: '2x6', 7.25: '2x8', 9.25: '2x10', 11.25: '2x12'}.get(round(width, 2), f'2x{width:g}')


NOM = nominal(BOARD_W)
ALT_NOM = nominal(ALT_BOARD_W)


def ft_in(inches):
    ft, rem = divmod(round(inches, 3), 12)
    ft = int(ft)
    if abs(rem) < 1e-6:
        return f'{ft} ft'
    if ft == 0:
        return f'{rem:g} in'
    return f'{ft} ft {rem:g} in'


def frac(x):
    """23.875 -> '23 7/8', 24.0 -> '24'."""
    whole = int(math.floor(x + 1e-9))
    rem = x - whole
    for den in (2, 4, 8, 16):
        k = round(rem * den)
        if abs(rem - k / den) < 1e-6:
            return f'{whole}' if k == 0 else (f'{k}/{den}' if whole == 0 else f'{whole} {k}/{den}')
    return f'{x:g}'


# ------------------------------------------------------------------ beds
beds = OrderedDict()
for b in bodies:
    c = b['component']
    if c.startswith('Bed ') and c != 'Bed Lumber':
        bd = beds.setdefault(c, {'sides': [], 'ends': [], 'posts': [], 'sills': [], 'stakes': [], 'bodies': []})
        bd['bodies'].append(b)
        n = b['body']
        if n.startswith('Side'):
            bd['sides'].append(b)
        elif n.startswith('End'):
            bd['ends'].append(b)
        elif 'sill' in n.lower():
            bd['sills'].append(b)        # "2x4 sill": flat on grade along the bed centreline, the arch foot sits on it
        elif 'stake' in n.lower():
            bd['stakes'].append(b)       # "2x4 stake": one at each end of a sill
        elif 'post' in n.lower():
            bd['posts'].append(b)

def is_flat(p):
    """Flat posts show their 3.5 in face to the side board and are 1.5 in across the bed; edge-on corner posts are 3.5 in across."""
    return (p['max'][0] - p['min'][0]) < 2.5


def kind(p):
    """'trellis' (Trellis_Post_Length, holds the arch near its crown), 'joint' (a 2x8 offcut flat behind a side-board seam),
    'mid' (flat mid-span stake) or 'corner' (edge-on, on grade)."""
    n = p['body'].lower()
    if 'trellis' in n:
        return 'trellis'
    if 'joint' in n:
        return 'joint'
    if 'mid' in n or p['min'][2] < -1e-6:
        return 'mid'
    return 'corner'


def is_mid(p):
    return kind(p) == 'mid'


all_posts = [p for bd in beds.values() for p in bd['posts']]
first_corner = next(p for p in all_posts if kind(p) == 'corner')
first_mid = next((p for p in all_posts if kind(p) == 'mid'), None)
first_trellis = next((p for p in all_posts if kind(p) == 'trellis'), None)
first_joint = next((p for p in all_posts if kind(p) == 'joint'), None)
PT, PW, POST_H = first_corner['dims_in']   # 1.5, 3.5, 14.5 for a 2x4 corner post
POST_NOM = {(1.5, 3.5): '2x4', (3.5, 3.5): '4x4', (1.5, 5.5): '2x6'}.get((round(PT, 2), round(PW, 2)), f'{PT:g}x{PW:g}')
MID_LEN = first_mid['dims_in'][2] if first_mid else POST_H     # 24 in: the Mid_Post_Length parameter
EMBED_IN = -first_mid['min'][2] if first_mid else 0.0           # 9.5 in of each mid-span post below grade
TRELLIS_LEN = first_trellis['dims_in'][2] if first_trellis else (TRELLIS_LEN or 0.0)   # 96 in: Trellis_Post_Length, an uncut 8 ft stick
TRELLIS_EMBED = -first_trellis['min'][2] if first_trellis else EMBED_IN                 # 20 in: Trellis_Post_Embed
TRELLIS_ABOVE = TRELLIS_LEN - TRELLIS_EMBED                     # 76 in of each trellis post above grade
JOINT_T, JOINT_W, JOINT_LEN = first_joint['dims_in'] if first_joint else (T, BOARD_W, MID_LEN)   # 1.5 x 7.25 x 24: a 2x8 offcut lying flat behind a seam
JOINT_NOM = nominal(JOINT_W)                                    # 2x8: the joint posts are offcuts of the wall boards
JOINT_EMBED = -first_joint['min'][2] if first_joint else EMBED_IN   # 9.5 in of each joint post below grade, like a mid-span post
JOINT_OFF = 1.75            # in from the seam to each screw into a joint post: two per board end, so four per course where two boards meet
all_sills = [x for bd in beds.values() for x in bd['sills']]
all_stakes = [x for bd in beds.values() for x in bd['stakes']]
SILL_LEN = all_sills[0]['dims_in'][2] if all_sills else 0.0            # 60.5 in: the panel width, between the stakes
STAKE_LEN = all_stakes[0]['dims_in'][2] if all_stakes else MID_LEN      # 24 in: the same cut as a mid-span post
STAKE_EMBED = -all_stakes[0]['min'][2] if all_stakes else 0.0           # 10.5 in in the ground
STAKE_ABOVE = STAKE_LEN - STAKE_EMBED                                   # 13.5 in above grade: Stake_Above_Sill plus the sill

bed_rows = []
for name, bd in sorted(beds.items(), key=lambda kv: kv[0]):
    letter = name.split(' ')[1]
    sides_ymax = max(b['max'][1] for b in bd['sides'])
    sides_ymin = min(b['min'][1] for b in bd['sides'])
    L = sides_ymax - sides_ymin                              # the wall runs the bed's full length even when each course is two boards
    E = max(bd['ends'][0]['dims_in'])
    corners = [p for p in bd['posts'] if kind(p) == 'corner']
    mids = [p for p in bd['posts'] if kind(p) == 'mid']
    joints = [p for p in bd['posts'] if kind(p) == 'joint']  # 2x8 offcuts flat against the wall behind the seams where two side boards meet
    trellis = [p for p in bd['posts'] if kind(p) == 'trellis']
    # side pieces: lengths per course from the near end, and the seams between them (both walls are cut alike)
    side_pieces = Counter(round(max(b['dims_in']), 3) for b in bd['sides'])
    x_east = max(b['max'][0] for b in bd['sides'])
    side_layout = OrderedDict()
    seams_by_course = {}
    for b in sorted(bd['sides'], key=lambda b: (b['min'][2], -b['max'][1])):
        course = int(round(b['min'][2] / BOARD_W)) + 1
        if abs(b['max'][0] - x_east) < 1e-3:
            side_layout.setdefault(course, []).append(round(max(b['dims_in']), 3))
        if b['max'][1] < sides_ymax - 1e-3:
            seams_by_course.setdefault(course, set()).add(round(sides_ymax - b['max'][1], 3))
    side_seams = sorted({x for ss in seams_by_course.values() for x in ss})
    anchors = bd['sills'] + bd['stakes']
    H = COURSES * BOARD_W
    W = E + 2 * T
    n_joint = len(joints)
    n_posts = len(bd['posts']) - n_joint                 # 2x4 posts; the joint posts are 2x8 offcuts and are counted apart
    n_mid = sum(1 for p in bd['posts'] if is_flat(p) and kind(p) != 'joint')   # mid-span positions (2.5 in screws)
    n_mid_plain = len(mids)
    n_tr_corner = sum(1 for p in trellis if not is_flat(p))
    n_tr_flat = len(trellis) - n_tr_corner
    xc_bed = (min(b['min'][0] for b in bd['bodies']) + max(b['max'][0] for b in bd['bodies'])) / 2

    def where(p):
        side = 'west' if (p['min'][0] + p['max'][0]) / 2 < xc_bed else 'east'
        dist = -(p['min'][1] + p['max'][1]) / 2
        if is_flat(p):
            return f'{side} wall, {dist:.0f} in from the near end'
        return f"{side} corner at the {'near' if dist < L / 2 else 'far'} end"
    trellis_sorted = sorted(trellis, key=lambda p: (-(p['min'][1] + p['max'][1]) / 2, p['min'][0]))
    trellis_where = [where(p) for p in trellis_sorted]
    trellis_pos = [((p['min'][1] + p['max'][1]) / 2, where(p)) for p in trellis_sorted]
    xs = [v for b in bd['bodies'] for v in (b['min'][0], b['max'][0])]
    ys = [v for b in bd['bodies'] for v in (b['min'][1], b['max'][1])]
    inner_L = L - 2 * T
    # posts, sills and stakes displace soil only above grade and below the wall top

    def wood_vol(Hh):
        return sum((p['max'][0] - p['min'][0]) * (p['max'][1] - p['min'][1]) * max(0.0, min(p['max'][2], Hh) - max(p['min'][2], 0.0))
                   for p in bd['posts'] + anchors)
    soil_in3 = E * inner_L * H - wood_vol(H)
    H_alt = COURSES * ALT_BOARD_W
    soil_alt_in3 = E * inner_L * H_alt - wood_vol(H_alt)
    mass = sum(b['mass_kg'] or 0 for b in bd['bodies'])
    posts_per_side = 2 + (n_mid + n_joint) // 2
    # screws, per bed
    corner_side_screws = COURSES * 4 * SCREWS_PER_JOINT       # 3 in, side boards into the corner post edges
    mid_side_screws = COURSES * n_mid * SCREWS_PER_JOINT      # 2.5 in, side boards into the mid-span post faces
    joint_screws = 0                                          # 2.5 in, side boards into the joint post faces: two per board end where two boards meet, the usual pair where one runs past
    for p in joints:
        yc = round(sides_ymax - (p['min'][1] + p['max'][1]) / 2, 3)
        for c in range(1, COURSES + 1):
            joint_screws += 2 * SCREWS_PER_JOINT if any(abs(x - yc) < 0.01 for x in seams_by_course.get(c, ())) else SCREWS_PER_JOINT
    end_screws = COURSES * 4 * SCREWS_PER_JOINT               # 2.5 in, end boards into the corner post faces
    tie_screws = COURSES * 4 * TIES_PER_CORNER                # 3 in, corner ties into end grain
    anchor_screws = STAKE_SILL_SCREWS * len(bd['stakes'])      # 3 in, through each arch-foot stake into the sill's end grain
    panel_screws = (PANEL_SCREWS_PER_POST * len(trellis) + PANEL_SCREWS_PER_STAKE * len(bd['stakes'])
                    + PANEL_SCREWS_PER_SILL * len(bd['sills']))  # 1.25 in with washers: hog-wire panel to the post, stakes and sill
    centers = sorted({abs(round((p['min'][1] + p['max'][1]) / 2, 2)) for p in bd['posts']})
    mid_centers = sorted({abs(round((p['min'][1] + p['max'][1]) / 2, 2)) for p in mids})
    joint_centers = sorted({abs(round((p['min'][1] + p['max'][1]) / 2, 2)) for p in joints})
    bed_rows.append({
        'name': name, 'letter': letter, 'L': L, 'W': W, 'E': E, 'H': H, 'H_alt': H_alt,
        'inner_L': inner_L, 'n_posts': n_posts, 'n_mid': n_mid, 'posts_per_side': posts_per_side,
        'xmin': min(xs), 'xmax': max(xs), 'ymin': min(ys), 'ymax': max(ys),
        'soil_ft3': soil_in3 / 1728, 'soil_alt_ft3': soil_alt_in3 / 1728,
        'mass_lb': mass * KG2LB,
        'corner_side_screws': corner_side_screws, 'mid_side_screws': mid_side_screws, 'joint_screws': joint_screws,
        'end_screws': end_screws, 'tie_screws': tie_screws,
        'panel_screws': panel_screws, 'anchor_screws': anchor_screws,
        'screws_3': corner_side_screws + tie_screws + anchor_screws, 'screws_25': mid_side_screws + end_screws + joint_screws, 'screws_125': panel_screws,
        'n_joint': n_joint, 'joints': joints, 'joint_centers': joint_centers, 'mid_centers': mid_centers,
        'side_pieces': side_pieces, 'side_layout': side_layout, 'side_seams': side_seams, 'seams_by_course': seams_by_course,
        'n_mid_plain': n_mid_plain, 'n_trellis': len(trellis), 'n_tr_corner': n_tr_corner, 'n_tr_flat': n_tr_flat,
        'n_sills': len(bd['sills']), 'n_stakes': len(bd['stakes']), 'sills': bd['sills'], 'stakes': bd['stakes'], 'anchors': anchors,
        'trellis_where': trellis_where, 'trellis_pos': trellis_pos,
        'post_spacing': max(b - a for a, b in zip(centers, centers[1:])) if len(centers) > 1 else 0.0,   # the longest centre-to-centre gap along a wall
        'post_centers': centers,
        'n_sides': len(bd['sides']), 'n_ends': len(bd['ends']),
        'posts': bd['posts'],
    })

# ------------------------------------------------------------------ lumber stock: what to buy, bed by bed
# The pieces each bed needs, then the cheapest set of store-length sticks that yields them (scripts/cutstock.py).
# Side boards are whole sticks where a stock length fits; a two-board wall's short piece is cut from a stick whose offcut becomes a joint post.
# End boards may run END_TOL short so two clear the kerf on one 8 ft board; posts may run a little short.
side_stock = Counter()
post_pieces = 0
mid_post_pieces = 0
trellis_pieces = 0
sill_pieces = 0
stake_pieces = 0
joint_pieces = 0
for r in bed_rows:
    for Lp, n in r['side_pieces'].items():
        side_stock[(NOM, Lp)] += n
    joint_pieces += r['n_joint']
    post_pieces += r['n_posts']
    mid_post_pieces += r['n_mid_plain']
    trellis_pieces += r['n_trellis']
    sill_pieces += r['n_sills']
    stake_pieces += r['n_stakes']
corner_pieces = post_pieces - mid_post_pieces - trellis_pieces
trellis_uncut = TRELLIS_LEN in STOCK_IN_PRICES[POST_NOM]      # the trellis post is an uncut stock stick
mid_embed_cut = MID_LEN - COURSES * BOARD_W                    # 9.5 in of a full-length mid-span post below grade


def board_pieces(r):
    """The 2x8 pieces of one bed: side pieces by length (whole sticks where a stock length fits), end boards, and the joint posts,
    which are offcuts of the same stock and may run POST_TOL short like a mid-span post."""
    ps = [cutstock.Piece(f'side{Lp:g}', 'side board', Lp, n, short='side') for Lp, n in sorted(r['side_pieces'].items(), reverse=True)]
    ps.append(cutstock.Piece('end', 'end board', r['E'], r['n_ends'], min_len=r['E'] - END_TOL, short='end'))
    if r['n_joint']:
        ps.append(cutstock.Piece('joint', 'joint post', JOINT_LEN, r['n_joint'], min_len=JOINT_LEN - POST_TOL, short='joint'))
    return ps


def post_pieces_of(r):
    return [cutstock.Piece('corner', 'corner post', POST_H, 4 - r['n_tr_corner'], min_len=POST_H - CORNER_TOL, short='corner'),
            cutstock.Piece('mid', 'mid-span post', MID_LEN, r['n_mid_plain'], min_len=MID_LEN - POST_TOL, short='mid'),
            cutstock.Piece('trellis', 'trellis post', TRELLIS_LEN, r['n_trellis'], short='trellis'),
            cutstock.Piece('sill', 'arch sill', SILL_LEN, r['n_sills'], short='sill'),
            cutstock.Piece('stake', 'arch stake', STAKE_LEN, r['n_stakes'], min_len=STAKE_LEN - POST_TOL, short='stake')]


def options_for(pieces, nom):
    return [o for o in cutstock.single_length_options(pieces, STOCK_IN_PRICES[nom]) if o['length'] >= OPTION_MIN_FT * 12]


def plan_key(plan):
    return sorted((g['stock'], g['count'], tuple((c['key'], c['n'], round(c['len'], 4)) for c in g['cuts'])) for g in plan['sticks'])


def same_cutting(a, b):
    return plan_key(a) == plan_key(b)


def priced_as(plan, nom):
    """The same sticks at another nominal size's prices."""
    return round(sum(STOCK_IN_PRICES[nom][g['stock']] * g['count'] for g in plan['sticks']), 2)


for r in bed_rows:
    bp, pp = board_pieces(r), post_pieces_of(r)
    r['plan_boards'] = cutstock.solve(bp, STOCK_IN_PRICES[NOM])
    r['plan_boards_alt'] = cutstock.solve(bp, STOCK_IN_PRICES[ALT_NOM])
    r['plan_posts'] = cutstock.solve(pp, STOCK_IN_PRICES[POST_NOM])
    r['opts_boards'] = options_for(bp, NOM)
    r['opts_posts'] = options_for(pp, POST_NOM)
    r['board_cost_alt'] = priced_as(r['plan_boards'], ALT_NOM)        # the same cutting at the 2x10 prices
    r['alt_same_cutting'] = same_cutting(r['plan_boards'], r['plan_boards_alt'])
    r['lumber_cost'] = round(r['plan_boards']['cost'] + r['plan_posts']['cost'], 2)
    r['lumber_cost_alt'] = round(r['board_cost_alt'] + r['plan_posts']['cost'], 2)
    r['lumber_sticks'] = r['plan_boards']['n_sticks'] + r['plan_posts']['n_sticks']
    r['board_cuts'] = cutstock.piece_cuts(r['plan_boards'])
    r['post_cuts'] = cutstock.piece_cuts(r['plan_posts'])

# all four beds cut together: sticks shared between beds can save a little over the per-bed plans
_boards_all = OrderedDict()
for r in bed_rows:
    for p in board_pieces(r):
        k = (p.key, p.length)
        if k in _boards_all:
            _boards_all[k].qty += p.qty
        else:
            _boards_all[k] = cutstock.Piece(p.key if p.key.startswith('side') else f'{p.key}{p.length:g}', p.label, p.length, p.qty, min_len=p.min_len, short=p.short)
_n24 = mid_post_pieces + (stake_pieces if abs(STAKE_LEN - MID_LEN) < 1e-6 else 0)
_posts_all = [cutstock.Piece('corner', 'corner post', POST_H, corner_pieces, min_len=POST_H - CORNER_TOL, short='corner'),
              cutstock.Piece('post24', 'mid or stake post' if _n24 > mid_post_pieces else 'mid-span post', MID_LEN, _n24, min_len=MID_LEN - POST_TOL, short='post'),
              cutstock.Piece('trellis', 'trellis post', TRELLIS_LEN, trellis_pieces, short='trellis'),
              cutstock.Piece('sill', 'arch sill', SILL_LEN, sill_pieces, short='sill')]
if abs(STAKE_LEN - MID_LEN) >= 1e-6:
    _posts_all.append(cutstock.Piece('stake', 'arch stake', STAKE_LEN, stake_pieces, min_len=STAKE_LEN - POST_TOL, short='stake'))
combined_boards = cutstock.solve(sorted(_boards_all.values(), key=lambda p: -p.length), STOCK_IN_PRICES[NOM])
combined_posts = cutstock.solve(_posts_all, STOCK_IN_PRICES[POST_NOM])
per_bed_board_cost = round(sum(r['plan_boards']['cost'] for r in bed_rows), 2)
per_bed_post_cost = round(sum(r['plan_posts']['cost'] for r in bed_rows), 2)
combined_cost = round(combined_boards['cost'] + combined_posts['cost'], 2)
combined_saving = round(per_bed_board_cost + per_bed_post_cost - combined_cost, 2)
combined_sticks = combined_boards['n_sticks'] + combined_posts['n_sticks']

# shopping-list lumber rows: the per-bed plans added up, so they reconcile with the checklists
stock_rows = []   # {'nom', 'ft', 'qty', 'price', 'price_alt', 'beds': {letter: n}, 'use': text}
for nom_key, pk in ((NOM, 'plan_boards'), (POST_NOM, 'plan_posts')):
    by = OrderedDict()
    for r in bed_rows:
        for L_in, n in sorted(r[pk]['by_length'].items()):
            by.setdefault(L_in, OrderedDict())[r['letter']] = n
    for L_in in sorted(by):
        uses = []
        for r in bed_rows:
            gs = [g for g in r[pk]['sticks'] if g['stock'] == L_in]
            if gs:
                uses.append(f"Bed {r['letter']} " + ', '.join(f"{g['count']}: {cutstock.stick_text(g)}" for g in gs))
        stock_rows.append({'nom': nom_key, 'ft': int(L_in // 12), 'qty': sum(by[L_in].values()), 'price': STOCK_IN_PRICES[nom_key][L_in],
                           'price_alt': STOCK_IN_PRICES[ALT_NOM][L_in] if nom_key == NOM else None, 'beds': by[L_in], 'use': '; '.join(uses)})
lumber_cost = round(sum(x['price'] * x['qty'] for x in stock_rows), 2)
lumber_cost_alt = round(sum((x['price_alt'] if x['price_alt'] is not None else x['price']) * x['qty'] for x in stock_rows), 2)
total_2x_boards = sum(x['qty'] for x in stock_rows if x['nom'] == NOM)
post_sticks = sum(x['qty'] for x in stock_rows if x['nom'] == POST_NOM)
total_lin_ft_2x = sum(x['ft'] * x['qty'] for x in stock_rows if x['nom'] == NOM)
lumber_list = [{'item': f"{x['nom']} x {x['ft']} ft", 'qty': x['qty'], 'price': x['price'], 'price_alt': x['price_alt'], 'use': x['use']} for x in stock_rows]
board_lengths_txt = ', '.join(f'{ft}' for ft in sorted(STOCK_PRICES[NOM])) + ' ft'
post_lengths_txt = ', '.join(f'{ft}' for ft in sorted(STOCK_PRICES[POST_NOM])) + ' ft'


def beds_text(letters, capital=False):
    """'Bed C' or 'beds C and D'."""
    letters = list(letters)
    if not letters:
        return ''
    t = f'Bed {letters[0]}' if len(letters) == 1 else 'beds ' + ', '.join(letters[:-1]) + ' and ' + letters[-1]
    return t[0].upper() + t[1:] if capital else t


split_beds = [r['letter'] for r in bed_rows if r['side_seams']]
whole_beds = [r['letter'] for r in bed_rows if not r['side_seams']]
staggered_beds = [r['letter'] for r in bed_rows if len({tuple(v) for v in r['side_layout'].values()}) > 1]
short_sides = sorted({Lp for r in bed_rows for Lp in r['side_pieces'] if Lp not in STOCK_IN_PRICES[NOM]})
side_stock_ft = sorted({g['stock'] / 12 for r in bed_rows if r['side_seams'] for g in r['plan_boards']['sticks'] for c in g['cuts'] if c['key'].startswith('side')})
side_stock_txt = ' and '.join(f'{x:g} ft' for x in side_stock_ft)
# does the stick that yields a short side piece also yield a joint post, as intended?
offcut_joints = any(any(c['key'] == 'joint' for c in g['cuts']) for r in bed_rows for g in r['plan_boards']['sticks']
                    if any(c['key'].startswith('side') and c['len'] not in STOCK_IN_PRICES[NOM] for c in g['cuts']))


def layout_txt(r):
    """'course 1: 96 + 72 in, course 2: 72 + 96 in'."""
    return ', '.join(f"course {c}: {' + '.join(f'{x:g}' for x in ls)} in" for c, ls in r['side_layout'].items())


def sticks_txt(n):
    return f"{n} stick{'' if n == 1 else 's'}"


short_side_beds = [r['letter'] for r in bed_rows if any(Lp not in STOCK_IN_PRICES[NOM] for Lp in r['side_pieces'])]


side_scheme_txt = ((f'{beds_text(whole_beds, True)} use one board per course. ' if whole_beds else '')
                   + (f'{beds_text(split_beds, True)} use two boards per course from {side_stock_txt} stock ('
                      + '; '.join(f"Bed {r['letter']} {layout_txt(r)}" for r in bed_rows if r['side_seams'])
                      + f'), meeting over {JOINT_NOM} joint posts: {JOINT_LEN:g} in pieces of {JOINT_NOM} lying flat with the {frac(JOINT_W)} in face against the inside of the wall, '
                      + f'{JOINT_EMBED:g} in in the ground like a mid-span post.'
                      + (f" {beds_text(short_side_beds, True)}'s joint posts are the offcuts of {'its' if len(short_side_beds) == 1 else 'their'} "
                         f"{' and '.join(f'{x:g} in' for x in short_sides)} side pieces." if offcut_joints and short_side_beds else '') if split_beds else '')
                   + (f" {beds_text(staggered_beds, True)} stagger{'s' if len(staggered_beds) == 1 else ''} the seams course to course, so no joint runs the full height of the wall." if staggered_beds else ''))
side_stock_note = (f'no 14 ft, so {beds_text(split_beds)} use two boards per course from {side_stock_txt} stock, joined over {JOINT_NOM} joint posts' if split_beds else 'no 14 ft')
cut_rule_txt = ('Side boards are whole sticks'
                + (f"; the {' and '.join(f'{x:g} in' for x in short_sides)} side pieces are cut from {side_stock_txt} boards and the offcut becomes a {JOINT_NOM} joint post, "
                   f"cut up to {POST_TOL:g} in short so both clear the kerf" if short_sides and offcut_joints else
                   f"; the {' and '.join(f'{x:g} in' for x in short_sides)} side pieces are cut from {side_stock_txt} boards" if short_sides else '')
                + f'. End boards may be cut up to {frac(END_TOL)} in short so two 48 in pieces clear the saw kerf on one 8 ft board; '
                f'corner posts may run up to {frac(CORNER_TOL)} in short of the wall height and mid-span posts, joint posts and arch stakes up to {POST_TOL:g} in short, '
                f'which only takes them a little less deep into the ground, when that lets one more piece fit a stick.')
lumber_mass_lb = sum(r['mass_lb'] for r in bed_rows)
lumber_mass_alt_lb = lumber_mass_lb * ALT_BOARD_W / BOARD_W
screws_3 = sum(r['screws_3'] for r in bed_rows)
screws_25 = sum(r['screws_25'] for r in bed_rows)
screws_125 = sum(r['screws_125'] for r in bed_rows)
screws_total = screws_3 + screws_25 + screws_125
tot_corner_side = sum(r['corner_side_screws'] for r in bed_rows)
tot_mid_side = sum(r['mid_side_screws'] for r in bed_rows)
tot_end = sum(r['end_screws'] for r in bed_rows)
tot_tie = sum(r['tie_screws'] for r in bed_rows)
tot_joint = sum(r['joint_screws'] for r in bed_rows)
tot_panel = sum(r['panel_screws'] for r in bed_rows)
tot_anchor = sum(r['anchor_screws'] for r in bed_rows)
tot_tr_corner = sum(r['n_tr_corner'] for r in bed_rows)
buy_3 = buy_text(screws_3, 3.0)
buy_25 = buy_text(screws_25, 2.5)

# ------------------------------------------------------------------ pavers
paver_bodies = [b for b in bodies if (b['material'] or '').startswith('Concrete')]
paver_groups = OrderedDict()
PAVER_LABEL = {
    '12x12 Paver': 'Walkway along the top edge (2 rows, 15 in pitch)',
    'First Bed Path': 'Path between Bed D (16 ft) and Bed C (14 ft), 18 in pitch',
    'Second Bed Path': 'Path between Bed C (14 ft) and Bed B (12 ft), 18 in pitch',
    'Third Paver Path': 'Path between Bed B (12 ft) and Bed A (10 ft), 18 in pitch',
    'Fourth Paver Path': 'Path west of Bed A (10 ft), 18 in pitch',
}
for b in paver_bodies:
    g = paver_groups.setdefault(b['component'], {'n': 0, 'mass': 0.0, 'dims': b['dims_in']})
    g['n'] += 1
    g['mass'] += b['mass_kg'] or 0
paver_n = len(paver_bodies)
paver_dims = paver_bodies[0]['dims_in']
paver_each_lb = (paver_bodies[0]['mass_kg'] or 0) * KG2LB
paver_total_lb = sum(b['mass_kg'] or 0 for b in paver_bodies) * KG2LB
paver_area_ft2 = paver_n * (paver_dims[1] * paver_dims[2]) / 144
base_depth_in = 2.0
base_ft3 = paver_area_ft2 * base_depth_in / 12
base_bags = math.ceil(base_ft3 / 0.5)

# ------------------------------------------------------------------ arches
arch_comps = OrderedDict()
for b in bodies:
    if b['component'].startswith('Arch '):
        a = arch_comps.setdefault(b['component'], {'wires': 0, 'span': 0, 'height': 0, 'mass': 0.0,
                                                   'xmin': 1e9, 'xmax': -1e9, 'ymin': 1e9, 'ymax': -1e9, 'zmin': 1e9, 'zmax': -1e9})
        a['wires'] += 1
        a['span'] = max(a['span'], b['dims_in'][1])
        a['height'] = max(a['height'], b['dims_in'][2])
        a['mass'] += b['mass_kg'] or 0
        a['xmin'] = min(a['xmin'], b['min'][0]); a['xmax'] = max(a['xmax'], b['max'][0])
        a['ymin'] = min(a['ymin'], b['min'][1]); a['ymax'] = max(a['ymax'], b['max'][1])
        a['zmin'] = min(a['zmin'], b['min'][2]); a['zmax'] = max(a['zmax'], b['max'][2])
ARCH_R = HOG_ARC / math.pi
for k, a in arch_comps.items():
    a['chord'] = a['xmax'] - a['xmin'] - 2 * WIRE_R      # between the leg centerlines
    a['feet'] = a['zmin']                                 # the panel's bottom wire: on the sill tops, Board_Thickness above grade
    a['crown'] = a['zmax'] - WIRE_R
    a['xc'] = (a['xmin'] + a['xmax']) / 2
    a['spring'] = a['feet'] + HOG_LEG                     # where the straight leg ends and the curve starts

    def h(x, a=a):
        """Height of the panel above grade at x, on the curved part."""
        dx = abs(x - a['xc'])
        return a['spring'] + math.sqrt(max(ARCH_R ** 2 - dx ** 2, 0.0))
    a['h'] = h
    under = sorted((r for r in bed_rows if r['xmax'] > a['xmin'] and r['xmin'] < a['xmax']), key=lambda r: r['xmin'])
    a['beds'] = under
    a['walk'] = None
    for b1, b2 in zip(under, under[1:]):
        if b2['xmin'] > b1['xmax']:
            x0, x1 = b1['xmax'], b2['xmin']
            a['walk'] = {'x0': x0, 'x1': x1, 'bed0': b1['letter'], 'bed1': b2['letter'], 'width': x1 - x0,
                         'h0': h(x0), 'hc': h((x0 + x1) / 2), 'h1': h(x1)}
            break
    # which trellis posts hold this arch (centerline under the panel), and where the panel crosses each post's face
    carried, cross = [], []
    for r in under:
        ws = [w for (yc, w) in r['trellis_pos'] if a['ymin'] - 2 <= yc <= a['ymax'] + 2]
        if ws:
            carried.append(f"Bed {r['letter']}: " + ' + '.join(ws))
        for p in r['posts']:
            yc = (p['min'][1] + p['max'][1]) / 2
            if kind(p) == 'trellis' and a['ymin'] - 2 <= yc <= a['ymax'] + 2:
                x_in, x_out = sorted((p['min'][0], p['max'][0]), key=lambda x: abs(x - a['xc']))
                cross.append({'bed': r['letter'], 'x0': p['min'][0], 'x1': p['max'][0], 'z_in': h(x_in), 'z_out': h(x_out)})
    a['posts'] = '; '.join(carried)
    a['cross'] = cross
    a['sills'] = [x for r in under for x in r['sills'] if x['max'][1] >= a['ymin'] - 2 and x['min'][1] <= a['ymax'] + 2]
    a['stakes'] = [x for r in under for x in r['stakes'] if x['max'][1] >= a['ymin'] - 2 and x['min'][1] <= a['ymax'] + 2]
n_arches = len(arch_comps)
arch_wire_len = 2 * HOG_LEG + HOG_ARC
arch_leg_16ft = (HOGWIRE_LEN - HOG_ARC) / 2
ARCH_BETWEEN = {'Arch AB': 'the centrelines of Bed A (10 ft) and Bed B (12 ft)', 'Arch BC': 'Bed B (12 ft) and Bed C (14 ft)'}
first_arch = list(arch_comps.values())[0]
cross0 = first_arch['cross']
CROSS_LO = min(c['z_out'] for c in cross0) if cross0 else 0.0     # where the panel enters a post's outer edge, above grade
CROSS_HI = max(c['z_in'] for c in cross0) if cross0 else 0.0      # where it leaves the inner edge
POST_TOP_ABOVE_CROSS = TRELLIS_ABOVE - CROSS_LO                   # post top above the crossing


def headroom(a):
    w = a['walk']
    if not w:
        return ''
    return f"{w['hc']:.0f} in at the center, {w['h0']:.0f} in at the Bed {w['bed0']} wall, {w['h1']:.0f} in at the Bed {w['bed1']} wall"


arch_paras = [
    f"Arch AB is one {HOGWIRE_LEN/12:g} ft panel bent over the {first_arch['chord']:.0f} in between the centrelines of Bed A and Bed B, "
    f"with its feet on {POST_NOM} sills lying on the ground inside the beds, {first_arch['feet']:g} in above grade. "
    f"The {ARCH_R:.1f} in radius top uses {HOG_ARC:.0f} in of the panel, so the straight legs are {HOG_LEG:.1f} in (the Fusion parameter Hogwire_height derives from the panel length) "
    f"and the crown is {first_arch['crown']:.0f} in above grade, level with the post tops. Standing the arch on the ground instead of the wall tops drops it "
    f"{COURSES * BOARD_W - first_arch['feet']:g} in, so that much of each leg ends up in the bed soil once the beds are filled. "
    f"Walkway headroom: {headroom(first_arch)}.",
    f"Two of the beds' own corner posts hold the arch up: the inside corner post at the near end of each bed (Bed A's east corner, Bed B's west corner), "
    f"which are uncut {ft_in(TRELLIS_LEN)} {POST_NOM}s set {TRELLIS_EMBED:g} in into the ground, {TRELLIS_ABOVE:g} in above grade. "
    f"The panel's near edge wire runs up the {PW:g} in face of each post that looks down the bed and crosses it between {CROSS_LO:.0f} and {CROSS_HI:.0f} in above grade, "
    f"so the post top stands {POST_TOP_ABOVE_CROSS:.0f} in above the crossing. {PANEL_SCREWS_PER_POST} screws with fender washers there, one each side of the wire, trap it. "
    f"The posts keep the arch upright along the beds and take the wind; the sills and stakes hold its feet.",
    f"Each foot: a {SILL_LEN:g} in {POST_NOM} sill lies flat on grade along the bed centreline with a {STAKE_LEN:g} in {POST_NOM} stake at each end, "
    f"driven {STAKE_EMBED:g} in and standing {STAKE_ABOVE - first_arch['feet']:g} in above the sill. The near stake sits against the end board like a corner post; "
    f"the far one is {-first_arch['ymin']:g} in down the bed. The panel's bottom wire lies along the sill top and its edge wires rise against the stake faces: "
    f"{PANEL_SCREWS_PER_SILL} screws with washers along the sill, {PANEL_SCREWS_PER_STAKE} on each stake, and {STAKE_SILL_SCREWS} x #9 3 in through each stake into the sill's end grain. "
    f"Set the posts and stakes before the walls go on (the near stake and the trellis post both stand against the end board), screw the sills to the stakes, "
    f"bend the panel in and fasten it, then fill the beds.",
]
arch_note = (f"The model wires are 1/2 in for visibility; real panels are 4-gauge and weigh about 35 to 40 lb each, so ignore the model's steel mass. "
             f"A 48 or 50 in wide panel makes the tunnel that much shorter along the walkway; shorten the sills to match. "
             f"Arch BC (between beds B and C at the far end) is still modeled on the old wall-top scheme and is hidden (parked) in the model: "
             f"the same bed-centre scheme there needs one more {ft_in(TRELLIS_LEN)} post on Bed C's west wall opposite Bed B's far corner. "
             f"There is no arch between beds C and D.")

# ------------------------------------------------------------------ low-tunnel hoops (assembly Garden Hoops, over Bed C since 2026-11-06)
HOOP_LEG, HOOP_ARC = 36.0, 64.33     # the Hoop part's Sketch1: two 36 in straight legs and a 64.33 in semicircle, 1 in tube
hoop_len = 2 * HOOP_LEG + HOOP_ARC
hoop_bodies = sorted([b for b in bodies if b['component'] == 'Hoop'], key=lambda b: -(b['min'][1] + b['max'][1]))
n_hoops = len(hoop_bodies)
HOOPS_SAVED = True                   # the Fusion document was saved on 2026-11-06 with the hoop assembly in it
if n_hoops:
    h0 = hoop_bodies[0]
    hoop_w = h0['max'][0] - h0['min'][0]              # outside width: 40 in between the leg centrelines + the tube
    hoop_h = h0['max'][2]                               # top of the tube above grade
    hoop_cx = (h0['min'][0] + h0['max'][0]) / 2
    hoop_ys = [(b['min'][1] + b['max'][1]) / 2 for b in hoop_bodies]   # near end first
    hoop_pitch = params['Hoop_Pitch']['value_in'] if 'Hoop_Pitch' in params else ((hoop_ys[0] - hoop_ys[-1]) / (n_hoops - 1) if n_hoops > 1 else 0.0)
    hoop_bed = next((r for r in bed_rows if r['xmin'] <= hoop_cx <= r['xmax']), None)
    hoop_bed_letter = hoop_bed['letter'] if hoop_bed else '?'
    hoop_near_gap = (hoop_bed['ymax'] - T) - hoop_ys[0] if hoop_bed else 0.0     # first hoop to the near end board's inside face
    hoop_far_gap = hoop_ys[-1] - (hoop_bed['ymin'] + T) if hoop_bed else 0.0     # last hoop to the far end board
    hoop_wall_gap = ((hoop_bed['W'] - 2 * T) - hoop_w) / 2 if hoop_bed else 0.0  # tube outside to each side wall's inside face
    hoop_in_soil = hoop_bed['H'] if hoop_bed else 0.0                             # the legs reach grade, so this much is in the soil
    hoop_leg_up = HOOP_LEG - hoop_in_soil                                          # straight leg above the soil
    hoop_tube_ft = n_hoops * hoop_len / 12
    hoop_cover_w = HOOP_ARC + 2 * hoop_leg_up                                      # over the hoop from soil to soil, if a cover goes on
    hoop_cover_l = (hoop_bed['inner_L'] if hoop_bed else hoop_ys[0] - hoop_ys[-1]) + 2 * hoop_leg_up
    hoop_summary = (f"{n_hoops} over Bed {hoop_bed_letter} ({ft_in(hoop_bed['L']) if hoop_bed else ''}) at {hoop_pitch:g} in pitch, "
                    f"the first and last {hoop_near_gap:g} in inside the end boards")

if n_hoops:
    hoop_paras = [
        f"{n_hoops} hoops of 1 in tube cover Bed {hoop_bed_letter}: the first stands {hoop_near_gap:g} in inside the near end board, the last {hoop_far_gap:g} in inside the far one, "
        f"and they are {hoop_pitch:g} in apart. Each hoop is {hoop_w - 1:.0f} in wide between its legs, {hoop_wall_gap:.1f} in clear of the side walls, with {HOOP_LEG:g} in straight legs "
        f"that go down through the {hoop_in_soil:g} in of soil to grade (set them before the beds are filled, or push them in afterwards) and a {HOOP_ARC:.0f} in semicircular top "
        f"of {HOOP_ARC/math.pi:.0f} in radius; the crown is {hoop_h:.0f} in above grade, {hoop_h - hoop_in_soil:.0f} in above the soil.",
        f"Tube: {hoop_len:.0f} in ({hoop_len/12:.1f} ft) per hoop, {hoop_tube_ft:.0f} ft in all. A 10 ft stick is short, so either bend 12 ft stock or join two pieces with a coupling "
        f"low in one leg. If the tunnel gets a cover, it needs about {hoop_cover_w/12:.0f} ft of width over the hoops and {hoop_cover_l/12:.0f} ft of length to reach the soil at both ends.",
    ]
    hoops_model_note = (f'- 2026-11-06, hoops: the six root-level Garden Hoops occurrences (one seed at the plot edge, a copy over Bed B and the root pattern R-Pattern2) '
                        f'are now an assembly. Component **Garden Hoops** holds one occurrence of the part, renamed **Hoop** (body "1 in tube hoop", visible again), '
                        f'placed over Bed {hoop_bed_letter}\'s centreline {-hoop_ys[0]:g} in from the near end, and a rectangular pattern "Hoops along the bed" along the assembly Y axis '
                        f'driven by the new parameters `Hoop_Count` ({n_hoops}) and `Hoop_Pitch` ({hoop_pitch:g} in). Change either parameter to respace the tunnel.')
else:
    hoop_paras = []
    hoops_model_note = '- No hoops are visible in the model.'
DRIP_SAVED = True                    # the Fusion document was saved again on 2026-11-06 with the drip risers, the 3/4 in main and the end-board holes in it
SPLIT_SAVED = False                  # the two-board sides of beds C and D (2026-11-08) are in the open document but not saved yet
saved_note = ('The Fusion document was saved on 2026-11-06 with the bed-centre arch, sills, stakes, the hoop assembly over Bed C and the drip risers in place.' if HOOPS_SAVED and DRIP_SAVED else
              'The Fusion document was saved on 2026-11-06 with the bed-centre arch, sills, stakes and the hoop assembly over Bed C in place; the drip risers, the 3/4 in main and the holes in the end boards came after that save and are not saved yet.' if HOOPS_SAVED else
              'The Fusion document was saved on 2026-11-06 with the bed-centre arch, sills and stakes in place; the hoop assembly and the drip risers came after that save and are not saved yet.')
if split_beds and not SPLIT_SAVED:
    saved_note += f' The two-board side walls of {beds_text(split_beds)} with their {JOINT_NOM} joint posts (2026-11-08) came after that save and are not saved yet.'
split_model_note = ((f'- 2026-11-08, two-board sides: the side walls of {beds_text(split_beds)} are now two boards per course ('
                     + '; '.join(f"Bed {r['letter']} {layout_txt(r)}" for r in bed_rows if r['side_seams'])
                     + f') with a {JOINT_NOM} joint post behind every seam, done in place by scripts/fusion_split_sides.py: a hidden construction plane and a Split Body at each seam, '
                     f'a "Joint posts" sketch with a two-sided `Joint post extrude` (bodies "2x8 joint post", Courses x Board_Width up and the rest of Mid_Post_Length down), '
                     f'the 2x4 mid posts a joint post replaces removed and the rest moved so the gaps between posts are even, all in the timeline group "Two-board sides". '
                     f'scripts/fusion_build_bed_lumber.py builds the same layout from scratch (SIDE_SPLITS).') if split_beds else '- All side boards are single sticks.')
hoop_mass_note = (f' The model hoops are solid 1 in rod of wrought iron, about {hoop_bodies[0]["mass_kg"] * KG2LB:.0f} lb each; real 1 in EMT weighs about {hoop_len/12*0.67:.0f} lb per hoop.'
                  if n_hoops and hoop_bodies[0]['mass_kg'] else '')

# ------------------------------------------------------------------ drip irrigation (assembly Drip Irrigation, 2026-11-06)
HOLE_DIA = 1.0                 # the "Drip hole cut" through each top far end board (a feature, so not in the extract)
DRIP_STICK = 120.0             # 1/2 in PVC comes in 10 ft sticks
WALL_TOP = COURSES * BOARD_W
riser_paths = sorted({b['path'] for b in bodies if b['component'] == 'Drip riser'})
n_risers = len(riser_paths)
main_bodies = [b for b in bodies if b['component'].startswith('3/4 in main')]
PIPE_ORDER = ['ground', 'lower riser', 'upper riser', 'through wall', 'head']
risers = []
for p in riser_paths:
    parts = {b['body']: b for b in bodies if b['path'] == p}
    tee = parts['3/4 x 1/2 in reducer tee']
    tx, ty, tz = [(tee['min'][i] + tee['max'][i]) / 2 for i in range(3)]
    bed = next((r for r in bed_rows if r['xmin'] - 1 <= tx <= r['xmax'] + 1), None)
    up = parts['1/2 in pipe, upper riser']
    wall = parts['1/2 in pipe, through wall']
    valve = parts['1/2 in ball valve']
    head = parts['1/2 in NPT x 4-port 1/4 in drip head']
    run = next((b for b in main_bodies if 'elbow' not in b['body'] and b['min'][0] - 1 <= tx <= b['max'][0] + 1
                and abs((b['min'][1] + b['max'][1]) / 2 - ty) < 2), None)
    main_y = (run['min'][1] + run['max'][1]) / 2 if run else ty      # the main's axis (the tee's box is pulled toward the bed by its branch hub)
    risers.append({
        'path': p, 'bed': bed['letter'] if bed else '?', 'bed_row': bed,
        'x_off': tx - bed['xmin'] if bed else 0.0,                 # riser axis from the bed's west outside face
        'main_offset': (bed['ymin'] - main_y) if bed else 0.0,     # main axis beyond the far end board's outside face
        'main_depth': -tz,
        'standoff': (bed['ymin'] - (up['min'][1] + up['max'][1]) / 2) if bed else 0.0,
        'through_z': (wall['min'][2] + wall['max'][2]) / 2,
        'valve_z': (valve['min'][2] + valve['max'][2]) / 2,
        'head_top': head['max'][2], 'head_bottom': head['min'][2],
        'clamps': sorted((v['min'][2] + v['max'][2]) / 2 for k, v in parts.items() if 'clamp' in k),
        'pipes': {k[len('1/2 in pipe, '):]: v['dims_in'][2] for k, v in parts.items() if k.startswith('1/2 in pipe')},
        'n_elbows': sum(1 for k in parts if k.startswith('1/2 in elbow')),
        'n_clamps': sum(1 for k in parts if 'clamp' in k),
    })
risers.sort(key=lambda r: r['bed'])
if risers:
    r0 = risers[0]
    drip_pipe_per = sum(r0['pipes'].values())
    drip_pipe_total = sum(sum(r['pipes'].values()) for r in risers)
    drip_pieces = sum(len(r['pipes']) for r in risers)
    drip_sticks = math.ceil((drip_pipe_total + (drip_pieces - 1) * KERF) / DRIP_STICK)
    drip_spare = drip_sticks * DRIP_STICK - drip_pipe_total - (drip_pieces - 1) * KERF
    drip_elbows = sum(r['n_elbows'] for r in risers)
    drip_clamps = sum(r['n_clamps'] for r in risers)
    main_len = sum(b['dims_in'][2] for b in main_bodies if 'elbow' not in b['body'])
    main_elbows = sum(1 for b in main_bodies if 'elbow' in b['body'])
    drip_cuts = ' + '.join(frac(r0['pipes'][k]) for k in PIPE_ORDER if k in r0['pipes'])
    drip_beds = ', '.join(r['bed'] for r in risers)
    drip_hole_up = r0['through_z'] - (COURSES - 1) * BOARD_W      # hole centre above the top board's lower edge
    drip_paras = [
        f"Every bed gets the same riser on the outside of its far end wall, {frac(r0['x_off'])} in from the bed's west outside face (beds {drip_beds}): "
        f"that keeps the hole clear of the edge-on corner post, which reaches {T + PW:g} in in from the side board, and in Bed C keeps the pipe inside the bed clear of the hoop legs. "
        f"From the 3/4 in main, {frac(r0['main_offset'])} in beyond the end board and {frac(r0['main_depth'])} in below grade, a 3/4 x 3/4 x 1/2 reducer tee feeds "
        f"{frac(r0['pipes']['ground'])} in of 1/2 in pipe along the ground, an elbow turning up, {frac(r0['pipes']['lower riser'])} in of pipe up the outside of the wall, the ball valve, "
        f"{frac(r0['pipes']['upper riser'])} in more pipe, an elbow turning into the bed, {frac(r0['pipes']['through wall'])} in of pipe through a {HOLE_DIA:g} in hole, "
        f"an elbow turning up inside the bed, and {frac(r0['pipes']['head'])} in of pipe to the 4-port 1/4 in drip head.",
        f"The hole is centred {frac(r0['through_z'])} in above grade, {frac(drip_hole_up)} in up the top board, so it sits in the middle of that board and the elbows on either side "
        f"of the wall stop 1/4 in short of it; the riser stands {frac(r0['standoff'])} in off the wall. The valve is {frac(r0['valve_z'])} in above grade with its lever pointing west along the wall. "
        f"Two stand-off clamps at {frac(r0['clamps'][0])} and {frac(r0['clamps'][1])} in, each screwed into a single board with two screws, hold the riser and so the valve. "
        f"Inside the bed the head stands on {frac(r0['pipes']['head'])} in of pipe: its base is at {frac(r0['head_bottom'])} in, just under the {frac(WALL_TOP)} in wall top, "
        f"and its four 1/4 in barbs are about {frac(round((r0['head_top'] - 0.45 - WALL_TOP) * 4) / 4)} in above the soil line, where the 1/4 in drip lines start.",
        f"Per bed: one reducer tee, {r0['n_elbows']} elbows, one valve, one head with a 1/2 in male adapter to thread it on (not modelled; the head sits straight on the pipe in the model), "
        f"two clamps with four screws, and {frac(drip_pipe_per)} in of 1/2 in pipe cut {drip_cuts}. All {n_risers} risers need {frac(drip_pipe_total)} in of pipe: "
        f"{drip_sticks} x 10 ft stick{'s' if drip_sticks > 1 else ''} with {frac(round(drip_spare * 8) / 8)} in to spare after the kerfs. "
        f"Prime and cement the slip joints, tape the head's thread, and bore the holes with a {HOLE_DIA:g} in spade bit, in place or before the top boards go on.",
    ]
    drip_note = (f"The 3/4 in main is drawn only to place the tees: a stair-step {frac(r0['main_offset'])} in beyond each far end board, {frac(r0['main_depth'])} in deep, "
                 f"stepping to the next bed at the gap centres under the paver paths ({main_len / 12:.0f} ft and {main_elbows} elbows as drawn). "
                 f"The plot's angled edge passes only 2 to 4 in beyond the inner step corners, so the real route may have to cut those corners. "
                 f"Change the main's offset or depth, the pipe lengths or the riser position in scripts/fusion_build_irrigation.py and run it again; the risers and holes follow.")
    drip_model_note = (f'- 2026-11-06, drip risers: new root component **Drip Irrigation** holds one **Drip riser** component placed at each bed\'s far end wall and the reference '
                       f'**3/4 in main (existing)**. Their bodies are temporary-BRep solids in one base feature per component (not parametric: scripts/fusion_build_irrigation.py holds '
                       f'the numbers and rebuilds everything on re-run). Each bed\'s lumber component got a "Drip hole" sketch on the outer face of its top far end board and a through-all '
                       f'`Drip hole cut` ({HOLE_DIA:g} in). Materials PVC-Piping, clamps Steel, Galvanized; all of it in the timeline group "Drip irrigation". '
                       f'fusion_build_bed_lumber.py does not know about the holes, so run the irrigation script again after rebuilding the lumber.')
    drip_table = [
        ('Risers', f'{n_risers}, one per bed, on the outside of each far end wall'),
        ('Riser position', f"{frac(r0['x_off'])} in from the bed's west outside face, {frac(r0['standoff'])} in off the wall"),
        ('Hole', f"{HOLE_DIA:g} in, centred {frac(r0['through_z'])} in above grade (the middle of the top board)"),
        ('Ball valve', f"{frac(r0['valve_z'])} in above grade, lever west along the wall"),
        ('Clamps', f"{frac(r0['clamps'][0])} and {frac(r0['clamps'][1])} in above grade, one per board"),
        ('Head', f"base {frac(r0['head_bottom'])} in, top {frac(r0['head_top'])} in ({frac(r0['head_top'] - WALL_TOP)} in above the wall)"),
        ('Main', f"{frac(r0['main_offset'])} in beyond the end board, {frac(r0['main_depth'])} in deep; reducer tee at each riser"),
        ('1/2 in pipe per bed', f"{frac(drip_pipe_per)} in: {drip_cuts}"),
        ('1/2 in pipe in all', f"{frac(drip_pipe_total)} in = {drip_sticks} x 10 ft stick{'s' if drip_sticks > 1 else ''}"),
    ]
else:
    drip_paras, drip_note, drip_table = [], '', []
    drip_model_note = '- No drip risers in the model.'

# ------------------------------------------------------------------ hidden / optional
hidden_comps = [c for c in d['components'] if not c['visible'] and c['bodyCount'] > 0]
tube_arch_len = 42 + 42 + 131.95
cloth_ft = round(sum(r['L'] for r in bed_rows) / 12 + 4)

# ------------------------------------------------------------------ totals
soil_ft3 = sum(r['soil_ft3'] for r in bed_rows)
soil_alt_ft3 = sum(r['soil_alt_ft3'] for r in bed_rows)
mass_by_mat = Counter()
for b in bodies:
    mass_by_mat[b['material']] += (b['mass_kg'] or 0) * KG2LB
MASSING = {'A': '4th Bed', 'B': '3rd Bed', 'C': '2nd Bed', 'D': '1st Bed'}

# ------------------------------------------------------------------ materials by bed
# One list per bed with everything that goes to that bed, built from the same counts as the shopping list.
# A part shared by two beds (the arch panel) is listed under both; the 1/2 in drip pipe is cut from the sticks on the shopping list.
BED_GROUPS = ['Lumber', 'Cuts', 'Fasteners', 'Trellis arch', 'Hoops', 'Drip riser', 'Soil', 'Optional']


def cuts_text(cuts):
    return ' or '.join(frac(x) for x in cuts) if cuts else ''


def from_text(plan, key):
    """'4 from 2 x 8 ft' for one piece type in a plan, by stock length."""
    by = OrderedDict()
    for g in plan['sticks']:
        for c in g['cuts']:
            if c['key'] == key:
                pieces, sticks = by.get(g['stock'], (0, 0))
                by[g['stock']] = (pieces + c['n'] * g['count'], sticks + g['count'])
    return ', '.join(f"{pieces} from {sticks} x {L/12:g} ft" for L, (pieces, sticks) in by.items())


def stock_of(plan, key):
    """(stock length, offcut) of the first stick group that yields a piece type."""
    for g in plan['sticks']:
        if any(c['key'] == key for c in g['cuts']):
            return g['stock'], g['offcut']
    return None, 0.0


def bed_items(r):
    L = r['letter']
    items = []

    def add(group, key, item, qty, unit, spec, source, notes, qty_alt=None, item_alt=None, spec_alt=None):
        items.append({'group': group, 'key': f'{L.lower()}:{key}', 'item': item, 'qty': qty, 'unit': unit, 'spec': spec,
                      'source': source, 'notes': notes, 'qty_alt': qty_alt, 'item_alt': item_alt, 'spec_alt': spec_alt})

    pb, pp = r['plan_boards'], r['plan_posts']
    # Lumber to buy: the cheapest set of store-length sticks for this bed's cuts (one line per length)
    for nom, plan in ((NOM, pb), (POST_NOM, pp)):
        for L_in in sorted(plan['by_length']):
            ft = L_in / 12
            gs = [g for g in plan['sticks'] if g['stock'] == L_in]
            n = sum(g['count'] for g in gs)
            price = STOCK_IN_PRICES[nom][L_in]
            whole = len(gs) == 1 and gs[0]['cuts'][0]['n'] == 1 and len(gs[0]['cuts']) == 1 and gs[0]['offcut'] < 0.5
            if len(gs) == 1:
                notes = ('' if n == 1 or whole else 'each: ') + cutstock.stick_text(gs[0])
            elif all(g['count'] == 1 for g in gs):
                notes = 'one each: ' + '; '.join(cutstock.stick_text(g) for g in gs)
            else:
                notes = '; '.join(f"{g['count']} x {cutstock.stick_text(g)}" for g in gs)
            alt = nom == NOM
            add('Lumber', f'stock-{nom}-{ft:g}', f'{nom} x {ft:g} ft', n, 'ea', f'${price:.2f} each, ${price * n:.2f}', 'Store price', notes,
                item_alt=f'{ALT_NOM} x {ft:g} ft' if alt else None,
                spec_alt=f'${STOCK_IN_PRICES[ALT_NOM][L_in]:.2f} each, ${STOCK_IN_PRICES[ALT_NOM][L_in] * n:.2f}' if alt else None)
    # Cuts: every piece, with the length it is cut to in the plan above
    bc, pc = r['board_cuts'], r['post_cuts']
    mids = ', '.join(f'{c:.0f}' for c in r['mid_centers'])
    for Lp, n in sorted(r['side_pieces'].items(), reverse=True):
        key = f'side{Lp:g}'
        s_stock, s_off = stock_of(pb, key)
        mate = next((g for g in pb['sticks'] if any(c['key'] == key for c in g['cuts']) and any(c['key'] == 'joint' for c in g['cuts'])), None)
        if s_stock and abs(s_stock - Lp) < 1e-6:
            side_spec = f'{NOM} x {ft_in(Lp)}, whole board'
        elif mate:
            jl = next(c['len'] for c in mate['cuts'] if c['key'] == 'joint')
            side_spec = f'{NOM}, cut {Lp:g} in from a {s_stock/12:g} ft board; the {frac(jl)} in offcut is a joint post'
        else:
            side_spec = f'{NOM}, cut {Lp:g} in from a {s_stock/12:g} ft board ({frac(s_off)} in left)'
        if r['side_seams']:
            by_course = {}
            for c, ls in r['side_layout'].items():
                for i, x in enumerate(ls):
                    if abs(x - Lp) < 1e-6:
                        by_course.setdefault(c, []).append('near' if i == 0 else 'far' if i == len(ls) - 1 else 'middle')
            if len(by_course) == len(r['side_layout']) and all(sorted(e) == ['far', 'near'] for e in by_course.values()):
                places = 'every course, both ends'
            else:
                places = ', '.join(f"course {c} {' and '.join(e)} end{'s' if len(e) > 1 else ''}" for c, e in sorted(by_course.items()))
            where_txt = f"outside, both walls: {places}; the seams meet over the joint posts"
            item = f'Side board, {Lp:g} in'
        else:
            where_txt = '2 per course, outside'
            item = 'Side board'
        add('Cuts', f'side-board-{Lp:g}', item, n, 'ea', side_spec, 'Model (Bed Lumber)', where_txt)
    end_cut = cuts_text(bc.get('end', []))
    add('Cuts', 'end-board', 'End board', r['n_ends'], 'ea', f'{NOM}, cut {end_cut} in', 'Model (Bed Lumber)',
        f"{from_text(pb, 'end')}, between the side boards" + (f'; a hair under {r["E"]:g} so two clear the kerf' if bc.get('end') and min(bc['end']) < r['E'] - 1e-6 else ''))
    add('Cuts', 'corner-post', f'{POST_NOM} corner post', 4 - r['n_tr_corner'], 'ea', f'{POST_NOM}, cut {cuts_text(pc.get("corner", []))} in ({r["H_alt"]:g} in with {ALT_NOM} walls)', 'Model (Bed Lumber)',
        f"inside each corner, edge-on to the side boards, standing on grade; {from_text(pp, 'corner')}")
    add('Cuts', 'mid-post', f'{POST_NOM} mid-span post', r['n_mid_plain'], 'ea', f'{POST_NOM}, cut {cuts_text(pc.get("mid", []))} in', 'Model (Bed Lumber)',
        f"flat against the side boards, centred {mids} in from the near end, about {frac(mid_embed_cut)} in in the ground; {from_text(pp, 'mid')}")
    if r['n_joint']:
        jc = ', '.join(f'{c:g}' for c in r['joint_centers'])
        add('Cuts', 'joint-post', f'{JOINT_NOM} joint post', r['n_joint'], 'ea', f'{JOINT_NOM}, cut {cuts_text(bc.get("joint", []))} in, lying flat', 'Model (Bed Lumber)',
            f"inside the wall behind each seam, {frac(JOINT_W)} in face against the boards, centred {jc} in from the near end, about {frac(JOINT_EMBED)} in in the ground; {from_text(pb, 'joint')}")
    if r['n_trellis']:
        add('Cuts', 'trellis-post', f'{POST_NOM} trellis post', r['n_trellis'], 'ea', f'{POST_NOM} x {ft_in(TRELLIS_LEN)}' + (', uncut' if trellis_uncut else f', cut {TRELLIS_LEN:g} in'), 'Model (Bed Lumber)',
            f"{'; '.join(r['trellis_where'])}; in place of a corner post, set {TRELLIS_EMBED:g} in deep, {TRELLIS_ABOVE:g} in above grade; holds the arch near its crown")
    if r['n_sills']:
        add('Cuts', 'sill', f'{POST_NOM} arch sill', r['n_sills'], 'ea', f'{POST_NOM}, cut {frac(SILL_LEN)} in', 'Model (Bed Lumber)',
            f"flat on grade along the bed centreline, {-r['sills'][0]['max'][1]:g} to {-r['sills'][0]['min'][1]:g} in from the near end; the arch foot sits on it; {from_text(pp, 'sill')}")
        add('Cuts', 'stake', f'{POST_NOM} arch stake', r['n_stakes'], 'ea', f'{POST_NOM}, cut {cuts_text(pc.get("stake", []))} in', 'Model (Bed Lumber)',
            f"one at each end of the sill, {STAKE_EMBED:g} in in the ground, {STAKE_ABOVE:g} in above grade; {from_text(pp, 'stake')}")
    add('Fasteners', 'screw-3', '#9 x 3 in exterior structural screws', r['screws_3'], 'ea', 'star drive; coated for treated lumber, stainless 305/316 for cedar or redwood', 'Derived from model',
        f"{r['corner_side_screws']} side boards into the corner post edges + {r['tie_screws']} corner ties into end grain" + (f" + {r['anchor_screws']} arch stakes into the sill ends" if r['anchor_screws'] else ''))
    add('Fasteners', 'screw-25', '#9 x 2.5 in exterior structural screws', r['screws_25'], 'ea', 'same finish as the 3 in screws', 'Derived from model',
        f"{r['mid_side_screws']} side boards into the mid-span post faces + {r['end_screws']} end boards into the corner post faces"
        + (f" + {r['joint_screws']} side boards into the joint post faces" if r['joint_screws'] else ''))
    if r['screws_125']:
        add('Fasteners', 'screw-125', f'{PANEL_SCREW} exterior screws', r['screws_125'], 'ea', 'same finish, each through a fender washer', 'Derived from model',
            f'hog-wire panel to the trellis post ({PANEL_SCREWS_PER_POST}), the stakes ({PANEL_SCREWS_PER_STAKE} each) and the sill ({PANEL_SCREWS_PER_SILL})')
        add('Fasteners', 'washer', '1/4 x 1 in galvanized fender washers', r['panel_screws'], 'ea', 'one under each panel screw', 'Derived from model', 'the washer beside a wire traps it against the wood')
    for k, a in arch_comps.items():
        if any(b['letter'] == L for b in a['beds']):
            others = ' and '.join(f"Bed {b['letter']}" for b in a['beds'] if b['letter'] != L)
            add('Trellis arch', 'panel-' + k.lower().replace(' ', '-'), f'Hog-wire / cattle panel, {HOGWIRE_LEN/12:g} ft, 4 x 4 in mesh ({k})', 1, 'ea', '4-gauge galvanized, 48 to 60 in wide', 'Model (Hogwire Arches)',
                f'one panel bent from the centre of this bed to the centre of {others}; it is listed under both beds, buy one. {HOG_LEG:.0f} in straight legs, crown {a["crown"]:.0f} in above grade')
    if n_hoops and hoop_bed_letter == L:
        add('Hoops', 'hoop', f'Low-tunnel hoop, 1 in tube, {hoop_w - 1:.0f} in wide x {hoop_h:.0f} in tall', n_hoops, 'ea', f'{hoop_len:.0f} in of tube each ({hoop_len/12:.1f} ft), {hoop_tube_ft:.0f} ft in all', 'Model (Garden Hoops)',
            f'{hoop_pitch:g} in pitch, the first and last {hoop_near_gap:g} in inside the end boards; {HOOP_LEG:g} in legs pushed through the soil to grade')
    rb = next((x for x in risers if x['bed'] == L), None)
    if rb:
        cuts = ', '.join(frac(rb['pipes'][k]) for k in PIPE_ORDER if k in rb['pipes'])
        add('Drip riser', 'tee', '3/4 x 3/4 x 1/2 in PVC reducer tee, slip', 1, 'ea', 'schedule 40', 'Model (Drip Irrigation)',
            f"on the 3/4 in main, {frac(rb['main_offset'])} in beyond the far end board, {frac(rb['main_depth'])} in deep")
        add('Drip riser', 'pipe', '1/2 in PVC pipe, schedule 40', len(rb['pipes']), 'pieces', f'cut {cuts} in ({frac(sum(rb["pipes"].values()))} in in all)', 'Model (Drip Irrigation)',
            f"ground run, lower riser, upper riser, through the wall, head; cut from the {drip_sticks} x 10 ft stick{'s' if drip_sticks > 1 else ''} on the shopping list, shared by all {n_risers} beds")
        add('Drip riser', 'elbow', '1/2 in PVC 90 degree elbow, slip', rb['n_elbows'], 'ea', 'schedule 40', 'Model (Drip Irrigation)', 'at the bottom of the riser and on each side of the wall')
        add('Drip riser', 'valve', '1/2 in PVC ball valve, slip x slip', 1, 'ea', 'lever handle', 'Model (Drip Irrigation)',
            f"{frac(rb['valve_z'])} in above grade on the outside of the far end wall, lever west along the wall")
        add('Drip riser', 'head', '1/2 in FPT x 4-port 1/4 in barb drip manifold head', 1, 'ea', '', 'Model (Drip Irrigation)',
            f"inside the bed, top {frac(rb['head_top'] - WALL_TOP)} in above the wall top")
        add('Drip riser', 'adapter', '1/2 in PVC male adapter, slip x MPT', 1, 'ea', 'threads the head onto the riser', 'Derived from model', 'not modelled; a female adapter instead if your head is male')
        add('Drip riser', 'clamp', '1/2 in stand-off pipe clamp', rb['n_clamps'], 'ea', 'galvanized or UV-stable plastic', 'Model (Drip Irrigation)',
            f"at {frac(rb['clamps'][0])} and {frac(rb['clamps'][1])} in above grade, one on each board")
        add('Drip riser', 'clamp-screw', '#8 x 1 in exterior pan-head screws', 2 * rb['n_clamps'], 'ea', 'same finish as the bed screws', 'Derived from model', 'two per clamp')
        add('Drip riser', 'hole', f'{HOLE_DIA:g} in hole through the top far end board', 1, 'ea',
            f"spade bit, centred {frac(rb['through_z'])} in above grade and {frac(rb['x_off'])} in from the bed's west outside face", 'Model (Drip Irrigation)',
            'the through-wall pipe passes it; bore it in place or before the top board goes on')
    add('Soil', 'soil', 'Raised-bed soil mix', round(r['soil_ft3'], 1), 'cu ft', f"{r['soil_ft3']/27:.2f} cu yd at {r['H']:g} in deep", 'Derived from model',
        f"{ALT_NOM} walls: {r['soil_alt_ft3']:.1f} cu ft ({r['soil_alt_ft3']/27:.2f} cu yd)", qty_alt=round(r['soil_alt_ft3'], 1))
    add('Optional', 'cloth', 'Hardware cloth 1/2 in, 48 in wide (under the bed)', round(r['L'] / 12 + 1), 'lin ft', 'gopher / vole barrier', 'Estimate',
        'not in model; one strip the length of the bed plus a foot' + (f", trimmed to {r['W'] - 2 * T:g} in wide" if r['W'] - 2 * T < 48 else ''))
    return items


def cap(t):
    return t[0].upper() + t[1:] if t else t


bed_lists = [(r, bed_items(r)) for r in bed_rows]
for _, _items in bed_lists:
    for _it in _items:
        _it['spec'], _it['notes'] = cap(_it['spec']), cap(_it['notes'])
bed_lines_total = sum(len(items) for _, items in bed_lists)

# ================================================================== shopping list (CSV + md)
rows = []  # section, item, qty, unit, spec, source, notes
for x in lumber_list:
    rows.append(('Lumber', x['item'], x['qty'], 'ea', f"${x['price']:.2f} each, ${x['price'] * x['qty']:.2f}" + (f"; {ALT_NOM}: ${x['price_alt']:.2f} each" if x['price_alt'] is not None else ''),
                 'Store price', x['use']))
rows.append(('Hardware', '#9 x 3 in exterior structural screws, star drive', screws_3, 'ea',
             'Coated for treated lumber; stainless 305/316 for cedar or redwood', 'Derived from model',
             f'Side boards into the corner post edges ({tot_corner_side}) + corner ties into end grain ({tot_tie}) + arch stakes into the sill ends ({tot_anchor}); buy {buy_3}'))
rows.append(('Hardware', '#9 x 2.5 in exterior structural screws, star drive', screws_25, 'ea',
             'Same finish as the 3 in screws', 'Derived from model',
             f'Side boards into the mid-span post faces ({tot_mid_side}) + end boards into the corner post faces ({tot_end})'
             + (f' + side boards into the joint post faces ({tot_joint})' if tot_joint else '') + f'; buy {buy_25}'))
rows.append(('Hardware', f'{PANEL_SCREW} exterior screws, star drive', screws_125, 'ea',
             'Same finish; short enough to stay inside a 1.5 in post, stake or sill', 'Derived from model',
             f'Hog-wire panel to the trellis posts ({PANEL_SCREWS_PER_POST} each), arch stakes ({PANEL_SCREWS_PER_STAKE} each) and sills ({PANEL_SCREWS_PER_SILL} each), '
             f'each through a fender washer; a 1 lb box holds about {PER_LB[1.25]}'))
rows.append(('Hardware', '1/4 x 1 in galvanized fender washers', tot_panel, 'ea',
             'Under the panel screws', 'Derived from model',
             'One per panel screw; the washer beside a wire traps it against the wood'))
rows.append(('Pavers', f'Concrete paver {paver_dims[1]:g} x {paver_dims[2]:g} x {paver_dims[0]:g} in', paver_n, 'ea',
             f'about {paver_each_lb:.0f} lb each, {paver_total_lb:,.0f} lb total', 'Model (Small Pavers)',
             '; '.join(f"{g['n']} {PAVER_LABEL.get(k, k)}" for k, g in paver_groups.items())))
rows.append(('Pavers', 'Paver leveling base (crushed stone or all-purpose sand)', base_bags, '0.5 cu ft bag',
             f'{base_depth_in:g} in under each paver, {base_ft3:.1f} cu ft', 'Estimate', 'Not in model'))
rows.append(('Arches', f'Hog-wire / cattle panel, {HOGWIRE_LEN/12:g} ft long, 4 x 4 in mesh', n_arches, 'ea',
             '4-gauge galvanized, 48 to 60 in wide', 'Model (Hogwire Arches)',
             f'Bent over {first_arch["chord"]:.0f} in between the Bed A and Bed B centrelines, feet on {POST_NOM} sills on the ground: {HOG_LEG:.0f} in straight legs, '
             f'crown {first_arch["crown"]:.0f} in above grade, held near the top by the two {ft_in(TRELLIS_LEN)} inside corner posts, no T-posts. '
             f'Model wires are 60 in wide at 4 in pitch. Arch BC is parked (hidden) in the model'))
if risers:
    rows.append(('Drip', '3/4 x 3/4 x 1/2 in PVC reducer tee, slip', n_risers, 'ea', 'Schedule 40', 'Model (Drip Irrigation)',
                 f"One per bed on the 3/4 in main, {frac(r0['main_offset'])} in beyond the far end board and {frac(r0['main_depth'])} in deep"))
    rows.append(('Drip', '1/2 in PVC pipe, schedule 40, 10 ft', drip_sticks, 'ea', f'{frac(drip_pipe_total)} in needed in {drip_pieces} pieces', 'Model (Drip Irrigation)',
                 f'Per bed {drip_cuts} in; {frac(round(drip_spare * 8) / 8)} in spare after the kerfs'))
    rows.append(('Drip', '1/2 in PVC 90 degree elbow, slip', drip_elbows, 'ea', 'Schedule 40', 'Model (Drip Irrigation)', f"{r0['n_elbows']} per bed: at the bottom of the riser and on each side of the wall"))
    rows.append(('Drip', '1/2 in PVC ball valve, slip x slip', n_risers, 'ea', 'Lever handle', 'Model (Drip Irrigation)', f"{frac(r0['valve_z'])} in above grade on the outside of the far end wall, between the two clamps"))
    rows.append(('Drip', '1/2 in FPT x 4-port 1/4 in barb drip manifold head', n_risers, 'ea', '', 'Model (Drip Irrigation)', f"Top at {frac(r0['head_top'])} in, {frac(r0['head_top'] - WALL_TOP)} in above the wall top, inside the bed"))
    rows.append(('Drip', '1/2 in PVC male adapter, slip x MPT', n_risers, 'ea', 'Threads the head onto the riser', 'Derived from model', 'Not modelled; use a female adapter instead if your head is male'))
    rows.append(('Drip', '1/2 in stand-off pipe clamp', drip_clamps, 'ea', 'Galvanized or UV-stable plastic', 'Model (Drip Irrigation)',
                 f"Two per bed at {frac(r0['clamps'][0])} and {frac(r0['clamps'][1])} in, each on one board"))
    rows.append(('Drip', '#8 x 1 in exterior pan-head screws', 2 * drip_clamps, 'ea', 'Same finish as the bed screws', 'Derived from model', 'Two per clamp'))
    rows.append(('Drip', 'PVC primer and cement, small cans', 1, 'set', '', 'Estimate', f'{n_risers * (r0["n_elbows"] * 2 + 3 + 1)} slip joints in all'))
    rows.append(('Drip', 'PTFE thread tape', 1, 'roll', '', 'Estimate', 'Head onto the male adapter'))
    rows.append(('Drip (reference)', '3/4 in sprinkler main, existing', round(main_len / 12, 1), 'ft', f'{main_elbows} elbows if routed as drawn', 'Model (3/4 in main (existing))',
                 f"Stair-step {frac(r0['main_offset'])} in beyond the far end boards, {frac(r0['main_depth'])} in deep; drawn only to place the tees"))
rows.append(('Soil', 'Raised-bed soil mix', round(soil_ft3 / 27, 2), 'cu yd', f'{soil_ft3:.0f} cu ft at {bed_rows[0]["H"]:g} in deep',
             'Derived from model', f'{ALT_NOM} alternative: {soil_alt_ft3/27:.2f} cu yd'))
rows.append(('Optional', 'Hardware cloth 1/2 in, 48 in wide (under beds)', cloth_ft, 'lin ft', 'Gopher / vole barrier', 'Estimate',
             'Not in model; one strip per bed, trimmed to 21 in wide for Bed D'))
if n_hoops:
    rows.append(('Hoops', f'Low-tunnel hoop, 1 in tube, {hoop_w - 1:.0f} in wide x {hoop_h:.0f} in tall', n_hoops, 'ea',
                 f'{hoop_len:.0f} in of tube each ({hoop_len/12:.1f} ft), {hoop_tube_ft:.0f} ft in all', 'Model (Garden Hoops)',
                 f'{hoop_summary}; {HOOP_LEG:g} in legs pushed through the {hoop_in_soil:g} in of soil to grade, {hoop_leg_up:g} in of straight leg above the soil. '
                 f'{hoop_len/12:.1f} ft each, so 10 ft sticks need a coupling in one leg; 12 ft stock makes one-piece hoops'))
rows.append(('Optional (hidden in model)', 'Single-tube garden arch, 1 in tube, 7 ft wide x 7 ft tall', 1, 'ea',
             f'{tube_arch_len:.0f} in of tube ({tube_arch_len/12:.0f} ft)', 'Model (Garden Arch, hidden)', 'Superseded by Arch AB at the same spot'))

with open(ROOT / 'BOM.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Section', 'Item', 'Qty', 'Unit', 'Spec', 'Source', 'Notes'])
    for r in rows:
        w.writerow(r)

with open(ROOT / 'BOM-by-bed.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Bed', 'Group', 'Item', 'Qty', 'Unit', 'Spec', 'Source', 'Notes'])
    for r, items in bed_lists:
        for it in items:
            w.writerow([r['letter'], it['group'], it['item'], it['qty'], it['unit'], it['spec'], it['source'], it['notes']])

def option_label(o, nom):
    S = f"{o['length']/12:g} ft"
    forced = ' and '.join(f"{x/12:g} ft" for x in o['forced'])
    if nom == POST_NOM:
        return f'{S} sticks' + (f' plus the uncut {forced} trellis post' if forced else '')
    return f'{S} boards' + (f' for the ends, {forced} for the sides' if forced else ' only')


def option_mark(o, plan):
    diff = round(o['cost'] - plan['cost'], 2)
    if abs(diff) < 0.005:
        return 'chosen' if same_cutting(o, plan) else 'same cost'
    return f'+${diff:.2f}'


def options_text(r, nom, opts, plan):
    parts = [f"{option_label(o, nom)}: {sticks_txt(o['n_sticks'])}, ${o['cost']:.2f}, {frac(o['offcut'])} in offcut ({option_mark(o, plan)})" for o in opts]
    return f'{nom}: ' + '; '.join(parts) + '.'


# ================================================================== BOM.md
md = []
md.append('# Raised Bed Design: bill of materials\n')
md.append(f'Generated {TODAY} from the Fusion design **{d["document"]}** (data/model_extract.json). '
          f'Quantities marked *Model* are counted from model bodies; *Derived* rows are computed from the model geometry; *Estimate* rows are not modeled.\n')
md.append('## Layout\n')
md.append('Four beds in a 24 ft x 18 ft plot, a 2-row paver walkway along the top edge, 12 in paver paths between beds, '
          f'and a {HOGWIRE_LEN/12:g} ft hog-wire trellis arch from the centre of Bed A to the centre of Bed B, its feet on {POST_NOM} sills on the ground '
          f'and its top held by the two inside corner posts, uncut {ft_in(TRELLIS_LEN)} {POST_NOM}s (a second arch, Arch BC, is modeled but parked). '
          'Bed letters follow the arch names in the model (Arch AB spans beds A and B). '
          + (f'{n_hoops} low-tunnel hoops of 1 in tube stand over Bed {hoop_bed_letter} at {hoop_pitch:g} in pitch.\n' if n_hoops else '\n'))
md.append('| Bed | Model body | Outside (W x L) | Inside | Height | Posts | Soil |')
md.append('|---|---|---|---|---|---|---|')
for r in bed_rows:
    md.append(f"| **{r['letter']}** | {MASSING[r['letter']]} | {r['W']:g} in x {ft_in(r['L'])} | {r['E']:g} x {r['inner_L']:g} in | "
              f"{r['H']:g} in ({COURSES} x {NOM}) | {r['n_posts']} x {POST_NOM} ({4 - r['n_tr_corner']} corner"
              + (f" + {r['n_trellis']} uncut {ft_in(TRELLIS_LEN)} trellis corner" if r['n_trellis'] else '')
              + f" + {r['n_mid']} mid)" + (f" + {r['n_joint']} x {JOINT_NOM} joint" if r['n_joint'] else '') + f", {r['post_spacing']:.0f} in max spacing"
              + (f" + {r['n_sills']} arch sill with {r['n_stakes']} stakes" if r['n_sills'] else '') + f" | {r['soil_ft3']:.0f} cu ft |")
md.append('')
md.append(f'Bed walls are {NOM} on edge, {COURSES} courses, {bed_rows[0]["H"]:g} in tall. Side boards run outside the end boards, which sit between them. '
          f'{side_scheme_txt} {POST_NOM} corner posts stand inside every corner, edge-on, so side-board screws there get {PW:g} in of post to bite into; '
          f'{POST_NOM} mid-span posts lie flat against the long walls and run {MID_LEN:g} in long, {EMBED_IN:g} in of it driven into the ground. '
          f'Under the arch, the inside corner post at the near end of beds A and B is an uncut {ft_in(TRELLIS_LEN)} {POST_NOM} (trellis post) set {TRELLIS_EMBED:g} in deep, '
          f'{TRELLIS_ABOVE:g} in above grade, and a {SILL_LEN:g} in {POST_NOM} sill with a {STAKE_LEN:g} in stake at each end lies on the ground along each of those beds\' centrelines to anchor the arch foot. '
          f'Switching the Fusion parameter `Board_Width` to 9.25 in gives {ALT_NOM} walls {bed_rows[0]["H_alt"]:g} in tall with the same cut list.\n')

md.append('## Shopping list\n')
md.append('| Section | Item | Qty | Unit | Spec | Source | Notes |')
md.append('|---|---|---|---|---|---|---|')
for r in rows:
    md.append('| ' + ' | '.join(str(x) for x in r) + ' |')
md.append('')
md.append(f'Lumber totals: {total_2x_boards} boards of {NOM} ({total_lin_ft_2x:.0f} linear ft) plus {post_sticks} sticks of {POST_NOM}, '
          f'about ${lumber_cost:.2f} before tax at these prices ({ALT_NOM} walls: ${lumber_cost_alt:.2f}); prices are {PRICE_SOURCE}. '
          f'Model lumber weight about {lumber_mass_lb:,.0f} lb ({ALT_NOM}: about {lumber_mass_alt_lb:,.0f} lb). '
          f'Pavers weigh about {paver_total_lb:,.0f} lb in total, so plan for delivery.\n')

md.append('## Screw plan\n')
md.append(f'Every joint is a {NOM} board face-screwed to a {POST_NOM} post, {SCREWS_PER_JOINT} screws per board per post, '
          f'{SCREW_HEIGHTS[0]:g} in and {SCREW_HEIGHTS[1]:g} in up from the bottom edge of each board. Corner posts stand edge-on: {PT:g} in edge against the side board, '
          f'{PW:g} in face against the end board. Mid-span posts lie flat, {PW:g} in face against the side board, and run {MID_LEN:g} in long so {EMBED_IN:g} in is driven into the ground. '
          + (f'Where two side boards meet over a {JOINT_NOM} joint post ({beds_text(split_beds)}), each board end gets its own pair, {JOINT_OFF:g} in from the end. ' if split_beds else '')
          + f'Use #9 star-drive exterior structural screws (coated for treated lumber; stainless 305 or 316 for cedar or redwood, which stain and corrode plain coated screws).\n')
md.append('| Joint | Screw | Why that length and where | Count |')
md.append('|---|---|---|---|')
md.append(f'| Side board into a corner post edge | #9 x 3 in | 1.5 in through the board, 1.5 in into the post\'s {PW:g} in depth. The target is only {PT:g} in wide: mark the post centerline on the outside face first, {T+PT/2:g} in from the board end. | {SCREWS_PER_JOINT} per board per post |')
md.append(f'| Side board into a mid-span post face | #9 x 2.5 in | 1.5 in through the board, 1 in into the post\'s {PT:g} in thickness; a 3 in screw would poke out the back. The face is {PW:g} in wide, so stagger the pair {MID_OFFSET:g} in either side of the post centerline: the lower screw to one side, the upper to the other. Drive the posts first, then screw the boards to them. | {SCREWS_PER_JOINT} per board per post |')
md.append(f'| End board into a corner post face | #9 x 2.5 in | Same joint as the mid-span posts: 1 in into the post\'s {PT:g} in thickness. Center them {T+PW/2:g} in from the board end. | {SCREWS_PER_JOINT} per board per post |')
if split_beds:
    md.append(f'| Side board end into a joint post face | #9 x 2.5 in | The joint post is a {JOINT_NOM} offcut lying flat, {frac(JOINT_W)} in wide and {JOINT_T:g} in thick, so the screws are the mid-span length. Where two boards meet over it, each board end gets two screws {JOINT_OFF:g} in from the end at the usual heights (pre-drill: they are within 2 in of the end); a course that runs past the post gets the mid-span pair instead. | {2 * SCREWS_PER_JOINT} per course where boards meet, {SCREWS_PER_JOINT} where one runs past |')
md.append(f'| Corner tie: through the side board into the end board\'s end grain | #9 x 3 in | Holds the corner closed. Pre-drill 1/8 in; place at {TIE_HEIGHTS[0]:g} in and {TIE_HEIGHTS[1]:g} in up, {T/2:g} in from the board end, staggered off the post screws. | {TIES_PER_CORNER} per corner per course |')
md.append(f'| Hog-wire panel to the trellis posts, arch stakes and sills | {PANEL_SCREW} + 1 in fender washer | The washer beside a wire traps it against the wood, and 1.25 in stays inside a 1.5 in post, stake or sill so no tip pokes out the back. At the post top, one screw each side of the edge wire where it crosses the face; on each stake, beside two cross wires; along the sill, beside the bottom wire. | {PANEL_SCREWS_PER_POST} per post, {PANEL_SCREWS_PER_STAKE} per stake, {PANEL_SCREWS_PER_SILL} per sill |')
md.append(f'| Arch stake into the sill\'s end grain | #9 x 3 in | 1.5 in through the stake, 1.5 in into the sill end. Pre-drill 1/8 in and drive from the stake\'s back before the end board goes on, {T/2:g} in up, 1 in either side of center. | {STAKE_SILL_SCREWS} per stake |')
md.append('')
md.append('| Bed | Posts per side | 3 in: corner posts | 3 in: corner ties | 3 in: arch stakes | 2.5 in: mid-span posts | 2.5 in: joint posts | 2.5 in: end boards | 1.25 in: arch panel | Total |')
md.append('|---|---|---|---|---|---|---|---|---|---|')
for r in bed_rows:
    md.append(f"| {r['letter']} | {r['posts_per_side']} | {r['corner_side_screws']} | {r['tie_screws']} | {r['anchor_screws']} | {r['mid_side_screws']} | {r['joint_screws']} | {r['end_screws']} | {r['panel_screws']} | {r['screws_3']+r['screws_25']+r['screws_125']} |")
md.append(f'| **Total** | | **{tot_corner_side}** | **{tot_tie}** | **{tot_anchor}** | **{tot_mid_side}** | **{tot_joint}** | **{tot_end}** | **{tot_panel}** | **{screws_total}** |')
md.append('')
md.append(f'Buy: 3 in, {screws_3} needed, {buy_3}; 2.5 in, {screws_25} needed, {buy_25}; 1.25 in, {screws_125} needed, one 1 lb box. '
          f'Pre-drill the corner ties and any screw within 2 in of a board end (1/8 in bit for cedar, 3/32 in for SPF). '
          f'Set the mid-span posts{" and the joint posts" if split_beds else ""} first: chamfer the bottom of each to a point, drive it {frac(mid_embed_cut)} in at the marked centerline with its wide face toward the wall, '
          f'stop when its top is flush with the top of the wall, then screw the side boards to it from outside. Corner posts stay {POST_H:g} in and sit on grade, except the {tot_tr_corner} inside corner posts at the near end of beds A and B under the arch, which are uncut {ft_in(TRELLIS_LEN)} trellis posts set {TRELLIS_EMBED:g} in deep (see the arch).\n')

md.append('## Cut list\n')
md.append(f'Stock lengths and prices: {PRICE_SOURCE}. {NOM} and {ALT_NOM} come in {board_lengths_txt} ({side_stock_note}); '
          f'{POST_NOM} comes in {post_lengths_txt}. Each bed\'s plan is the cheapest set of sticks for that bed on its own, so the four plans add up to the shopping list. '
          f'{cut_rule_txt}\n')
md.append('| Buy | Qty | Each | Total | For |')
md.append('|---|---|---|---|---|')
for x in stock_rows:
    md.append(f"| {x['nom']} x {x['ft']} ft | **{x['qty']}** | ${x['price']:.2f} | ${x['price'] * x['qty']:.2f} | {x['use']} |")
md.append(f"| **Total** | **{total_2x_boards + post_sticks}** | | **${lumber_cost:.2f}** | {ALT_NOM} walls: ${lumber_cost_alt:.2f} |")
md.append('')
md.append(f'Cutting all four beds from one pile instead: {combined_sticks} sticks, ${combined_cost:.2f}'
          + (f', saving ${combined_saving:.2f} over the per-bed plans (offcuts from one bed become pieces for another).' if combined_saving > 0.005 else '; the per-bed plans are already as cheap.') + '\n')
md.append('| Buy | Qty | Each one is cut into | Offcut |')
md.append('|---|---|---|---|')
for nom, plan in ((NOM, combined_boards), (POST_NOM, combined_posts)):
    for g in plan['sticks']:
        md.append(f"| {nom} x {g['stock']/12:g} ft | {g['count']} | {cutstock.stick_text(g, offcut=False)} | {frac(g['offcut'])} in |")
md.append('')

md.append('## Materials by bed\n')
md.append('Everything that goes to one bed, so each bed can be checked on its own. The lumber lines are the sticks to buy, in store lengths with store prices, '
          'and the cut lines beneath them say what every stick becomes; fasteners come from the screw plan. '
          'The hog-wire panel spans beds A and B and is listed under both (buy one); the 1/2 in drip pipe for every bed is cut from the sticks on the shopping list. '
          'The same lists are in BOM-by-bed.csv, and bom.html has tick boxes that are remembered in the browser.\n')
for r, items in bed_lists:
    md.append(f"### Bed {r['letter']}: {ft_in(r['L'])} x {r['W']:g} in, {r['H']:g} in tall\n")
    md.append(f"Inside {r['E']:g} x {r['inner_L']:g} in. {len(items)} lines. Lumber: {r['lumber_sticks']} sticks, ${r['lumber_cost']:.2f} ({ALT_NOM} walls: ${r['lumber_cost_alt']:.2f}).\n")
    md.append('| Buy | Qty | Each one is cut into | Offcut |')
    md.append('|---|---|---|---|')
    for nom, plan in ((NOM, r['plan_boards']), (POST_NOM, r['plan_posts'])):
        for g in plan['sticks']:
            md.append(f"| {nom} x {g['stock']/12:g} ft | {g['count']} | {cutstock.stick_text(g, offcut=False)} | {frac(g['offcut'])} in |")
    md.append('')
    md.append('Other ways to buy it: ' + ' '.join(options_text(r, nom, opts, plan) for nom, opts, plan in ((NOM, r['opts_boards'], r['plan_boards']), (POST_NOM, r['opts_posts'], r['plan_posts']))) + '\n')
    for g in BED_GROUPS:
        gi = [it for it in items if it['group'] == g]
        if not gi:
            continue
        md.append(f'**{g}**\n')
        for it in gi:
            qty = f"{it['qty']:g} x" if it['unit'] == 'ea' else f"{it['qty']:g} {it['unit']}"
            spec = f" {it['spec']}." if it['spec'] else ''
            md.append(f"- [ ] **{qty}** {it['item']}.{spec} {it['notes']}. *{it['source']}*")
        md.append('')

md.append('## Pavers and paths\n')
md.append('| Group | Pavers | Where |')
md.append('|---|---|---|')
for k, g in paver_groups.items():
    md.append(f"| {k} | {g['n']} | {PAVER_LABEL.get(k, '')} |")
md.append(f'| **Total** | **{paver_n}** | {paver_dims[1]:g} x {paver_dims[2]:g} x {paver_dims[0]:g} in, about {paver_each_lb:.0f} lb each |')
md.append('')
md.append(f'Beds are 24 in apart with one 12 in paver centered in each gap. The walkway is a 33 in strip with two rows of pavers at 15 in pitch; '
          f'a second 36 in strip beyond it is in the site sketch but not modeled. Base estimate: {base_depth_in:g} in of leveling material under each paver, '
          f'{base_ft3:.1f} cu ft, about {base_bags} half-cubic-foot bags.\n')

md.append('## Hog-wire trellis arches\n')
md.append('| Arch | Between | Chord | Feet | Straight leg | Crown above grade | Upper supports | Walkway headroom | Panel width modeled |')
md.append('|---|---|---|---|---|---|---|---|---|')
for k, a in arch_comps.items():
    md.append(f"| {k} | {ARCH_BETWEEN.get(k, '')} | {a['chord']:.0f} in | on {POST_NOM} sills, {a['feet']:g} in above grade | {HOG_LEG:.0f} in | {a['crown']:.0f} in | {a['posts']} | {headroom(a)} | {a['ymax']-a['ymin']-2*WIRE_R:.0f} in ({a['wires']} wires at 4 in) |")
md.append('')
for para in arch_paras:
    md.append(para + '\n')
md.append(arch_note + '\n')

if n_hoops:
    md.append('## Low-tunnel hoops\n')
    md.append('| Over | Hoops | Pitch | Width | Top above grade | Legs | Tube each | Tube in all |')
    md.append('|---|---|---|---|---|---|---|---|')
    md.append(f"| Bed {hoop_bed_letter} ({ft_in(hoop_bed['L'])}) | {n_hoops} | {hoop_pitch:g} in | {hoop_w - 1:.0f} in | {hoop_h:.0f} in | {HOOP_LEG:g} in | {hoop_len:.0f} in ({hoop_len/12:.1f} ft) | {hoop_tube_ft:.0f} ft |")
    md.append('')
    for para in hoop_paras:
        md.append(para + '\n')

if risers:
    md.append('## Drip risers\n')
    md.append('| Item | Value |')
    md.append('|---|---|')
    for k, v in drip_table:
        md.append(f'| {k} | {v} |')
    md.append('')
    for para in drip_paras:
        md.append(para + '\n')
    md.append(drip_note + '\n')

md.append('## Soil\n')
md.append('| Bed | Inside | Depth | Volume |')
md.append('|---|---|---|---|')
for r in bed_rows:
    md.append(f"| {r['letter']} | {r['E']:g} x {r['inner_L']:g} in | {r['H']:g} in | {r['soil_ft3']:.1f} cu ft |")
md.append(f'| **Total** | | | **{soil_ft3:.0f} cu ft = {soil_ft3/27:.1f} cu yd** |')
md.append('')
md.append(f'Volumes subtract the posts. With {ALT_NOM} walls ({bed_rows[0]["H_alt"]:g} in) the total is {soil_alt_ft3:.0f} cu ft = {soil_alt_ft3/27:.1f} cu yd.\n')

md.append('## Optional items modeled but hidden\n')
md.append(f'- **Single-tube arch** (Garden Arch): 1 in tube, 7 ft span, 42 in legs, 7 ft tall, about {tube_arch_len/12:.0f} ft of tube. Same location as Arch AB; superseded.\n')

md.append('## Model notes (Fusion)\n')
md.append(f'- New component **Bed Lumber** holds the buildable beds ({NOM} walls, {POST_NOM} posts); the original 4 in-wall massing bodies in **Raised Beds** are hidden and kept as the layout reference the arch sketches use.')
md.append('- New user parameters: `Board_Width` (7.25 in = 2x8), `Courses` (2) and `Mid_Post_Length` (24 in), plus `Board_Thickness` and `Post_Size` for reference. Bed height = Courses x Board_Width; each bed\'s `Mid post extrude` runs Courses x Board_Width up and the rest of Mid_Post_Length down from the Posts sketch.')
md.append('- Physical materials fixed: pavers were Pine with a concrete appearance and are now **Concrete (paver)** at 2300 kg/m3; arch wires are **Steel, Galvanized**; the tube arch is **Steel**.')
md.append('- Component part numbers and descriptions filled in; "Forth Paver Path" renamed "Fourth Paver Path".')
md.append('- The ten superseded rolled-back features that sat after the timeline marker (Position5, R-Pattern2, the old Sketch1-4 / Extrude1-3 bed layout, and a broken CopyPaste 2x8x8:3) were deleted on 2026-11-05.')
md.append(f'- 2026-11-06, trellis arch: Arch AB now runs from the centre of Bed A to the centre of Bed B with its feet on the ground (parametric Move "Onto the sills": 21 in across the beds, 1.25 in along them, Board_Thickness up). New parameters `Trellis_Post_Length` ({TRELLIS_LEN:g} in), `Trellis_Post_Embed` ({TRELLIS_EMBED:g} in) and `Stake_Above_Sill` ({STAKE_ABOVE - T:g} in). The inside corner post at the near end of beds A and B moved out of `Post extrude` into a two-sided `Trellis post extrude` (body "2x4 trellis post"); each of those beds got an "Arch anchors" sketch with a `Sill extrude` (body "2x4 sill") and a two-sided `Stake extrude` (bodies "2x4 stake"). `Hogwire_height` is `(Hogwire_length - Hogwire_archlength) / 2` = {HOG_LEG:.1f} in. The earlier wall-top scheme of the same day (72 in posts under the arch legs) is superseded: Arch BC is hidden (parked) and its posts are ordinary again. The T-post anchors are gone.')
md.append(hoops_model_note)
md.append(drip_model_note)
md.append(split_model_note)
md.append('- ' + saved_note)
md.append('')
md.append('Model mass by material (visible bodies): ' + ', '.join(f'{k} {v:,.0f} lb' for k, v in mass_by_mat.items()) + '.' + hoop_mass_note)

(ROOT / 'BOM.md').write_text('\n'.join(md) + '\n')

# ================================================================== bom.html
S = 2.5          # px per inch in the plan view
M = 56           # margin px
XMIN, XMAX, YMIN, YMAX = -288.0, 0.0, -216.0, 69.0


def sx(x):
    return (x - XMIN) * S + M


def sy(y):
    return (YMAX - y) * S + M


VW = int((XMAX - XMIN) * S + 2 * M)
VH = int((YMAX - YMIN) * S + 2 * M + 24)


def esc(s):
    return html.escape(str(s), quote=True)


svg = []
svg.append(f'<svg viewBox="0 0 {VW} {VH}" role="img" aria-label="Plan view of the four beds, paver walkway and paths, the hog-wire arch, the low-tunnel hoops over Bed C, and the drip main with a riser at the far end of every bed" xmlns="http://www.w3.org/2000/svg">')
svg.append('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<line x1="0" y1="0" x2="0" y2="6" stroke="currentColor" stroke-width="1" opacity="0.45"/></pattern>'
           '<marker id="dim" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
           '<path d="M2 1 L8 5 L2 9" fill="none" stroke="currentColor" stroke-width="1.4"/></marker></defs>')
pts = [(0, 69), (-288, 69), (-288, -120), (0, -216)]
svg.append('<polygon points="' + ' '.join(f'{sx(x):.1f},{sy(y):.1f}' for x, y in pts) + '" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.8"/>')
for y in (0, 33):
    svg.append(f'<line x1="{sx(-288):.1f}" y1="{sy(y):.1f}" x2="{sx(0):.1f}" y2="{sy(y):.1f}" stroke="currentColor" stroke-width="1" stroke-dasharray="4 4" opacity="0.6"/>')
svg.append(f'<text x="{sx(-144):.1f}" y="{sy(51)+4:.1f}" text-anchor="middle" font-size="12" fill="currentColor" opacity="0.75">36 in strip (site sketch only)</text>')
svg.append(f'<text x="{sx(-144):.1f}" y="{sy(33)-5:.1f}" text-anchor="middle" font-size="12" fill="currentColor" opacity="0.75">walkway: 2 rows of pavers, 15 in pitch</text>')
for comp, g in paver_groups.items():
    tip = f"{comp}: {g['n']} pavers, {PAVER_LABEL.get(comp, '')}"
    svg.append(f'<g class="pv" data-tip="{esc(tip)}">')
    for b in paver_bodies:
        if b['component'] != comp:
            continue
        x0, y0 = b['min'][0], b['min'][1]
        x1, y1 = b['max'][0], b['max'][1]
        svg.append(f'<rect x="{sx(x0):.1f}" y="{sy(y1):.1f}" width="{(x1-x0)*S:.1f}" height="{(y1-y0)*S:.1f}" fill="url(#hatch)" stroke="currentColor" stroke-width="0.8" opacity="0.9"/>')
    svg.append('</g>')
for r in bed_rows:
    x0, x1, y0, y1 = r['xmin'], r['xmax'], r['ymin'], r['ymax']
    tip = (f"Bed {r['letter']}: {r['W']:g} in x {ft_in(r['L'])} outside, {COURSES} x {NOM} = {r['H']:g} in tall, "
           f"{r['n_posts']} {POST_NOM} posts" + (f" + {r['n_joint']} {JOINT_NOM} joint posts behind the side-board seams" if r['n_joint'] else '')
           + (f" + {r['n_sills']} arch sill with {r['n_stakes']} stakes" if r['n_sills'] else '') + f", {r['screws_3']+r['screws_25']+r['screws_125']} screws, soil {r['soil_ft3']:.0f} cu ft"
           + (f"; {n_hoops} low-tunnel hoops at {hoop_pitch:g} in pitch" if n_hoops and r['letter'] == hoop_bed_letter else ''))
    svg.append(f'<g class="bed" data-tip="{esc(tip)}">')
    outer = f'M{sx(x0):.1f} {sy(y1):.1f} H{sx(x1):.1f} V{sy(y0):.1f} H{sx(x0):.1f} Z'
    inner = f'M{sx(x0+T):.1f} {sy(y1-T):.1f} H{sx(x1-T):.1f} V{sy(y0+T):.1f} H{sx(x0+T):.1f} Z'
    svg.append(f'<path d="{outer} {inner}" fill="var(--lumber)" fill-rule="evenodd" stroke="var(--lumber)" stroke-width="1.2"/>')
    svg.append(f'<rect x="{sx(x0+T):.1f}" y="{sy(y1-T):.1f}" width="{(r["W"]-2*T)*S:.1f}" height="{(r["L"]-2*T)*S:.1f}" fill="var(--lumber)" opacity="0.12"/>')
    for p in r['posts'] + r['anchors']:
        svg.append(f'<rect x="{sx(p["min"][0]):.1f}" y="{sy(p["max"][1]):.1f}" width="{(p["max"][0]-p["min"][0])*S:.1f}" height="{(p["max"][1]-p["min"][1])*S:.1f}" fill="var(--lumber)" opacity="0.85"/>')
    for s_ in r['side_seams']:       # where two side boards meet (one course or both), a hairline across each wall
        for wx in (x0, x1 - T):
            svg.append(f'<line x1="{sx(wx):.1f}" y1="{sy(y1 - s_):.1f}" x2="{sx(wx + T):.1f}" y2="{sy(y1 - s_):.1f}" stroke="var(--panel)" stroke-width="1.2"/>')
    cx, cy = sx((x0 + x1) / 2), sy((y0 + y1) / 2)
    svg.append(f'<text x="{cx:.1f}" y="{cy-6:.1f}" text-anchor="middle" font-size="26" font-weight="700" fill="currentColor">{r["letter"]}</text>')
    svg.append(f'<text x="{cx:.1f}" y="{cy+14:.1f}" text-anchor="middle" font-size="12" fill="currentColor">{ft_in(r["L"])}</text>')
    svg.append(f'<text x="{cx:.1f}" y="{cy+28:.1f}" text-anchor="middle" font-size="12" fill="currentColor">{r["W"]:g} in wide</text>')
    svg.append('</g>')
for ga, gb in [(-24, -48), (-99, -123), (-174, -198)]:
    svg.append(f'<text x="{sx((ga+gb)/2):.1f}" y="{sy(-205):.1f}" text-anchor="middle" font-size="11" fill="currentColor" opacity="0.75" transform="rotate(-90 {sx((ga+gb)/2):.1f} {sy(-205):.1f})">24 in gap</text>')
bed_label_ys = [(r['ymin'] + r['ymax']) / 2 for r in bed_rows]
for k, a in arch_comps.items():
    tip = f"{k}: {HOGWIRE_LEN/12:g} ft hog-wire panel between {ARCH_BETWEEN.get(k, '')}, {a['chord']:.0f} in chord, feet on {POST_NOM} sills on the ground, crown {a['crown']:.0f} in above grade, held by the two {ft_in(TRELLIS_LEN)} inside corner posts"
    svg.append(f'<g class="arch" data-tip="{esc(tip)}">')
    svg.append(f'<rect x="{sx(a["xmin"]):.1f}" y="{sy(a["ymax"]):.1f}" width="{(a["xmax"]-a["xmin"])*S:.1f}" height="{(a["ymax"]-a["ymin"])*S:.1f}" fill="var(--arch)" fill-opacity="0.12" stroke="var(--arch)" stroke-width="2" stroke-dasharray="7 5"/>')
    y_top, y_bot = a['ymax'] - 9, a['ymin'] + 5
    pick = max((y_top, y_bot), key=lambda yy: min(abs(yy - by) for by in bed_label_ys))
    svg.append(f'<text x="{sx((a["xmin"]+a["xmax"])/2):.1f}" y="{sy(pick):.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="var(--arch)">{k}</text>')
    svg.append('</g>')
if n_hoops:
    tip = f"Garden Hoops: {n_hoops} low-tunnel hoops of 1 in tube over Bed {hoop_bed_letter}, {hoop_pitch:g} in pitch, {hoop_w - 1:.0f} in wide, {hoop_h:.0f} in tall, {hoop_len/12:.1f} ft of tube each"
    svg.append(f'<g class="hoops" data-tip="{esc(tip)}">')
    for b in hoop_bodies:
        svg.append(f'<rect x="{sx(b["min"][0]):.1f}" y="{sy(b["max"][1]):.1f}" width="{(b["max"][0]-b["min"][0])*S:.1f}" height="{max((b["max"][1]-b["min"][1])*S, 2.5):.1f}" rx="1" fill="var(--arch)" stroke="var(--arch)" stroke-width="0.8"/>')
    # ticks at the leg positions so the bars read as hoops, not boards
    for b in hoop_bodies:
        for xx in (b['min'][0] + 0.5, b['max'][0] - 0.5):
            svg.append(f'<circle cx="{sx(xx):.1f}" cy="{sy((b["min"][1]+b["max"][1])/2):.1f}" r="2.6" fill="var(--panel)" stroke="var(--arch)" stroke-width="1.2"/>')
    lx = sx(hoop_cx)
    ly = sy((hoop_ys[0] + hoop_ys[1]) / 2) if n_hoops >= 2 else sy(hoop_ys[-1]) + 14   # between the first two hoops, clear of the bed letter at mid-length
    svg.append(f'<text x="{lx:.1f}" y="{ly+4:.1f}" text-anchor="middle" font-size="11" font-weight="600" fill="var(--arch)" paint-order="stroke" stroke="var(--panel)" stroke-width="3" stroke-linejoin="round">{n_hoops} hoops, {hoop_pitch:g} in</text>')
    svg.append('</g>')
if risers:
    tip = (f"Drip: 3/4 in main (existing, drawn as a stair-step {frac(r0['main_offset'])} in beyond the far end boards, {frac(r0['main_depth'])} in deep) "
           f"with a 1/2 in riser and ball valve on the outside of every far end wall, {frac(r0['x_off'])} in from the west face, and a 4-port 1/4 in head inside")
    svg.append(f'<g class="drip" data-tip="{esc(tip)}">')
    for b in main_bodies:
        if 'elbow' in b['body']:
            continue
        x0, y0, x1, y1 = b['min'][0], b['min'][1], b['max'][0], b['max'][1]
        if x1 - x0 > y1 - y0:
            svg.append(f'<line x1="{sx(x0):.1f}" y1="{sy((y0+y1)/2):.1f}" x2="{sx(x1):.1f}" y2="{sy((y0+y1)/2):.1f}" stroke="currentColor" stroke-width="2" stroke-dasharray="6 3 1.5 3" opacity="0.8"/>')
        else:
            svg.append(f'<line x1="{sx((x0+x1)/2):.1f}" y1="{sy(y0):.1f}" x2="{sx((x0+x1)/2):.1f}" y2="{sy(y1):.1f}" stroke="currentColor" stroke-width="2" stroke-dasharray="6 3 1.5 3" opacity="0.8"/>')
    for r in risers:
        bx = r['bed_row']['xmin'] + r['x_off']
        by = r['bed_row']['ymin']
        svg.append(f'<line x1="{sx(bx):.1f}" y1="{sy(by - r["main_offset"]):.1f}" x2="{sx(bx):.1f}" y2="{sy(by):.1f}" stroke="currentColor" stroke-width="1.5" opacity="0.8"/>')
        svg.append(f'<circle cx="{sx(bx):.1f}" cy="{sy(by - r["standoff"]):.1f}" r="4" fill="var(--panel)" stroke="currentColor" stroke-width="1.6"/>')
    la = min(risers, key=lambda r: r['bed_row']['xmin'])['bed_row']     # label in the margin under bed A, level with the gap labels
    lax = sx(la['xmin'] + la['W'] / 2)
    svg.append(f'<text x="{lax:.1f}" y="{sy(-205) - 3:.1f}" text-anchor="middle" font-size="11" fill="currentColor" opacity="0.85">3/4 in main (dash-dot),</text>')
    svg.append(f'<text x="{lax:.1f}" y="{sy(-205) + 11:.1f}" text-anchor="middle" font-size="11" fill="currentColor" opacity="0.85">risers at every far end</text>')
    svg.append('</g>')
yd = sy(69) - 22
svg.append(f'<line x1="{sx(-288):.1f}" y1="{yd:.1f}" x2="{sx(0):.1f}" y2="{yd:.1f}" stroke="currentColor" stroke-width="1" marker-start="url(#dim)" marker-end="url(#dim)"/>')
svg.append(f'<text x="{sx(-144):.1f}" y="{yd-6:.1f}" text-anchor="middle" font-size="12" fill="currentColor">24 ft</text>')
xd = sx(0) + 24
svg.append(f'<line x1="{xd:.1f}" y1="{sy(0):.1f}" x2="{xd:.1f}" y2="{sy(-216):.1f}" stroke="currentColor" stroke-width="1" marker-start="url(#dim)" marker-end="url(#dim)"/>')
svg.append(f'<text x="{xd+6:.1f}" y="{sy(-108):.1f}" font-size="12" fill="currentColor" transform="rotate(90 {xd+6:.1f} {sy(-108):.1f})" text-anchor="middle">18 ft</text>')
xd2 = sx(-288) - 24
svg.append(f'<line x1="{xd2:.1f}" y1="{sy(0):.1f}" x2="{xd2:.1f}" y2="{sy(-120):.1f}" stroke="currentColor" stroke-width="1" marker-start="url(#dim)" marker-end="url(#dim)"/>')
svg.append(f'<text x="{xd2-6:.1f}" y="{sy(-60):.1f}" font-size="12" fill="currentColor" transform="rotate(-90 {xd2-6:.1f} {sy(-60):.1f})" text-anchor="middle">10 ft</text>')
svg.append('</svg>')
SVG = '\n'.join(svg)

# ---- corner joint detail, plan view (top down), 1 in = K px ----
K = 28
ox, oy = 40, 60            # px origin of the bed's outside corner; the bed extends right and down in this drawing
DW, DH = 17.0, 13.5        # inches shown
MIDY = 8.0                 # where the first mid-span post is drawn (schematic, not to scale along the bed)
HALO = 'paint-order="stroke" stroke="var(--panel)" stroke-width="3" stroke-linejoin="round"'


def dx(xin):
    return ox + xin * K


def dy(yin):
    return oy + yin * K


def screw_x(y, length, color='currentColor', extra='', marker='scr'):
    """A screw driven from outside the side board in +x, at true length; the head sits 0.4 in proud of the board."""
    return (f'<line x1="{dx(-0.4):.1f}" y1="{dy(y):.1f}" x2="{dx(length):.1f}" y2="{dy(y):.1f}" '
            f'stroke="{color}" stroke-width="2"{extra} marker-end="url(#{marker})"/>')


cs = []
cs.append(f'<svg viewBox="0 0 {int(DW*K+ox+40)} {int(DH*K+oy+40)}" role="img" aria-label="Plan view of one corner and a mid-span post: side board outside, end board between the side boards, a 2x4 corner post edge-on inside the corner, a 2x4 mid-span post flat against the side board, and the screw groups drawn at true length" xmlns="http://www.w3.org/2000/svg">')
cs.append('<defs><marker id="scr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M1 1 L9 5 L1 9 Z" fill="currentColor"/></marker>'
          '<marker id="scrb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M1 1 L9 5 L1 9 Z" fill="var(--arch)"/></marker></defs>')
# soil
cs.append(f'<rect x="{dx(T):.1f}" y="{dy(T):.1f}" width="{(DW-T)*K:.1f}" height="{(DH-T)*K:.1f}" fill="var(--lumber)" opacity="0.08"/>')
# side board, outside, runs down the drawing
cs.append(f'<rect x="{dx(0):.1f}" y="{dy(0):.1f}" width="{T*K:.1f}" height="{DH*K:.1f}" fill="var(--lumber)" opacity="0.55" stroke="var(--lumber)" stroke-width="1.5"/>')
# end board, between the side boards
cs.append(f'<rect x="{dx(T):.1f}" y="{dy(0):.1f}" width="{(DW-T)*K:.1f}" height="{T*K:.1f}" fill="var(--lumber)" opacity="0.55" stroke="var(--lumber)" stroke-width="1.5"/>')
# corner post: PT along the side board, PW into the bed
cs.append(f'<rect x="{dx(T):.1f}" y="{dy(T):.1f}" width="{PW*K:.1f}" height="{PT*K:.1f}" fill="var(--lumber)" opacity="0.9" stroke="currentColor" stroke-width="1"/>')
# mid-span post: flat, PW along the side board, PT into the bed
cs.append(f'<rect x="{dx(T):.1f}" y="{dy(MIDY):.1f}" width="{PT*K:.1f}" height="{PW*K:.1f}" fill="var(--lumber)" opacity="0.9" stroke="currentColor" stroke-width="1"/>')
# 3 in: side board into the corner post edge, on the post centerline
cs.append(screw_x(T + PT / 2, 3.0))
# 2.5 in: side board into the mid-span post face, staggered either side of its centerline
mc = MIDY + PW / 2
cs.append(screw_x(mc - MID_OFFSET, 2.5))
cs.append(screw_x(mc + MID_OFFSET, 2.5))
# 2.5 in: end board into the corner post's wide face, from above
cs.append(f'<line x1="{dx(T+PW/2):.1f}" y1="{dy(-0.4):.1f}" x2="{dx(T+PW/2):.1f}" y2="{dy(2.5):.1f}" stroke="currentColor" stroke-width="2" marker-end="url(#scr)"/>')
# corner tie: 3 in through the side board into the end board's end grain
cs.append(screw_x(T / 2, 3.0, 'var(--arch)', ' stroke-dasharray="5 3"', 'scrb'))
# labels
LX0 = dx(T + PW + 0.5)
LX1 = dx(T + PT + 0.6)
cs.append(f'<text x="{LX0:.1f}" y="{dy(T/2)+4:.1f}" font-size="12" fill="var(--arch)" {HALO}>3 in tie into end grain</text>')
cs.append(f'<text x="{dx(DW-0.3):.1f}" y="{dy(T/2)+4:.1f}" font-size="11" fill="currentColor" text-anchor="end" {HALO}>end board</text>')
cs.append(f'<text x="{LX0:.1f}" y="{dy(T+PT/2)+4:.1f}" font-size="12" fill="currentColor" {HALO}>3 in into the post edge, {PW:g} in deep</text>')
cs.append(f'<text x="{LX0:.1f}" y="{dy(T+PT/2)+19:.1f}" font-size="11" fill="currentColor" opacity="0.7" {HALO}>corner post, {PT:g} x {PW:g} in, edge-on</text>')
cs.append(f'<text x="{dx(T+PW/2)+8:.1f}" y="{dy(-1.0):.1f}" font-size="12" fill="currentColor">2.5 in into the post face, {PT:g} in thick</text>')
cs.append(f'<text x="{LX1:.1f}" y="{dy(mc-MID_OFFSET)+4:.1f}" font-size="12" fill="currentColor" {HALO}>2.5 in: lower screw, {SCREW_HEIGHTS[0]:g} in up</text>')
cs.append(f'<text x="{LX1:.1f}" y="{dy(mc+MID_OFFSET)+4:.1f}" font-size="12" fill="currentColor" {HALO}>2.5 in: upper screw, {SCREW_HEIGHTS[1]:g} in up</text>')
cs.append(f'<text x="{dx(T):.1f}" y="{dy(MIDY+PW)+16:.1f}" font-size="11" fill="currentColor" opacity="0.7" {HALO}>mid-span post, flat: {PW:g} in face on the board, {MID_OFFSET:g} in each side of center</text>')
cs.append(f'<text x="{dx(T/2):.1f}" y="{dy(DH)+16:.1f}" font-size="11" fill="currentColor" text-anchor="middle">side board</text>')
cs.append(f'<text x="{dx(10):.1f}" y="{dy(6):.1f}" font-size="11" fill="currentColor" opacity="0.6">soil side</text>')
cs.append('</svg>')
CORNER_SVG = '\n'.join(cs)

# ---- elevation at a corner, outside face of a side board: two courses, screw heights ----
E_K = 22
ex0, ey0 = 30, 34
EW = 9.0   # inches of board length shown, starting at the bed end
EH = COURSES * BOARD_W
PX = ex0 + (T + PT / 2) * E_K   # post centerline
TX = ex0 + T / 2 * E_K          # tie line, through the end board's end grain
LX = ex0 + EW * E_K             # right edge of the drawn board
el = []
el.append(f'<svg viewBox="0 0 {int(LX+176)} {int(EH*E_K+ey0+58)}" role="img" aria-label="Outside elevation of a side board at a corner: two courses, the end board end grain and the corner post behind it, post screws at {SCREW_HEIGHTS[0]:g} and {SCREW_HEIGHTS[1]:g} inches from the bottom of each board, corner ties at {TIE_HEIGHTS[0]:g} and {TIE_HEIGHTS[1]:g} inches" xmlns="http://www.w3.org/2000/svg">')
for c in range(COURSES):
    y_top = ey0 + c * BOARD_W * E_K
    el.append(f'<rect x="{ex0}" y="{y_top:.1f}" width="{EW*E_K:.1f}" height="{BOARD_W*E_K:.1f}" fill="var(--lumber)" opacity="0.45" stroke="var(--lumber)" stroke-width="1.5"/>')
# behind the board, dashed: the end board's end grain (0 to T) and the corner post (T to T+PT)
el.append(f'<rect x="{ex0:.1f}" y="{ey0-6}" width="{T*E_K:.1f}" height="{EH*E_K+12:.1f}" fill="none" stroke="var(--arch)" stroke-width="1.2" stroke-dasharray="4 3"/>')
el.append(f'<rect x="{ex0+T*E_K:.1f}" y="{ey0-6}" width="{PT*E_K:.1f}" height="{EH*E_K+12:.1f}" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3"/>')
el.append(f'<text x="{ex0+(T+PT)*E_K+6:.1f}" y="{ey0-12}" font-size="11" fill="currentColor">end grain and {POST_NOM} corner post behind the side board</text>')
for c in range(COURSES):
    bottom = ey0 + (c + 1) * BOARD_W * E_K
    for h in SCREW_HEIGHTS:
        yy = bottom - h * E_K
        el.append(f'<circle cx="{PX:.1f}" cy="{yy:.1f}" r="4" fill="currentColor"/>')
        el.append(f'<line x1="{LX+6:.1f}" y1="{yy:.1f}" x2="{LX+24:.1f}" y2="{yy:.1f}" stroke="currentColor" stroke-width="1"/>')
        el.append(f'<text x="{LX+28:.1f}" y="{yy+4:.1f}" font-size="11" fill="currentColor">post screw, {h:g} in up</text>')
    for h in TIE_HEIGHTS:
        yy = bottom - h * E_K
        el.append(f'<circle cx="{TX:.1f}" cy="{yy:.1f}" r="4" fill="var(--arch)"/>')
        el.append(f'<line x1="{LX+6:.1f}" y1="{yy:.1f}" x2="{LX+24:.1f}" y2="{yy:.1f}" stroke="var(--arch)" stroke-width="1" stroke-dasharray="3 2"/>')
        el.append(f'<text x="{LX+28:.1f}" y="{yy+4:.1f}" font-size="11" fill="var(--arch)">corner tie, {h:g} in up</text>')
by = ey0 + EH * E_K
el.append(f'<text x="{TX:.1f}" y="{by+16:.1f}" font-size="11" fill="var(--arch)" text-anchor="middle">tie {T/2:g} in in</text>')
el.append(f'<text x="{PX:.1f}" y="{by+30:.1f}" font-size="11" fill="currentColor" text-anchor="middle">post {T+PT/2:g} in in</text>')
el.append(f'<text x="{ex0}" y="{by+46:.1f}" font-size="11" fill="currentColor">{NOM} boards, {BOARD_W:g} in each, seen from outside; bed end at the left</text>')
el.append('</svg>')
ELEV_SVG = '\n'.join(el)

# ---- elevation at a mid-span post, outside face of a side board: the post runs below grade ----
M_K = 16
mx0, my0 = 30, 34
MW = 12.0                       # inches of board length shown; the post is centered
MCX = mx0 + MW / 2 * M_K        # post centerline, px
m_grade = my0 + EH * M_K        # grade line: the bottom of the lower course
m_bot = m_grade + EMBED_IN * M_K
LXM = mx0 + MW * M_K
me = []
me.append(f'<svg viewBox="0 0 {int(LXM+236)} {int(m_bot+52)}" role="img" aria-label="Outside elevation of a side board at a mid-span post: two courses, the post {PW:g} in wide behind the board and {EMBED_IN:g} in below grade, two 2.5 in screws per course staggered {MID_OFFSET:g} in either side of the post centerline" xmlns="http://www.w3.org/2000/svg">')
me.append(f'<rect x="0" y="{m_grade:.1f}" width="{int(LXM+236)}" height="{m_bot-m_grade+18:.1f}" fill="currentColor" opacity="0.05"/>')
for c in range(COURSES):
    y_top = my0 + c * BOARD_W * M_K
    me.append(f'<rect x="{mx0}" y="{y_top:.1f}" width="{MW*M_K:.1f}" height="{BOARD_W*M_K:.1f}" fill="var(--lumber)" opacity="0.45" stroke="var(--lumber)" stroke-width="1.5"/>')
# the post behind the board, dashed, chamfered to a point over its last 2 in
px0 = MCX - PW / 2 * M_K
px1 = MCX + PW / 2 * M_K
pt_y = m_bot - 2.0 * M_K
me.append(f'<path d="M{px0:.1f} {my0-6} V{pt_y:.1f} L{MCX:.1f} {m_bot:.1f} L{px1:.1f} {pt_y:.1f} V{my0-6} Z" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3"/>')
me.append(f'<line x1="{MCX:.1f}" y1="{my0-6}" x2="{MCX:.1f}" y2="{m_bot:.1f}" stroke="currentColor" stroke-width="0.8" stroke-dasharray="2 4" opacity="0.6"/>')
me.append(f'<line x1="{mx0-20}" y1="{m_grade:.1f}" x2="{LXM+20}" y2="{m_grade:.1f}" stroke="currentColor" stroke-width="1.2" stroke-dasharray="8 4"/>')
me.append(f'<text x="{LXM+28:.1f}" y="{m_grade+4:.1f}" font-size="11" fill="currentColor">grade</text>')
me.append(f'<text x="{mx0}" y="{my0-12}" font-size="11" fill="currentColor">{POST_NOM} mid-span post behind the board, {PW:g} in face</text>')
for c in range(COURSES):
    bottom = my0 + (c + 1) * BOARD_W * M_K
    for h, side in zip(SCREW_HEIGHTS, (-1, 1)):
        xx = MCX + side * MID_OFFSET * M_K
        yy = bottom - h * M_K
        me.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="4" fill="currentColor"/>')
        me.append(f'<line x1="{LXM+6:.1f}" y1="{yy:.1f}" x2="{LXM+24:.1f}" y2="{yy:.1f}" stroke="currentColor" stroke-width="1"/>')
        me.append(f'<text x="{LXM+28:.1f}" y="{yy+4:.1f}" font-size="11" fill="currentColor">{h:g} in up, {frac(MID_OFFSET)} in {"left" if side < 0 else "right"} of center</text>')
me.append(f'<text x="{mx0}" y="{m_bot+16:.1f}" font-size="11" fill="currentColor">{MID_LEN:g} in post, {EMBED_IN:g} in below grade, bottom chamfered to a point</text>')
me.append(f'<text x="{mx0}" y="{m_bot+32:.1f}" font-size="11" fill="currentColor">{NOM} boards, {BOARD_W:g} in each, seen from outside</text>')
me.append('</svg>')
MID_ELEV_SVG = '\n'.join(me)

# ---- elevation at a joint post, outside face of a side wall: the lower course's two boards meet over the post, the upper course runs past it ----
J_K = 16
jx0, jy0 = 30, 34
JWID = 14.0                     # inches of wall shown; the post is centred
JCX = jx0 + JWID / 2 * J_K      # post and seam centreline, px
j_grade = jy0 + EH * J_K
j_bot = j_grade + JOINT_EMBED * J_K
LXJ = jx0 + JWID * J_K
je = []
je.append(f'<svg viewBox="0 0 {int(LXJ+252)} {int(j_bot+52)}" role="img" aria-label="Outside elevation of a side wall at a joint post: the post {frac(JOINT_W)} in wide behind the boards and {JOINT_EMBED:g} in below grade; in the lower course two boards meet over it and each end gets two 2.5 in screws {JOINT_OFF:g} in from the end, the upper course runs past with the staggered mid-span pair" xmlns="http://www.w3.org/2000/svg">')
je.append(f'<rect x="0" y="{j_grade:.1f}" width="{int(LXJ+252)}" height="{j_bot-j_grade+18:.1f}" fill="currentColor" opacity="0.05"/>')
SEAM_COURSE = COURSES - 1       # drawn index of the course with the seam: the lowest course (Bed C has the seam in one course only; Bed D in both)
for c in range(COURSES):
    y_top = jy0 + c * BOARD_W * J_K
    if c == SEAM_COURSE:
        je.append(f'<rect x="{jx0}" y="{y_top:.1f}" width="{(JWID/2 - KERF/2)*J_K:.1f}" height="{BOARD_W*J_K:.1f}" fill="var(--lumber)" opacity="0.45" stroke="var(--lumber)" stroke-width="1.5"/>')
        je.append(f'<rect x="{JCX + KERF/2*J_K:.1f}" y="{y_top:.1f}" width="{(JWID/2 - KERF/2)*J_K:.1f}" height="{BOARD_W*J_K:.1f}" fill="var(--lumber)" opacity="0.45" stroke="var(--lumber)" stroke-width="1.5"/>')
    else:
        je.append(f'<rect x="{jx0}" y="{y_top:.1f}" width="{JWID*J_K:.1f}" height="{BOARD_W*J_K:.1f}" fill="var(--lumber)" opacity="0.45" stroke="var(--lumber)" stroke-width="1.5"/>')
jp0 = JCX - JOINT_W / 2 * J_K
jp1 = JCX + JOINT_W / 2 * J_K
jpt_y = j_bot - 2.0 * J_K
je.append(f'<path d="M{jp0:.1f} {jy0-6} V{jpt_y:.1f} L{JCX:.1f} {j_bot:.1f} L{jp1:.1f} {jpt_y:.1f} V{jy0-6} Z" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3"/>')
je.append(f'<line x1="{JCX:.1f}" y1="{jy0-6}" x2="{JCX:.1f}" y2="{j_bot:.1f}" stroke="currentColor" stroke-width="0.8" stroke-dasharray="2 4" opacity="0.6"/>')
je.append(f'<line x1="{jx0-20}" y1="{j_grade:.1f}" x2="{LXJ+20}" y2="{j_grade:.1f}" stroke="currentColor" stroke-width="1.2" stroke-dasharray="8 4"/>')
je.append(f'<text x="{LXJ+28:.1f}" y="{j_grade+4:.1f}" font-size="11" fill="currentColor">grade</text>')
je.append(f'<text x="{jx0}" y="{jy0-12}" font-size="11" fill="currentColor">{JOINT_NOM} joint post behind the boards, {frac(JOINT_W)} in face, flat</text>')
for c in range(COURSES):
    bottom = jy0 + (c + 1) * BOARD_W * J_K
    if c == SEAM_COURSE:
        for h in SCREW_HEIGHTS:
            yy = bottom - h * J_K
            for side in (-1, 1):
                je.append(f'<circle cx="{JCX + side * JOINT_OFF * J_K:.1f}" cy="{yy:.1f}" r="4" fill="currentColor"/>')
            je.append(f'<line x1="{LXJ+6:.1f}" y1="{yy:.1f}" x2="{LXJ+24:.1f}" y2="{yy:.1f}" stroke="currentColor" stroke-width="1"/>')
            je.append(f'<text x="{LXJ+28:.1f}" y="{yy+4:.1f}" font-size="11" fill="currentColor">{h:g} in up, one each side, {frac(JOINT_OFF)} in from the ends</text>')
    else:
        for h, side in zip(SCREW_HEIGHTS, (-1, 1)):
            yy = bottom - h * J_K
            je.append(f'<circle cx="{JCX + side * MID_OFFSET * J_K:.1f}" cy="{yy:.1f}" r="4" fill="currentColor"/>')
            je.append(f'<line x1="{LXJ+6:.1f}" y1="{yy:.1f}" x2="{LXJ+24:.1f}" y2="{yy:.1f}" stroke="currentColor" stroke-width="1"/>')
            je.append(f'<text x="{LXJ+28:.1f}" y="{yy+4:.1f}" font-size="11" fill="currentColor">{h:g} in up, {frac(MID_OFFSET)} in {"left" if side < 0 else "right"}: the board runs past</text>')
je.append(f'<text x="{JCX:.1f}" y="{jy0 + (SEAM_COURSE + 1) * BOARD_W * J_K + 14:.1f}" font-size="11" fill="currentColor" text-anchor="middle">seam, {frac(KERF)} in gap</text>')
je.append(f'<text x="{jx0}" y="{j_bot+16:.1f}" font-size="11" fill="currentColor">{JOINT_LEN:g} in offcut, {JOINT_EMBED:g} in below grade, bottom chamfered to a point</text>')
je.append(f'<text x="{jx0}" y="{j_bot+32:.1f}" font-size="11" fill="currentColor">{NOM} boards, {BOARD_W:g} in each, seen from outside</text>')
je.append('</svg>')
JOINT_ELEV_SVG = '\n'.join(je)
joint_elev_caption = (f"Outside face of a side wall at a joint post: a {JOINT_LEN:g} in {JOINT_NOM} offcut lying flat behind the boards, {frac(JOINT_W)} in wide, {JOINT_EMBED:g} in below grade. "
                      f"Where two boards meet over it (the lower course here), each board end gets two 2.5 in screws {frac(JOINT_OFF)} in from the end at the usual heights; pre-drill them, they are within 2 in of the end. "
                      f"A course that runs past the post gets the same staggered pair as a mid-span post. "
                      + (f"{beds_text(staggered_beds, True)} stagger{'s' if len(staggered_beds) == 1 else ''} the seams, so every joint post sees one of each; " if staggered_beds else '')
                      + (f"in {beds_text([b for b in split_beds if b not in staggered_beds])} both courses meet over the post." if [b for b in split_beds if b not in staggered_beds] else ''))


# ---- the arch in elevation, seen from the near end: both beds, the walkway, the trellis posts, the sills and stakes, the panel ----
a0 = first_arch
A_K = 4.0
ax0, az0 = 214, 22          # room on the left for the labels
X_LO = min(r['xmin'] for r in a0['beds']) - 4
X_HI = max(r['xmax'] for r in a0['beds']) + 4
Z_LO, Z_HI = -TRELLIS_EMBED - 4, max(a0['crown'], TRELLIS_ABOVE) + 12


def ex(x):
    return ax0 + (x - X_LO) * A_K


def ez(z):
    return az0 + (Z_HI - z) * A_K


def under_panel(body, a=a0):
    return body['max'][1] >= a['ymin'] - 2 and body['min'][1] <= a['ymax'] + 2


AW, AH = int(ex(X_HI) + 20), int(ez(Z_LO) + 24)
BED_H = COURSES * BOARD_W
av = []
av.append(f'<svg viewBox="0 0 {AW} {AH}" role="img" aria-label="Elevation of the hog-wire arch from the near end: two beds with a walkway between, the panel standing on sills at the bed centrelines, {ft_in(TRELLIS_LEN)} posts at the inside corners reaching the crown, headroom figures in the walkway" xmlns="http://www.w3.org/2000/svg">')
av.append(f'<rect x="{ex(X_LO):.1f}" y="{ez(0):.1f}" width="{(X_HI-X_LO)*A_K:.1f}" height="{(0-Z_LO)*A_K:.1f}" fill="currentColor" opacity="0.05"/>')
av.append(f'<line x1="{ex(X_LO):.1f}" y1="{ez(0):.1f}" x2="{ex(X_HI):.1f}" y2="{ez(0):.1f}" stroke="currentColor" stroke-width="1"/>')
for r in a0['beds']:
    # soil between the walls, then the two wall boards seen end-on
    av.append(f'<rect x="{ex(r["xmin"]):.1f}" y="{ez(BED_H):.1f}" width="{(r["xmax"]-r["xmin"])*A_K:.1f}" height="{BED_H*A_K:.1f}" fill="var(--lumber)" opacity="0.12"/>')
    for (w0, w1) in ((r['xmin'], r['xmin'] + T), (r['xmax'] - T, r['xmax'])):
        av.append(f'<rect x="{ex(w0):.1f}" y="{ez(BED_H):.1f}" width="{(w1-w0)*A_K:.1f}" height="{BED_H*A_K:.1f}" fill="var(--lumber)" opacity="0.7" stroke="var(--lumber)" stroke-width="1"/>')
    toward_walk = 0.75 if r['xmax'] < a0['xc'] else 0.25     # the label sits between the stake and the post
    av.append(f'<text x="{ex(r["xmin"] + (r["xmax"]-r["xmin"])*toward_walk):.1f}" y="{ez(BED_H/2)+4:.1f}" font-size="12" font-weight="600" text-anchor="middle" fill="currentColor">Bed {r["letter"]}</text>')
    for p in r['posts']:
        if kind(p) == 'trellis' and under_panel(p):
            x0, x1 = p['min'][0], p['max'][0]
            av.append(f'<rect x="{ex(x0):.1f}" y="{ez(TRELLIS_ABOVE):.1f}" width="{(x1-x0)*A_K:.1f}" height="{TRELLIS_ABOVE*A_K:.1f}" fill="var(--lumber)" opacity="0.9" stroke="currentColor" stroke-width="1"/>')
            av.append(f'<rect x="{ex(x0):.1f}" y="{ez(0):.1f}" width="{(x1-x0)*A_K:.1f}" height="{TRELLIS_EMBED*A_K:.1f}" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="4 3"/>')
    for s_ in r['sills']:
        if under_panel(s_):
            av.append(f'<rect x="{ex(s_["min"][0]):.1f}" y="{ez(s_["max"][2]):.1f}" width="{(s_["max"][0]-s_["min"][0])*A_K:.1f}" height="{(s_["max"][2]-s_["min"][2])*A_K:.1f}" fill="var(--lumber)" opacity="0.9" stroke="currentColor" stroke-width="1"/>')
w = a0['walk']
if w:
    av.append(f'<rect x="{ex(w["x0"]):.1f}" y="{ez(0):.1f}" width="{w["width"]*A_K:.1f}" height="6" fill="currentColor" opacity="0.25"/>')
    av.append(f'<text x="{ex((w["x0"]+w["x1"])/2):.1f}" y="{ez(0)+20:.1f}" font-size="11" text-anchor="middle" fill="currentColor">walkway {w["width"]:g} in</text>')
xl, xr = a0['xmin'] + WIRE_R, a0['xmax'] - WIRE_R
av.append(f'<path d="M{ex(xl):.1f} {ez(a0["feet"]):.1f} L{ex(xl):.1f} {ez(a0["spring"]):.1f} A{ARCH_R*A_K:.1f} {ARCH_R*A_K:.1f} 0 0 1 {ex(xr):.1f} {ez(a0["spring"]):.1f} L{ex(xr):.1f} {ez(a0["feet"]):.1f}" fill="none" stroke="var(--arch)" stroke-width="3" stroke-linejoin="round"/>')
for r in a0['beds']:
    stakes_here = [s_ for s_ in r['stakes'] if under_panel(s_)]
    if stakes_here:
        s_ = max(stakes_here, key=lambda b: b['max'][1])     # the two stakes line up in this view; the near one stands in front of the panel
        x0, x1 = s_['min'][0], s_['max'][0]
        av.append(f'<rect x="{ex(x0):.1f}" y="{ez(s_["max"][2]):.1f}" width="{(x1-x0)*A_K:.1f}" height="{s_["max"][2]*A_K:.1f}" fill="var(--lumber)" opacity="0.9" stroke="currentColor" stroke-width="1"/>')
        av.append(f'<rect x="{ex(x0):.1f}" y="{ez(0):.1f}" width="{(x1-x0)*A_K:.1f}" height="{-s_["min"][2]*A_K:.1f}" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="4 3"/>')
if w:
    # edge labels sit on the walkway side of their lines, at three different heights so none collide
    for (xx, hh, anchor, fh) in ((w['x0'], w['h0'], 'start', 0.30), ((w['x0'] + w['x1']) / 2, w['hc'], 'middle', 0.62), (w['x1'], w['h1'], 'end', 0.44)):
        av.append(f'<line x1="{ex(xx):.1f}" y1="{ez(0):.1f}" x2="{ex(xx):.1f}" y2="{ez(hh):.1f}" stroke="var(--arch)" stroke-width="1" stroke-dasharray="3 3"/>')
        av.append(f'<circle cx="{ex(xx):.1f}" cy="{ez(hh):.1f}" r="3.5" fill="var(--arch)"/>')
        av.append(f'<text x="{ex(xx) + (0 if anchor == "middle" else (6 if anchor == "start" else -6)):.1f}" y="{ez(hh*fh)+4:.1f}" font-size="11" fill="var(--arch)" text-anchor="{anchor}" {HALO}>{hh:.0f} in</text>')
av.append(f'<text x="{ex(a0["xc"]):.1f}" y="{ez(a0["crown"])-8:.1f}" font-size="11" fill="var(--arch)" text-anchor="middle">crown {a0["crown"]:.0f} in above grade</text>')
LBL = ex(X_LO) - 8
av.append(f'<text x="{LBL:.1f}" y="{ez(TRELLIS_ABOVE)+4:.1f}" font-size="11" fill="currentColor" text-anchor="end">post top {TRELLIS_ABOVE:g} in, level with the crown</text>')
av.append(f'<text x="{LBL:.1f}" y="{ez(CROSS_LO)+4:.1f}" font-size="11" fill="var(--arch)" text-anchor="end">panel crosses the posts at {CROSS_LO:.0f} to {CROSS_HI:.0f} in</text>')
av.append(f'<text x="{LBL:.1f}" y="{ez(a0["spring"])+4:.1f}" font-size="11" fill="var(--arch)" text-anchor="end">curve starts {HOG_LEG:.0f} in up the leg</text>')
av.append(f'<text x="{LBL:.1f}" y="{ez(STAKE_ABOVE)+4:.1f}" font-size="11" fill="currentColor" text-anchor="end">stakes {STAKE_ABOVE:g} in above grade</text>')
av.append(f'<text x="{LBL:.1f}" y="{ez(a0["feet"])+4:.1f}" font-size="11" fill="var(--arch)" text-anchor="end">feet on the sills, {a0["feet"]:g} in above grade</text>')
av.append(f'<text x="{LBL:.1f}" y="{ez(-TRELLIS_EMBED/2)+4:.1f}" font-size="11" fill="currentColor" text-anchor="end">posts {TRELLIS_EMBED:g} in in the ground, stakes {STAKE_EMBED:g}</text>')
av.append(f'<text x="{ex(X_HI)-2:.1f}" y="{ez(0)-4:.1f}" font-size="10" fill="currentColor" opacity="0.7" text-anchor="end">grade</text>')
av.append('</svg>')
ARCH_ELEV_SVG = '\n'.join(av)
arch_elev_caption = (f"{list(arch_comps.keys())[0]} seen from the near end: {HOGWIRE_LEN/12:g} ft panel, {a0['chord']:.0f} in between the legs, feet on the {POST_NOM} sills at the bed centrelines, "
                     f"{a0['feet']:g} in above grade. The two inside corner posts are {ft_in(TRELLIS_LEN)} {POST_NOM}s with {TRELLIS_EMBED:g} in in the ground; the panel's edge wire crosses "
                     f"their faces at {CROSS_LO:.0f} to {CROSS_HI:.0f} in and their tops stand level with the {a0['crown']:.0f} in crown. The near stake of each sill is in front of the panel. "
                     f"Blue dots mark headroom at the walkway edges and centre.")

# ---- arch foot, seen from the walkway looking into Bed B along its centreline: end board, stakes, sill, the bottom of the panel ----
F_K = 5.0
fx0, fz0 = 16, 22
f_sill = next((x for r in a0['beds'] for x in r['sills'] if under_panel(x)), None)
f_stakes = sorted((x for r in a0['beds'] for x in r['stakes'] if f_sill and under_panel(x) and abs(x['min'][0] - f_sill['min'][0]) < 0.01),
                  key=lambda b: -b['max'][1]) if f_sill else []
FY_HI = 2.5                                                           # just outside the end board at y = 0
FY_LO = (f_stakes[-1]['min'][1] if f_stakes else -70.0) - 4.5
FZ_LO, FZ_HI = -STAKE_EMBED - 4.0, 26.0


def fx(y):
    return fx0 + (FY_HI - y) * F_K          # near end at the left


def fz(z):
    return fz0 + (FZ_HI - z) * F_K


FW, FH = int(fx(FY_LO) + 232), int(fz(FZ_LO) + 40)
fg = []
fg.append(f'<svg viewBox="0 0 {FW} {FH}" role="img" aria-label="Side view of an arch foot: the end board, a {STAKE_LEN:g} in stake against it, the {SILL_LEN:g} in sill on grade, a second stake at the far end, and the bottom of the panel standing on the sill between the stakes with its screws" xmlns="http://www.w3.org/2000/svg">')
fg.append(f'<rect x="{fx(FY_HI):.1f}" y="{fz(0):.1f}" width="{(FY_HI-FY_LO)*F_K:.1f}" height="{(0-FZ_LO)*F_K:.1f}" fill="currentColor" opacity="0.05"/>')
fg.append(f'<rect x="{fx(-T):.1f}" y="{fz(BED_H):.1f}" width="{(-T-FY_LO)*F_K:.1f}" height="{BED_H*F_K:.1f}" fill="var(--lumber)" opacity="0.08"/>')
fg.append(f'<line x1="{fx(FY_HI):.1f}" y1="{fz(0):.1f}" x2="{fx(FY_LO):.1f}" y2="{fz(0):.1f}" stroke="currentColor" stroke-width="1"/>')
fg.append(f'<rect x="{fx(0):.1f}" y="{fz(BED_H):.1f}" width="{T*F_K:.1f}" height="{BED_H*F_K:.1f}" fill="var(--lumber)" opacity="0.5" stroke="var(--lumber)" stroke-width="1.5"/>')
for b in f_stakes:
    fg.append(f'<rect x="{fx(b["max"][1]):.1f}" y="{fz(b["max"][2]):.1f}" width="{(b["max"][1]-b["min"][1])*F_K:.1f}" height="{b["max"][2]*F_K:.1f}" fill="var(--lumber)" opacity="0.9" stroke="currentColor" stroke-width="1"/>')
    fg.append(f'<rect x="{fx(b["max"][1]):.1f}" y="{fz(0):.1f}" width="{(b["max"][1]-b["min"][1])*F_K:.1f}" height="{-b["min"][2]*F_K:.1f}" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="4 3"/>')
if f_sill:
    fg.append(f'<rect x="{fx(f_sill["max"][1]):.1f}" y="{fz(f_sill["max"][2]):.1f}" width="{(f_sill["max"][1]-f_sill["min"][1])*F_K:.1f}" height="{(f_sill["max"][2]-f_sill["min"][2])*F_K:.1f}" fill="var(--lumber)" opacity="0.9" stroke="currentColor" stroke-width="1"/>')
# the panel: long wires 4 in apart rising from the sill, cross wires every 4 in; the bottom cross wire lies on the sill
y_edge = a0['ymax'] - WIRE_R
y_far = y_edge - 4 * (a0['wires'] - 1)
for i in range(a0['wires']):
    yy = y_edge - 4 * i
    fg.append(f'<line x1="{fx(yy):.1f}" y1="{fz(a0["feet"]):.1f}" x2="{fx(yy):.1f}" y2="{fz(FZ_HI-1.5):.1f}" stroke="var(--arch)" stroke-width="2" opacity="0.85"/>')
zz = a0['feet'] + WIRE_R
cross_z = []
while zz < FZ_HI - 1.5:
    fg.append(f'<line x1="{fx(y_edge):.1f}" y1="{fz(zz):.1f}" x2="{fx(y_far):.1f}" y2="{fz(zz):.1f}" stroke="var(--arch)" stroke-width="1.5" opacity="0.85"/>')
    cross_z.append(zz)
    zz += 4
# screws: down into the sill beside the bottom wire, sideways into each stake beside two cross wires, and through each stake into the sill end (blue dashed)
for i in range(PANEL_SCREWS_PER_SILL):
    yy = y_edge - (y_edge - y_far) * (i + 0.5) / PANEL_SCREWS_PER_SILL
    fg.append(f'<line x1="{fx(yy):.1f}" y1="{fz(4.6):.1f}" x2="{fx(yy):.1f}" y2="{fz(0.4):.1f}" stroke="currentColor" stroke-width="2" marker-end="url(#scr)"/>')
stake_screw_z = cross_z[1:1 + PANEL_SCREWS_PER_STAKE]
for b in f_stakes:
    inward = 1 if b['max'][1] > (y_edge + y_far) / 2 else -1     # the panel is on the -y side of the near stake, the +y side of the far one
    face = b['min'][1] if inward > 0 else b['max'][1]
    for zz in stake_screw_z:
        fg.append(f'<line x1="{fx(face - inward*2.4):.1f}" y1="{fz(zz):.1f}" x2="{fx(face + inward*1.15):.1f}" y2="{fz(zz):.1f}" stroke="currentColor" stroke-width="2" marker-end="url(#scr)"/>')
    back = b['max'][1] if inward > 0 else b['min'][1]
    fg.append(f'<line x1="{fx(back + inward*1.2):.1f}" y1="{fz(T/2):.1f}" x2="{fx(face - inward*1.4):.1f}" y2="{fz(T/2):.1f}" stroke="var(--arch)" stroke-width="2" stroke-dasharray="5 3" marker-end="url(#scrb)"/>')
LFX = fx(FY_LO) + 8
fg.append(f'<text x="{LFX:.1f}" y="{fz(23.5)+4:.1f}" font-size="11" fill="var(--arch)">panel: long wires 4 in apart rise</text>')
fg.append(f'<text x="{LFX:.1f}" y="{fz(21.0)+4:.1f}" font-size="11" fill="var(--arch)">from the sill, cross wires every 4 in</text>')
fg.append(f'<text x="{LFX:.1f}" y="{fz(STAKE_ABOVE)+4:.1f}" font-size="11" fill="currentColor">stake top, {STAKE_ABOVE - a0["feet"]:g} in above the sill</text>')
fg.append(f'<text x="{LFX:.1f}" y="{fz(sum(stake_screw_z)/len(stake_screw_z))+4:.1f}" font-size="11" fill="currentColor">{PANEL_SCREW} screw + 1 in washer, {PANEL_SCREWS_PER_STAKE} per stake</text>')
fg.append(f'<text x="{LFX:.1f}" y="{fz(3.3)+4:.1f}" font-size="11" fill="currentColor">{PANEL_SCREWS_PER_SILL} more along the sill, beside the bottom wire</text>')
fg.append(f'<text x="{LFX:.1f}" y="{fz(0.2)+4:.1f}" font-size="11" fill="var(--arch)">{STAKE_SILL_SCREWS} x #9 3 in through each stake into the sill end</text>')
fg.append(f'<text x="{LFX:.1f}" y="{fz(-STAKE_EMBED/2)+4:.1f}" font-size="11" fill="currentColor">stakes {STAKE_EMBED:g} in in the ground, sill on grade</text>')
fg.append(f'<text x="{fx(-35):.1f}" y="{fz(BED_H-3)+4:.1f}" font-size="11" fill="currentColor" opacity="0.75" text-anchor="middle" {HALO}>soil, once the bed is filled</text>')
by = fz(FZ_LO) + 14
fg.append(f'<text x="{fx(-1.5):.1f}" y="{by:.1f}" font-size="10" fill="currentColor" text-anchor="start">end board, near stake</text>')
if f_sill:
    fg.append(f'<text x="{fx((f_sill["max"][1]+f_sill["min"][1])/2):.1f}" y="{by+14:.1f}" font-size="10" fill="currentColor" text-anchor="middle">sill, {SILL_LEN:g} in</text>')
if f_stakes:
    fg.append(f'<text x="{fx(f_stakes[-1]["max"][1]):.1f}" y="{by:.1f}" font-size="10" fill="currentColor" text-anchor="end">far stake</text>')
fg.append('</svg>')
FOOT_SVG = '\n'.join(fg)
foot_caption = (f"Arch foot, seen from the walkway along the bed centreline with the near end at the left: the {SILL_LEN:g} in {POST_NOM} sill lies flat on grade between two "
                f"{STAKE_LEN:g} in stakes with {STAKE_EMBED:g} in in the ground. The panel's bottom wire lies on the sill and its edge wires stand against the stake faces; "
                f"{PANEL_SCREW} screws with 1 in fender washers pin them, and {STAKE_SILL_SCREWS} x 3 in screws through each stake into the sill's end grain tie the three pieces "
                f"together before the end board goes on. The soil then buries all of it.")

# ---- top of a trellis post, seen from inside the bed looking at the near end: the panel's edge wire crossing the post face ----
c0 = min(cross0, key=lambda c: c['x0']) if cross0 else None       # Bed A's post: the crown lies to its right in this view
T_K = 14.0
tx0, tz0 = 16, 20
if c0:
    TX_LO, TX_HI = c0['x0'] - 3.0, c0['x1'] + 9.0
    TZ_LO, TZ_HI = CROSS_LO - 9.0, TRELLIS_ABOVE + 4.0
else:
    TX_LO, TX_HI, TZ_LO, TZ_HI = 0.0, 15.5, 0.0, 17.0


def tx(x):
    return tx0 + (x - TX_LO) * T_K


def tz(z):
    return tz0 + (TZ_HI - z) * T_K


TW, TH = int(tx(TX_HI) + 236), int(tz(TZ_LO) + 30)
tp = []
tp.append(f'<svg viewBox="0 0 {TW} {TH}" role="img" aria-label="Top of a trellis post: the panel edge wire crosses the post face at {CROSS_LO:.0f} to {CROSS_HI:.0f} in above grade, the post ends {POST_TOP_ABOVE_CROSS:.0f} in higher, two screws with washers hold the wire" xmlns="http://www.w3.org/2000/svg">')
if c0:
    hfun = a0['h']
    tp.append(f'<rect x="{tx(c0["x0"]):.1f}" y="{tz(TRELLIS_ABOVE):.1f}" width="{(c0["x1"]-c0["x0"])*T_K:.1f}" height="{(TRELLIS_ABOVE-TZ_LO)*T_K:.1f}" fill="var(--lumber)" opacity="0.9" stroke="currentColor" stroke-width="1"/>')
    pts = []
    xx = TX_LO
    while xx <= TX_HI + 1e-9:
        pts.append(f'{tx(xx):.1f} {tz(hfun(xx)):.1f}')
        xx += 0.5
    tp.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="var(--arch)" stroke-width="{2*WIRE_R*T_K:.1f}" stroke-linecap="round"/>')
    xa, xb = c0['x0'] + 0.9, c0['x1'] - 0.9
    for (sx_, dz) in ((xa, 0.55), (xb, -0.55)):          # one washer each side of the wire, overlapping it
        zz = hfun(sx_) + dz
        tp.append(f'<circle cx="{tx(sx_):.1f}" cy="{tz(zz):.1f}" r="{0.5*T_K:.1f}" fill="var(--panel)" fill-opacity="0.85" stroke="currentColor" stroke-width="1.5"/>')
        tp.append(f'<circle cx="{tx(sx_):.1f}" cy="{tz(zz):.1f}" r="{0.14*T_K:.1f}" fill="currentColor"/>')
    LTX = tx(TX_HI) + 8
    tp.append(f'<text x="{LTX:.1f}" y="{tz(TRELLIS_ABOVE)+4:.1f}" font-size="11" fill="currentColor">post top, {TRELLIS_ABOVE:g} in above grade</text>')
    tp.append(f'<text x="{LTX:.1f}" y="{tz(CROSS_HI)+4:.1f}" font-size="11" fill="var(--arch)">wire leaves the face at {CROSS_HI:.0f} in</text>')
    tp.append(f'<text x="{LTX:.1f}" y="{tz(CROSS_LO)+4:.1f}" font-size="11" fill="var(--arch)">and enters it at {CROSS_LO:.0f} in</text>')
    tp.append(f'<text x="{LTX:.1f}" y="{tz(CROSS_LO-3.2)+4:.1f}" font-size="11" fill="currentColor">{PANEL_SCREW} screw + 1 in washer,</text>')
    tp.append(f'<text x="{LTX:.1f}" y="{tz(CROSS_LO-4.4)+4:.1f}" font-size="11" fill="currentColor">one each side of the wire</text>')
    tp.append(f'<text x="{LTX:.1f}" y="{tz(TZ_LO+1.2)+4:.1f}" font-size="11" fill="currentColor" opacity="0.75">the crown is off to the right</text>')
    tp.append(f'<text x="{tx((c0["x0"]+c0["x1"])/2):.1f}" y="{tz(TZ_LO)+16:.1f}" font-size="10" fill="currentColor" text-anchor="middle">{PW:g} in post face</text>')
tp.append('</svg>')
TOP_SVG = '\n'.join(tp)
top_caption = (f"Top of a trellis post, seen from inside the bed: the panel's edge wire climbs across the post's {PW:g} in face between {CROSS_LO:.0f} and {CROSS_HI:.0f} in above grade "
               f"and the post ends {POST_TOP_ABOVE_CROSS:.0f} in higher, level with the crown. Two {PANEL_SCREW} screws with washers, one each side of the wire, hold it; "
               f"1.25 in stays inside the post's {PT:g} in thickness, so nothing pokes out of its back at the near end.")

# ---- drip riser, side view: looking west along the far end wall, the outside of the bed at the left ----
DRIP_SIDE_SVG = DRIP_BACK_SVG = ''
drip_side_caption = drip_back_caption = ''
if risers:
    DR_K = 12
    dr_so, dr_zt_, dr_zv, dr_zm = r0['standoff'], r0['through_z'], r0['valve_z'], -r0['main_depth']
    dr_mo, dr_cl, dr_zh, dr_zhb = r0['main_offset'], r0['clamps'], r0['head_top'], r0['head_bottom']
    dr_yo = dr_mo + 2.5                 # inches shown beyond the wall (outside, drawn to the left)
    dr_yi = 5.5                         # inches of the bed inside shown
    dr_zb = r0['main_depth'] + 2.0      # below grade shown
    dr_zt = dr_zh + 1.6
    dr_x0, dr_y0 = 212, 14
    HUB, PR, HR, SOCK = 1.0, 0.42, 0.585, 0.75   # 1/2 in fittings as modelled: hub length from the centre, pipe and hub radii, socket depth
    P34R, H34R = 0.525, 0.70

    def drx(y):
        return dr_x0 + (y + dr_yo) * DR_K

    def drz(z):
        return dr_y0 + (dr_zt - z) * DR_K

    DRW = int(dr_x0 + (dr_yo + T + dr_yi) * DR_K + 232)
    DRH = int(dr_y0 + (dr_zt + dr_zb) * DR_K + 26)
    PS = 'fill="var(--panel)" stroke="currentColor" stroke-width="1.2"'

    def vrect(y0, y1, z0, z1, style, rx=0):
        return (f'<rect x="{drx(min(y0, y1)):.1f}" y="{drz(max(z0, z1)):.1f}" width="{abs(y1 - y0) * DR_K:.1f}" '
                f'height="{abs(z1 - z0) * DR_K:.1f}" rx="{rx}" {style}/>')

    def velbow(yc, zc, dy, dz):
        out = []
        if dy:
            out.append(vrect(yc, yc + dy * HUB, zc - HR, zc + HR, PS, 2))
        if dz:
            out.append(vrect(yc - HR, yc + HR, zc, zc + dz * HUB, PS, 2))
        out.append(f'<circle cx="{drx(yc):.1f}" cy="{drz(zc):.1f}" r="{HR * DR_K:.1f}" {PS}/>')
        return '\n'.join(out)

    dv = []
    dv.append(f'<svg viewBox="0 0 {DRW} {DRH}" role="img" aria-label="Side view of a drip riser at the far end wall of a bed: the buried 3/4 in main and reducer tee outside, 1/2 in pipe up the outside of the wall through a ball valve held by two clamps, an elbow through a hole in the top board, and a 4-port drip head standing inside the bed" xmlns="http://www.w3.org/2000/svg">')
    dv.append(vrect(-dr_yo, T + dr_yi, -dr_zb, 0, 'fill="currentColor" opacity="0.06"'))
    dv.append(vrect(T, T + dr_yi, 0, WALL_TOP - 1.0, 'fill="var(--lumber)" opacity="0.12"'))
    dv.append(f'<line x1="{drx(-dr_yo):.1f}" y1="{drz(0):.1f}" x2="{drx(T + dr_yi):.1f}" y2="{drz(0):.1f}" stroke="currentColor" stroke-width="1" stroke-dasharray="5 3" opacity="0.7"/>')
    for c in range(COURSES):
        dv.append(vrect(0, T, c * BOARD_W, (c + 1) * BOARD_W, 'fill="var(--lumber)" opacity="0.55" stroke="var(--lumber)" stroke-width="1.2"'))
    dv.append(vrect(-0.15, T + 0.15, dr_zt_ - HOLE_DIA / 2, dr_zt_ + HOLE_DIA / 2, 'fill="var(--panel)" stroke="var(--arch)" stroke-width="1.3" stroke-dasharray="3 2"'))
    # pipes, then fittings on top of their ends
    dv.append(vrect(-dr_mo + HUB - SOCK, -dr_so - (HUB - SOCK), dr_zm - PR, dr_zm + PR, PS))
    dv.append(vrect(-dr_so - PR, -dr_so + PR, dr_zm + HUB - SOCK, dr_zv - 1.5 + SOCK, PS))
    dv.append(vrect(-dr_so - PR, -dr_so + PR, dr_zv + 1.5 - SOCK, dr_zt_ - (HUB - SOCK), PS))
    dv.append(vrect(-dr_so + HUB - SOCK, T + dr_so - (HUB - SOCK), dr_zt_ - PR, dr_zt_ + PR, PS))
    dv.append(vrect(T + dr_so - PR, T + dr_so + PR, dr_zt_ + HUB - SOCK, dr_zhb + SOCK, PS))
    dv.append(vrect(-dr_mo, -dr_mo + HUB, dr_zm - HR, dr_zm + HR, PS, 2))
    dv.append(f'<circle cx="{drx(-dr_mo):.1f}" cy="{drz(dr_zm):.1f}" r="{H34R * DR_K:.1f}" {PS}/>')
    dv.append(f'<circle cx="{drx(-dr_mo):.1f}" cy="{drz(dr_zm):.1f}" r="{P34R * DR_K:.1f}" fill="none" stroke="currentColor" stroke-width="0.8" opacity="0.6"/>')
    dv.append(velbow(-dr_so, dr_zm, -1, 1))
    dv.append(velbow(-dr_so, dr_zt_, 1, -1))
    dv.append(velbow(T + dr_so, dr_zt_, -1, 1))
    dv.append(vrect(-dr_so - HR, -dr_so + HR, dr_zv - 1.5, dr_zv + 1.5, PS, 2))
    dv.append(vrect(-dr_so - 0.8, -dr_so + 0.8, dr_zv - 1.0, dr_zv + 1.0, PS, 3))
    dv.append(f'<line x1="{drx(-dr_so - 0.8):.1f}" y1="{drz(dr_zv):.1f}" x2="{drx(-dr_so - 1.3):.1f}" y2="{drz(dr_zv):.1f}" stroke="currentColor" stroke-width="2.5"/>')
    dv.append(f'<circle cx="{drx(-dr_so - 1.52):.1f}" cy="{drz(dr_zv):.1f}" r="{0.23 * DR_K:.1f}" {PS}/>')
    for cz in dr_cl:
        dv.append(vrect(-(dr_so + PR + 0.2), 0, cz - 0.5, cz + 0.5, 'fill="currentColor" opacity="0.5" stroke="currentColor" stroke-width="1"'))
    dv.append(vrect(T + dr_so - 0.625, T + dr_so + 0.625, dr_zhb, dr_zh, PS, 2))
    for sgn_ in (-1, 1):
        y_a = T + dr_so + sgn_ * 0.6
        dv.append(vrect(y_a, y_a + sgn_ * 0.6, dr_zh - 0.58, dr_zh - 0.32, PS))
    # labels: outside features at the left (right-aligned, leader to the feature), inside features at the right
    LX = dr_x0 - 10

    def llabel(z, text, y_to, z_to=None, color='currentColor'):
        zz = z if z_to is None else z_to
        return (f'<line x1="{LX + 4:.1f}" y1="{drz(z):.1f}" x2="{drx(y_to):.1f}" y2="{drz(zz):.1f}" stroke="{color}" stroke-width="0.9" opacity="0.8"/>'
                f'<text x="{LX:.1f}" y="{drz(z) + 4:.1f}" font-size="12" fill="{color}" text-anchor="end" {HALO}>{text}</text>')

    RX = drx(T + dr_yi) + 8

    def rlabel(z, text, y_to, z_to=None, color='currentColor'):
        zz = z if z_to is None else z_to
        return (f'<line x1="{RX - 4:.1f}" y1="{drz(z):.1f}" x2="{drx(y_to):.1f}" y2="{drz(zz):.1f}" stroke="{color}" stroke-width="0.9" opacity="0.8"/>'
                f'<text x="{RX:.1f}" y="{drz(z) + 4:.1f}" font-size="12" fill="{color}" {HALO}>{text}</text>')

    dv.append(llabel(dr_zt_ + 1.45, '1/2 in elbows each side of the wall', -dr_so - HR, dr_zt_ + 0.4))
    dv.append(llabel(dr_zt_ - 0.05, f'{HOLE_DIA:g} in hole, {frac(dr_zt_)} in up', -0.15, color='var(--arch)'))
    dv.append(llabel(dr_cl[1], f'clamp {frac(dr_cl[1])} in up, {frac(r0["pipes"]["upper riser"])} in pipe above', -(dr_so + PR + 0.2)))
    dv.append(llabel(dr_zv, f'ball valve {frac(dr_zv)} in up', -dr_so - 1.52 - 0.23))
    dv.append(llabel(dr_cl[0], f'clamp {frac(dr_cl[0])} in up, {frac(r0["pipes"]["lower riser"])} in pipe', -(dr_so + PR + 0.2)))
    dv.append(f'<text x="{LX:.1f}" y="{drz(0) + 4:.1f}" font-size="12" fill="currentColor" text-anchor="end" opacity="0.8">grade</text>')
    dv.append(llabel(dr_zm + 1.35, f'{frac(r0["pipes"]["ground"])} in pipe on the main', -(dr_mo + dr_so) / 2, dr_zm + PR))
    dv.append(llabel(dr_zm - 0.1, f'3/4 x 1/2 tee, {frac(dr_mo)} in out, {frac(-dr_zm)} in deep', -dr_mo - H34R))
    dv.append(rlabel(dr_zh - 0.2, f'4-port 1/4 in head, top {frac(dr_zh)} in', T + dr_so + 1.2, dr_zh - 0.45))
    dv.append(rlabel(WALL_TOP - 0.2, f'wall top {frac(WALL_TOP)} in, soil about 1 in below', T, WALL_TOP))
    dv.append(rlabel(dr_zt_ + 1.65, f'{frac(r0["pipes"]["head"])} in pipe inside the bed', T + dr_so + PR, dr_zt_ + 2.2))
    dv.append(rlabel(dr_zt_ + 0.25, 'elbow hub 1/4 in clear of the board', T + dr_so + HR, dr_zt_ + 0.5))
    dv.append(f'<text x="{drx(T + dr_yi / 2 + 0.75):.1f}" y="{drz(3.5):.1f}" font-size="12" fill="currentColor" text-anchor="middle" opacity="0.7">bed soil</text>')
    dv.append(f'<text x="{drx(-dr_yo + 0.3):.1f}" y="{drz(-dr_zb) - 6:.1f}" font-size="11" fill="currentColor" opacity="0.7">outside the bed at the left, inside at the right</text>')
    dv.append('</svg>')
    DRIP_SIDE_SVG = '\n'.join(dv)
    drip_side_caption = (f"Side view at a far end wall, outside at the left: the reducer tee on the buried main, {frac(r0['pipes']['ground'])} in of pipe to the elbow, the riser up the "
                         f"outside of the wall through the ball valve between its two clamps, the elbow through the {HOLE_DIA:g} in hole in the top board, and the head on "
                         f"{frac(r0['pipes']['head'])} in of pipe inside the bed. The dashed outline is the hole.")

    # ---- back view: the far end wall seen from outside the bed (looking toward the walkway), west at the left ----
    BK = 8.5
    bk_x0, bk_y0 = 30, 26
    bk_W = r0['bed_row']['W']
    bk_zt, bk_zb = dr_zh + 1.4, r0['main_depth'] + 2.6

    def bkx(x):
        return bk_x0 + x * BK

    def bkz(z):
        return bk_y0 + (bk_zt - z) * BK

    BKW = int(bk_x0 + bk_W * BK + 30)
    BKH = int(bk_y0 + (bk_zt + bk_zb) * BK + 22)
    xr = r0['x_off']

    def brect(x0, x1, z0, z1, style, rx=0):
        return (f'<rect x="{bkx(min(x0, x1)):.1f}" y="{bkz(max(z0, z1)):.1f}" width="{abs(x1 - x0) * BK:.1f}" '
                f'height="{abs(z1 - z0) * BK:.1f}" rx="{rx}" {style}/>')

    bv = []
    bv.append(f'<svg viewBox="0 0 {BKW} {BKH}" role="img" aria-label="Back view of a bed\'s far end wall from outside: the side board ends, the two end boards with the corner posts dashed behind them, the riser {frac(xr)} in from the west face with its clamps and ball valve, the hole behind the upper elbow, the head showing above the wall, and the buried main dashed below grade" xmlns="http://www.w3.org/2000/svg">')
    bv.append('<defs><marker id="bdim" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M2 1 L8 5 L2 9" fill="none" stroke="currentColor" stroke-width="1.4"/></marker></defs>')
    bv.append(brect(-2, bk_W + 2, -bk_zb, 0, 'fill="currentColor" opacity="0.06"'))
    bv.append(f'<line x1="{bkx(-2):.1f}" y1="{bkz(0):.1f}" x2="{bkx(bk_W + 2):.1f}" y2="{bkz(0):.1f}" stroke="currentColor" stroke-width="1" stroke-dasharray="5 3" opacity="0.7"/>')
    bv.append(f'<line x1="{bkx(-2):.1f}" y1="{bkz(dr_zm):.1f}" x2="{bkx(bk_W + 2):.1f}" y2="{bkz(dr_zm):.1f}" stroke="currentColor" stroke-width="2.5" stroke-dasharray="7 4" opacity="0.5"/>')
    for c in range(COURSES):
        bv.append(brect(T, bk_W - T, c * BOARD_W, (c + 1) * BOARD_W, 'fill="var(--lumber)" opacity="0.5" stroke="var(--lumber)" stroke-width="1.2"'))
        for xa in (0, bk_W - T):
            bv.append(brect(xa, xa + T, c * BOARD_W, (c + 1) * BOARD_W, 'fill="var(--lumber)" opacity="0.85" stroke="var(--lumber)" stroke-width="1.2"'))
    for xa in (T, bk_W - T - PW):
        bv.append(brect(xa, xa + PW, 0, WALL_TOP, 'fill="none" stroke="currentColor" stroke-width="1.1" stroke-dasharray="4 3" opacity="0.8"'))
    # the head above the wall, the riser and its fittings
    bv.append(brect(xr - 0.625, xr + 0.625, WALL_TOP, dr_zh, PS, 2))
    for sgn_ in (-1, 1):
        bv.append(brect(xr + sgn_ * 0.6, xr + sgn_ * 1.2, dr_zh - 0.58, dr_zh - 0.32, PS))
    bv.append(brect(xr - PR, xr + PR, dr_zm + HUB - SOCK, dr_zt_ - (HUB - SOCK), PS))
    bv.append(brect(xr - HR, xr + HR, dr_zm - HR, dr_zm + HUB, PS, 2))
    bv.append(f'<circle cx="{bkx(xr):.1f}" cy="{bkz(dr_zm):.1f}" r="{HR * BK:.1f}" {PS}/>')
    bv.append(brect(xr - HR, xr + HR, dr_zt_ - HUB, dr_zt_ + HR, PS, 2))
    bv.append(f'<circle cx="{bkx(xr):.1f}" cy="{bkz(dr_zt_):.1f}" r="{HR * BK:.1f}" {PS}/>')
    bv.append(f'<circle cx="{bkx(xr):.1f}" cy="{bkz(dr_zt_):.1f}" r="{HOLE_DIA / 2 * BK:.1f}" fill="none" stroke="var(--arch)" stroke-width="1.3" stroke-dasharray="3 2"/>')
    bv.append(brect(xr - HR, xr + HR, dr_zv - 1.5, dr_zv + 1.5, PS, 2))
    bv.append(brect(xr - 0.8, xr + 0.8, dr_zv - 1.0, dr_zv + 1.0, PS, 3))
    bv.append(f'<circle cx="{bkx(xr):.1f}" cy="{bkz(dr_zv):.1f}" r="{0.2 * BK:.1f}" {PS}/>')
    bv.append(brect(xr - 0.2 - 2.4, xr - 0.2, dr_zv - 0.15, dr_zv + 0.15, PS))
    for cz in dr_cl:
        bv.append(brect(xr - 1.25, xr + 1.25, cz - 0.5, cz + 0.5, 'fill="currentColor" opacity="0.5" stroke="currentColor" stroke-width="1"'))
        for sgn_ in (-1, 1):
            bv.append(f'<circle cx="{bkx(xr + sgn_ * 0.9):.1f}" cy="{bkz(cz):.1f}" r="2" fill="var(--panel)"/>')
    # dimension: riser from the west outside face, drawn below grade
    zd = -1.4
    bv.append(f'<line x1="{bkx(0):.1f}" y1="{bkz(zd):.1f}" x2="{bkx(xr):.1f}" y2="{bkz(zd):.1f}" stroke="currentColor" stroke-width="1" marker-start="url(#bdim)" marker-end="url(#bdim)"/>')
    bv.append(f'<text x="{bkx(xr / 2):.1f}" y="{bkz(zd) + 14:.1f}" font-size="12" fill="currentColor" text-anchor="middle" {HALO}>{frac(xr)} in</text>')
    LXB = bkx(xr + 3.2)

    def blabel(z, text, x_to, z_to=None, color='currentColor'):
        zz = z if z_to is None else z_to
        return (f'<line x1="{LXB - 4:.1f}" y1="{bkz(z):.1f}" x2="{bkx(x_to):.1f}" y2="{bkz(zz):.1f}" stroke="{color}" stroke-width="0.9" opacity="0.8"/>'
                f'<text x="{LXB:.1f}" y="{bkz(z) + 4:.1f}" font-size="12" fill="{color}" {HALO}>{text}</text>')

    bv.append(blabel(dr_zh - 0.3, f'head above the soil, barbs {frac(round((dr_zh - 0.45 - WALL_TOP) * 4) / 4)} in up', xr + 1.2, dr_zh - 0.45))
    bv.append(blabel(dr_zt_ + 0.1, f'{HOLE_DIA:g} in hole behind the elbow (dashed)', xr + HR, color='var(--arch)'))
    bv.append(blabel(dr_cl[1], 'stand-off clamp, 2 screws into one board', xr + 1.25))
    bv.append(blabel(dr_zv, 'ball valve, lever west along the wall', xr + 0.8))
    bv.append(blabel(dr_cl[0], 'second clamp on the bottom board', xr + 1.25))
    bv.append(blabel(dr_zm - 1.6, f'3/4 in main {frac(-dr_zm)} in down (dashed); its branch comes toward you', xr + HR, dr_zm - 0.4))
    bv.append(f'<text x="{bkx(bk_W - T - PW / 2):.1f}" y="{bkz(WALL_TOP / 2):.1f}" font-size="11" fill="currentColor" text-anchor="middle" transform="rotate(-90 {bkx(bk_W - T - PW / 2):.1f} {bkz(WALL_TOP / 2):.1f})" opacity="0.8">corner post behind</text>')
    bv.append(f'<text x="{bkx(bk_W + 2) - 2:.1f}" y="{bkz(0) + 13:.1f}" font-size="11" fill="currentColor" text-anchor="end" opacity="0.7">grade</text>')
    bv.append('</svg>')
    DRIP_BACK_SVG = '\n'.join(bv)
    drip_back_caption = (f"Back view of a far end wall from outside the bed (west at the left): side board ends, the two end boards with the corner posts dashed behind them, "
                         f"the riser {frac(xr)} in from the west face with its clamps and valve, the {HOLE_DIA:g} in hole behind the upper elbow, the head above the wall, "
                         f"and the main dashed {frac(-dr_zm)} in below grade. Bed D's wall is 24 in wide; its riser sits at the same {frac(xr)} in.")


def tr(cells, head=False):
    tag = 'th' if head else 'td'
    return '<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>'


def num(v8, v10, fmt='{:.0f}', unit=''):
    return f'<span class="sw" data-v8="{fmt.format(v8)}{unit}" data-v10="{fmt.format(v10)}{unit}">{fmt.format(v8)}{unit}</span>'


def src_tag(s):
    s = str(s)
    cls = 'model' if s.startswith('Model') else ('derived' if s.startswith('Derived') else 'est')
    return f'<span class="src {cls}">{esc(s)}</span>'


shop_rows = ''.join(tr([esc(r[0]), esc(r[1]), f'<b>{esc(r[2])}</b>', esc(r[3]), esc(r[4]), src_tag(r[5]), esc(r[6])]) for r in rows)
shop_text = '\n'.join(f'{r[2]} {r[3]}  {r[1]}  [{r[5]}]' for r in rows)

def ufrac(x):
    whole = int(math.floor(x + 1e-9))
    rem = round(x - whole, 4)
    glyph = {0.5: '½', 0.25: '¼', 0.75: '¾', 0.125: '⅛', 0.375: '⅜', 0.625: '⅝', 0.875: '⅞'}.get(rem)
    if rem == 0:
        return f'{whole}'
    if glyph:
        return f'{whole}{glyph}' if whole else glyph
    return frac(x)


def bars_html(plan, nom, scale_len, toggle=False):
    parts = []
    for g in plan['sticks']:
        segs = []
        cls = 'post' if nom == POST_NOM else 'board'
        for c in g['cuts']:
            for _ in range(c['n']):
                segs.append(f'<span class="pc {cls}" style="flex-grow:{c["len"]:.3f}" title="{esc(c["label"])} {frac(c["len"])} in"><i>{ufrac(c["len"])}</i></span>')
        if g['offcut'] >= 0.5:
            segs.append(f'<span class="pc waste" style="flex-grow:{g["offcut"]:.3f}" title="offcut {frac(g["offcut"])} in"><i>{ufrac(g["offcut"]) if g["offcut"] >= 4 else ""}</i></span>')
        nom_html = f'<span class="nom">{esc(nom)}</span>' if toggle else esc(nom)
        price_html = num(g['price'], STOCK_IN_PRICES[ALT_NOM][g['stock']], '${:.2f}') if toggle else f"${g['price']:.2f}"
        parts.append(f'<div class="cutbar"><div class="stock"><b>{g["count"]} x</b> {nom_html} x {g["stock"]/12:g} ft <span class="muted">{price_html} each</span></div>'
                     f'<div class="bar" style="width:{g["stock"]/scale_len*100:.1f}%">{"".join(segs)}</div><div class="legend">{esc(cutstock.stick_text(g))}</div></div>')
    return f'<div class="cutbars">{"".join(parts)}</div>'


def options_html(r):
    lis = []
    for nom, opts, plan, toggle in ((NOM, r['opts_boards'], r['plan_boards'], True), (POST_NOM, r['opts_posts'], r['plan_posts'], False)):
        items = []
        for o in opts:
            cost = num(o['cost'], priced_as(o, ALT_NOM), '${:.2f}') if toggle else f"${o['cost']:.2f}"
            mark = option_mark(o, plan)
            items.append(f'{esc(option_label(o, nom))}: {sticks_txt(o["n_sticks"])}, {cost}, {frac(o["offcut"])} in offcut '
                         + (f'<b>({mark})</b>' if mark in ('chosen', 'same cost') else f'<span class="muted">({esc(mark)})</span>'))
        nom_html = f'<span class="nom">{esc(nom)}</span>' if toggle else esc(nom)
        lis.append(f'<li><b>{nom_html}</b>: ' + '<span class="sep">·</span>'.join(items) + '</li>')
    return '<p class="opts-h">Other ways to buy it</p><ul class="opts">' + ''.join(lis) + '</ul>'


bed_cards = []
for r, items in bed_lists:
    body = []
    scale = max(g['stock'] for p in (r['plan_boards'], r['plan_posts']) for g in p['sticks'])
    for g in BED_GROUPS:
        gi = [it for it in items if it['group'] == g]
        if not gi:
            continue
        head = esc(g)
        if g == 'Lumber':
            head += f' <span class="sub">{r["lumber_sticks"]} sticks, {num(r["lumber_cost"], r["lumber_cost_alt"], "${:.2f}")} at store prices</span>'
        body.append(f'<tr class="grp"><td colspan="5">{head}</td></tr>')
        for it in gi:
            cid = 'ck-' + it['key'].replace(':', '-')
            qty = num(it['qty'], it['qty_alt'], '{:g}') if it['qty_alt'] is not None else f"{it['qty']:g}"
            unit = '' if it['unit'] == 'ea' else f' <span class="muted">{esc(it["unit"])}</span>'
            item = num(esc(it['item']), esc(it['item_alt']), '{}') if it.get('item_alt') else esc(it['item'])
            spec = num(esc(it['spec']), esc(it['spec_alt']), '{}') if it.get('spec_alt') else esc(it['spec'])
            body.append(f'<tr><td class="ck"><input type="checkbox" id="{cid}" data-key="{esc(it["key"])}"></td>'
                        f'<td><label for="{cid}">{item}</label> {src_tag(it["source"])}</td>'
                        f'<td><b>{qty}</b>{unit}</td><td>{spec}</td><td>{esc(it["notes"])}</td></tr>')
        if g == 'Lumber':
            body.append(f'<tr class="cuts"><td colspan="5">{bars_html(r["plan_boards"], NOM, scale, toggle=True)}{bars_html(r["plan_posts"], POST_NOM, scale)}{options_html(r)}</td></tr>')
    bed_cards.append(f"""
<article class="card bed-card" id="bed-{r['letter'].lower()}" data-bed="{r['letter']}">
  <header><span class="letter">{r['letter']}</span><div class="grow"><h3>Bed {r['letter']} <small>{ft_in(r['L'])} x {r['W']:g} in</small></h3>
  <p class="muted">Inside {r['E']:g} x {r['inner_L']:g} in, {num(r['H'], r['H_alt'], '{:g}', ' in')} tall. {len(items)} lines.{f" Side walls: two boards per course ({esc(layout_txt(r))}) over {r['n_joint']} {JOINT_NOM} joint posts." if r['side_seams'] else ''} Replaces massing body "{MASSING[r['letter']]}".</p></div>
  <div class="check-state"><span class="count" aria-live="polite">0 of {len(items)} checked</span><button type="button" class="clear">Clear</button></div></header>
  <table class="checklist">
    <thead><tr><th class="ck"><span class="vh">Checked</span></th><th>Item</th><th>Qty</th><th>Spec / cut</th><th>Notes</th></tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table>
</article>""")

paver_rows = ''.join(tr([esc(k), f"<b>{g['n']}</b>", esc(PAVER_LABEL.get(k, ''))]) for k, g in paver_groups.items())
arch_rows = ''.join(tr([esc(k), esc(ARCH_BETWEEN.get(k, '')), f"{a['chord']:.0f} in", f"on {POST_NOM} sills, {a['feet']:g} in above grade", f"{HOG_LEG:.0f} in", f"{a['crown']:.0f} in", esc(a['posts']), esc(headroom(a)), f"{a['ymax']-a['ymin']-2*WIRE_R:.0f} in, {a['wires']} wires at 4 in"]) for k, a in arch_comps.items())
arch_html_paras = ''.join(f'<p>{esc(x)}</p>' for x in arch_paras)
hoop_html_paras = ''.join(f'<p>{esc(x)}</p>' for x in hoop_paras)
hoop_rows = (tr([f"Bed {hoop_bed_letter} ({ft_in(hoop_bed['L'])})", str(n_hoops), f'{hoop_pitch:g} in', f'{hoop_w - 1:.0f} in', f'{hoop_h:.0f} in', f'{HOOP_LEG:g} in',
                 f'{hoop_len:.0f} in ({hoop_len/12:.1f} ft)', f'{hoop_tube_ft:.0f} ft']) if n_hoops else tr(['none visible in the model'] + [''] * 7))
_n = hoops_model_note[2:]
for _k in ('Garden Hoops', 'Hoop'):
    _n = _n.replace(f'**{_k}**', f'<b>{_k}</b>')
_n = re.sub(r'`([^`]+)`', r'<code>\1</code>', esc(_n).replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>'))
hoops_model_note_html = f'<li>{_n}</li>'
drip_html_paras = ''.join(f'<p>{esc(x)}</p>' for x in drip_paras)
drip_rows = ''.join(tr([esc(k), esc(v)]) for k, v in drip_table) if risers else tr(['none in the model', ''])
_n = drip_model_note[2:]
for _k in ('Drip Irrigation', 'Drip riser', '3/4 in main (existing)'):
    _n = _n.replace(f'**{_k}**', f'<b>{_k}</b>')
_n = re.sub(r'`([^`]+)`', r'<code>\1</code>', esc(_n).replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>'))
drip_model_note_html = f'<li>{_n}</li>'
_n = re.sub(r'`([^`]+)`', r'<code>\1</code>', esc(split_model_note[2:]))
split_model_note_html = f'<li>{_n}</li>'
joint_fig_html = (f'<figure>\n      {JOINT_ELEV_SVG}\n      <figcaption>{esc(joint_elev_caption)}</figcaption>\n    </figure>' if split_beds else '')
soil_rows = ''.join(tr([f"Bed {r['letter']}", f"{r['E']:g} x {r['inner_L']:g} in", num(r['H'], r['H_alt'], '{:g}', ' in'), num(r['soil_ft3'], r['soil_alt_ft3'], '{:.1f}', ' cu ft')]) for r in bed_rows)
lumber_rows = ''.join(tr([(f'<span class="nom">{esc(x["nom"])}</span>' if x['nom'] == NOM else esc(x['nom'])) + f" x {x['ft']} ft", f"<b>{x['qty']}</b>",
                             num(x['price'], x['price_alt'], '${:.2f}') if x['price_alt'] is not None else f"${x['price']:.2f}",
                             num(x['price'] * x['qty'], x['price_alt'] * x['qty'], '${:.2f}') if x['price_alt'] is not None else f"${x['price'] * x['qty']:.2f}",
                             esc(x['use'])]) for x in stock_rows)
lumber_rows += tr(['<b>Total</b>', f'<b>{total_2x_boards + post_sticks}</b>', '', f'<b>{num(lumber_cost, lumber_cost_alt, "${:.2f}")}</b>', 'before tax, single-stick prices'])
combined_scale = max(g['stock'] for p in (combined_boards, combined_posts) for g in p['sticks'])
combined_bars = bars_html(combined_boards, NOM, combined_scale, toggle=True) + bars_html(combined_posts, POST_NOM, combined_scale)
screw_bed_rows = ''.join(tr([f"Bed {r['letter']}", str(r['posts_per_side']), str(r['corner_side_screws']), str(r['tie_screws']), str(r['anchor_screws']), str(r['mid_side_screws']), str(r['joint_screws']), str(r['end_screws']), str(r['panel_screws']), f"<b>{r['screws_3']+r['screws_25']+r['screws_125']}</b>"]) for r in bed_rows)
screw_bed_rows += tr(['<b>Total</b>', '', f"<b>{tot_corner_side}</b>", f"<b>{tot_tie}</b>", f"<b>{tot_anchor}</b>", f"<b>{tot_mid_side}</b>", f"<b>{tot_joint}</b>", f"<b>{tot_end}</b>", f"<b>{tot_panel}</b>", f"<b>{screws_total}</b>"])
screw_joint_rows = ''.join([
    tr(["Side board into a corner post edge", "<b>#9 x 3 in</b>",
        f"1.5 in through the board, 1.5 in into the post's {PW:g} in depth. The target is only {PT:g} in wide: mark the post centerline on the outside face before driving, {T+PT/2:g} in from the board end.",
        f"{SCREWS_PER_JOINT} per board per post"]),
    tr(["Side board into a mid-span post face", "<b>#9 x 2.5 in</b>",
        f"1.5 in through the board, 1 in into the post's {PT:g} in thickness; a 3 in screw would poke out the back. The face is {PW:g} in wide, so stagger the pair {MID_OFFSET:g} in either side of the post centerline, the lower screw to one side and the upper to the other. Drive the posts first, then screw the boards to them.",
        f"{SCREWS_PER_JOINT} per board per post"]),
    tr(["End board into a corner post face", "<b>#9 x 2.5 in</b>",
        f"Same joint as the mid-span posts: 1 in into the post's {PT:g} in thickness. Center them {T+PW/2:g} in from the board end.",
        f"{SCREWS_PER_JOINT} per board per post"]),
] + ([
    tr(["Side board end into a joint post face", "<b>#9 x 2.5 in</b>",
        f"The joint post is a {JOINT_NOM} offcut lying flat, {frac(JOINT_W)} in wide and {JOINT_T:g} in thick, so the screws are the mid-span length. Where two boards meet over it, each board end gets two screws {JOINT_OFF:g} in from the end at the usual heights (pre-drill: they are within 2 in of the end); a course that runs past the post gets the mid-span pair instead.",
        f"{2 * SCREWS_PER_JOINT} per course where boards meet, {SCREWS_PER_JOINT} where one runs past"]),
] if split_beds else []) + [
    tr(["Corner tie through the side board into the end board's end grain", "<b>#9 x 3 in</b>",
        f"Holds the corner closed. Pre-drill 1/8 in. Place at {TIE_HEIGHTS[0]:g} in and {TIE_HEIGHTS[1]:g} in up, {T/2:g} in from the board end, staggered off the post screws.",
        f"{TIES_PER_CORNER} per corner per course"]),
    tr(["Hog-wire panel to the trellis posts, arch stakes and sills", f"<b>{PANEL_SCREW}</b> + 1 in fender washer",
        f"The washer beside a wire traps it against the wood, and 1.25 in stays inside a 1.5 in post, stake or sill so no tip pokes out the back. At the post top, one screw each side of the edge wire where it crosses the face; on each stake, beside two cross wires; along the sill, beside the bottom wire.",
        f"{PANEL_SCREWS_PER_POST} per post, {PANEL_SCREWS_PER_STAKE} per stake, {PANEL_SCREWS_PER_SILL} per sill"]),
    tr(["Arch stake into the sill's end grain", "<b>#9 x 3 in</b>",
        f"1.5 in through the stake, 1.5 in into the sill end. Pre-drill 1/8 in and drive from the stake's back before the end board goes on, {T/2:g} in up, 1 in either side of center.",
        f"{STAKE_SILL_SCREWS} per stake"]),
])

CSS = r'''
:root {
  /* plan: a worksite ledger. Sturdy grotesque display, humanist body; orange = lumber, blue = arches and tie screws, hatched neutral = pavers. */
  --bg: #f4f3ef; --panel: #ffffff; --ink: #1d1f22; --muted: #5d6168; --line: #d6d4cc; --soft: #ebe9e2;
  --lumber: #eb6834; --arch: #2a78d6; --accent: #2a78d6; --focus: #2a78d6;
  --font-display: "Archivo", "Helvetica Neue", Arial, sans-serif;
  --font-body: "Source Sans 3", "Segoe UI", Roboto, sans-serif;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #1a1a19; --panel: #232322; --ink: #efeee9; --muted: #b3b1a8; --line: #3a3a37; --soft: #2c2c2a;
    --lumber: #d95926; --arch: #3987e5; --accent: #3987e5; --focus: #8fbcf0;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #1a1a19; --panel: #232322; --ink: #efeee9; --muted: #b3b1a8; --line: #3a3a37; --soft: #2c2c2a;
  --lumber: #d95926; --arch: #3987e5; --accent: #3987e5; --focus: #8fbcf0;
  color-scheme: dark;
}
* { box-sizing: border-box; }
html, body { margin: 0; }
body { background: var(--bg); color: var(--ink); font-family: var(--font-body); font-size: 17px; line-height: 1.5; }
h1, h2, h3 { font-family: var(--font-display); text-wrap: balance; margin: 0; letter-spacing: -0.01em; }
h1 { font-size: clamp(1.9rem, 4vw, 2.6rem); line-height: 1.1; }
h2 { font-size: 1.35rem; margin-bottom: 0.6rem; }
h3 { font-size: 1.1rem; }
h3 small { font-weight: 500; color: var(--muted); font-family: var(--font-body); font-size: 0.95rem; margin-left: 0.4rem; }
p { margin: 0 0 0.8rem; max-width: 68ch; }
.muted { color: var(--muted); }
a { color: var(--accent); }
code { font-size: 0.9em; background: var(--soft); padding: 1px 5px; border-radius: 4px; }
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 16px 48px; }
header.top { padding: 32px 0 16px; display: flex; flex-wrap: wrap; gap: 16px; align-items: end; justify-content: space-between; }
header.top .meta { color: var(--muted); font-size: 0.95rem; }
nav.sticky { position: sticky; top: 0; z-index: 5; background: color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line); margin: 0 -16px; padding: 8px 16px; display: flex; gap: 6px; overflow-x: auto; align-items: center; }
nav.sticky a { color: var(--ink); text-decoration: none; font-size: 0.92rem; padding: 6px 10px; border-radius: 999px; white-space: nowrap; }
nav.sticky a:hover, nav.sticky a:focus-visible { background: var(--soft); outline: none; }
button { font: inherit; font-size: 0.9rem; color: var(--ink); background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 6px 12px; cursor: pointer; }
button:hover { background: var(--soft); }
button:focus-visible, .seg button:focus-visible, a:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.seg button { border: 0; border-radius: 0; background: var(--panel); }
.seg button[aria-pressed="true"] { background: var(--ink); color: var(--bg); }
section { padding: 28px 0 8px; scroll-margin-top: 56px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 16px 0 8px; }
.tile { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.tile .n { font-family: var(--font-display); font-size: 1.9rem; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.1; }
.tile .l { color: var(--muted); font-size: 0.9rem; margin-top: 4px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; margin: 12px 0; }
.bed-card { overflow-x: auto; }   /* the per-bed cut tables run a few px wide at phone width */
.card header { display: flex; gap: 14px; align-items: flex-start; margin-bottom: 10px; }
.letter { flex: 0 0 auto; width: 44px; height: 44px; border-radius: 10px; background: var(--lumber); color: #fff; font-family: var(--font-display); font-weight: 700; font-size: 1.5rem; display: grid; place-items: center; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.95rem; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; }
tbody tr:hover { background: var(--soft); }
td b { font-variant-numeric: tabular-nums; }
.src { display: inline-block; font-size: 0.78rem; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); white-space: nowrap; }
.src.model { border-color: var(--arch); color: var(--arch); }
.src.derived { border-color: var(--lumber); color: var(--lumber); }
.src.est { border-style: dashed; color: var(--muted); }
.legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.9rem; color: var(--muted); margin: 8px 0 0; }
.legend > span { display: inline-flex; align-items: center; gap: 6px; }
.sw-lumber { width: 14px; height: 14px; background: var(--lumber); border-radius: 3px; }
.sw-arch { width: 14px; height: 14px; border: 2px dashed var(--arch); border-radius: 3px; }
.sw-hoop { width: 16px; height: 4px; background: var(--arch); border-radius: 2px; }
.sw-drip { width: 18px; height: 0; border-top: 2px dashed currentColor; opacity: 0.8; }
.sw-paver { width: 14px; height: 14px; border: 1px solid currentColor; border-radius: 2px; background: repeating-linear-gradient(45deg, transparent 0 2px, currentColor 2px 3px); opacity: 0.7; }
figure { margin: 12px 0 0; }
figure .scroll { overflow-x: auto; }
figure svg { display: block; max-width: 100%; height: auto; }
figure.plan svg { min-width: 680px; }
figure.detail { max-width: 600px; }
figure.wide { max-width: 820px; }
figcaption { color: var(--muted); font-size: 0.92rem; margin-top: 8px; max-width: 72ch; }
.two { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
figure .bed:hover path, figure .bed:hover rect { filter: brightness(1.1); }
figure .arch:hover rect { fill-opacity: 0.25; }
figure .pv:hover rect { opacity: 1; stroke-width: 1.4; }
#tip { position: fixed; pointer-events: none; background: var(--ink); color: var(--bg); padding: 6px 10px; border-radius: 8px; font-size: 0.88rem; max-width: 320px; display: none; z-index: 10; box-shadow: 0 6px 20px rgba(0,0,0,0.25); }
ul { padding-left: 1.2rem; max-width: 72ch; }
li { margin-bottom: 4px; }
.sw { font-variant-numeric: tabular-nums; }
textarea.copytext { width: 100%; min-height: 160px; font: 0.85rem/1.4 ui-monospace, Menlo, monospace; background: var(--soft); color: var(--ink); border: 1px solid var(--line); border-radius: 8px; padding: 10px; display: none; margin-top: 10px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 8px; }
.note { border-left: 3px solid var(--lumber); padding: 6px 12px; background: var(--soft); border-radius: 0 8px 8px 0; margin: 10px 0; max-width: 72ch; }
.card header .grow { flex: 1 1 auto; min-width: 0; }
.check-state { flex: 0 0 auto; display: flex; gap: 10px; align-items: center; font-size: 0.9rem; color: var(--muted); white-space: nowrap; }
.check-state .count { font-variant-numeric: tabular-nums; }
.checklist th.ck, .checklist td.ck { width: 40px; padding-right: 0; }
.checklist input[type="checkbox"] { width: 20px; height: 20px; margin: 1px 0 0; accent-color: var(--arch); cursor: pointer; vertical-align: top; }
.checklist tbody tr:not(.grp):not(.cuts) { cursor: pointer; }
.checklist tbody tr:not(.grp):not(.cuts):hover { background: var(--soft); }
.checklist label { cursor: pointer; }
.checklist tr.grp td { background: var(--soft); color: var(--muted); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; padding: 6px 10px; }
.checklist tr.done td { color: var(--muted); }
.checklist tr.done label, .checklist tr.done td b { text-decoration: line-through; text-decoration-thickness: 1.5px; }
.card.done { border-color: var(--arch); box-shadow: inset 3px 0 0 var(--arch); }
.card.done .letter { background: var(--arch); }
.card.done .letter::after { content: " \2713"; font-size: 0.9rem; }
.vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.checklist td:nth-child(3) { white-space: nowrap; }
#cuts table td:first-child { white-space: nowrap; }
.checklist tr.grp .sub { text-transform: none; letter-spacing: 0; font-weight: 500; margin-left: 8px; }
.checklist tbody tr.cuts, .checklist tbody tr.cuts:hover { cursor: default; background: var(--panel); }
.checklist tr.cuts td { padding: 10px 10px 14px; }
.cutbars { display: grid; gap: 10px; }
.cutbar .stock { font-size: 0.92rem; margin-bottom: 4px; }
.cutbar .bar { display: flex; gap: 2px; height: 28px; min-width: 140px; }
.pc { display: flex; align-items: center; justify-content: center; flex: 0 1 0; min-width: 0; overflow: hidden; border: 1px solid var(--line); border-radius: 4px; font-size: 0.74rem; font-variant-numeric: tabular-nums; color: var(--ink); }
.pc i { font-style: normal; white-space: nowrap; padding: 0 2px; }
.pc.board { background: color-mix(in srgb, var(--lumber) 30%, var(--panel)); }
.pc.post { background: color-mix(in srgb, var(--arch) 26%, var(--panel)); }
.pc.waste { background: repeating-linear-gradient(135deg, var(--soft) 0 4px, var(--panel) 4px 8px); color: var(--muted); border-style: dashed; }
.cutbar .legend { font-size: 0.86rem; color: var(--muted); margin-top: 4px; }
.opts-h { margin: 14px 0 4px; font-weight: 600; font-size: 0.9rem; }
.opts { margin: 0; padding-left: 18px; font-size: 0.9rem; }
.opts li { margin: 4px 0; }
.opts .sep { color: var(--muted); padding: 0 6px; }
@media (max-width: 640px) {
  /* each checklist line stacks: tick, item and qty on the first line, spec and notes beneath */
  .bed-card { overflow-x: visible; }
  .checklist, .checklist tbody { display: block; }
  .checklist thead { display: none; }
  .checklist tr.grp { display: block; }
  .checklist tr.grp td { display: block; border-radius: 6px; }
  .checklist tr.cuts, .checklist tr.cuts td { display: block; }
  .checklist tr.cuts td { padding: 10px 0 14px; }
  .cutbar .bar { width: 100% !important; }
  .checklist tbody tr:not(.grp):not(.cuts) { display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; column-gap: 8px; row-gap: 2px; padding: 10px 4px; border-bottom: 1px solid var(--line); }
  .checklist tbody tr:not(.grp):not(.cuts) td { display: block; border: 0; padding: 0; }
  .checklist td.ck { grid-column: 1; grid-row: 1 / span 3; width: auto; }
  .checklist td:nth-child(2) { grid-column: 2; grid-row: 1; }
  .checklist td:nth-child(3) { grid-column: 3; grid-row: 1; text-align: right; }
  .checklist td:nth-child(4) { grid-column: 2 / span 2; grid-row: 2; font-size: 0.92rem; }
  .checklist td:nth-child(5) { grid-column: 2 / span 2; grid-row: 3; font-size: 0.92rem; color: var(--muted); }
  .checklist td:nth-child(4):empty, .checklist td:nth-child(5):empty { display: none; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
@media (max-width: 520px) { body { font-size: 16px; } .card header { flex-direction: column; } }
'''

JS = r'''
(function () {
  var root = document.documentElement;
  function setTheme(t) {
    if (t) root.setAttribute('data-theme', t); else root.removeAttribute('data-theme');
    var b = document.getElementById('themeBtn');
    if (b) b.textContent = (t === 'dark' || (!t && window.matchMedia('(prefers-color-scheme: dark)').matches)) ? 'Light theme' : 'Dark theme';
  }
  var saved = null;
  try { saved = localStorage.getItem('fg-theme'); } catch (e) {}
  setTheme(saved);
  document.getElementById('themeBtn').addEventListener('click', function () {
    var cur = root.getAttribute('data-theme');
    var isDark = cur === 'dark' || (!cur && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var next = isDark ? 'light' : 'dark';
    setTheme(next);
    try { localStorage.setItem('fg-theme', next); } catch (e) {}
  });

  function setLumber(v) {
    document.querySelectorAll('.sw').forEach(function (el) { el.textContent = el.getAttribute(v === '10' ? 'data-v10' : 'data-v8'); });
    document.querySelectorAll('.seg button').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-l') === v ? 'true' : 'false'); });
    document.querySelectorAll('.nom').forEach(function (el) { el.textContent = v === '10' ? '2x10' : '2x8'; });
  }
  var lv = '8';
  try { lv = localStorage.getItem('fg-lumber') || '8'; } catch (e) {}
  setLumber(lv);
  document.querySelectorAll('.seg button').forEach(function (b) {
    b.addEventListener('click', function () { setLumber(b.getAttribute('data-l')); try { localStorage.setItem('fg-lumber', b.getAttribute('data-l')); } catch (e) {} });
  });

  var tip = document.getElementById('tip');
  function show(e, el) {
    tip.textContent = el.getAttribute('data-tip');
    tip.style.display = 'block';
    var x = e.clientX + 14, y = e.clientY + 14;
    if (x + 330 > window.innerWidth) x = e.clientX - 330;
    if (y + 60 > window.innerHeight) y = e.clientY - 60;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  document.querySelectorAll('[data-tip]').forEach(function (el) {
    el.addEventListener('mousemove', function (e) { show(e, el); });
    el.addEventListener('mouseleave', function () { tip.style.display = 'none'; });
    el.addEventListener('click', function (e) { show(e, el); });
  });

  var copyBtn = document.getElementById('copyBtn');
  var ta = document.getElementById('copyText');
  copyBtn.addEventListener('click', function () {
    var text = ta.value;
    function fallback() { ta.style.display = 'block'; ta.focus(); ta.select(); copyBtn.textContent = 'Select and copy the text below'; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { copyBtn.textContent = 'Copied'; setTimeout(function () { copyBtn.textContent = 'Copy shopping list'; }, 1800); }, fallback);
    } else { fallback(); }
  });

  // per-bed checklists, remembered in this browser
  var CK = 'fg-checks';
  var checks = {};
  try { checks = JSON.parse(localStorage.getItem(CK) || '{}') || {}; } catch (e) { checks = {}; }
  function saveChecks() { try { localStorage.setItem(CK, JSON.stringify(checks)); } catch (e) {} }
  function updateTotal() {
    var all = document.querySelectorAll('.bed-card input[type="checkbox"]');
    var n = 0;
    all.forEach(function (b) { if (b.checked) n++; });
    var t = document.getElementById('checkTotal');
    if (t) t.textContent = n + ' of ' + all.length + ' lines ticked across the four beds';
  }
  function updateCard(card) {
    var boxes = card.querySelectorAll('input[type="checkbox"]');
    var n = 0;
    boxes.forEach(function (b) { b.closest('tr').classList.toggle('done', b.checked); if (b.checked) n++; });
    var c = card.querySelector('.count');
    var done = boxes.length > 0 && n === boxes.length;
    if (c) c.textContent = done ? 'All ' + boxes.length + ' checked' : n + ' of ' + boxes.length + ' checked';
    card.classList.toggle('done', done);
    updateTotal();
  }
  document.querySelectorAll('.bed-card').forEach(function (card) {
    card.querySelectorAll('input[type="checkbox"]').forEach(function (b) {
      var k = b.getAttribute('data-key');
      b.checked = !!checks[k];
      b.addEventListener('change', function () { if (b.checked) checks[k] = true; else delete checks[k]; saveChecks(); updateCard(card); });
    });
    card.querySelectorAll('tbody tr:not(.grp):not(.cuts)').forEach(function (row) {
      row.addEventListener('click', function (e) {
        if (e.target.closest('input, label, button, a') || String(window.getSelection && window.getSelection())) return;
        var b = row.querySelector('input[type="checkbox"]');
        if (!b) return;
        b.checked = !b.checked;
        b.dispatchEvent(new Event('change', { bubbles: true }));
      });
    });
    var clr = card.querySelector('.clear');
    if (clr) clr.addEventListener('click', function () {
      card.querySelectorAll('input[type="checkbox"]').forEach(function (b) { b.checked = false; delete checks[b.getAttribute('data-key')]; });
      saveChecks(); updateCard(card);
    });
    updateCard(card);
  });
  var clearAll = document.getElementById('clearAll');
  if (clearAll) clearAll.addEventListener('click', function () {
    if (!window.confirm('Clear every tick on all four beds?')) return;
    checks = {}; saveChecks();
    document.querySelectorAll('.bed-card').forEach(function (card) { card.querySelectorAll('input[type="checkbox"]').forEach(function (b) { b.checked = false; }); updateCard(card); });
  });
})();
'''

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Raised Bed Design BOM</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div id="tip" role="tooltip"></div>
<div class="wrap">
<header class="top">
  <div>
    <h1>Raised Bed Design: bill of materials</h1>
    <div class="meta">From the Fusion design "{esc(d['document'])}", extracted {TODAY}. Counts come from model bodies; derived and estimated rows are marked.</div>
  </div>
  <div class="toolbar">
    <div class="seg" role="group" aria-label="Wall lumber"><button type="button" data-l="8" aria-pressed="true">2x8 walls</button><button type="button" data-l="10" aria-pressed="false">2x10 walls</button></div>
    <button type="button" id="themeBtn">Dark theme</button>
  </div>
</header>
<nav class="sticky" aria-label="Sections">
  <a href="#plan">Plan</a><a href="#shopping">Shopping list</a><a href="#screws">Screws</a><a href="#cuts">Cut list</a><a href="#beds">By bed</a><a href="#pavers">Pavers</a><a href="#arches">Trellis arches</a><a href="#hoops">Hoops</a><a href="#drip">Drip</a><a href="#soil">Soil</a><a href="#optional">Optional</a><a href="#model">Model notes</a>
</nav>

<div class="tiles">
  <div class="tile"><div class="n">{total_2x_boards + post_sticks}</div><div class="l">sticks of lumber: {total_2x_boards} <span class="nom">{NOM}</span> + {post_sticks} {POST_NOM}, about {num(lumber_cost, lumber_cost_alt, '${:.2f}')}</div></div>
  <div class="tile"><div class="n">{screws_total}</div><div class="l">screws: {screws_3} x 3 in, {screws_25} x 2.5 in</div></div>
  <div class="tile"><div class="n">{paver_n}</div><div class="l">12 x 12 in pavers, {paver_total_lb:,.0f} lb</div></div>
  <div class="tile"><div class="n">{n_arches}</div><div class="l">{HOGWIRE_LEN/12:g} ft hog-wire arch: {trellis_pieces} x {ft_in(TRELLIS_LEN)} posts, {sill_pieces} sills, {stake_pieces} stakes</div></div>
  <div class="tile"><div class="n">{n_hoops}</div><div class="l">low-tunnel hoops over Bed {hoop_bed_letter}, {hoop_pitch:g} in pitch, {hoop_tube_ft:.0f} ft of 1 in tube</div></div>
  <div class="tile"><div class="n">{n_risers}</div><div class="l">drip risers: {n_risers} tees, {drip_elbows} elbows, {n_risers} valves, {drip_sticks} x 10 ft of 1/2 in pipe</div></div>
  <div class="tile"><div class="n">{num(soil_ft3/27, soil_alt_ft3/27, '{:.1f}')}</div><div class="l">cu yd of soil</div></div>
</div>

<section id="plan">
  <h2>Plan</h2>
  <p>Four beds in a 24 ft x 18 ft plot. Side boards run outside the end boards, which are 48 in (21 in for Bed D). {esc(side_scheme_txt)} {POST_NOM} posts stand inside each corner, edge-on to the side boards, and lie flat against the long walls at mid-span, where they run {MID_LEN:g} in long and are driven {EMBED_IN:g} in into the ground. The hog-wire arch between beds A and B stands on {POST_NOM} sills at the bed centrelines and is held near its crown by the two inside corner posts at the near end, uncut {ft_in(TRELLIS_LEN)} {POST_NOM}s set {TRELLIS_EMBED:g} in deep. Letters follow the arch names in the model: Arch AB spans beds A and B; Arch BC is modeled but parked. {f'{n_hoops} low-tunnel hoops of 1 in tube (the blue bars) cover Bed {hoop_bed_letter} at {hoop_pitch:g} in pitch, the first and last {hoop_near_gap:g} in inside the end boards.' if n_hoops else ''}</p>
  <div class="legend"><span><i class="sw-lumber"></i><span>bed walls and posts (<span class="nom">{NOM}</span>, {POST_NOM})</span></span><span><i class="sw-arch"></i><span>hog-wire arch footprint</span></span>{'<span><i class="sw-hoop"></i><span>low-tunnel hoops (solid bars, a dot at each leg)</span></span>' if n_hoops else ''}{'<span><i class="sw-drip"></i><span>drip main (dash-dot, buried) and risers (circles)</span></span>' if risers else ''}<span><i class="sw-paver"></i><span>12 x 12 pavers</span></span></div>
  <figure class="plan">
    <div class="scroll">{SVG}</div>
    <figcaption>Top view, 1 px = 0.4 in. Hover or tap a bed, path or arch for its numbers. Beds are 24 in apart with one paver centered in each gap; the walkway strip is 33 in with two paver rows.{f' The wider posts on the long walls of {esc(beds_text(split_beds))} are the {JOINT_NOM} joint posts, with a hairline across the wall where the boards meet.' if split_beds else ''}</figcaption>
  </figure>
</section>

<section id="shopping">
  <h2>Shopping list</h2>
  <div class="toolbar"><button type="button" id="copyBtn">Copy shopping list</button><span class="muted">Rows tagged <span class="src model">Model</span> are counted from the design, <span class="src derived">Derived</span> rows are computed from its geometry, and <span class="src est">Estimate</span> rows are not modeled.</span></div>
  <textarea id="copyText" class="copytext" readonly aria-label="Shopping list as text">{esc(shop_text)}</textarea>
  <div class="card tablewrap"><table>
    <thead>{tr(['Section', 'Item', 'Qty', 'Unit', 'Spec', 'Source', 'Notes'], True)}</thead>
    <tbody>{shop_rows}</tbody>
  </table></div>
  <p class="muted">Lumber: {total_2x_boards} boards of <span class="nom">{NOM}</span>, {total_lin_ft_2x:.0f} linear ft, plus {post_sticks} sticks of {POST_NOM}, about {num(lumber_cost, lumber_cost_alt, '${:.2f}')} before tax ({esc(PRICE_SOURCE)}); about {num(lumber_mass_lb, lumber_mass_alt_lb, '{:,.0f}', ' lb')} in the model. Rows tagged <span class="src est">Store price</span> carry those prices; the <a href="#cuts">cut list</a> shows how each stick is cut.</p>
</section>

<section id="screws">
  <h2>Screw plan</h2>
  <p>Every joint is a <span class="nom">{NOM}</span> board face-screwed to a {POST_NOM} post: {SCREWS_PER_JOINT} screws per board per post, {SCREW_HEIGHTS[0]:g} in and {SCREW_HEIGHTS[1]:g} in up from the bottom edge of each board. Corner posts stand edge-on, {PT:g} in edge against the side board and {PW:g} in face against the end board, so the side-board screws there drive into {PW:g} in of post. Mid-span posts lie flat, {PW:g} in face against the side board, and run {MID_LEN:g} in long so {EMBED_IN:g} in is driven into the ground; the screws into them are shorter and staggered across the face.{f' Where two side boards meet over a {JOINT_NOM} joint post ({esc(beds_text(split_beds))}), each board end gets its own pair, {JOINT_OFF:g} in from the end.' if split_beds else ''}</p>
  <div class="card tablewrap"><table>
    <thead>{tr(['Joint', 'Screw', 'Why that length and where', 'Count'], True)}</thead>
    <tbody>{screw_joint_rows}</tbody>
  </table></div>
  <figure class="detail">
    {CORNER_SVG}
    <figcaption>Plan view of a corner and the first mid-span post, looking down, with the screws drawn at true length. Arrows from the left are the side-board screws: 3 in into the corner post edge, 2.5 in into the mid-span post face, staggered {MID_OFFSET:g} in either side of its centerline. The arrow from the top is a 2.5 in screw through the end board into the corner post face, and the dashed blue arrow is the corner tie into the end board's end grain. Each arrow is one screw per board course; the elevations show where they sit up the board.</figcaption>
  </figure>
  <div class="two">
    <figure>
      {ELEV_SVG}
      <figcaption>Outside face of a side board at a corner, both courses, bed end at the left. Dots on the post centerline, {T+PT/2:g} in from the end, are the 3 in post screws; blue dots {T/2:g} in from the end are the corner ties into the end board's end grain.</figcaption>
    </figure>
    <figure>
      {MID_ELEV_SVG}
      <figcaption>Outside face of a side board at a mid-span post. The post is {PW:g} in wide behind the board and continues {EMBED_IN:g} in below grade. Each course gets two 2.5 in screws, the lower one {MID_OFFSET:g} in left of the post centerline and the upper one {MID_OFFSET:g} in right, so the board cannot pivot on the post.</figcaption>
    </figure>
    {joint_fig_html}
  </div>
  <div class="card tablewrap"><table>
    <thead>{tr(['Bed', 'Posts per side', '3 in: corner posts', '3 in: corner ties', '3 in: arch stakes', '2.5 in: mid-span posts', '2.5 in: joint posts', '2.5 in: end boards', '1.25 in: arch panel', 'Total'], True)}</thead>
    <tbody>{screw_bed_rows}</tbody>
  </table></div>
  <p>Buy 3 in: {screws_3} needed, {buy_3}. Buy 2.5 in: {screws_25} needed, {buy_25}. Use #9 star-drive exterior structural screws, coated for treated lumber or stainless 305 or 316 for cedar and redwood, which stain and corrode plain coated screws. Pre-drill the corner ties and any screw within 2 in of a board end (1/8 in bit for cedar, 3/32 in for SPF).</p>
  <div class="note">Set the mid-span posts{' and the joint posts' if split_beds else ''} first: chamfer the bottom of each to a point, drive it {frac(mid_embed_cut)} in at the marked centerline with its wide face toward the wall, and stop when its top is flush with the top of the wall. Then screw the side boards to it from outside. Corner posts stay {POST_H:g} in and sit on grade, except the {tot_tr_corner} inside corner posts at the near end of beds A and B under the arch, which are uncut {ft_in(TRELLIS_LEN)} trellis posts set {TRELLIS_EMBED:g} in deep (see the arch).</div>
</section>

<section id="cuts">
  <h2>Cut list</h2>
  <p>Stock lengths and prices: {esc(PRICE_SOURCE)}. <span class="nom">{NOM}</span> comes in {board_lengths_txt} ({esc(side_stock_note)}) and {POST_NOM} in {post_lengths_txt}. Each bed's plan under <a href="#beds">Materials by bed</a> is the cheapest set of sticks for that bed on its own, so the four plans add up to this table. {esc(cut_rule_txt)}</p>
  <div class="card tablewrap"><table>
    <thead>{tr(['Buy', 'Qty', 'Each', 'Total', 'Used for'], True)}</thead>
    <tbody>{lumber_rows}</tbody>
  </table></div>
  <h3>All four beds from one pile</h3>
  <p>Cutting every bed from one pile instead: {combined_sticks} sticks, {num(combined_cost, priced_as(combined_boards, ALT_NOM) + combined_posts['cost'], '${:.2f}')}{f', saving {num(combined_saving, round(per_bed_board_cost - combined_boards["cost"] + per_bed_post_cost - combined_posts["cost"], 2), "${:.2f}")} over the per-bed plans because offcuts from one bed become pieces for another.' if combined_saving > 0.005 else '; the per-bed plans are already as cheap.'}</p>
  <div class="card">{combined_bars}</div>
</section>

<section id="beds">
  <h2>Materials by bed</h2>
  <p>Everything that goes to one bed, so each bed can be checked on its own. The lumber lines are the sticks to buy, in store lengths with store prices (checked {PRICE_DATE}), and the bars beneath them show how each stick is cut; then the cuts themselves, screws and washers, the arch panel, the hoops, the drip riser and the soil. Tick a line as you check or buy it; the ticks are kept in this browser. The hog-wire panel spans beds A and B and is listed under both (buy one). The 1/2 in drip pipe for every bed is cut from the {drip_sticks} x 10 ft stick{'s' if drip_sticks > 1 else ''} on the shopping list.</p>
  <div class="toolbar"><span class="muted" id="checkTotal" aria-live="polite">0 of {bed_lines_total} lines ticked</span><button type="button" id="clearAll">Clear all ticks</button></div>
  {''.join(bed_cards)}
</section>

<section id="pavers">
  <h2>Pavers and paths</h2>
  <div class="card tablewrap"><table>
    <thead>{tr(['Group', 'Pavers', 'Where'], True)}</thead>
    <tbody>{paver_rows}{tr(['<b>Total</b>', f'<b>{paver_n}</b>', f'{paver_dims[1]:g} x {paver_dims[2]:g} x {paver_dims[0]:g} in, about {paver_each_lb:.0f} lb each, {paver_total_lb:,.0f} lb in all'])}</tbody>
  </table></div>
  <p>The walkway is a 33 in strip with two rows of pavers at 15 in pitch; the 36 in strip beyond it is in the site sketch but not modeled. Bed paths use one paver centered in each 24 in gap at 18 in pitch. Base estimate: {base_depth_in:g} in of leveling material under each paver, {base_ft3:.1f} cu ft, about {base_bags} half-cubic-foot bags.</p>
</section>

<section id="arches">
  <h2>Hog-wire trellis arches</h2>
  <div class="card tablewrap"><table>
    <thead>{tr(['Arch', 'Between', 'Chord', 'Feet', 'Straight leg', 'Crown above grade', 'Upper supports', 'Walkway headroom', 'Panel width modeled'], True)}</thead>
    <tbody>{arch_rows}</tbody>
  </table></div>
  {arch_html_paras}
  <figure class="wide">
    {ARCH_ELEV_SVG}
    <figcaption>{esc(arch_elev_caption)}</figcaption>
  </figure>
  <div class="two">
    <figure class="detail">
      {FOOT_SVG}
      <figcaption>{esc(foot_caption)}</figcaption>
    </figure>
    <figure class="detail">
      {TOP_SVG}
      <figcaption>{esc(top_caption)}</figcaption>
    </figure>
  </div>
  <div class="note">{esc(arch_note)}</div>
</section>

<section id="hoops">
  <h2>Low-tunnel hoops</h2>
  <div class="card tablewrap"><table>
    <thead>{tr(['Over', 'Hoops', 'Pitch', 'Width', 'Top above grade', 'Legs', 'Tube each', 'Tube in all'], True)}</thead>
    <tbody>{hoop_rows}</tbody>
  </table></div>
  {hoop_html_paras}
</section>

<section id="drip">
  <h2>Drip risers</h2>
  <div class="card tablewrap"><table>
    <thead>{tr(['Item', 'Value'], True)}</thead>
    <tbody>{drip_rows}</tbody>
  </table></div>
  {drip_html_paras}
  <div class="two">
    <figure class="detail">
      {DRIP_SIDE_SVG}
      <figcaption>{esc(drip_side_caption)}</figcaption>
    </figure>
    <figure class="detail">
      {DRIP_BACK_SVG}
      <figcaption>{esc(drip_back_caption)}</figcaption>
    </figure>
  </div>
  <div class="note">{esc(drip_note)}</div>
</section>

<section id="soil">
  <h2>Soil</h2>
  <div class="card tablewrap"><table>
    <thead>{tr(['Bed', 'Inside', 'Depth', 'Volume'], True)}</thead>
    <tbody>{soil_rows}{tr(['<b>Total</b>', '', '', '<b>' + num(soil_ft3, soil_alt_ft3, '{:.0f}', ' cu ft') + ' = ' + num(soil_ft3/27, soil_alt_ft3/27, '{:.1f}', ' cu yd') + '</b>'])}</tbody>
  </table></div>
  <p class="muted">Volumes subtract the posts. The 2x8 / 2x10 switch above changes depth and soil only; the cut list and screw counts are the same either way.</p>
</section>

<section id="optional">
  <h2>Optional items modeled but hidden</h2>
  <ul>
    <li><b>Single-tube arch</b> (Garden Arch): 1 in tube, 7 ft span, 42 in legs, 7 ft tall, about {tube_arch_len/12:.0f} ft of tube. Same spot as Arch AB; superseded.</li>
    <li><b>Hardware cloth</b> under the beds (gopher barrier): about {cloth_ft} linear ft of 48 in roll, trimmed to 21 in for Bed D.</li>
  </ul>
</section>

<section id="model">
  <h2>Model notes</h2>
  <ul>
    <li>New component <b>Bed Lumber</b> holds the buildable beds ({NOM} walls, {POST_NOM} posts). The original 4 in-wall massing bodies in <b>Raised Beds</b> are hidden and kept as the layout reference the arch sketches use.</li>
    <li>New user parameters: <code>Board_Width</code> (7.25 in = 2x8; 9.25 in = 2x10), <code>Courses</code> (2) and <code>Mid_Post_Length</code> (24 in), plus <code>Board_Thickness</code> and <code>Post_Size</code> for reference. Bed height = Courses x Board_Width; each bed's <code>Mid post extrude</code> runs Courses x Board_Width up and the rest of Mid_Post_Length down from the Posts sketch.</li>
    <li>Physical materials fixed: pavers are now <b>Concrete (paver)</b> at 2300 kg/m3 (they were pine with a concrete look); arch wires are <b>Steel, Galvanized</b>; the tube arch is <b>Steel</b>.</li>
    <li>Part numbers and descriptions filled in on every component; "Forth Paver Path" renamed "Fourth Paver Path".</li>
    <li>The ten superseded rolled-back features that sat after the timeline marker (Position5, R-Pattern2, the old Sketch1 to Sketch4 / Extrude1 to Extrude3 bed layout, and a broken CopyPaste 2x8x8:3) were deleted on 2026-11-05.</li>
    <li>2026-11-06, trellis arch: Arch AB now runs from the centre of Bed A to the centre of Bed B with its feet on the ground (parametric Move "Onto the sills": 21 in across the beds, 1.25 in along them, Board_Thickness up). New parameters <code>Trellis_Post_Length</code> ({TRELLIS_LEN:g} in), <code>Trellis_Post_Embed</code> ({TRELLIS_EMBED:g} in) and <code>Stake_Above_Sill</code> ({STAKE_ABOVE - T:g} in). The inside corner post at the near end of beds A and B moved out of <code>Post extrude</code> into a two-sided <code>Trellis post extrude</code> (body "2x4 trellis post"); each of those beds got an "Arch anchors" sketch with a <code>Sill extrude</code> (body "2x4 sill") and a two-sided <code>Stake extrude</code> (bodies "2x4 stake"). <code>Hogwire_height</code> is <code>(Hogwire_length - Hogwire_archlength) / 2</code> = {HOG_LEG:.1f} in. The earlier wall-top scheme of the same day (72 in posts under the arch legs) is superseded: Arch BC is hidden (parked) and its posts are ordinary again. The T-post anchors are gone.</li>
    {hoops_model_note_html}
    {drip_model_note_html}
    {split_model_note_html}
    <li>{esc(saved_note)}</li>
  </ul>
  <p class="muted">Model mass by material (visible bodies): {', '.join(f'{esc(k)} {v:,.0f} lb' for k, v in mass_by_mat.items())}.{esc(hoop_mass_note)}</p>
</section>
</div>
<script>{JS}</script>
</body>
</html>
'''
(ROOT / 'bom.html').write_text(HTML)
print('wrote', ROOT / 'BOM.md', ROOT / 'BOM.csv', ROOT / 'BOM-by-bed.csv', ROOT / 'bom.html', f'({bed_lines_total} per-bed lines)')
print(f'beds={len(bed_rows)} {NOM} boards={total_2x_boards} {POST_NOM} sticks={post_sticks} lumber=${lumber_cost:.2f} (alt ${lumber_cost_alt:.2f}; all beds from one pile {combined_sticks} sticks ${combined_cost:.2f}, saving ${combined_saving:.2f}) '
      f'screws 3in={screws_3} 2.5in={screws_25} 1.25in={screws_125} total={screws_total} pavers={paver_n} arches={n_arches} hoops={n_hoops} risers={n_risers} pipe={drip_pipe_total if risers else 0:g}in sticks={drip_sticks if risers else 0} '
      f'soil={soil_ft3:.1f} ft3 ({soil_ft3/27:.2f} yd3) alt={soil_alt_ft3/27:.2f} yd3')
for r in bed_rows:
    print(f"  Bed {r['letter']}: posts/side={r['posts_per_side']} corner={r['corner_side_screws']} mid={r['mid_side_screws']} joint={r['joint_screws']} ties={r['tie_screws']} end={r['end_screws']} "
          f"mid centers={r['mid_centers']} joints={r['joint_centers']} sides={dict(r['side_pieces'])} layout={dict(r['side_layout'])}")
for x in lumber_list:
    print('  ', x['qty'], 'x', x['item'], f"@ ${x['price']:.2f}", '|', x['use'])
for r in bed_rows:
    print(f"  Bed {r['letter']} lumber: {r['lumber_sticks']} sticks ${r['lumber_cost']:.2f}" + ('' if r['alt_same_cutting'] else f"  [note: a different cutting is cheaper at {ALT_NOM} prices: ${r['plan_boards_alt']['cost']:.2f} vs ${r['board_cost_alt']:.2f}]"))
    for nom, p in ((NOM, r['plan_boards']), (POST_NOM, r['plan_posts'])):
        for g in p['sticks']:
            print(f"     {g['count']} x {nom} {g['stock']/12:g} ft: {cutstock.stick_text(g)}")

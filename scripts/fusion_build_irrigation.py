"""Fusion script: a drip riser on the far end wall of every raised bed, tapped off the 3/4 in sprinkler main.

The owner's request of 2026-11-06 (hand sketch, back and side views), changed on 2026-11-15 from cut 1/2 in pipe glued into
slip fittings to a stack of threaded 1/2 in PVC risers (pre-threaded nipples, male thread both ends, sold in fixed lengths):
the 3/4 in main runs along the stair-step far ends of the beds, buried. At each bed a 3/4 x 3/4 x 3/4 slip tee feeds, in
order: a stub of 3/4 in pipe toward the bed (the only cut pipe), a 3/4 in slip x 1/2 in FPT reducing elbow turned up, a
1/2 in riser up the OUTSIDE of the far end wall, a 1/2 in FPT x FPT ball valve, another riser, a 1/2 in FPT elbow turning
into the bed, a riser through a hole in the top board, a 1/2 in FPT elbow turning up inside the bed, a riser, and a
1/2 in FPT x 4-port 1/4 in drip manifold head threaded straight onto it. Two stand-off clamps hold the upper riser to the
outside of the wall, both above the valve, each screwed into a single board.

Layout (inches, world frame of the Raised Bed Design document: origin at the walkway corner of Bed D, beds run toward -y):
- The riser stands RISER_X in from each bed's west outside face, so the hole misses the edge-on corner post (3.5 in from the
  side board) and the riser inside the bed misses the hoop legs over Bed C.
- The through-wall riser is centred in the top board: z = Courses * Board_Width - Board_Width / 2 = 10.875 in.
- The bought riser lengths RISER_UPPER (6) and RISER_LOWER (8) set the valve height and the main's depth: valve centre
  3.25 in above grade, main axis 6.5 in below grade. RISER_HEAD (4) puts the head's base 0.5 in and its top 2.5 in above the
  wall top. RISER_WALL (3) puts the inside riser 4.25 in from the outside one; the 3/4 in stub is derived from STANDOFF and
  MAIN_OFFSET.
- The main is modelled as a reference ("3/4 in main (existing)"): a stair-step MAIN_OFFSET in beyond each far end board,
  stepping at the gap centres between beds. The plot's angled boundary is only 2 to 4 in beyond the inner step corners.
  Its real depth is not known. Hole centre above grade = RISER_LOWER + RISER_UPPER + 3.375 - depth of the main's centre,
  so measure the main at each bed and set RISER_LOWER to suit before trusting the depth drawn here.

Fittings: 1/2 in riser 0.84 OD, threaded hubs about 1.30 OD, a riser end goes THREAD (0.5) into a fitting; 3/4 in pipe
1.05 OD, slip hubs 1.40 OD, 3/4 in socket depth. A riser body runs from thread end to thread end, so its length is the
bought length; the stub runs from socket bottom to socket bottom, so its length is the cut length.

Structure: root occurrence "Drip Irrigation" > "Drip riser" x 4 (one component, placed per bed) + "3/4 in main (existing)".
Bodies are made with the temporary BRep manager inside one base feature per component (not parametric; this file is the
source of the numbers). The holes are real "Drip hole cut" extrudes in the Bed Lumber bed components, so
fusion_build_bed_lumber.py does not know about them: run this script again after rebuilding the lumber.
Re-running deletes and rebuilds everything it made. Read-only for the rest of the design; nothing is saved.
scripts/planned_layout.py applies the same stack to an extract of a model that still has the glued risers.
"""
import adsk.core, adsk.fusion, math

IN = 2.54

# ---- layout, inches ----
MAIN_OFFSET = 8.0      # 3/4 in main axis beyond the far end board's outside face
RISER_X = 9.0          # riser axis from the bed's west outside face
HOLE_DIA = 1.0         # through the top board for the 0.84 OD riser
RISER_HEAD = 4.0       # threaded 1/2 in risers, bought lengths: inside the bed, elbow to head
RISER_WALL = 3.0       # through the top board, elbow to elbow
RISER_UPPER = 6.0      # outside, valve to the top elbow
RISER_LOWER = 8.0      # outside, reducing elbow to valve (sets the main's depth)
CLAMP_LOWER_Z = 5.5    # clamp centres above grade: both on the upper riser, each on one board
CLAMP_UPPER_Z = 8.75

# ---- parts, inches ----
PIPE_R12, HUB_R12 = 0.84 / 2, 1.30 / 2   # threaded riser, FPT hub
PIPE_R34, HUB_R34 = 1.05 / 2, 1.40 / 2
THREAD = 0.5           # a riser end screws this far into a fitting
HUB_12 = 1.125         # 1/2 in FPT elbow: centre to hub end
HUB_RED = 1.25         # 3/4 in slip x 1/2 in FPT reducing elbow: centre to hub end, both ways
HUB_34 = 1.25          # 3/4 in tee and elbow: centre to hub end
SOCKET = 0.75          # a 3/4 in pipe end sits this far inside a slip hub
GRIP = HUB_12 - THREAD     # FPT elbow centre to the end of the riser screwed into it
STANDOFF = HUB_12 + 0.25   # riser axis off the wall face: the elbow hub stops 1/4 in short of the board
VALVE_HALF, VALVE_BODY_R, VALVE_BODY_HALF = 1.5, 0.8, 1.0
HEAD_R, HEAD_H, BARB_R, BARB_LEN = 0.625, 2.0, 0.125, 0.6
CLAMP_W, CLAMP_H = 2.5, 1.0



def P(x, y, z):
    return adsk.core.Point3D.create(x * IN, y * IN, z * IN)


def V(x, y, z):
    return adsk.core.Vector3D.create(x, y, z)


def sgn(v):
    return float((v > 0) - (v < 0))


def run(_context):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    tmp = adsk.fusion.TemporaryBRepManager.get()
    params = design.userParameters
    T = params.itemByName('Board_Thickness').value / IN
    BW = params.itemByName('Board_Width').value / IN
    COURSES = int(round(params.itemByName('Courses').value))
    THROUGH_Z = COURSES * BW - BW / 2           # centre of the top board
    WALL_TOP = COURSES * BW

    def cyl(p, q, r):
        return tmp.createCylinderOrCone(P(*p), r * IN, P(*q), r * IN)

    def union(a, b):
        if not tmp.booleanOperation(a, b, adsk.fusion.BooleanTypes.UnionBooleanType):
            raise RuntimeError('union failed')
        return a

    def cut(a, b):
        if not tmp.booleanOperation(a, b, adsk.fusion.BooleanTypes.DifferenceBooleanType):
            raise RuntimeError('cut failed')
        return a

    def box(c, lx, ly, lz):
        obb = adsk.core.OrientedBoundingBox3D.create(P(*c), V(1, 0, 0), V(0, 1, 0), lx * IN, ly * IN, lz * IN)
        return tmp.createBox(obb)

    def elbow(c, d1, d2, hub, r):
        b = tmp.createSphere(P(*c), r * IN)
        for d in (d1, d2):
            e = tuple(c[i] + d[i] * hub for i in range(3))
            union(b, cyl(c, e, r))
        return b

    # ---- the beds, from the lumber ----
    lumber = [o for o in root.occurrences if o.name == 'Bed Lumber:1'][0]
    beds = []
    for o in lumber.childOccurrences:
        comp = o.component
        xs, ys = [], []
        far_top = None
        for b in comp.bRepBodies:
            if not b.isVisible:
                continue
            bb = b.boundingBox
            xs += [bb.minPoint.x / IN, bb.maxPoint.x / IN]
            ys += [bb.minPoint.y / IN, bb.maxPoint.y / IN]
        xmin, xmax, ymin = min(xs), max(xs), min(ys)
        for b in comp.bRepBodies:
            bb = b.boundingBox
            if b.name.startswith('End') and abs(bb.minPoint.y / IN - ymin) < 1e-3 and bb.minPoint.z / IN > 1.0:
                far_top = b
        if far_top is None:
            raise RuntimeError('no far top end board in ' + comp.name)
        beds.append({'letter': comp.name[4], 'comp': comp, 'xmin': xmin, 'xmax': xmax, 'ymin': ymin, 'board': far_top})
    beds.sort(key=lambda d: d['xmin'])
    print('beds', [(d['letter'], d['xmin'], d['xmax'], d['ymin']) for d in beds])

    # ---- clean up an earlier run ----
    for o in list(root.occurrences):
        if o.component.name == 'Drip Irrigation':
            if not o.deleteMe():
                raise RuntimeError('could not delete the old Drip Irrigation occurrence')
    for d in beds:
        comp = d['comp']
        for i in range(comp.features.count - 1, -1, -1):
            f = comp.features.item(i)
            if f.name == 'Drip hole cut':
                f.deleteMe()
        for i in range(comp.sketches.count - 1, -1, -1):
            s = comp.sketches.item(i)
            if s.name == 'Drip hole':
                s.deleteMe()
    tl = design.timeline
    first_new = tl.count

    # ---- riser chain, local frame: wall outside face at y = 0, bed inside toward +y, riser axis at x = 0 ----
    E2 = (0.0, -STANDOFF, THROUGH_Z)                 # outside elbow
    E3 = (0.0, -STANDOFF + RISER_WALL + 2 * GRIP, THROUGH_Z)   # inside elbow (STANDOFF inside a 1.5 in board's inner face)
    VZ = THROUGH_Z - (RISER_UPPER - 2 * THREAD + HUB_12 + VALVE_HALF)   # valve centre
    E1Z = VZ - (RISER_LOWER - 2 * THREAD + VALVE_HALF + HUB_RED)       # reducing elbow = main depth
    MAIN_Z = E1Z
    E1 = (0.0, -STANDOFF, E1Z)
    TEE = (0.0, -MAIN_OFFSET, MAIN_Z)
    stub = (MAIN_OFFSET - STANDOFF) - (HUB_34 - SOCKET) - (HUB_RED - SOCKET)
    head_base = THROUGH_Z + GRIP + RISER_HEAD - THREAD
    print(f'through-wall z {THROUGH_Z:.3f}, valve z {VZ:.3f}, main z {MAIN_Z:.3f}, 3/4 in stub {stub:.3f}, risers: lower {RISER_LOWER}, upper {RISER_UPPER}, wall {RISER_WALL}, head {RISER_HEAD}; '
          f'inside elbow hub {E3[1] - HUB_12 - T:.3f} clear of the board; head {head_base:.3f} to {head_base + HEAD_H:.3f} (wall top {WALL_TOP})')

    def riser_pieces():
        y0 = -STANDOFF
        pieces = []
        tee = cyl((-HUB_34, -MAIN_OFFSET, MAIN_Z), (HUB_34, -MAIN_OFFSET, MAIN_Z), HUB_R34)
        union(tee, cyl(TEE, (0.0, -MAIN_OFFSET + HUB_34, MAIN_Z), HUB_R34))
        pieces.append(('3/4 in tee', tee))
        pieces.append(('3/4 in pipe, stub', cyl((0, -MAIN_OFFSET + HUB_34 - SOCKET, MAIN_Z), (0, y0 - (HUB_RED - SOCKET), MAIN_Z), PIPE_R34)))
        pieces.append(('3/4 x 1/2 in reducing elbow', elbow(E1, (0, -1, 0), (0, 0, 1), HUB_RED, HUB_R34)))
        pieces.append(('1/2 in riser, lower', cyl((0, y0, E1Z + HUB_RED - THREAD), (0, y0, VZ - VALVE_HALF + THREAD), PIPE_R12)))
        valve = cyl((0, y0, VZ - VALVE_HALF), (0, y0, VZ + VALVE_HALF), HUB_R12)
        union(valve, cyl((0, y0, VZ - VALVE_BODY_HALF), (0, y0, VZ + VALVE_BODY_HALF), VALVE_BODY_R))
        stem0, stem1 = y0 - VALVE_BODY_R, y0 - VALVE_BODY_R - 0.5
        union(valve, cyl((0, stem0, VZ), (0, stem1, VZ), 0.2))
        union(valve, box((-1.0, stem1 - 0.225, VZ), 2.4, 0.45, 0.3))      # lever, pointing west along the wall
        pieces.append(('1/2 in ball valve', valve))
        pieces.append(('1/2 in riser, upper', cyl((0, y0, VZ + VALVE_HALF - THREAD), (0, y0, THROUGH_Z - GRIP), PIPE_R12)))
        pieces.append(('1/2 in elbow, outside', elbow(E2, (0, 0, -1), (0, 1, 0), HUB_12, HUB_R12)))
        pieces.append(('1/2 in riser, through wall', cyl((0, E2[1] + GRIP, THROUGH_Z), (0, E3[1] - GRIP, THROUGH_Z), PIPE_R12)))
        pieces.append(('1/2 in elbow, inside', elbow(E3, (0, -1, 0), (0, 0, 1), HUB_12, HUB_R12)))
        pieces.append(('1/2 in riser, head', cyl((0, E3[1], THROUGH_Z + GRIP), (0, E3[1], THROUGH_Z + GRIP + RISER_HEAD), PIPE_R12)))
        head = cyl((0, E3[1], head_base), (0, E3[1], head_base + HEAD_H), HEAD_R)
        bz = head_base + HEAD_H - 0.45
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            union(head, cyl((dx * (HEAD_R - 0.05), E3[1] + dy * (HEAD_R - 0.05), bz), (dx * (HEAD_R + BARB_LEN), E3[1] + dy * (HEAD_R + BARB_LEN), bz), BARB_R))
        pieces.append(('1/2 in NPT x 4-port 1/4 in drip head', head))
        depth = STANDOFF + PIPE_R12 + 0.2
        for nm, cz in (('1/2 in stand-off clamp, lower', CLAMP_LOWER_Z), ('1/2 in stand-off clamp, upper', CLAMP_UPPER_Z)):
            blk = box((0.0, -depth / 2, cz), CLAMP_W, depth, CLAMP_H)
            cut(blk, cyl((0, y0, cz - 1), (0, y0, cz + 1), PIPE_R12 + 0.03))
            pieces.append((nm, blk))
        return pieces

    # ---- assembly ----
    irr_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    irr = irr_occ.component
    irr.name = 'Drip Irrigation'
    irr.partNumber = 'IRR-DRIP'
    irr.description = ('Drip risers on the far end wall of each bed, tapped off the 3/4 in main that runs along the stair-step far ends. '
                       'One "Drip riser" component placed per bed; the main is a reference. Built by scripts/fusion_build_irrigation.py (threaded riser stack of 2026-11-15).')
    riser_comp = None
    riser_occs = []
    for d in beds:
        m = adsk.core.Matrix3D.create()
        m.translation = V((d['xmin'] + RISER_X) * IN, d['ymin'] * IN, 0.0)
        if riser_comp is None:
            occ = irr.occurrences.addNewComponent(m)
            riser_comp = occ.component
            riser_comp.name = 'Drip riser'
            riser_comp.partNumber = 'IRR-RISER'
            riser_comp.description = (f'One bed\'s drip riser: 3/4 in slip tee on the main ({MAIN_OFFSET:g} in beyond the end board, {-MAIN_Z:g} in deep), '
                                      f'{stub:g} in stub of 3/4 in pipe, 3/4 in slip x 1/2 in FPT reducing elbow, {RISER_LOWER:g} in threaded riser, FPT ball valve {VZ:g} in above grade, '
                                      f'{RISER_UPPER:g} in riser, FPT elbow, {RISER_WALL:g} in riser through the top board ({HOLE_DIA:g} in hole centred {THROUGH_Z:g} in up), FPT elbow, '
                                      f'{RISER_HEAD:g} in riser to a 4-port 1/4 in head. '
                                      f'Two stand-off clamps at {CLAMP_LOWER_Z:g} and {CLAMP_UPPER_Z:g} in. Local frame: wall outside face at y = 0, bed toward +y, riser at x = 0.')
            bf = riser_comp.features.baseFeatures.add()
            bf.name = 'Drip riser bodies'
            bf.startEdit()
            for nm, body in riser_pieces():
                nb = riser_comp.bRepBodies.add(body, bf)
                nb.name = nm
            bf.finishEdit()
        else:
            occ = irr.occurrences.addExistingComponent(riser_comp, m)
        riser_occs.append((d['letter'], occ))

    # the main: stair-step along the far ends, stepping at the gap centres
    main_occ = irr.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    main = main_occ.component
    main.name = '3/4 in main (existing)'
    main.partNumber = 'IRR-MAIN'
    main.description = (f'Reference only: the existing 3/4 in sprinkler main drawn as a stair-step {MAIN_OFFSET:g} in beyond each bed\'s far end board, '
                        f'axis {-MAIN_Z:g} in below grade, stepping at the gap centres. Its real route is the owner\'s; the risers tee off it.')
    pts = []
    for i, d in enumerate(beds):
        y = d['ymin'] - MAIN_OFFSET
        x0 = d['xmin'] if i == 0 else (beds[i - 1]['xmax'] + d['xmin']) / 2
        x1 = d['xmax'] - RISER_X - 1.0 if i == len(beds) - 1 else (d['xmax'] + beds[i + 1]['xmin']) / 2
        if i == 0:
            pts.append((x0, y))
        pts.append((x1, y))
        if i < len(beds) - 1:
            pts.append((x1, beds[i + 1]['ymin'] - MAIN_OFFSET))
    print('main corners', pts)
    bf = main.features.baseFeatures.add()
    bf.name = 'Main bodies'
    bf.startEdit()
    total = 0.0
    for i in range(len(pts) - 1):
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        seg = cyl((xa, ya, MAIN_Z), (xb, yb, MAIN_Z), PIPE_R34)
        total += math.hypot(xb - xa, yb - ya)
        nb = main.bRepBodies.add(seg, bf)
        nb.name = '3/4 in main, ' + ('along the ends' if abs(ya - yb) < 1e-6 else 'step')
    for i in range(1, len(pts) - 1):
        (xa, ya), (xc, yc), (xb, yb) = pts[i - 1], pts[i], pts[i + 1]
        d1 = (sgn(xa - xc), sgn(ya - yc), 0.0)     # the segments are axis-aligned, so unit directions are just signs
        d2 = (sgn(xb - xc), sgn(yb - yc), 0.0)
        nb = main.bRepBodies.add(elbow((xc, yc, MAIN_Z), d1, d2, HUB_34, HUB_R34), bf)
        nb.name = '3/4 in elbow'
    bf.finishEdit()
    print(f'main length modelled {total:.1f} in, {len(pts) - 2} elbows')

    # ---- materials ----
    lib = app.materialLibraries.itemByName('Fusion Material Library')
    pvc = lib.materials.itemByName('PVC-Piping')
    galv = design.materials.itemByName('Steel, Galvanized') or lib.materials.itemByName('Steel, Galvanized')
    if pvc is None or galv is None:
        raise RuntimeError('materials not found')
    for comp in (riser_comp, main):
        for b in comp.bRepBodies:
            b.material = galv if 'clamp' in b.name else pvc

    # ---- holes through the top far end boards ----
    hole_r = HOLE_DIA / 2
    for d in beds:
        comp, board = d['comp'], d['board']
        face = None
        for f in board.faces:
            g = f.geometry
            if g.objectType == adsk.core.Plane.classType() and g.normal.y < -0.9 and abs(g.origin.y / IN - d['ymin']) < 1e-3:
                face = f
        if face is None:
            raise RuntimeError('outer face not found on ' + board.name)
        sk = comp.sketches.add(face)
        sk.name = 'Drip hole'
        centre = sk.modelToSketchSpace(P(d['xmin'] + RISER_X, d['ymin'], THROUGH_Z))
        sk.sketchCurves.sketchCircles.addByCenterRadius(centre, hole_r * IN)
        prof = None
        for i in range(sk.profiles.count):
            pr = sk.profiles.item(i)
            if abs(pr.areaProperties().area / IN ** 2 - math.pi * hole_r ** 2) < 0.01:
                prof = pr
        if prof is None:
            raise RuntimeError('hole profile not found')
        v0 = board.volume
        done = False
        for direction in (adsk.fusion.ExtentDirections.NegativeExtentDirection, adsk.fusion.ExtentDirections.PositiveExtentDirection):
            try:
                inp = comp.features.extrudeFeatures.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
                inp.setOneSideExtent(adsk.fusion.ThroughAllExtentDefinition.create(), direction)
                inp.participantBodies = [board]
                f = comp.features.extrudeFeatures.add(inp)
            except Exception as e:
                print('   cut attempt failed:', str(e)[:80])
                continue
            dv = (v0 - board.volume) / IN ** 3
            if abs(dv - math.pi * hole_r ** 2 * T) < 0.05:
                f.name = 'Drip hole cut'
                done = True
                break
            f.deleteMe()
        if not done:
            raise RuntimeError('hole cut failed on bed ' + d['letter'])
        print(f"   bed {d['letter']}: hole at x {d['xmin'] + RISER_X:g}, z {THROUGH_Z:g} through {board.name}")

    if design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
    try:
        grp = tl.timelineGroups.add(first_new, tl.count - 1)
        grp.name = 'Drip irrigation'
    except Exception as e:
        print('timeline group not made:', str(e)[:80])

    # ---- verify ----
    bad = [tl.item(i).name for i in range(tl.count) if not tl.item(i).isGroup and tl.item(i).healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState]
    if bad:
        raise RuntimeError('unhealthy: ' + str(bad))
    for letter, occ in riser_occs:
        n = 0
        for b in occ.bRepBodies:
            n += 1
            if 'drip head' in b.name:
                bb = b.boundingBox
                print(f'   riser {letter}: {n} bodies so far; head x {bb.minPoint.x/IN:.2f}..{bb.maxPoint.x/IN:.2f} y {bb.minPoint.y/IN:.2f}..{bb.maxPoint.y/IN:.2f} z {bb.minPoint.z/IN:.2f}..{bb.maxPoint.z/IN:.2f}')
        if n != 13:
            raise RuntimeError(f'riser {letter} has {n} bodies, expected 13')
    print('timeline', tl.count, 'root occs', [o.name for o in root.occurrences])

"""Fusion script: rework beds C and D of the live "Raised Bed Design" model in place (2026-11-08) so each
course of their side walls is two 8 ft boards joined over a 2x8 joint post instead of one 14 or 16 ft board.

Run once, through the Fusion MCP, on the model saved on 2026-11-06. scripts/fusion_build_bed_lumber.py
builds the same beds from scratch (see SIDE_SPLITS there); this is the in-place edit applied to the live
document instead, so the "Drip hole cut" features in its end boards stayed intact.

Per bed, inside the existing bed component:
  - Side boards split: a hidden construction plane at each seam and a Split Body of that course's two side
    boards. Bed D: 96 + 96 in every course, seam 96 in from the near end. Bed C: course 1 is 96 in (near)
    + 72 in (far) and course 2 is 72 + 96, so the seams (96 and 72 in) are staggered. The pieces are renamed
    "Side board 96 in" / "Side board 72 in".
  - "Joint posts" sketch and "Joint post extrude": a 2x8 offcut (1.5 x 7.25 in, drawn at Board_Width) lying
    flat against the inside of the wall, centred on each seam, Courses * Board_Width up from grade and the
    rest of Mid_Post_Length down, like a mid-span post. Bodies "2x8 joint post". Bed C's four are the 24 in
    offcuts of its 72 in pieces.
  - Mid-span posts re-spaced: a 2x4 mid post that a joint post replaces is removed and the rest are moved so
    the mid posts divide each run of wall between its fixed points (a point MIDREF inside each end board, as
    the build script places them, and the seams) evenly, under MAXSP. Bed C: 3 per wall at 43.6 / 84 / 124.4
    in -> 2 per wall at 37.6 / 130.4. Bed D: the post at 96 goes, the two at 49.6 / 142.4 already sit at the
    midpoints and stay.
The new features are grouped in the timeline as "Two-board sides". The document is not saved.
"""
import adsk.core, adsk.fusion, math

IN = 2.54
T = 1.5        # 2x lumber thickness (in)
PT = 1.5       # 2x4 thickness
MIDREF = 1.75  # mid-post runs start this far inside the end boards (the build script's convention)
JW = 7.25      # a 2x8 offcut lying flat: 7.25 in face against the wall (drawn at Board_Width)
MAXSP = 48.0   # max centre-to-centre gap between posts along a long wall (in)

# component name -> seams per course, inches from the near end
SIDE_SPLITS = {
    'Bed C - 14 ft':        {1: [96.0], 2: [72.0]},
    'Bed D - 16 ft x 2 ft': {1: [96.0], 2: [96.0]},
}


def P(x, y, z=0.0):
    return adsk.core.Point3D.create(x * IN, y * IN, z * IN)


def plane_at_y(comp, y_in, name):
    """A hidden construction plane parallel to XZ through world y = y_in (the components sit at the origin)."""
    planes = comp.constructionPlanes
    xz = comp.xZConstructionPlane
    sign = 1.0 if xz.geometry.normal.y > 0 else -1.0
    pin = planes.createInput()
    pin.setByOffset(xz, adsk.core.ValueInput.createByReal(sign * y_in * IN))
    pl = planes.add(pin)
    oy = pl.geometry.origin.y / IN
    if abs(oy - y_in) > 1e-3:
        pl.deleteMe()
        pin = planes.createInput()
        pin.setByOffset(xz, adsk.core.ValueInput.createByReal(-sign * y_in * IN))
        pl = planes.add(pin)
        oy = pl.geometry.origin.y / IN
        if abs(oy - y_in) > 1e-3:
            raise RuntimeError(f'{name}: plane landed at y={oy:g}, wanted {y_in:g}')
    pl.name = name
    pl.isLightBulbOn = False
    return pl


def run(_context):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    pine = design.materials.itemByName('Pine')
    BW = design.userParameters.itemByName('Board_Width').value / IN
    t0 = design.timeline.count
    for occ in root.allOccurrences:
        comp = occ.component
        if comp.name not in SIDE_SPLITS:
            continue
        splits = SIDE_SPLITS[comp.name]
        letter = comp.name.split(' ')[1]
        sides = [b for b in comp.bRepBodies if b.name.startswith('Side board')]
        mids = [b for b in comp.bRepBodies if b.name.startswith('2x4 mid post')]
        if len(sides) != 4 or not mids:
            raise RuntimeError(f'{comp.name}: expected 4 side boards and some mid posts, found {len(sides)} / {len(mids)}')
        xmin = min(b.boundingBox.minPoint.x for b in sides) / IN
        xmax = max(b.boundingBox.maxPoint.x for b in sides) / IN
        L = (max(b.boundingBox.maxPoint.y for b in sides) - min(b.boundingBox.minPoint.y for b in sides)) / IN
        W = xmax - xmin
        ix0, ix1 = xmin + T, xmax - T
        seams = sorted({s for ss in splits.values() for s in ss})

        # 1. split each course's side boards at that course's seams
        planes = {s: plane_at_y(comp, -s, f'Seam {s:g} in') for s in seams}
        sb = comp.features.splitBodyFeatures
        pieces = {}
        for course, ss in sorted(splits.items()):
            cb = [b for b in sides if abs(b.boundingBox.minPoint.z / IN - (course - 1) * BW) < 1e-3]
            if len(cb) != 2:
                raise RuntimeError(f'{comp.name}: course {course} has {len(cb)} side boards')
            for s in ss:
                coll = adsk.core.ObjectCollection.create()
                for b in cb:
                    coll.add(b)
                f = sb.add(sb.createInput(coll, planes[s], True))
                f.name = f'Split course {course} sides at {s:g} in'
                cb = []
                for b in f.bodies:
                    bb = b.boundingBox
                    ln = round((bb.maxPoint.y - bb.minPoint.y) / IN, 3)
                    b.name = f'Side board {ln:g} in'
                    b.material = pine
                    pieces[ln] = pieces.get(ln, 0) + 1
                    cb.append(b)

        # 2. mid-span posts: remove the ones a joint post replaces, move the rest to even gaps
        fixed = sorted([T + MIDREF] + seams + [L - T - MIDREF])
        wanted = []
        for a, b in zip(fixed, fixed[1:]):
            n = int(math.ceil((b - a) / MAXSP)) - 1
            wanted += [a + (b - a) * k / (n + 1) for k in range(1, n + 1)]
        groups = {}
        for b in mids:
            bb = b.boundingBox
            yc = round(-(bb.minPoint.y + bb.maxPoint.y) / 2.0 / IN, 3)
            groups.setdefault(yc, []).append(b)
        unused = set(groups)
        moves = []
        for w in wanted:
            yc = min(unused, key=lambda y: abs(y - w))
            unused.discard(yc)
            moves.append((yc, w, groups[yc]))
        rf = comp.features.removeFeatures
        removed = 0
        for yc in sorted(unused):
            for b in groups[yc]:
                rf.add(b)
                removed += 1
        mf = comp.features.moveFeatures
        for yc, w, bs in moves:
            if abs(w - yc) < 1e-6:
                continue
            coll = adsk.core.ObjectCollection.create()
            for b in bs:
                coll.add(b)
            inp = mf.createInput2(coll)
            inp.defineAsTranslateXYZ(adsk.core.ValueInput.createByReal(0.0), adsk.core.ValueInput.createByReal(-(w - yc) * IN),
                                     adsk.core.ValueInput.createByReal(0.0), True)
            f = mf.add(inp)
            f.name = f'Move mid posts {yc:g} to {w:g} in'

        # 3. joint posts: a 2x8 offcut flat against the inside of each wall behind every seam
        sk = comp.sketches.add(comp.xYConstructionPlane)
        sk.name = 'Joint posts'
        for s in seams:
            cy = -s
            sk.sketchCurves.sketchLines.addTwoPointRectangle(P(ix1 - T, cy - JW / 2.0), P(ix1, cy + JW / 2.0))
            sk.sketchCurves.sketchLines.addTwoPointRectangle(P(ix0, cy - JW / 2.0), P(ix0 + T, cy + JW / 2.0))
        profs = adsk.core.ObjectCollection.create()
        for i in range(sk.profiles.count):
            profs.add(sk.profiles.item(i))
        ext = comp.features.extrudeFeatures
        inp = ext.createInput(profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        inp.setTwoSidesExtent(
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Courses * Board_Width')),
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Mid_Post_Length - Courses * Board_Width')))
        f_j = ext.add(inp)
        f_j.name = 'Joint post extrude'
        for b in f_j.bodies:
            b.name = '2x8 joint post'
            b.material = pine

        n_mid = 2 * len(wanted)
        n_joint = f_j.bodies.count
        layout = ' / '.join(f"course {c}: {' + '.join(f'{x:g}' for x in run_lengths(ss, L))} in" for c, ss in sorted(splits.items()))
        comp.description = (f'Bed {letter}: {W:g} x {L:g} in outside ({L/12:g} ft), inside {W-2*T:g} x {L-2*T:g} in. '
                            f'Side walls are two 8 ft boards per course ({layout}) joined over 2x8 joint posts; end boards {W-2*T:g} in between them. '
                            f'4 corner 2x4 posts + {n_mid} mid-span 2x4 posts (3.5 in face flat against the side boards, Mid_Post_Length long, driven into the ground) '
                            f'+ {n_joint} 2x8 joint posts ({JW:g} in face flat against the inside of the wall behind each seam, same length as a mid-span post). '
                            + ('The joint posts are the 24 in offcuts of the 72 in side pieces. ' if 72.0 in pieces else '')
                            + f'Reworked in place 2026-11-08 (scripts/fusion_split_sides.py).')
        print(f'{comp.name}: side pieces {dict(sorted(pieces.items()))}, mid posts removed {removed}, moved to {[round(w, 3) for w in wanted]}, '
              f'joint posts {n_joint} at {seams} in')
    t1 = design.timeline.count
    if t1 > t0:
        g = design.timeline.timelineGroups.add(t0, t1 - 1)
        g.name = 'Two-board sides'
    print('timeline', t0, '->', t1, 'marker', design.timeline.markerPosition)


def run_lengths(seams, L):
    pts = [0.0] + sorted(seams) + [L]
    return [b - a for a, b in zip(pts, pts[1:])]

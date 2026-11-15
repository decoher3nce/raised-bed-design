"""Fusion script: rework the bed lumber of the live "Raised Bed Design" model in place (2026-11-15) so that every
bed but A is built from 8 ft boards and the 2x4 mid-span stakes stand on a regular grid.

Run once, through the Fusion MCP or Utilities > Scripts and Add-Ins, on the model saved on 2026-11-08. It had NOT
been run when it was written: Fusion was not reachable, so scripts/planned_layout.py applies the same layout to the
extract and the BOM was made from that. Check the printed summary against that overlay's (python3
scripts/planned_layout.py) before saving, then run scripts/fusion_extract_model.py and scripts/make_bom.py again:
the overlay then finds nothing left to do. scripts/fusion_build_bed_lumber.py builds the same beds from scratch;
this is the in-place edit, so the "Drip hole cut" features in the end boards and the arch parts stay as they are.

Per bed, inside the existing bed component:
  - Bed B only (SIDE_SPLITS): the side boards are split like those of beds C and D on 2026-11-08 (scripts/
    fusion_split_sides.py): a hidden construction plane at each seam and a Split Body of that course's two side
    boards. Course 1 is 96 in (near) + 48 in (far) and course 2 is 48 + 96, so the seams (96 and 48 in from the
    near end) are staggered. The pieces are renamed "Side board 96 in" / "Side board 48 in". A "Joint posts" sketch
    and "Joint post extrude" add a 2x8 x Mid_Post_Length joint post lying flat against the inside of each wall
    behind every seam (bodies "2x8 joint post"). At the saw, each 48 in piece comes off an 8 ft board whose other
    half is an end board; the four joint posts come from one more 8 ft board.
  - Every bed: the existing "2x4 mid post" bodies are removed (Remove features) and a "Stake grid" sketch with a
    two-sided "Stake grid extrude" puts a new "2x4 mid post" every STAKE_PITCH (24 in) from the near end on both
    long walls, flat against the side boards, Courses * Board_Width up from grade and the rest of Mid_Post_Length
    down. Every bed is a whole number of pitches long and every seam falls on the grid, so the joint post stands
    in for the stake at a seam: Bed A 24/48/72/96, Bed B 24/72/120, Bed C 24/48/120/144, Bed D 24/48/72/120/144/168
    in from the near end.
The new features are grouped in the timeline as "8 ft boards and stake grid". The document is not saved.
"""
import adsk.core, adsk.fusion, re

IN = 2.54
T = 1.5             # 2x lumber thickness (in)
PT, PW = 1.5, 3.5   # a 2x4 lying flat against the wall: 1.5 in into the bed, 3.5 in along it
JW = 7.25           # a 2x8 offcut lying flat: 7.25 in face against the wall (drawn at Board_Width)
STAKE_PITCH = 24.0  # mid-span stakes, centre to centre along each long wall, from the near end (in)

BEDS = ('Bed A - 10 ft', 'Bed B - 12 ft', 'Bed C - 14 ft', 'Bed D - 16 ft x 2 ft')
# component name -> seams per course, inches from the near end (beds whose side boards are still one piece)
SIDE_SPLITS = {
    'Bed B - 12 ft': {1: [96.0], 2: [48.0]},
}


def P(x, y, z=0.0):
    return adsk.core.Point3D.create(x * IN, y * IN, z * IN)


def run_lengths(seams, L):
    pts = [0.0] + sorted(seams) + [L]
    return [b - a for a, b in zip(pts, pts[1:])]


def stake_stations(L, seams):
    """Stake centres, inches from the near end: every STAKE_PITCH, clear of the far corner post, not where a joint post stands."""
    out = []
    k = 1
    while k * STAKE_PITCH < L - (T + PT + PW / 2.0) + 1e-6:
        s = k * STAKE_PITCH
        if not any(abs(s - j) < (JW + PW) / 2.0 for j in seams):
            out.append(s)
        k += 1
    return out


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
        if comp.name not in BEDS:
            continue
        letter = comp.name.split(' ')[1]
        sides = [b for b in comp.bRepBodies if b.name.startswith('Side board')]
        mids = [b for b in comp.bRepBodies if b.name.startswith('2x4 mid post')]
        if not sides or not mids:
            raise RuntimeError(f'{comp.name}: expected side boards and mid posts, found {len(sides)} / {len(mids)}')
        xmin = min(b.boundingBox.minPoint.x for b in sides) / IN
        xmax = max(b.boundingBox.maxPoint.x for b in sides) / IN
        near = max(b.boundingBox.maxPoint.y for b in sides) / IN     # the near end: y = 0 in this model
        far = min(b.boundingBox.minPoint.y for b in sides) / IN
        L = near - far
        ix0, ix1 = xmin + T, xmax - T
        ext = comp.features.extrudeFeatures

        def stake_extrude(profs, feat_name, body_name):
            """Courses * Board_Width up from grade and the rest of Mid_Post_Length down, like every mid-span post."""
            inp = ext.createInput(profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            inp.setTwoSidesExtent(
                adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Courses * Board_Width')),
                adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Mid_Post_Length - Courses * Board_Width')))
            f = ext.add(inp)
            f.name = feat_name
            for b in f.bodies:
                b.name = body_name
                b.material = pine
            return f

        # 1. two side boards per course where the bed still has one (Bed B)
        splits = SIDE_SPLITS.get(comp.name)
        pieces = {}
        n_joint_new = 0
        if splits:
            if len(sides) != 4:
                raise RuntimeError(f'{comp.name}: expected 4 one-piece side boards, found {len(sides)}')
            new_seams = sorted({s for ss in splits.values() for s in ss})
            planes = {s: plane_at_y(comp, near - s, f'Seam {s:g} in') for s in new_seams}
            sb = comp.features.splitBodyFeatures
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
            sk = comp.sketches.add(comp.xYConstructionPlane)
            sk.name = 'Joint posts'
            for s in new_seams:
                cy = near - s
                sk.sketchCurves.sketchLines.addTwoPointRectangle(P(ix1 - T, cy - JW / 2.0), P(ix1, cy + JW / 2.0))
                sk.sketchCurves.sketchLines.addTwoPointRectangle(P(ix0, cy - JW / 2.0), P(ix0 + T, cy + JW / 2.0))
            profs = adsk.core.ObjectCollection.create()
            for i in range(sk.profiles.count):
                profs.add(sk.profiles.item(i))
            n_joint_new = stake_extrude(profs, 'Joint post extrude', '2x8 joint post').bodies.count

        # 2. mid-span stakes on the grid: every seam in the bed, old or new, keeps its joint post instead of a stake
        seams = sorted({round(near - b.boundingBox.maxPoint.y / IN, 3) for b in comp.bRepBodies
                        if b.name.startswith('Side board') and b.boundingBox.maxPoint.y / IN < near - 1e-3})
        want = stake_stations(L, seams)
        have = sorted({round(near - (b.boundingBox.minPoint.y + b.boundingBox.maxPoint.y) / 2.0 / IN, 2) for b in mids})
        n_removed = n_new = 0
        if [round(w, 2) for w in want] != have:
            rf = comp.features.removeFeatures
            for b in mids:
                rf.add(b)
                n_removed += 1
            sk = comp.sketches.add(comp.xYConstructionPlane)
            sk.name = 'Stake grid'
            for s in want:
                cy = near - s
                sk.sketchCurves.sketchLines.addTwoPointRectangle(P(ix1 - PT, cy - PW / 2.0), P(ix1, cy + PW / 2.0))
                sk.sketchCurves.sketchLines.addTwoPointRectangle(P(ix0, cy - PW / 2.0), P(ix0 + PT, cy + PW / 2.0))
            profs = adsk.core.ObjectCollection.create()
            for i in range(sk.profiles.count):
                profs.add(sk.profiles.item(i))
            n_new = stake_extrude(profs, 'Stake grid extrude', '2x4 mid post').bodies.count

        # 3. the component's description follows
        desc = comp.description or ''
        if splits:
            layout = ' / '.join(f"course {c}: {' + '.join(f'{x:g}' for x in run_lengths(ss, L))} in" for c, ss in sorted(splits.items()))
            desc = desc.replace('Side boards full length outside, end boards',
                                f'Side walls are two 8 ft boards per course ({layout}) joined over {n_joint_new} 2x8 joint posts; end boards')
        if n_new:
            desc = re.sub(r'\+ \d+ mid-span 2x4 posts', f'+ {n_new} mid-span 2x4 posts every {STAKE_PITCH:g} in', desc)
        comp.description = desc + ' Reworked in place 2026-11-15 (scripts/fusion_stake_grid.py).'
        print(f'{comp.name}: side pieces {dict(sorted(pieces.items()))}, joint posts added {n_joint_new}, seams at {seams} in, '
              f'mid posts removed {n_removed}, new ones {n_new} at {want} in on both walls')
    t1 = design.timeline.count
    if t1 > t0:
        g = design.timeline.timelineGroups.add(t0, t1 - 1)
        g.name = '8 ft boards and stake grid'
    print('timeline', t0, '->', t1, 'marker', design.timeline.markerPosition, '(not saved)')

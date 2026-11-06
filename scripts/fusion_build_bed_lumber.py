"""Fusion script: build parametric lumber for the four raised beds of the Raised Bed Design document.

Run from Fusion (Utilities > Scripts and Add-Ins) or through the Fusion MCP.
It was used once on 2026-11-05 to add the "Bed Lumber" component (then with
4x4 posts). The live model was then reworked in place the same day: the posts
became 2x4s by editing each bed's "Posts" sketch, and the mid-span posts were
rotated flat and split into their own two-sided extrude. This script builds
that final version directly. Re-running it on a design that already has
"Bed Lumber" would add a second copy.

What it builds, per bed, inside a new "Bed Lumber" component:
  - 2 side boards (full outer length, outside) and 2 end boards (between them),
    extruded Board_Width tall and stacked with a rectangular pattern whose
    quantity is the user parameter Courses.
  - One "Posts" sketch holding every post footprint, driving two extrudes:
      "Post extrude"     4 corner 2x4s, Courses * Board_Width tall, standing
                         edge-on: the 1.5 in edge against the side board and
                         the 3.5 in face against the end board, so side-board
                         screws there bite 3.5 in of post.
      "Mid post extrude" mid-span 2x4s along both long walls at <= MAXSP
                         spacing, lying flat with the 3.5 in face against the
                         side board. They run Courses * Board_Width up from
                         grade and the rest of Mid_Post_Length down, so they
                         are stakes driven into the ground.
      "Trellis post extrude" (beds A and B) the inside corner post at the
                         near end (ARCH_POSTS), same footprint and orientation
                         but Trellis_Post_Length long with Trellis_Post_Embed of
                         it in the ground: an uncut 8 ft 2x4 whose top is just
                         above where the arch panel crosses it, so the panel's
                         edge wire can be screwed to its face near the crown.
  - "Arch anchors" sketch (beds A and B) with "Sill extrude" and "Stake
    extrude": a flat 2x4 sill lying on grade along the bed centreline between
    the panel edges (ARCH_FEET), and a Mid_Post_Length stake at each end of
    it, Stake_Above_Sill above the sill and the rest in the ground. The arch
    feet sit on the sills and the edge wires are screwed to the stakes.
    The arches themselves (component "Hogwire Arches") are not built here; in
    the live model Arch AB has a parametric Move "Onto the sills" of 21 in
    along x, 1.25 in along y and Board_Thickness up, which puts its feet on
    the sills at the bed centrelines with its edge wire against the posts.
    Mid-post centerlines interpolate between points MIDREF inside each end
    board (the 4x4 centerlines the beds were first built with), which is
    where the live model has them.
Bed outer footprints match the hidden massing bodies in "Raised Beds".

User parameters it adds (edit these in Modify > Change Parameters):
  Board_Width      7.25 in  (2x8). 9.25 in = 2x10, 5.5 in = 2x6
  Courses          2        stacked courses; bed height = Courses * Board_Width
  Mid_Post_Length  24 in    total length of a mid-span post; 24 - 14.5 = 9.5 in in the ground
  Trellis_Post_Length 96 in total length of each inside corner post under an arch (uncut 8 ft stick)
  Trellis_Post_Embed  20 in how deep that post is set; 96 - 20 = 76 in above grade
  Stake_Above_Sill    12 in height of each arch-foot stake above its sill (the rest of the
                            Mid_Post_Length stake is in the ground)
  Board_Thickness, Post_Size  reference only (sketches are drawn at 1.5 / 3.5 in)
"""
import adsk.core, adsk.fusion, math

IN = 2.54


def P(x, y, z=0.0):
    return adsk.core.Point3D.create(x * IN, y * IN, z * IN)


# name, letter, xmax, outer width, outer length, massing body it replaces
BEDS = [
    ('Bed A - 10 ft',        'A', -198.0, 51.0, 120.0, '4th Bed'),
    ('Bed B - 12 ft',        'B', -123.0, 51.0, 144.0, '3rd Bed'),
    ('Bed C - 14 ft',        'C',  -48.0, 51.0, 168.0, '2nd Bed'),
    ('Bed D - 16 ft x 2 ft', 'D',    0.0, 24.0, 192.0, '1st Bed'),
]
T = 1.5       # 2x lumber actual thickness (in)
PT = 1.5      # 2x4 thickness (in)
PW = 3.5      # 2x4 width (in)
MIDREF = 1.75 # mid-post centerlines interpolate between points this far inside the end boards (in)
MAXSP = 48.0  # max post spacing along long walls (in)
# hog-wire arch supports: wall ('W' = xmin side, 'E' = xmax side) and the world y range of the post.
# Every post on that wall inside the range becomes a Trellis_Post_Length trellis post (bed-centre scheme
# of 2026-11-06: Arch AB runs from the centre of bed A to the centre of bed B and is held near its crown
# by the two inside corner posts at the near end).
ARCH_POSTS = {
    'A': [('E', 0.0, -3.5)],   # Arch AB: bed A's NE corner post
    'B': [('W', 0.0, -3.5)],   # Arch AB: bed B's NW corner post
}
# arch feet: bed centreline x and the world y range the panel covers (its edge wires sit against the stakes)
ARCH_FEET = {
    'A': (-223.5, -3.0, -63.5),
    'B': (-148.5, -3.0, -63.5),
}


def run(_context):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    ups = design.userParameters

    def ensure(name, expr, unit, comment):
        p = ups.itemByName(name)
        if p is None:
            p = ups.add(name, adsk.core.ValueInput.createByString(expr), unit, comment)
        return p

    ensure('Board_Thickness', '1.5 in', 'in', 'Actual thickness of 2x lumber (reference; sketches drawn at 1.5 in)')
    ensure('Board_Width', '7.25 in', 'in', 'Actual face width of one course: 7.25 = 2x8, 9.25 = 2x10, 5.5 = 2x6')
    ensure('Courses', '2', '', 'Number of stacked board courses per bed (bed height = Courses * Board_Width)')
    ensure('Post_Size', '3.5 in', 'in', '2x4 posts are 1.5 x 3.5 in; value is reference only')
    ensure('Mid_Post_Length', '24 in', 'in',
           'Total length of each mid-span 2x4 post: Courses * Board_Width above grade, the rest driven into the ground')
    ensure('Trellis_Post_Length', '96 in', 'in',
           'Total length of each 2x4 trellis post (the inside corner post under each arch, uncut 8 ft stick): Trellis_Post_Embed in the ground, the rest above grade')
    ensure('Trellis_Post_Embed', '20 in', 'in',
           'How deep each 8 ft trellis post is set; 20 in puts its top 4 in above where the panel crosses it')
    ensure('Stake_Above_Sill', '12 in', 'in',
           'Height of each arch-foot stake above the sill it is screwed to; the rest of the Mid_Post_Length stake is in the ground')
    pine = design.materials.itemByName('Pine')

    parentOcc = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    parent = parentOcc.component
    parent.name = 'Bed Lumber'
    parent.partNumber = 'ASM-BED-LUMBER'
    parent.description = ('Buildable lumber for all four beds: 2x boards (Courses x Board_Width tall) with 2x4 posts inside: '
                          'corner posts edge-on to the side boards, mid-span posts flat against them and Mid_Post_Length long '
                          'so they drive into the ground.')

    for (name, letter, xmax, W, L, massing) in BEDS:
        occ = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component
        comp.name = name
        comp.partNumber = f'BED-{letter}'
        xmin = xmax - W
        ymin = -L
        ix0, ix1 = xmin + T, xmax - T
        iy0, iy1 = ymin + T, -T
        n_mid = int(math.ceil(L / MAXSP)) - 1
        comp.description = (f'Bed {letter}: {W:g} x {L:g} in outside ({L/12:g} ft), inside {W-2*T:g} x {L-2*T:g} in. '
                            f'Side boards full length outside, end boards {W-2*T:g} in between them, '
                            f'4 corner 2x4 posts + {2*n_mid} mid-span 2x4 posts (3.5 in face flat against the side boards, '
                            f'Mid_Post_Length long, driven into the ground). Replaces massing body "{massing}".')

        ext = comp.features.extrudeFeatures

        def extrude_rects(sketch_name, rects, dist_expr, feat_name):
            sk = comp.sketches.add(comp.xYConstructionPlane)
            sk.name = sketch_name
            for (x0, y0, x1, y1) in rects:
                sk.sketchCurves.sketchLines.addTwoPointRectangle(P(x0, y0), P(x1, y1))
            profs = adsk.core.ObjectCollection.create()
            for i in range(sk.profiles.count):
                profs.add(sk.profiles.item(i))
            inp = ext.createInput(profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            inp.setDistanceExtent(False, adsk.core.ValueInput.createByString(dist_expr))
            f = ext.add(inp)
            f.name = feat_name
            return f

        f_sides = extrude_rects('Side boards', [
            (xmax - T, ymin, xmax, 0.0),
            (xmin, ymin, xmin + T, 0.0),
        ], 'Board_Width', 'Course 1 sides')
        f_ends = extrude_rects('End boards', [
            (ix0, -T, ix1, 0.0),
            (ix0, ymin, ix1, ymin + T),
        ], 'Board_Width', 'Course 1 ends')
        course_bodies = adsk.core.ObjectCollection.create()
        for b in f_sides.bodies:
            b.name = f'Side board {L:g} in'
            b.material = pine
            course_bodies.add(b)
        for b in f_ends.bodies:
            b.name = f'End board {W-2*T:g} in'
            b.material = pine
            course_bodies.add(b)

        rp = comp.features.rectangularPatternFeatures
        rinp = rp.createInput(course_bodies, comp.zConstructionAxis,
                              adsk.core.ValueInput.createByString('Courses'),
                              adsk.core.ValueInput.createByString('Board_Width'),
                              adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
        # createInput defaults direction two to 3 coincident copies; force it to 1.
        rinp.quantityTwo = adsk.core.ValueInput.createByString('1')
        rpf = rp.add(rinp)
        rpf.name = 'Stack courses'
        if rpf.quantityTwo is not None and rpf.quantityTwo.expression != '1':
            rpf.quantityTwo.expression = '1'

        # corner posts: edge-on, PT along the side board, PW along the end board
        corner_rects = [
            (ix1 - PW, iy1 - PT, ix1, iy1),
            (ix0, iy1 - PT, ix0 + PW, iy1),
            (ix0, iy0, ix0 + PW, iy0 + PT),
            (ix1 - PW, iy0, ix1, iy0 + PT),
        ]
        # mid-span posts: flat, PW along the side board, PT into the bed
        mid_rects = []
        c_top = iy1 - MIDREF
        c_bot = iy0 + MIDREF
        for k in range(1, n_mid + 1):
            cy = c_top + (c_bot - c_top) * k / (n_mid + 1)
            mid_rects.append((ix1 - PT, cy - PW / 2.0, ix1, cy + PW / 2.0))
            mid_rects.append((ix0, cy - PW / 2.0, ix0 + PT, cy + PW / 2.0))
        sk = comp.sketches.add(comp.xYConstructionPlane)
        sk.name = 'Posts'
        for (x0, y0, x1, y1) in corner_rects + mid_rects:
            sk.sketchCurves.sketchLines.addTwoPointRectangle(P(x0, y0), P(x1, y1))
        corner_profs = adsk.core.ObjectCollection.create()
        mid_profs = adsk.core.ObjectCollection.create()
        trellis_profs = adsk.core.ObjectCollection.create()
        for i in range(sk.profiles.count):
            pr = sk.profiles.item(i)
            bb = pr.boundingBox
            x0, y0, x1, y1 = bb.minPoint.x / IN, bb.minPoint.y / IN, bb.maxPoint.x / IN, bb.maxPoint.y / IN
            is_corner = abs(y1 - iy1) < 1e-3 or abs(y0 - iy0) < 1e-3
            side = 'W' if abs(x0 - ix0) < 1e-3 else 'E'
            is_trellis = any(s == side and y1 <= ya + 0.01 and y0 >= yb - 0.01 for (s, ya, yb) in ARCH_POSTS.get(letter, []))
            (trellis_profs if is_trellis else corner_profs if is_corner else mid_profs).add(pr)
        inp = ext.createInput(corner_profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        inp.setDistanceExtent(False, adsk.core.ValueInput.createByString('Courses * Board_Width'))
        f_posts = ext.add(inp)
        f_posts.name = 'Post extrude'
        for b in f_posts.bodies:
            b.name = '2x4 corner post'
            b.material = pine
        inp = ext.createInput(mid_profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        inp.setTwoSidesExtent(
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Courses * Board_Width')),
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Mid_Post_Length - Courses * Board_Width')))
        f_mid = ext.add(inp)
        f_mid.name = 'Mid post extrude'
        for b in f_mid.bodies:
            b.name = '2x4 mid post'
            b.material = pine
        n_tr = 0
        if trellis_profs.count:
            inp = ext.createInput(trellis_profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            inp.setTwoSidesExtent(
                adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Trellis_Post_Length - Trellis_Post_Embed')),
                adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Trellis_Post_Embed')))
            f_tr = ext.add(inp)
            f_tr.name = 'Trellis post extrude'
            for b in f_tr.bodies:
                b.name = '2x4 trellis post'
                b.material = pine
            n_tr = f_tr.bodies.count
            comp.description += f' {n_tr} of the posts are Trellis_Post_Length long (bodies "2x4 trellis post") and hold the hog-wire arch near its crown.'
        if letter in ARCH_FEET:
            xc, ya, yb = ARCH_FEET[letter]
            sk2 = comp.sketches.add(comp.xYConstructionPlane)
            sk2.name = 'Arch anchors'
            for (x0, y0, x1, y1) in ((xc - PW / 2, ya, xc + PW / 2, yb),          # sill between the stakes
                                     (xc - PW / 2, ya, xc + PW / 2, ya + PT),     # near stake, inside the end board
                                     (xc - PW / 2, yb - PT, xc + PW / 2, yb)):    # far stake
                sk2.sketchCurves.sketchLines.addTwoPointRectangle(P(x0, y0), P(x1, y1))
            sill_profs = adsk.core.ObjectCollection.create()
            stake_profs = adsk.core.ObjectCollection.create()
            for i in range(sk2.profiles.count):
                pr = sk2.profiles.item(i)
                bb = pr.boundingBox
                (sill_profs if (bb.maxPoint.y - bb.minPoint.y) / IN > 20 else stake_profs).add(pr)
            inp = ext.createInput(sill_profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            inp.setDistanceExtent(False, adsk.core.ValueInput.createByString('Board_Thickness'))
            f_sill = ext.add(inp)
            f_sill.name = 'Sill extrude'
            for b in f_sill.bodies:
                b.name = '2x4 sill'
                b.material = pine
            inp = ext.createInput(stake_profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            inp.setTwoSidesExtent(
                adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Board_Thickness + Stake_Above_Sill')),
                adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString('Mid_Post_Length - Board_Thickness - Stake_Above_Sill')))
            f_stk = ext.add(inp)
            f_stk.name = 'Stake extrude'
            for b in f_stk.bodies:
                b.name = '2x4 stake'
                b.material = pine
            comp.description += ' A 2x4 sill on grade along the bed centreline with a stake at each end anchors the arch foot (bodies "2x4 sill", "2x4 stake").'
        print(f'{name}: sides={f_sides.bodies.count} ends={f_ends.bodies.count} '
              f'corner posts={f_posts.bodies.count} mid posts={f_mid.bodies.count} trellis posts={n_tr} total bodies={comp.bRepBodies.count}')

    # hide the massing bodies; they stay as the layout reference the arch sketches use
    for occ in root.occurrences:
        if occ.component.name == 'Raised Beds':
            for b in occ.component.bRepBodies:
                b.isVisible = False
    print('massing bodies hidden; timeline count', design.timeline.count,
          'marker', design.timeline.markerPosition)

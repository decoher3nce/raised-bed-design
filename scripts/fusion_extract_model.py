"""Fusion script: dump every body in the active design to data/model_extract.json.

Read-only. Run it from Fusion (Utilities > Scripts and Add-Ins) or through the
Fusion MCP, then run scripts/make_bom.py to regenerate BOM.md, BOM.csv and
bom.html from the fresh extract.
"""
import adsk.core, adsk.fusion, json, os

IN = 2.54
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'model_extract.json')


def run(_context):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    out = {'document': app.activeDocument.name, 'units': 'in', 'params': {},
           'components': [], 'bodies': []}
    for p in design.userParameters:
        out['params'][p.name] = {'expression': p.expression,
                                 'value_in': round(p.value / IN, 4) if p.unit else p.value,
                                 'unit': p.unit, 'comment': p.comment}
    for occ in root.allOccurrences:
        c = occ.component
        out['components'].append({'path': occ.fullPathName, 'name': c.name,
                                  'partNumber': c.partNumber, 'description': c.description,
                                  'visible': occ.isVisible, 'bodyCount': c.bRepBodies.count})
        for b in occ.bRepBodies:
            bb = b.boundingBox
            dims = sorted([(bb.maxPoint.x - bb.minPoint.x) / IN,
                           (bb.maxPoint.y - bb.minPoint.y) / IN,
                           (bb.maxPoint.z - bb.minPoint.z) / IN])
            try:
                mass = b.physicalProperties.mass
            except Exception:
                mass = None
            out['bodies'].append({
                'component': c.name, 'path': occ.fullPathName, 'body': b.name,
                'visible': bool(occ.isVisible and b.isVisible),
                'material': b.material.name if b.material else None,
                'appearance': b.appearance.name if b.appearance else None,
                'dims_in': [round(d, 3) for d in dims],
                'min': [round(bb.minPoint.x / IN, 3), round(bb.minPoint.y / IN, 3), round(bb.minPoint.z / IN, 3)],
                'max': [round(bb.maxPoint.x / IN, 3), round(bb.maxPoint.y / IN, 3), round(bb.maxPoint.z / IN, 3)],
                'volume_in3': round(b.volume / IN ** 3, 2),
                'mass_kg': round(mass, 4) if mass is not None else None,
            })
    site = []
    for s in root.sketches:
        for l in s.sketchCurves.sketchLines:
            g = l.worldGeometry
            site.append([[round(g.startPoint.x / IN, 2), round(g.startPoint.y / IN, 2)],
                         [round(g.endPoint.x / IN, 2), round(g.endPoint.y / IN, 2)]])
    out['site_lines'] = site
    out['materials'] = {}
    for m in design.materials:
        dens = None
        for p in m.materialProperties:
            if p.id == 'structural_Density':
                dens = p.value
        out['materials'][m.name] = {'density_kg_m3': dens}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=1)
    print('wrote', OUT, 'bodies', len(out['bodies']))

# Raised Bed Design

Fusion 360 build scripts, a bill of materials and a design-study page for a set of four raised garden beds:
2x8 walls on 2x4 posts and stakes, every bed but the shortest built from 8 ft boards, a hog-wire trellis arch standing on sills between two beds, low-tunnel hoops over one bed,
and a 1/2 in drip riser with a ball valve on the far end wall of every bed, tapped off a buried 3/4 in main.

The Fusion document is called *Raised Bed Design*. Its bodies drive everything here: the lumber, posts, fasteners,
pavers, soil, arch, hoops and drip parts in the BOM are counted from an extract of the model, not typed in.

## Layout

| Path | What it is |
|---|---|
| `scripts/fusion_build_bed_lumber.py` | Builds the bed lumber (boards, corner posts, mid-span stakes every 24 in, trellis posts, arch sills and stakes, and the two-board side walls of beds B, C and D with their 2x8 joint posts) in Fusion from the massing bodies and the user parameters. |
| `scripts/fusion_split_sides.py` | The in-place edit applied to the live model on 2026-11-08: splits the side boards of beds C and D into two 8 ft pieces per course, adds the 2x8 joint posts behind the seams and re-spaces the 2x4 mid posts. |
| `scripts/fusion_stake_grid.py` | The in-place edit of 2026-11-15: gives Bed B the same two-board sides from 8 ft stock and puts every bed's 2x4 mid-span stakes on a 24 in grid. Written while Fusion was out of reach, so it has not been run yet. |
| `scripts/planned_layout.py` | Applies a planned change to the extract in memory, so the BOM can be made before the model is edited. `make_bom.py` calls it on every run; once the model has the change and is extracted again it finds nothing to do, and the "planned" notes drop out of the BOM. |
| `scripts/fusion_build_irrigation.py` | Builds the drip risers, cuts the hole in each far end wall, and draws the reference main. Re-runnable; constants at the top. |
| `scripts/fusion_extract_model.py` | Run inside Fusion (read-only): dumps every body to `data/model_extract.json`. |
| `scripts/make_bom.py` | Turns the extract into `BOM.md`, `BOM.csv`, `BOM-by-bed.csv`, `bom.html` and `shopping-list.html`, a two-page black-and-white sheet to print and take to the store. `bom.html` has the plan, elevations, details, drip drawings, and a materials checklist for each bed whose ticks are kept in the browser. Lumber is listed as store-length sticks to buy, with store prices and a cut diagram for every stick; the prices and stocked lengths are the `STOCK_PRICES` table at the top of the script. |
| `scripts/cutstock.py` | The small exact solver behind the buy lists: the cheapest set of stocked sticks that yields one bed's pieces, with posts allowed to run a little short when that fits one more on a stick. |
| `scripts/make_arch_study.py` | Elastica study of the hog-wire arch: `arch-study.html` and `data/arch_study.json`. |
| `renders/` | Screenshots of the model as it was built. |

## Regenerating

1. In Fusion, run `scripts/fusion_extract_model.py` (Utilities > Scripts and Add-Ins, or through the Fusion MCP).
2. `python3 scripts/make_bom.py` (it prints what `planned_layout.py` still had to apply, if anything)
3. `python3 scripts/make_arch_study.py` (needs `bom.html` for its stylesheet)

The pages are plain HTML with inline SVG, light and dark themes, and a palette chosen for red-green colour blindness
(blue for the arch and hoops, orange for lumber, patterns and labels as a second channel).

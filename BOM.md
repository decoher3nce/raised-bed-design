# Raised Bed Design: bill of materials

Generated 2026-11-08 from the Fusion design **Raised Bed Design** (data/model_extract.json). Quantities marked *Model* are counted from model bodies; *Derived* rows are computed from the model geometry; *Estimate* rows are not modeled.

## Layout

Four beds in a 24 ft x 18 ft plot, a 2-row paver walkway along the top edge, 12 in paver paths between beds, and a 16 ft hog-wire trellis arch from the centre of Bed A to the centre of Bed B, its feet on 2x4 sills on the ground and its top held by the two inside corner posts, uncut 8 ft 2x4s (a second arch, Arch BC, is modeled but parked). Bed letters follow the arch names in the model (Arch AB spans beds A and B). 6 low-tunnel hoops of 1 in tube stand over Bed C at 31 in pitch.

| Bed | Model body | Outside (W x L) | Inside | Height | Posts | Soil |
|---|---|---|---|---|---|---|
| **A** | 4th Bed | 51 in x 10 ft | 48 x 117 in | 14.5 in (2 x 2x8) | 8 x 2x4 (3 corner + 1 uncut 8 ft trellis corner + 4 mid), 39 in max spacing + 1 arch sill with 2 stakes | 47 cu ft |
| **B** | 3rd Bed | 51 in x 12 ft | 48 x 141 in | 14.5 in (2 x 2x8) | 8 x 2x4 (3 corner + 1 uncut 8 ft trellis corner + 4 mid), 47 in max spacing + 1 arch sill with 2 stakes | 56 cu ft |
| **C** | 2nd Bed | 51 in x 14 ft | 48 x 165 in | 14.5 in (2 x 2x8) | 8 x 2x4 (4 corner + 4 mid) + 4 x 2x8 joint, 35 in max spacing | 66 cu ft |
| **D** | 1st Bed | 24 in x 16 ft | 21 x 189 in | 14.5 in (2 x 2x8) | 8 x 2x4 (4 corner + 4 mid) + 2 x 2x8 joint, 47 in max spacing | 33 cu ft |

Bed walls are 2x8 on edge, 2 courses, 14.5 in tall. Side boards run outside the end boards, which sit between them. Beds A and B use one board per course. Beds C and D use two boards per course from 8 ft stock (Bed C course 1: 96 + 72 in, course 2: 72 + 96 in; Bed D course 1: 96 + 96 in, course 2: 96 + 96 in), meeting over 2x8 joint posts: 24 in pieces of 2x8 lying flat with the 7 1/4 in face against the inside of the wall, 9.5 in in the ground like a mid-span post. Bed C's joint posts are the offcuts of its 72 in side pieces. Bed C staggers the seams course to course, so no joint runs the full height of the wall. 2x4 corner posts stand inside every corner, edge-on, so side-board screws there get 3.5 in of post to bite into; 2x4 mid-span posts lie flat against the long walls and run 24 in long, 9.5 in of it driven into the ground. Under the arch, the inside corner post at the near end of beds A and B is an uncut 8 ft 2x4 (trellis post) set 20 in deep, 76 in above grade, and a 60.5 in 2x4 sill with a 24 in stake at each end lies on the ground along each of those beds' centrelines to anchor the arch foot. Switching the Fusion parameter `Board_Width` to 9.25 in gives 2x10 walls 18.5 in tall with the same cut list.

## Shopping list

| Section | Item | Qty | Unit | Spec | Source | Notes |
|---|---|---|---|---|---|---|
| Lumber | 2x8 x 8 ft | 22 | ea | $14.78 each, $325.16; 2x10: $21.08 each | Store price | Bed A 2: 2 end boards x 47 15/16 in (no offcut); Bed B 2: 2 end boards x 47 15/16 in (no offcut); Bed C 4: side board, whole, 4: 1 side board x 72 in + 1 joint post x 23 7/8 in (no offcut), 2: 2 end boards x 47 15/16 in (no offcut); Bed D 8: side board, whole |
| Lumber | 2x8 x 10 ft | 4 | ea | $18.88 each, $75.52; 2x10: $26.88 each | Store price | Bed A 4: side board, whole |
| Lumber | 2x8 x 12 ft | 5 | ea | $22.68 each, $113.40; 2x10: $32.78 each | Store price | Bed B 4: side board, whole; Bed D 1: 4 end boards x 21 in + 2 joint posts x 24 in (11 3/8 in offcut) |
| Lumber | 2x4 x 6 ft | 4 | ea | $5.28 each, $21.12 | Store price | Bed A 1: 2 mid-span posts x 23 7/8 in + 1 arch stake x 23 7/8 in (no offcut); Bed B 1: 2 mid-span posts x 23 7/8 in + 1 arch stake x 23 7/8 in (no offcut); Bed C 1: 3 corner posts x 14 1/2 in + 1 mid-span post x 24 in (4 1/8 in offcut); Bed D 1: 3 corner posts x 14 1/2 in + 1 mid-span post x 24 in (4 1/8 in offcut) |
| Lumber | 2x4 x 8 ft | 8 | ea | $7.08 each, $56.64 | Store price | Bed A 1: 3 corner posts x 14 1/2 in + 2 mid-span posts x 24 in (4 in offcut), 1: trellis post, whole, 1: 1 arch sill x 60 1/2 in + 1 arch stake x 24 in (11 3/8 in offcut); Bed B 1: 3 corner posts x 14 1/2 in + 2 mid-span posts x 24 in (4 in offcut), 1: trellis post, whole, 1: 1 arch sill x 60 1/2 in + 1 arch stake x 24 in (11 3/8 in offcut); Bed C 1: 1 corner post x 14 1/2 in + 3 mid-span posts x 24 in (9 1/8 in offcut); Bed D 1: 1 corner post x 14 1/2 in + 3 mid-span posts x 24 in (9 1/8 in offcut) |
| Hardware | #9 x 3 in exterior structural screws, star drive | 136 | ea | Coated for treated lumber; stainless 305/316 for cedar or redwood | Derived from model | Side boards into the corner post edges (64) + corner ties into end grain (64) + arch stakes into the sill ends (8); buy one 5 lb box (about 350); 1 lb boxes hold only about 70 |
| Hardware | #9 x 2.5 in exterior structural screws, star drive | 168 | ea | Same finish as the 3 in screws | Derived from model | Side boards into the mid-span post faces (64) + end boards into the corner post faces (64) + side boards into the joint post faces (40); buy one 5 lb box (about 450); 1 lb boxes hold only about 90 |
| Hardware | #9 x 1.25 in exterior screws, star drive | 20 | ea | Same finish; short enough to stay inside a 1.5 in post, stake or sill | Derived from model | Hog-wire panel to the trellis posts (2 each), arch stakes (2 each) and sills (4 each), each through a fender washer; a 1 lb box holds about 180 |
| Hardware | 1/4 x 1 in galvanized fender washers | 20 | ea | Under the panel screws | Derived from model | One per panel screw; the washer beside a wire traps it against the wood |
| Pavers | Concrete paver 12 x 12 x 1.5 in | 74 | ea | about 18 lb each, 1,328 lb total | Model (Small Pavers) | 38 Walkway along the top edge (2 rows, 15 in pitch); 11 Path between Bed D (16 ft) and Bed C (14 ft), 18 in pitch; 10 Path between Bed C (14 ft) and Bed B (12 ft), 18 in pitch; 8 Path between Bed B (12 ft) and Bed A (10 ft), 18 in pitch; 7 Path west of Bed A (10 ft), 18 in pitch |
| Pavers | Paver leveling base (crushed stone or all-purpose sand) | 25 | 0.5 cu ft bag | 2 in under each paver, 12.3 cu ft | Estimate | Not in model |
| Arches | Hog-wire / cattle panel, 16 ft long, 4 x 4 in mesh | 1 | ea | 4-gauge galvanized, 48 to 60 in wide | Model (Hogwire Arches) | Bent over 75 in between the Bed A and Bed B centrelines, feet on 2x4 sills on the ground: 37 in straight legs, crown 76 in above grade, held near the top by the two 8 ft inside corner posts, no T-posts. Model wires are 60 in wide at 4 in pitch. Arch BC is parked (hidden) in the model |
| Drip | 3/4 x 3/4 x 1/2 in PVC reducer tee, slip | 4 | ea | Schedule 40 | Model (Drip Irrigation) | One per bed on the 3/4 in main, 8 in beyond the far end board and 6 1/8 in deep |
| Drip | 1/2 in PVC pipe, schedule 40, 10 ft | 1 | ea | 115 in needed in 20 pieces | Model (Drip Irrigation) | Per bed 6 1/4 + 9 + 6 + 3 1/2 + 4 in; 2 5/8 in spare after the kerfs |
| Drip | 1/2 in PVC 90 degree elbow, slip | 12 | ea | Schedule 40 | Model (Drip Irrigation) | 3 per bed: at the bottom of the riser and on each side of the wall |
| Drip | 1/2 in PVC ball valve, slip x slip | 4 | ea | Lever handle | Model (Drip Irrigation) | 3 7/8 in above grade on the outside of the far end wall, between the two clamps |
| Drip | 1/2 in FPT x 4-port 1/4 in barb drip manifold head | 4 | ea |  | Model (Drip Irrigation) | Top at 16 3/8 in, 1 7/8 in above the wall top, inside the bed |
| Drip | 1/2 in PVC male adapter, slip x MPT | 4 | ea | Threads the head onto the riser | Derived from model | Not modelled; use a female adapter instead if your head is male |
| Drip | 1/2 in stand-off pipe clamp | 8 | ea | Galvanized or UV-stable plastic | Model (Drip Irrigation) | Two per bed at 1 1/2 and 8 3/4 in, each on one board |
| Drip | #8 x 1 in exterior pan-head screws | 16 | ea | Same finish as the bed screws | Derived from model | Two per clamp |
| Drip | PVC primer and cement, small cans | 1 | set |  | Estimate | 40 slip joints in all |
| Drip | PTFE thread tape | 1 | roll |  | Estimate | Head onto the male adapter |
| Drip (reference) | 3/4 in sprinkler main, existing | 25.9 | ft | 6 elbows if routed as drawn | Model (3/4 in main (existing)) | Stair-step 8 in beyond the far end boards, 6 1/8 in deep; drawn only to place the tees |
| Soil | Raised-bed soil mix | 7.45 | cu yd | 201 cu ft at 14.5 in deep | Derived from model | 2x10 alternative: 9.53 cu yd |
| Optional | Hardware cloth 1/2 in, 48 in wide (under beds) | 56 | lin ft | Gopher / vole barrier | Estimate | Not in model; one strip per bed, trimmed to 21 in wide for Bed D |
| Hoops | Low-tunnel hoop, 1 in tube, 40 in wide x 57 in tall | 6 | ea | 136 in of tube each (11.4 ft), 68 ft in all | Model (Garden Hoops) | 6 over Bed C (14 ft) at 31 in pitch, the first and last 5 in inside the end boards; 36 in legs pushed through the 14.5 in of soil to grade, 21.5 in of straight leg above the soil. 11.4 ft each, so 10 ft sticks need a coupling in one leg; 12 ft stock makes one-piece hoops |
| Optional (hidden in model) | Single-tube garden arch, 1 in tube, 7 ft wide x 7 ft tall | 1 | ea | 216 in of tube (18 ft) | Model (Garden Arch, hidden) | Superseded by Arch AB at the same spot |

Lumber totals: 31 boards of 2x8 (276 linear ft) plus 12 sticks of 2x4, about $591.84 before tax at these prices (2x10 walls: $812.94); prices are single-stick prices for #1 ground-contact pressure-treated pine at a big-box home center, checked 2026-11-08. Model lumber weight about 847 lb (2x10: about 1,081 lb). Pavers weigh about 1,328 lb in total, so plan for delivery.

## Screw plan

Every joint is a 2x8 board face-screwed to a 2x4 post, 2 screws per board per post, 1.75 in and 5.5 in up from the bottom edge of each board. Corner posts stand edge-on: 1.5 in edge against the side board, 3.5 in face against the end board. Mid-span posts lie flat, 3.5 in face against the side board, and run 24 in long so 9.5 in is driven into the ground. Where two side boards meet over a 2x8 joint post (beds C and D), each board end gets its own pair, 1.75 in from the end. Use #9 star-drive exterior structural screws (coated for treated lumber; stainless 305 or 316 for cedar or redwood, which stain and corrode plain coated screws).

| Joint | Screw | Why that length and where | Count |
|---|---|---|---|
| Side board into a corner post edge | #9 x 3 in | 1.5 in through the board, 1.5 in into the post's 3.5 in depth. The target is only 1.5 in wide: mark the post centerline on the outside face first, 2.25 in from the board end. | 2 per board per post |
| Side board into a mid-span post face | #9 x 2.5 in | 1.5 in through the board, 1 in into the post's 1.5 in thickness; a 3 in screw would poke out the back. The face is 3.5 in wide, so stagger the pair 0.75 in either side of the post centerline: the lower screw to one side, the upper to the other. Drive the posts first, then screw the boards to them. | 2 per board per post |
| End board into a corner post face | #9 x 2.5 in | Same joint as the mid-span posts: 1 in into the post's 1.5 in thickness. Center them 3.25 in from the board end. | 2 per board per post |
| Side board end into a joint post face | #9 x 2.5 in | The joint post is a 2x8 offcut lying flat, 7 1/4 in wide and 1.5 in thick, so the screws are the mid-span length. Where two boards meet over it, each board end gets two screws 1.75 in from the end at the usual heights (pre-drill: they are within 2 in of the end); a course that runs past the post gets the mid-span pair instead. | 4 per course where boards meet, 2 where one runs past |
| Corner tie: through the side board into the end board's end grain | #9 x 3 in | Holds the corner closed. Pre-drill 1/8 in; place at 2.75 in and 4.5 in up, 0.75 in from the board end, staggered off the post screws. | 2 per corner per course |
| Hog-wire panel to the trellis posts, arch stakes and sills | #9 x 1.25 in + 1 in fender washer | The washer beside a wire traps it against the wood, and 1.25 in stays inside a 1.5 in post, stake or sill so no tip pokes out the back. At the post top, one screw each side of the edge wire where it crosses the face; on each stake, beside two cross wires; along the sill, beside the bottom wire. | 2 per post, 2 per stake, 4 per sill |
| Arch stake into the sill's end grain | #9 x 3 in | 1.5 in through the stake, 1.5 in into the sill end. Pre-drill 1/8 in and drive from the stake's back before the end board goes on, 0.75 in up, 1 in either side of center. | 2 per stake |

| Bed | Posts per side | 3 in: corner posts | 3 in: corner ties | 3 in: arch stakes | 2.5 in: mid-span posts | 2.5 in: joint posts | 2.5 in: end boards | 1.25 in: arch panel | Total |
|---|---|---|---|---|---|---|---|---|---|
| A | 4 | 16 | 16 | 4 | 16 | 0 | 16 | 10 | 78 |
| B | 4 | 16 | 16 | 4 | 16 | 0 | 16 | 10 | 78 |
| C | 6 | 16 | 16 | 0 | 16 | 24 | 16 | 0 | 88 |
| D | 5 | 16 | 16 | 0 | 16 | 16 | 16 | 0 | 80 |
| **Total** | | **64** | **64** | **8** | **64** | **40** | **64** | **20** | **324** |

Buy: 3 in, 136 needed, one 5 lb box (about 350); 1 lb boxes hold only about 70; 2.5 in, 168 needed, one 5 lb box (about 450); 1 lb boxes hold only about 90; 1.25 in, 20 needed, one 1 lb box. Pre-drill the corner ties and any screw within 2 in of a board end (1/8 in bit for cedar, 3/32 in for SPF). Set the mid-span posts and the joint posts first: chamfer the bottom of each to a point, drive it 9 1/2 in at the marked centerline with its wide face toward the wall, stop when its top is flush with the top of the wall, then screw the side boards to it from outside. Corner posts stay 14.5 in and sit on grade, except the 2 inside corner posts at the near end of beds A and B under the arch, which are uncut 8 ft trellis posts set 20 in deep (see the arch).

## Cut list

Stock lengths and prices: single-stick prices for #1 ground-contact pressure-treated pine at a big-box home center, checked 2026-11-08. 2x8 and 2x10 come in 8, 10, 12, 16 ft (no 14 ft, so beds C and D use two boards per course from 8 ft stock, joined over 2x8 joint posts); 2x4 comes in 2, 4, 6, 8, 10, 12, 16 ft. Each bed's plan is the cheapest set of sticks for that bed on its own, so the four plans add up to the shopping list. Side boards are whole sticks; the 72 in side pieces are cut from 8 ft boards and the offcut becomes a 2x8 joint post, cut up to 1 in short so both clear the kerf. End boards may be cut up to 1/4 in short so two 48 in pieces clear the saw kerf on one 8 ft board; corner posts may run up to 1/2 in short of the wall height and mid-span posts, joint posts and arch stakes up to 1 in short, which only takes them a little less deep into the ground, when that lets one more piece fit a stick.

| Buy | Qty | Each | Total | For |
|---|---|---|---|---|
| 2x8 x 8 ft | **22** | $14.78 | $325.16 | Bed A 2: 2 end boards x 47 15/16 in (no offcut); Bed B 2: 2 end boards x 47 15/16 in (no offcut); Bed C 4: side board, whole, 4: 1 side board x 72 in + 1 joint post x 23 7/8 in (no offcut), 2: 2 end boards x 47 15/16 in (no offcut); Bed D 8: side board, whole |
| 2x8 x 10 ft | **4** | $18.88 | $75.52 | Bed A 4: side board, whole |
| 2x8 x 12 ft | **5** | $22.68 | $113.40 | Bed B 4: side board, whole; Bed D 1: 4 end boards x 21 in + 2 joint posts x 24 in (11 3/8 in offcut) |
| 2x4 x 6 ft | **4** | $5.28 | $21.12 | Bed A 1: 2 mid-span posts x 23 7/8 in + 1 arch stake x 23 7/8 in (no offcut); Bed B 1: 2 mid-span posts x 23 7/8 in + 1 arch stake x 23 7/8 in (no offcut); Bed C 1: 3 corner posts x 14 1/2 in + 1 mid-span post x 24 in (4 1/8 in offcut); Bed D 1: 3 corner posts x 14 1/2 in + 1 mid-span post x 24 in (4 1/8 in offcut) |
| 2x4 x 8 ft | **8** | $7.08 | $56.64 | Bed A 1: 3 corner posts x 14 1/2 in + 2 mid-span posts x 24 in (4 in offcut), 1: trellis post, whole, 1: 1 arch sill x 60 1/2 in + 1 arch stake x 24 in (11 3/8 in offcut); Bed B 1: 3 corner posts x 14 1/2 in + 2 mid-span posts x 24 in (4 in offcut), 1: trellis post, whole, 1: 1 arch sill x 60 1/2 in + 1 arch stake x 24 in (11 3/8 in offcut); Bed C 1: 1 corner post x 14 1/2 in + 3 mid-span posts x 24 in (9 1/8 in offcut); Bed D 1: 1 corner post x 14 1/2 in + 3 mid-span posts x 24 in (9 1/8 in offcut) |
| **Total** | **43** | | **$591.84** | 2x10 walls: $812.94 |

Cutting all four beds from one pile instead: 41 sticks, $586.98, saving $4.86 over the per-bed plans (offcuts from one bed become pieces for another).

| Buy | Qty | Each one is cut into | Offcut |
|---|---|---|---|
| 2x8 x 12 ft | 4 | side board, whole | 0 in |
| 2x8 x 12 ft | 2 | 1 side board x 120 in + 1 end board x 21 in | 2 7/8 in |
| 2x8 x 10 ft | 2 | side board, whole | 0 in |
| 2x8 x 8 ft | 12 | side board, whole | 0 in |
| 2x8 x 8 ft | 4 | 1 side board x 72 in + 1 joint post x 23 7/8 in | 0 in |
| 2x8 x 8 ft | 5 | 2 end boards x 47 15/16 in | 0 in |
| 2x8 x 8 ft | 2 | 1 end board x 48 in + 1 joint post x 24 in + 1 end board x 21 in | 2 3/4 in |
| 2x4 x 12 ft | 1 | 2 corner posts x 14 in + 5 mid or stake posts x 23 in | 1/4 in |
| 2x4 x 12 ft | 2 | 1 corner post x 14 in + 3 mid or stake posts x 23 in + 1 arch sill x 60 1/2 in | 0 in |
| 2x4 x 8 ft | 2 | trellis post, whole | 0 in |
| 2x4 x 6 ft | 2 | 5 corner posts x 14 1/4 in | 1/4 in |
| 2x4 x 6 ft | 3 | 3 mid or stake posts x 23 7/8 in | 1/8 in |

## Materials by bed

Everything that goes to one bed, so each bed can be checked on its own. The lumber lines are the sticks to buy, in store lengths with store prices, and the cut lines beneath them say what every stick becomes; fasteners come from the screw plan. The hog-wire panel spans beds A and B and is listed under both (buy one); the 1/2 in drip pipe for every bed is cut from the sticks on the shopping list. The same lists are in BOM-by-bed.csv, and bom.html has tick boxes that are remembered in the browser.

### Bed A: 10 ft x 51 in, 14.5 in tall

Inside 48 x 117 in. 27 lines. Lumber: 10 sticks, $131.60 (2x10 walls: $176.20).

| Buy | Qty | Each one is cut into | Offcut |
|---|---|---|---|
| 2x8 x 10 ft | 4 | side board, whole | 0 in |
| 2x8 x 8 ft | 2 | 2 end boards x 47 15/16 in | 0 in |
| 2x4 x 8 ft | 1 | 3 corner posts x 14 1/2 in + 2 mid-span posts x 24 in | 4 in |
| 2x4 x 8 ft | 1 | trellis post, whole | 0 in |
| 2x4 x 8 ft | 1 | 1 arch sill x 60 1/2 in + 1 arch stake x 24 in | 11 3/8 in |
| 2x4 x 6 ft | 1 | 2 mid-span posts x 23 7/8 in + 1 arch stake x 23 7/8 in | 1/8 in |

Other ways to buy it: 2x8: 8 ft boards for the ends, 10 ft for the sides: 6 sticks, $105.08, 0 in offcut (chosen); 10 ft boards only: 6 sticks, $113.28, 47 3/4 in offcut (+$8.20); 12 ft boards only: 6 sticks, $136.08, 192 1/8 in offcut (+$31.00); 16 ft boards only: 4 sticks, $122.72, 95 1/2 in offcut (+$17.64). 2x4: 6 ft sticks plus the uncut 8 ft trellis post: 4 sticks, $26.52, 15 1/2 in offcut (chosen); 8 ft sticks: 4 sticks, $28.32, 39 1/8 in offcut (+$1.80); 10 ft sticks: 3 sticks, $26.94, 15 1/8 in offcut (+$0.42); 12 ft sticks: 3 sticks, $32.64, 90 1/2 in offcut (+$6.12); 16 ft sticks: 2 sticks, $33.56, 38 7/8 in offcut (+$7.04).

**Lumber**

- [ ] **2 x** 2x8 x 8 ft. $14.78 each, $29.56. Each: 2 end boards x 47 15/16 in (no offcut). *Store price*
- [ ] **4 x** 2x8 x 10 ft. $18.88 each, $75.52. Side board, whole. *Store price*
- [ ] **1 x** 2x4 x 6 ft. $5.28 each, $5.28. 2 mid-span posts x 23 7/8 in + 1 arch stake x 23 7/8 in (no offcut). *Store price*
- [ ] **3 x** 2x4 x 8 ft. $7.08 each, $21.24. One each: 3 corner posts x 14 1/2 in + 2 mid-span posts x 24 in (4 in offcut); trellis post, whole; 1 arch sill x 60 1/2 in + 1 arch stake x 24 in (11 3/8 in offcut). *Store price*

**Cuts**

- [ ] **4 x** Side board. 2x8 x 10 ft, whole board. 2 per course, outside. *Model (Bed Lumber)*
- [ ] **4 x** End board. 2x8, cut 47 15/16 in. 4 from 2 x 8 ft, between the side boards; a hair under 48 so two clear the kerf. *Model (Bed Lumber)*
- [ ] **3 x** 2x4 corner post. 2x4, cut 14 1/2 in (18.5 in with 2x10 walls). Inside each corner, edge-on to the side boards, standing on grade; 3 from 1 x 8 ft. *Model (Bed Lumber)*
- [ ] **4 x** 2x4 mid-span post. 2x4, cut 23 7/8 or 24 in. Flat against the side boards, centred 41, 79 in from the near end, about 9 1/2 in in the ground; 2 from 1 x 8 ft, 2 from 1 x 6 ft. *Model (Bed Lumber)*
- [ ] **1 x** 2x4 trellis post. 2x4 x 8 ft, uncut. East corner at the near end; in place of a corner post, set 20 in deep, 76 in above grade; holds the arch near its crown. *Model (Bed Lumber)*
- [ ] **1 x** 2x4 arch sill. 2x4, cut 60 1/2 in. Flat on grade along the bed centreline, 3 to 63.5 in from the near end; the arch foot sits on it; 1 from 1 x 8 ft. *Model (Bed Lumber)*
- [ ] **2 x** 2x4 arch stake. 2x4, cut 23 7/8 or 24 in. One at each end of the sill, 10.5 in in the ground, 13.5 in above grade; 1 from 1 x 8 ft, 1 from 1 x 6 ft. *Model (Bed Lumber)*

**Fasteners**

- [ ] **36 x** #9 x 3 in exterior structural screws. Star drive; coated for treated lumber, stainless 305/316 for cedar or redwood. 16 side boards into the corner post edges + 16 corner ties into end grain + 4 arch stakes into the sill ends. *Derived from model*
- [ ] **32 x** #9 x 2.5 in exterior structural screws. Same finish as the 3 in screws. 16 side boards into the mid-span post faces + 16 end boards into the corner post faces. *Derived from model*
- [ ] **10 x** #9 x 1.25 in exterior screws. Same finish, each through a fender washer. Hog-wire panel to the trellis post (2), the stakes (2 each) and the sill (4). *Derived from model*
- [ ] **10 x** 1/4 x 1 in galvanized fender washers. One under each panel screw. The washer beside a wire traps it against the wood. *Derived from model*

**Trellis arch**

- [ ] **1 x** Hog-wire / cattle panel, 16 ft, 4 x 4 in mesh (Arch AB). 4-gauge galvanized, 48 to 60 in wide. One panel bent from the centre of this bed to the centre of Bed B; it is listed under both beds, buy one. 37 in straight legs, crown 76 in above grade. *Model (Hogwire Arches)*

**Drip riser**

- [ ] **1 x** 3/4 x 3/4 x 1/2 in PVC reducer tee, slip. Schedule 40. On the 3/4 in main, 8 in beyond the far end board, 6 1/8 in deep. *Model (Drip Irrigation)*
- [ ] **5 pieces** 1/2 in PVC pipe, schedule 40. Cut 6 1/4, 9, 6, 3 1/2, 4 in (28 3/4 in in all). Ground run, lower riser, upper riser, through the wall, head; cut from the 1 x 10 ft stick on the shopping list, shared by all 4 beds. *Model (Drip Irrigation)*
- [ ] **3 x** 1/2 in PVC 90 degree elbow, slip. Schedule 40. At the bottom of the riser and on each side of the wall. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in PVC ball valve, slip x slip. Lever handle. 3 7/8 in above grade on the outside of the far end wall, lever west along the wall. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in FPT x 4-port 1/4 in barb drip manifold head. Inside the bed, top 1 7/8 in above the wall top. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in PVC male adapter, slip x MPT. Threads the head onto the riser. Not modelled; a female adapter instead if your head is male. *Derived from model*
- [ ] **2 x** 1/2 in stand-off pipe clamp. Galvanized or UV-stable plastic. At 1 1/2 and 8 3/4 in above grade, one on each board. *Model (Drip Irrigation)*
- [ ] **4 x** #8 x 1 in exterior pan-head screws. Same finish as the bed screws. Two per clamp. *Derived from model*
- [ ] **1 x** 1 in hole through the top far end board. Spade bit, centred 10 7/8 in above grade and 9 in from the bed's west outside face. The through-wall pipe passes it; bore it in place or before the top board goes on. *Model (Drip Irrigation)*

**Soil**

- [ ] **46.5 cu ft** Raised-bed soil mix. 1.72 cu yd at 14.5 in deep. 2x10 walls: 59.5 cu ft (2.20 cu yd). *Derived from model*

**Optional**

- [ ] **11 lin ft** Hardware cloth 1/2 in, 48 in wide (under the bed). Gopher / vole barrier. Not in model; one strip the length of the bed plus a foot. *Estimate*

### Bed B: 12 ft x 51 in, 14.5 in tall

Inside 48 x 141 in. 27 lines. Lumber: 10 sticks, $146.80 (2x10 walls: $199.80).

| Buy | Qty | Each one is cut into | Offcut |
|---|---|---|---|
| 2x8 x 12 ft | 4 | side board, whole | 0 in |
| 2x8 x 8 ft | 2 | 2 end boards x 47 15/16 in | 0 in |
| 2x4 x 8 ft | 1 | 3 corner posts x 14 1/2 in + 2 mid-span posts x 24 in | 4 in |
| 2x4 x 8 ft | 1 | trellis post, whole | 0 in |
| 2x4 x 8 ft | 1 | 1 arch sill x 60 1/2 in + 1 arch stake x 24 in | 11 3/8 in |
| 2x4 x 6 ft | 1 | 2 mid-span posts x 23 7/8 in + 1 arch stake x 23 7/8 in | 1/8 in |

Other ways to buy it: 2x8: 8 ft boards for the ends, 12 ft for the sides: 6 sticks, $120.28, 0 in offcut (chosen); 10 ft boards for the ends, 12 ft for the sides: 6 sticks, $128.48, 47 3/4 in offcut (+$8.20); 12 ft boards only: 6 sticks, $136.08, 96 1/8 in offcut (+$15.80); 16 ft boards only: 4 sticks, $122.72, 0 in offcut (+$2.44). 2x4: 6 ft sticks plus the uncut 8 ft trellis post: 4 sticks, $26.52, 15 1/2 in offcut (chosen); 8 ft sticks: 4 sticks, $28.32, 39 1/8 in offcut (+$1.80); 10 ft sticks: 3 sticks, $26.94, 15 1/8 in offcut (+$0.42); 12 ft sticks: 3 sticks, $32.64, 90 1/2 in offcut (+$6.12); 16 ft sticks: 2 sticks, $33.56, 38 7/8 in offcut (+$7.04).

**Lumber**

- [ ] **2 x** 2x8 x 8 ft. $14.78 each, $29.56. Each: 2 end boards x 47 15/16 in (no offcut). *Store price*
- [ ] **4 x** 2x8 x 12 ft. $22.68 each, $90.72. Side board, whole. *Store price*
- [ ] **1 x** 2x4 x 6 ft. $5.28 each, $5.28. 2 mid-span posts x 23 7/8 in + 1 arch stake x 23 7/8 in (no offcut). *Store price*
- [ ] **3 x** 2x4 x 8 ft. $7.08 each, $21.24. One each: 3 corner posts x 14 1/2 in + 2 mid-span posts x 24 in (4 in offcut); trellis post, whole; 1 arch sill x 60 1/2 in + 1 arch stake x 24 in (11 3/8 in offcut). *Store price*

**Cuts**

- [ ] **4 x** Side board. 2x8 x 12 ft, whole board. 2 per course, outside. *Model (Bed Lumber)*
- [ ] **4 x** End board. 2x8, cut 47 15/16 in. 4 from 2 x 8 ft, between the side boards; a hair under 48 so two clear the kerf. *Model (Bed Lumber)*
- [ ] **3 x** 2x4 corner post. 2x4, cut 14 1/2 in (18.5 in with 2x10 walls). Inside each corner, edge-on to the side boards, standing on grade; 3 from 1 x 8 ft. *Model (Bed Lumber)*
- [ ] **4 x** 2x4 mid-span post. 2x4, cut 23 7/8 or 24 in. Flat against the side boards, centred 49, 95 in from the near end, about 9 1/2 in in the ground; 2 from 1 x 8 ft, 2 from 1 x 6 ft. *Model (Bed Lumber)*
- [ ] **1 x** 2x4 trellis post. 2x4 x 8 ft, uncut. West corner at the near end; in place of a corner post, set 20 in deep, 76 in above grade; holds the arch near its crown. *Model (Bed Lumber)*
- [ ] **1 x** 2x4 arch sill. 2x4, cut 60 1/2 in. Flat on grade along the bed centreline, 3 to 63.5 in from the near end; the arch foot sits on it; 1 from 1 x 8 ft. *Model (Bed Lumber)*
- [ ] **2 x** 2x4 arch stake. 2x4, cut 23 7/8 or 24 in. One at each end of the sill, 10.5 in in the ground, 13.5 in above grade; 1 from 1 x 8 ft, 1 from 1 x 6 ft. *Model (Bed Lumber)*

**Fasteners**

- [ ] **36 x** #9 x 3 in exterior structural screws. Star drive; coated for treated lumber, stainless 305/316 for cedar or redwood. 16 side boards into the corner post edges + 16 corner ties into end grain + 4 arch stakes into the sill ends. *Derived from model*
- [ ] **32 x** #9 x 2.5 in exterior structural screws. Same finish as the 3 in screws. 16 side boards into the mid-span post faces + 16 end boards into the corner post faces. *Derived from model*
- [ ] **10 x** #9 x 1.25 in exterior screws. Same finish, each through a fender washer. Hog-wire panel to the trellis post (2), the stakes (2 each) and the sill (4). *Derived from model*
- [ ] **10 x** 1/4 x 1 in galvanized fender washers. One under each panel screw. The washer beside a wire traps it against the wood. *Derived from model*

**Trellis arch**

- [ ] **1 x** Hog-wire / cattle panel, 16 ft, 4 x 4 in mesh (Arch AB). 4-gauge galvanized, 48 to 60 in wide. One panel bent from the centre of this bed to the centre of Bed A; it is listed under both beds, buy one. 37 in straight legs, crown 76 in above grade. *Model (Hogwire Arches)*

**Drip riser**

- [ ] **1 x** 3/4 x 3/4 x 1/2 in PVC reducer tee, slip. Schedule 40. On the 3/4 in main, 8 in beyond the far end board, 6 1/8 in deep. *Model (Drip Irrigation)*
- [ ] **5 pieces** 1/2 in PVC pipe, schedule 40. Cut 6 1/4, 9, 6, 3 1/2, 4 in (28 3/4 in in all). Ground run, lower riser, upper riser, through the wall, head; cut from the 1 x 10 ft stick on the shopping list, shared by all 4 beds. *Model (Drip Irrigation)*
- [ ] **3 x** 1/2 in PVC 90 degree elbow, slip. Schedule 40. At the bottom of the riser and on each side of the wall. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in PVC ball valve, slip x slip. Lever handle. 3 7/8 in above grade on the outside of the far end wall, lever west along the wall. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in FPT x 4-port 1/4 in barb drip manifold head. Inside the bed, top 1 7/8 in above the wall top. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in PVC male adapter, slip x MPT. Threads the head onto the riser. Not modelled; a female adapter instead if your head is male. *Derived from model*
- [ ] **2 x** 1/2 in stand-off pipe clamp. Galvanized or UV-stable plastic. At 1 1/2 and 8 3/4 in above grade, one on each board. *Model (Drip Irrigation)*
- [ ] **4 x** #8 x 1 in exterior pan-head screws. Same finish as the bed screws. Two per clamp. *Derived from model*
- [ ] **1 x** 1 in hole through the top far end board. Spade bit, centred 10 7/8 in above grade and 9 in from the bed's west outside face. The through-wall pipe passes it; bore it in place or before the top board goes on. *Model (Drip Irrigation)*

**Soil**

- [ ] **56.2 cu ft** Raised-bed soil mix. 2.08 cu yd at 14.5 in deep. 2x10 walls: 71.8 cu ft (2.66 cu yd). *Derived from model*

**Optional**

- [ ] **13 lin ft** Hardware cloth 1/2 in, 48 in wide (under the bed). Gopher / vole barrier. Not in model; one strip the length of the bed plus a foot. *Estimate*

### Bed C: 14 ft x 51 in, 14.5 in tall

Inside 48 x 165 in. 23 lines. Lumber: 12 sticks, $160.16 (2x10 walls: $223.16).

| Buy | Qty | Each one is cut into | Offcut |
|---|---|---|---|
| 2x8 x 8 ft | 4 | side board, whole | 0 in |
| 2x8 x 8 ft | 4 | 1 side board x 72 in + 1 joint post x 23 7/8 in | 0 in |
| 2x8 x 8 ft | 2 | 2 end boards x 47 15/16 in | 0 in |
| 2x4 x 8 ft | 1 | 1 corner post x 14 1/2 in + 3 mid-span posts x 24 in | 9 1/8 in |
| 2x4 x 6 ft | 1 | 3 corner posts x 14 1/2 in + 1 mid-span post x 24 in | 4 1/8 in |

Other ways to buy it: 2x8: 8 ft boards only: 10 sticks, $147.80, 0 in offcut (chosen); 10 ft boards only: 8 sticks, $151.04, 0 in offcut (+$3.24); 12 ft boards only: 8 sticks, $181.44, 191 1/2 in offcut (+$33.64); 16 ft boards only: 5 sticks, $153.40, 0 in offcut (+$5.60). 2x4: 6 ft sticks: 3 sticks, $15.84, 61 3/4 in offcut (+$3.48); 8 ft sticks: 2 sticks, $14.16, 37 1/4 in offcut (+$1.80); 10 ft sticks: 2 sticks, $17.96, 85 1/4 in offcut (+$5.60); 12 ft sticks: 2 sticks, $21.76, 133 1/4 in offcut (+$9.40); 16 ft sticks: 1 stick, $16.78, 37 1/8 in offcut (+$4.42).

**Lumber**

- [ ] **10 x** 2x8 x 8 ft. $14.78 each, $147.80. 4 x side board, whole; 4 x 1 side board x 72 in + 1 joint post x 23 7/8 in (no offcut); 2 x 2 end boards x 47 15/16 in (no offcut). *Store price*
- [ ] **1 x** 2x4 x 6 ft. $5.28 each, $5.28. 3 corner posts x 14 1/2 in + 1 mid-span post x 24 in (4 1/8 in offcut). *Store price*
- [ ] **1 x** 2x4 x 8 ft. $7.08 each, $7.08. 1 corner post x 14 1/2 in + 3 mid-span posts x 24 in (9 1/8 in offcut). *Store price*

**Cuts**

- [ ] **4 x** Side board, 96 in. 2x8 x 8 ft, whole board. Outside, both walls: course 1 near end, course 2 far end; the seams meet over the joint posts. *Model (Bed Lumber)*
- [ ] **4 x** Side board, 72 in. 2x8, cut 72 in from a 8 ft board; the 23 7/8 in offcut is a joint post. Outside, both walls: course 1 far end, course 2 near end; the seams meet over the joint posts. *Model (Bed Lumber)*
- [ ] **4 x** End board. 2x8, cut 47 15/16 in. 4 from 2 x 8 ft, between the side boards; a hair under 48 so two clear the kerf. *Model (Bed Lumber)*
- [ ] **4 x** 2x4 corner post. 2x4, cut 14 1/2 in (18.5 in with 2x10 walls). Inside each corner, edge-on to the side boards, standing on grade; 1 from 1 x 8 ft, 3 from 1 x 6 ft. *Model (Bed Lumber)*
- [ ] **4 x** 2x4 mid-span post. 2x4, cut 24 in. Flat against the side boards, centred 38, 130 in from the near end, about 9 1/2 in in the ground; 3 from 1 x 8 ft, 1 from 1 x 6 ft. *Model (Bed Lumber)*
- [ ] **4 x** 2x8 joint post. 2x8, cut 23 7/8 in, lying flat. Inside the wall behind each seam, 7 1/4 in face against the boards, centred 72, 96 in from the near end, about 9 1/2 in in the ground; 4 from 4 x 8 ft. *Model (Bed Lumber)*

**Fasteners**

- [ ] **32 x** #9 x 3 in exterior structural screws. Star drive; coated for treated lumber, stainless 305/316 for cedar or redwood. 16 side boards into the corner post edges + 16 corner ties into end grain. *Derived from model*
- [ ] **56 x** #9 x 2.5 in exterior structural screws. Same finish as the 3 in screws. 16 side boards into the mid-span post faces + 16 end boards into the corner post faces + 24 side boards into the joint post faces. *Derived from model*

**Hoops**

- [ ] **6 x** Low-tunnel hoop, 1 in tube, 40 in wide x 57 in tall. 136 in of tube each (11.4 ft), 68 ft in all. 31 in pitch, the first and last 5 in inside the end boards; 36 in legs pushed through the soil to grade. *Model (Garden Hoops)*

**Drip riser**

- [ ] **1 x** 3/4 x 3/4 x 1/2 in PVC reducer tee, slip. Schedule 40. On the 3/4 in main, 8 in beyond the far end board, 6 1/8 in deep. *Model (Drip Irrigation)*
- [ ] **5 pieces** 1/2 in PVC pipe, schedule 40. Cut 6 1/4, 9, 6, 3 1/2, 4 in (28 3/4 in in all). Ground run, lower riser, upper riser, through the wall, head; cut from the 1 x 10 ft stick on the shopping list, shared by all 4 beds. *Model (Drip Irrigation)*
- [ ] **3 x** 1/2 in PVC 90 degree elbow, slip. Schedule 40. At the bottom of the riser and on each side of the wall. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in PVC ball valve, slip x slip. Lever handle. 3 7/8 in above grade on the outside of the far end wall, lever west along the wall. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in FPT x 4-port 1/4 in barb drip manifold head. Inside the bed, top 1 7/8 in above the wall top. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in PVC male adapter, slip x MPT. Threads the head onto the riser. Not modelled; a female adapter instead if your head is male. *Derived from model*
- [ ] **2 x** 1/2 in stand-off pipe clamp. Galvanized or UV-stable plastic. At 1 1/2 and 8 3/4 in above grade, one on each board. *Model (Drip Irrigation)*
- [ ] **4 x** #8 x 1 in exterior pan-head screws. Same finish as the bed screws. Two per clamp. *Derived from model*
- [ ] **1 x** 1 in hole through the top far end board. Spade bit, centred 10 7/8 in above grade and 9 in from the bed's west outside face. The through-wall pipe passes it; bore it in place or before the top board goes on. *Model (Drip Irrigation)*

**Soil**

- [ ] **65.7 cu ft** Raised-bed soil mix. 2.43 cu yd at 14.5 in deep. 2x10 walls: 84.1 cu ft (3.11 cu yd). *Derived from model*

**Optional**

- [ ] **15 lin ft** Hardware cloth 1/2 in, 48 in wide (under the bed). Gopher / vole barrier. Not in model; one strip the length of the bed plus a foot. *Estimate*

### Bed D: 16 ft x 24 in, 14.5 in tall

Inside 21 x 189 in. 22 lines. Lumber: 11 sticks, $153.28 (2x10 walls: $213.78).

| Buy | Qty | Each one is cut into | Offcut |
|---|---|---|---|
| 2x8 x 12 ft | 1 | 4 end boards x 21 in + 2 joint posts x 24 in | 11 3/8 in |
| 2x8 x 8 ft | 8 | side board, whole | 0 in |
| 2x4 x 8 ft | 1 | 1 corner post x 14 1/2 in + 3 mid-span posts x 24 in | 9 1/8 in |
| 2x4 x 6 ft | 1 | 3 corner posts x 14 1/2 in + 1 mid-span post x 24 in | 4 1/8 in |

Other ways to buy it: 2x8: 8 ft boards only: 10 sticks, $147.80, 59 1/2 in offcut (+$6.88); 10 ft boards only: 8 sticks, $151.04, 59 1/2 in offcut (+$10.12); 12 ft boards only: 8 sticks, $181.44, 251 1/4 in offcut (+$40.52); 16 ft boards only: 8 sticks, $245.44, 635 1/4 in offcut (+$104.52). 2x4: 6 ft sticks: 3 sticks, $15.84, 61 3/4 in offcut (+$3.48); 8 ft sticks: 2 sticks, $14.16, 37 1/4 in offcut (+$1.80); 10 ft sticks: 2 sticks, $17.96, 85 1/4 in offcut (+$5.60); 12 ft sticks: 2 sticks, $21.76, 133 1/4 in offcut (+$9.40); 16 ft sticks: 1 stick, $16.78, 37 1/8 in offcut (+$4.42).

**Lumber**

- [ ] **8 x** 2x8 x 8 ft. $14.78 each, $118.24. Side board, whole. *Store price*
- [ ] **1 x** 2x8 x 12 ft. $22.68 each, $22.68. 4 end boards x 21 in + 2 joint posts x 24 in (11 3/8 in offcut). *Store price*
- [ ] **1 x** 2x4 x 6 ft. $5.28 each, $5.28. 3 corner posts x 14 1/2 in + 1 mid-span post x 24 in (4 1/8 in offcut). *Store price*
- [ ] **1 x** 2x4 x 8 ft. $7.08 each, $7.08. 1 corner post x 14 1/2 in + 3 mid-span posts x 24 in (9 1/8 in offcut). *Store price*

**Cuts**

- [ ] **8 x** Side board, 96 in. 2x8 x 8 ft, whole board. Outside, both walls: every course, both ends; the seams meet over the joint posts. *Model (Bed Lumber)*
- [ ] **4 x** End board. 2x8, cut 21 in. 4 from 1 x 12 ft, between the side boards. *Model (Bed Lumber)*
- [ ] **4 x** 2x4 corner post. 2x4, cut 14 1/2 in (18.5 in with 2x10 walls). Inside each corner, edge-on to the side boards, standing on grade; 1 from 1 x 8 ft, 3 from 1 x 6 ft. *Model (Bed Lumber)*
- [ ] **4 x** 2x4 mid-span post. 2x4, cut 24 in. Flat against the side boards, centred 50, 142 in from the near end, about 9 1/2 in in the ground; 3 from 1 x 8 ft, 1 from 1 x 6 ft. *Model (Bed Lumber)*
- [ ] **2 x** 2x8 joint post. 2x8, cut 24 in, lying flat. Inside the wall behind each seam, 7 1/4 in face against the boards, centred 96 in from the near end, about 9 1/2 in in the ground; 2 from 1 x 12 ft. *Model (Bed Lumber)*

**Fasteners**

- [ ] **32 x** #9 x 3 in exterior structural screws. Star drive; coated for treated lumber, stainless 305/316 for cedar or redwood. 16 side boards into the corner post edges + 16 corner ties into end grain. *Derived from model*
- [ ] **48 x** #9 x 2.5 in exterior structural screws. Same finish as the 3 in screws. 16 side boards into the mid-span post faces + 16 end boards into the corner post faces + 16 side boards into the joint post faces. *Derived from model*

**Drip riser**

- [ ] **1 x** 3/4 x 3/4 x 1/2 in PVC reducer tee, slip. Schedule 40. On the 3/4 in main, 8 in beyond the far end board, 6 1/8 in deep. *Model (Drip Irrigation)*
- [ ] **5 pieces** 1/2 in PVC pipe, schedule 40. Cut 6 1/4, 9, 6, 3 1/2, 4 in (28 3/4 in in all). Ground run, lower riser, upper riser, through the wall, head; cut from the 1 x 10 ft stick on the shopping list, shared by all 4 beds. *Model (Drip Irrigation)*
- [ ] **3 x** 1/2 in PVC 90 degree elbow, slip. Schedule 40. At the bottom of the riser and on each side of the wall. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in PVC ball valve, slip x slip. Lever handle. 3 7/8 in above grade on the outside of the far end wall, lever west along the wall. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in FPT x 4-port 1/4 in barb drip manifold head. Inside the bed, top 1 7/8 in above the wall top. *Model (Drip Irrigation)*
- [ ] **1 x** 1/2 in PVC male adapter, slip x MPT. Threads the head onto the riser. Not modelled; a female adapter instead if your head is male. *Derived from model*
- [ ] **2 x** 1/2 in stand-off pipe clamp. Galvanized or UV-stable plastic. At 1 1/2 and 8 3/4 in above grade, one on each board. *Model (Drip Irrigation)*
- [ ] **4 x** #8 x 1 in exterior pan-head screws. Same finish as the bed screws. Two per clamp. *Derived from model*
- [ ] **1 x** 1 in hole through the top far end board. Spade bit, centred 10 7/8 in above grade and 9 in from the bed's west outside face. The through-wall pipe passes it; bore it in place or before the top board goes on. *Model (Drip Irrigation)*

**Soil**

- [ ] **32.8 cu ft** Raised-bed soil mix. 1.21 cu yd at 14.5 in deep. 2x10 walls: 42.0 cu ft (1.55 cu yd). *Derived from model*

**Optional**

- [ ] **17 lin ft** Hardware cloth 1/2 in, 48 in wide (under the bed). Gopher / vole barrier. Not in model; one strip the length of the bed plus a foot, trimmed to 21 in wide. *Estimate*

## Pavers and paths

| Group | Pavers | Where |
|---|---|---|
| 12x12 Paver | 38 | Walkway along the top edge (2 rows, 15 in pitch) |
| First Bed Path | 11 | Path between Bed D (16 ft) and Bed C (14 ft), 18 in pitch |
| Second Bed Path | 10 | Path between Bed C (14 ft) and Bed B (12 ft), 18 in pitch |
| Third Paver Path | 8 | Path between Bed B (12 ft) and Bed A (10 ft), 18 in pitch |
| Fourth Paver Path | 7 | Path west of Bed A (10 ft), 18 in pitch |
| **Total** | **74** | 12 x 12 x 1.5 in, about 18 lb each |

Beds are 24 in apart with one 12 in paver centered in each gap. The walkway is a 33 in strip with two rows of pavers at 15 in pitch; a second 36 in strip beyond it is in the site sketch but not modeled. Base estimate: 2 in of leveling material under each paver, 12.3 cu ft, about 25 half-cubic-foot bags.

## Hog-wire trellis arches

| Arch | Between | Chord | Feet | Straight leg | Crown above grade | Upper supports | Walkway headroom | Panel width modeled |
|---|---|---|---|---|---|---|---|---|
| Arch AB | the centrelines of Bed A (10 ft) and Bed B (12 ft) | 75 in | on 2x4 sills, 1.5 in above grade | 37 in | 76 in | Bed A: east corner at the near end; Bed B: west corner at the near end | 76 in at the center, 74 in at the Bed A wall, 74 in at the Bed B wall | 60 in (16 wires at 4 in) |

Arch AB is one 16 ft panel bent over the 75 in between the centrelines of Bed A and Bed B, with its feet on 2x4 sills lying on the ground inside the beds, 1.5 in above grade. The 37.5 in radius top uses 118 in of the panel, so the straight legs are 37.1 in (the Fusion parameter Hogwire_height derives from the panel length) and the crown is 76 in above grade, level with the post tops. Standing the arch on the ground instead of the wall tops drops it 13 in, so that much of each leg ends up in the bed soil once the beds are filled. Walkway headroom: 76 in at the center, 74 in at the Bed A wall, 74 in at the Bed B wall.

Two of the beds' own corner posts hold the arch up: the inside corner post at the near end of each bed (Bed A's east corner, Bed B's west corner), which are uncut 8 ft 2x4s set 20 in into the ground, 76 in above grade. The panel's near edge wire runs up the 3.5 in face of each post that looks down the bed and crosses it between 72 and 74 in above grade, so the post top stands 4 in above the crossing. 2 screws with fender washers there, one each side of the wire, trap it. The posts keep the arch upright along the beds and take the wind; the sills and stakes hold its feet.

Each foot: a 60.5 in 2x4 sill lies flat on grade along the bed centreline with a 24 in 2x4 stake at each end, driven 10.5 in and standing 12 in above the sill. The near stake sits against the end board like a corner post; the far one is 63.5 in down the bed. The panel's bottom wire lies along the sill top and its edge wires rise against the stake faces: 4 screws with washers along the sill, 2 on each stake, and 2 x #9 3 in through each stake into the sill's end grain. Set the posts and stakes before the walls go on (the near stake and the trellis post both stand against the end board), screw the sills to the stakes, bend the panel in and fasten it, then fill the beds.

The model wires are 1/2 in for visibility; real panels are 4-gauge and weigh about 35 to 40 lb each, so ignore the model's steel mass. A 48 or 50 in wide panel makes the tunnel that much shorter along the walkway; shorten the sills to match. Arch BC (between beds B and C at the far end) is still modeled on the old wall-top scheme and is hidden (parked) in the model: the same bed-centre scheme there needs one more 8 ft post on Bed C's west wall opposite Bed B's far corner. There is no arch between beds C and D.

## Low-tunnel hoops

| Over | Hoops | Pitch | Width | Top above grade | Legs | Tube each | Tube in all |
|---|---|---|---|---|---|---|---|
| Bed C (14 ft) | 6 | 31 in | 40 in | 57 in | 36 in | 136 in (11.4 ft) | 68 ft |

6 hoops of 1 in tube cover Bed C: the first stands 5 in inside the near end board, the last 5 in inside the far one, and they are 31 in apart. Each hoop is 40 in wide between its legs, 3.5 in clear of the side walls, with 36 in straight legs that go down through the 14.5 in of soil to grade (set them before the beds are filled, or push them in afterwards) and a 64 in semicircular top of 20 in radius; the crown is 57 in above grade, 43 in above the soil.

Tube: 136 in (11.4 ft) per hoop, 68 ft in all. A 10 ft stick is short, so either bend 12 ft stock or join two pieces with a coupling low in one leg. If the tunnel gets a cover, it needs about 9 ft of width over the hoops and 17 ft of length to reach the soil at both ends.

## Drip risers

| Item | Value |
|---|---|
| Risers | 4, one per bed, on the outside of each far end wall |
| Riser position | 9 in from the bed's west outside face, 1 1/4 in off the wall |
| Hole | 1 in, centred 10 7/8 in above grade (the middle of the top board) |
| Ball valve | 3 7/8 in above grade, lever west along the wall |
| Clamps | 1 1/2 and 8 3/4 in above grade, one per board |
| Head | base 14 3/8 in, top 16 3/8 in (1 7/8 in above the wall) |
| Main | 8 in beyond the end board, 6 1/8 in deep; reducer tee at each riser |
| 1/2 in pipe per bed | 28 3/4 in: 6 1/4 + 9 + 6 + 3 1/2 + 4 |
| 1/2 in pipe in all | 115 in = 1 x 10 ft stick |

Every bed gets the same riser on the outside of its far end wall, 9 in from the bed's west outside face (beds A, B, C, D): that keeps the hole clear of the edge-on corner post, which reaches 5 in in from the side board, and in Bed C keeps the pipe inside the bed clear of the hoop legs. From the 3/4 in main, 8 in beyond the end board and 6 1/8 in below grade, a 3/4 x 3/4 x 1/2 reducer tee feeds 6 1/4 in of 1/2 in pipe along the ground, an elbow turning up, 9 in of pipe up the outside of the wall, the ball valve, 6 in more pipe, an elbow turning into the bed, 3 1/2 in of pipe through a 1 in hole, an elbow turning up inside the bed, and 4 in of pipe to the 4-port 1/4 in drip head.

The hole is centred 10 7/8 in above grade, 3 5/8 in up the top board, so it sits in the middle of that board and the elbows on either side of the wall stop 1/4 in short of it; the riser stands 1 1/4 in off the wall. The valve is 3 7/8 in above grade with its lever pointing west along the wall. Two stand-off clamps at 1 1/2 and 8 3/4 in, each screwed into a single board with two screws, hold the riser and so the valve. Inside the bed the head stands on 4 in of pipe: its base is at 14 3/8 in, just under the 14 1/2 in wall top, and its four 1/4 in barbs are about 1 1/2 in above the soil line, where the 1/4 in drip lines start.

Per bed: one reducer tee, 3 elbows, one valve, one head with a 1/2 in male adapter to thread it on (not modelled; the head sits straight on the pipe in the model), two clamps with four screws, and 28 3/4 in of 1/2 in pipe cut 6 1/4 + 9 + 6 + 3 1/2 + 4. All 4 risers need 115 in of pipe: 1 x 10 ft stick with 2 5/8 in to spare after the kerfs. Prime and cement the slip joints, tape the head's thread, and bore the holes with a 1 in spade bit, in place or before the top boards go on.

The 3/4 in main is drawn only to place the tees: a stair-step 8 in beyond each far end board, 6 1/8 in deep, stepping to the next bed at the gap centres under the paver paths (26 ft and 6 elbows as drawn). The plot's angled edge passes only 2 to 4 in beyond the inner step corners, so the real route may have to cut those corners. Change the main's offset or depth, the pipe lengths or the riser position in scripts/fusion_build_irrigation.py and run it again; the risers and holes follow.

## Soil

| Bed | Inside | Depth | Volume |
|---|---|---|---|
| A | 48 x 117 in | 14.5 in | 46.5 cu ft |
| B | 48 x 141 in | 14.5 in | 56.2 cu ft |
| C | 48 x 165 in | 14.5 in | 65.7 cu ft |
| D | 21 x 189 in | 14.5 in | 32.8 cu ft |
| **Total** | | | **201 cu ft = 7.5 cu yd** |

Volumes subtract the posts. With 2x10 walls (18.5 in) the total is 257 cu ft = 9.5 cu yd.

## Optional items modeled but hidden

- **Single-tube arch** (Garden Arch): 1 in tube, 7 ft span, 42 in legs, 7 ft tall, about 18 ft of tube. Same location as Arch AB; superseded.

## Model notes (Fusion)

- New component **Bed Lumber** holds the buildable beds (2x8 walls, 2x4 posts); the original 4 in-wall massing bodies in **Raised Beds** are hidden and kept as the layout reference the arch sketches use.
- New user parameters: `Board_Width` (7.25 in = 2x8), `Courses` (2) and `Mid_Post_Length` (24 in), plus `Board_Thickness` and `Post_Size` for reference. Bed height = Courses x Board_Width; each bed's `Mid post extrude` runs Courses x Board_Width up and the rest of Mid_Post_Length down from the Posts sketch.
- Physical materials fixed: pavers were Pine with a concrete appearance and are now **Concrete (paver)** at 2300 kg/m3; arch wires are **Steel, Galvanized**; the tube arch is **Steel**.
- Component part numbers and descriptions filled in; "Forth Paver Path" renamed "Fourth Paver Path".
- The ten superseded rolled-back features that sat after the timeline marker (Position5, R-Pattern2, the old Sketch1-4 / Extrude1-3 bed layout, and a broken CopyPaste 2x8x8:3) were deleted on 2026-11-05.
- 2026-11-06, trellis arch: Arch AB now runs from the centre of Bed A to the centre of Bed B with its feet on the ground (parametric Move "Onto the sills": 21 in across the beds, 1.25 in along them, Board_Thickness up). New parameters `Trellis_Post_Length` (96 in), `Trellis_Post_Embed` (20 in) and `Stake_Above_Sill` (12 in). The inside corner post at the near end of beds A and B moved out of `Post extrude` into a two-sided `Trellis post extrude` (body "2x4 trellis post"); each of those beds got an "Arch anchors" sketch with a `Sill extrude` (body "2x4 sill") and a two-sided `Stake extrude` (bodies "2x4 stake"). `Hogwire_height` is `(Hogwire_length - Hogwire_archlength) / 2` = 37.1 in. The earlier wall-top scheme of the same day (72 in posts under the arch legs) is superseded: Arch BC is hidden (parked) and its posts are ordinary again. The T-post anchors are gone.
- 2026-11-06, hoops: the six root-level Garden Hoops occurrences (one seed at the plot edge, a copy over Bed B and the root pattern R-Pattern2) are now an assembly. Component **Garden Hoops** holds one occurrence of the part, renamed **Hoop** (body "1 in tube hoop", visible again), placed over Bed C's centreline 6.5 in from the near end, and a rectangular pattern "Hoops along the bed" along the assembly Y axis driven by the new parameters `Hoop_Count` (6) and `Hoop_Pitch` (31 in). Change either parameter to respace the tunnel.
- 2026-11-06, drip risers: new root component **Drip Irrigation** holds one **Drip riser** component placed at each bed's far end wall and the reference **3/4 in main (existing)**. Their bodies are temporary-BRep solids in one base feature per component (not parametric: scripts/fusion_build_irrigation.py holds the numbers and rebuilds everything on re-run). Each bed's lumber component got a "Drip hole" sketch on the outer face of its top far end board and a through-all `Drip hole cut` (1 in). Materials PVC-Piping, clamps Steel, Galvanized; all of it in the timeline group "Drip irrigation". fusion_build_bed_lumber.py does not know about the holes, so run the irrigation script again after rebuilding the lumber.
- 2026-11-08, two-board sides: the side walls of beds C and D are now two boards per course (Bed C course 1: 96 + 72 in, course 2: 72 + 96 in; Bed D course 1: 96 + 96 in, course 2: 96 + 96 in) with a 2x8 joint post behind every seam, done in place by scripts/fusion_split_sides.py: a hidden construction plane and a Split Body at each seam, a "Joint posts" sketch with a two-sided `Joint post extrude` (bodies "2x8 joint post", Courses x Board_Width up and the rest of Mid_Post_Length down), the 2x4 mid posts a joint post replaces removed and the rest moved so the gaps between posts are even, all in the timeline group "Two-board sides". scripts/fusion_build_bed_lumber.py builds the same layout from scratch (SIDE_SPLITS).
- The Fusion document was saved on 2026-11-06 with the bed-centre arch, sills, stakes, the hoop assembly over Bed C and the drip risers in place. The two-board side walls of beds C and D with their 2x8 joint posts (2026-11-08) came after that save and are not saved yet.

Model mass by material (visible bodies): Concrete (paver) 1,328 lb, Steel, Galvanized 180 lb, Pine 847 lb, Iron, Wrought 182 lb, PVC-Piping 22 lb. The model hoops are solid 1 in rod of wrought iron, about 30 lb each; real 1 in EMT weighs about 8 lb per hoop.

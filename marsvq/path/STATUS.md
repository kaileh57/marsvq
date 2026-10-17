# Path status: ground-plane path labels for the sol-104 NavCam frames

Built 2026-10-17 by `marsvq/path/build_paths.py` (Python 3 standard library only, no network). To rebuild, run `python3 -I marsvq/path/build_paths.py`.

**Camera model:** the full CAHVORE from `raw_image_api_metadata.json`, not a pinhole fallback. Its type is 2 (fisheye, linearity 0), it is in the rover navigation frame, and it is in 1280×960 pixel space. Output is scaled by 0.9375 to the 1200×900 JPEGs.

The fisheye reading comes from the type code, and the published optics confirm it. The model's focal length (|A×H|) is about 740 px. An equidistant fisheye with that focal length covers 99° horizontally, while a perspective lens would cover 82°; the published NavCam FOV is 96° × 73°. That 96:73 ratio also matches the 1280:960 frame, as a linear-angle mapping requires; a perspective lens with 96° horizontal would cover about 80° vertically. The horizon check below doesn't separate the two mappings, because they differ by only about 25–30 px at the horizon.

## Outputs

- `data/pairs/<stem>/path.json` is a plain list of `[u, v]` in JPEG pixels. (0, 0) is the top-left corner of the image, pixel centers sit at +0.5, u points right and v points down. These coordinates go straight onto a 1200×900 canvas.
- `data/pairs/index.json` has one entry per frame: `stem`, `jpeg` (a repo-relative reference to the source; nothing is copied), `path`, and the geometry used (heading, curvature, start point, camera height, point counts, predicted horizon row).

## Path definition

- **Ground:** flat plane z = 0 in the rover navigation frame (x forward, y right, z down). The model puts the camera 1.90 m above that plane. Rover tilt is ignored. Reading the attitude quaternion as w,x,y,z order gives about 1.6° of tilt.
- **Points:** 33 points, spaced by arc length s_i = 20·(i/32)² m (spec §4.1). They start at the camera footprint, the ground point directly under the camera center C.
- **Shape:** a constant-curvature arc bending left, κ = 1/80 m⁻¹. That gives about 2.5 m of lateral offset and 14° of heading change at 20 m.
- **Heading:** each frame's path follows that frame's camera boresight (the horizontal part of CAHVORE A), not the rover's +x drive direction. Four of the six frames look 60°–150° away from the rover's nose, so a +x path would leave them with no label. To switch to +x, set `heading = 0` in `main()`.
- **Drops:** points behind the camera and points at or above the horizon are dropped. On flat ground out to 20 m, neither case happens, so all 6 frames keep all 33 points.
- **Off-frame points:** the first 7 points (s ≤ 0.70 m) land below the bottom edge (v > 900), because that ground is nearly under the camera. They were kept because they are not behind the camera or above the horizon. 26 of 33 points fall inside the frame in every image.

## Checks

- **Horizon.** The predicted horizon row along each heading (`horizon_v_at_heading`, v = 61 to 99) matches the visible far-plain edge in all six JPEGs to within about 10–25 px. The difference comes from terrain.
- **Distortion terms.** E only moves the off-frame nadir point, by about 1 px. R moves the far points by about 3 px.

## Known limits

- **Rover body hides the near path in some frames.** By eye, hardware covers the path below roughly these rows:

  | Mast az | Path hidden below about |
  |---|---|
  | 228° | v ≈ 310 (deck and high-gain antenna) |
  | 299° | v ≈ 320 (arm turret) |
  | 156° | v ≈ 700 (arm) |
  | 10.9° | v ≈ 810 |
  | 0.6° | v ≈ 860 |
  | 84° | essentially clear |

  The labels carry no occlusion mask. A training loader should mask these rows or skip the az 228° and 299° frames.
- **Ground height is uncertain.** z = 0 assumes the rover frame origin is on the ground. The published NavCam height of about 2 m suggests the true ground may sit a few cm lower, which would move near points by a few pixels.
- **These are synthetic paths, not driven paths.** Five frames come from one stop, so this is not a drive sequence (see `data/raw/SOURCES.md`).

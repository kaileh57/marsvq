# MarsVQ

Team: solo, Kellen Heraty (Discord: DISCORD_TBD)

Title track: Visa

Side track: SpaceXAI

Other tracks: none

Repo: https://github.com/kaileh57/marsvq

Video: https://github.com/kaileh57/marsvq/blob/main/docs/demo.mp4

Visa is the submission slot; the work is the driving-pair system.

## What it does

MarsVQ makes training pairs for a driving model from real Mars rover photos. Each pair starts from a Perseverance NavCam frame. A driving path is projected into the frame through that frame's own CAHVORE camera model. Then Grok Imagine edits the frame into Europa ice, with a prompt that asks it to keep every rock, the horizon, and the camera unchanged. If the edit keeps the geometry, the path label from the real frame also fits the edited one, and a single label covers two images.

The demo is a single page and a 40 s video. Both show 8 pairs from a 225 m stretch of Perseverance's drive across the Jezero crater floor, sols 102 to 110. Each image has one green path line. The arrow keys step through pairs, and E switches between the real frame and the edit.

## How I built it

I searched NASA's raw-image API for NavCam frames on sols 100 to 112 and took one frame per rover stop, the one with the mast pointed closest to straight ahead. That gave 16 frames from 16 different stops. The API record for each frame includes its CAHVORE camera model, so the path projection uses the camera's real fisheye geometry rather than a guessed field of view.

Each path is a flat-ground arc of 33 points out to 20 m. I dropped 7 of the 16 frames. In five, the mast points 25° above the horizon, so the near path falls below the image. In two, the mast is turned 10° to 16° left and the near path crosses the rover's deck rail.

The 9 frames left were sent to the xAI image edit endpoint (grok-imagine-image-2.0) with one fixed prompt. Two already had edits from an earlier batch, so 7 new edits cost $0.49 in total.

To check the edits, I compare Canny edge maps of each edit and its source. Recall is the fraction of source edges that still have an edge within 3 px in the edit. Before building the drive set, I scored the four edits from the earlier batch. Their median recall was 0.769, above the 0.6 bar I had set for spending more. The 9 drive-set edits have a median recall of 0.744. The demo keeps the 8 with recall of at least 0.5.

## What failed

The edge check is weak. An unrelated image with as many edges as these edits would still score a recall of 0.32 to 0.64, so 0.7 is only modestly above chance.

It also misses invented objects. Four of the 9 drive edits add something the prompt forbids. Three put a planet in a starry sky. One puts a rock about 50 px from the path, on what is bare sand in the real frame. The 0.5 recall cut removed one of the four. Recall can't see the others, because adding an object removes no source edges. The other three are in the demo, and the README table marks them. For the rock pair, the reused label no longer matches the terrain under it.

Earlier, I tried restyling video instead of stills, on a single NASA Mastcam-Z photo (PIA24765). By 1 s the video prompted as Europa showed new ice slabs that matched none of the original rocks, and its edge IoU against the source was 0.215, below the 0.241 expected by chance. An image edit of the same photo scored 0.511 against a chance level of 0.260. That is one clip, so it is not a benchmark, but it is why I edit stills.

The paths are synthetic, not the rover's real track, and they assume flat ground. There is no occlusion mask and no trained model.

## Built with

Python, numpy, Pillow, ffmpeg, xAI Grok Imagine image edit (grok-imagine-image-2.0), HTML canvas, NASA Mars 2020 raw-image API.

## Credits

NavCam images and PIA24765: NASA/JPL-Caltech.

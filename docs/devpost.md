# MarsVQ

Team: solo, Kellen Heraty (Discord: DISCORD_TBD)

Title track: Visa

Side track: SpaceXAI

Repo: REPO_TBD

Video: VIDEO_TBD

Visa is the submission slot. The work is the driving-pair system.

## What it does

MarsVQ builds driving-data pairs from real Mars rover photos. It starts from six real Perseverance NavCam frames taken on sol 104. On each frame it draws a driving path across the ground, projected through that frame's own CAHVORE camera model. Then Grok Imagine edits the same frame into Europa ice while keeping the camera and the rocks in place. Because the framing stays fixed, the path drawn for the real frame can be reused as the label for the edited frame.

A single HTML page shows the pairs. Each frame fills the window with its path as a green line. The arrow keys step through frames, and `E` switches between the real photo and the edit with the same path on top.

## How I built it

The frames are 1200×900 NavCam browse JPEGs from NASA's raw-image archive. The API record for each frame includes its CAHVORE camera model, the rover attitude, and the mast pointing. The model is a fisheye (type 2). Its focal length implies about 99° of horizontal coverage, close to the published NavCam field of view of 96°.

A Python script that uses only the standard library builds the paths. Each path has 33 points on flat ground, spaced out to 20 m along an arc that bends left at a curvature of 1/80 m⁻¹. The path follows each frame's camera boresight rather than the rover's nose. Four of the six frames look 60° to 150° away from the nose, so a nose-forward path would leave them with no label. As a check, I compared the predicted horizon row with the visible far-plain edge, and they match to within about 10 to 25 px in all six frames.

A second script sends each frame to the xAI image edit endpoint with `grok-imagine-image-2.0` and one fixed prompt. The prompt asks for photoreal Europa ice and asks the model to keep every rock, the horizon, and the camera unchanged. Each edit cost $0.07.

The viewer is one `index.html` that opens from disk with no server. The path data is copied into the page, and the line is scaled to whichever image is showing.

## What failed

The edit batch stopped at 4 of 6. The fifth call returned HTTP 402 with code `personal-team-blocked:spending-limit` and the message "You have run out of credits or need a Grok subscription." The sixth was never sent. Two frames have only the real photo and the path.

In two frames, the camera looks sideways at the rover and the path runs across the rover deck. The labels have no occlusion mask, so a training loader would need to mask those rows or skip those frames.

Restyling video directly does not keep the geometry. Before the NavCam batch, I tested image-to-video on a NASA Mastcam-Z photo (PIA24765) prompted as Europa. By 1 s the whole frame was new ice slabs that matched none of the original rocks. Its edge overlap with the source fell to an IoU of 0.215, below the 0.241 expected by chance. That is one clip, so it is not a benchmark. An image edit of the same photo kept the rocks in place, with an edge IoU of 0.511 against a chance level of 0.260. So the NavCam batch edits stills, not video.

The edits are not perfect either. One of them added Jupiter to the sky, even though the prompt said "Add no new objects."

## Built with

Python standard library, xAI Grok Imagine image edit (`grok-imagine-image-2.0`), HTML canvas, NASA Mars 2020 raw-image API.

## Credits

NavCam images: NASA/JPL-Caltech. PIA24765: NASA.

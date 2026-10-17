# Frame sources: Perseverance NavCam drive, sols 101 to 110

All 16 frames are NavCam left-eye browse JPEGs (1200×900, downsampled by JPL from 1280×960) from the NASA Mars 2020 raw-image server. Credit: NASA/JPL-Caltech. Each frame was taken at a different stop (site 4, drive 218 to 922) as the rover drove across the Jezero crater floor. They are not a panorama from one stop. For each stop we took the full-frame image whose rover-relative mast azimuth was nearest 0° (straight ahead).

Local copies are in `data/raw/real/m2020_sol0101_0110_ncam_drive/` (gitignored). The API record for each frame, including its CAHVORE camera model, is in `raw_image_api_metadata.json` in the same folder.

Query used per sol (sol 100 to 112 searched):

`https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&num=100&page=0&order=sol+desc&search=%7CNAVCAM_LEFT&condition_2=<sol>:sol:gte&condition_3=<sol>:sol:lte&extended=sample_type::full,`

Filter: `extended.dimension == (1280,960)`, `subframeRect == (1,1,5120,3840)`, mast azimuth within 25° of 0, one frame per (site, drive).

Kept frames are the ones that `marsvq/path/select_drive.py` marks `kept` in `data/pairs/drive_index.json`. Two rules drop frames: a mast pointed above the horizon, or a near path that lies on the rover deck rail. We found the rail crossings by looking at the frames. The saturation threshold in the script only records that visual check.

| # | Sol | Drive | Taken (UTC) | Mast az / el (°) | Step from previous stop (m) | Kept | Reason | URL |
|---|---|---|---|---|---|---|---|---|
| 1 | 101 | 218 | 2021-06-02T17:19:15Z | 360.0 / 25.0 |  | no | mast pointed above the horizon; near path below the frame | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00101/ids/edr/browse/ncam/NLF_0101_0675926193_193ECM_N0040218NCAM00501_01_295J01_1200.jpg |
| 2 | 102 | 350 | 2021-06-03T13:12:14Z | 359.8 / -29.9 | 42.7 | yes |  | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00102/ids/edr/browse/ncam/NLF_0102_0675997770_933ECM_N0040350NCAM00301_01_295J01_1200.jpg |
| 3 | 103 | 372 | 2021-06-04T13:39:51Z | 360.0 / 25.0 | 4.9 | no | mast pointed above the horizon; near path below the frame | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00103/ids/edr/browse/ncam/NLF_0103_0676085828_396ECM_N0040372NCAM00501_01_295J01_1200.jpg |
| 4 | 103 | 408 | 2021-06-04T14:59:18Z | 359.8 / -29.9 | 19.5 | yes |  | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00103/ids/edr/browse/ncam/NLF_0103_0676090594_606ECM_N0040408NCAM00301_01_295J01_1200.jpg |
| 5 | 103 | 430 | 2021-06-04T15:59:20Z | 343.8 / -30.1 | 5.0 | no | near path lies on the rover deck rail | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00103/ids/edr/browse/ncam/NLF_0103_0676094195_382ECM_N0040430NCAM03103_01_295J01_1200.jpg |
| 6 | 104 | 488 | 2021-06-05T15:12:35Z | 359.8 / -29.9 | 34.1 | yes |  | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00104/ids/edr/browse/ncam/NLF_0104_0676177790_823ECM_N0040488NCAM00301_01_295J01_1200.jpg |
| 7 | 104 | 510 | 2021-06-05T16:09:05Z | 10.1 / -30.6 | 5.0 | yes |  | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00104/ids/edr/browse/ncam/NLF_0104_0676181181_035ECM_N0040510NCAM03104_01_295J01_1200.jpg |
| 8 | 105 | 570 | 2021-06-06T15:39:31Z | 359.8 / -29.9 | 22.0 | yes |  | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00105/ids/edr/browse/ncam/NLF_0105_0676265805_788ECM_N0040570NCAM00309_01_295J01_1200.jpg |
| 9 | 105 | 592 | 2021-06-06T17:58:57Z | 360.0 / 25.0 | 4.9 | no | mast pointed above the horizon; near path below the frame | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00105/ids/edr/browse/ncam/NLF_0105_0676274173_698ECM_N0040592NCAM00501_01_295J01_1200.jpg |
| 10 | 107 | 638 | 2021-06-08T18:16:44Z | 359.8 / -29.9 | 5.9 | yes |  | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00107/ids/edr/browse/ncam/NLF_0107_0676448037_177ECM_N0040638NCAM00309_01_295J01_1200.jpg |
| 11 | 108 | 710 | 2021-06-09T16:54:11Z | 359.8 / -29.9 | 16.0 | yes |  | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00108/ids/edr/browse/ncam/NLF_0108_0676529483_823ECM_N0040710NCAM00301_01_295J01_1200.jpg |
| 12 | 108 | 738 | 2021-06-09T17:45:59Z | 349.7 / -29.7 | 4.9 | no | near path lies on the rover deck rail | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00108/ids/edr/browse/ncam/NLF_0108_0676532592_679ECM_N0040738NCAM03108_01_295J01_1200.jpg |
| 13 | 109 | 810 | 2021-06-10T18:28:40Z | 359.8 / -29.9 | 46.8 | yes |  | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00109/ids/edr/browse/ncam/NLF_0109_0676621552_135ECM_N0040810NCAM00301_01_295J01_1200.jpg |
| 14 | 110 | 822 | 2021-06-11T12:39:29Z | 360.0 / 25.0 | 5.0 | no | mast pointed above the horizon; near path below the frame | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00110/ids/edr/browse/ncam/NLF_0110_0676687000_491ECM_N0040822NCAM00501_01_295J01_1200.jpg |
| 15 | 110 | 910 | 2021-06-11T19:09:10Z | 359.8 / -29.9 | 51.1 | yes |  | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00110/ids/edr/browse/ncam/NLF_0110_0676710381_120ECM_N0040910NCAM00301_01_295J01_1200.jpg |
| 16 | 110 | 922 | 2021-06-11T21:52:08Z | 360.0 / 25.0 | 5.0 | no | mast pointed above the horizon; near path below the frame | https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00110/ids/edr/browse/ncam/NLF_0110_0676720159_902ECM_N0040922NCAM00501_01_295J01_1200.jpg |

Frames 0676177790 and 0676181181 also appear in the earlier sol-104 set (`data/raw/real/m2020_sol0104_ncam/`). Their edits were made from that copy, and it is the same file.

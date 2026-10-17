"""Frozen DINOv2 ViT-S/14 features for a list of images.

Run: ~/Projects/mlenv/.venv/bin/python marsvq/model/features.py OUT_NPZ IMAGE [IMAGE ...]

Every image is converted to grayscale (many NavCam frames are mono, and the edits recolor the
scene), copied to three channels, resized to 448x336 and normalized with ImageNet statistics.
The output per image is the CLS token (384) followed by the patch tokens average-pooled to a 4x3
grid (12 x 384), 5376 numbers in all. The grid keeps where in the frame things are, which a
bearing depends on. The backbone is never trained.
"""

import sys

import numpy as np
import torch
from PIL import Image

W, H = 448, 336  # 32 x 24 patches of 14 px
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


def load(path):
    g = np.asarray(Image.open(path).convert("L").resize((W, H), Image.BICUBIC), np.float32) / 255
    x = (np.repeat(g[..., None], 3, -1) - MEAN) / STD
    return torch.from_numpy(x.transpose(2, 0, 1))


@torch.no_grad()
def main():
    out, paths = sys.argv[1], sys.argv[2:]
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    net = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14", trust_repo=True).eval().to(dev)
    feats = []
    for i in range(0, len(paths), 16):
        x = torch.stack([load(p) for p in paths[i:i + 16]]).to(dev)
        o = net.forward_features(x)
        cls = o["x_norm_clstoken"]
        patch = o["x_norm_patchtokens"].reshape(len(x), H // 14, W // 14, -1).permute(0, 3, 1, 2)
        grid = torch.nn.functional.adaptive_avg_pool2d(patch, (3, 4)).flatten(1)
        feats.append(torch.cat([cls, grid], 1).cpu().numpy())
    np.savez(out, feats=np.concatenate(feats), paths=np.array(paths))
    print("%d images -> %s" % (len(paths), out))


if __name__ == "__main__":
    main()

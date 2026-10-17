"""Train three bearing predictors and test them on the real held-out sols.

Run: ~/Projects/mlenv/.venv/bin/python marsvq/model/train_eval.py

Target: cam_bearing_deg, the direction of the real next stop (>= 10 m away) relative to the camera
boresight, from data/real/{train,test}_labels.json.

Runs:
- constant: predicts the training mean for every frame.
- mars: ridge regression on frozen DINOv2 features (features.py) of the 81 real training frames.
- mars+edits: the same, plus every Imagine edit of a training frame that passed edit_filter.py,
  labeled with its source frame's bearing.

Train is sols 1 to 339 (sites 3 to 8). Test is sols 340 to 460 (sites 9, 10, 23, 24, 25). No stop
and no site is in both. Features are standardized on the training rows. The ridge alpha is chosen
once, by 5-fold cross-validation on the mars run, grouped by sol so that stops from one drive never
sit on both sides of a fold. mars+edits uses the same alpha, so the two runs differ only in their
training rows. The mars+edits cross-validation score at that alpha is reported too, with each edit
in its source's fold and only real frames scored. The test set is used once per run, after the
alpha is fixed.

Writes data/real/results.json: the table, the alpha, a paired bootstrap of the difference in
held-out MAE, and every test prediction (used by the demo). The bootstrap resamples test sols, not
stops, because stops from one sol share a drive and are not independent.
"""

import json
import os

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REAL = os.path.join(ROOT, "data", "real")
ALPHAS = np.logspace(0, 6, 25)
SEED = 0


def load(name):
    z = np.load(os.path.join(REAL, "features", name + ".npz"))
    return z["feats"].astype(np.float64), [os.path.basename(str(p)) for p in z["paths"]]


def fit_predict(x_tr, y_tr, x_te, alpha):
    mu, sd = x_tr.mean(0), x_tr.std(0) + 1e-6
    m = Ridge(alpha=alpha).fit((x_tr - mu) / sd, y_tr)
    return m.predict((x_te - mu) / sd)


def cv_mae(x, y, groups, is_real, alpha):
    err = []
    for tr, va in GroupKFold(5).split(x, y, groups):
        va = va[is_real[va]]
        err.append(np.abs(fit_predict(x[tr], y[tr], x[va], alpha) - y[va]))
    return float(np.concatenate(err).mean())


def choose_alpha(x, y, groups, is_real):
    return min(((a, cv_mae(x, y, groups, is_real, a)) for a in ALPHAS), key=lambda r: r[1])


def metrics(pred, y):
    e = pred - y
    return {"mae_deg": round(float(np.abs(e).mean()), 2),
            "median_ae_deg": round(float(np.median(np.abs(e))), 2),
            "rmse_deg": round(float(np.sqrt((e ** 2).mean())), 2),
            "within_10deg": round(float((np.abs(e) <= 10).mean()), 3)}


def main():
    train = json.load(open(os.path.join(REAL, "train_labels.json")))
    test = json.load(open(os.path.join(REAL, "test_labels.json")))
    filt = json.load(open(os.path.join(REAL, "edit_filter_train.json")))["edits"]
    keep = {r["stem"] for r in filt if r["keep"]}

    x_tr, p_tr = load("train_real")
    x_te, p_te = load("test_real")
    x_ed, p_ed = load("train_edits")
    assert p_tr == [e["stem"] + ".jpg" for e in train] and p_te == [e["stem"] + ".jpg" for e in test]
    y_tr = np.array([e["cam_bearing_deg"] for e in train])
    y_te = np.array([e["cam_bearing_deg"] for e in test])
    g_tr = np.array([e["sol"] for e in train])
    by_stem = {e["stem"]: e for e in train}

    # p_ed holds data/pairs/<stem>/edit.jpg paths; recover the stem from the parent directory.
    ed_stems = [os.path.basename(os.path.dirname(p)) for p in np.load(os.path.join(REAL, "features", "train_edits.npz"))["paths"]]
    sel = [i for i, s in enumerate(ed_stems) if s in keep]
    x_e = x_ed[sel]
    y_e = np.array([by_stem[ed_stems[i]]["cam_bearing_deg"] for i in sel])
    g_e = np.array([by_stem[ed_stems[i]]["sol"] for i in sel])

    preds, runs = {}, {}
    preds["constant"] = np.full(len(y_te), y_tr.mean())
    runs["constant"] = {"n_train": len(y_tr), "n_edits": 0, "value_deg": round(float(y_tr.mean()), 2)}

    # One alpha for every run, picked on mars alone.
    a, cv = choose_alpha(x_tr, y_tr, g_tr, np.ones(len(y_tr), bool))
    preds["mars"] = fit_predict(x_tr, y_tr, x_te, a)
    runs["mars"] = {"n_train": len(y_tr), "n_edits": 0, "alpha": float(a), "cv_mae_deg": round(cv, 2)}

    x2, y2 = np.vstack([x_tr, x_e]), np.concatenate([y_tr, y_e])
    g2, real2 = np.concatenate([g_tr, g_e]), np.concatenate([np.ones(len(y_tr), bool), np.zeros(len(y_e), bool)])
    cv = cv_mae(x2, y2, g2, real2, a)
    preds["mars+edits"] = fit_predict(x2, y2, x_te, a)
    runs["mars+edits"] = {"n_train": len(y2), "n_edits": len(y_e), "alpha": float(a), "cv_mae_deg": round(cv, 2)}

    for k in runs:
        runs[k].update(metrics(preds[k], y_te))

    # Resample sols with replacement and pool the stops of the drawn sols.
    g_te = np.array([e["sol"] for e in test])
    sols = np.unique(g_te)
    member = (g_te[None, :] == sols[:, None]).astype(float)
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(sols), (10000, len(sols)))
    counts = np.stack([np.bincount(r, minlength=len(sols)) for r in draws]) @ member
    boot = {}
    for a_name, b_name in (("mars+edits", "mars"), ("mars", "constant"), ("mars+edits", "constant")):
        d = np.abs(preds[a_name] - y_te) - np.abs(preds[b_name] - y_te)
        bd = counts @ d / counts.sum(1)
        boot[f"{a_name} minus {b_name}"] = {
            "mae_diff_deg": round(float(d.mean()), 2),
            "ci95": [round(float(np.percentile(bd, 2.5)), 2), round(float(np.percentile(bd, 97.5)), 2)],
            "p_diff_below_0": round(float((bd < 0).mean()), 3)}

    out = {
        "target": "cam_bearing_deg (real next stop >= 10 m, relative to camera boresight)",
        "train": {"sols": "1-339", "sites": sorted({e["site"] for e in train}), "n_stops": len(train),
                  "n_edits_made": len(ed_stems), "n_edits_kept": len(y_e)},
        "test": {"sols": "340-460", "sites": sorted({e["site"] for e in test}), "n_stops": len(test),
                 "n_sols": len(sols), "label_sd_deg": round(float(y_te.std(ddof=1)), 2)},
        "alpha": {"value": float(a), "chosen_on": "mars", "used_for": ["mars", "mars+edits"]},
        "runs": runs, "bootstrap_resampled_by": "sol", "bootstrap_paired": boot,
        "test_predictions": [{"stem": e["stem"], "sol": e["sol"], "site": e["site"], "drive": e["drive"],
                              "true_deg": e["cam_bearing_deg"],
                              **{k: round(float(preds[k][i]), 2) for k in preds}} for i, e in enumerate(test)],
    }
    with open(os.path.join(REAL, "results.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print("held-out sols 340-460, %d stops in %d sols, label sd %.1f deg, alpha %.0f" % (
        len(y_te), len(sols), y_te.std(ddof=1), a))
    print("%-11s %8s %7s %8s %9s %8s %8s" % ("run", "n_train", "edits", "MAE", "median", "RMSE", "<=10deg"))
    for k, r in runs.items():
        print("%-11s %8d %7d %8.2f %9.2f %8.2f %8.3f" % (k, r["n_train"], r["n_edits"], r["mae_deg"],
                                                      r["median_ae_deg"], r["rmse_deg"], r["within_10deg"]))
    for k, v in boot.items():
        print("%s: %+.2f deg, 95%% CI [%+.2f, %+.2f]" % (k, v["mae_diff_deg"], *v["ci95"]))


if __name__ == "__main__":
    main()

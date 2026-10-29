"""Train on the metric's own gradient: absolute error with the band as a dead zone.

Why this and not the L1 arm that already exists. `abloss.py` measured -0.0455 from
switching to L1, the largest single effect in the log, and item 77 then showed the whole
of it survives only until the affine pair is applied. The reason is that L1 on the point
label is still a *monotone* thing to ask for -- it changes how hard the model pulls, not
which compounds it pulls for, and a monotone post-processing can undo it. The metric,
though, is not L1 on the point label. It is

    L(p) = max(0, lo - p, p - hi),

absolute error with a dead zone whose width is different for every compound. That width
is per-compound information, and no monotone map of the predictions can put it back.

The dead zone is worth having because the widths are not decoration. Measured on the
saved out-of-fold predictions, the rows whose band is wider than 1.0 pIC50 are

    enzyme    share of rows   share of squared loss   share of ST-RAE
    CYP1A2        14.6 %             44.7 %                20.0 %
    CYP2C9        17.0 %             33.8 %                12.6 %
    CYP2D6         9.9 %             41.2 %                12.8 %
    CYP3A4        29.4 %             44.5 %                11.3 %

so a squared loss spends about forty per cent of its effort on rows that supply about
thirteen per cent of the score. On CYP3A4 73.9 % of the predictions on those rows already
land inside the band: the error is already free and the objective is still pushing on it.
Those rows are also the weakest compounds, which is where a squared loss puts its largest
weights anyway, so the misallocation compounds.

How it is fitted without a new dependency. The dead-zone gradient is

    dL/dp = sign(p - clip(p, lo, hi)),

which is exactly the L1 gradient against the target clip(p, lo, hi). And for any t in the
band, |p - t| >= L(p), with equality at t = clip(p, lo, hi). So L1 against the reprojected
target is a majoriser of the dead-zone loss that is tight at the current prediction:
alternating "reproject, refit" is a majorise-minimise scheme and cannot increase the loss.
The pinned scikit-learn already has `loss="absolute_error"`. No LightGBM, no custom
objective, no touching the version ceiling.

The trap, and why the projection is taken out of fold. If the reprojection used the model's
predictions on its own training rows, an overfitted inner model would place every training
row inside its band, every gradient would be zero and the scheme would collapse into doing
nothing. So each pass projects the *out-of-fold* predictions of the pass before it, which
no model has seen its own row of. That leaves a mild stacking leak -- a training row's
target was influenced by models that saw other folds -- but it can only make the target
easier to predict, and what is scored here is rank against the truth, which an easier
target does not help. Stated rather than hidden.

Arms. Each dead-zone pass is a full cross-validation, so the passes are cumulative and are
reported separately: if pass 2 and pass 3 move nothing, one pass is the whole effect.

Same folds, masks, metric and learner settings as src/ablate.py. Reads data/feats.npz and
data/rows.csv, writes results/preds/oof_dead.json.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from cyppaths import D, RES, tutorial
tutorial()

import argparse
import json
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from evaluation.custom_scoring_functions import rae_soft_threshold_absolute_error as strae

from cypsplit import butina_folds
from shrinkchoice import fit_apply

CYPS = ["CYP1A2", "CYP2C9", "CYP2D6", "CYP3A4"]
KW = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=31,
          l2_regularization=1.0, random_state=0)


def cv(Xi, target, fi, loss):
    """One full cross-validation. `target` is per-row and may differ from the label."""
    p = np.zeros(len(target))
    for f in range(5):
        trn, te = fi != f, fi == f
        if te.sum() == 0:
            continue
        p[te] = HistGradientBoostingRegressor(**KW, loss=loss).fit(
            Xi[trn], target[trn]).predict(Xi[te])
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--passes", type=int, default=3, help="сколько шагов мажорирования")
    ap.add_argument("--out", default=RES + "preds/oof_dead.json")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]

    rows = pd.read_csv(D + "rows.csv")
    tr = (pd.read_csv(D + "cyp-challenge-TRAIN_inhibition.csv")
            .set_index("Molecule_Name").loc[rows.Molecule_Name].reset_index())
    z = np.load(D + "feats.npz")
    X = np.hstack([z["FP"], z["DESC"], z["MECH"]])

    # Сколько строк вообще попадает в мёртвую зону: если почти никто, эффекта не будет.
    print(f"{'фермент':8s} {'медиана полосы':>15s} {'доля шире 1.0':>15s} {'доля шире 2.0':>15s}")
    for c in CYPS:
        col = f"{c}_pIC50_direct_inhibition"
        m = tr[col].notna()
        w = (tr.loc[m, col + "_conf_high"] - tr.loc[m, col + "_conf_low"]).to_numpy()
        print(f"{c:8s} {np.median(w):15.3f} {100*(w > 1.0).mean():14.1f} % {100*(w > 2.0).mean():14.1f} %")
    print()

    out, table = {}, []
    for seed in seeds:
        fold, _ = butina_folds(list(rows.SMILES), seed=seed)

        # Руки строятся по нарастающей: каждый проход мёртвой зоны проецирует
        # честные предсказания предыдущего, поэтому порядок обязателен.
        names = ["L2 по метке", "L1 по метке"] + [f"мёртвая зона x{k}" for k in range(1, a.passes + 1)]
        acc = {nm: {"seed": seed, "рука": nm} for nm in names}
        clock = {nm: 0.0 for nm in names}
        inside = {}

        for c in CYPS:
            col = f"{c}_pIC50_direct_inhibition"
            m = tr[col].notna().to_numpy()
            y = tr.loc[m, col].to_numpy()
            lo = tr.loc[m, col + "_conf_low"].to_numpy()
            hi = tr.loc[m, col + "_conf_high"].to_numpy()
            Xi, fi = X[m], fold[m]

            preds = {}
            t0 = time.time(); preds["L2 по метке"] = cv(Xi, y, fi, "squared_error")
            clock["L2 по метке"] += time.time() - t0
            t0 = time.time(); preds["L1 по метке"] = cv(Xi, y, fi, "absolute_error")
            clock["L1 по метке"] += time.time() - t0

            prev = preds["L1 по метке"]
            for k in range(1, a.passes + 1):
                nm = f"мёртвая зона x{k}"
                t0 = time.time()
                target = np.clip(prev, lo, hi)      # проекция честного OOF на полосу
                prev = cv(Xi, target, fi, "absolute_error")
                preds[nm] = prev
                clock[nm] += time.time() - t0
            # Доля строк, у которых градиент обнулился на первом же шаге.
            inside[c] = float(np.mean((preds["L1 по метке"] >= lo) & (preds["L1 по метке"] <= hi)))

            for nm, p in preds.items():
                q = fit_apply(p, lo, hi, fi, np.ones(len(y)) / len(y))
                out[f"{seed}|{nm}|{c}"] = p.tolist()
                acc[nm][f"{c} пара"] = round(float(strae(y, q, y_true_upper=hi, y_true_lower=lo)), 4)
                acc[nm][f"{c} сырое"] = round(float(strae(y, p, y_true_upper=hi, y_true_lower=lo)), 4)
                acc[nm][f"{c} rho"] = round(float(spearmanr(y, p).statistic), 4)

        for nm in names:
            r = acc[nm]
            for tag in ("пара", "сырое", "rho"):
                r[f"MACRO {tag}"] = round(float(np.mean([r[f"{c} {tag}"] for c in CYPS])), 4)
            table.append(r)
            print(f"  сид {seed} {nm:18s} пара {r['MACRO пара']:.4f} сырое {r['MACRO сырое']:.4f} "
                  f"rho {r['MACRO rho']:.4f}  "
                  + " ".join(f"{c[3:]} {r[f'{c} rho']:.3f}" for c in CYPS)
                  + f"  ({clock[nm]:.0f} с)", flush=True)
        print("  из-под градиента выпало сразу: "
              + " ".join(f"{c[3:]} {100*inside[c]:.0f} %" for c in CYPS), flush=True)

    print()
    df = pd.DataFrame(table)
    print(df.groupby("рука", sort=False)[["MACRO пара", "MACRO сырое", "MACRO rho"]
                                         + [f"{c} rho" for c in CYPS]].mean().to_string())
    json.dump({"table": table, "preds": out}, open(a.out, "w"))
    print(f"\nсохранено: {a.out}")
    print("""
Как читать. Смотреть на rho и на пару, не на сырое: сырое --- это то, что аффинная пара
всё равно перепишет, и именно на нём L1 показала свои -0.0455, которые потом никуда не
дошли (пункт 77).

Ожидание. Мёртвая зона обязана двигать rho, потому что ширина полосы --- поферментная
информация, которой у монотонного преобразования нет. Если rho стоит на месте, а сырое
двигается --- значит мёртвая зона делает ровно то же, что L1, и это ещё один пункт в
пользу того, что ранг здесь берётся только признаками, а не целью.

Прирост обязан быть неравномерным по ферментам: доля широких полос от 9.9 % на 2D6 до
29.4 % на 3A4, так что 3A4 должен выиграть больше всех. Равномерный прирост означал бы,
что работает не мёртвая зона, а просто смена цели на более гладкую.""")


if __name__ == "__main__":
    main()

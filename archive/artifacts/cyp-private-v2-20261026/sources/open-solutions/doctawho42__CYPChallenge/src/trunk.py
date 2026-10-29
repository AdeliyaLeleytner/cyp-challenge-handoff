"""Shared trunk, three heads, and lambda_scr / lambda_ext as the switches.

The question this answers: does bringing the primary screen in as a second likelihood
term - not as an input feature - help the pIC50 head?

Why not as an input feature. The blind test set carries Molecule_Name and SMILES and
nothing else; there is no screening reading for those 750 compounds, and a model that
conditions on one at inference cannot be submitted. src/mech3.py already went down the
neighbouring road, feeding a *predicted* screen in as a column, and measured exactly zero.
A shared latent layer is a different object: the gradient from the log2fc head shapes the
representation, and at inference the screening head is simply not called.

What the channel actually buys, measured before writing any of this: per enzyme the
screen carries a reading for 2570-3090 compounds whose curve was never run, so the
supervision available to the trunk goes up by a factor of 2.1 to 3.4 depending on the
enzyme, 2.76 overall. Note it is not extra *rows* - every one of the 4905 molecules has
at least one pIC50 label - it is extra *columns* for rows already present.

The control is the same architecture with lambda_scr = 0. Both heads exist in both arms,
so the parameter count is identical; with lambda_scr = 0 the screening head simply
receives no gradient and cannot influence the trunk. Weight initialisation is seeded on
(split seed, fold) and not on lambda, so the two arms start from identical weights and the
loss term is the only difference between them.

The third head, `head_ext`, is for a source measured on another instrument entirely: the
external CYP pIC50 labels that src/trunkext.py put in the SCREENING head, displacing the
channel this file was built around. It is a free head, like head_scr in twohead mode, it
takes its own lambda, and with lam_ext = 0 and no external block it is INERT -- run_fold
returns predictions bit for bit identical to those of the two-head file, which is the
condition under which the numbers already published stay published. Inertness is not free;
Net.__init__ says why the head is built last and its generator draws handed back.

Nothing here touches cypsplit.py, results/preds/oof.json or the golden digest.
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
import torch
import torch.nn as nn
from evaluation.custom_scoring_functions import rae_soft_threshold_absolute_error as strae
from scipy.stats import spearmanr

from cypsplit import butina_folds, fold_digest

CYPS = ["CYP1A2", "CYP2C9", "CYP2D6", "CYP3A4"]

# Instrument calibration fitted per enzyme by verify/g1_calib.py. The document's claim is
# that the screen constrains pi *through* this map, not through a free second head: it is
# a fixed monotone saturating function, and knowing where the curve saturates is what
# turns rank into scale. Zero new parameters.
PC0 = 4.305
CAL_E = np.array([0.728, 0.621, 0.867, 0.931], dtype=np.float32)
CAL_H = np.array([1.261, 1.112, 1.243, 1.968], dtype=np.float32)

# Двухсайтовая форма прибора, подогнанная в verify/k52_twosite.py на тех же парных ячейках:
#   I = E [ f/(1 + 10^{h(pC0-pi)}) + (1-f)/(1 + 10^{h(pC0-pi-D)}) ]
# Пункт 178: перекрёстно проверенный остаток улучшается на всех четырёх, но параметры
# различают. На CYP3A4 это настоящая смесь --- доля 0.481 при разделении 0.978, обе величины
# внутренние, остаток падает на 26 %. На CYP2C9 и CYP2D6 разделение УПИРАЕТСЯ В ГРАНИЦУ 3.0,
# то есть второй сигмоид работает переменной-заглушкой для хвоста, а не вторым сайтом.
# Константы внесены как измерены; рука «только 3A4» существует ровно потому, что на двух
# ферментах они не описывают физику.
CAL_F = np.array([0.8641, 0.8554, 0.6725, 0.4813], dtype=np.float32)
CAL_D2 = np.array([1.6739, 3.0000, 3.0000, 0.9781], dtype=np.float32)
CAL_E2 = np.array([0.7211, 0.5864, 0.8638, 0.9288], dtype=np.float32)
CAL_H2 = np.array([1.2635, 1.3984, 0.9518, 1.4735], dtype=np.float32)
TWO_ONLY_3A4 = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

# Сдвиг между слоями измерений, намеренный алгебраически в пункте 171 при ПОДОГНАННОМ E.
# Здесь он ни во что не подаётся --- только печатается рядом с найденным, чтобы сравнение
# двух независимых маршрутов было видно в логе, а не выводилось потом из головы.
ALG_SHIFT = np.array([0.103, -0.081, 0.000, 0.556], dtype=np.float32)

# Chosen on the lambda_scr = 0 arm alone, never looking at an arm with the screening
# term on, so the choice cannot favour the experiment. It moves the absolute level; it
# cannot move the comparison, which is between two arms sharing these settings exactly.
#
# The criterion was stated before searching: get the trunk into the same league as the
# gradient boosting the rest of the repository uses, because a null result on a trunk
# that is far weaker would say nothing about the channel. It reaches macro ST-RAE 0.7672
# against the boosting's 0.7673.
#
# The one non-obvious choice is BLOCKS. On the full FP+DESC+MECH matrix the best this
# trunk managed was 0.7949 - 2048 fingerprint bits against roughly 1400 labelled rows per
# enzyme is more width than an MLP can use, and regularising harder made it worse, not
# better (weight decay 1e-3 gave 0.8264). Dropping the fingerprint and keeping the 247
# descriptor and mechanistic columns recovered the whole gap at once.
BLOCKS = "DESC+MECH"
HIDDEN = 512
DEPTH = 2
DROPOUT = 0.5
LR = 1e-3
WEIGHT_DECAY = 1e-4
EPOCHS = 200
BATCH = 256


def load(blocks="FP+DESC+MECH"):
    """Feature matrix, both target blocks, and their masks, all in rows.csv order.

    `blocks` selects which feature blocks enter the trunk. 2048 fingerprint bits against
    roughly 1400 labelled rows per enzyme is a lot of width for an MLP; the narrower
    DESC+MECH matrix is better conditioned and may be the more sensitive instrument for
    the question actually being asked. Whatever is chosen applies to both arms.
    """
    z = np.load(D + "feats.npz")
    rows = pd.read_csv(D + "rows.csv")
    tr = (pd.read_csv(D + "cyp-challenge-TRAIN_inhibition.csv")
            .set_index("Molecule_Name").loc[rows.Molecule_Name].reset_index())

    # Morgan counts are heavily zero-inflated with a long tail; log1p first so that
    # standardising them afterwards does not hand a few busy bits enormous weight.
    parts = {"FP": np.log1p(z["FP"]), "DESC": z["DESC"], "MECH": z["MECH"]}
    X = np.hstack([parts[b] for b in blocks.split("+")]).astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    sc = pd.read_csv(D + "cyp-challenge-single-concentration-TRAIN.csv")
    piv = sc.pivot_table(index="Molecule_Name", columns="enzyme", values="log2fc_estimate")
    scr = rows.set_index("Molecule_Name").join(piv)[CYPS].to_numpy(np.float32)

    y = np.stack([tr[f"{c}_pIC50_direct_inhibition"].to_numpy(np.float32) for c in CYPS], 1)
    lo = np.stack([tr[f"{c}_pIC50_direct_inhibition_conf_low"].to_numpy(np.float32) for c in CYPS], 1)
    hi = np.stack([tr[f"{c}_pIC50_direct_inhibition_conf_high"].to_numpy(np.float32) for c in CYPS], 1)
    return X, y, lo, hi, scr, list(rows.SMILES)


class Net(nn.Module):
    """Shared trunk, one head per target block. All three heads always exist."""

    def __init__(self, d_in, hidden=None, depth=None, dropout=None, n_out=4):
        hidden = HIDDEN if hidden is None else hidden
        depth = DEPTH if depth is None else depth
        dropout = DROPOUT if dropout is None else dropout
        super().__init__()
        layers, d = [], d_in
        for _ in range(depth):
            layers += [nn.Linear(d, hidden), nn.ReLU(), nn.Dropout(dropout)]
            d = hidden
        self.trunk = nn.Sequential(*layers)
        self.head_pic = nn.Linear(d, n_out)
        self.head_scr = nn.Linear(d, n_out)
        # head_ext is built LAST and the generator wound back to where it stood before it,
        # so the trunk and the two older heads keep the exact weights they had when this
        # file's numbers were published. Winding back is the half that is easy to miss.
        # nn.Linear draws from the CPU generator, and with device="cpu" so does every
        # dropout mask in the training loop below: a head that merely came last would leave
        # the weights alone and still move every prediction, through the masks. Seeding
        # head_ext off its own generator would fix the weights and not the masks. Restoring
        # the state fixes both, and head_ext stays deterministic in (seed, fold) anyway,
        # because it draws from the state it finds here.
        g = torch.get_rng_state()
        self.head_ext = nn.Linear(d, n_out)
        torch.set_rng_state(g)

    def forward(self, x):
        h = self.trunk(x)
        return self.head_pic(h), self.head_scr(h), self.head_ext(h)


def g_of_pi(pi, e_, h_, d_=None, b_=None, two_=None):
    """log2fc predicted from pIC50 through the fitted instrument calibration.

    g(pi) = log2(1 - E / (1 + 10^{h (pC0 - pi - d)})). Differentiable in pi, so the screening
    residual sends gradient back into the same latent the pIC50 head reads - which is what
    "shared latent curve" in the document actually means, as opposed to two free heads
    that are under no obligation to agree about anything.

    `d_` is the per-enzyme offset between the two measurement layers, and it is None for every
    mode that existed before `calshift`, so their arithmetic is unchanged to the bit.

    Why the offset is worth a parameter at all. The `calibrated` mode as built raises rank
    (macro 0.530 to 0.562 at lambda 0.3 on seed 0) and wrecks the metric (0.767 to 0.955, and
    CYP2D6 from 0.963 to 1.630, which is worse than predicting the mean). That is the signature
    of a model forced to distort the potency scale in order to satisfy a screening constraint it
    cannot otherwise meet: with E and h carried in as constants there is no free parameter
    between pi_hat and the reading. One offset per enzyme is the smallest thing that separates
    "match the screen" from "keep pIC50 on scale".

    Item 171 measured what those offsets should be, algebraically and independently of any
    model: +0.103, -0.081, +0.000 and +0.556 under the fitted amplitude. **If the fitted d_e
    lands near those numbers, two unrelated routes agree; if it runs to the bound, the offset is
    absorbing something else and the arm says nothing.** That is the pre-registration, and it is
    the reason d is bounded rather than free -- an unbounded offset can push the predicted
    inhibition into saturation and switch the screening term off altogether, which would look
    like a clean run and mean nothing.
    """
    # The exponent has to be bounded. Unbounded, 10^(h(pC0 - pi)) overflows to inf as soon
    # as the predicted potency wanders far below pC0, and although the forward value stays
    # finite (e/(1+inf) = 0), the gradient through the overflow is nan and the run dies.
    # This is not hypothetical: the noise ladder lost the calibrated arm on split seed 0 at
    # eta = 0.5 and eta = 1 to exactly this. Clamping at +-30 changes nothing that was
    # already finite - 10^30 and inf give the same inhibited fraction to float precision -
    # and only replaces nan gradients with finite ones.
    # Эффективная потенция: b*pi + d. b_=None означает b=1, d_=None означает d=0,
    # поэтому режимы до calshift и сам calshift идут по прежней арифметике.
    eff = pi if b_ is None else b_ * pi
    arg = PC0 - eff if d_ is None else PC0 - eff - d_
    inh = e_ / (1.0 + torch.pow(10.0, torch.clamp(h_ * arg, min=-30.0, max=30.0)))
    if two_ is not None:
        # Второй сайт: та же кривая, сдвинутая на D, смешанная с долей f. Клампы те же и по
        # той же причине --- через переполнение градиент становится nan, и прогон умирает.
        f_, dd_, w_ = two_
        a1 = 1.0 / (1.0 + torch.pow(10.0, torch.clamp(h_ * arg, min=-30.0, max=30.0)))
        a2 = 1.0 / (1.0 + torch.pow(10.0, torch.clamp(h_ * (arg - dd_), min=-30.0, max=30.0)))
        inh2 = e_ * (f_ * a1 + (1.0 - f_) * a2)
        # w_ выбирает, какие ферменты идут по двухсайтовой форме: 1 --- две, 0 --- одна.
        inh = w_ * inh2 + (1.0 - w_) * inh
    return torch.log2(torch.clamp(1.0 - inh, min=1e-3))


def masked_mse(pred, target, mask):
    """Mean squared error over observed cells only; zero if nothing is observed.

    Normalised by the number of observed cells rather than summed, so that lambda_scr
    means the same thing regardless of how dense each block happens to be.
    """
    if mask.sum() == 0:
        return pred.sum() * 0.0
    d = (pred - target)[mask]
    return (d * d).mean()


def masked_mae(pred, target, mask):
    """Mean ABSOLUTE error over observed cells only; zero if nothing is observed.

    Not a cosmetic variant of `masked_mse`: it is a different ESTIMATOR. Squared error
    estimates the conditional mean, absolute error the conditional median, and item 198 is
    the standing reminder of what happens when that distinction is treated as a detail --
    there a booster fitted on `sign(y - s)` with mean-valued leaves was compared against
    Friedman's LAD as though the two were the same thing, and the resulting table looked
    entirely plausible for a day.

    It is here because the dead-zone pass needs the gradient of the metric. The metric is
    L(p) = max(0, lo - p, p - hi), whose derivative is sign(p - clip(p, lo, hi)) -- exactly
    the derivative of |p - t| at t = clip(p, lo, hi). So absolute error against the projected
    target IS the metric's own gradient, and squared error against it is not.

    Normalised by observed cells, identically to `masked_mse`, so that `lambda_scr` keeps
    meaning the same thing when the two are swapped.
    """
    if mask.sum() == 0:
        return pred.sum() * 0.0
    return (pred - target)[mask].abs().mean()


def run_fold(X, y, scr, fold, f, lam, seed, device, mode="twohead", zn=None, eta=0.0,
             target=None, l1=False, ext=None, lam_ext=0.0):
    """Train one fold and return held-out pIC50 predictions in original units.

    `target` and `l1` are the dead-zone pass (item 164, and item 204 for the other four
    members). `target` is the band-projected version of `y`, clip(p_oof, lo, hi), supplied by
    the caller in ORIGINAL pIC50 units; `l1` switches the pIC50 head to absolute error.
    Both default to the previous behaviour, so every existing number is unchanged to the bit.

    THREE THINGS STAY ON `y` AND NOT ON `target`, and each would fail silently:

      the observed-cell mask (`my`) --- it defines which cells are supervised at all;
      the standardisation statistics `ym`, `ys` --- fitted on the LABEL, so that the
        projected target is expressed in the label's units rather than its own;
      the de-standardisation on return --- predictions must come back in label units.

    Projecting in original units and standardising afterwards is equivalent to projecting in
    standardised units, because standardisation is monotone for ys > 0:
    clip((p-ym)/ys, (lo-ym)/ys, (hi-ym)/ys) == (clip(p,lo,hi)-ym)/ys. Original units are used
    because the band arrives in them and two fewer matrices need converting.

    `ext` and `lam_ext` are the third head. `ext` is an (n, 4) block of labels from another
    source, NaN where unobserved, shaped and standardised exactly as `scr` is; `lam_ext`
    weights its masked loss exactly as `lam` weights the screening head's -- the same
    `masked_mse`, normalised by observed cells, so the two lambdas are the same kind of
    number. `ext=None` means the block does not exist, and every line below then reduces to
    the two-block arithmetic bit for bit. Rows that carry ONLY external labels are the
    caller's business, not this function's: appended with fold index -1 they are never held
    out, and their NaN pIC50 gives the primary head no gradient, which is how
    src/trunkext.py already builds them.
    """
    te = fold == f
    trn = ~te

    my = ~np.isnan(y)
    ms = ~np.isnan(scr)
    # A third target block, or none at all. lam_ext without one would be a SILENT zero --
    # masked_mse over an empty mask returns 0, and the arm would run and mean nothing.
    if lam_ext > 0 and ext is None:
        raise SystemExit("lam_ext > 0, а блока ext нет: слагаемое было бы тихим нулём")
    me = np.zeros_like(my) if ext is None else ~np.isnan(ext)

    # Every statistic below is fitted on the training folds only.
    xm = X[trn].mean(0)
    xs = X[trn].std(0)
    xs[xs < 1e-6] = 1.0
    Xn = (X - xm) / xs

    ym = np.zeros(4, np.float32); ys = np.ones(4, np.float32)
    sm = np.zeros(4, np.float32); ss = np.ones(4, np.float32)
    em = np.zeros(4, np.float32); es = np.ones(4, np.float32)
    for e in range(4):
        a = my[:, e] & trn
        if a.sum() > 1:
            ym[e], ys[e] = y[a, e].mean(), max(y[a, e].std(), 1e-6)
        b = ms[:, e] & trn
        if b.sum() > 1:
            sm[e], ss[e] = scr[b, e].mean(), max(scr[b, e].std(), 1e-6)
        c = me[:, e] & trn
        if ext is not None and c.sum() > 1:
            em[e], es[e] = ext[c, e].mean(), max(ext[c, e].std(), 1e-6)
    # Мишень обучения: метка либо её проекция на полосу. ym/ys выше подогнаны по МЕТКЕ и
    # только по обучающим фолдам --- это верно и здесь: проекция выражается в единицах
    # метки, а не в своих собственных.
    yn = (np.nan_to_num(y if target is None else target) - ym) / ys
    sn = (np.nan_to_num(scr) - sm) / ss
    en = np.zeros_like(yn) if ext is None else (np.nan_to_num(ext) - em) / es

    # Degrading the screening channel by a known amount. The division by sqrt(1 + eta^2)
    # is the whole point: without it the noise inflates the target's sd and lambda would
    # silently change meaning, so "less information" would be confounded with "more
    # weight". With it the standardised target keeps sd 1 and only its correlation with
    # pIC50 falls, by exactly 1 / sqrt(1 + eta^2). The noise draw is shared across lambda
    # and across modes, so arms compared at one eta see the same corrupted channel.
    if eta > 0 and zn is not None:
        sn = (sn + eta * zn) / np.sqrt(1.0 + eta * eta)

    t = lambda a: torch.as_tensor(a, device=device)
    Xt, yt, st = t(Xn), t(yn), t(sn)
    myt, mst = t(my), t(ms)
    et, met = t(en), t(me)
    ymt, yst = t(ym), t(ys)
    smt, sst = t(sm), t(ss)
    cal_e, cal_h = t(CAL_E), t(CAL_H)

    # Seeded on (seed, fold) and NOT on lam, so both arms start from the same weights.
    torch.manual_seed(hash((seed, f)) % (2 ** 31))
    net = Net(X.shape[1]).to(device)
    params = list(net.parameters())

    # calfit: the instrument constants become parameters. `calibrated` carries E and h in from
    # section 4, where they were fitted on the compounds that *have* curves -- that is, on the
    # activity-selected third of the matrix -- and then applies them to the whole population.
    # That is the same two-step calibration outside its own population which item 83 used to
    # kill the pseudo-label route, so the objection applies to the fixed-constant arm as much
    # as it did there. Estimating them jointly answers it from inside rather than around it.
    #
    # Both are reparameterised to stay in range: E through a scaled sigmoid, since the depth of
    # suppression is bounded, and h through softplus, since a Hill slope is positive. An
    # unconstrained E can cross 1 and make log2(1 - E/...) undefined, which is a silent nan
    # rather than an error.
    cal_p = None
    cal_d = None
    cal_b = None
    two = None
    if mode in ("caltwo", "caltwo3a4", "caltwoshift"):
        # Константы второго сайта вносятся, а не оцениваются: они подогнаны на МЕТКАХ в
        # k52_twosite, и оценивать их заново внутри модели значило бы дать им подгоняться
        # под pi_hat, что пункты 173 и 175 уже показали как источник путаницы.
        w = TWO_ONLY_3A4 if mode == "caltwo3a4" else np.ones(len(CYPS), dtype=np.float32)
        two = (torch.as_tensor(CAL_F, device=device),
               torch.as_tensor(CAL_D2, device=device),
               torch.as_tensor(w, device=device))
        cal_e = torch.as_tensor(CAL_E2, device=device)
        cal_h = torch.as_tensor(CAL_H2, device=device)
    if mode == "caltwoshift":
        cal_d = torch.nn.Parameter(torch.zeros(len(CYPS), device=device))
        params += [cal_d]
    if mode == "calaff":
        # Аффинная замена постоянному сдвигу: g(a + b*pi) вместо g(pi - d).
        #
        # Зачем. Если pi_hat усажен, то E[pi_hat | pi] = pi_bar + beta*(pi - pi_bar) при
        # beta < 1, а прибор ждёт pi. Ошибка равна (1 - beta)*(pi_bar - pi): она ноль в
        # среднем и растёт ЛИНЕЙНО к краям, поэтому одна константа исправляет её ровно в
        # одной точке. Разделитель 1 (пункт 173) уже показал, что найденный сдвиг зависит
        # от lambda и значит держится за шкалу модели; здесь проверяется, разожмёт ли
        # свободный наклон эту усадку обратно.
        #
        # Предрегистрация. Усадка -> b_e заметно больше единицы. Внешний межанализовый
        # сдвиг -> b_e около единицы, работает только a_e. Разделение жёсткое, потому что
        # два числа на фермент разделяют то, что одно смешивает.
        #
        # b = 1 + tanh(raw) в (0, 2), a = 2*tanh(raw) в (-2, 2), оба нулевых raw дают
        # b = 1 и a = 0, то есть в точке инициализации calaff ТОЖДЕСТВЕН calibrated.
        cal_d = torch.nn.Parameter(torch.zeros(len(CYPS), device=device))
        cal_b = torch.nn.Parameter(torch.zeros(len(CYPS), device=device))
        params += [cal_d, cal_b]
    if mode == "calshift":
        # Инициализация нулём: на первом шаге calshift ТОЖДЕСТВЕН calibrated, поэтому всё,
        # что он выигрывает, выиграно сдвигом, а не другой отправной точкой. Ограничение
        # 2*tanh держит смещение в пределах двух логарифмических единиц --- вчетверо больше
        # самого крупного, который пункт 171 намерил алгебраически (+0.556 на CYP3A4).
        cal_d = torch.nn.Parameter(torch.zeros(len(CYPS), device=device))
        params += [cal_d]
    if mode == "calfit":
        e0 = torch.as_tensor(CAL_E, dtype=torch.float32).clamp(1e-3, 1.499)
        h0 = torch.as_tensor(CAL_H, dtype=torch.float32).clamp(min=1e-3)
        a0 = torch.log(e0 / (1.5 - e0))                 # sigmoid^-1(E / 1.5)
        b0 = torch.log(torch.expm1(h0))                 # softplus^-1(h)
        cal_a = torch.nn.Parameter(a0.clone().to(device))
        cal_b = torch.nn.Parameter(b0.clone().to(device))
        cal_p = (cal_a, cal_b)
        params += [cal_a, cal_b]
    opt = torch.optim.Adam(params, lr=LR, weight_decay=WEIGHT_DECAY)

    idx = np.where(trn)[0]
    g = np.random.default_rng(1000 + seed * 10 + f)
    net.train()
    for _ in range(EPOCHS):
        for b in np.array_split(g.permutation(idx), max(1, len(idx) // BATCH)):
            bt = t(b)
            p, s, xe = net(Xt[bt])
            loss = (masked_mae if l1 else masked_mse)(p, yt[bt], myt[bt])
            if lam > 0:
                if mode == "twohead":
                    loss = loss + lam * masked_mse(s, st[bt], mst[bt])
                else:
                    # One latent: the screening prediction is g(pi_hat), not a free head.
                    # Standardised on the same statistics as the observed screen so that
                    # lambda keeps the same meaning across modes.
                    pi = p * yst + ymt
                    if cal_p is None:
                        e_, h_ = cal_e, cal_h
                    else:
                        e_ = torch.sigmoid(cal_p[0]) * 1.5
                        h_ = torch.nn.functional.softplus(cal_p[1])
                    d_ = None if cal_d is None else 2.0 * torch.tanh(cal_d)
                    b_ = None if cal_b is None else 1.0 + torch.tanh(cal_b)
                    loss = loss + lam * masked_mse(
                        (g_of_pi(pi, e_, h_, d_, b_, two) - smt) / sst, st[bt], mst[bt])
            if lam_ext > 0:
                # A free head, deliberately. An external pIC50 is read on another
                # instrument, so routing it through the Hill curve above -- which describes
                # THIS screen's readout -- would assert a relation nobody measured;
                # src/trunkext.py stayed in twohead mode for that reason. (The curve is not
                # named here on purpose: item 307 counts its call sites.) Same masked_mse as
                # the screening term, so lam_ext and lam weigh comparable things.
                loss = loss + lam_ext * masked_mse(xe, et[bt], met[bt])
            opt.zero_grad(); loss.backward(); opt.step()

    net.eval()
    if cal_p is not None:
        with torch.no_grad():
            e_ = (torch.sigmoid(cal_p[0]) * 1.5).cpu().numpy()
            h_ = torch.nn.functional.softplus(cal_p[1]).cpu().numpy()
        print(f"      калибровка ушла: E " + " ".join(f"{a:.3f}->{b:.3f}"
              for a, b in zip(CAL_E, e_))
              + " | h " + " ".join(f"{a:.3f}->{b:.3f}" for a, b in zip(CAL_H, h_)), flush=True)
    if cal_d is not None:
        with torch.no_grad():
            dd = (2.0 * torch.tanh(cal_d)).cpu().numpy()
            bb = None if cal_b is None else (1.0 + torch.tanh(cal_b)).cpu().numpy()
        if bb is None:
            print("      сдвиг найден: "
                  + " ".join(f"{c[3:]} {v:+.3f}" for c, v in zip(CYPS, dd))
                  + " | алгебраически (пункт 171): "
                  + " ".join(f"{v:+.3f}" for v in ALG_SHIFT), flush=True)
        else:
            print("      аффинно: " + " ".join(f"{c[3:]} a{v:+.3f} b{w:.3f}"
                                               for c, v, w in zip(CYPS, dd, bb)),
                  flush=True)
    with torch.no_grad():
        p, _, _ = net(Xt[t(np.where(te)[0])])
    return p.cpu().numpy() * ys + ym


def fit_predict_test(FP_te, DESC_te, MECH_te, lam=3.0, seed=0, mode="twohead",
                     blocks=None, device="cpu", dead=""):
    """Train on the whole training set and predict the blinded test rows.

    Item 120 measured the trunk as a fifth ensemble member at -0.0061 of pair and +0.0054 of
    rank, four seeds out of four on every enzyme, which is more than twice what the ridge
    contributes and the only member that helps all four. Acting on that needs the trunk applied
    to the 750 test structures, and this is that path.

    Nothing about the fitting is new. The test rows are appended with their own fold index and
    with NaN in both target blocks, so `masked_mse` gives them no gradient and every statistic
    `run_fold` computes -- the feature standardisation included -- is still taken over training
    rows alone. `run_fold` itself is called unchanged, which is what makes the regression check
    below possible.

    The one thing a caller must not get wrong: `load()` puts the fingerprint block through
    log1p before standardising, and `src/submit.py` does not. The transform is applied here so
    that a caller passing raw counts, as submit.py builds them, gets the right matrix.
    """
    blocks = blocks or BLOCKS
    X, y, lo, hi, scr, smiles = load(blocks)
    parts_te = {"FP": np.log1p(np.asarray(FP_te, np.float32)),
                "DESC": np.asarray(DESC_te, np.float32),
                "MECH": np.asarray(MECH_te, np.float32)}
    Xte = np.hstack([parts_te[b] for b in blocks.split("+")]).astype(np.float32)
    Xte = np.nan_to_num(Xte, nan=0.0, posinf=0.0, neginf=0.0)
    if Xte.shape[1] != X.shape[1]:
        raise SystemExit(f"ширина не совпала: обучение {X.shape[1]}, тест {Xte.shape[1]}")

    n_tr, n_te = len(X), len(Xte)
    Xa = np.vstack([X, Xte])
    ya = np.vstack([y, np.full((n_te, 4), np.nan, np.float32)])
    sa = np.vstack([scr, np.full((n_te, 4), np.nan, np.float32)])
    fold = np.concatenate([np.zeros(n_tr, int), np.ones(n_te, int)])

    tgt = None
    if dead:
        # Проход мёртвой зоны на тестовом пути. Мишень --- проекция ЧЕСТНЫХ предсказаний
        # вне фолда, взятых из `dead`, на полосу; тестовые строки получают NaN и потому не
        # дают градиента, как и их метки. Обучающие фолды здесь все, так как отложен тест.
        J = json.load(open(dead))
        T = J.get("preds", J)
        key = f"{mode}|{seed}|{lam}"
        if key not in T:
            raise SystemExit(f"нет ключа {key} в {dead}")
        A = np.asarray(T[key], float)
        if A.shape != y.shape:
            raise SystemExit(f"форма {A.shape} против {y.shape} в {dead}")
        if not np.array_equal(np.isnan(A), np.isnan(y)):
            raise SystemExit(f"маска NaN в {dead} не совпадает с маской меток")
        rec = (J.get("meta") or {}).get("fold_digests") or {}
        d = fold_digest(butina_folds(smiles, seed=seed)[0])
        if str(seed) in rec and rec[str(seed)] != d:
            raise SystemExit(f"сид {seed}: дайджест {d}, а {dead} посчитан на {rec[str(seed)]}")
        if str(seed) not in rec:
            raise SystemExit(f"в {dead} нет записанных дайджестов фолдов; перезапустите trunk.py")
        # astype обязателен: np.clip даёт float64, MPS его не берёт.
        tgt = np.vstack([np.clip(A, lo, hi).astype(y.dtype),
                         np.full((n_te, 4), np.nan, np.float32)])
    return run_fold(Xa, ya, sa, fold, 1, lam, seed, device, mode=mode,
                    target=tgt, l1=bool(dead))


def check_test_path(seed=0, lam=3.0, mode="twohead", blocks=None, device="cpu"):
    """The test path must be `run_fold` and nothing else. Prove it rather than assert it.

    Holding out fold 1 through the ordinary route and through the appended-rows route has to
    give identical numbers: same weight seed (both use f = 1), same batching seed, same
    standardisation over the complement of fold 1. Any difference means the appended rows are
    reaching a statistic they should not.
    """
    blocks = blocks or BLOCKS
    X, y, lo, hi, scr, smiles = load(blocks)
    fold, _ = butina_folds(smiles, seed=seed)
    direct = run_fold(X, y, scr, fold, 1, lam, seed, device, mode=mode)

    keep = fold != 1
    Xa = np.vstack([X[keep], X[~keep]])
    ya = np.vstack([y[keep], np.full((int((~keep).sum()), 4), np.nan, np.float32)])
    sa = np.vstack([scr[keep], np.full((int((~keep).sum()), 4), np.nan, np.float32)])
    fa = np.concatenate([np.zeros(int(keep.sum()), int), np.ones(int((~keep).sum()), int)])
    viaappend = run_fold(Xa, ya, sa, fa, 1, lam, seed, device, mode=mode)

    d = float(np.max(np.abs(direct - viaappend)))
    print(f"фолд 1, сид {seed}, lam {lam}: максимум |разности| между обычным путём и "
          f"путём с дописанными строками = {d:.3e}")
    print("совпало побитово" if d == 0.0 else
          "НЕ совпало --- дописанные строки куда-то дотягиваются, путь на тест использовать нельзя")
    return d


def evaluate(y, lo, hi, pred):
    """ST-RAE and Spearman per enzyme plus macro, over observed cells."""
    out = {}
    for e, c in enumerate(CYPS):
        m = ~np.isnan(y[:, e])
        out[c] = round(float(strae(y[m, e], pred[m, e],
                                   y_true_upper=hi[m, e], y_true_lower=lo[m, e])), 4)
        out["rho_" + c] = round(float(spearmanr(pred[m, e], y[m, e]).statistic), 3)
    out["MACRO"] = round(float(np.mean([out[c] for c in CYPS])), 4)
    out["MACRO_rho"] = round(float(np.mean([out["rho_" + c] for c in CYPS])), 3)
    return out


def main():
    global HIDDEN, DEPTH, DROPOUT, EPOCHS, WEIGHT_DECAY
    ap = argparse.ArgumentParser()
    ap.add_argument("--lams", default="0,1.0", help="lambda_scr values, comma separated")
    ap.add_argument("--seeds", default="0", help="split seeds, comma separated")
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--out", default=None, help="по умолчанию preds/trunk_<mode>.json")
    ap.add_argument("--hidden", type=int, default=HIDDEN)
    ap.add_argument("--depth", type=int, default=DEPTH)
    ap.add_argument("--dropout", type=float, default=DROPOUT)
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--wd", type=float, default=WEIGHT_DECAY)
    ap.add_argument("--blocks", default=BLOCKS)
    ap.add_argument("--swap-cal", default="",
                    help="обменять (E, h) между двумя ферментами, например CYP2D6,CYP3A4 - "
                         "единственное вмешательство, которое двигает карту прибора, "
                         "оставляя данные, метки, полосы, разбиение и информативность теми же")
    ap.add_argument("--dead", default="",
                    help="проход мёртвой зоны: путь к файлу предсказаний ВНЕ ФОЛДА, которые "
                         "будут спроецированы на полосу и станут мишенью, плюс absolute_error "
                         "на голове pIC50. Обычно results/preds/trunk_twohead.json. Ключ "
                         "строится из ТЕКУЩИХ mode|seed|lam цикла, а не из константы: чужой "
                         "сид сделал бы мишень не-вне-фолда и схема выродилась бы в тождество.")
    ap.add_argument("--noise", type=float, default=0.0,
                    help="eta: порча скринингового канала в его же ско, ранг падает в "
                         "sqrt(1+eta^2) раз, масштаб сохраняется")
    ap.add_argument("--mode", default="twohead",
                    choices=["twohead", "calibrated", "calfit", "calshift", "calaff",
                             "caltwo", "caltwo3a4", "caltwoshift"],
                    help="twohead: free second head. calibrated: screen via g(pi) with the "
                         "instrument constants held fixed. calfit: the same g(pi), but E and h "
                         "are estimated jointly with the model instead of being carried in "
                         "from section 4")
    ap.add_argument("--check-test-path", action="store_true",
                    help="проверить, что путь на тест --- это тот же run_fold, и выйти")
    a = ap.parse_args()

    if a.check_test_path:
        HIDDEN, DEPTH, DROPOUT = a.hidden, a.depth, a.dropout
        EPOCHS, WEIGHT_DECAY = a.epochs, a.wd
        for seed in [int(x) for x in a.seeds.split(",")]:
            check_test_path(seed=seed, lam=float(a.lams.split(",")[-1]),
                            mode=a.mode, blocks=a.blocks, device=a.device)
        return

    HIDDEN, DEPTH, DROPOUT = a.hidden, a.depth, a.dropout
    EPOCHS, WEIGHT_DECAY = a.epochs, a.wd
    # Swapping the instrument map between two enzymes. lambda = 0 does not touch g_of_pi at
    # all, so that arm is unaffected by construction and serves as the leak check.
    global CAL_E, CAL_H
    swap = ""
    if a.swap_cal:
        u, v = [CYPS.index(x.strip()) for x in a.swap_cal.split(",")]
        CAL_E = CAL_E.copy(); CAL_H = CAL_H.copy()
        CAL_E[[u, v]] = CAL_E[[v, u]]
        CAL_H[[u, v]] = CAL_H[[v, u]]
        swap = f"_swap{CYPS[u][3:]}-{CYPS[v][3:]}"
        print(f"карта прибора обменяна: {CYPS[u]} <-> {CYPS[v]}; "
              f"E {CAL_E.tolist()}, h {CAL_H.tolist()}", flush=True)

    if a.out is None:
        tag = ("" if a.noise == 0 else f"_noise{a.noise:g}") + swap \
              + ("_dead" if a.dead else "")
        a.out = RES + f"preds/trunk_{a.mode}{tag}.json"
    lams = [float(v) for v in a.lams.split(",")]
    seeds = [int(v) for v in a.seeds.split(",")]
    X, y, lo, hi, scr, smiles = load(a.blocks)
    print(f"X {X.shape} ({a.blocks}) | устройство {a.device}", flush=True)

    dead = None
    if a.dead:
        dead = json.load(open(a.dead))
        dead = dead.get("preds", dead)
        meta = json.load(open(a.dead)).get("meta", {}) if a.dead else {}
        print(f"мёртвая зона: мишень из {a.dead}"
              + (f" (посчитан на {meta.get('device')}, torch {meta.get('torch')})"
                 if meta else ""), flush=True)
        if meta.get("device") and meta["device"] != a.device:
            # Не педантизм: проекция берётся у предсказаний, посчитанных на другом
            # вычислителе, и если он даёт другие числа, мишень построена не той моделью,
            # которую мы перепроецируем. Тот же довод, что в submit._trunk_device.
            print(f"  ВНИМАНИЕ: файл посчитан на {meta['device']}, а считаем на {a.device}",
                  flush=True)

    saved, table = {}, []
    digests = {}
    for seed in seeds:
        fold, n_cl = butina_folds(smiles, seed=seed)
        # Дайджест фолдов пишется В ФАЙЛ по каждому сиду. Раньше потребитель мог
        # сверяться только с золотой константой сида 0, поэтому на прочих сидах
        # сторожа не было вовсе. Записанный дайджест делает проверку данными.
        digests[str(seed)] = fold_digest(fold)
        # One draw per split seed, reused at every eta and in both modes: the ladder is
        # nested rather than independent, which takes the noise draw out of the comparison.
        zn = np.random.default_rng(90000 + seed).standard_normal(scr.shape).astype(np.float32)
        if dead is not None and seed == 0:
            # Сторож на фолды. Мишень честна только если файл-источник посчитан на ЭТИХ
            # фолдах; иначе его предсказания видели строки, которые здесь отложены, и
            # проход становится дистилляцией собственных ответов. Золотое значение то же,
            # что пинит tests/test_split.py и проверяет submit._oof_trunk.
            d = fold_digest(fold)
            if d != "2d93c19815e14261":
                raise SystemExit(f"дайджест фолдов {d}, ожидался 2d93c19815e14261: "
                                 f"сплит сдвинулся, мишень мёртвой зоны больше не вне фолда")
        for lam in lams:
            t0 = time.time()
            tgt = None
            if dead is not None:
                key = f"{a.mode}|{seed}|{lam}"
                if key not in dead:
                    raise SystemExit(f"нет ключа {key} в {a.dead}; "
                                     f"есть: {sorted(dead)[:8]}")
                A = np.asarray(dead[key], float)
                if A.shape != y.shape:
                    raise SystemExit(f"форма {A.shape} против {y.shape}: файл посчитан на "
                                     f"другом порядке строк или другой сборке признаков")
                if not np.array_equal(np.isnan(A), np.isnan(y)):
                    raise SystemExit("маска NaN источника не совпадает с маской меток")
                # Проекция в ИСХОДНОЙ шкале pIC50: полоса задана в ней, а нормировка
                # происходит внутри run_fold по статистикам, подогнанным по МЕТКЕ.
                # np.clip сохраняет NaN, поэтому маска мишени бит в бит равна маске меток.
                # astype обязателен: np.clip возвращает float64, а MPS float64 не берёт
                # и падает уже внутри run_fold, далеко от места ошибки.
                tgt = np.clip(A, lo, hi).astype(y.dtype)
                # Доля считается ПО НАБЛЮДАЕМЫМ ячейкам: в матрице 4905x4 меток только
                # 6525 из 19620, и деление на все ячейки занизило бы её втрое.
                obs = ~np.isnan(y)
                ins = ((A >= lo) & (A <= hi))[obs]
                print(f"  мишень {key}: уже внутри полосы {ins.mean():.1%}, "
                      f"на краю {1-ins.mean():.1%} (по {int(obs.sum())} наблюдаемым)",
                      flush=True)
                for e, c in enumerate(CYPS):
                    o = obs[:, e]
                    print(f"      {c} {((A[:, e] >= lo[:, e]) & (A[:, e] <= hi[:, e]))[o].mean():.1%}",
                          flush=True)
            pred = np.full_like(y, np.nan)
            for f in range(5):
                te = fold == f
                if te.sum() == 0:
                    continue
                pred[te] = run_fold(X, y, scr, fold, f, lam, seed, a.device, a.mode,
                                    zn=zn, eta=a.noise,
                                    target=tgt, l1=dead is not None)
            r = evaluate(y, lo, hi, pred)
            r["seed"], r["lambda"], r["mode"], r["noise"] = seed, lam, a.mode, a.noise
            table.append(r)
            saved[f"{a.mode}|{seed}|{lam}"] = np.where(np.isnan(y), np.nan, pred).tolist()
            print(f"  [{a.mode}] сид {seed} lambda {lam:<4} макро {r['MACRO']:.4f} "
                  f"rho {r['MACRO_rho']:.3f}  ({time.time()-t0:.0f} с)", flush=True)

    df = pd.DataFrame(table)[["seed", "lambda", *CYPS, "MACRO",
                              *[f"rho_{c}" for c in CYPS], "MACRO_rho"]]
    print()
    print(df.to_string(index=False))
    meta = {"mode": a.mode, "blocks": a.blocks, "hidden": a.hidden, "depth": a.depth,
            "dropout": a.dropout, "epochs": a.epochs, "wd": a.wd, "lr": LR, "batch": BATCH,
            "seeds": seeds, "lams": lams, "noise": a.noise, "swap_cal": a.swap_cal,
            "device": a.device,
            "pc0": PC0, "cal_e": CAL_E.tolist(), "cal_h": CAL_H.tolist(),
            "torch": torch.__version__, "numpy": np.__version__}
    meta["fold_digests"] = digests
    json.dump({"table": table, "preds": saved, "meta": meta}, open(a.out, "w"))
    print(f"\nсохранено: {a.out}")


if __name__ == "__main__":
    main()

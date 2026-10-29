"""The cross-validation split. One definition, used by every script that needs folds.

Butina clustering over Morgan fingerprints at a Tanimoto distance threshold of 0.35; a
cluster goes into a single fold as a whole, so no close analogue of a held-out compound
sits in the training half.

This recipe used to be pasted into twelve scripts. Numbers printed by different scripts
are comparable only when their folds agree element for element, and twelve copies cannot
be kept in agreement by hand. `tests/test_split.py` pins the canonical fold vector to a
golden digest, so an accidental change fails loudly instead of silently invalidating
every comparison in the document.

The copies were never quite identical, and the differences are preserved here rather
than papered over, because changing them would change published numbers:

  * ablate, base, decision, range, rangectl, tdibase, tdiprob, f3_seeds, f12_cvhard
    cluster at fp_size=2048 - the canonical split;
  * mech2, mech3, mech4 cluster at fp_size=1024, so their folds have never matched the
    ablation table. Each of those scripts only compares models against each other on its
    own folds, which is internally sound, but their numbers are not comparable to
    ablate.py's;
  * tdibase and tdiprob cluster the TDI subset (rows.SMILES[keep]), a different molecule
    set, so different folds are correct there.

Seed 0 is the split every reported number uses. verify/f3_seeds.py deliberately passes
1, 2, 3 to measure how much the split alone moves the answer.
"""
import hashlib

import numpy as np
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from rdkit.ML.Cluster import Butina

from cyppaths import DATA

RDLogger.DisableLog("rdApp.*")

THRESHOLD = 0.35
N_FOLDS = 5
SEED = 0
FP_RADIUS = 2
FP_SIZE = 2048


def fingerprints(smiles, fp_size=FP_SIZE):
    """Bit fingerprints at the clustering settings.

    These are the fingerprints the split is built on, not the count features the models
    train on. verify/f12_cvhard.py also needs them for nearest-neighbour similarity.
    """
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=FP_RADIUS, fpSize=fp_size)
    return [gen.GetFingerprint(Chem.MolFromSmiles(s)) for s in smiles]


def _key(smiles, threshold, fp_size):
    payload = "\n".join(smiles) + f"|{threshold}|{FP_RADIUS}|{fp_size}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def cluster_ids(smiles, threshold=THRESHOLD, fp_size=FP_SIZE, cache=True):
    """Butina cluster index per molecule, in the order the SMILES were given.

    Returns (cluster_id, n_clusters). This is the expensive half - O(n^2) Tanimoto
    comparisons - and it is fully deterministic, so it is cached under data/. The cache
    key covers the SMILES themselves and every parameter, which makes a stale hit
    impossible rather than merely unlikely.

    Callers that reuse their own Generator after drawing folds (src/mech3.py draws a
    nested inner split from the same advanced generator) must call this and keep their
    own draw, not butina_folds, or the generator state changes and the numbers move.
    """
    path = DATA / f"clusters_{_key(smiles, threshold, fp_size)}.npz"
    if cache and path.exists():
        z = np.load(path)
        return z["cid"], int(z["n_clusters"])

    bits = fingerprints(smiles, fp_size)
    dists = []
    for i in range(1, len(bits)):
        dists.extend([1 - x for x in DataStructs.BulkTanimotoSimilarity(bits[i], bits[:i])])
    clusters = Butina.ClusterData(dists, len(bits), threshold, isDistData=True)
    cid = np.zeros(len(bits), int)
    for k, c in enumerate(clusters):
        for i in c:
            cid[i] = k
    if cache:
        np.savez_compressed(path, cid=cid, n_clusters=len(clusters))
    return cid, len(clusters)


def butina_folds(smiles, seed=SEED, n_folds=N_FOLDS, threshold=THRESHOLD,
                 fp_size=FP_SIZE, cache=True):
    """Fold index per molecule. Returns (fold, n_clusters)."""
    cid, n_clusters = cluster_ids(smiles, threshold, fp_size, cache)
    fold = np.random.default_rng(seed).integers(0, n_folds, n_clusters)[cid]
    return fold, n_clusters


def fold_digest(fold):
    """Short stable digest of a fold vector, for the golden-value test."""
    return hashlib.sha256(np.asarray(fold, dtype=np.int64).tobytes()).hexdigest()[:16]

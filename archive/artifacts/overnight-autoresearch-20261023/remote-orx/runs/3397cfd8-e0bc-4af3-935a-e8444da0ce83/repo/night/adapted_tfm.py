"""TabPFN over the frozen encoder of the exact, clean, own neural fitting fold.

Only root's committed ORX run may execute real feature extraction or fitting.
There are no downloads and no fallback to inherited CYP-adapted checkpoints.
Required pins: parent_trial_dir, parent_checkpoint_sha256, parent_metadata_sha256.
Required identity: cohort, fold_index, seed (base seed, before adding the fold).
Only MP -> aggregation -> BatchNorm fingerprints are supported, not FFN latents.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .features import molecule_ids, verified_file
from .public_data import _digest, normalize_parent_key
from .reference import CANONICAL

FOUNDATION_SHA256 = "c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651"
CHEMPROP_VERSION = "2.2.1"


def _ids_hash(ids):
    return hashlib.sha256(("\n".join(map(str, ids)) + "\n").encode()).hexdigest()


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _read_ids(path):
    return molecule_ids(pd.read_csv(path, dtype={"Molecule_Name": str}))


def validate_parent(config, train_df, query_df, asset_root, validation_df):
    """Read-only provenance/identity validation, with no torch load or inference."""
    cfg = dict(config)
    root = Path(asset_root)
    for key in ["parent_trial_dir", "parent_checkpoint_sha256", "parent_metadata_sha256", "cohort", "fold_index", "seed"]:
        if key not in cfg:
            raise ValueError(f"Adapted TFM requires config.{key}")
    if cfg.get("encoder_stage", "fingerprint") != "fingerprint":
        raise ValueError("Only MP+aggregation+BN fingerprint is supported; FFN latent extraction is not implemented")
    if validation_df is None or validation_df.empty:
        raise ValueError("Exact parent fold validation rows are required for provenance checks")
    supplied, query, validation = (molecule_ids(f) for f in [train_df, query_df, validation_df])
    if not supplied or not query or set(supplied) & set(query) or set(supplied) & set(validation):
        raise ValueError("Nonempty disjoint fitting/query/validation ID sets are required")
    parent = Path(cfg["parent_trial_dir"]).resolve()
    metadata_path = verified_file(parent / "trial_metadata.json", cfg["parent_metadata_sha256"], root)
    metadata = json.loads(metadata_path.read_text())
    job_path = parent / "job.json"
    if cfg.get("parent_job_sha256"):
        verified_file(job_path, cfg["parent_job_sha256"], root)
    job = json.loads(job_path.read_text())
    complete = json.loads((parent / "complete.json").read_text())
    if complete.get("status") != "complete" or not (parent / "worker_done.json").is_file():
        raise ValueError("Parent neural worker has not completed")
    effective = metadata["effective_config"]
    base_seed, fold = int(cfg["seed"]), int(cfg["fold_index"])
    if (job.get("cohort") != cfg["cohort"] or int(job.get("fold", -1)) != fold
            or int(job.get("config", {}).get("seed", -1)) != base_seed
            or int(effective.get("seed", -1)) != base_seed
            or int(effective.get("fold_index", -1)) != fold
            or int(metadata.get("seed", -1)) != base_seed + fold):
        raise ValueError("Parent cohort/fold/base seed/effective seed does not match this child")
    if job.get("config", {}).get("kind") != "neural":
        raise ValueError("Parent job is not a neural trial")
    if effective.get("component") != "official_aux":
        raise ValueError("Initial clean adapted-TFM protocol supports own official_aux parents only")
    if metadata.get("packages", {}).get("chemprop") != CHEMPROP_VERSION:
        raise ValueError("Parent checkpoint must use Chemprop2.2.1")
    initialization = metadata["initialization"]
    if initialization.get("initialization") == "chemeleon":
        if initialization.get("checkpoint_sha256") != FOUNDATION_SHA256:
            raise ValueError("Parent was initialized from an unapproved/unknown adapted encoder")
    elif initialization.get("initialization") != "scratch":
        raise ValueError("Parent initialization provenance is unsupported")

    cohorts_path = root / "cohorts.json"
    cohorts = json.loads(cohorts_path.read_text())
    cohort = cohorts["cohorts"][cfg["cohort"]]
    expected = cohort["inner_folds"][fold]
    if supplied != list(map(str, expected["train_ids"])) or validation != list(map(str, expected["val_ids"])):
        raise ValueError("Supplied official train/validation rows differ from the frozen cohort fold")
    expected_query = list(map(str, expected["val_ids"] + cohort["test_ids"]))
    if query != expected_query:
        raise ValueError("Child query IDs/order differ from the parent fold validation+outer query contract")
    fit_ids = _read_ids(parent / "fit_ids.csv")
    parent_val_ids = _read_ids(parent / "validation_ids.csv")
    if not set(supplied) <= set(fit_ids) or set(query) & set(fit_ids):
        raise ValueError("Parent gradient-fitting IDs omit supplied training rows or overlap query/outer IDs")
    if not parent_val_ids or not set(parent_val_ids) <= set(validation):
        raise ValueError("Parent epoch-selection IDs include rows outside this validation fold")
    for key, ids in [("supplied_train_id_sha256", supplied), ("fit_id_sha256", fit_ids),
                     ("validation_id_sha256", parent_val_ids), ("query_id_sha256", query)]:
        if metadata.get(key) != _ids_hash(ids):
            raise ValueError(f"Parent {key} does not match its source IDs")
    pred_path = parent / "predictions.csv"
    if _read_ids(pred_path) != query:
        raise ValueError("Parent persisted predictions do not match this query order")

    official = pd.read_csv(root / "official-train.csv")
    official_test = pd.read_csv(root / "official-test.csv", usecols=["Molecule_Name", "SMILES"])
    official_ids, test_ids = molecule_ids(official), molecule_ids(official_test)
    if set(fit_ids) & (set(official_ids) | set(test_ids)) != set(supplied):
        raise ValueError("Parent fitting set includes other official fold/test molecules")
    lookup = official.assign(Molecule_Name=official_ids).set_index("Molecule_Name")
    qlookup = pd.concat([official[["Molecule_Name", "SMILES"]], official_test], ignore_index=True)
    qlookup["Molecule_Name"] = qlookup.Molecule_Name.astype(str)
    if qlookup.Molecule_Name.duplicated().any():
        raise ValueError("Official train/test IDs overlap")
    qlookup = qlookup.set_index("Molecule_Name")
    for frame, ids in [(train_df, supplied), (query_df, query), (validation_df, validation)]:
        if frame.SMILES.tolist() != qlookup.loc[ids, "SMILES"].tolist():
            raise ValueError("Supplied SMILES differ from immutable official row identities")
    # Ensure the TabPFN fit labels are precisely the staged official primary labels.
    for target in CANONICAL:
        if target not in train_df or not np.allclose(train_df[target].to_numpy(float),
                lookup.loc[supplied, target].to_numpy(float), equal_nan=True, rtol=0, atol=0):
            raise ValueError("Child official primary labels differ from staged official TRAIN")
    parents = [normalize_parent_key(s) for s in pd.concat([official.SMILES, official_test.SMILES])]
    if any(p is None for p in parents):
        raise ValueError("Official parent normalization failed")
    excluded = set(cohorts["excluded_parent_keys"])
    if not set(parents) <= excluded:
        raise ValueError("Cohort exclusions omit official parent structures")
    for left, right in [(supplied, validation), (supplied, list(map(str, cohort["test_ids"])) )]:
        if ({normalize_parent_key(s) for s in lookup.loc[left, "SMILES"]}
                & {normalize_parent_key(s) for s in lookup.loc[right, "SMILES"]}):
            raise ValueError("Parent fitting/validation or outer normalized structures overlap")
    extra = metadata.get("component", {}).get("extra_public")
    public_provenance = None
    if effective.get("extra_public_sources"):
        if not extra:
            raise ValueError("Parent extra-public provenance is absent")
        expected_exclusion_hash = hashlib.sha256("\n".join(sorted(excluded)).encode()).hexdigest()
        if extra["assembly"].get("excluded_parent_sha256") != expected_exclusion_hash:
            raise ValueError("Parent public data did not use the exact all-official exclusion set")
        folder = root / effective.get("extra_public_dir", "new_public")
        table = verified_file(folder / "measurements.csv", extra["table_sha256"], root)
        if effective.get("extra_public_sha256") != extra["table_sha256"]:
            raise ValueError("Parent public table pin and assembly provenance disagree")
        public_provenance = {"table_sha256": _digest(table), "sources": extra["sources"],
                             "excluded_parent_sha256": expected_exclusion_hash}
    elif set(fit_ids) != set(supplied):
        raise ValueError("Unexpected additional gradient-fitting IDs without audited public-source provenance")
    checkpoint = Path(cfg.get("parent_checkpoint_path", metadata["best_checkpoint"]))
    checkpoint = checkpoint if checkpoint.is_absolute() else parent / checkpoint
    checkpoint = checkpoint.resolve()
    if not checkpoint.is_relative_to(parent):
        raise ValueError("Parent checkpoint must live inside its own trial directory")
    verified_file(checkpoint, cfg["parent_checkpoint_sha256"], root)
    if int(complete["best_epoch"]) != int(metadata["best_epoch"]):
        raise ValueError("Parent completion and best-epoch metadata disagree")
    source_files = metadata.get("component", {}).get("source_files", {})
    reference_dirs = ([Path(effective["reference_data_dir"])] if effective.get("reference_data_dir") else
                      [root / "reference/public_data", root / "reference_audit/public_data"])
    for filename, expected_hash in source_files.items():
        candidates = [directory / filename for directory in reference_dirs if (directory / filename).is_file()]
        if not candidates or not any(_digest(path) == expected_hash for path in candidates):
            raise ValueError(f"Parent reference source missing or hash-mismatched: {filename}")
    provenance = {"parent_trial_dir": str(parent), "checkpoint": str(checkpoint),
                  "checkpoint_sha256": cfg["parent_checkpoint_sha256"],
                  "metadata_sha256": _digest(metadata_path), "job_sha256": _digest(job_path),
                  "complete_sha256": _digest(parent / "complete.json"),
                  "worker_done_sha256": _digest(parent / "worker_done.json"),
                  "parent_predictions_sha256": _digest(pred_path),
                  "cohorts_sha256": _digest(cohorts_path),
                  "official_train_sha256": _digest(root / "official-train.csv"),
                  "official_test_sha256": _digest(root / "official-test.csv"),
                  "parent_effective_config": effective,
                  "parent_effective_config_sha256": hashlib.sha256(json.dumps(effective, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                  "initialization": initialization,
                  "public_source": public_provenance, "reference_source_hashes": source_files,
                  "supplied_train_ids_sha256": _ids_hash(supplied), "parent_fit_ids_sha256": _ids_hash(fit_ids),
                  "parent_validation_ids_sha256": _ids_hash(parent_val_ids), "query_ids_sha256": _ids_hash(query),
                  "cohort": cfg["cohort"], "fold_index": fold, "base_seed": base_seed,
                  "parent_effective_seed": base_seed + fold,
                  "parent_fit_rows": len(fit_ids), "official_child_fit_rows": len(supplied),
                  "best_epoch": int(metadata["best_epoch"]),
                  "known_caveat": "Parent neural epoch was chosen using this inner validation fold. Its OOF predictions and encoder are not independent of epoch selection; outer query labels remain unused."}
    return checkpoint, metadata, provenance


def load_encoder(checkpoint, metadata, device):
    """Reconstruct only encoder modules; supports ordinary and interval parent state dicts."""
    import torch
    from chemprop import nn
    if importlib.metadata.version("chemprop") != CHEMPROP_VERSION:
        raise ValueError("This audited encoder adapter requires Chemprop2.2.1")
    # Own checkpoint is pinned and identity-checked before this function is called.
    try:
        saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
    except Exception as error:
        raise ValueError("Unsupported own checkpoint serialization; no alternate checkpoint fallback") from error
    if int(saved.get("epoch", -1)) != metadata["best_epoch"]:
        raise ValueError("Checkpoint epoch differs from pinned parent metadata")
    hyper = saved["hyper_parameters"]
    if hyper.get("X_d_transform") is not None:
        raise ValueError("Additional global descriptors are not supported by fingerprint-only adapter")
    mp_args = dict(hyper["message_passing"])
    if mp_args.pop("cls", None) is not nn.BondMessagePassing or mp_args.get("d_vd") is not None:
        raise ValueError("Only default-feature BondMessagePassing without extra atom descriptors is supported")
    agg_args = dict(hyper["agg"])
    agg_class = agg_args.pop("cls", None)
    allowed = {"mean": nn.MeanAggregation, "sum": nn.SumAggregation, "norm": nn.NormAggregation}
    effective = metadata["effective_config"]
    if agg_class is not allowed.get(effective["aggregation"]):
        raise ValueError("Checkpoint aggregation does not match parent config")
    if bool(hyper["batch_norm"]) != bool(effective["batch_norm"]):
        raise ValueError("Checkpoint BatchNorm setting does not match parent config")

    class Encoder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.message_passing = nn.BondMessagePassing(**mp_args)
            self.agg = agg_class(**agg_args)
            self.bn = torch.nn.BatchNorm1d(self.message_passing.output_dim) if hyper["batch_norm"] else torch.nn.Identity()

        def forward(self, bmg, descriptors=None):
            return self.bn(self.agg(self.message_passing(bmg, descriptors), bmg.batch))

    encoder = Encoder()
    state = {k: v for k, v in saved["state_dict"].items() if k.startswith(("message_passing.", "agg.", "bn."))}
    encoder.load_state_dict(state, strict=True)
    for parameter in encoder.parameters():
        parameter.requires_grad_(False)
    encoder.eval().to(device)
    return encoder


def extract_fingerprint(encoder, molecules, device, batch_size=256):
    import torch
    from chemprop import data, featurizers
    from chemprop.data.collate import collate_batch
    from rdkit import Chem
    ids = molecule_ids(molecules)
    if batch_size < 1:
        raise ValueError("Encoder batch size must be positive")
    if any(not isinstance(s, str) or Chem.MolFromSmiles(s) is None for s in molecules.SMILES):
        raise ValueError("Invalid official SMILES during encoder extraction")
    dataset = data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s, [np.nan]) for s in molecules.SMILES],
                                   featurizers.SimpleMoleculeMolGraphFeaturizer())
    dataset.cache = True
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False, drop_last=False,
                                         num_workers=0, collate_fn=collate_batch)
    encoder.eval()
    rows = []
    with torch.inference_mode():
        for bmg, vd, xd, *_ in loader:
            if vd is not None or xd is not None:
                raise ValueError("Unexpected extra atom/molecule descriptors")
            bmg.to(device)
            rows.append(encoder(bmg).float().cpu().numpy())
    features = np.concatenate(rows).astype(np.float32, copy=False)
    if features.ndim != 2 or len(features) != len(ids) or not np.isfinite(features).all():
        raise ValueError("Invalid or misaligned frozen fingerprints")
    return features


def run_trial(config, train_df, query_df, asset_root, output_dir, validation_df=None):
    import torch
    from . import tabular
    cfg = dict(config)
    if cfg.get("model", "tabpfn") != "tabpfn":
        raise ValueError("Initial adapted-TFM protocol implements pinned TabPFN only")
    if not isinstance(cfg.get("model_asset"), dict):
        raise ValueError("Pinned TabPFN model_asset is required; no implicit download")
    verified_file(cfg["model_asset"]["path"], cfg["model_asset"]["sha256"], Path(asset_root))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if any((out / n).exists() for n in ["adapted_encoder.json", "trial.json", "predictions.csv", "encoder_features.npy"]):
        raise FileExistsError("Adapted trial artifacts exist; use a new immutable trial directory")
    checkpoint, metadata, provenance = validate_parent(cfg, train_df, query_df, asset_root, validation_df)
    device = cfg.get("encoder_device", "cuda" if torch.cuda.is_available() else "cpu")
    encoder = load_encoder(checkpoint, metadata, device)
    molecules = pd.concat([train_df[["Molecule_Name", "SMILES"]], query_df[["Molecule_Name", "SMILES"]]], ignore_index=True)
    features = extract_fingerprint(encoder, molecules, device, int(cfg.get("encoder_batch_size", 256)))
    del encoder
    if str(device).startswith("cuda"):
        torch.cuda.empty_cache()
    matrix = out / "encoder_features.npy"
    ids_path = out / "encoder_feature_ids.json"
    np.save(matrix, features)
    _write_json(ids_path, molecule_ids(molecules))
    asset = {"matrix_path": str(matrix.resolve()), "sha256": _digest(matrix),
             "ids_path": str(ids_path.resolve()), "ids_sha256": _digest(ids_path)}
    learner = dict(cfg, model="tabpfn", features=[{"family": "precomputed", "asset": asset}],
                   preprocessing=dict(cfg.get("preprocessing", {"scale": True, "pca_components": 100})))
    provenance.update(encoder_stage="message_passing -> aggregation -> BatchNorm", encoder_eval=True,
                      encoder_gradients_enabled=False, feature_shape=list(features.shape), feature_asset=asset,
                      transform_fit_scope="Supplied official training molecules only; no public auxiliary/query/validation rows",
                      tabpfn_label_scope="Observed official primary training labels only; missing labels remain unknown",
                      source_module_sha256=_digest(Path(__file__)),
                      child_config_sha256=hashlib.sha256(json.dumps(cfg, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                      representation_caveat="Encoder was supervised on these training molecules; downstream learner fits their in-sample representations. Outer performance, not training fit, determines utility.")
    _write_json(out / "adapted_encoder.json", provenance)
    # Existing audited tabular adapter fits imputation/scaling/PCA on train rows,
    # gathers frozen query features by ID, and uses the pinned TabPFN asset.
    return tabular.run_trial(learner, train_df, query_df, Path(asset_root), out, validation_df=validation_df)

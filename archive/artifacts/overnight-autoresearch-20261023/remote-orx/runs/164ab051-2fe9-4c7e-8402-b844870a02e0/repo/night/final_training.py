"""Future post-gate full-TRAIN five-fold bags; actual TEST is never scored here.

Root must launch this from a committed ORX child after its promotion gate:
python -u -m night.final_training --config final_training_config.json
No provisioning, dependency installation, submission, or run.sh changes occur.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

from .public_data import _atomic_bytes, _digest, normalize_parent_key
from .reference import CANONICAL

SPLIT_SEED = 42
N_FOLDS = 5
SPLIT_SOURCE = "https://github.com/SuperCowPowers/workbench/blob/8c72c7559471febaf0962fd551b4eaab8db3a136/src/workbench/training/splits.py"
R0_NAMES = ["union18", "mtaux8", "2d6isoform6", "2d6single"]


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _hash(value):
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _immutable(path, value):
    """Create once; a byte-identical existing artifact is a verified resume."""
    path = Path(path)
    if path.exists():
        if path.read_bytes() != value:
            raise FileExistsError(f"Refusing to overwrite different artifact: {path}")
        return
    _atomic_bytes(path, value)


def _write_json(path, value):
    _immutable(path, _json_bytes(value))


def _write_frame(path, frame):
    _immutable(path, frame.to_csv(index=False, float_format="%.17g").encode())


def _ids(frame, label):
    if "Molecule_Name" not in frame or frame.Molecule_Name.isna().any():
        raise ValueError(f"{label} has missing molecule IDs")
    ids = frame.Molecule_Name.astype(str).tolist()
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label} has duplicate molecule IDs")
    return ids


def read_official(asset_root):
    root = Path(asset_root)
    train = pd.read_csv(root / "official-train.csv")
    # Restrict at read time: actual TEST cannot supply labels to any downstream API.
    test = pd.read_csv(root / "official-test.csv", usecols=["Molecule_Name", "SMILES"])
    for name, frame in [("official TRAIN", train), ("actual TEST", test)]:
        frame["Molecule_Name"] = _ids(frame, name)
        if frame.empty or "SMILES" not in frame or frame.SMILES.isna().any():
            raise ValueError(f"{name} requires nonempty valid structure rows")
    if set(train.Molecule_Name) & set(test.Molecule_Name):
        raise ValueError("Official TRAIN/actual TEST ID overlap")
    if not set(CANONICAL) <= set(train):
        raise ValueError("Official TRAIN lacks primary targets")
    return train, test[["Molecule_Name", "SMILES"]]


def make_final_folds(train, test):
    """Same published greedy shuffled scaffold assignment as night/cohorts.py."""
    train_ids, test_ids = _ids(train, "TRAIN"), _ids(test, "TEST")
    if set(train_ids) & set(test_ids):
        raise ValueError("TRAIN/TEST ID overlap")
    parents = [normalize_parent_key(s) for s in train.SMILES]
    test_parents = [normalize_parent_key(s) for s in test.SMILES]
    if any(p is None for p in parents + test_parents):
        raise ValueError("Invalid official parent structure")
    if set(parents) & set(test_parents):
        raise ValueError("Official TRAIN and actual TEST share normalized parents; root must resolve explicitly")
    groups, scaffold_to_group = [], {}
    for smiles in train.SMILES:
        scaffold = Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(Chem.MolFromSmiles(smiles)))
        if scaffold not in scaffold_to_group:
            scaffold_to_group[scaffold] = len(scaffold_to_group)
        groups.append(scaffold_to_group[scaffold])
    groups = np.asarray(groups)
    unique, counts = np.unique(groups, return_counts=True)
    if len(unique) < N_FOLDS:
        raise ValueError("Fewer than five scaffold groups")
    loads, assignment = np.zeros(N_FOLDS, dtype=int), {}
    for i in np.random.default_rng(SPLIT_SEED).permutation(len(unique)):
        fold = int(np.argmin(loads))
        assignment[int(unique[i])] = fold
        loads[fold] += int(counts[i])
    fold_ids = np.asarray([assignment[int(g)] for g in groups])
    folds = []
    for f in range(N_FOLDS):
        val_idx = np.flatnonzero(fold_ids == f)
        val_parents = {parents[i] for i in val_idx}
        fit_idx = [i for i in range(len(train)) if fold_ids[i] != f and parents[i] not in val_parents]
        purged = [train_ids[i] for i in range(len(train)) if fold_ids[i] != f and parents[i] in val_parents]
        if not len(val_idx) or not fit_idx:
            raise ValueError("Empty fitting/validation partition")
        assert not ({parents[i] for i in fit_idx} & val_parents)
        folds.append({"fold": f, "train_ids": [train_ids[i] for i in fit_idx],
                      "val_ids": [train_ids[i] for i in val_idx], "parent_purged_ids": purged})
    seen = [i for f in folds for i in f["val_ids"]]
    if len(seen) != len(set(seen)) or set(seen) != set(train_ids):
        raise ValueError("Final folds do not give exactly one OOF prediction per official TRAIN row")
    return {"seed": SPLIT_SEED, "n_folds": N_FOLDS, "source": SPLIT_SOURCE,
            "train_ids": train_ids, "actual_test_ids": test_ids, "inner_folds": folds,
            "excluded_parent_keys": sorted(set(parents) | set(test_parents)),
            "scaffold_count": len(unique), "scaffold_group_assignment": {str(k): v for k, v in assignment.items()},
            "policy": "Published original-SMILES Murcko scaffold groups; shuffle seed42; greedy least-loaded fold; train-side normalized-parent purge",
            "oof_caveat": "Validation labels choose neural epochs; these OOF predictions are out of gradient fitting but not independent of epoch selection"}


def model_targets(model):
    if "targets" in model:
        requested = model["targets"]
        if isinstance(requested, str):
            requested = [requested]
        targets = [t if t in CANONICAL else t + "_pIC50_direct_inhibition" for t in requested]
    elif model.get("kind") == "neural" and model.get("component") in {"2d6isoform6", "2d6single"}:
        targets = ["CYP2D6_pIC50_direct_inhibition"]
    else:
        targets = list(CANONICAL)
    if not targets or len(set(targets)) != len(targets) or not set(targets) <= set(CANONICAL):
        raise ValueError("Model targets must be a unique canonical target subset")
    return targets


def validate_config(config):
    cfg = dict(config)
    for key in ["asset_root", "output_dir", "models"]:
        if key not in cfg:
            raise ValueError(f"Missing config.{key}")
    cfg["asset_root"] = str(Path(cfg["asset_root"]).resolve())
    cfg["output_dir"] = str(Path(cfg["output_dir"]).resolve())
    cfg.setdefault("seeds", [42, 142])
    cfg.setdefault("gpus", [0])
    cfg.setdefault("torch_num_threads", 4)
    cfg.setdefault("num_workers", 0)
    if not cfg["models"] or not cfg["seeds"] or not cfg["gpus"]:
        raise ValueError("Models, seeds and GPU slots must be nonempty")
    if any(not isinstance(s, int) or isinstance(s, bool) for s in cfg["seeds"]) or len(set(cfg["seeds"])) != len(cfg["seeds"]):
        raise ValueError("Seeds must be distinct integers")
    slots = [str(g) for g in cfg["gpus"]]
    if len(set(slots)) != len(slots) or any(not re.fullmatch(r"\d+", g) for g in slots):
        raise ValueError("GPU slots must be distinct nonnegative numeric IDs")
    cfg["gpus"] = slots
    names = []
    for model in cfg["models"]:
        if model.get("kind") not in {"neural", "tabular"}:
            raise ValueError("Every model requires kind neural or tabular")
        name = model.get("name", "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
            raise ValueError("Model names must be safe nonempty path components")
        names.append(name)
        model_targets(model)
    if len(names) != len(set(names)):
        raise ValueError("Duplicate model names")
    if cfg.get("split_seed", SPLIT_SEED) != SPLIT_SEED or cfg.get("n_folds", N_FOLDS) != N_FOLDS:
        raise ValueError("Final protocol fixes five folds and split seed42")
    if cfg.get("reference_members") is None:
        present = [n for n in R0_NAMES if n in names]
        if set(R0_NAMES) <= set(present):
            cfg["reference_members"] = R0_NAMES.copy()
        elif set(R0_NAMES[:2]) <= set(present):
            cfg["reference_members"] = R0_NAMES[:2]
        else:
            cfg["reference_members"] = []
        cfg["reference_assembly_policy"] = "Auto: all four members when complete, otherwise the complete two-base pair; incomplete families still export individually"
    members = cfg["reference_members"]
    if members and (len(members) not in {2, 4} or len(set(members)) != len(members) or not set(members) <= set(names)):
        raise ValueError("reference_members must name exactly two or four available distinct models")
    if "briford_reference" in names and members:
        raise ValueError("briford_reference is reserved for assembled reference output")
    return cfg


def input_fingerprints(cfg):
    root = Path(cfg["asset_root"])
    paths = {root / "official-train.csv", root / "official-test.csv"}
    for optional in ["asset_manifest.json", "cohorts.json"]:
        if (root / optional).exists():
            paths.add(root / optional)
    for folder in [root / "reference/public_data", root / "reference_audit/public_data"]:
        if folder.exists():
            paths.update(folder.glob("*.csv"))
    for model in cfg["models"]:
        if model.get("reference_data_dir"):
            paths.update(Path(model["reference_data_dir"]).glob("*.csv"))
        if model.get("initialization") == "chemeleon":
            paths.add(Path(model.get("checkpoint_path", root / "weights/chemeleon_mp.pt")))
        if model.get("extra_public_sources"):
            folder = root / model.get("extra_public_dir", "new_public")
            paths.update(folder / n for n in ["measurements.csv", "manifest.json", "data_quality.json"])
        if model.get("model_asset"):
            path = Path(model["model_asset"]["path"])
            paths.add(path if path.is_absolute() else root / path)
    source = Path(__file__).resolve().parent
    code = list(source.glob("*.py")) + [source.parent / "official_scoring_functions.py"]
    packages = {}
    for package in ["numpy", "pandas", "rdkit", "scipy", "scikit-learn", "torch", "chemprop", "lightning",
                    "lightgbm", "catboost", "tabpfn", "tabicl"]:
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    return {"assets": {str(p): _digest(p) for p in sorted(paths)},
            "source": {str(p.relative_to(source.parent)): _digest(p) for p in sorted(code)},
            "packages": packages,
            "scope": "Official tables, reference CSVs, configured pretrained/new-public assets, manifests and all night Python sources"}


def prepare_run(config):
    cfg = validate_config(config)
    train, test = read_official(cfg["asset_root"])
    folds = make_final_folds(train, test)
    fingerprints = input_fingerprints(cfg)
    payload = {"config": cfg, "fingerprints": fingerprints, "folds_sha256": _hash(folds)}
    manifest = {**payload, "run_sha256": _hash(payload),
                "actual_test_scoring": False, "purpose": "Post-gate full official TRAIN bagging and structures-only actual TEST prediction"}
    output = Path(cfg["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    if not (output / "run_manifest.json").exists() and any(output.iterdir()):
        raise FileExistsError("Refusing to initialize a nonempty output directory without this run manifest")
    _write_json(output / "run_manifest.json", manifest)
    _write_json(output / "folds.json", folds)
    _write_json(output / "config.json", cfg)
    jobs = []
    for seed in cfg["seeds"]:
        for model in cfg["models"]:
            for f in range(N_FOLDS):
                trial = output / model["name"] / f"seed{seed}" / f"fold{f}"
                effective = dict(model, seed=seed, fold_index=f,
                                 targets=model_targets(model),
                                 excluded_parent_keys=folds["excluded_parent_keys"],
                                 torch_num_threads=cfg["torch_num_threads"], num_workers=cfg["num_workers"])
                job = {"run_sha256": manifest["run_sha256"], "run_dir": str(output),
                       "asset_root": cfg["asset_root"], "output_dir": str(trial),
                       "model_name": model["name"], "seed": seed, "fold": f, "config": effective}
                job["job_sha256"] = _hash(job)
                trial.mkdir(parents=True, exist_ok=True)
                _write_json(trial / "job.json", job)
                jobs.append(job)
    return manifest, folds, jobs


def _check_prediction(frame, ids, targets):
    actual = _ids(frame, "predictions")
    if actual != list(ids) or set(frame.columns) != {"Molecule_Name", *targets}:
        raise ValueError("Prediction row order/IDs or exact target columns differ")
    if not np.isfinite(frame[targets].to_numpy(float)).all():
        raise ValueError("Nonfinite final prediction cells")
    return frame[["Molecule_Name"] + targets]


def verify_completed(job):
    out = Path(job["output_dir"])
    done_path = out / "worker_done.json"
    if not done_path.exists():
        return False
    done = json.loads(done_path.read_text())
    if done.get("job_sha256") != job["job_sha256"] or done.get("run_sha256") != job["run_sha256"]:
        raise ValueError("Completed trial hash mismatch")
    if json.loads((out / "job.json").read_text()) != job:
        raise ValueError("Completed job definition changed")
    for name, expected in done["artifact_sha256"].items():
        if _digest(out / name) != expected:
            raise ValueError(f"Completed trial artifact changed: {out / name}")
    if "predictions.csv" not in done["artifact_sha256"]:
        raise ValueError("Completed trial lacks prediction checksum")
    return True


def worker(job_path, run_trial_override=None):
    """One fit. Override is solely for tiny injected mock tests, not a CLI option."""
    job = json.loads(Path(job_path).read_text())
    claimed = job["job_sha256"]
    if _hash({k: v for k, v in job.items() if k != "job_sha256"}) != claimed:
        raise ValueError("Job configuration checksum mismatch")
    run = Path(job["run_dir"])
    manifest = json.loads((run / "run_manifest.json").read_text())
    payload = {k: manifest[k] for k in ["config", "fingerprints", "folds_sha256"]}
    if _hash(payload) != manifest["run_sha256"]:
        raise ValueError("Run manifest checksum mismatch")
    if manifest["run_sha256"] != job["run_sha256"] or input_fingerprints(manifest["config"]) != manifest["fingerprints"]:
        raise ValueError("Run configuration/source/assets changed before worker")
    folds = json.loads((run / "folds.json").read_text())
    if _hash(folds) != manifest["folds_sha256"]:
        raise ValueError("Final folds changed")
    if verify_completed(job):
        return
    out = Path(job["output_dir"])
    if any(p.name != "job.json" for p in out.iterdir()):
        raise FileExistsError("Incomplete trial artifacts exist; use a new root-owned run directory instead of overwriting")
    # Exclusive creation also rejects a concurrent second worker for this same job.
    with (out / "worker_started.json").open("x") as handle:
        json.dump({"job_sha256": claimed, "pid": os.getpid(), "time": time.time()}, handle)
    train, test = read_official(job["asset_root"])
    indexed = train.set_index("Molecule_Name", drop=False)
    fold = folds["inner_folds"][job["fold"]]
    fit = indexed.loc[fold["train_ids"]].reset_index(drop=True)
    val = indexed.loc[fold["val_ids"]].reset_index(drop=True)
    query = pd.concat([val[["Molecule_Name", "SMILES"]], test], ignore_index=True)
    if set(fit.Molecule_Name) & set(query.Molecule_Name):
        raise ValueError("Fit/query ID overlap")
    if run_trial_override is None:
        if job["config"]["kind"] == "neural":
            from .neural import run_trial
        else:
            from .tabular import run_trial
    else:
        run_trial = run_trial_override
    started = time.monotonic()
    result = run_trial(job["config"], fit, query, Path(job["asset_root"]), out, validation_df=val)
    result = _check_prediction(result, query.Molecule_Name.tolist(), job["config"]["targets"])
    # Existing model APIs write predictions.csv; preserve those bytes after validating the returned result.
    path = out / "predictions.csv"
    if path.exists():
        stored = pd.read_csv(path, dtype={"Molecule_Name": str})
        stored = _check_prediction(stored, query.Molecule_Name.tolist(), job["config"]["targets"])
        for target in job["config"]["targets"]:
            expected = result[target].to_numpy()
            restored = stored[target].to_numpy().astype(expected.dtype)
            tolerance = 8 * np.finfo(expected.dtype).eps if np.issubdtype(expected.dtype, np.floating) else 0.0
            if not np.allclose(restored, expected, rtol=tolerance, atol=tolerance):
                raise ValueError("Model API returned predictions different from its persisted file")
    else:
        _write_frame(path, result)
    names = [n for n in ["predictions.csv", "trial_metadata.json", "trial.json", "complete.json"] if (out / n).exists()]
    _write_json(out / "worker_done.json", {"run_sha256": job["run_sha256"], "job_sha256": claimed,
                "artifact_sha256": {n: _digest(out / n) for n in names}, "rows": len(result),
                "targets": job["config"]["targets"], "seconds": time.monotonic() - started})
    print(json.dumps({"event": "final_fit_complete", "model": job["model_name"], "seed": job["seed"], "fold": job["fold"]}), flush=True)


def _save_aggregate(destination, train, test, oof, raw_test, fold_mapping, provenance, calibrator):
    targets = [t for t in CANONICAL if t in oof]
    oof = _check_prediction(oof, train.Molecule_Name.tolist(), targets)
    raw_test = _check_prediction(raw_test, test.Molecule_Name.tolist(), targets)
    variants, parameters = calibrator(train, oof, raw_test, fold_mapping, targets=targets,
                                      allowed_fit_ids=train.Molecule_Name.tolist(),
                                      forbidden_fit_ids=test.Molecule_Name.tolist())
    for name, pred in variants.items():
        _check_prediction(pred, test.Molecule_Name.tolist(), targets)
    destination.mkdir(parents=True, exist_ok=True)
    _write_frame(destination / "oof.csv", oof)
    _write_frame(destination / "test_raw.csv", raw_test)
    _write_frame(destination / "test_calibrated.csv", variants[parameters["selected_name"]])
    for name, pred in variants.items():
        _write_frame(destination / f"test_placement_{name}.csv", pred)
    _write_json(destination / "calibration.json", parameters)
    _write_json(destination / "aggregate.json", {**provenance, "targets": targets,
                "selected_calibration": parameters["selected_name"], "actual_test_scored": False,
                "caveats": ["Neural OOF rows participated in epoch selection; not independent of that selection.",
                            "Each OOF row uses one fold model; actual TEST uses five-fold averaging, so prediction variance can differ.",
                            "Development calibration selection scores are not independent estimates of final TEST performance."],
                "output_sha256": {p.name: _digest(p) for p in destination.glob("*.csv")}})


def collect(manifest, folds, jobs, calibrator_override=None):
    from .evaluation import calibrate_variants
    calibrator = calibrator_override or calibrate_variants
    cfg = manifest["config"]
    payload = {k: manifest[k] for k in ["config", "fingerprints", "folds_sha256"]}
    if (_hash(payload) != manifest["run_sha256"] or _hash(folds) != manifest["folds_sha256"]
            or input_fingerprints(cfg) != manifest["fingerprints"]):
        raise ValueError("Run source/assets/config/folds changed before final collection")
    train, test = read_official(cfg["asset_root"])
    output = Path(cfg["output_dir"])
    mapping = {i: f["fold"] for f in folds["inner_folds"] for i in f["val_ids"]}
    aggregate = {}
    for seed in cfg["seeds"]:
        for model in cfg["models"]:
            targets = model_targets(model)
            selected = sorted([j for j in jobs if j["seed"] == seed and j["model_name"] == model["name"]], key=lambda j: j["fold"])
            if len(selected) != N_FOLDS or [j["fold"] for j in selected] != list(range(N_FOLDS)):
                raise ValueError("Missing or duplicate model fold jobs")
            parts, test_parts = [], []
            for job in selected:
                if not verify_completed(job):
                    raise ValueError("Cannot collect incomplete trial")
                pred = pd.read_csv(Path(job["output_dir"]) / "predictions.csv", dtype={"Molecule_Name": str})
                val_ids = folds["inner_folds"][job["fold"]]["val_ids"]
                pred = _check_prediction(pred, val_ids + test.Molecule_Name.tolist(), targets).set_index("Molecule_Name")
                parts.append(pred.loc[val_ids].reset_index())
                test_parts.append(pred.loc[test.Molecule_Name, targets].to_numpy())
            oof = pd.concat(parts, ignore_index=True)
            _ids(oof, "collected OOF")
            oof = oof.set_index("Molecule_Name").loc[train.Molecule_Name].reset_index()
            raw = pd.DataFrame(np.mean(test_parts, axis=0), columns=targets)
            raw.insert(0, "Molecule_Name", test.Molecule_Name.to_numpy())
            provenance = {"run_sha256": manifest["run_sha256"], "model": model["name"], "seed": seed,
                          "fold_job_sha256": [j["job_sha256"] for j in selected]}
            _save_aggregate(output / model["name"] / f"seed{seed}", train, test, oof, raw, mapping, provenance, calibrator)
            aggregate[(model["name"], seed)] = (oof, raw)
        members = cfg["reference_members"]
        if members:
            assembled = []
            for index, ids in [(0, train.Molecule_Name.tolist()), (1, test.Molecule_Name.tolist())]:
                result = pd.DataFrame({"Molecule_Name": ids})
                frames = [aggregate[(name, seed)][index].set_index("Molecule_Name") for name in members]
                for target in CANONICAL:
                    available = [f.loc[ids, target].to_numpy() for f in frames if target in f]
                    if not available:
                        raise ValueError(f"Reference has no member predicting {target}")
                    result[target] = np.mean(available, axis=0)
                assembled.append(result)
            _save_aggregate(output / "briford_reference" / f"seed{seed}", train, test, *assembled, mapping,
                            {"run_sha256": manifest["run_sha256"], "model": "briford_reference", "seed": seed,
                             "members": members, "aggregation": "Equal weight among available member predictions for each target"}, calibrator)
    _write_json(output / "final_predictions_complete.json", {"run_sha256": manifest["run_sha256"],
                "models": [m["name"] for m in cfg["models"]], "seeds": cfg["seeds"],
                "reference_members": cfg["reference_members"], "test_rows": len(test),
                "test_ids_sha256": _hash(test.Molecule_Name.tolist()), "actual_test_scored": False,
                "next_step": "Root applies previously promoted stack/width/P0 recipe, validates submission and decides submission"})


def run(config):
    manifest, folds, jobs = prepare_run(config)
    cfg = manifest["config"]
    pending = [j for j in jobs if not verify_completed(j)]
    for job in pending:
        if any(p.name != "job.json" for p in Path(job["output_dir"]).iterdir()):
            raise FileExistsError("Incomplete started trial exists; refusing overwrite")
    slots, failures = {}, []
    try:
        while pending or slots:
            for gpu in cfg["gpus"]:
                if gpu in slots or not pending:
                    continue
                job = pending.pop(0)
                # Keep logs outside trial directories so their pre-fit guard remains strict.
                log_path = Path(cfg["output_dir"]) / f"{job['model_name']}-seed{job['seed']}-fold{job['fold']}.log"
                log = log_path.open("x")
                env = dict(os.environ, CUDA_VISIBLE_DEVICES=gpu)
                try:
                    process = subprocess.Popen([sys.executable, "-u", "-m", "night.final_training", "--worker",
                                                str(Path(job["output_dir"]) / "job.json")], env=env, stdout=log, stderr=subprocess.STDOUT)
                except Exception:
                    log.close()
                    raise
                slots[gpu] = (process, log, job)
                print(json.dumps({"event": "final_fit_started", "gpu": gpu, "model": job["model_name"], "seed": job["seed"], "fold": job["fold"]}), flush=True)
            for gpu, (process, log, job) in list(slots.items()):
                code = process.poll()
                if code is None:
                    continue
                log.close()
                del slots[gpu]
                if code != 0 or not verify_completed(job):
                    failures.append({"model": job["model_name"], "seed": job["seed"], "fold": job["fold"], "exit": code})
            if pending or slots:
                time.sleep(5)
    finally:
        for process, log, job in slots.values():
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            log.close()
    if failures:
        _write_json(Path(cfg["output_dir"]) / "failed_jobs.json", {"run_sha256": manifest["run_sha256"], "failures": failures})
        raise RuntimeError(f"{len(failures)} final fits failed; no final aggregate is declared complete")
    collect(manifest, folds, jobs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if bool(args.config) == bool(args.worker):
        parser.error("Supply exactly one of --config or --worker")
    if args.worker:
        worker(args.worker)
    else:
        run(json.loads(args.config.read_text()))


if __name__ == "__main__":
    main()

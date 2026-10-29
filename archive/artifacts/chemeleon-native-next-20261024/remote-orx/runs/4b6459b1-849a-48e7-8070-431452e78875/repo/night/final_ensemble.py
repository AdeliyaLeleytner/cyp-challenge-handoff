"""Post-gate final reference_reweight_affine ensemble; no TEST scoring or submission.

Future committed ORX entrypoint: python -m night.final_ensemble --config CONFIG.
Config requires asset_root, output_dir, seed_roots={'42':..., '142':...}, and
qualified_recipe/gate_manifest/gate_certificate records, each {path, sha256}.
Only full official TRAIN labels fit the already-qualified metamodel recipe.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .reference import CANONICAL, DEFAULTS
from .public_data import normalize_parent_key

TRAIN_ROWS, TEST_ROWS = 4905, 750
MEMBERS = ["union18", "mtaux8", "2d6isoform6", "2d6single"]
VIEWS = ["briford_reference", "union18", "mtaux8", "specialist_single_view", "specialist_aux_view"]
D6 = "CYP2D6_pIC50_direct_inhibition"
TRAINING_REVISION = "72dc8a7"
METAMODEL_REVISION = "262990e"
TRAINING_SOURCES = {
    "night/cohorts.py": "7d2439abcc523805037f1318a7fcd830409de8dc1a60a53f8489a347edd4e49d",
    "night/evaluation.py": "f674c658e44baf14b442c6a0d4aa7c0c1a54538437e498cf8ced337e3a47d963",
    "night/features.py": "ce4c52b94ab28e70ddc53d2ab574309a9a8043ef9afc756f6c8190b427344989",
    "night/final_training.py": "0422b1d0ad5212015d1f6e32160656e13e65078597f89d99dc9c76479bcafaeb",
    "night/neural.py": "015c91cc8e43a186bf0a9ed9bf99a313cbb242a76d76b79d7d52bf228ca1fc6a",
    "night/public_data.py": "c91d5a3268cd3b0ea0e96fbbe601524333d62804c8985f7641382968bb560968",
    "night/reference.py": "dd10a6be65a813e9ea2b76a4afc15806f0de1a64d809da42f3e8171c40ea3320",
    "night/runner.py": "1d1b05798ce3b97be8f385e39c999ab616a1af1049799a4cb22ad96a8e641ad7",
    "night/tabular.py": "6db69b2e54e25138ce929796f582abcaa6cb633a2932b93a01e0be595d9fbc73",
    "official_scoring_functions.py": "c0ee287c06c0301d4b3bfd74559b90eb1bd85db68b75b7d018ae92280c0e1dd3",
}
RUNTIME_SOURCES = {
    "night/stacking.py": "f230f87cfc420d6a042d9e29ec5529ca37c546c4aba885a92bef01d7d436b4fc",
    "night/reference_views.py": "e7eefe2f06c06c3d69f1f6ff62173b254e528205865b12aa7af4f61909d84ce2",
    **{k: TRAINING_SOURCES[k] for k in ["night/evaluation.py", "night/reference.py", "night/public_data.py", "official_scoring_functions.py"]},
}


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _run_hash(value):
    """Exact final_training JSON hash, including indentation and trailing newline."""
    return hashlib.sha256((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()).hexdigest()


def _canonical_hash(value):
    """Exact promotion_gate canonical manifest hash (not the raw file hash)."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _ids_hash(ids):
    return hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text())


def _pinned_json(record, label):
    if not isinstance(record, dict) or not {"path", "sha256"} <= set(record):
        raise ValueError(f"{label} requires path and SHA256")
    path = Path(record["path"])
    if _sha(path) != record["sha256"]:
        raise ValueError(f"{label} file hash mismatch")
    return _json(path), {"path": str(path), "sha256": record["sha256"]}


def verify_qualification(cfg):
    recipe, rp = _pinned_json(cfg["qualified_recipe"], "qualified recipe")
    gate_manifest, mp = _pinned_json(cfg["gate_manifest"], "gate manifest")
    certificate, cp = _pinned_json(cfg["gate_certificate"], "gate certificate")
    if certificate.get("manifest_sha256") != _canonical_hash(gate_manifest):
        raise ValueError("Certificate canonical gate-manifest binding mismatch")
    if certificate.get("manifest_file", {}).get("sha256") != mp["sha256"]:
        raise ValueError("Certificate raw gate-manifest file binding mismatch")
    name = "reference_reweight_affine"
    if (recipe.get("candidate_name") != name or certificate.get("candidate_name") != name
            or gate_manifest.get("candidate", {}).get("name") != name):
        raise ValueError("Candidate identity differs across recipe/manifest/certificate")
    if gate_manifest["candidate"].get("recipe", {}).get("sha256") != rp["sha256"]:
        raise ValueError("Qualified recipe is not the recipe bound by the passed gate")
    if certificate.get("passed") is not True or certificate.get("status") != "pass" or certificate.get("reasons"):
        raise ValueError("Gate certificate did not pass")
    if set(certificate.get("required_cohorts", [])) != {"own750", "briford529"} or set(map(str, certificate.get("required_seeds", []))) != {"42", "142"}:
        raise ValueError("Gate lacks both required cohorts/seeds")
    if certificate.get("reference_recipe_members") != MEMBERS or certificate.get("targets") != CANONICAL:
        raise ValueError("Gate reference family or target scope differs")
    for cohort in ["own750", "briford529"]:
        paired = certificate["comparisons"][cohort]
        averaged = certificate["averaged_prediction_scores"][cohort]
        if (paired.get("n_paired_seeds") != 2 or set(paired.get("per_seed", {})) != {"42", "142"}
                or not np.isfinite(paired["delta_candidate_minus_reference"])
                or not paired["delta_candidate_minus_reference"] < 0
                or not np.isfinite(averaged["delta_candidate_minus_reference"])
                or not averaged["delta_candidate_minus_reference"] < 0):
            raise ValueError("Certificate does not meet both predeclared numerical criteria")
    meta = recipe.get("metamodel", {})
    if (recipe.get("base_members") != MEMBERS or recipe.get("seeds") != [42, 142]
            or recipe.get("inner_folds") != 5 or recipe.get("fold_seed") != 42
            or recipe.get("foundation_initialization") != "scratch"
            or meta.get("model_names") != VIEWS or meta.get("reference_model") != "briford_reference"
            or meta.get("weight_constraint") != "positive_affine" or meta.get("l1_grid") != [0, .01, .1, 1.]):
        raise ValueError("Unsupported or changed qualified ensemble recipe")
    return recipe, gate_manifest, certificate, {"recipe": rp, "gate_manifest": mp, "certificate": cp,
        "canonical_manifest_sha256": _canonical_hash(gate_manifest),
        "binding_chain": "pinned certificate -> canonical+raw gate manifest -> candidate.recipe.sha256 -> exact qualified recipe bytes"}


def verify_runtime_sources():
    source_root = Path(__file__).resolve().parent.parent
    actual = {name: _sha(source_root / name) for name in RUNTIME_SOURCES}
    if actual != RUNTIME_SOURCES:
        raise ValueError("Runtime stacking/view/scoring dependency differs from qualified frozen sources")
    return actual


def _ids(frame, label):
    if "Molecule_Name" not in frame or frame.Molecule_Name.isna().any():
        raise ValueError(f"Missing IDs in {label}")
    ids = frame.Molecule_Name.astype(str).tolist()
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate IDs in {label}")
    return ids


def _prediction(path, ids, targets):
    frame = pd.read_csv(path, dtype={"Molecule_Name": str})
    if _ids(frame, str(path)) != ids or set(frame) != {"Molecule_Name", *targets}:
        raise ValueError(f"Prediction ID/order/target mismatch: {path}")
    if not np.isfinite(frame[targets].to_numpy(float)).all():
        raise ValueError(f"Nonfinite predictions: {path}")
    return frame[["Molecule_Name"] + targets]


def _expected_folds(train, test):
    """Independently reconstruct the published seed42 assignment and parent purge."""
    from rdkit import Chem
    from rdkit.Chem.Scaffolds import MurckoScaffold
    ids = train.Molecule_Name.tolist()
    parents = [normalize_parent_key(s) for s in train.SMILES]
    tp = [normalize_parent_key(s) for s in test.SMILES]
    if any(p is None for p in parents + tp) or set(parents) & set(tp):
        raise ValueError("Invalid or overlapping official TRAIN/TEST normalized parents")
    group_map, groups = {}, []
    for smiles in train.SMILES:
        scaffold = Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(Chem.MolFromSmiles(smiles)))
        if scaffold not in group_map:
            group_map[scaffold] = len(group_map)
        groups.append(group_map[scaffold])
    groups = np.asarray(groups)
    unique, counts = np.unique(groups, return_counts=True)
    loads, assignment = np.zeros(5, dtype=int), {}
    for i in np.random.default_rng(42).permutation(len(unique)):
        f = int(np.argmin(loads)); assignment[int(unique[i])] = f; loads[f] += int(counts[i])
    labels = np.asarray([assignment[int(g)] for g in groups])
    result = []
    for f in range(5):
        vi = np.flatnonzero(labels == f); vp = {parents[i] for i in vi}
        result.append({"fold": f, "val_ids": [ids[i] for i in vi],
                       "train_ids": [ids[i] for i in range(len(ids)) if labels[i] != f and parents[i] not in vp],
                       "parent_purged_ids": [ids[i] for i in range(len(ids)) if labels[i] != f and parents[i] in vp]})
    return result, sorted(set(parents) | set(tp))


def _safe_artifacts(directory, hashes):
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Missing artifact hashes")
    for name, expected in hashes.items():
        if Path(name).name != name or name in {".", ".."} or _sha(directory / name) != expected:
            raise ValueError(f"Unsafe or hash-mismatched artifact: {directory}/{name}")


def _near_equal(left, right, label):
    # CSV roundtrip tolerance, not a performance acceptance threshold.
    if left.shape != right.shape or not np.allclose(left, right, rtol=1e-12, atol=1e-12):
        raise ValueError(f"Reconstructed aggregate differs: {label}")


def verify_seed_root(seed_root, seed, assets, train, test, expected_folds, excluded):
    root = Path(seed_root)
    manifest = _json(root / "run_manifest.json")
    folds = _json(root / "folds.json")
    complete = _json(root / "final_predictions_complete.json")
    payload = {k: manifest[k] for k in ["config", "fingerprints", "folds_sha256"]}
    run_hash = _run_hash(payload)
    if manifest["run_sha256"] != run_hash or complete["run_sha256"] != run_hash or manifest["folds_sha256"] != _run_hash(folds):
        raise ValueError("Final-training manifest/fold/completion hash mismatch")
    cfg = manifest["config"]
    if (_json(root / "config.json") != cfg or cfg["seeds"] != [seed]
            or set(complete["models"]) != set(MEMBERS) or complete["seeds"] != [seed]
            or cfg["reference_members"] != MEMBERS or complete["reference_members"] != MEMBERS
            or complete.get("actual_test_scored") is not False or manifest.get("actual_test_scoring") is not False):
        raise ValueError("Incomplete or incompatible final-training family/seed")
    if manifest["fingerprints"]["source"] != TRAINING_SOURCES:
        raise ValueError("Recorded relative training-source hashes differ from72dc8a7")
    # Resolve recorded absolute asset paths against the caller's staged asset root.
    original_assets = Path(cfg["asset_root"])
    resolved_assets = {}
    for recorded, expected in manifest["fingerprints"]["assets"].items():
        try:
            relative = Path(recorded).relative_to(original_assets)
        except ValueError as error:
            raise ValueError("Training fingerprint references an unstaged external asset path") from error
        local = assets / relative
        if _sha(local) != expected:
            raise ValueError(f"Training asset changed: {relative}")
        resolved_assets[str(relative)] = expected
    if not {"official-train.csv", "official-test.csv"} <= set(resolved_assets):
        raise ValueError("Training fingerprints omit official tables")
    ids, qids = train.Molecule_Name.tolist(), test.Molecule_Name.tolist()
    if (folds.get("seed") != 42 or folds.get("n_folds") != 5 or folds.get("train_ids") != ids
            or folds.get("actual_test_ids") != qids or folds.get("inner_folds") != expected_folds
            or folds.get("excluded_parent_keys") != excluded or complete.get("test_rows") != len(qids)
            or complete.get("test_ids_sha256") != _run_hash(qids)):
        raise ValueError("Final folds/IDs/parent exclusions differ from the frozen full-TRAIN protocol")
    models = {m["name"]: m for m in cfg["models"]}
    if len(models) != 4 or set(models) != set(MEMBERS):
        raise ValueError("Exactly all four reference components are required")
    predictions, evidence = {}, {}
    for member in MEMBERS:
        model = models[member]
        if (model.get("kind") != "neural" or model.get("component") != member
                or model.get("initialization", "scratch") != "scratch" or model.get("extra_public_sources")
                or model.get("checkpoint_path") or model.get("task_weights") is not None):
            raise ValueError("Final component is not the qualified scratch reference recipe")
        targets = [D6] if member.startswith("2d6") else list(CANONICAL)
        directory = root / member / f"seed{seed}"
        aggregate = _json(directory / "aggregate.json")
        _safe_artifacts(directory, aggregate["output_sha256"])
        if not {"oof.csv", "test_raw.csv"} <= set(aggregate["output_sha256"]):
            raise ValueError("Required raw aggregate hashes absent")
        if aggregate.get("run_sha256") != run_hash or aggregate.get("seed") != seed or aggregate.get("model") != member or aggregate.get("actual_test_scored") is not False:
            raise ValueError("Component aggregate provenance mismatch")
        oof = _prediction(directory / "oof.csv", ids, targets)
        query = _prediction(directory / "test_raw.csv", qids, targets)
        parts, queries, jobs = [], [], []
        for f, fold in enumerate(expected_folds):
            trial = directory / f"fold{f}"
            job, done = _json(trial / "job.json"), _json(trial / "worker_done.json")
            job_hash = _run_hash({k: v for k, v in job.items() if k != "job_sha256"})
            if (job.get("job_sha256") != job_hash or done.get("job_sha256") != job_hash
                    or job.get("run_sha256") != run_hash or done.get("run_sha256") != run_hash
                    or job.get("model_name") != member or job.get("seed") != seed or job.get("fold") != f):
                raise ValueError("Fold job/completion provenance mismatch")
            expected_config = dict(model, seed=seed, fold_index=f, targets=targets,
                                   excluded_parent_keys=excluded, torch_num_threads=cfg["torch_num_threads"], num_workers=cfg["num_workers"])
            if job["config"] != expected_config:
                raise ValueError("Fold effective job config differs from declared run model")
            _safe_artifacts(trial, done["artifact_sha256"])
            if not {"predictions.csv", "trial_metadata.json", "complete.json"} <= set(done["artifact_sha256"]):
                raise ValueError("Fold lacks required neural completion hashes")
            neural = _json(trial / "trial_metadata.json")
            neural_complete = _json(trial / "complete.json")
            if neural_complete.get("status") != "complete" or neural_complete.get("best_epoch") != neural.get("best_epoch"):
                raise ValueError("Neural checkpoint completion status/epoch mismatch")
            effective = neural["effective_config"]
            for key, expected in DEFAULTS.items():
                if key != "seed" and effective.get(key) != expected:
                    raise ValueError(f"Qualified neural default changed: {member}/{key}")
            if (neural["initialization"].get("initialization") != "scratch"
                    or effective.get("seed") != seed or effective.get("fold_index") != f
                    or effective.get("component") != member or neural.get("seed") != seed + f
                    or effective.get("include_official_side_rows") is not True):
                raise ValueError("Neural component/seed/source policy mismatch")
            query_ids = fold["val_ids"] + qids
            if neural.get("supplied_train_id_sha256") != _ids_hash(fold["train_ids"]) or neural.get("query_id_sha256") != _ids_hash(query_ids):
                raise ValueError("Parent neural fit/query IDs differ from final folds")
            fit_ids = _ids(pd.read_csv(trial / "fit_ids.csv", dtype={"Molecule_Name": str}), "fit IDs")
            val_ids = _ids(pd.read_csv(trial / "validation_ids.csv", dtype={"Molecule_Name": str}), "validation IDs")
            if (neural.get("fit_id_sha256") != _ids_hash(fit_ids) or neural.get("validation_id_sha256") != _ids_hash(val_ids)
                    or set(fit_ids) & set(query_ids) or not set(val_ids) <= set(fold["val_ids"])
                    or not (set(fit_ids) & set(ids)) <= set(fold["train_ids"])):
                raise ValueError("Actual fitting/epoch-selection ID audit failed")
            pred = _prediction(trial / "predictions.csv", query_ids, targets).set_index("Molecule_Name")
            parts.append(pred.loc[fold["val_ids"]].reset_index())
            queries.append(pred.loc[qids, targets].to_numpy())
            jobs.append(job_hash)
        if aggregate.get("fold_job_sha256") != jobs:
            raise ValueError("Aggregate fold job hash list differs")
        joined = pd.concat(parts).set_index("Molecule_Name").loc[ids, targets].to_numpy()
        _near_equal(joined, oof[targets].to_numpy(), member + " OOF")
        _near_equal(np.mean(queries, axis=0), query[targets].to_numpy(), member + " TEST")
        predictions[member] = (oof, query)
        evidence[member] = {"aggregate_sha256": _sha(directory / "aggregate.json"),
                            "oof_sha256": _sha(directory / "oof.csv"), "test_raw_sha256": _sha(directory / "test_raw.csv"),
                            "fold_job_sha256": jobs}
    # Verify raw R0 itself against its two/four-member arithmetic mean.
    directory = root / "briford_reference" / f"seed{seed}"
    aggregate = _json(directory / "aggregate.json")
    _safe_artifacts(directory, aggregate["output_sha256"])
    if (not {"oof.csv", "test_raw.csv"} <= set(aggregate["output_sha256"])
            or aggregate.get("members") != MEMBERS or aggregate.get("run_sha256") != run_hash
            or aggregate.get("seed") != seed or aggregate.get("model") != "briford_reference"
            or aggregate.get("actual_test_scored") is not False):
        raise ValueError("Raw reference aggregate provenance mismatch")
    reference = []
    for index, (file, order) in enumerate([("oof.csv", ids), ("test_raw.csv", qids)]):
        frame = _prediction(directory / file, order, list(CANONICAL))
        for target in CANONICAL:
            means = np.mean([p[index][target].to_numpy() for p in predictions.values() if target in p[index]], axis=0)
            _near_equal(means, frame[target].to_numpy(), "R0/" + target)
        reference.append(frame)
    predictions["briford_reference"] = tuple(reference)
    evidence["briford_reference"] = {"aggregate_sha256": _sha(directory / "aggregate.json"),
                                    "oof_sha256": _sha(directory / "oof.csv"), "test_raw_sha256": _sha(directory / "test_raw.csv")}
    return predictions, folds, {"seed": seed, "run_sha256": run_hash,
        "run_manifest_sha256": _sha(root / "run_manifest.json"), "completion_sha256": _sha(root / "final_predictions_complete.json"),
        "folds_sha256": _sha(root / "folds.json"), "recorded_relative_source_hashes": manifest["fingerprints"]["source"],
        "training_source_revision": TRAINING_REVISION, "verified_asset_hashes": resolved_assets,
        "training_packages": manifest["fingerprints"]["packages"], "model_configs": models, "aggregates": evidence}


def build_views(predictions, index):
    """Exact262990e view arithmetic: raw R0 except the explicitly replaced CYP2D6."""
    views = {name: predictions[name][index].copy() for name in VIEWS[:3]}
    for member, name in [("2d6single", "specialist_single_view"), ("2d6isoform6", "specialist_aux_view")]:
        frame = predictions["briford_reference"][index].copy()
        specialist = predictions[member][index].set_index("Molecule_Name")
        frame[D6] = specialist.loc[frame.Molecule_Name, D6].to_numpy()
        views[name] = frame[["Molecule_Name"] + list(CANONICAL)]
    return views


def run(config, fit_stack_override=None):
    cfg = dict(config)
    output = Path(cfg["output_dir"])
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Refusing to overwrite a completed or partial final-ensemble directory")
    recipe, gate_manifest, certificate, chain = verify_qualification(cfg)
    runtime = verify_runtime_sources()
    roots = {str(k): Path(v) for k, v in cfg["seed_roots"].items()}
    if set(roots) != {"42", "142"}:
        raise ValueError("Exactly seed42 and seed142 roots are required")
    assets = Path(cfg["asset_root"])
    train = pd.read_csv(assets / "official-train.csv", dtype={"Molecule_Name": str})
    test = pd.read_csv(assets / "official-test.csv", usecols=["Molecule_Name", "SMILES"], dtype={"Molecule_Name": str})
    ids, qids = _ids(train, "official TRAIN"), _ids(test, "actual TEST")
    if len(ids) != TRAIN_ROWS or len(qids) != TEST_ROWS or set(ids) & set(qids):
        raise ValueError("Expected all4905 official TRAIN and750 disjoint actual TEST IDs")
    if gate_manifest["truth"]["sha256"] != _sha(assets / "official-train.csv"):
        raise ValueError("Official TRAIN differs from the gate-bound truth")
    expected, excluded = _expected_folds(train, test)
    audited = {}
    for seed in [42, 142]:
        audited[seed] = verify_seed_root(roots[str(seed)], seed, assets, train, test, expected, excluded)
    if audited[42][1] != audited[142][1] or audited[42][2]["model_configs"] != audited[142][2]["model_configs"]:
        raise ValueError("Seed roots use different fold maps or component recipes")
    if fit_stack_override is None:
        from .stacking import fit_stack
    else:
        fit_stack = fit_stack_override  # In-process mock tests only; no CLI override.
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError("Final ensemble output changed during input verification")
    with (output / "started.json").open("x") as handle:
        json.dump({"config_sha256": _canonical_hash(cfg), "candidate_name": recipe["candidate_name"]}, handle)
    def save_json(name, data):
        (output / name).write_text(json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n")
    save_json("config.json", cfg)
    save_json("qualification_chain.json", chain)
    seed_predictions, seed_metadata = [], {}
    for seed in [42, 142]:
        predictions, folds, audit = audited[seed]
        oofs, queries = build_views(predictions, 0), build_views(predictions, 1)
        fold_mapping = {i: f["fold"] for f in folds["inner_folds"] for i in f["val_ids"]}
        method = {k: recipe["metamodel"][k] for k in ["model_names", "weight_constraint", "reference_model", "l1_grid"]}
        method.update(seed=seed, allowed_fit_ids=ids, forbidden_fit_ids=qids)
        pred, metadata = fit_stack(train, oofs, queries, fold_mapping, method)
        if _ids(pred, "final seed prediction") != qids or set(pred) != {"Molecule_Name", *CANONICAL} or not np.isfinite(pred[CANONICAL].to_numpy(float)).all():
            raise ValueError("Final stacking output IDs/targets/values invalid")
        pred = pred[["Molecule_Name"] + list(CANONICAL)]
        pred.to_csv(output / f"seed{seed}_predictions.csv", index=False, float_format="%.17g")
        save_json(f"seed{seed}_metadata.json", metadata)
        save_json(f"seed{seed}_source_audit.json", audit)
        seed_metadata[str(seed)] = {"selected_candidate": metadata["selected_candidate"],
                                   "weights": metadata["per_target"], "source_audit_sha256": _sha(output / f"seed{seed}_source_audit.json"),
                                   "prediction_sha256": _sha(output / f"seed{seed}_predictions.csv")}
        seed_predictions.append(pred[CANONICAL].to_numpy(float))
    submission = test[["Molecule_Name", "SMILES"]].copy()
    submission[CANONICAL] = np.mean(seed_predictions, axis=0)
    if submission.shape != (TEST_ROWS, 6) or not np.isfinite(submission[CANONICAL]).all().all():
        raise ValueError("Invalid final six-column submission shape or values")
    submission.to_csv(output / "submission.csv", index=False, float_format="%.17g")
    save_json("metadata.json", {"candidate_name": recipe["candidate_name"], "qualification_chain": chain,
        "recipe": recipe, "recipe_compatibility": {"matched": True, "base_members": MEMBERS, "views": VIEWS,
            "training_source_revision": TRAINING_REVISION, "metamodel_source_revision": METAMODEL_REVISION,
            "actual_runtime_relative_source_hashes": runtime, "view_semantics": "R0 raw reference copied; only CYP2D6 replaced in each specialist view",
            "no_additional_base_placement": True, "no_additional_width_or_neighbor_correction": True,
            "same_full_train_folds_both_seeds": True},
        "seeds": seed_metadata, "actual_test_scored": False, "actual_test_labels_read": False,
        "model_selection_labels": "Full official TRAIN OOF only, using the gate-bound procedure",
        "submission_sha256": _sha(output / "submission.csv"), "submission_rows": TEST_ROWS,
        "source_module_sha256": _sha(Path(__file__)), "official_train_sha256": _sha(assets / "official-train.csv"),
        "official_test_sha256": _sha(assets / "official-test.csv"),
        "runtime_packages": {p: importlib.metadata.version(p) for p in ["numpy", "pandas", "scipy", "rdkit"]},
        "provenance_attestation": "Root-owned; this module does not set the competition provenance checkbox or submit",
        "gate_qualifications": certificate.get("qualifications", {})})
    save_json("complete.json", {"status": "complete", "candidate_name": recipe["candidate_name"],
        "submission_sha256": _sha(output / "submission.csv"), "metadata_sha256": _sha(output / "metadata.json"),
        "automatic_submission": False})
    print(json.dumps({"event": "final_ensemble_ready", "rows": TEST_ROWS, "path": str(output / "submission.csv"), "actual_test_scored": False}), flush=True)
    return submission


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    run(_json(args.config))


if __name__ == "__main__":
    main()

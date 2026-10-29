"""Strict external ADMETlab feature alignment and fold-local preprocessing.

No service calls and no training occur here. Values are external predictions or
calculated descriptors, never experimental replacements for the CYP labels.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

FEATURE_PREFIX = "ADMETLAB::"
DEFAULT_METADATA_COLUMNS = ("request_id", "SMILES", "priority", "service_smiles", "taskid")
TEACHER_MEMBERSHIP = "unknown: the external teacher's historical training membership is not established"


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ordered_digest(values: Sequence[str]) -> str:
    return hashlib.sha256(json.dumps(list(values), ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _text_column(frame: pd.DataFrame, name: str) -> list[str]:
    if name not in frame or frame[name].isna().any():
        raise ValueError(f"Missing or null identifier column: {name}")
    values = frame[name].tolist()
    if any(not isinstance(x, str) or not x.strip() for x in values):
        raise ValueError(f"Identifiers must be nonempty strings: {name}")
    return values


@dataclass(frozen=True)
class AlignedFeatures:
    molecule_ids: tuple[str, ...]
    request_ids: tuple[str, ...]
    columns: tuple[str, ...]
    values: np.ndarray

    def audit(self) -> dict:
        return {"rows": len(self.molecule_ids), "ordered_molecule_id_sha256": ordered_digest(self.molecule_ids),
                "ordered_request_id_sha256": ordered_digest(self.request_ids),
                "unique_request_ids": len(set(self.request_ids)),
                "missing_values": int(np.isnan(self.values).sum())}


class AdmetFeatureCache:
    """A frozen table keyed by request_id, with an explicit all-endpoint schema.

    The mapping binds the original (molecule ID, original SMILES) pair to the
    request ID. Equivalent structures can intentionally share a request ID. ID-only
    merges, row-position joins and silent missing-request filling are prohibited.
    """
    def __init__(self, id_map: pd.DataFrame, table: pd.DataFrame, schema: dict, *, provenance: dict | None = None):
        self.provenance = dict(provenance or {})
        self.provenance['service_regime'] = {k: schema[k] for k in ['source_mode', 'backend', 'api_probe_vectors_used'] if k in schema}
        names = schema.get("feature_columns")
        if not isinstance(names, list) or not names or any(not isinstance(x, str) for x in names):
            raise ValueError("feature-schema.json must explicitly list feature_columns")
        if len(set(names)) != len(names) or any(not x.startswith(FEATURE_PREFIX) for x in names):
            raise ValueError("Feature names must be unique ADMETLAB:: source endpoints/features")
        self.columns = tuple(names)
        if not table.columns.is_unique or not id_map.columns.is_unique:
            raise ValueError("Duplicate table headers are ambiguous")
        metadata = set(schema.get("metadata_columns", DEFAULT_METADATA_COLUMNS))
        if metadata & set(names):
            raise ValueError("Feature/metadata column overlap")
        extras = set(table) - set(names) - metadata
        if extras:
            raise ValueError(f"Columns absent from the frozen schema: {sorted(extras)}")
        missing = set(names) - set(table)
        if missing:
            raise ValueError(f"Declared source endpoints absent from feature table: {sorted(missing)}")
        reqs = _text_column(table, "request_id")
        if len(set(reqs)) != len(reqs):
            raise ValueError("Feature cache requires exactly one row per request_id")
        numeric = table[list(names)].apply(pd.to_numeric, errors="raise")
        self._values = numeric.to_numpy(dtype=np.float64)
        if np.isinf(self._values).any():
            raise ValueError("Infinite ADMETlab outputs must be resolved explicitly before training")
        self._row_for_request = {r: i for i, r in enumerate(reqs)}
        mols = _text_column(id_map, "Molecule_Name")
        smiles = _text_column(id_map, "SMILES")
        mapped = _text_column(id_map, "request_id")
        canonical = _text_column(id_map, "request_smiles")
        self._mapping: dict[tuple[str, str], str] = {}
        self._request_smiles: dict[str, str] = {}
        for mol, smi, req, canon in zip(mols, smiles, mapped, canonical):
            if hashlib.sha256(canon.encode()).hexdigest() != req:
                raise ValueError(f"request_id is not the SHA256 of request_smiles: {mol}")
            old = self._mapping.setdefault((mol, smi), req)
            if old != req:
                raise ValueError(f"Ambiguous source ID/SMILES pair: {mol}")
            old_canon = self._request_smiles.setdefault(req, canon)
            if old_canon != canon:
                raise ValueError("One request_id maps to different request SMILES")
        if "SMILES" in table:
            table_smiles = _text_column(table, "SMILES")
            for req, smi in zip(reqs, table_smiles):
                if hashlib.sha256(smi.encode()).hexdigest() != req:
                    raise ValueError("Feature cache SMILES does not match its request_id hash")
                if req in self._request_smiles and smi != self._request_smiles[req]:
                    raise ValueError("Feature cache SMILES does not match its request_id mapping")
        self.provenance.update({"feature_columns": list(self.columns), "feature_count": len(self.columns),
                                "external_teacher_training_membership": TEACHER_MEMBERSHIP,
                                "feature_semantics": "External predicted/calculated features; not experimental CYP targets"})

    @classmethod
    def from_files(cls, id_map_path: str | Path, feature_csv: str | Path, schema_path: str | Path,
                   *, expected_sha256: dict[str, str] | None = None) -> "AdmetFeatureCache":
        paths = {"id_map": Path(id_map_path), "feature_table": Path(feature_csv), "feature_schema": Path(schema_path)}
        actual = {name: file_sha256(p) for name, p in paths.items()}
        if expected_sha256 is not None and actual != expected_sha256:
            raise ValueError(f"Frozen feature inputs changed: expected {expected_sha256}, observed {actual}")
        schema = json.loads(paths["feature_schema"].read_text())
        return cls(pd.read_csv(paths["id_map"], dtype={"Molecule_Name": str, "SMILES": str, "request_id": str, "request_smiles": str}),
                   pd.read_csv(paths["feature_table"], dtype={"request_id": str, "SMILES": str}), schema,
                   provenance={"input_sha256": actual})

    def align(self, frame: pd.DataFrame, *, id_column: str | None = None, smiles_column: str | None = None) -> AlignedFeatures:
        id_column = id_column or ("molecule_name" if "molecule_name" in frame else "Molecule_Name")
        smiles_column = smiles_column or ("smiles" if "smiles" in frame else "SMILES")
        ids = _text_column(frame, id_column); smiles = _text_column(frame, smiles_column)
        if len(set(ids)) != len(ids):
            raise ValueError("Native member/query molecule IDs must be unique")
        requests = []
        for mol, smi in zip(ids, smiles):
            try:
                req = self._mapping[(mol, smi)]
            except KeyError as exc:
                raise ValueError(f"No exact ID/SMILES mapping for {mol}; no ID-only or positional fallback") from exc
            if "request_id" in frame and str(frame.iloc[len(requests)]["request_id"]) != req:
                raise ValueError(f"Provided request_id disagrees with the source mapping: {mol}")
            if req not in self._row_for_request:
                raise ValueError(f"ADMETlab cache is incomplete for requested molecule {mol}, request_id={req}")
            requests.append(req)
        rows = [self._row_for_request[r] for r in requests]
        return AlignedFeatures(tuple(ids), tuple(requests), self.columns, self._values[rows].copy())


@dataclass(frozen=True)
class FoldImputer:
    columns: tuple[str, ...]
    medians: np.ndarray
    unsupported: np.ndarray
    fitted_request_id_sha256: str

    @classmethod
    def fit(cls, fit: AlignedFeatures) -> "FoldImputer":
        if len(fit.values) == 0:
            raise ValueError("Cannot fit feature preprocessing without training rows")
        medians = np.zeros(len(fit.columns), dtype=np.float64)
        unsupported = np.zeros(len(fit.columns), dtype=bool)
        for j in range(len(fit.columns)):
            observed = fit.values[np.isfinite(fit.values[:, j]), j]
            unsupported[j] = len(observed) == 0
            if len(observed): medians[j] = np.median(observed)
        return cls(fit.columns, medians, unsupported, ordered_digest(fit.request_ids))

    @property
    def descriptor_columns(self) -> tuple[str, ...]:
        return self.columns + tuple("is_missing::" + c for c in self.columns)

    def transform(self, aligned: AlignedFeatures) -> np.ndarray:
        if aligned.columns != self.columns:
            raise ValueError("Feature column order/schema changed after fitting")
        missing = np.isnan(aligned.values)
        result = np.where(missing, self.medians[None, :], aligned.values)
        # An endpoint absent throughout fit has no learned effect. Retain its
        # dimensions as constants, including on held rows where it later appears.
        result[:, self.unsupported] = 0.
        missing[:, self.unsupported] = True
        array = np.concatenate((result, missing.astype(np.float64)), axis=1).astype(np.float32)
        if not np.isfinite(array).all():
            raise ValueError("Imputed descriptors must be finite float32 values")
        return array

    def to_dict(self) -> dict:
        return {"schema_version": 1, "columns": list(self.columns), "medians": self.medians.tolist(),
                "unsupported": self.unsupported.tolist(), "fitted_request_id_sha256": self.fitted_request_id_sha256,
                "scaling": "none here: native train_chemprop_fold fits the only descriptor StandardScaler",
                "unsupported_policy": "Retain column, set value=0 and is_missing=1 in all partitions"}

    @classmethod
    def from_dict(cls, state: dict) -> "FoldImputer":
        if state["schema_version"] != 1: raise ValueError("Unsupported imputer version")
        columns = tuple(state["columns"]); medians = np.asarray(state["medians"], dtype=np.float64)
        unsupported = np.asarray(state["unsupported"], dtype=bool)
        if medians.shape != (len(columns),) or unsupported.shape != medians.shape or not np.isfinite(medians).all():
            raise ValueError("Invalid serialized imputer")
        return cls(columns, medians, unsupported, state["fitted_request_id_sha256"])


@dataclass(frozen=True)
class FoldDescriptors:
    train: np.ndarray
    validation: np.ndarray
    query: np.ndarray
    imputer: FoldImputer
    audit: dict

    @property
    def n_extra_descriptors(self) -> int:
        return len(self.imputer.descriptor_columns)

    def native_training_kwargs(self) -> dict:
        # Native code normalizes train/validation datasets internally. Its
        # val_extra_raw must remain an independent RAW imputed copy for inference.
        return {"train_extra": self.train.copy(), "val_extra": self.validation.copy(),
                "val_extra_raw": self.validation.copy()}

    def configure_spec(self, spec):
        from dataclasses import replace
        return replace(spec, use_extra_features=True, n_extra_descriptors=self.n_extra_descriptors)


def prepare_fold_descriptors(cache: AdmetFeatureCache, train: pd.DataFrame, validation: pd.DataFrame,
                             query: pd.DataFrame, *, require_disjoint_requests: bool = True) -> FoldDescriptors:
    parts = {"train": cache.align(train), "validation": cache.align(validation), "query": cache.align(query)}
    overlaps = {f"{a}/{b}": len(set(parts[a].request_ids) & set(parts[b].request_ids))
                for a, b in [("train", "validation"), ("train", "query"), ("validation", "query")]}
    if overlaps["train/validation"] or (require_disjoint_requests and any(overlaps.values())):
        raise ValueError(f"Structural request IDs overlap across declared held partitions: {overlaps}")
    imputer = FoldImputer.fit(parts["train"])
    arrays = {k: imputer.transform(v) for k, v in parts.items()}
    audit = {"feature_source": cache.provenance, "partitions": {k: v.audit() for k, v in parts.items()},
             "request_id_overlaps": overlaps, "strict_disjoint_requests": require_disjoint_requests,
             "train_validation_disjoint_always_required": True,
             "imputer": imputer.to_dict(), "n_extra_descriptors": len(imputer.descriptor_columns),
             "neural_preprocessing_fitted_on": "inner-fold training rows only",
             "external_teacher_training_membership": TEACHER_MEMBERSHIP}
    return FoldDescriptors(arrays["train"], arrays["validation"], arrays["query"], imputer, audit)


def copy_graph_model_weights(base_model, feature_model) -> dict:
    """Warm-start an already constructed descriptor model without changing its initial function.

    Build feature_model using the same native architecture, target scaler, loss and
    task weights as base_model, plus n_extra_descriptors and a new TRAIN-only
    descriptor ScaleTransform. Copy all existing parameters/buffers; append zeros
    only to the first FFN weight's descriptor columns. Keep the new descriptor
    transform. Start a fresh optimizer; old first-layer optimizer tensors have the
    wrong width. This function does not fit a scaler or alter source model weights.
    """
    import torch
    from torch import nn
    graph_width = int(base_model.message_passing.output_dim)
    if int(feature_model.message_passing.output_dim) != graph_width:
        raise ValueError("Encoder widths differ; this is not a feature-only warm start")
    def first_linear(model):
        for name, module in model.predictor.ffn.named_modules():
            if isinstance(module, nn.Linear): return "predictor.ffn." + name, module
        raise ValueError("No first FFN Linear layer")
    source_name, old_layer = first_linear(base_model); dest_name, new_layer = first_linear(feature_model)
    if source_name != dest_name or old_layer.in_features != graph_width:
        raise ValueError("Base must be the corresponding graph-only native model")
    if new_layer.in_features <= graph_width or old_layer.out_features != new_layer.out_features:
        raise ValueError("Feature model must only expand first FFN input width")
    if type(base_model.agg) is not type(feature_model.agg) or dict(base_model.agg.hparams) != dict(feature_model.agg.hparams):
        raise ValueError("Aggregation changed; descriptor addition cannot explain this comparison")
    old, new = base_model.state_dict(), feature_model.state_dict()
    first_weight = source_name + ".weight"
    old_without_transform = {k for k in old if not k.startswith("X_d_transform.")}
    new_without_transform = {k for k in new if not k.startswith("X_d_transform.")}
    if old_without_transform != new_without_transform:
        raise ValueError("Source/feature model state keys differ beyond the descriptor transform")
    expanded = {}
    for name, value in new.items():
        if name.startswith("X_d_transform."):
            expanded[name] = value.clone()
        elif name == first_weight:
            widened = torch.zeros_like(value)
            widened[:, :graph_width] = old[name].to(device=value.device, dtype=value.dtype)
            expanded[name] = widened
        else:
            if old[name].shape != value.shape: raise ValueError(f"Unexpected state shape change: {name}")
            expanded[name] = old[name].to(device=value.device, dtype=value.dtype).clone()
    feature_model.load_state_dict(expanded, strict=True)
    return {"graph_width": graph_width, "added_descriptor_columns": new_layer.in_features - graph_width,
            "expanded_weight": first_weight, "initialization": "existing graph columns copied; added columns zero",
            "all_other_parameters_and_buffers": "copied; new descriptor transform retained",
            "parity": "same mathematical function; floating point roundoff may differ",
            "optimizer": "must be freshly constructed"}


def build_with_zero_extended_fresh_head(native_builder, hyperparameters: dict, **kwargs):
    """Construct a feature model paired to the graph-only initialization.

    Intended first feature experiment: same native encoder initialization and
    fresh graph FFN, same training budget; added descriptor weights start at zero.
    Native construction is on CPU. Fork its CPU RNG while building the expanded
    copy, leaving the caller's RNG at precisely the graph-only construction state.
    No pretrained/fitted graph weights are inferred from feature values.
    """
    import torch
    if int(kwargs.get("n_extra_descriptors", 0)) <= 0:
        raise ValueError("A positive n_extra_descriptors is required")
    base_kwargs = dict(kwargs)
    base_kwargs["n_extra_descriptors"] = 0
    base_kwargs["x_d_transform"] = None
    base_model = native_builder(hyperparameters, **base_kwargs)
    if any(p.device.type != "cpu" for p in base_model.parameters()):
        raise ValueError("Paired native model construction must happen on CPU before Trainer device placement")
    with torch.random.fork_rng(devices=[]):
        feature_model = native_builder(hyperparameters, **kwargs)
    note = copy_graph_model_weights(base_model, feature_model)
    note.update(mode="paired_fresh_head", rng="CPU RNG restored to graph-only construction state",
                comparison="same initial graph predictor and full training budget; descriptors start with zero contribution")
    return feature_model, note

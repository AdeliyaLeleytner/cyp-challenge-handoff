"""Public, versioned CYP measurements. Network calls occur only when loaders run.

Tidy rows retain assay domains, units and censoring. The wide helper defaults to
assay-specific, equality-only p-activity heads; binary outcomes are never silently
substituted for potency. No credentials or private cloud storage are used.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize

TOX21_CYP_ASSAYS = {"CYP1A2": 1671199, "CYP2C9": 1671198,
                    "CYP2D6": 1671196, "CYP3A4": 1671201}
HUMAN_CYP_ACCESSIONS = {"P05177": "CYP1A2", "P11712": "CYP2C9",
                       "P10635": "CYP2D6", "P08684": "CYP3A4"}
PUBLIC_HOSTS = {"pubchem.ncbi.nlm.nih.gov", "www.bindingdb.org", "bindingdb.org",
                "raw.githubusercontent.com", "huggingface.co"}
TIDY_COLUMNS = ["source", "source_version", "assay_id", "record_id", "compound_id",
                "SMILES", "canonical_smiles", "parent_key", "target", "endpoint",
                "task_kind", "relation", "value", "units", "raw_value", "p_activity",
                "p_relation", "is_censored", "is_point_eligible", "quality_flag",
                "activity_outcome", "replicate", "phenotype", "curve_class", "efficacy",
                "fit_r2", "original_source", "document_id", "target_organism",
                "assay_description", "provenance_json"]


class PublicDataError(RuntimeError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_json(path: Path, value: dict) -> None:
    _atomic_bytes(path, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode())


@contextmanager
def _file_lock(path: Path):
    import fcntl
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class CachedHTTP:
    """Paced public-only HTTP, verified immutable cache, retry + atomic writes.

    The injected opener supports tiny fixture tests without network access.
    Cache files are addressed by the caller's source/version directory plus a
    request hash; changing URL/POST parameters cannot silently reuse other data.
    """
    def __init__(self, cache_root: Path, *, timeout: float = 60, retries: int = 4,
                 min_interval: float = 0.35, opener=None):
        self.root = Path(cache_root)
        self.timeout, self.retries, self.interval = timeout, retries, min_interval
        self.opener = opener or urllib.request.urlopen
        self.records: list[dict] = []

    def _pace(self):
        with _file_lock(self.root / ".http-pace.lock") as handle:
            handle.seek(0)
            try:
                previous = float(handle.read() or "0")
            except ValueError:
                previous = 0
            delay = min(self.interval, self.interval - (time.time() - previous))
            if delay > 0:
                time.sleep(delay)
            handle.seek(0)
            handle.truncate()
            handle.write(str(time.time()))
            handle.flush()

    def fetch(self, url: str, relative: str, *, data: dict | None = None,
              expected_sha256: str | None = None, expected_md5: str | None = None) -> Path:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in PUBLIC_HOSTS or parsed.username or parsed.password:
            raise PublicDataError("Only allowlisted, credential-free HTTPS source URLs are supported")
        body = urllib.parse.urlencode(data or {}).encode() if data is not None else None
        signature = hashlib.sha256(url.encode() + b"\0" + (body or b"")).hexdigest()
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise PublicDataError("Cache path must stay inside cache_root")
        path = self.root / relative_path
        sidecar = path.with_name(path.name + ".http.json")
        with _file_lock(path.with_name(path.name + ".lock")):
            if path.exists() and sidecar.exists():
                record = json.loads(sidecar.read_text())
                actual = _digest(path)
                if record.get("request_sha256") != signature or actual != record.get("sha256"):
                    raise PublicDataError(f"Immutable cache mismatch: {path}")
                if expected_sha256 and actual != expected_sha256:
                    raise PublicDataError(f"Unexpected source hash: {path}")
                if expected_md5 and _digest(path, "md5") != expected_md5.lower():
                    raise PublicDataError(f"Unexpected source MD5: {path}")
                self.records.append(record)
                return path
            path.parent.mkdir(parents=True, exist_ok=True)
            last_error = None
            for attempt in range(self.retries):
                temporary = None
                try:
                    self._pace()
                    request = urllib.request.Request(url, data=body,
                        headers={"User-Agent": "CYP-public-data-ingestion/1.0", "Accept": "*/*"})
                    with self.opener(request, timeout=self.timeout) as response:
                        fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
                        with os.fdopen(fd, "wb") as output:
                            while True:
                                block = response.read(4 * 1024 * 1024)
                                if not block:
                                    break
                                output.write(block)
                            output.flush()
                            os.fsync(output.fileno())
                        temporary_path = Path(temporary)
                        actual = _digest(temporary_path)
                        if expected_sha256 and actual != expected_sha256:
                            raise PublicDataError(f"Downloaded SHA256 mismatch: {url}")
                        if expected_md5 and _digest(temporary_path, "md5") != expected_md5.lower():
                            raise PublicDataError(f"Downloaded MD5 mismatch: {url}")
                        record = {"url": url, "method": "POST" if body is not None else "GET",
                                  "request_sha256": signature, "retrieved_utc": _utc(),
                                  "sha256": actual, "bytes": temporary_path.stat().st_size,
                                  "path": str(path), "content_type": response.headers.get("Content-Type")}
                    os.replace(temporary, path)
                    temporary = None
                    _atomic_json(sidecar, record)
                    self.records.append(record)
                    return path
                except (urllib.error.URLError, TimeoutError, OSError, PublicDataError) as error:
                    last_error = error
                    if isinstance(error, PublicDataError):
                        break
                    if isinstance(error, urllib.error.HTTPError) and error.code not in {408, 429, 500, 502, 503, 504}:
                        break
                    if attempt + 1 < self.retries:
                        retry_after = error.headers.get("Retry-After", "") if isinstance(error, urllib.error.HTTPError) else ""
                        delay = float(retry_after) if str(retry_after).isdigit() else 2 ** attempt
                        time.sleep(min(60, max(1, delay)))
                finally:
                    if temporary and os.path.exists(temporary):
                        os.unlink(temporary)
            raise PublicDataError(f"Public download failed after bounded retries: {url}: {last_error}")


@lru_cache(maxsize=200000)
def _normalize(smiles: str) -> tuple[str | None, str | None]:
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None, None
        mol = rdMolStandardize.FragmentParent(mol)
        mol = rdMolStandardize.Uncharger().uncharge(mol)
        canonical = Chem.MolToSmiles(mol, isomericSmiles=True)
        Chem.RemoveStereochemistry(mol)
        return Chem.MolToSmiles(mol, isomericSmiles=False), canonical
    except Exception:
        return None, None


def normalize_parent_key(smiles: str) -> str | None:
    if not isinstance(smiles, str) or not smiles.strip():
        return None
    return _normalize(smiles)[0]


parent_key = normalize_parent_key


def normalize_and_exclude(df: pd.DataFrame, excluded_parent_keys: Iterable[str],
                          smiles_col: str = "SMILES") -> tuple[pd.DataFrame, dict]:
    """Preserve row order/original SMILES; return valid, non-excluded rows, reset index."""
    if smiles_col not in df:
        raise PublicDataError(f"Missing structure column {smiles_col}")
    excluded_set = set(excluded_parent_keys)
    result = df.copy()
    normalized = [(_normalize(s) if isinstance(s, str) and s.strip() else (None, None))
                  for s in result[smiles_col]]
    result["parent_key"] = [x[0] for x in normalized]
    result["canonical_smiles"] = [x[1] for x in normalized]
    invalid = result.parent_key.isna()
    excluded = result.parent_key.isin(excluded_set) & ~invalid
    audit = {"input_records": len(result), "invalid_structure_records": int(invalid.sum()),
             "excluded_official_parent_records": int(excluded.sum()),
             "excluded_official_parent_count": int(result.loc[excluded, "parent_key"].nunique()),
             "retained_records": int((~invalid & ~excluded).sum())}
    result = result.loc[~invalid & ~excluded].reset_index(drop=True)
    assert not set(result.parent_key) & excluded_set
    return result, audit


def parse_measurement(value) -> tuple[str, float | None]:
    if value is None or pd.isna(value):
        return "", None
    text = str(value).strip().replace("≤", "<=").replace("≥", ">=")
    match = re.fullmatch(r"([<>]=?|=|~)?\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?)", text)
    if not match:
        return "", None
    number = float(match.group(2))
    return (match.group(1) or "="), number if math.isfinite(number) else None


def to_p_activity(value: float | None, units: str, relation: str = "=") -> tuple[float | None, str]:
    if value is None or not math.isfinite(value):
        return None, ""
    normalized = units.strip().replace("µ", "u").replace("μ", "u")
    reverse = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "=": "=", "~": "~"}
    if normalized == "log10(M)":
        return -float(value), reverse.get(relation, relation)
    scales = {"M": 1., "mM": 1e-3, "uM": 1e-6, "nM": 1e-9, "pM": 1e-12}
    if normalized not in scales or value <= 0:
        return None, ""
    return -math.log10(value * scales[normalized]), reverse.get(relation, relation)


def _text(value) -> str:
    return "" if value is None or (not isinstance(value, (dict, list)) and pd.isna(value)) else str(value).strip()


def _base_record(**kwargs) -> dict:
    row = {c: None for c in TIDY_COLUMNS}
    row.update(kwargs)
    return row


def _read_pubchem_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "PUBCHEM_SID" not in frame or "PUBCHEM_CID" not in frame:
        raise PublicDataError(f"Expected full PubChem assay CSV, got columns {list(frame)[:8]}")
    sid = pd.to_numeric(frame.PUBCHEM_SID, errors="coerce")
    return frame.loc[sid.notna()].reset_index(drop=True)


def parse_tox21_frame(frame: pd.DataFrame, description: dict, smiles_by_cid: dict[int, str],
                      target: str, *, include_outcomes: bool = True) -> tuple[pd.DataFrame, dict]:
    """Parse full per-SID result CSV; retain all numeric fits but flag valid point views."""
    aid = int(description["aid"]["id"])
    version = str(description["aid"].get("version", "unknown"))
    definitions = {r["name"]: r for r in description.get("results", [])}
    fit_columns = [c for c in frame if re.fullmatch(r"Fit_LogAC50(?:-Replicate_\d+)?", c)]
    potency_columns = [c for c in frame if re.fullmatch(r"Potency(?:-Replicate_\d+)?", c)]
    suffixes = sorted({c[len("Fit_LogAC50"):] for c in fit_columns} | {c[len("Potency"):] for c in potency_columns})
    if not suffixes:
        raise PublicDataError(f"AID {aid} exposes no supported AC50 columns")
    rows = []
    outcome_counts = frame.get("PUBCHEM_ACTIVITY_OUTCOME", pd.Series(dtype=str)).value_counts().to_dict()
    for ordinal, raw in enumerate(frame.to_dict("records")):
        sid = _text(raw.get("PUBCHEM_SID"));cid_text = _text(raw.get("PUBCHEM_CID"))
        cid = int(float(cid_text)) if cid_text and re.fullmatch(r"\d+(?:\.0)?", cid_text) else None
        smiles = smiles_by_cid.get(cid) if cid is not None else None
        outcome = _text(raw.get("PUBCHEM_ACTIVITY_OUTCOME"))
        tag = _text(raw.get("PUBCHEM_RESULT_TAG")) or f"sid{sid}-row{ordinal}"
        provenance = json.dumps({"aid": aid, "version": version, "sid": sid, "cid": cid,
                                 "result_tag": tag, "source": description.get("aid_source")}, sort_keys=True)
        shared = dict(source="pubchem_tox21_cyp", source_version=f"aid{aid}-v{version}",
                      assay_id=f"PUBCHEM_AID_{aid}", compound_id=f"CID:{cid}" if cid else f"SID:{sid}",
                      SMILES=smiles, target=target, original_source="Tox21/NCATS", target_organism="Homo sapiens",
                      activity_outcome=outcome, provenance_json=provenance)
        if include_outcomes:
            val = {"active": 1., "inactive": 0.}.get(outcome.lower())
            rows.append(_base_record(**shared, record_id=f"{aid}:{tag}:outcome", endpoint="activity_outcome",
                task_kind="binary", relation="=" if val is not None else "", value=val, units="binary",
                raw_value=outcome, is_censored=False, is_point_eligible=False,
                quality_flag="known_outcome" if val is not None else "unknown_outcome"))
        for suffix in suffixes:
            fit_name, potency_name = "Fit_LogAC50" + suffix, "Potency" + suffix
            fit_def = definitions.get(fit_name, {})
            fit_rel, fit_value = parse_measurement(raw.get(fit_name))
            description_text = " ".join(fit_def.get("description", [])).lower()
            use_fit = fit_value is not None and re.search(r"\bmolar\b", description_text) is not None
            potency_rel, potency_value = parse_measurement(raw.get(potency_name))
            keep_unverified_fit = fit_value is not None and not use_fit and potency_value is None
            column = fit_name if use_fit or keep_unverified_fit else potency_name
            rel, value = (fit_rel, fit_value) if use_fit or keep_unverified_fit else (potency_rel, potency_value)
            if value is None:
                continue
            unit_code = definitions.get(column, {}).get("unit")
            units = "log10(M)" if use_fit else ("unverified_log10" if keep_unverified_fit else ("uM" if unit_code == 5 else f"pubchem_unit_{unit_code}"))
            p_value, p_relation = to_p_activity(value, units, rel)
            phenotype = _text(raw.get("Phenotype" + suffix)).lower()
            qc_ok = ("inhibitor" in phenotype or "antagonist" in phenotype) if phenotype else outcome.lower() == "active"
            bad_phenotype = any(term in phenotype for term in ["activator", "fluorescent", "cytotoxic", "inconclusive", "inactive"])
            qc_ok = qc_ok and not bad_phenotype
            eligible = p_value is not None and rel == "=" and qc_ok
            prov = json.loads(provenance);prov.update({"value_column": column, "unit_code": unit_code,
                                                       "unit_definition": definitions.get(column, {})})
            rows.append(_base_record(**{**shared, "provenance_json": json.dumps(prov, sort_keys=True)},
                record_id=f"{aid}:{tag}:{column}", endpoint="AC50", task_kind="regression", relation=rel,
                value=value, units=units, raw_value=_text(raw.get(column)), p_activity=p_value,
                p_relation=p_relation, is_censored=rel not in {"=", ""}, is_point_eligible=eligible,
                quality_flag="source_inhibitory_point" if eligible else "retain_fit_not_default_point",
                replicate=suffix.lstrip("-") or "unreplicated", phenotype=phenotype,
                curve_class=_text(raw.get("Fit_CurveClass" + suffix)), efficacy=_text(raw.get("Efficacy" + suffix)),
                fit_r2=_text(raw.get("Fit_R2" + suffix))))
    return pd.DataFrame(rows, columns=TIDY_COLUMNS), {"raw_assay_rows": len(frame), "parsed_measurements": len(rows),
        "outcome_counts": {str(k): int(v) for k, v in outcome_counts.items()}, "aid": aid, "version": version}


def _pubchem_smiles(client: CachedHTTP, cids: list[int]) -> dict[int, str]:
    result = {}
    url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/property/CanonicalSMILES,IsomericSMILES/CSV"
    for offset in range(0, len(cids), 200):
        batch = cids[offset:offset + 200]
        key = hashlib.sha256(",".join(map(str, batch)).encode()).hexdigest()[:20]
        path = client.fetch(url, f"pubchem/compound-properties/{key}.csv", data={"cid": ",".join(map(str, batch))})
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        column = next((c for c in ["SMILES", "IsomericSMILES", "ConnectivitySMILES", "CanonicalSMILES"] if c in frame), None)
        if "CID" not in frame or column is None:
            raise PublicDataError(f"Unexpected PubChem property schema: {list(frame)}")
        for cid, smiles in zip(frame.CID, frame[column]):
            if str(cid).isdigit() and smiles:
                result[int(cid)] = smiles
    return result


def load_tox21_cyp(client: CachedHTTP, *, targets=None, expected_version: int = 1,
                   sid_batch_size: int = 2000, include_outcomes: bool = True) -> tuple[pd.DataFrame, dict]:
    if not 1 <= sid_batch_size <= 3000:
        raise ValueError("sid_batch_size must be between1and3000")
    tables, audits = [], []
    for target in (list(TOX21_CYP_ASSAYS) if targets is None else list(targets)):
        aid = TOX21_CYP_ASSAYS[target];prefix = f"tox21_cyp/aid{aid}-v{expected_version}"
        base = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/assay/aid/{aid}"
        desc_file = client.fetch(base + "/description/JSON", prefix + "/description.json")
        desc = json.loads(desc_file.read_text())["PC_AssayContainer"][0]["assay"]["descr"]
        if int(desc["aid"]["id"]) != aid or int(desc["aid"].get("version", -1)) != expected_version:
            raise PublicDataError(f"AID{aid} version changed; review source before updating pinned version")
        concise_file = client.fetch(base + "/concise/CSV", prefix + "/concise.csv")
        concise = pd.read_csv(concise_file)
        if "SID" not in concise:
            raise PublicDataError(f"Missing SID in AID{aid} concise export")
        sids = sorted(pd.to_numeric(concise.SID, errors="coerce").dropna().astype(int).unique().tolist())
        frames = []
        for offset in range(0, len(sids), sid_batch_size):
            batch = sids[offset:offset + sid_batch_size]
            key = hashlib.sha256(",".join(map(str, batch)).encode()).hexdigest()[:16]
            path = client.fetch(base + "/CSV", f"{prefix}/full-{offset:06d}-{key}.csv",
                                data={"sid": ",".join(map(str, batch))})
            part = _read_pubchem_csv(path)
            returned = set(pd.to_numeric(part.PUBCHEM_SID, errors="coerce").dropna().astype(int))
            if not returned.issubset(set(batch)):
                raise PublicDataError(f"AID{aid} server returned SIDs outside requested batch")
            frames.append(part)
        frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if frame.empty:
            audits.append({"aid": aid, "raw_assay_rows": 0, "parsed_measurements": 0});continue
        cids = sorted(pd.to_numeric(frame.PUBCHEM_CID, errors="coerce").dropna().astype(int).unique().tolist())
        smiles = _pubchem_smiles(client, cids)
        table, audit = parse_tox21_frame(frame, desc, smiles, target, include_outcomes=include_outcomes)
        audit.update({"requested_sids": len(sids), "unique_cids": len(cids), "resolved_structure_cids": len(smiles)})
        tables.append(table);audits.append(audit)
    return (pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(columns=TIDY_COLUMNS)), {"assays": audits}


def _single_zip_text(path: Path):
    archive = zipfile.ZipFile(path)
    members = [n for n in archive.namelist() if not n.endswith("/") and not n.startswith("__MACOSX/")]
    names = [n for n in members if n.lower().endswith(".tsv")]
    if not names:
        names = [n for n in members if n.lower().endswith(".txt") and "readme" not in n.lower()]
    if len(names) != 1:
        archive.close();raise PublicDataError(f"Expected one TSV member in {path}, found {names}")
    return archive, io.TextIOWrapper(archive.open(names[0]), encoding="utf-8-sig", errors="replace")


def parse_bindingdb_stream(handle, *, release: str = "202610", require_native: bool = True) -> tuple[pd.DataFrame, dict]:
    """Streaming TSV reader: BindingDB explicitly permits variable chain-tail widths."""
    reader = csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE)
    header = next(reader, None)
    if header is None:
        raise PublicDataError("Empty BindingDB TSV")
    header = [c.strip() for c in header]
    required = {"BindingDB Reactant_set_id", "Ligand SMILES", "Target Name"}
    if not required.issubset(header):
        raise PublicDataError(f"Unexpected BindingDB header: {header[:12]}")
    access_columns = [c for c in header if c.startswith("UniProt (SwissProt) Primary ID of Target Chain")]
    if not access_columns:
        raise PublicDataError("BindingDB TSV has no SwissProt primary target accessions")
    audit = {"raw_rows": 0, "extra_chain_tail_rows": 0, "selected_target_rows": 0,
             "excluded_multichain_rows": 0, "excluded_nonhuman_rows": 0, "excluded_imported_source_rows": 0,
             "unsupported_target_rows": 0, "invalid_numeric_cells": 0}
    chain_count_column = next((c for c in header if c.startswith("Number of Protein Chains in Target")), None)
    rows = []
    for values in reader:
        audit["raw_rows"] += 1
        if len(values) > len(header):audit["extra_chain_tail_rows"] += 1
        raw = dict(zip(header, values))
        access = _text(raw.get(access_columns[0])).split()[0:1]
        accession = access[0] if access else ""
        if accession not in HUMAN_CYP_ACCESSIONS:
            audit["unsupported_target_rows"] += 1;continue
        chains = _text(raw.get(chain_count_column, "1"))
        if chains and chains not in {"1", "1.0"}:
            audit["excluded_multichain_rows"] += 1;continue
        organism = _text(raw.get("Target Source Organism According to Curator or DataSource"))
        if organism and "homo sapiens" not in organism.lower() and "human" not in organism.lower():
            audit["excluded_nonhuman_rows"] += 1;continue
        source = _text(raw.get("Curation/DataSource"))
        if require_native and source and "bindingdb" not in source.lower():
            audit["excluded_imported_source_rows"] += 1;continue
        audit["selected_target_rows"] += 1
        reaction = _text(raw.get("BindingDB Reactant_set_id"));monomer = _text(raw.get("BindingDB MonomerID"))
        doi = _text(raw.get("Article DOI"));pmid = _text(raw.get("PMID"));entry = _text(raw.get("BindingDB Entry DOI"))
        prov = {k: _text(raw.get(k)) for k in ["BindingDB Reactant_set_id", "BindingDB MonomerID", "Curation/DataSource",
             "Article DOI", "BindingDB Entry DOI", "PMID", "PubChem AID", "Patent Number", "Target Name",
             "pH", "Temp (C)", "PubChem CID", "Ligand InChI key", "Date of publication", "Date of curation"]}
        prov["target_accession"] = accession
        for endpoint in ["IC50", "Ki", "Kd", "EC50"]:
            key = endpoint + " (nM)";text = _text(raw.get(key))
            if not text:continue
            relation, value = parse_measurement(text)
            if value is None:
                audit["invalid_numeric_cells"] += 1;continue
            p_value, p_relation = to_p_activity(value, "nM", relation)
            eligible = p_value is not None and relation == "="
            rows.append(_base_record(source="bindingdb_native_articles", source_version=release,
                assay_id=f"BDB_RSID_{reaction}", record_id=f"{reaction}:{endpoint}", compound_id=f"BDB:{monomer}",
                SMILES=_text(raw.get("Ligand SMILES")), target=HUMAN_CYP_ACCESSIONS[accession], endpoint=endpoint,
                task_kind="regression", relation=relation, value=value, units="nM", raw_value=text,
                p_activity=p_value, p_relation=p_relation, is_censored=relation != "=", is_point_eligible=eligible,
                quality_flag="native_equal_point" if eligible else "censored_or_invalid_point", original_source=source,
                document_id=doi or ("PMID:" + pmid if pmid else entry), target_organism=organism,
                provenance_json=json.dumps(prov, sort_keys=True)))
    return pd.DataFrame(rows, columns=TIDY_COLUMNS), audit


def _fetch_bindingdb_zip(client: CachedHTTP, filename: str, release: str) -> Path:
    url = "https://www.bindingdb.org/rwd/bind/downloads/" + filename
    checksum = client.fetch(url.removesuffix(".zip") + ".md5", f"bindingdb/{release}/{filename}.md5")
    found = re.findall(r"\b[0-9a-fA-F]{32}\b", checksum.read_text())
    if len(set(found)) != 1:
        raise PublicDataError(f"Ambiguous BindingDB MD5 file for {filename}")
    return client.fetch(url, f"bindingdb/{release}/{filename}", expected_md5=found[0])


def _join_bindingdb_assays(table: pd.DataFrame, mapping_path: Path, assay_path: Path) -> tuple[pd.DataFrame, dict]:
    wanted = {json.loads(p)["BindingDB Reactant_set_id"] for p in table.provenance_json}
    archive, stream = _single_zip_text(mapping_path);mapping = {}
    try:
        for row in csv.reader(stream, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(row) >= 2 and row[0].strip() in wanted:
                mapping[row[0].strip()] = row[1].strip()
    finally:stream.close();archive.close()
    wanted_assays = {k for text in mapping.values() for k in re.split(r"[,; ]+", text) if k}
    archive, stream = _single_zip_text(assay_path);descriptions = {}
    try:
        for row in csv.reader(stream, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(row) >= 3:
                key = row[0].strip() + "_" + row[1].strip();value = row[2]
            elif len(row) == 2:
                key,value = row[0].strip(),row[1]
            else:continue
            if key in wanted_assays:descriptions[key] = value
    finally:stream.close();archive.close()
    result = table.copy();matched = 0
    for idx, row in result.iterrows():
        prov = json.loads(row.provenance_json);rsid = prov["BindingDB Reactant_set_id"]
        ids = [x for x in re.split(r"[,; ]+", mapping.get(rsid, "")) if x]
        if ids:
            result.at[idx,"assay_id"] = "BDB_ASSAY_" + ";".join(sorted(ids));matched += 1
            result.at[idx,"assay_description"] = json.dumps({k:descriptions.get(k) for k in ids},sort_keys=True)
        prov["assay_ids"] = ids;prov["assay_join_status"] = "mapped" if ids else "unresolved_reaction_set_only"
        result.at[idx,"provenance_json"] = json.dumps(prov,sort_keys=True)
    return result, {"assay_mapped_measurements": matched, "assay_unmapped_measurements": len(result)-matched,
                    "assay_descriptions_found": len(descriptions)}


def load_bindingdb_native_articles(client: CachedHTTP, *, release: str = "202610",
                                   join_assays: bool = True) -> tuple[pd.DataFrame, dict]:
    if not re.fullmatch(r"20\d{4}", release):
        raise ValueError("BindingDB release must be YYYYMM")
    path = _fetch_bindingdb_zip(client, f"BindingDB_BindingDB_Articles_{release}_tsv.zip", release)
    archive, stream = _single_zip_text(path)
    try:table,audit = parse_bindingdb_stream(stream,release=release)
    finally:stream.close();archive.close()
    if join_assays and not table.empty:
        mapping = _fetch_bindingdb_zip(client, f"BindingDB_rsid_eaids_{release}_tsv.zip", release)
        assays = _fetch_bindingdb_zip(client, f"BindingDB_Assays_{release}_tsv.zip", release)
        table,join_audit = _join_bindingdb_assays(table,mapping,assays);audit.update(join_audit)
    audit.update({"release":release,"parsed_measurements":len(table),
                  "license_note":"BindingDB Info links native data CC-BY; ChEMBL imports retain CC-BY-SA. Native-only rows selected."})
    return table,audit


def load_public_data(asset_root: Path, sources=None, excluded_parent_keys=(), config=None,
                     known_parent_keys=None) -> tuple[pd.DataFrame, dict]:
    """Remote-runtime entrypoint. Return tidy filtered measurements plus audit manifest.

    sources: tox21_cyp, bindingdb_native_articles. Any unsupported source raises;
    adapters never silently substitute other assays or unfiltered data.
    """
    config = dict(config or {});root = Path(asset_root)/"public_data";client=CachedHTTP(root/"cache",
        timeout=float(config.get("http_timeout",60)),retries=int(config.get("http_retries",4)),
        min_interval=float(config.get("http_min_interval",.35)))
    sources = list(["tox21_cyp","bindingdb_native_articles"] if sources is None else sources)
    excluded=set(excluded_parent_keys);known=None if known_parent_keys is None else set(known_parent_keys)
    tables=[];audits={}
    for source in sources:
        if source == "tox21_cyp":
            raw,details=load_tox21_cyp(client,targets=config.get("targets"),expected_version=int(config.get("tox21_version",1)),
                                     sid_batch_size=int(config.get("sid_batch_size",2000)),include_outcomes=bool(config.get("include_outcomes",True)))
        elif source == "bindingdb_native_articles":
            raw,details=load_bindingdb_native_articles(client,release=str(config.get("bindingdb_release","202610")),
                                                       join_assays=bool(config.get("bindingdb_join_assays",True)))
        else:raise PublicDataError(f"Unsupported public source {source!r}")
        clean,identity=normalize_and_exclude(raw,excluded)
        duplicate_key=["source","source_version","assay_id","record_id","target","endpoint","relation","raw_value","parent_key"]
        duplicate_count=int(clean.duplicated(duplicate_key).sum());clean=clean.drop_duplicates(duplicate_key).reset_index(drop=True)
        parents=set(clean.parent_key);details.update(identity);details.update({"exact_duplicate_records_removed":duplicate_count,
            "retained_measurements":len(clean),"retained_unique_parents":len(parents),
            "net_new_parent_count":None if known is None else len(parents-known),
            "overlap_existing_parent_count":None if known is None else len(parents&known),
            "eligible_point_measurements":int(clean.is_point_eligible.fillna(False).sum()),
            "endpoint_counts":{str(k):int(v) for k,v in clean.endpoint.value_counts().items()}})
        tables.append(clean);audits[source]=details
    tidy=pd.concat(tables,ignore_index=True) if tables else pd.DataFrame(columns=TIDY_COLUMNS)
    signature=hashlib.sha256(json.dumps({"sources":sources,"config":config,"excluded":sorted(excluded)},sort_keys=True).encode()).hexdigest()[:20]
    output=root/"derived"/signature;output.mkdir(parents=True,exist_ok=True)
    path=output/"measurements.csv";_atomic_bytes(path,tidy.to_csv(index=False).encode())
    manifest={"created_utc":_utc(),"schema_version":1,"source_audits":audits,"sources":sources,"config":config,
              "excluded_parent_count":len(excluded),"excluded_parent_sha256":hashlib.sha256("\n".join(sorted(excluded)).encode()).hexdigest(),
              "known_parent_count":None if known is None else len(known),"retained_records":len(tidy),
              "retained_unique_parents":int(tidy.parent_key.nunique()),"table_path":str(path),"table_sha256":_digest(path),
              "downloads":client.records,"normalization":"FragmentParent, uncharge, remove stereo; no tautomer canonicalization",
              "unknown_labels":"Retained as missing/unknown; never converted to inactive or numerical potency"}
    _atomic_json(output/"manifest.json",manifest)
    return tidy,manifest


def wide_auxiliary_table(tidy: pd.DataFrame, *, group_by=("source","assay_id","target","endpoint"),
                         endpoints=("IC50","AC50"), require_source_quality: bool = True) -> tuple[pd.DataFrame,list[str],dict]:
    """Equality-only p-activity heads. Changing group_by explicitly opts into assay pooling.

    Aggregation is median within exact normalized isomeric molecule and head;
    censored values and binary outcomes are not used as exact potencies.
    """
    finite_activity = np.isfinite(pd.to_numeric(tidy.p_activity, errors="coerce"))
    use=tidy.loc[tidy.task_kind.eq("regression") & tidy.endpoint.isin(endpoints) & tidy.p_relation.eq("=") & finite_activity].copy()
    if require_source_quality:use=use.loc[use.is_point_eligible.fillna(False).astype(bool)]
    if use.empty:return pd.DataFrame(columns=["Molecule_Name","SMILES","parent_key"]),[],{"records_used":0,"heads":{},"group_by":list(group_by)}
    headmap={};heads=[]
    for values in use[list(group_by)].itertuples(index=False,name=None):
        key=json.dumps(list(values),ensure_ascii=True);digest=hashlib.sha256(key.encode()).hexdigest()[:12]
        head="aux_"+re.sub(r"[^A-Za-z0-9]+","_","_".join(str(x) for x in values))[:100]+"_"+digest
        headmap[head]=dict(zip(group_by,values));heads.append(head)
    use["head"]=heads
    grouped=use.groupby(["canonical_smiles","parent_key","head"],dropna=False).p_activity.median().unstack("head")
    wide=grouped.reset_index().rename(columns={"canonical_smiles":"SMILES"})
    wide.insert(0,"Molecule_Name",["PUBLIC_"+hashlib.sha256(s.encode()).hexdigest()[:20] for s in wide.SMILES])
    names=sorted(headmap);wide=wide[["Molecule_Name","SMILES","parent_key"]+names]
    return wide,names,{"records_used":len(use),"molecules":len(wide),"heads":headmap,"group_by":list(group_by),
                        "aggregation":"median within normalized isomeric identity and specified head; equality-only"}


def build_public_auxiliary_dataset(
    train_df: pd.DataFrame, tidy: pd.DataFrame, *,
    excluded_parent_keys: Iterable[str], primary_columns: Iterable[str],
    group_by=("source", "target", "endpoint"), endpoints=("IC50", "AC50"),
    require_source_quality: bool = True,
) -> tuple[pd.DataFrame, list[str], dict]:
    """Attach public auxiliary heads to official training rows and append public rows.

    This function does no networking or model fitting. Supply the official rows of
    the current fitting fold only. excluded_parent_keys applies to public rows
    only: the campaign policy supplies ALL official train and test parents, so
    exactly the same uncontaminated external corpus is used in every fold.
    Exclusion is parent-level (stereo removed); attachment is exact normalized
    isomeric identity, so stereoisomer labels are never copied between molecules.
    Primary labels are untouched and are missing for appended public-only rows.

    The default deliberately pools assays within source/target/endpoint for a
    small auxiliary-head set. Pass assay_id in group_by for separate assay heads.
    All raw assay provenance remains in the supplied tidy table and its manifest.
    """
    primary_columns = list(primary_columns)
    required = ["Molecule_Name", "SMILES"] + primary_columns
    missing = [c for c in required if c not in train_df]
    if missing:
        raise PublicDataError(f"Official training table is missing columns: {missing}")
    if train_df.Molecule_Name.isna().any() or train_df.Molecule_Name.duplicated().any():
        raise PublicDataError("Official training molecule IDs must be present and unique")
    if len(primary_columns) != len(set(primary_columns)):
        raise PublicDataError("Primary columns must be unique")
    excluded = set(excluded_parent_keys)
    official, official_audit = normalize_and_exclude(train_df, ())
    if len(official) != len(train_df):
        raise PublicDataError("Official training rows contain invalid structures: "
                              + json.dumps(official_audit, sort_keys=True))
    public, exclusion_audit = normalize_and_exclude(tidy, excluded)
    wide, head_names, wide_meta = wide_auxiliary_table(
        public, group_by=group_by, endpoints=endpoints,
        require_source_quality=require_source_quality)
    collisions = set(head_names) & set(train_df.columns)
    if collisions:
        raise PublicDataError(f"Auxiliary head names collide with official columns: {sorted(collisions)}")
    if wide.SMILES.duplicated().any():
        raise PublicDataError("Auxiliary table has duplicate normalized isomeric identities")

    # Reindex rather than merge to retain exactly the official input order and IDs.
    lookup = wide.set_index("SMILES")
    official_identity = official.canonical_smiles.tolist()
    for head in head_names:
        official[head] = lookup[head].reindex(official_identity).to_numpy()
    official_parents = set(official.parent_key)
    official_isomers = set(official_identity)
    public_only = wide.loc[~wide.SMILES.isin(official_isomers)].copy()
    public_only["canonical_smiles"] = public_only.SMILES
    if set(public_only.Molecule_Name) & set(official.Molecule_Name):
        raise PublicDataError("Generated public molecule IDs collide with official molecule IDs")
    for column in primary_columns:
        public_only[column] = np.nan
    combined = pd.concat([official, public_only], ignore_index=True, sort=False)
    # Do not permit a future refactor to substitute auxiliary values for primary labels.
    pd.testing.assert_frame_equal(
        combined.iloc[:len(train_df)][primary_columns].reset_index(drop=True),
        train_df[primary_columns].reset_index(drop=True), check_dtype=False)
    assert not set(public.parent_key) & excluded
    assert not set(public_only.parent_key) & excluded
    assert combined.iloc[len(train_df):][primary_columns].isna().all().all()

    source_versions = {}
    if not public.empty:
        for source, rows in public.groupby("source", dropna=False):
            source_versions[str(source)] = {
                "versions": sorted(set(rows.source_version.astype(str))),
                "assay_ids": sorted(set(rows.assay_id.astype(str))),
                "retained_tidy_records": len(rows),
                "retained_parents": int(rows.parent_key.nunique()),
            }
    metadata = {
        "schema_version": 1, "official_rows": len(official),
        "public_only_rows": len(public_only), "combined_rows": len(combined),
        "official_rows_with_auxiliary_labels": int(official[head_names].notna().any(axis=1).sum()),
        "public_only_net_new_parents": len(set(public_only.parent_key) - official_parents),
        "primary_columns": primary_columns, "auxiliary_heads": head_names,
        "auxiliary_nonmissing_counts": {h: int(combined[h].notna().sum()) for h in head_names},
        "public_exclusion": exclusion_audit, "wide_table": wide_meta,
        "source_metadata": source_versions,
        "excluded_parent_count": len(excluded),
        "excluded_parent_sha256": hashlib.sha256("\n".join(sorted(excluded)).encode()).hexdigest(),
        "join_identity": "FragmentParent + uncharge + canonical isomeric SMILES; no tautomer canonicalization",
        "row_order": "Original official training order followed by deterministic public-only rows",
        "primary_label_policy": "Official labels preserved; appended public rows have unknown primary labels",
        "heldout_policy": "Exclusion applies only to public rows; caller supplies all official train+test parents for campaign policy",
    }
    return combined, head_names, metadata

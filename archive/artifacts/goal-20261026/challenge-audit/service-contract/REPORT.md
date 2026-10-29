# ADMETlab service-contract audit

**Conclusion:** no demonstrated asynchronous alternative was found, and `feature=False` has not been shown equivalent to our `web_default` outputs. Retain the current web-derived feature regime.

One read-only public-document request was made: `GET /api/openapi.json`, HTTP200 at **25 October 2026 23:42:57 UTC / 26 October 02:42:57 Moscow**. The returned JSON matches the saved 24 October schema. SHA256: `35bbe69850c637e09eb3f395a70f9438a4647d999e56772f43c25ed27d127008`. No prediction requests, proxy calls, collection changes, or acquisition runs were performed. [Receipt](read-only-document-receipt.json), [current OpenAPI](official-openapi-current.json).

## Exact documented interface

| Route | Request/response evidence | Relevance |
|---|---|---|
| `POST /api/single/admet` | `SMILES` is one string; `feature` boolean defaults **true**. Responses 200/400 are documented. Saved successful response includes `raw_smiles`, standardized `smiles`, complete grouped predictions, structure SVG and `taskid`. | Synchronous single-molecule prediction; no early acknowledgement demonstrated. |
| `POST /api/single/admetFile` | `{ "taskId": "..." }`; response 200 file. Historical CCO download succeeded. | Retrieves an already-created single-molecule result. |
| `POST /api/single/admetPDF` | Same task-ID schema; response 200 file. | PDF retrieval, not job status. |
| `POST /api/admetCSV` | `{ "taskId": "..." }`; response 200 file. | Existing batch-result export; existence does not establish an async submission route. |
| `POST /api/uploadfile` | Only 410 Gone is documented. | Not an available asynchronous batch-upload option. |
| `POST /api/molsvg`, `/api/washmol` | Structure rendering/cleaning. | Not ADMET job submission/polling. |

The inspected OpenAPI has no 202 response, `queued`/`running` contract, status/poll route, client-supplied idempotency key, or lookup by original request. Its generic JSON response schema does not itself prove execution semantics, but the successful saved calls returned calculated values in the same response as the task ID. Therefore **a task ID is evidence of result retrieval identity, not evidence of an immediate async acknowledgement**. If that response is lost, the documented interface provides no established way to recover its missing ID. [Official OpenAPI](https://admetlab3.scbdd.com/api/openapi.json).

The public Markdown still describes legacy `POST /api/admet` with a string/list, optional `feature`/`uncertain`, and synchronous chunking into 1000-molecule lists. That route is absent from current OpenAPI; a saved read-only GET returned404. This discrepancy is not authorization to invent a batch endpoint. The web form simply POSTs `/server/screeningCal` and shows a waiting modal; no early-ID polling workflow appears in the inspected frontend. [Legacy documentation](https://admetlab3.scbdd.com/apis/#/two), [examples](https://admetlab3.scbdd.com/apis/#/three).

## Source-mode equivalence

The legacy documentation describes `feature` as selecting models with descriptors. Current single-molecule OpenAPI accepts explicit `false`, but its default is **true**; omitting the flag would not test the proposed alternative. The web form has no corresponding visible flag, and its backend model selection/version is not exposed by the form code.

Saved successful API requests used `feature=True`. Paired comparisons against the web export disagree on 80 endpoints for ethanol and 81 for nitrobenzene, using the prior comparison's 1e-7 reporting tolerance. These are substantial model differences, not merely names or formatting: ethanol CYP1A2-inhibition is0.04461 in APItrue versus0.27368 on the web; CYP3A4-substrate is0.35245 versus0.83436. The tolerance is a diagnostic reporting setting, not a new equivalence criterion. [Saved paired comparison](../../../chemeleon-native-next-20261024/admetlab-access/webbatch-three-probe/api-web-comparison.json).

API JSON exposed 119 endpoint values in the successful probes. Its CSV had 125 columns: `taskId`/`smiles`, 120 usable endpoint identities including `Other_assay_interference`, and three empty legacy fields (`cl-int`, `LM-mouse`, `LM-rat`). The web CSV has 122 columns: `raw_smiles`, `smiles`, and 120 endpoints. Consequently, matching endpoint names or deleting the three empty API fields would **not** establish a matching predictor. The API JSON's `raw_smiles` and returned task ID are also needed for trustworthy input association; the API CSV alone lacks `raw_smiles`.

No successful `feature=False` response paired with web output was found in the saved evidence. Third-party client canary code mentionsFalse, but a code setting or mocked test is not prediction-equivalence evidence. Current feature-cache readiness code explicitly requires `source_mode=web_default`, `backend=documented_web_batch`, and `api_probe_vectors_used=false`; bypassing that check would erase an unresolved source-mode difference.

## Minimal future equivalence investigation, if separately authorized

Start with explicit APIfalse calls for a few exact inputs whose web outputs are already cached—ethanol/nitrobenzene provide existing diagnostic references, plus chemically relevant cached structures with stereochemistry or ionization/salts. Keep these outputs quarantined as `api_feature_false`, not production web rows. Obtain both JSON and the task-ID CSV so all 120 usable endpoints and the request-to-service-structure mapping can be compared.

Check exact input identity, returned chemical graph/stereo transformations, endpoint units/probability meanings, numeric values across **all** endpoints, and structural-alert lists/counts. Any systematic material discrepancy falsifies interchangeability. If apparent matches occur, repeat enough paired cases to characterize numerical variation and extend across representative chemistry; a handful of matching rows cannot prove global model identity. Contemporary web repeats or a maintainer-confirmed backend model/version mapping may be necessary to separate source-mode effects from service drift. Column names alone are insufficient.

Even demonstrated empirical APIfalse agreement would provide **shorter single-molecule synchronous calls**, not an established immediate-ID asynchronous service. Obtaining the full CSV feature set would ordinarily require a prediction call plus a retrieval call per molecule, so throughput must be evaluated separately from source equivalence.

The exact inspected files and hashes are recorded in [contract-findings.json](contract-findings.json). No proposed equivalence probe was executed.

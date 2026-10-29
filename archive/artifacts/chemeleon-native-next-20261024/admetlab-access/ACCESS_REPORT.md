# Live verification update — 2026-10-24

The earlier Mac-only access blocker was resolved by accessing the official service from the already-authorized Vast host. Live officialOpenAPI and API docs returnedHTTP200. One public ethanol(`CCO`) prediction using`POST /api/single/admet`, `{"SMILES":"CCO","feature":true}` returnedHTTP200/statussuccess in1.55seconds. Noauthneeded. Rawresponse, metadata, officialOpenAPI and documentationMarkdown are savedin`live-probe/`.

LiveJSON returnedexactly119numericendpointvalues. Its groupedcategories were21physicochemical,20medchem,9absorption,9distribution,14metabolism,2excretion,24toxicity,12tox21,8toxicityrules. No uncertainty fields were present.

The same task's `POST /api/single/admetFile` CSVdownload succeeded. CSVhas125columns:119JSONendpointnames plus taskId/smiles andfourCSV-onlycolumns. `Other_assay_interference`is a genuinelyadditionalnumericendpoint(0.6620000004768372forCCO); cl-int/LM-mouse/LM-rat areemptyforCCO. AllJSONnamesappearverbatiminCSV, so theextraendpointisnotanunderscore/namealias. CSVrulelistsarealsopreservedwithcounts/patternencodings.

OfficialcurrentOpenAPIsupportssingle-stringpredictions, CSV/PDFlookupsbytaskId, moleculeSVG/wash; `/api/uploadfile`is410Gone. Read-onlyGETtolegacy`/api/admet`returned404. TheofficialMarkdownstilladvertiseslegacybatch`/api/admet`and`uncertain`; theliveOpenAPI/successfulresponsearesourcesoftruthforcurrentcontract. CSVlookupacceptsonlytaskId, soallavailableoutputsrequiretworequestspermolecule.

Boundedclientready(notlaunchedbyhelper): ORXexperiment`da109f67-66be-4e06-8c6d-dea5561ebebc`, commit`d07b403519d3d4711b42e34cfd0bdfbc5f3f262d`, privateworktree`../admetlab-worktree`. Global4requests/sacrossbothPOSTtypes,max8inflight,atomicJSON+CSVcache,CSV-onlyresume,Retry-Afterandcircuitbreaker; priority0milestonebeforepublicqueue. Eightmocktests passed. Rootownsbulkdispatchandcompute.

---

# ADMETlab 3.0 access audit — 2026-10-24

## Practical state

Official host: https://admetlab3.scbdd.com/
Official API documentation: https://admetlab3.scbdd.com/apis/
Official paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11223840/ (doi:10.1093/nar/gkae236).

The official documentation/paper describe public access without registration. No missing API key has been identified. The obstacle observed from this Mac is HTTPS/TLS handshake timeouts, not authentication. The web retrieval service can see the homepage and indexed documentation text, but its current page extraction for the JavaScript API docs returns only Loading. No prediction request was sent and no endpoint values were obtained.

`read-access-probes.json` records 12-second TLS handshake timeouts for the official docs and proposed OpenAPI route. An independent curl call also timed out after15seconds. Read-only access from a different network, such as the already-authorized GPU server, can distinguish local routing from a globally unavailable service.

## Coverage and uncertainty

The advertised platform total is119features. These are NOT119distinct learned ADMET labels: the official homepage describes77modeled endpoints alongside calculated physicochemical/medicinal-chemistry properties and rule-based alerts. Paper Table1 lists21physicochemical,20medicinalchemistry,34ADME,36toxicity and8toxicophore-rule categories (119total); the live homepage says19medicinalchemistry, an internal discrepancy. Therefore use the complete actual returned schema, not a hard-coded119-column assertion or categorysum. Preserve every returned endpoint and all available uncertainty outputs, plus raw response.

The paper says model uncertainty is available viaAPI. The currently maintained third-party client says the old `uncertain` requestflag is deprecated and must not be sent. Availability and exact returned names cannot yet be certified from a successful live response. Calculated descriptors/rule outputs do not acquire model uncertainty merely because the platform also returns uncertainty for learned endpoints.

## Candidate current API contract (secondary evidence, NOT yet live-verified)

The maintained ToxMCP client source and tests inspected on2026-10-24 use:

- `POST /api/single/admet` with `{"SMILES":"CCO","feature":true}` — STRING-valued uppercaseSMILES, one molecule per request.
- `POST /api/washmol` with `{"SMILES":["CCO"]}`.
- `POST /api/admetCSV` with `{"taskId":"returned-task-id"}`.
- `POST /api/molsvg` with stringSMILES.

Source: https://github.com/ToxMCP/admetlab-mcp/blob/main/src/admetlab_mcp/client/admet_client.py
Tests: https://github.com/ToxMCP/admetlab-mcp/blob/main/tests/test_prediction_contract.py
Stored copies: tox-src_admetlab_mcp_client_admet_client.py, tox-tests_test_prediction_contract.py.

This client explicitly fixed a previous nonexistent `/api/admet` route and notes a prior upstream `BSEP` server error (observed2026-07-22). That historical outage is not proof that predictions fail today. Do not adopt generic third-party snippets that POST a lowercase `smiles` list to `/api/predict` or `/api/admet`. Do not treat the client's1000-SMILES MCP-call limit as an upstream batch endpoint limit: it fans out one request per molecule.

## Rate and workload limits

Official indexed API docs advise≤5requests/second and say the service is not designed for millions of simultaneous requests. They currently display a notice about attacks, resource exhaustion and instability, and suggest contacting the authors for large calculations. No precise official maximum molecules per batch was recoverable. The public web Screening function accepts SMILES/SDF/TXT/CSV batches, but its present input limit was not established.

For root's authorized public molecules, prefer a persisted deduplicated queue, concurrency1initially and≤1request/second until servicehealth is measured; never exceed official5rps. Stop on repeated5xx/429, preserve taskIDs and returned results, respect Retry-After, and avoid resubmitting a successfully issued task when only downloadfailed. One successful simple-molecule test with actualJSON+CSVschema is required before bulkdispatch. No author has been contacted; sending messages needs explicit userinstruction.

## Local models / licensing

The official homepage LICENSE link points to https://github.com/antwiser/ADMETlab-3.0/blob/main/LICENSE, which returned404. No official downloadable v3weights or runnable local v3repository was established. The paper's CC-BY-NC4.0 license covers the publication and is not evidence of a software/checkpointlicense. Do not substitute a public v2model or unofficial implementation and call itADMETlab3.0. Hostedpublicprediction is explicitly described as free/no-login; commercial/rehosting rights remain separate.

## Feature extraction proposal

Keep identity columns(inputSMILES, canonicalkey, returnedwashedSMILES, moleculeID), source/modeloptions, requesttime, taskID, rawJSON and rawCSV. Generate one feature table from every available numeric/probability/count output and returneduncertainty; preserve nonnumeric substructurealerts separately and encode them explicitly if used. Fit imputation/scaling on eachtrainingfoldonly. Distinguish these external predictions from experimental labels. The model's CYPinhibitor/substrate probabilities are potentially usefulpriorfeatures, but they are not the challenge's pIC50. Retain all endpoints for the requestedinitialcomparison; avoid silently droppingCYPfeatures.

A complete benchmark also needs an external-model provenance note: exactADMETlabtrainingmembership/version is notknown from a successful result yet. This is an externallypredictedfeature experiment, not evidence of additional measuredchallenge labels.

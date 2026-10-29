# Live transport diagnostic result

The relay path worked on the same live tenant and with the same registered identity for which the direct path stalled. This distinguishes the direct transport/forwarding path from authentication and model-runtime readiness; it does not isolate the VPN versus provider-side cause.

| Probe | TCP connected | SSH banner/key exchange | Authenticated | Command outcome |
|---|---|---|---|---|
| direct, IPv4 `true` | True | False / False | False | exit255, 12.03s |
| relay, IPv4 `true` | True | True / True | True | exit0, 3.80s |

Relay runtime readback succeeded: Python3.11.11, `/opt/conda`, Torch2.6.0+cu124, CUDA available, one NVIDIA GeForce RTX4060Ti. There were no package installs, model runs, optimizer steps, global route/VPN changes or identity changes. Verbose traces with per-line timestamps are retained privately.

The direct connection established TCP but received no SSH identification banner within the fixed12-second connection limit. It did not reach authentication. The relay completed authentication and remote `true`, then the Python/CUDA command. Therefore wrong credentials or an unbooted container do not explain this paired observation. It does not prove what happened on the two earlier tenants; their evidence remains separately qualified.

No reviewed continuation arrived before the diagnostic deadline. The guard stopped compute at its bound, and `destroy --yes` plus a fresh absence readback confirmed deletion. No probes were made after deletion. A future authorized profile should use the verified relay route and a newly reviewed deadline/cost, not the failed direct endpoint. No further lease was created.

Provider-reported diagnostic charge: $0.015, within the$0.10 maximum. Cumulative private-campaign reported spend: $4.101; remaining campaign cap: $5.899. Rounded charges may receive a minor final settlement adjustment.

Evidence: `DIAGNOSTIC_RESULT.json`, both `*-true.receipt.json`, `relay-runtime.receipt.json`, private timestampedJSONL/stderr traces, `TEARDOWN.json`, `BUDGET.json`, and the immutable lease record.

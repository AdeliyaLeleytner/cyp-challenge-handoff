# P7R startup versus SSH-readiness failures

The two attempts failed at different stages. No model training or profiling run launched.

## Instance57843947: container provisioning did not complete

The API stayed in `loading` with an unchanged Docker-layer checksum message. Logs reported `No such container: C.57843947`. No SSH endpoint or model runtime was verified. The underlying image-download/provider cause is unknown; this does not show that the pinned image itself is invalid. The instance was explicitly destroyed and independently absent on readback at17:02:13UTC.

## Instance57848621: container and SSH service started; client session did not become usable

The saved boot log shows apt/package setup completed. `sshd` reported listening on0.0.0.0:22 at17:43:22UTC, and the API reported `running`. Thus this was not an image-provisioning failure.

The client tool outputs contain connection timeouts and explicit `Connection timed out during banner exchange` messages. One SCP attempt saved an ED25519 host key locally, so at least one connection progressed through host-key exchange. The server log contains connections closed during `preauth`. Those server entries lack sufficiently detailed timestamps/identities to match every client attempt. No `Permission denied (publickey)`, accepted-authentication record, remote Python output or CUDA readback was captured. There is no evidence of a failed model command: the command was never observed running.

No `ssh -vvv` trace was collected while the instance was live. The available stderr is the ordinary task-tool transcript, not a complete packet/handshake diagnosis. The later relay attempt happened after the budget guard had stopped the instance; its timeout is not valid evidence that the relay would have failed against a running container.

The10-minute deadline was17:52:41UTC. The guard recorded provider status `exited` at17:53:28UTC after stop/readback. Destructive teardown with `--yes` and fresh absence verification completed at17:57:06UTC. Remote originals contained no trained model results. No further rental attempt is authorized or running.

## Current read-only local evidence

- Effective alias: root login, explicit `~/.ssh/id_ed25519`, `IdentitiesOnly yes`, one connection attempt, ConnectTimeout15seconds, ServerAliveInterval20/CountMax3. No effective ProxyCommand, ProxyJump or ControlMaster was configured.
- The private-key file exists with mode600; its contents were not read or printed. Its corresponding local public key matches one of the currently registered Vast account public keys. This does not retrospectively prove the deleted container's authorized_keys contents.
- A local known-host entry exists for the failed direct endpoint, consistent with the captured host-key exchange warning.
- Current local route lookups put both the failed alternative IP and the earlier successful host IP through `utun5`. These lookups sent no probes to tenant ports. They describe the current route, not a saved route at failure time. VPN-path involvement is possible, but this evidence does not establish that the VPN caused the failure, especially because the prior successful host currently uses the same tunnel interface.
- The IPv6/address-family warning in the provider log is retained, but cannot be assigned causal responsibility from the available trace.

The defensible classification is intermittent/failed SSH transport or early-handshake readiness, with incomplete evidence to distinguish local tunnel path, provider forwarding, or server-side readiness. It is not a demonstrated wrong-key error, bad Python environment, bad model implementation or failed image provisioning on the second host.

## Future discrimination, only on a newly authorized live owned instance

Capture a timestamped `ssh -vvv -E` trace with BatchMode enabled and a local route snapshot before model setup. Test direct and provider-relay paths only while the owned instance is live. A TCP/banner timeout, a host-key/authentication refusal, and a successfully authenticated remote-command error require different repairs. Do not call a host ready until an explicit remote runtime probe returns the expected interpreter/Torch/device count. Do not probe ports after tenancy ends or change the global VPN based on these ambiguous results.

No credentials, private keys or account key strings were printed. No global VPN, routing or account-key changes were made.

## Costs and evidence

Fresh provider charges report totalP7R bootstrap cost$0.058, with no training runs. The private campaign total is$4.086, leaving$5.914 of the$10 campaign cap; P7R retains$3.142 of its$3.20 subcap. Amounts are provider-reported and rounded, with a minor-settlement caveat. Both failed tenants are confirmed absent and the unrelated instance set was unchanged.

Evidence: `local-evidence-private.json`, `account-key-match.json`, `../compute/alternative-boot-log.txt`, per-instance lease/guard records, `../compute/boot-failure-teardown.json`, `../compute/alternative-teardown.json`, and `../compute/BOOT_BUDGET_FINAL.json`. Public-key/raw account responses are kept permission600 and are not reproduced in this report.

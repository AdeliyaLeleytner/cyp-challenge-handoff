# Teardown error and correction

I omitted the required `--yes` flag when destroying the first failed-bootstrap instance57806735. The CLI displayed a confirmation prompt, aborted when no answer arrived, and returned exit code0. I failed to inspect that response or verify resource absence, incorrectly recorded the instance as destroyed, and incorrectly told root it had been removed. Reusing the rolling lease file for the replacement also ended protection for that first instance. These were my verification/orchestration errors.

The error was discovered during final teardown verification. The first host had continued accruing charges. Both owned instances57806735 and57807389 were then explicitly destroyed with `--yes`. Those successful commands emitted no stdout, so success was established by a fresh independent instance listing, not by exit code or an assumed response format. Both IDs were absent and the pre-existing unrelated instance set was unchanged. See `TEARDOWN_CERTIFICATE.json` and preserved command outputs.

Vast currently reports $2.181 for the failed first host and $1.847 for the useful replacement, totaling $4.028 (about $4.03). Much of the first-host charge was avoidable. The earlier ~$0.08 estimate was incorrect because it assumed cancellation had succeeded. The total remains within the authorized $6 subcap and $10 campaign cap; that does not excuse the avoidable charge.

All30 full-CV checkpoints and their result files were locally hash-verified before the successful destructive teardown. No trained artifact was lost. Both owned instances are gone; the lease guard, recovery daemons and task-owned bounded keepawake process have exited.

Required prevention for future leases:

- Inspect the CLI's confirmation contract and pass the explicit confirmation flag for already authorized teardown.
- Verify the requested resource's actual state after a mutation. An exit code or empty stdout alone is insufficient.
- Mark a lease destroyed, retire its guard, or replace a lease pointer only after absence is confirmed.
- Bind each guard to an immutable instance-specific lease record, so replacing one lease cannot leave another unprotected.
- Preserve the failed response and correct prior status/cost claims openly.

No external refund request or public message was sent.

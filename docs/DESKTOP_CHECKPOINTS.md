# Cognitive preservation and desktop product checkpoints

This record separates reviewed source preservation, native usability and packaged
software qualification. No source checkpoint is a release or certification.

## Checkpoint A: cognitive engine

The source baseline contains full-session qualification review, Capsules v1,
two-session comparison, the Holmes journal, deterministic challenges, reviewed
pattern resemblance, native investigation UI, reports and a synthetic cooperation
contract. Existing observation and capsule/journal formats are preserved.

The checkpoint stacks on the four commits in PR #1, at
`ab019da0d2c970efab80fe4878b7f2ec55cb9370`, targeting
`feature/living-observatory-v1`. The complete source inventory is copied through
an explicit reviewed manifest into an isolated checkout. Local artifact identifiers
are removed from the public progress document; original documentation and evidence
remain in the private local rollback snapshot. No databases, recordings, journals,
capsules, executable dependencies or private human assessments enter the branch.

The required standard suite recheck ran 130 tests with one failure and 97 error
entries under the restricted token. **Owner-shell execution is PENDING OWNER
EXECUTION**: the owner is away, and neither success nor failure is inferred.

Initial compatibility checks exposed a separate timing-sensitive attach test.
Its fixed delay could write a file before the filesystem observer's first snapshot.
The test now waits for an actual baseline and change event within bounded deadlines;
all original scope and specimen-survival assertions remain. Three consecutive
targeted runs passed. This is a test synchronization fix, not an observer rewrite
or a resolution of the restricted temporary-directory problem. Historical failing
logs are retained alongside the final staged-source verification.

The final isolated-checkout compatibility run passed **130 tests** in **90.243 s**,
including all 18 Holmes tests. The complete staged source matched the reviewed
manifest. No visual acceptance or clean-owner-shell pass is implied.

Read-only retained-owner acceptance again checked 108 records, five public reports,
one failed command report, one completed turn, 81 host process-generation records,
68 child-generation records and 21 resolved citations. Database/WAL hashes and the
protected executable hash matched the retained evidence. No Codex workload was rerun.

Git's local clone helper failed to create a signal pipe under the restricted token;
the staging repository was reconstructed using the preserved Git bundle instead.
Shell GitHub access is blocked by the configured proxy. The GitHub connector is the
available publication route; branch protection inspection returned 403 and remains
unreadable. No protection or configuration setting was altered.

## Acceptance boundaries

Compatibility success does not replace the standard command's result. Native Tk
widget checks do not establish visible owner acceptance. Synthetic assessments are
not authenticated live model cooperation. Hashes are not signatures, timestamps are
not causal proof, and human review never grants execution authority.

Desktop refinement and artifact build/installation qualification are subsequent
work. GitHub Releases and binary uploads require a separate owner decision.

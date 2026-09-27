# APM engineering boundaries

Work within this repository and its explicitly selected test fixtures. Do not
alter unrelated projects, global machine configuration, or installed agent binaries.
APM observes external actions, never private reasoning or private agent histories.

Keep observed evidence, inference, unknown/unavailable facts and synthetic fixtures
distinct. Redact before queues, displays and durable recording. Minimize collection;
do not capture file contents or unrelated process command lines. Replay must stay
passive and stopping attach observation must never terminate the specimen.

Background helpers must be hidden, bounded, observable and cleaned up. Preserve
the small Python/Tk architecture. Do not add infrastructure or refactor working
observers as part of documentation/publication tasks.

Use the project's isolated `.venv`; psutil is its only runtime dependency. Run
`python -m unittest discover -s tests -v` for executable changes. Documentation-only
work should verify links and claims against actual source and recorded evidence.

Keep environments, sessions, raw reports, screenshots, caches and build outputs
out of version control. Publication requires explicit owner authorization and a
staged-content audit. Never publish credentials or personal session data. Public
visibility changes require explicit authorization independent of a private push.

Read [project principles](docs/PRINCIPLES.md) and [security guidance](SECURITY.md).

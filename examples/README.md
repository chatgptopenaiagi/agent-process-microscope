# Synthetic examples only

Everything in this directory was authored as fictional data for publication.
No personal recording, machine identifier, real command result or private export
was copied here. Paths, IDs, times and process details are invented.

## Passive demo recording

`synthetic-demo/` is a small valid APM session. Every canonical event has
`status: synthetic` and `interpretation_level: synthetic`. Its commands are strings
for display only. The derived states identify their synthetic inputs.

From the repository directory:

```powershell
.\.venv\Scripts\python.exe -m apm inspect .\examples\synthetic-demo
.\.venv\Scripts\python.exe -m apm replay .\examples\synthetic-demo
```

Replay does not execute commands. Actual live attach cannot detect file READs or
recover exit codes; the fixture's test outcome is purely illustrative.

## Status vocabulary

`status-vocabulary.json` illustrates OBSERVED, INFERRED, SYNTHETIC, UNKNOWN and
UNAVAILABLE using fictional cases. It is a documentation container, **not an APM
recording or import source**. Its `illustrated_status` values explain the vocabulary;
they do not turn these authored examples into genuine observations.

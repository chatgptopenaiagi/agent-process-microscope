# Validation

The Genesis baseline passed **66 tests with zero failures, errors, or skips** on 27 September 2026. These are saved results from the implementation validation, not a claim that every platform or workload has been tested. The publication audit preserved the runtime modules and did not rerun the suite merely for documentation changes.

The tested environment was Windows with Python 3.14.7, Tk 9, and psutil 7.2.2. Packaging declares Python `>=3.12` and psutil `>=7,<9`; those declared ranges are broader than the exercised baseline and are not evidence of testing every supported combination.

## Automated coverage

| Test group | Tests | Main coverage |
| --- | ---: | --- |
| Core | 8 | Canonical events, redaction, queue bounds, recording and state rules |
| Codex import | 8 | Allowlisted protocol fixtures, excluded content, bounds and private-path refusal |
| Integration | 2 | Owned live process/workspace fixture and passive replay boundaries |
| Observers | 23 | Scoped process, filesystem, Git and system behavior, unavailable evidence and limits |
| Reader security | 10 | Malformed or oversized input, identity, truncation and replay safety |
| UI | 15 | Bounded presentation, controls, lifecycle, conservative replay state and passivity |
| **Total** | **66** | **0 failures, 0 errors, 0 skips** |

The local test wrapper reported 22.757 seconds overall; the unittest log reported 22.549 seconds for the suite itself. The small difference is wrapper overhead, not a second run or a separate performance claim.

The live integration fixture confirmed that stopping observation left the owned specimen process alive. The fixture owner then cleaned up its own process. Tests did not attach to an unrelated private agent session. Git tests used temporary repositories, including filter/fsmonitor canaries, and checked that read-only observation did not run those configured helpers or alter the index.

The passive reader was exercised with process creation patched to raise an error
if invoked. Replay therefore had a check specifically designed to fail if reading
historical evidence attempted to launch a process. GUI tests also verify that
replay does not start observation and reconstructs state from the recorded history.

Codex protocol tests used synthetic fixtures. They establish handling of the tested report shapes, not end-to-end validation against a paid model call or an existing private Codex history.

## Native GUI smoke

The saved Windows smoke result passed a 14-event synthetic demonstration followed by passive replay of the same 14 events. It captured only APM's own window. The demo/replay code path spawned no console helpers; this is not a blanket claim that every observation adapter uses no subprocesses, since Git observation uses bounded hidden Git helpers.

The capture predates the final replay-state and drop-label corrections. Those corrections are covered by the final 66-test suite. The screenshot is therefore a historical view of the Genesis interface, not a pixel-perfect verification of every final semantic change.

## Small-fixture resource measurement

| Measurement | Saved result |
| --- | ---: |
| Duration | 6.113 seconds |
| Observer CPU | 5.11% of one core over the measured interval |
| Resident memory | 27,881,472 bytes |
| Recorded events | 28 |
| Dropped events | 0 |
| Observation worker after stop | Stopped |
| Observed specimen after stop | Still alive |

This was one small owned fixture. It is not a production performance guarantee, large-workspace benchmark, sustained-load result, or worst-case resource bound.

## Packaging evidence

The original validated artifact was `agent_process_microscope-0.1.0-py3-none-any.whl`, 44,270 bytes, with SHA-256:

```text
f24c30b9ffe5696c63e643e146599659ecdce6a044565f7c35149541963996c5
```

The publication audit found all 26 runtime Python modules byte-identical to those in that validated wheel. This ties the unchanged runtime source to the historical implementation tests; it does not claim that a future wheel containing updated publication metadata will have the same hash. A dependency consistency check was also recorded as passing during Genesis validation.

## Reproducing checks

From a prepared checkout with the declared dependencies installed:

```powershell
python scripts/run_checks.py
```

The wrapper runs unittest discovery and writes local `reports/tests.log` and `reports/test-results.json`. Those local reports can include environment details and are excluded from publication by default. The source tests are available in [tests](../tests).

For the bounded native Windows GUI demonstration/replay check:

```powershell
python scripts/smoke_gui.py
```

This opens APM's window, records a synthetic session, and writes local smoke metadata and an own-window screenshot. It is an intentional GUI check, not a headless test. It does not observe a private user process.

## What this does not validate

Genesis does not claim a standalone executable, signed installer, browser/Joomla adapter, GPU observer, managed agent launcher, WSL/cloud deployment, secret-proof recording, formal security certification, or statistically calibrated inference confidence. Replay does not validate the authenticity of imported reports. See [Genesis status](GENESIS_STATUS.md) and [Security](../SECURITY.md).

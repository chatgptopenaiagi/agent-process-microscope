# ADR 0004: external portable qualification and local build locks

Accepted for development; no public release authorization.

Keep the Python/Tk application and existing evidence formats intact. Introduce a
standalone standard-library verifier for explicitly reviewed portable artifacts,
separate from evidence-capsule import. Capsules remain bounded JSON and never
execute anything. Qualifying a selected software build is an explicit engineering
action, not authority inferred from imported evidence or a human interpretation.

The verifier requires an external inventory and expected ZIP hash, checks all
members before execution, and emits durable results with partial failures. It
qualifies isolated execution on the current machine, never a simulated clean OS.
Retain failed fixtures rather than automatically deleting diagnostic evidence.

Pin local toolchain content using distribution inventory hashes and a Python
runtime inventory digest. Fail the build on drift. These are reproducibility
inputs, not upstream trust anchors. Reconstructing an environment from independently
authenticated, hash-pinned upstream downloads remains a release gate. Preserve
license texts but do not infer unrestricted binary redistribution rights.

Use fixed SOURCE_DATE_EPOCH, PYTHONHASHSEED and canonical ZIP order/attributes.
Report bitwise equality only for builds actually compared. Keep portable ZIP as
the initial distribution route; defer installer lifecycle, signing and updates
until an owner-controlled Windows acceptance environment is available.

Expose a versioned capability inventory with local source/test references. It is
engineering documentation with executable validation, not an autonomous execution
catalog or a promise of stable APIs. Do not add services, providers or network calls.

"""Shared frozen desktop/console entry point; no source-checkout assumptions."""
from apm.__main__ import main

if __name__ == '__main__':
    raise SystemExit(main())

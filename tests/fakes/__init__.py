"""In-memory adapters for the ports, used by tests only.

These live under `tests/` on purpose: a fake that ships inside `src/` can be
wired into a running application by accident, which is exactly how the API came
to serve process memory while the database sat unused. `create_app()` has no
in-memory default — a test that wants one passes it in.
"""

"""Behaviour every adapter of a port must satisfy, whatever it stores in.

Each module here holds one contract as a plain class. A test module binds it to
an adapter by subclassing it and overriding the `repository` fixture, so the
in-memory and SQL adapters are held to exactly the same checks — the rule in
AGENTS.md that says two adapters of one Protocol must behave identically.
"""

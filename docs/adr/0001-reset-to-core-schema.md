# Remove implemented schema history until the Core schema is owned

The project is still pre-release and does not need to preserve any database containing the implemented AI workflow. Remove the implemented schema and migration history entirely; keep only a clearly marked persistence placeholder. Until the database owner designs and initializes the single Core schema, the example CRUD runs against server-owned in-memory state that may reset on restart. The project must not imply that the example model is the accepted database contract.

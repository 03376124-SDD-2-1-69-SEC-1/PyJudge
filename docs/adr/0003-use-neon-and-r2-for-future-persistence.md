# Use Neon and R2 for future persistence

When persistence begins, the Database owner will store structured Core data in
Neon PostgreSQL and uploaded PDFs or other objects in Cloudflare R2. D1 is not
selected because this FastAPI application needs a conventional PostgreSQL path
and R2 remains the object-storage choice in either case. This decision does not
authorize schema, client, migration, or credential implementation in the
current scaffold.

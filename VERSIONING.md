# Versioning

Telachat uses Semantic Versioning:

- `MAJOR`: incompatible configuration, storage, or command changes.
- `MINOR`: new user-visible features or provider capabilities.
- `PATCH`: bug fixes, documentation-only updates, and internal hardening.

Every feature should produce a small version bump, a `CHANGELOG.md` entry, a
Git commit, and a matching `vX.Y.Z` tag after tests pass.

The GitHub history starts at `0.2.0` because the local prototype already existed
before the repository was created.

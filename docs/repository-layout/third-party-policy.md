# Third-Party Policy

`third_party/` is not used as a standing storage area for external source trees in this repository.

## Rules

- Runtime dependencies should come from package managers and lockfiles when possible.
- Do not keep large forked source trees in this repository only for occasional code reading.
- If upstream internals need to be inspected again, clone the upstream or a fresh fork outside this repository when needed.
- Do not record developer-specific absolute paths in repository docs.

## Current Status

- No active vendored third-party source tree is required in this repository.
- External implementation references should point to package-managed dependencies or upstream source locations.

# Contributing

- Use `make install` to install the project with development dependencies.
- Run `make lint` and `make test` before submitting changes.
- Preserve the evidence hierarchy: primary, derived, heuristic, and external claims must stay separate.
- New analyzers should register through the existing registry modules instead of hard-coding behavior into the CLI.
- Do not add workflows that require network access to analyze evidence.

# Contributing

Thanks for taking the time to contribute.

## Setup

```bash
git clone git@github.com:info-fauna/luciole-toolbox.git
cd luciole-toolbox
pip install -e ".[dev]"
```

## Testing

```bash
pytest                      # all tests, incl. calls to swisstopo/pyproj CDN
pytest -m "not integration" # skip tests hitting real network endpoints
```

New behavior should come with tests. Tests that hit a real network endpoint
(swisstopo API, pyproj CDN grid shift files) must be marked `@pytest.mark.integration`.

## Linting & formatting

```bash
ruff check .
ruff format .
```

CI runs `ruff check .`, `ruff format --check .`, and the test matrix
(Python 3.9-3.13) on every PR. If you use VS Code with the Ruff extension
(recommended in `.vscode/extensions.json`), formatting runs automatically
on save.

## Docs

If you change public API behavior, update `docs/reference.md` or the
relevant docstrings — the docs site is built from them via mkdocstrings.

```bash
pip install -e ".[docs]"
mkdocs serve # preview locally at http://127.0.0.1:8000
```

## Changelog

Add an entry under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md) for
any user-facing change (new feature, bug fix, breaking change).

## Submitting a change

1. Open an issue first for anything beyond a small fix, so we can align on
   approach before you put work into it.
2. Keep PRs focused on one change.
3. Make sure `ruff check .`, `ruff format --check .`, and
   `pytest -m "not integration"` pass locally.
4. Open the PR against `main`.

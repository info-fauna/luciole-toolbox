# luciole-toolbox

[![CI](https://github.com/info-fauna/luciole-toolbox/actions/workflows/ci.yml/badge.svg)](https://github.com/info-fauna/luciole-toolbox/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/luciole-toolbox.svg)](https://pypi.org/project/luciole-toolbox/)

Python utility library. Currently ships a `geo` module for Swiss coordinates:
CRS detection (WGS84/LV03/LV95), conversion between them, CKM2/CNHA grid
codes, and commune/canton lookup via the swisstopo API.

## Installation

```bash
pip install luciole-toolbox
```

## Usage

```python
from luciole_toolbox.geo import convert_coordinates, get_location_info, CRSType

convert_coordinates("46.9480", "7.4474", target=CRSType.LV95)
get_location_info("46.9480", "7.4474")
```

Full API reference: <https://info-fauna.github.io/luciole-toolbox/>

## Development

```bash
pip install -e ".[dev]"
```

### Testing

```bash
pytest                      # all tests, incl. calls to swisstopo/pyproj CDN
pytest -m "not integration" # skip tests hitting real network endpoints
```

### Docs

```bash
pip install -e ".[docs]"
mkdocs serve # preview locally at http://127.0.0.1:8000
```

## Versioning & releases

The version is derived from git tags via `hatch-vcs` — there is no version
string to hand-edit. Notable changes are tracked in
[CHANGELOG.md](CHANGELOG.md). To cut a release, push a tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

This triggers the `release` workflow, which builds the package, publishes
it to PyPI, and creates a matching GitHub Release.

# luciole-toolbox

[![CI](https://github.com/info-fauna/luciole-toolbox/actions/workflows/ci.yml/badge.svg)](https://github.com/info-fauna/luciole-toolbox/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/luciole-toolbox.svg)](https://pypi.org/project/luciole-toolbox/)
[![License](https://img.shields.io/pypi/l/luciole-toolbox.svg)](LICENSE)

Python utility library from info-fauna for preparing and standardizing Swiss
fauna observation data — coordinate conversion, formatting, and lookups
against Swiss reference geodata. Built for data producers (biologists,
cantonal monitoring staff, naturalists, and partner organizations) and for
use in ETL pipelines and internal systems that load this data into a
database.

Currently ships a `geo` module for Swiss coordinates: CRS detection
(WGS84/LV03/LV95), conversion between them, CKM2/CNHA grid codes, and
commune/canton lookup via the swisstopo API.

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
[CHANGELOG.md](CHANGELOG.md).

To cut a release:

1. Move the `[Unreleased]` entries in [CHANGELOG.md](CHANGELOG.md) under a
   new `## [x.y.z] - YYYY-MM-DD` heading and commit it to `main`.
2. Tag that commit and push the tag:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

This triggers the `release` workflow, which builds the package, publishes
it to PyPI, and creates a matching GitHub Release.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for
setup, testing, and PR guidelines, and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
for expected behavior in this project's spaces.

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md) — please don't
open a public issue for security reports.

## License

LGPL-3.0-or-later. See [LICENSE](LICENSE) for the LGPL terms and
[COPYING](COPYING) for the GPL terms it incorporates by reference.

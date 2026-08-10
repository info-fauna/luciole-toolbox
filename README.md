# luciole-toolbox

Python utility library. Currently ships a `geo` module for Swiss coordinates:
CRS detection (WGS84/LV03/LV95), conversion between them, CKM2/CNHA grid
codes, and commune/canton lookup via the swisstopo API.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```python
from luciole_toolbox.geo import convert_coordinates, get_location_info, CRSType

convert_coordinates("46.9480", "7.4474", target=CRSType.LV95)
get_location_info("46.9480", "7.4474")
```

## Testing

```bash
pytest                      # all tests, incl. calls to swisstopo/pyproj CDN
pytest -m "not integration" # skip tests hitting real network endpoints
```

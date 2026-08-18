# Luciole Toolbox

Python utility library from info-fauna for preparing and standardizing Swiss
fauna observation data. Currently ships a `geo` module for Swiss
coordinates: CRS detection (WGS84/LV03/LV95), conversion between them,
CKM2/CNHA grid codes, and commune/canton lookup via the swisstopo API.

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

See the [API Reference](reference.md) for full details.

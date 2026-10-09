# Changelog

All notable changes to this project are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `geo.convert_coordinates_seq` function to be able to convert a sequence of coordinates in one single call

## [1.1.1] - 2026-10-05

### Fixed

- `geo.convert_coordinates` no longer returns wrong results when LV03/LV95 easting/northing are passed in swapped order (also affects `is_in_switzerland_bbox`, `get_location_info` and `get_altitude`)
- `geo.convert_coordinates` with an explicit LV03/LV95 `source` now returns `None` for values outside that system's valid ranges, instead of converting them blindly

## [1.1.0] - 2026-09-17

### Added

- `geo` module: `get_altitude` calls swisstopo API to [Get Point Height](https://docs.geo.admin.ch/access-data/get-point-height.html)

### Fixed

- `geo` module: support DMS format using doubled apostrophe (`['’′]{2}`)

## [1.0.0] - 2026-08-20

First version of the info fauna luciole toolbox !

### Changed

- License changed from MIT to LGPL-3.0-or-later.

### Fixed

- `geo` module: DMS coordinates without an N/S/E/W hemisphere letter (e.g.
  `46°00′49.13″`) are now detected and converted as WGS84 instead of going unrecognized.
- `geo.convert_coordinates` round LV03 & LV95 values to 0 decimal, WGS84 to 6 decimals.

## [0.1.0] - 2026-08-10

### Added

- `geo` module: CRS detection (WGS84/LV03/LV95), coordinate conversion,
  CKM2/CNHA grid codes, and commune/canton lookup via the swisstopo API.

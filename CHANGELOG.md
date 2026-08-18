# Changelog

All notable changes to this project are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- License changed from MIT to LGPL-3.0-or-later.

### Fixed

- `geo` module: DMS coordinates without an N/S/E/W hemisphere letter (e.g.
  `46°00′49.13″`) are now detected and converted as WGS84 instead of going
  unrecognized.

## [0.1.0] - 2026-08-10

### Added

- `geo` module: CRS detection (WGS84/LV03/LV95), coordinate conversion,
  CKM2/CNHA grid codes, and commune/canton lookup via the swisstopo API.

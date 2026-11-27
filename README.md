# realtime-data-repo

The observations for the [ocean map](https://oceansensing.org/visualization/):
storms, gliders, USVs, Argo floats, radiosondes, buoys, tide gauges, the
tropical moored arrays, research vessels, NSF OOI's moorings and cabled
sites and the OISST temperature analysis — fetched from their upstream
sources through the hour and published as static files at
`https://oceansensing.org/realtime-data-repo/map/`, with a machine-readable
health record beside them at `/status/status.json`.

Updated three times an hour.

Among `map/`'s static files, `noaa-land/` is the land of NOAA's nautical
charts, a U.S. government work in the public domain. It moved to
`enc-chart-repo` on 2026-09-30; the set here is the last one published here,
kept while older readers still ask for it, and is not updated. ECMWF's wind,
air temperatures, cloud cover and 500 hPa heights, and ECWAM's wave height,
moved to `ecmwf-model-atmosphere-repo` on 2026-11-09 under the same names.

## License

Copyright (c) 2026 Donglai Gong. All rights reserved — see
[LICENSE.md](LICENSE.md). The repository is public so the data can be
served from GitHub Pages; that is not a grant of any license. The
scientific data itself belongs to the bodies that produced it, each named
in the LICENSE and credited on the map.

# License

Copyright (c) 2026 Donglai Gong and the Collaboratory for Physical
Oceanography (C4PO). All rights reserved.

This repository contains the orchestration code, workflow, product
declaration and documentation of the second-generation C4PO ocean data
pipeline, publishing at https://oceansensing.org/realtime-data-repo/.

No permission is granted to copy, modify, merge, publish, distribute,
sublicense, or sell any part of this repository, or to create derivative
works from it, whether in source or compiled form, without the prior written
permission of the copyright holder. The repository is public so that the
data can be served from GitHub Pages and so that the work is open to
inspection; publishing it is not a grant of any license.

Requests for permission: info@c4po.science

THE SOFTWARE AND CONTENT ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE AND
CONTENT OR THE USE OR OTHER DEALINGS IN THEM.

## What this license does and does not cover

**It covers the original work in this repository**: the orchestrator in
`pipeline/`, the product declaration, the workflow, the landing page and
the documentation.

**The fetch scripts are not here.** They live in
[`oceansensing/oceansensing.github.io`](https://github.com/oceansensing/oceansensing.github.io)
and are checked out at run time; they are covered by that repository's own
LICENSE, not this one.

**The scientific data is not ours and never was.** Everything published
under `map/` — and every snapshot of it on the `published` branch — is
fetched from the bodies that produced it and remains theirs, under their
own terms: GEBCO (bathymetry and isobaths), Natural Earth (coastline and
boundaries), Marine Regions/VLIZ (EEZ boundaries), NOAA/NHC (storm
forecasts and wind probabilities), NOAA PMEL (uncrewed surface vehicles),
US IOOS, NOC/BODC, OTN and VOTO (gliders), Ifremer (Argo floats),
NOAA/NCEI and NOAA/PSL (OISST), the US Navy via HYCOM (ESPC-D-V02
currents, temperature, salinity and ice), and ECMWF (IFS wind and air
temperature and ECWAM waves, open data under CC BY 4.0). Each is credited
on the map that reads this data, and anyone who needs the data itself
should take it from those sources, which publish it properly.

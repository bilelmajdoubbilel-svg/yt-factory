# Map data licences (Map Minutes)

`na.json` is built by `pipeline/looks/mm_geo_prep.py` from public-domain sources only. Checked 9 Nov 2026.

| Layer | Source | Licence |
|---|---|---|
| land, countries (Canada, US, Mexico, Greenland), Canadian provinces and territories, lakes, physical regions (Canadian Shield, Barren Grounds, Rocky Mountains...), populated places | Natural Earth 1:50m vectors, https://www.naturalearthdata.com (GitHub mirror nvkelso/natural-earth-vector) | Public domain: "All versions of Natural Earth raster + vector map data found on this website are in the public domain. You may use the maps in any manner, including modifying the content and design, electronic dissemination, and offset printing." No credit required. https://www.naturalearthdata.com/about/terms-of-use/ |
| US states | US Census Bureau cartographic boundary files, 2017 edition (cb_2017_us_state), https://www2.census.gov/geo/tiger/GENZ2017/shp/ , as TopoJSON in the npm package us-atlas 3.0.1 | Works of the US federal government are not under copyright (17 U.S.C. 105). The us-atlas packaging is ISC-licensed (Copyright 2013-2019 Michael Bostock); only the derived coordinates are kept here. |
| derived: Canada within 100 km of the lower-48 border; the southern border line; label points | computed with shapely from the layers above (LCC 49N/77N) | same as its sources |

Area check (NE 1:50m, LCC): the 100 km strip is about 5% of Canada's land, consistent with Statistics Canada's
"about 4% of Canada's territory" (The Daily, 8 Feb 2017). On screen we always quote Statistics Canada's figure.

No map tiles, satellite imagery or third-party basemaps are used (their licences differ); every map is drawn from
these vectors in our own parchment style. Fonts: `../fonts` (OFL). Music and effects: the repo's CC0 library.

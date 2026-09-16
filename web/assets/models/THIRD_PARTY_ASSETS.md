# Third-party 3D assets

The files in this directory are stored locally and do not require network
access at runtime. Exact source URLs, authors, dimensions, file hashes, and
sizes are recorded in `manifest.json`.

## Poly Haven models

`sofa.glb`, `bed.glb`, `table.glb`, `chair.glb`, `wardrobe.glb`, `stove.glb`,
`plant.glb`, and `tree.glb` are derived from Poly Haven's 1K glTF downloads.
Poly Haven publishes its assets under Creative Commons Zero 1.0 Universal
(CC0-1.0): https://polyhaven.com/license

The tree geometry was simplified for real-time browser use. The source artwork
and textures remain attributable through the manifest even though attribution
is not required by CC0.

## Commercial refrigerator

`refrigerator.glb` comes from KhronosGroup/glTF-Sample-Assets and is based on
"Commercial Fridge" by Sean Thomas, with additional work by Eric Chadwick and
Darmstadt Graphics Group GmbH. It is used under Creative Commons Attribution
4.0 International (CC-BY-4.0):

- Source: https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/CommercialRefrigerator
- License: https://creativecommons.org/licenses/by/4.0/

## Tooling

`python/download_3d_assets.py` documents and reproduces the acquisition and
packaging process. glTF Transform is used only as a build-time packaging tool;
the application itself loads the committed GLB files directly.

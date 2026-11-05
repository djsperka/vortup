# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

VORTUP is a PyQt5 GUI that controls the UC Davis SLO-OCT instrument. It is built on the [vortex](https://www.vortex-oct.dev/) OCT engine (`vortex_oct_cuda12x`), with an Alazar digitizer for acquisition, NI-DAQmx for galvo and strobe output, CUDA (cupy) for processing, and a serial-connected laser source. The target is Windows with Python 3.10/3.12. Real hardware has not been tested on Linux. On Linux, `FILE_ACQUISITION` mode (replaying a uint16 spectra file) is the only way to run the engine.

## Commands

```bash
pip install -r requirements.txt          # pulls vortex from --extra-index-url https://vortex-oct.dev/stable
python OCTUiParams.py --create           # write default config to ~/.octui/octui.conf (seeded from ./octui.conf)
python OCTUi.py                          # run the application (reads ~/.octui/octui.conf)
```

Linting (config in `pyproject.toml`; generated `Ui_*.py` files are excluded):

```bash
pip install -r requirements-dev.txt
ruff check .              # bugs, print()/commented-out code, deprecations, import order
ruff check --fix .        # apply safe autofixes
ruff format .             # format code
mypy .                    # type check (vortex/cupy/PyQt5 imports are skipped)
pre-commit install        # run ruff on every commit
```

There is no test suite or build step. `TestPlotWidget.py`, `*_example.py`, `myqt_app.py`, `scan_explorer.py` and `Galvo.py` are standalone scripts and manual test harnesses, run directly with `python <file>`.

`OCTUi.py` calls `git describe` on this repo at startup (GitPython), so it must run from a git checkout.

### Qt Designer files

Each `Foo.ui` has a generated `Ui_Foo.py` (pyuic5). Never hand-edit a `Ui_*.py` file. Edit the `.ui` file and regenerate:

```bash
pyuic5 Foo.ui -o Ui_Foo.py
```

The hand-written widget class (`Foo.py`) inherits from both the Qt base class and `Ui_Foo`, then calls `self.setupUi(self)`.

## vortex-tools dependency

`vortex_tools` (the display widgets `RasterEnFaceWidget`, `CrossSectionImageWidget`, and the scan plotting helpers) comes from a fork at `../vortex-tools` (gitlab.com/djsperka/vortex-tools), not only from the pip package `vortex_oct_tools`. `vortex_tools.pth` (which contains `C:/work/src`) looks like a path file for site-packages that puts the fork's source on the import path. Imports such as `vortex_tools.ui.backend.ucdqt` (used in `myqt_app.py`) may exist only in some versions of the fork. Changes to plotting widgets often belong in that repo.

## Architecture

**Entry point: `OCTUi.py`** (`OCTUi` QObject). It owns the main window (`OCTUiMainWindow`), the parameters (`OCTUiParams`), one `ScanGUIHelper` per configured scan, and the engine (`VtxEngine`). On each Start it builds a new engine and replaces the plot widgets in `stackedWidgetDummy`.

**Parameters** (`OCTUiParams.py`, `VtxEngineParams.py`, `ScanParams.py`): dataclasses serialized to JSON.
- `vtx: VtxEngineParams` holds hardware and engine settings. It is edited in `VtxEngineParamsDialog`.
- `scn: ScanParams` holds `current_index` plus a `scans` dict mapping a name to `RasterScanParams | AimingScanParams | LineScanParams | GalvoTuningScanParams`.
- `settings` holds per-scan plot settings such as ranges and ylims, as returned by `helper.getSettings()`.
- `_octui_decoder.from_dict` works out which dataclass to build **from the set of keys present**. If you add or rename a field on a params dataclass, update the matching key-set check and constructor call in the decoder. Otherwise old config files will load as plain dicts or will raise errors.
- Setters mark the params dirty. On close the app offers to save.

**Scan GUI helpers** (`ScanGUIHelper.py` and its subclasses `RasterScanGuiHelper.py`, `AimingScanGUIHelper.py`, `LineScanGUIHelper.py` and `GalvoTuningScanGUIHelper.py`, created by `scanGUIHelperFactory.py`, which dispatches on the params type). Each helper connects one scan type to the engine:
- `edit_widget` is created in `__init__` (from `ScanConfigWidget.py` and the `*ScanConfigWidget.ui` files). It is shown before the engine starts.
- `createEngineComponents(params, samples_per_record)` is called by `VtxEngine` at engine build time. It creates the `FormatPlanner`, the endpoints (null, storage, spectra, ascan) and the plot widget, wrapped in `ScanGUIHelperComponents`. Until this runs, `helper.components` raises an error.
- `getScan()` returns a configured vortex scan. Each helper is given a unique bit flag (`1 << index`), which goes into `marker.Flags` so the formatter routes each block to the correct helper's endpoints.
- `getStrobe()` optionally returns a strobe, which is added to the engine's strobe list.
- Adding a new scan type means adding a params dataclass, a decoder branch, a factory branch, a helper subclass and a config widget/.ui.

**Engine** (`VtxBaseEngine.py` → `VtxEngine.py`):
- `VtxBaseEngine` builds acquisition and processing according to `AcquisitionType`. `ALAZAR_ACQUISITION` uses an Alazar card with an external K-clock, AuxIO trigger out and `CUDAProcessor` with dispersion. `FILE_ACQUISITION` uses `FileAcquisition` looping over `cfg.input_file`, has no galvo, and the ascan endpoint becomes a host tensor endpoint (see `ScanGUIHelper._createAscanEndpoint`). `VtxBaseEngine` also builds the galvo `DAQmxIO`.
- `VtxEngine` assembles the `EngineConfig`. Every helper's format planner and endpoints are added up front, and switching scan type while running only calls `scan_queue.interrupt(helper.getScan())` (`OCTUi.connectCurrentScan`). Strobes always include `VolumeStrobe(7)`.
- Changing dispersion while running goes through `VtxEngine.update_dispersion`.

**Volume saving** (`OCTUi.volumeCallback` / `volumeCallback2`): the null endpoint's volume callback runs first. It calls `helper.volume()` and, if saving was requested, opens `SimpleStackUInt16` storage under `<data root>/<YYYY-MM-DD>/<timestamp>.npy` and writes the current params next to it as `.conf`. The storage endpoint's volume callback counts saved volumes and closes the storage. The order of endpoints in `ScanGUIHelperComponents.endpoints` matters for this. The current branch also contains a hack that dumps the spectra tensor to `data.dat`.

**Hardware helpers**: `LaserSource.py` (a `serial.Serial` subclass used as a context manager; Start refuses to run if the laser is off, Alazar mode only), `DAQConst.py` (Alazar channel mapping), `Galvo.py` and `setmzi.py` (standalone utilities).

## Config and data files in the repo

`octui.conf` is the seed config. `*-tupper-*.conf/.txt` and `profiler*.log*` are reference logs and configs from the instrument. Set `save_profiler_data` to write `profiler.log` (through `VORTEX_PROFILER_LOG`). It can be analyzed with the vortex profiler tool (`--statistics`).

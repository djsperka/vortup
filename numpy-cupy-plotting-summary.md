# numpy vs cupy for volume processing and plotting

Notes on how vortup's plotting code reads volume data from vortex endpoints, where numpy vs cupy
matters, and how GPU-side copies could make plotting cheaper. Based on vortex 0.5.1 and the
vortex-tools fork at `C:\work\pkgs\vortex-tools`.

## Short answers

- **numpy or cupy:** the endpoint type decides. Device endpoints hand you a cupy array that lives on
  the GPU; host endpoints hand you a numpy array. In vortup, A-scan endpoints are always device
  endpoints (cupy) and spectra endpoints are always host endpoints (numpy), in both acquisition
  modes.
- **Does it matter for the callbacks:** not for the callbacks themselves, which only pass along
  B-scan indices. It matters in the paint code and in the volume callbacks, where the data is read.
  Volume callbacks also run on a vortex thread, so they must not touch Qt widgets (section 2).
- **GPU copies:** vortex 0.5.1 has no dedicated "copy this volume on the GPU" call in its Python
  bindings. The same benefit is available with a few lines of cupy (section 3).

## 1. numpy vs cupy: the endpoint decides

| Endpoint | `with ep.tensor as volume` gives you | Used in vortup for |
|---|---|---|
| `StackDeviceTensorEndpointInt8` | `cupy.ndarray` (GPU) | A-scans, both modes |
| `SpectraStackHostTensorEndpointUInt16` | `numpy.ndarray` | raw spectra, both modes |

Both acquisition modes use `CUDAProcessor` (`VtxBaseEngine`). Blocks from the Alazar card and from
`FileAcquisition` are both pinned host memory, so the GPU processor takes either. The processed
A-scans are on the GPU, so `ScanGUIHelper._createAscanEndpoint` always returns a device endpoint.
Earlier, file mode used `CPUProcessor` with a host A-scan endpoint, and every A-scan consumer needed
numpy and cupy branches. That is gone. An NVIDIA GPU is now required in every mode.

The cupy array points directly at vortex's own GPU buffer, so getting it costs nothing. The cost
comes with `.get()`, which copies GPU → CPU over PCIe. The rule that follows: **reduce on the GPU,
then transfer.** For example:

- `RasterEnFaceWidget` takes the max projection on the GPU and transfers only the B×A image, not the
  B×A×Z volume (`vortex_tools/ui/display.py`).
- `SpectraTraceWidget` pulls only 11 A-scans (`TraceWidget.py`).

**Where the array type is still checked:**

- `SpectraTraceWidget` is the only vortup widget that checks the type. It is given both kinds of
  endpoint (raster uses it for the A-scan endpoint and for the spectra endpoint). It slices the data,
  calls `.get()` only if the slice is a cupy array, and then runs one shared numpy path.
- The vortex-tools display widgets keep their `isinstance(volume, cupy.ndarray)` branches. That is
  fork code, and in vortup only the cupy branch runs.
- `AscanTraceWidget`, `LineScanTraceWidget` and `RasterScanGUIHelper.cb_volume` assume cupy for
  A-scans and numpy for spectra, with no branches.

## 2. Callbacks: what matters

**Which thread runs what.** `aggregate_segment_callback` and `volume_callback` run on a vortex worker
thread, not the Qt GUI thread. The segment callbacks follow the right pattern. `notify_segments` and
`update_trace` only record indices and call `update()`. The GPU work and the `.get()` happen later in
`paintEvent` on the GUI thread. For these callbacks numpy vs cupy makes no difference.

**Qt widgets touched from the vortex thread (fixed).** `RasterScanGUIHelper.cb_volume` used to call
`MPSW.add_data()`, which calls `set_image` on child widgets, from the vortex thread. Touching Qt
widgets from another thread can crash at random, so it may explain the occasional crash (commit
e2be2d2). The fix:

- `MPSW` has `post_data()`. It emits a signal connected to `add_data` with `QueuedConnection`, so
  `add_data` always runs on the GUI thread.
- `cb_volume` copies the arrays itself, then calls `post_data()`.

Rule from here on: anything called from a vortex callback either touches only plain Python data and
calls `widget.update()`, or hands its results to the GUI thread through a queued signal.

**How long the lock is held.** Inside `with ep.tensor as volume:` you hold the endpoint's lock, and
vortex can't write into that endpoint until you let go. For cupy, keep the block short:

- Run GPU work on the endpoint's stream (`with ep.stream:`) so it's correctly ordered after vortex's
  writes.
- Do the `.get()` inside the block, because the view isn't safe once the lock is released.
- Don't add `.copy()` before `.get()`, or `synchronize()` after it. `.get()` already copies to the
  host and waits for the stream.

`cb_volume` now follows this pattern:

```python
with self.components.ascan_endpoint.tensor as volume:
    with self.components.ascan_endpoint.stream:
        ascan_data = volume.max(axis=2).transpose().get()
```

For numpy data from a host endpoint, use `.copy()` when the array is used after the lock is released
(as `cb_volume` does for the spectra before passing them to the GUI thread).

## 3. Using GPU-side copies to make plotting cheaper

What the vortex 0.5.1 Python bindings actually provide:

- Device endpoints expose the volume as a cupy view (section 1).
- A second constructor, `StackDeviceTensorEndpointInt8(executor, tensor, log)`, takes another
  endpoint's `.tensor`, so two endpoints can share one buffer.
- `vortex.process.CopyProcessor` copies raw spectra through the pipeline without OCT processing.
  That's a pipeline stage, not a plotting tool.

What would make plotting faster is a **GPU snapshot**: hold the lock only long enough for a
GPU-to-GPU copy, then do the slow work without the lock. This is a sketch, not implemented:

```python
# once, at createEngineComponents time
self._snap = cupy.empty(shape, dtype=cupy.int8)   # preallocated, no per-volume malloc

def cb_volume(self, *_):
    ep = self.components.ascan_endpoint
    with ep.tensor as volume, ep.stream:
        cupy.copyto(self._snap, volume)            # device→device, very fast (memory bandwidth)
        self._snap_ready = ep.stream.record()      # event; no CPU sync needed
    self.snapshotReady.emit()                      # queued → GUI thread

# GUI thread, lock-free:
def on_snapshot(self):
    self._snap_ready.synchronize()
    img = self._snap.max(axis=2).T.get()           # reduce on GPU, transfer only the 2-D image
    self._mpsw.add_data(img, ...)
```

This buys three things:

- **Vortex never waits on display.** The lock is held only for the device-to-device copy, which is
  far faster than any reduction plus PCIe transfer.
- **Consistent images.** The snapshot is a whole, single volume. Reading the live buffer in
  `paintEvent` can mix B-scans from the old and new volume, because vortex keeps writing between the
  callback and the paint.
- **Moving work off the vortex thread.** Several widgets (en face MIP, cross-section, saved
  thumbnails) can work from one snapshot. Heavier steps, such as averaging, flattening or log
  scaling, can move to the GUI thread without slowing acquisition. Use two snapshot buffers if a slow
  GUI frame could overlap the next copy.

This may not be needed for the live per-segment displays, which already transfer little data. The
snapshot pays off mainly for whole-volume processing such as `cb_volume` and MPSW.

For the spectra, which go through a host endpoint, there's nothing on the GPU to snapshot. numpy's
`volume.copy()` is already that pattern. Switching to `SpectraStackDeviceTensorEndpointUInt16` would
only help if spectra processing moved to the GPU. Where vortex copies spectra from hasn't been
measured, so whether the host endpoint costs anything extra today is unknown.

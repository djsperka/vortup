from vortex.acquire import alazar
from vortex.engine import source, Source
from typing import Tuple
from dataclasses import dataclass

#from vortex.engine import Source

@dataclass
class VtxEngineParams:

    # scan parameters
    scan_dimension: float
    bidirectional: bool
    ascans_per_bscan: int
    bscans_per_volume: int
    galvo_delay: float

    # acquisition parameters
    clock_samples_per_second: int
    blocks_to_acquire: int
    ascans_per_block: int
    samples_per_ascan: int
    trigger_delay_seconds: float

    # hardware configuration
    swept_source: Source
    internal_clock: bool
    external_clock_level_pct: int
    clock_channel: alazar.Channel
    input_channel: alazar.Channel
    input_channel_range_millivolts: int
    doIO: bool
    doStrobe: bool
    trigger_range_millivolts: int
    trigger_level_fraction: float

    # engine memory parameters
    blocks_to_allocate: int
    preload_count: int

    # processing control
    process_slots: int
    dispersion: Tuple[float, float]

    # logging
    log_level: int

DEFAULT_VTX_ENGINE_PARAMS = VtxEngineParams(
    # scan parameters
    scan_dimension=5,
    bidirectional=False,
    ascans_per_bscan=500,
    bscans_per_volume=500,
    galvo_delay=95e-6,

    # acquisition parameters
    blocks_to_acquire=0,
    ascans_per_block=500,
    samples_per_ascan=1376,     # Axsun 100k
    trigger_delay_seconds=0,

    # These are probably rig-specific? Hasn't been an issue to use these. 
    blocks_to_allocate=128,
    preload_count=32,

    # hardware configuration
    swept_source=source.Axsun100k,
    internal_clock=False,
    clock_samples_per_second=int(500e6),    # ATS 9350 - applies to internal clock only
    external_clock_level_pct=50,        # only relevant if internal_clock is False
    clock_channel=alazar.Channel.B,    # only relevant if internal_clock is True
    input_channel=alazar.Channel.A,
    input_channel_range_millivolts=1000,
    doIO=False,
    doStrobe=False,
    trigger_range_millivolts=5000,
    trigger_level_fraction=0.10,

    # engine memory parameters
    process_slots=2,                    # I think this is for in-stream processing?
    dispersion=(2.8e-5, 0),             # no idea

    # logging
    log_level=1,                        # 1 is normal, 0 is debug-level
)

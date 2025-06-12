from vortex.acquire import alazar
from vortex.engine import source, Source
from typing import Tuple
from dataclasses import dataclass
from enum import Enum
#from vortex.engine import Source

class AcquisitionType(Enum):
    ALAZAR_ACQUISITION = 1
    FILE_ACQUISITION= 2

@dataclass
class VtxEngineParams:
    # acquisition type
    acquisition_type: AcquisitionType

    # left over from scan parameters
    galvo_delay: float

    # hardware configuration
    swept_source: Source
    internal_clock: bool
    clock_samples_per_second: int
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

    acquisition_type=AcquisitionType.ALAZAR_ACQUISITION,
    galvo_delay=0.0,

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
    doIO=True,
    doStrobe=True,
    trigger_range_millivolts=5000,
    trigger_level_fraction=0.10,

    # engine memory parameters
    process_slots=2,                    # I think this is for in-stream processing?
    dispersion=(2.8e-5, 0),             # no idea

    # logging
    log_level=1,                        # 1 is normal, 0 is debug-level
)

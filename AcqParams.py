from dataclasses import dataclass

@dataclass
class AcqParams:
    ascans_per_block: int
    samples_per_ascan: int
    blocks_to_acquire: int
    trigger_delay_seconds: float

DEFAULT_ACQ_PARAMS = AcqParams(500, 1376, 0, 0)


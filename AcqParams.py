from dataclasses import dataclass

@dataclass
class AcqParams:
    ascans_per_block: int=0
    samples_per_ascan: int=0
    blocks_to_acquire: int=0
    trigger_delay_seconds: float=0.0

DEFAULT_ACQ_PARAMS = AcqParams(500, 1280, 0, 0)


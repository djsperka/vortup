import typing as t
from dataclasses import dataclass
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class AcqParams:
    ascans_per_block: int=0
    samples_per_ascan: int=0
    blocks_to_acquire: int=0
    trigger_delay_seconds: float=0.0

    @classmethod
    def from_dict(cls: t.Type["AcqParams"], obj: dict):
        return cls(
            ascans_per_block=obj.get("ascans_per_block"),
            samples_per_ascan=obj.get("samples_per_ascan"),
            blocks_to_acquire=obj.get("blocks_to_acquire"),
            trigger_delay_seconds=obj.get("trigger_delay_seconds"),
        )


DEFAULT_ACQ_PARAMS = AcqParams(500, 1280, 0, 0)


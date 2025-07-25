import json
from dataclasses import dataclass, asdict
from AcqParams import AcqParams, DEFAULT_ACQ_PARAMS
from VtxEngineParams import VtxEngineParams, DEFAULT_VTX_ENGINE_PARAMS


@dataclass 
class OCTConfig:
    eng: VtxEngineParams

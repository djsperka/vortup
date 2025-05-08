from myengine import setup_logging, StandardEngineParams, DEFAULT_ENGINE_PARAMS, BaseEngine
from vortex.scan import RasterScan, RasterScanConfig
from vortex import get_console_logger as gcl, Range
from vortex.process import NullProcessor, NullProcessorConfig
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutor, StackFormatExecutorConfig
from vortex.engine import SpectraStackHostTensorEndpointUInt16
from vortex.engine import Engine, EngineConfig

# engine parameters
myEngineParameters = DEFAULT_ENGINE_PARAMS
myEngineParameters.log_level = 1



# create a repeated A-scan
rsc = RasterScanConfig()
rsc.bscans_per_volume = myEngineParameters.bscans_per_volume
rsc.ascans_per_bscan = myEngineParameters.ascans_per_bscan
rsc.bscan_extent = Range(0, 0)
rsc.volume_extent = Range(0, 0)

# complete only a single volume
# hack - set to True
rsc.loop = True

scan = RasterScan()
scan.initialize(rsc)



from vortex.acquire import AlazarAcquisition, AlazarConfig, alazar

# configure external clocking from an Alazar card
# internal clock works for testing with 9350 (doesn't take 800*10**6)
ac = AlazarConfig()
ac.clock = alazar.ExternalClock(level_ratio = 50, coupling=alazar.Coupling.AC, edge=alazar.ClockEdge.Rising, dual=False)
# ac.clock = alazar.InternalClock(500000000)

# trigger with range - must be 5000 (2500 will err). TTL will work in config also. Discrepancy with docs
ac.trigger = alazar.SingleExternalTrigger(range_millivolts=5000, level_ratio = 0.10, delay_samples=0, slope=alazar.TriggerSlope.Negative)

# only input channel A
input = alazar.Input(alazar.Channel.A, range_millivolts = 1000)
ac.inputs.append(input)

# pull in engine params
ac.records_per_block = myEngineParameters.ascans_per_block
ac.samples_per_record = myEngineParameters.samples_per_ascan

acquire = AlazarAcquisition(gcl('acquire', myEngineParameters.log_level))
acquire.initialize(ac)


# configure no processing
pc = NullProcessorConfig()
pc.samples_per_record = acquire.config.samples_per_record
pc.ascans_per_block = acquire.config.records_per_block

process = NullProcessor()
process.initialize(pc)


# configure standard formatting
fc = FormatPlannerConfig()
fc.segments_per_volume = myEngineParameters.bscans_per_volume
fc.records_per_segment = myEngineParameters.ascans_per_bscan
fc.adapt_shape = False

format = FormatPlanner(gcl('format', myEngineParameters.log_level))
format.initialize(fc)

# store raw spectra in a volume
sfec = StackFormatExecutorConfig()
sfe  = StackFormatExecutor()
sfe.initialize(sfec)

endpoint = SpectraStackHostTensorEndpointUInt16(sfe, [myEngineParameters.bscans_per_volume, myEngineParameters.ascans_per_bscan, myEngineParameters.samples_per_ascan], gcl('endpoint', myEngineParameters.log_level))


# configure the engine
ec = EngineConfig()

ec.add_acquisition(acquire, [process])
ec.add_processor(process, [format])
ec.add_formatter(format, [endpoint])

# reasonable default parameters
ec.preload_count = 32
ec.records_per_block = myEngineParameters.ascans_per_block
ec.blocks_to_allocate = ec.preload_count * 2
ec.blocks_to_acquire = 1000 # 0 means inifinite acquisition

engine = Engine(gcl('engine', myEngineParameters.log_level))
engine.initialize(ec)
engine.prepare()

# load the scan
engine.scan_queue.append(scan)

# start the engine and wait for the scan to complete
# NOTE: since loop is false above, only one scan is executed
engine.start()
try:
    engine.wait()
finally:
    engine.stop()

# retrieve the collected data
# data is ordered by B-scan (segment), A-scan, and sample
with endpoint.tensor as volume:
    # combine all the B-scans (if there are multiple) and average all the spectra together
    average_spectrum = volume.reshape((-1,  myEngineParameters.samples_per_ascan)).mean(axis=0)

# show the average spectrum
from matplotlib import pyplot as plt
plt.plot(average_spectrum)

plt.xlabel('sample number')
plt.ylabel('intensity (unscaled)')
plt.title('Average Spectrum')
plt.show()

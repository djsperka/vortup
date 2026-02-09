from dataclasses import dataclass, field
from typing import Union
from abc import ABC, abstractmethod
from typing import List, Any, Dict, Tuple
from ScanParams import RasterScanParams, AimingScanParams, LineScanParams
from AcqParams import AcqParams
from OCTUiParams import OCTUiParams
from vortex.engine import NullEndpoint, VolumeStrobe, SegmentStrobe, SampleStrobe, EventStrobe
from vortex.engine import StackDeviceTensorEndpointInt8, SpectraStackHostTensorEndpointUInt16, SpectraStackEndpoint, NullEndpoint, EventStrobe
from vortex.format import FormatPlanner, FormatPlannerConfig, StackFormatExecutorConfig, StackFormatExecutor, SimpleSlice
from vortex.storage import SimpleStackUInt16
from qtpy.QtWidgets import QWidget


from vortex import get_console_logger as get_logger
import logging


class ScanGUIHelperComponents:
    def __init__(self, format_planner: FormatPlanner, null_endpoint: NullEndpoint, storage_endpoint: SpectraStackEndpoint, spectra_endpoint: SpectraStackHostTensorEndpointUInt16, storage: SimpleStackUInt16, ascan_endpoint: StackDeviceTensorEndpointInt8, plot_widget: QWidget):
        self._format_planner = format_planner
        self._null_endpoint = null_endpoint
        self._storage_endpoint = storage_endpoint
        self._storage = storage
        self._spectra_endpoint = spectra_endpoint
        self._ascan_endpoint = ascan_endpoint
        self._plot_widget = plot_widget

    @property
    def endpoints(self) -> List[Any]:
        return [self._null_endpoint, self._storage_endpoint, self._spectra_endpoint, self._ascan_endpoint]
    
    @property
    def format_planner(self) -> FormatPlanner:
        return self._format_planner
    
    @property 
    def null_endpoint(self) -> NullEndpoint:
        return self._null_endpoint

    @property
    def storage_endpoint(self) -> SpectraStackEndpoint:
        return self._storage_endpoint

    @property
    def storage(self) -> SimpleStackUInt16:
        return self._storage

    @property
    def spectra_endpoint(self) -> SpectraStackHostTensorEndpointUInt16:
        return self._spectra_endpoint
    
    @property
    def ascan_endpoint(self) -> StackDeviceTensorEndpointInt8:
        return self._ascan_endpoint
    
    @property
    def plot_widget(self) -> QWidget:
        return self._plot_widget

class ScanGUIHelper(ABC):
    '''
    ScanGUIHelper is an abstract class used as the bridge between the components of the vortex engine, the specifications for 
    specific scan types, the plot(s) generated during DAQ, and more. The things created by this class come in two types:
    configuration/edit widget, which is used _before_ the engine is started, and the engine components (format planner, 
    endpoints), which are used when the engine is created. 
    
    The edit widget should be created in the constructor, but the components will not be created until createComponents() is called, 
    with the latest engine parameters as an argument. 
    '''
    def __init__(self, name, flags, params, settings, log_level=1):
        '''
        Docstring for __init__
        
        :param self: Description
        :param name: Name for this scan
        :param flags: Bit pattern, will be arg for vortex.marker.Flags()
        :param params: Parameters for the helper's edit dialog
        :param settings: Settings for this helper's plots (saved range, etc)
        :param log_level: Log level for vortex loggers
        '''
        self.name = name
        self.flags = flags
        self.params = params
        self.settings = settings
        self.log_level = log_level
        self._logger = logging.getLogger('GUIHelper({0:s})'.format(self.name))
        self._components = None

    def has_components(self) -> bool:
        return None != self._components

    @property
    def components(self) -> ScanGUIHelperComponents:
        if self._components is None:
            raise RuntimeError("Cannot access components before calling createComponents()")
        else:
            return self._components

    # @property 
    # def format_planner(self) -> FormatPlanner:
    #     '''
    #     Returns format planner for this scan
        
    #     :param self: Should be a FormatPlaner, which can be used in EngineConfig.add_processor. Subclasses should set value.

    #     '''
    #     return self._format_planner

    # @property
    # def endpoints(self) -> List[Any]:
    #     return [self._null_endpoint, self._storage_endpoint, self._spectra_endpoint, self.ascan_endpoint]

    # @property
    # def null_endpoint(self) -> NullEndpoint:
    #     return self._null_endpoint

    # @property 
    # def storage(self):
    #     return self._spectra_storage
        
    # @property
    # def storage_endpoint(self) -> NullEndpoint:
    #     return self._storage_endpoint
    
    # @property
    # def ascan_endpoint(self):
    #     return self._ascan_endpoint
    
    # @property
    # def spectra_endpoint(self):
    #     return self._spectra_endpoint


    # @property
    # def plot_widget(self):
    #     '''
    #     Widget displayed in the plotting widget - QStackedWidget. Subclasses should set this.
        
    #     :param self: Description
    #     '''
    #     return self._plot_widget

    @property
    def edit_widget(self):
        '''
        Widget displayed in the editing widget - QStackedWidget. Subclasses should set this.
        
        :param self: Description
        '''
        return self._edit_widget

    # @abstractmethod
    # def getPlotWidget(self, components: ScanGUIHelperComponents) -> QWidget:
    #     '''
    #     Docstring for getPlotWidget
        
    #     :param self: Description
    #     :param components: Description
    #     :type components: ScanGUIHelperComponents
    #     :return: Description
    #     :rtype: QWidget
    #     '''
    #     pass


    @abstractmethod
    def getScan(self):
        '''
        Returns a configured scan pattern, e.g. RasterScan
        
        :param self: Description
        '''
        pass

    @abstractmethod
    def getParams(self):
        """Return the parameters currently specified in the edit widget"""
        pass

    @abstractmethod
    def clear(self):
        """Clear plots and any internal data
        Returns:
            None: None
        """
        pass

    @abstractmethod
    def getStrobe(self) -> None|VolumeStrobe|SegmentStrobe|SampleStrobe|EventStrobe:
        """
        Return None (if no strobe for this scan type), or return a tuple with the device name and the strobe to use. 
        The strobe's 'line' parameter should be set here!  
        
        :param self: Description
        :return: Description
        :rtype: None | VolumeStrobe | SegmentStrobe | SampleStrobe | EventStrobe
        """
        return None

    @abstractmethod
    def createEngineComponents(self, octuiparams: OCTUiParams):
        '''
        Creates SCanGUIHelperComponents using the params passed. The scan params in octuiparams
        are the same as the params that this class has, so its OK to use self.params instead of 
        fishing the params out of octuiparams.scn
        
        :param self: ScanGUIHelper
        :param octuiparams: Current engine parameters. 
        :type octuiparams: OCTUiParams
        '''
        pass
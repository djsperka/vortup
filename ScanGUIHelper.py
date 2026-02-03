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
    def __init__(self, format_planner, null_endpoint: NullEndpoint, storage_endpoint: SpectraStackEndpoint, spectra_endpoint: SpectraStackHostTensorEndpointUInt16, ascan_endpoint: StackDeviceTensorEndpointInt8):
        self.format_planner = format_planner
        self.null_endpoint = null_endpoint
        self.storage_endpoint = storage_endpoint
        self.spectra_endpoint = spectra_endpoint
        self.ascan_endpoint = ascan_endpoint

    @property
    def endpoints(self) -> List[Any]:
        return [self.null_endpoint, self.storage_endpoint, self.spectra_endpoint, self.ascan_endpoint]


class ScanGUIHelper(ABC):
    def __init__(self, name, flags, params, settings, log_level=1):
        self.name = name
        self.flags = flags
        self.params = params
        self.settings = settings
        self.log_level = log_level
        self._logger = logging.getLogger('GUIHelper({0:s})'.format(self.name))

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

    @abstractmethod
    def getPlotWidget(self, components: ScanGUIHelperComponents) -> QWidget:
        '''
        Docstring for getPlotWidget
        
        :param self: Description
        :param components: Description
        :type components: ScanGUIHelperComponents
        :return: Description
        :rtype: QWidget
        '''
        pass


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
    def getEngineComponents(self, octuiparams: OCTUiParams) -> ScanGUIHelperComponents:
        '''
        Docstring for getEngineComponents
        
        :param self: Description
        :param octuiparams: Description
        :type octuiparams: OCTUiParams
        :return: Description
        :rtype: ScanGUIHelperComponents
        '''
        pass
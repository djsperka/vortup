from abc import ABC, abstractmethod
from typing import List, Any, Dict
from ScanParams import RasterScanParams, AimingScanParams, LineScanParams
from AcqParams import AcqParams
from vortex.engine import NullEndpoint
from vortex.format import FormatPlanner
from vortex import get_console_logger as get_logger
import logging

class ScanGUIHelper(ABC):
    def __init__(self, name, number, params, settings, log_level=1):
        self.name = name
        self.number = number
        self.params = params
        self.settings = settings
        self.log_level = log_level
        self._logger = logging.getLogger('GUIHelper({0:s})'.format(self.name))

    @property 
    def format_planner(self) -> FormatPlanner:
        '''
        Returns format planner for this scan
        
        :param self: Should be a FormatPlaner, which can be used in EngineConfig.add_processor. Subclasses should set value.

        '''
        return self._format_planner

    @property
    def endpoints(self) -> List[Any]:
        return [self._null_endpoint, self._storage_endpoint, self._spectra_endpoint, self.ascan_endpoint]

    @property
    def null_endpoint(self) -> NullEndpoint:
        return self._null_endpoint

    @property 
    def storage(self):
        return self._spectra_storage
        
    @property
    def storage_endpoint(self) -> NullEndpoint:
        return self._storage_endpoint
    
    @property
    def ascan_endpoint(self):
        return self._ascan_endpoint
    
    @property
    def spectra_endpoint(self):
        return self._spectra_endpoint


    @property
    def plot_widget(self):
        '''
        Widget displayed in the plotting widget - QStackedWidget. Subclasses should set this.
        
        :param self: Description
        '''
        return self._plot_widget

    @property
    def edit_widget(self):
        '''
        Widget displayed in the editing widget - QStackedWidget. Subclasses should set this.
        
        :param self: Description
        '''
        return self._edit_widget

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
    def getSettings(self) -> Dict[str, Any]:
        """Return the settings, a dict, associated with the plots, if any. Not scan settings!"""
        pass

    @abstractmethod
    def clear(self):
        """Clear plots and any internal data
        Returns:
            None: None
        """
        pass


import re
import time
from typing import Tuple
from enum import Enum
import serial

class LaserSource:

    class LaserState(Enum):
        ON = 60
        OFF = 61
        OFF_INTERLOCK = 62
        OFF_FAULT = 63
        UNKNOWN = 64

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 0):
        self.ser = serial.Serial(port, baudrate)

    def __del__(self):
        if self.ser.is_open:
            self.ser.close()

    def parse_response(self, response: str) -> Tuple[int, str, str]:
        p=re.compile(r'(\d{3}): (\w+):(.+)')
        m=p.match(response)
        if m:
            return int(m.group(1)), m.group(2), m.group(3)

        # check for an error response
        p=re.compile(r'(\d{3}): (.+)')
        m=p.match(response)
        if m:            
            raise RuntimeError(f"Error received: {m.group(2)}")
        else:
            raise ValueError("Invalid response format")

    def command(self, cmd: str):
        if not self.ser.is_open:
            raise RuntimeError("Serial port is not open - not connected to laser source?")
        num = self.ser.write((cmd + '\r\n').encode('utf-8'))

    def get_response(self, sleep_ms: int = 100) -> Tuple[int, str, str]:
        t = None
        time.sleep(sleep_ms / 1000.0)
        while self.ser.in_waiting > 0:
            response = self.ser.readline().decode('utf-8').strip()
            if response:
                if t is None:
                    t = self.parse_response(response)
        if t is None:
            raise RuntimeError("No response received from the laser source")
        
        return t

    def read_param(self, param: str) -> str:
        self.command('read_param {}'.format(param))
        _, _, value = self.get_response()
        # split value
        v = value.split(',')
        if len(v) == 2:
            return v[0].strip()
        else:
            raise RuntimeError("read_param returned value {value}, expecting format 'param_value,param_status'") 

    def laser_state(self) -> LaserState:
        state_str = self.read_param('laser_state')
        print(f"Laser state string: '{state_str}'")
        try:
            return LaserSource.LaserState(int(state_str))
        except KeyError:
            return LaserSource.LaserState.UNKNOWN

    def sweep_mode(self) -> Tuple[int, int]:
        try:
            sweep_mode_str = self.read_param('sweep_mode')
            i = int(sweep_mode_str)
            if i==1:
                mzi_str = self.read_param('mzi_delay')
            elif i==2:
                mzi_str = self.read_param('mzi_delay.2')
            elif i==3:
                mzi_str = self.read_param('mzi_delay.3')
            else:
                raise(ValueError("Got sweep mode {sweep_mode_str}. Expecting 1,2, or 3"))
            j = int(mzi_str)
        finally:
            return (i, j)

    def is_on(self) -> bool:
        return self.laser_state() == LaserSource.LaserState.ON
    
if __name__ == '__main__':

    try:
        laser = LaserSource('COM3')  # Update with your actual port
        if laser.ser.is_open:
            print("Serial port opened successfully")    
        laser.command('serial')
        #time.sleep(0.1)  # Wait a bit for the response to be ready
        (a,b,serial_number) = laser.get_response()
        print(f"Response: {a}, {b}, {serial_number}")   
        laser.command('firmware_version')
        (a,b,fw_version) = laser.get_response()
        print(f"Response: {a}, {b}, {fw_version}")   
        print("Laser serial number:", serial_number, "Firmware version:", fw_version)
        print("Laser state", laser.laser_state())
        (mode, mzi) = laser.sweep_mode()
        print("sweep mode: {:d}, mzi_delay: {:d}".format(mode, mzi))
    except Exception as e:
        print("Error:", e)
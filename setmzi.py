from LaserSource import LaserSource
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

if __name__ == "__main__":
    parser = ArgumentParser(description='save volume to disk', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('mzi', type=int, help='MZI delay to set (in ns)')
    parser.add_argument('--port', default='COM3', help='serial port for laser source')
    args = parser.parse_args()

    with LaserSource(args.port) as laser:
        print('Initial: {}'.format(laser.info()))
        laser_initially_on = laser.is_on()
        if laser_initially_on:
            print('Turning laser off to set MZI delay...')
            laser.laser_off()
            if laser.is_on():
                raise RuntimeError("Failed to turn laser off") 
  
        laser.write_param('mzi_delay', str(args.mzi))

        if laser_initially_on:
            print('Turning laser on...')
            laser.laser_on()
            if not laser.is_on():
                raise RuntimeError("Failed to turn laser on") 
        print('Final: {}'.format(laser.info())) 


# VORTUP: Instrumentation software for slo-oct device at EyePod

This application will control the SLO-OCT device at UCDavis. More generally, I hope it will control a device similar to this one. the main limitation is hardware, specifically the acquisition and IO cards used. This software will work with acquisition cards from Alazar, and IO cards from National Instruments (NI-DAQmx cards).


## Table of contents

* [Usage](#usage)
* [Known issues and limitations](#known-issues-and-limitations)
* [Getting help](#getting-help)
* [License](#license)
* [Acknowledgments](#acknowledgments)


## Usage

### Installation

Install CUDA for your device, then install from the requirements file - see below. 

This code works with python 3.10 and 3.12 on Windows. I have not tested hardware on a linux machine.

```
git clone https://github.com/djsperka/vortup
cd vortup
pip install -r requirements.txt
```

### Initial configuration file

Initialize a configuration file. From the folder where the code is installed, run OCTUiParams to create a new config file:


```
dan@bucky:~$ cd work/oct/vortup/
dan@bucky:~/work/oct/vortup$ 
dan@bucky:~/work/oct/vortup$ python OCTUiParams.py --create
INFO:OCTUiParams:creating new config file
INFO:OCTUiParams:loading OCTUi config from /home/dan/work/oct/vortup/octui.conf
INFO:OCTUiParams:saving OCTUi config to /home/dan/.octui/octui.conf
INFO:OCTUiParams:Creating directory /home/dan/.octui
INFO:OCTUiParams:Done.
```

### Basic operation

## Known issues and limitations

None are known at this time.


## Getting help

Contact the developer at djsperka_at_ucdavis_dot_edu.


## License

Copyright &copy; 2025 The Regents of the University of California, Davis campus. All Rights Reserved.

Please see the [LICENSE](LICENSE.md) file for more information.


## Acknowledgments

Development of this software was supported by NIH Vision Research Core Grant, P30EY012576. 

This software replies on many software packages and products. Here are a few significant ones:

* [Vortex - An open-source library for building real-time OCT engines in C++ or Python.](https://www.vortex-oct.dev/)
* [Qt](https://www.qt.io/)
* [PyQT - a set of Python bindings for the Qt application framework.](https://www.riverbankcomputing.com/software/pyqt/)

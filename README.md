# iot_exp
projects for the IoT Expedition lab at Carnegie Mellon University

## Interpreter
Python 2

## Instructions
To run, type in the command line `python wemo_bd_driver.py [on/off/sense] [Hz]`
Examples: 
* `python wemo_bd_driver.py on`
* `python wemo_bd_driver.py off`
* `python wemo_bd_driver.py sense`
* `python wemo_bd_driver.py sense .5` (this will cause the driver to sample at a rate of about .5 Hz from the wemo, and post to BD in a separate thread)

# Caveats
This was created on a Windows machine, so it may not work on Linux (at least not initially). Some file names may have to be changed to the Linux format.
The Wemo cannot respond to requests at a frequency of more than 2 Hz, so the driver cannot get wemo sensor samples faster than this.

# qcm-monitor
Real-time Quartz Crystal Microbalance (QCM) monitoring tool for molecular beam epitaxy (MBE). This repository contains a cleaner, modular Python GUI version of the original prototype.

## Project structure
- main.py: application entry point
- qcm_monitor/: Python package with the GUI, plotting, serial reading, and settings modules
- settings.ini: external configuration file for serial connection and GUI behavior
- requirements.txt: Python dependencies
- run_qcm_monitor.bat: Windows launcher that installs requirements and starts the app

## Windows setup
1. Install Python 3.10+.
2. Open a terminal in the repository folder.
3. Install the project in editable mode:
   - python -m pip install -e .
4. Edit settings.ini to match the serial port and device settings for your setup.
5. Start the app:
   - qcm-monitor
   - or python main.py
   - or double-click run_qcm_monitor.bat

## Notes
- The original prototype behavior is preserved: the app reads the frequency from the serial device, plots it, and shows slope-based information.
- The serial port, timing, and plotting behavior are now configurable through settings.ini.

@echo off
echo Building TCT Control Application...

REM Clean previous builds
rmdir /s /q build
rmdir /s /q dist
del /f /q TCTControl.spec

REM Install/Update required packages
pip install -r requirements.txt

REM Create executable using PyInstaller
pyinstaller --clean ^
    --name TCTControl ^
    --windowed ^
    --icon=icon.ico ^
    --add-data "icon.ico;." ^
    --hidden-import=pkg_resources ^
    --hidden-import=libximc ^
    --hidden-import=PyQt5 ^
    --hidden-import=PyQt5.QtCore ^
    --hidden-import=PyQt5.QtGui ^
    --hidden-import=PyQt5.QtWidgets ^
    --hidden-import=numpy ^
    --hidden-import=matplotlib ^
    --hidden-import=pyvisa ^
    --hidden-import=pyvisa.highlevel ^
    --hidden-import=pyvisa.constants ^
    --hidden-import=pyvisa_py ^
    --hidden-import=pyvisa_py.protocols ^
    --collect-all PyQt5 ^
    --collect-all libximc ^
    --collect-all pyvisa ^
    --collect-all pyvisa_py ^
    main.py

REM Run Inno Setup Compiler
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

echo Build complete! Installer is in the Output directory. 
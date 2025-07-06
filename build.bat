@echo off
echo Building TCT Control Application...

REM Clean up previous builds
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"
if exist "*.spec" del *.spec

REM Create Python executable
python -m PyInstaller --name "TCTControl" ^
    --windowed ^
    --icon=icon.ico ^
    --add-data "icon.ico;." ^
    --hidden-import=PyQt6 ^
    --hidden-import=pyvisa ^
    --hidden-import=numpy ^
    main.py

REM Run Inno Setup Compiler
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer.iss"

echo Build complete! Check the Output folder for the installer. 
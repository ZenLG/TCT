@echo off
echo Building TCT Control Application...

REM Clean previous builds
rmdir /s /q build
rmdir /s /q dist
del /f /q TCTControl.spec

REM Create executable using PyInstaller
pyinstaller --clean ^
    --name TCTControl ^
    --windowed ^
    --icon=icon.ico ^
    --add-data "icon.ico;." ^
    --hidden-import=pkg_resources ^
    --hidden-import=libximc ^
    --hidden-import=PyQt5 ^
    --hidden-import=numpy ^
    --hidden-import=matplotlib ^
    main.py

REM Run Inno Setup Compiler
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

echo Build complete! Installer is in the Output directory. 
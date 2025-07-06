from setuptools import setup, find_packages

setup(
    name="tct_control",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'pyvisa>=1.13.0',
        'pyvisa-py>=0.7.0',
        'numpy>=1.24.0',
        'pandas>=2.0.0',
        'PyQt6>=6.5.0',
        'pyserial>=3.5',
        'matplotlib>=3.7.0',
        'pyyaml>=6.0.0',
    ],
    entry_points={
        'console_scripts': [
            'tct_control=main:main',
        ],
    },
) 
# TCT Control System

A control system for Transient Current Technique (TCT) measurements, integrating stage control and oscilloscope data acquisition.

## Features

- 3-axis stage control using XIMC controllers
- Oscilloscope integration with Tektronix DPO7254
- Real-time data acquisition and visualization
- Automated scanning and measurement capabilities

## Requirements

- Python 3.8 or higher
- XILab software installed (for stage control)
- NI-VISA drivers (for oscilloscope control)
- Required Python packages (see requirements.txt)

## Installation

1. Install XILab software from the manufacturer's website
2. Install NI-VISA drivers
3. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/TCTcode.git
   cd TCTcode
   ```
4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Hardware Setup

### Stage Controller
- Supports 3-axis XIMC stage controllers
- Default COM port configuration:
  - X axis: COM4
  - Y axis: COM6
  - Z axis: COM5
- Configurable resolution and speed settings

### Oscilloscope
- Supports Tektronix DPO7254
- Default GPIB address: GPIB0::1::INSTR
- Configurable channel and trigger settings

## Usage

1. Connect the stage controllers and oscilloscope
2. Run the main application:
   ```bash
   python main.py
   ```

## Configuration

- Stage settings can be modified in `stage_controller.py`
- Oscilloscope settings can be modified in `scope_controller.py`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your License Here]

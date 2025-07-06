import sys
import os
import matplotlib
matplotlib.use('QtAgg')  # Use QtAgg backend which works with both Qt5 and Qt6

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QLabel, QSpinBox,
                            QDoubleSpinBox, QComboBox, QLineEdit, QFileDialog,
                            QMessageBox, QGroupBox, QGridLayout, QCheckBox)
from PyQt6.QtCore import QTimer, pyqtSlot
import logging
from datetime import datetime
import yaml
import numpy as np
from stage_controller import StageController
from scope_controller import ScopeController
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MainWindow(QMainWindow):
    """Main window for TCT control application."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Default serial numbers for the stage axes
        self.default_serials = {
            'X': '10223',
            'Y': '10222',
            'Z': '10999'
        }
        
        self.stage = StageController()
        self.scope = ScopeController()
        self.connected = False
        self.scanning = False
        
        self.setup_ui()
        
        # Setup data directory
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize state
        self.current_scan_position = 0
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.scan_step)
        
    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create control groups
        self.create_connection_group(layout)
        self.create_position_control_group(layout)
        self.create_scope_control_group(layout)
        self.create_scan_control_group(layout)
        self.create_acquisition_group(layout)
        
        # Right panel - Plot
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Create matplotlib figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Voltage (V)")
        self.ax.grid(True)
        right_layout.addWidget(self.canvas)
        
        layout.addWidget(right_panel)
        
    def create_connection_group(self, parent_layout):
        group = QGroupBox("Connection Control")
        layout = QGridLayout()
        
        # Serial number inputs with default values
        layout.addWidget(QLabel("X Axis Serial:"), 0, 0)
        self.x_serial = QLineEdit(self.default_serials['X'])
        layout.addWidget(self.x_serial, 0, 1)
        
        layout.addWidget(QLabel("Y Axis Serial:"), 1, 0)
        self.y_serial = QLineEdit(self.default_serials['Y'])
        layout.addWidget(self.y_serial, 1, 1)
        
        layout.addWidget(QLabel("Z Axis Serial:"), 2, 0)
        self.z_serial = QLineEdit(self.default_serials['Z'])
        layout.addWidget(self.z_serial, 2, 1)
        
        # Connect button
        self.connect_btn = QPushButton("Connect Devices")
        self.connect_btn.clicked.connect(self.connect_devices)
        layout.addWidget(self.connect_btn, 3, 0, 1, 2)
        
        # Status labels
        self.stage_status = QLabel("Stage: Not Connected")
        self.scope_status = QLabel("Scope: Not Connected")
        layout.addWidget(self.stage_status, 4, 0)
        layout.addWidget(self.scope_status, 4, 1)
        
        # Add save/load configuration buttons
        save_config_btn = QPushButton("Save Configuration")
        save_config_btn.clicked.connect(self.save_configuration)
        layout.addWidget(save_config_btn, 5, 0)
        
        load_config_btn = QPushButton("Load Configuration")
        load_config_btn.clicked.connect(self.load_configuration)
        layout.addWidget(load_config_btn, 5, 1)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_position_control_group(self, parent_layout):
        group = QGroupBox("Position Control")
        layout = QGridLayout()
        
        # X position control (in steps)
        layout.addWidget(QLabel("X (steps):"), 0, 0)
        self.x_pos = QSpinBox()
        self.x_pos.setRange(-100000, 100000)
        layout.addWidget(self.x_pos, 0, 1)
        
        # Y position control (in mm)
        layout.addWidget(QLabel("Y (mm):"), 1, 0)
        self.y_pos = QDoubleSpinBox()
        self.y_pos.setRange(-100, 100)
        self.y_pos.setDecimals(3)
        layout.addWidget(self.y_pos, 1, 1)
        
        # Z position control (in mm)
        layout.addWidget(QLabel("Z (mm):"), 2, 0)
        self.z_pos = QDoubleSpinBox()
        self.z_pos.setRange(-100, 100)
        self.z_pos.setDecimals(3)
        layout.addWidget(self.z_pos, 2, 1)
        
        # Movement controls
        move_btn = QPushButton("Move to Position")
        move_btn.clicked.connect(self.move_to_position)
        layout.addWidget(move_btn, 3, 0)
        
        home_btn = QPushButton("Home")
        home_btn.clicked.connect(self.home_stage)
        layout.addWidget(home_btn, 3, 1)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_scope_control_group(self, parent_layout):
        group = QGroupBox("Oscilloscope Control")
        layout = QGridLayout()
        
        # Channel 1 settings
        layout.addWidget(QLabel("Channel 1:"), 0, 0)
        self.ch1_enable = QCheckBox("Enable")
        self.ch1_enable.setChecked(True)
        layout.addWidget(self.ch1_enable, 0, 1)
        
        layout.addWidget(QLabel("Scale (mV/div):"), 1, 0)
        self.ch1_scale = QDoubleSpinBox()
        self.ch1_scale.setRange(1, 10000)  # 1mV to 10V per division
        self.ch1_scale.setValue(1000)  # Default 1V/div
        layout.addWidget(self.ch1_scale, 1, 1)
        
        layout.addWidget(QLabel("Trigger (mV):"), 2, 0)
        self.ch1_trigger = QDoubleSpinBox()
        self.ch1_trigger.setRange(-10000, 10000)  # ±10V in mV
        layout.addWidget(self.ch1_trigger, 2, 1)
        
        # Channel 3 settings
        layout.addWidget(QLabel("Channel 3:"), 0, 2)
        self.ch3_enable = QCheckBox("Enable")
        self.ch3_enable.setChecked(True)
        layout.addWidget(self.ch3_enable, 0, 3)
        
        layout.addWidget(QLabel("Scale (mV/div):"), 1, 2)
        self.ch3_scale = QDoubleSpinBox()
        self.ch3_scale.setRange(1, 10000)  # 1mV to 10V per division
        self.ch3_scale.setValue(1000)  # Default 1V/div
        layout.addWidget(self.ch3_scale, 1, 3)
        
        layout.addWidget(QLabel("Trigger (mV):"), 2, 2)
        self.ch3_trigger = QDoubleSpinBox()
        self.ch3_trigger.setRange(-10000, 10000)  # ±10V in mV
        layout.addWidget(self.ch3_trigger, 2, 3)
        
        # Auto-scale buttons
        auto_scale_ch1 = QPushButton("Auto Scale Ch1")
        auto_scale_ch1.clicked.connect(lambda: self.auto_scale(1))
        layout.addWidget(auto_scale_ch1, 3, 0, 1, 2)
        
        auto_scale_ch3 = QPushButton("Auto Scale Ch3")
        auto_scale_ch3.clicked.connect(lambda: self.auto_scale(3))
        layout.addWidget(auto_scale_ch3, 3, 2, 1, 2)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_scan_control_group(self, parent_layout):
        group = QGroupBox("Scan Control")
        layout = QGridLayout()
        
        # Step size
        layout.addWidget(QLabel("Step Size:"), 0, 0)
        self.step_size = QSpinBox()  # Changed to SpinBox for steps
        self.step_size.setRange(1, 1000)
        self.step_size.setValue(4)  # Default 4 steps (0.01mm equivalent)
        layout.addWidget(self.step_size, 0, 1)
        
        # Add step size unit label that updates based on axis
        self.step_unit_label = QLabel("steps")
        layout.addWidget(self.step_unit_label, 0, 2)
        
        # Number of steps
        layout.addWidget(QLabel("Number of Steps:"), 1, 0)
        self.num_steps = QSpinBox()
        self.num_steps.setRange(1, 1000)
        self.num_steps.setValue(10)
        layout.addWidget(self.num_steps, 1, 1)
        
        # Scan axis selection
        layout.addWidget(QLabel("Scan Axis:"), 2, 0)
        self.scan_axis = QComboBox()
        self.scan_axis.addItems(["X", "Y", "Z"])
        self.scan_axis.currentTextChanged.connect(self.update_step_size_unit)
        layout.addWidget(self.scan_axis, 2, 1)
        
        # Delay between measurements
        layout.addWidget(QLabel("Delay (s):"), 3, 0)
        self.scan_delay = QDoubleSpinBox()
        self.scan_delay.setRange(0.1, 10.0)
        self.scan_delay.setValue(1.0)
        layout.addWidget(self.scan_delay, 3, 1)
        
        # Scan controls
        self.start_scan_btn = QPushButton("Start Scan")
        self.start_scan_btn.clicked.connect(self.start_scan)
        layout.addWidget(self.start_scan_btn, 4, 0)
        
        self.stop_scan_btn = QPushButton("Stop Scan")
        self.stop_scan_btn.clicked.connect(self.stop_scan)
        self.stop_scan_btn.setEnabled(False)
        layout.addWidget(self.stop_scan_btn, 4, 1)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_acquisition_group(self, parent_layout):
        group = QGroupBox("Data Acquisition")
        layout = QGridLayout()
        
        # File path
        layout.addWidget(QLabel("Save Path:"), 0, 0)
        self.file_path = QLineEdit()
        layout.addWidget(self.file_path, 0, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_save_path)
        layout.addWidget(browse_btn, 0, 2)
        
        # Single acquisition button
        self.acquire_btn = QPushButton("Single Acquisition")
        self.acquire_btn.clicked.connect(self.acquire_data)
        layout.addWidget(self.acquire_btn, 1, 0, 1, 3)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def save_configuration(self):
        """Save the current configuration to a file."""
        try:
            config = {
                'serials': {
                    'X': self.x_serial.text(),
                    'Y': self.y_serial.text(),
                    'Z': self.z_serial.text()
                }
            }
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Configuration",
                "",
                "Configuration Files (*.yaml);;All Files (*)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    yaml.dump(config, f)
                self.logger.info(f"Configuration saved to {filename}")
                
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save configuration: {str(e)}")
            
    def load_configuration(self):
        """Load configuration from a file."""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Load Configuration",
                "",
                "Configuration Files (*.yaml);;All Files (*)"
            )
            
            if filename:
                with open(filename, 'r') as f:
                    config = yaml.safe_load(f)
                    
                if 'serials' in config:
                    self.x_serial.setText(config['serials'].get('X', ''))
                    self.y_serial.setText(config['serials'].get('Y', ''))
                    self.z_serial.setText(config['serials'].get('Z', ''))
                    self.logger.info(f"Configuration loaded from {filename}")
                    
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load configuration: {str(e)}")
            
    @pyqtSlot()
    def connect_devices(self):
        if not self.connected:
            # Set axis serial numbers
            x_serial = self.x_serial.text().strip()
            y_serial = self.y_serial.text().strip()
            z_serial = self.z_serial.text().strip()
            
            if not all([x_serial, y_serial, z_serial]):
                QMessageBox.warning(self, "Connection Error", "Please enter serial numbers for all axes")
                return
                
            # Configure stage serials
            self.stage.set_axis_serials(x_serial, y_serial, z_serial)
            
            # Connect stage
            if self.stage.connect():
                self.stage_status.setText("Stage: Connected")
            else:
                QMessageBox.warning(self, "Connection Error", "Failed to connect to stage")
                return
                
            # Connect scope
            if self.scope.connect():
                self.scope_status.setText("Scope: Connected")
            else:
                QMessageBox.warning(self, "Connection Error", "Failed to connect to scope")
                self.stage.disconnect()
                self.stage_status.setText("Stage: Not Connected")
                return
                
            self.connected = True
            self.connect_btn.setText("Disconnect")
            self.update_position_display()
            
            # Disable serial inputs while connected
            self.x_serial.setEnabled(False)
            self.y_serial.setEnabled(False)
            self.z_serial.setEnabled(False)
            
        else:
            self.stop_scan()  # Stop any ongoing scan
            self.stage.disconnect()
            self.scope.disconnect()
            self.stage_status.setText("Stage: Not Connected")
            self.scope_status.setText("Scope: Not Connected")
            self.connected = False
            self.connect_btn.setText("Connect Devices")
            
            # Re-enable serial inputs
            self.x_serial.setEnabled(True)
            self.y_serial.setEnabled(True)
            self.z_serial.setEnabled(True)
            
    def update_position_display(self):
        if self.connected:
            x, y, z = self.stage.get_position()
            self.x_pos.setValue(x)
            self.y_pos.setValue(y)
            self.z_pos.setValue(z)
            
    @pyqtSlot()
    def move_to_position(self):
        if not self.connected:
            return
            
        x = self.x_pos.value()  # X in steps
        y = self.y_pos.value()  # Y in mm
        z = self.z_pos.value()  # Z in mm
        
        if self.stage.move_to_position(x, y, z):
            self.logger.info(f"Moved to position: X={x}steps, Y={y:.3f}mm, Z={z:.3f}mm")
        else:
            QMessageBox.warning(self, "Movement Error", "Failed to move to position")
            
    @pyqtSlot()
    def home_stage(self):
        if not self.connected:
            return
            
        if self.stage.home():
            self.update_position_display()
        else:
            QMessageBox.warning(self, "Homing Error", "Failed to home stage")
            
    @pyqtSlot()
    def auto_scale(self, channel):
        if not self.connected:
            return
            
        self.scope.auto_scale(channel)
        
    @pyqtSlot()
    def acquire_data(self):
        if not self.connected or not self.file_path.text():
            return
            
        try:
            # Get current position for filename
            x, y, z = self.stage.get_position()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{self.file_path.text()}/waveform_x{x}_y{y:.3f}_z{z:.3f}_{timestamp}"
            
            # Acquire from enabled channels
            if self.ch1_enable.isChecked():
                self.scope.configure_channel(1, self.ch1_scale.value() / 1000.0)  # Convert mV to V
                self.scope.set_trigger(1, self.ch1_trigger.value() / 1000.0)  # Convert mV to V
                self.scope.save_waveform(1, f"{base_filename}_ch1.csv")
                
            if self.ch3_enable.isChecked():
                self.scope.configure_channel(3, self.ch3_scale.value() / 1000.0)  # Convert mV to V
                self.scope.set_trigger(3, self.ch3_trigger.value() / 1000.0)  # Convert mV to V
                self.scope.save_waveform(3, f"{base_filename}_ch3.csv")
                
            self.logger.info(f"Saved waveforms at position X={x}steps, Y={y:.3f}mm, Z={z:.3f}mm")
            
        except Exception as e:
            QMessageBox.warning(self, "Acquisition Error", f"Failed to acquire data: {str(e)}")
            
    @pyqtSlot()
    def browse_save_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if path:
            self.file_path.setText(path)
            
    @pyqtSlot()
    def start_scan(self):
        if not self.connected or not self.file_path.text():
            QMessageBox.warning(self, "Scan Error", "Please connect devices and set save path first")
            return
            
        try:
            self.scanning = True
            self.current_scan_position = 0
            self.start_scan_btn.setEnabled(False)
            self.stop_scan_btn.setEnabled(True)
            
            # Start scan timer
            self.scan_timer.start(int(self.scan_delay.value() * 1000))
            
        except Exception as e:
            QMessageBox.warning(self, "Scan Error", f"Failed to start scan: {str(e)}")
            self.stop_scan()
            
    @pyqtSlot()
    def stop_scan(self):
        self.scanning = False
        self.scan_timer.stop()
        self.start_scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        
    @pyqtSlot()
    def scan_step(self):
        if not self.scanning:
            return
            
        try:
            # Get current position
            x, y, z = self.stage.get_position()
            
            # Calculate new position based on selected axis
            axis = self.scan_axis.currentText()
            step = self.step_size.value()
            
            if axis == "X":
                x += step  # X uses raw steps
            elif axis == "Y":
                y += step / 1000.0  # Convert µm to mm
            else:  # Z
                z += step / 1000.0  # Convert µm to mm
                
            # Move to new position
            if self.stage.move_to_position(x, y, z):
                # Acquire data
                self.acquire_data()
                
                # Check if scan is complete
                self.current_scan_position += 1
                if self.current_scan_position >= self.num_steps.value():
                    self.stop_scan()
                    QMessageBox.information(self, "Scan Complete", "Automated scan completed successfully")
            else:
                raise Exception("Failed to move to next position")
                
        except Exception as e:
            QMessageBox.warning(self, "Scan Error", f"Error during scan: {str(e)}")
            self.stop_scan()

    def update_step_size_unit(self, axis):
        """Update step size unit and range based on selected axis"""
        if axis == "X":
            self.step_size.setRange(1, 1000)
            self.step_unit_label.setText("steps")
            self.step_size.setValue(4)  # Default 4 steps
        else:
            self.step_size.setRange(1, 1000)
            self.step_unit_label.setText("µm")
            self.step_size.setValue(10)  # Default 10 µm

def main():
    try:
        print("Initializing QApplication...")
        app = QApplication(sys.argv)
        print("Creating main window...")
        window = MainWindow()
        print("Showing main window...")
        window.show()
        print("Entering Qt event loop...")
        return app.exec()
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.debug("Starting application...")
    sys.exit(main())
    logger.debug("Application ended.") 
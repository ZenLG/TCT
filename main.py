import sys
import os
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tct_error.log'),
        logging.StreamHandler()
    ]
)

try:
    logging.info(f"Python version: {sys.version}")
    logging.info(f"Current working directory: {os.getcwd()}")
    logging.info(f"System PATH: {os.environ.get('PATH', '')}")
    
    # Try importing each major dependency separately to identify which one fails
    logging.info("Attempting to import dependencies...")
    
    try:
        import libximc
        logging.info("Successfully imported libximc")
    except Exception as e:
        logging.error(f"Failed to import libximc: {str(e)}\n{traceback.format_exc()}")
    
    try:
        import PyQt5
        from PyQt5 import QtWidgets, QtCore
        logging.info("Successfully imported PyQt5")
        from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QLineEdit, QGridLayout, QMessageBox
        from PyQt5.QtCore import Qt
        logging.info("Successfully imported PyQt5 widgets")
    except Exception as e:
        logging.error(f"Failed to import PyQt5: {str(e)}\n{traceback.format_exc()}")
    
    try:
        import pyvisa
        logging.info("Successfully imported pyvisa")
        import pyvisa_py
        logging.info("Successfully imported pyvisa_py")
    except Exception as e:
        logging.error(f"Failed to import pyvisa: {str(e)}\n{traceback.format_exc()}")
    
    try:
        import numpy
        logging.info("Successfully imported numpy")
    except Exception as e:
        logging.error(f"Failed to import numpy: {str(e)}\n{traceback.format_exc()}")
    
    try:
        import matplotlib
        matplotlib.use('Qt5Agg')  # Use Qt5Agg backend specifically
        logging.info("Successfully imported matplotlib")
    except Exception as e:
        logging.error(f"Failed to import matplotlib: {str(e)}\n{traceback.format_exc()}")

    # Rest of your imports
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    
    from scope_controller import ScopeController
    from stage_controller import StageController

    class MainWindow(QMainWindow):
        """Main window for TCT control application."""
        
        def __init__(self):
            super().__init__()
            self.logger = logging.getLogger(__name__)
            
            # Default COM ports for the stage axes
            self.default_ports = {
                'X': 'COM4',  # X axis
                'Y': 'COM6',  # Y axis
                'Z': 'COM5'   # Z axis
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
            
            # COM port inputs with default values
            layout.addWidget(QLabel("X Axis Port:"), 0, 0)
            self.x_port = QLineEdit(self.default_ports['X'])
            layout.addWidget(self.x_port, 0, 1)
            
            layout.addWidget(QLabel("Y Axis Port:"), 1, 0)
            self.y_port = QLineEdit(self.default_ports['Y'])
            layout.addWidget(self.y_port, 1, 1)
            
            layout.addWidget(QLabel("Z Axis Port:"), 2, 0)
            self.z_port = QLineEdit(self.default_ports['Z'])
            layout.addWidget(self.z_port, 2, 1)
            
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
                    'ports': {
                        'X': self.x_port.text(),
                        'Y': self.y_port.text(),
                        'Z': self.z_port.text()
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
                        
                    if 'ports' in config:
                        self.x_port.setText(config['ports'].get('X', ''))
                        self.y_port.setText(config['ports'].get('Y', ''))
                        self.z_port.setText(config['ports'].get('Z', ''))
                        self.logger.info(f"Configuration loaded from {filename}")
                        
            except Exception as e:
                QMessageBox.warning(self, "Load Error", f"Failed to load configuration: {str(e)}")
                
        @pyqtSlot()
        def connect_devices(self):
            if not self.connected:
                self.logger.info("Starting device connection process...")
                
                # Set axis ports
                x_port = self.x_port.text().strip()
                y_port = self.y_port.text().strip()
                z_port = self.z_port.text().strip()
                
                if not all([x_port, y_port, z_port]):
                    QMessageBox.warning(self, "Connection Error", "Please enter COM ports for all axes")
                    return
                    
                self.logger.info(f"Using ports - X: {x_port}, Y: {y_port}, Z: {z_port}")
                
                # Configure stage ports
                self.stage.set_axis_ports(x_port, y_port, z_port)
                
                # Connect stage
                try:
                    self.logger.info("Attempting to connect to stage...")
                    if self.stage.connect():
                        self.stage_status.setText("Stage: Connected")
                        self.logger.info("Stage connected successfully")
                    else:
                        error_msg = "Failed to connect to stage.\n\nPlease check:\n"
                        error_msg += "1. XILab software is installed\n"
                        error_msg += "2. Stage is powered on\n"
                        error_msg += "3. USB cables are properly connected\n"
                        error_msg += "4. Correct COM ports are selected\n"
                        error_msg += "\nCheck the application log for more details."
                        QMessageBox.warning(self, "Connection Error", error_msg)
                        return
                except Exception as e:
                    self.logger.error(f"Stage connection error: {str(e)}")
                    QMessageBox.warning(self, "Connection Error", f"Stage connection error: {str(e)}")
                    return
                    
                # Connect scope
                try:
                    self.logger.info("Attempting to connect to oscilloscope...")
                    if self.scope.connect():
                        self.scope_status.setText("Scope: Connected")
                        self.logger.info("Oscilloscope connected successfully")
                    else:
                        error_msg = "Failed to connect to scope.\n\nPlease check:\n"
                        error_msg += "1. VISA drivers are installed\n"
                        error_msg += "2. Scope is powered on\n"
                        error_msg += "3. GPIB cable is connected\n"
                        error_msg += "4. Scope is set to GPIB address 1\n"
                        error_msg += "\nTrying to connect using GPIB0::1::INSTR"
                        self.logger.warning(error_msg)
                        QMessageBox.warning(self, "Connection Error", error_msg)
                        self.stage.disconnect()
                        self.stage_status.setText("Stage: Not Connected")
                        return
                except Exception as e:
                    self.logger.error(f"Scope connection error: {str(e)}")
                    QMessageBox.warning(self, "Connection Error", f"Scope connection error: {str(e)}")
                    self.stage.disconnect()
                    self.stage_status.setText("Stage: Not Connected")
                    return
                    
                self.connected = True
                self.connect_btn.setText("Disconnect")
                self.update_position_display()
                self.logger.info("All devices connected successfully")
                
                # Disable port inputs while connected
                self.x_port.setEnabled(False)
                self.y_port.setEnabled(False)
                self.z_port.setEnabled(False)
                
            else:
                self.logger.info("Disconnecting devices...")
                self.stop_scan()  # Stop any ongoing scan
                self.stage.disconnect()
                self.scope.disconnect()
                self.stage_status.setText("Stage: Not Connected")
                self.scope_status.setText("Scope: Not Connected")
                self.connected = False
                self.connect_btn.setText("Connect Devices")
                self.logger.info("All devices disconnected")
                
                # Re-enable port inputs
                self.x_port.setEnabled(True)
                self.y_port.setEnabled(True)
                self.z_port.setEnabled(True)
                
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
            
        def acquire_data(self):
            """Acquire data from enabled channels with timeout protection."""
            if not self.connected or not self.file_path.text():
                return
            
            try:
                # Get current position for filename
                x, y, z = self.stage.get_position()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = f"{self.file_path.text()}/waveform_x{x}_y{y:.3f}_z{z:.3f}_{timestamp}"
                
                # Acquire from enabled channels with timeout protection
                if self.ch1_enable.isChecked():
                    try:
                        self.scope.configure_channel(1, self.ch1_scale.value() / 1000.0)  # Convert mV to V
                        self.scope.set_trigger(1, self.ch1_trigger.value() / 1000.0)  # Convert mV to V
                        self.scope.save_waveform(1, f"{base_filename}_ch1.csv")
                    except Exception as e:
                        self.logger.error(f"Channel 1 acquisition failed: {str(e)}")
                        raise
                        
                if self.ch3_enable.isChecked():
                    try:
                        self.scope.configure_channel(3, self.ch3_scale.value() / 1000.0)  # Convert mV to V
                        self.scope.set_trigger(3, self.ch3_trigger.value() / 1000.0)  # Convert mV to V
                        self.scope.save_waveform(3, f"{base_filename}_ch3.csv")
                    except Exception as e:
                        self.logger.error(f"Channel 3 acquisition failed: {str(e)}")
                        raise
                        
                self.logger.info(f"Saved waveforms at position X={x}steps, Y={y:.3f}mm, Z={z:.3f}mm")
                
            except Exception as e:
                self.logger.error(f"Data acquisition failed: {str(e)}")
                raise
            
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
                # Get current position with timeout
                try:
                    x, y, z = self.stage.get_position()
                except Exception as e:
                    self.logger.error(f"Failed to get position: {str(e)}")
                    self.stop_scan()
                    QMessageBox.warning(self, "Scan Error", "Failed to get stage position")
                    return
                    
                # Calculate new position based on selected axis
                axis = self.scan_axis.currentText()
                step = self.step_size.value()
                
                if axis == "X":
                    x += step  # X uses raw steps
                elif axis == "Y":
                    y += step / 1000.0  # Convert µm to mm
                else:  # Z
                    z += step / 1000.0  # Convert µm to mm
                    
                # Move to new position with timeout
                move_timer = QTimer()
                move_timer.setSingleShot(True)
                move_timer.start(10000)  # 10 second timeout
                
                try:
                    if not self.stage.move_to_position(x, y, z):
                        raise Exception("Stage movement failed")
                        
                    # Wait for movement to complete
                    while not move_timer.isActive():
                        QApplication.processEvents()  # Keep UI responsive
                        if self.stage.is_moving():
                            continue
                        break
                        
                    if move_timer.isActive():
                        move_timer.stop()
                    else:
                        raise Exception("Stage movement timed out")
                        
                except Exception as e:
                    self.logger.error(f"Movement error: {str(e)}")
                    self.stop_scan()
                    QMessageBox.warning(self, "Scan Error", f"Stage movement failed: {str(e)}")
                    return
                    
                # Small delay to ensure stage has settled
                QTimer.singleShot(100, self._acquire_after_move)
                
            except Exception as e:
                self.logger.error(f"Scan step error: {str(e)}")
                self.stop_scan()
                QMessageBox.warning(self, "Scan Error", f"Error during scan: {str(e)}")
                
        def _acquire_after_move(self):
            """Helper method to acquire data after movement has completed."""
            try:
                # Acquire data
                self.acquire_data()
                
                # Check if scan is complete
                self.current_scan_position += 1
                if self.current_scan_position >= self.num_steps.value():
                    self.stop_scan()
                    QMessageBox.information(self, "Scan Complete", "Scan completed successfully")
                
            except Exception as e:
                self.logger.error(f"Acquisition error: {str(e)}")
                self.stop_scan()
                QMessageBox.warning(self, "Scan Error", f"Failed to acquire data: {str(e)}")
                
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
except Exception as e:
    logging.error(f"Error initializing application: {str(e)}\n{traceback.format_exc()}")
    sys.exit(1) 
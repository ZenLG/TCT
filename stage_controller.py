import os
import sys
import time
import logging
from typing import Tuple, Optional, Dict

import libximc.highlevel as ximc
from libximc.highlevel import MicrostepMode, StateFlags, Axis

try:
    print(f"Using libximc {ximc.ximc_version()}")
except ImportError:
    print("Warning! libximc not found in pip packages. Trying to import from XILab installation...")
    ximc_dir = os.path.join(os.environ.get('PROGRAMFILES', ''), 'XILab', 'ximc')
    if not os.path.exists(ximc_dir):
        ximc_dir = os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'XILab', 'ximc')
    ximc_package_dir = os.path.join(ximc_dir, "crossplatform", "wrappers", "python")
    sys.path.append(ximc_package_dir)
    import libximc.highlevel as ximc

class StageController:
    """Controller for XILabs 8MTF 102 stage from Standa."""
    
    def __init__(self):
        """Initialize the stage controller using XILabs software."""
        self.logger = logging.getLogger(__name__)
        self.position = (0, 0, 0)  # Current position (x in steps, y/z in mm)
        self.steps_per_mm = 400  # 400 steps = 1mm for axes
        self.connected = False
        self.axes: Dict[str, ximc.Axis] = {}  # Maps axis name to Axis object
        
        # COM ports for each axis - these should be configured before use
        self.axis_ports = {
            'X': 'COM4',  # X axis
            'Y': 'COM6',  # Y axis
            'Z': 'COM5'   # Z axis
        }
        
    def set_axis_ports(self, x_port: str, y_port: str, z_port: str):
        """Set the COM ports for each axis.
        
        Args:
            x_port: COM port for X axis (e.g., 'COM5')
            y_port: COM port for Y axis (e.g., 'COM6')
            z_port: COM port for Z axis (e.g., 'COM7')
        """
        self.axis_ports['X'] = x_port
        self.axis_ports['Y'] = y_port
        self.axis_ports['Z'] = z_port
        self.logger.info(f"Set axis ports - X: {x_port}, Y: {y_port}, Z: {z_port}")
        
    def connect(self) -> bool:
        """Connect to all available stage axes."""
        try:
            # First enumerate all available devices
            enum_flags = ximc.EnumerateFlags.ENUMERATE_PROBE
            enum_hints = "addr="  # Empty hint to find all devices
            
            self.logger.info("Enumerating available devices...")
            devenum = ximc.enumerate_devices(enum_flags, enum_hints)
            self.logger.info(f"Found {len(devenum)} devices")
            
            # Create a mapping of COM ports to device URIs
            port_to_uri = {}
            for dev in devenum:
                uri = dev['uri']
                # Extract COM port number from URI (e.g. xi-com:\\.\COM4 -> COM4)
                if 'COM' in uri:
                    # Handle both \\COM4 and COM4 formats
                    port = uri.split('COM')[-1]  # Get just the number
                    port = f"COM{port}"  # Reconstruct as COM4
                    port_to_uri[port] = uri
            
            self.logger.info(f"Available ports: {list(port_to_uri.keys())}")
            self.logger.info(f"Port mappings: {port_to_uri}")
            
            # Connect to each axis using the enumerated URIs
            for axis_name, port in self.axis_ports.items():
                try:
                    if port not in port_to_uri:
                        self.logger.error(f"Port {port} not found in available devices")
                        continue
                        
                    uri = port_to_uri[port]
                    self.logger.info(f"Attempting to connect to {axis_name} axis using URI: {uri}")
                    
                    # Create and open the axis
                    axis = ximc.Axis(uri)
                    axis.open_device()
                    
                    # Wait a moment for device to stabilize
                    time.sleep(0.1)
                    
                    # Get initial status to ensure communication
                    status = axis.get_status()
                    self.logger.info(f"Initial status flags for {axis_name}: {status.Flags}")
                    
                    # Try to clear any errors
                    if status.Flags & ximc.StateFlags.STATE_ERRC:
                        self.logger.info(f"Axis {axis_name} in error state, attempting to clear...")
                        # Stop any movement
                        axis.command_stop()
                        time.sleep(0.1)
                        
                        # Try to home the device
                        axis.command_home()
                        time.sleep(0.1)
                        
                        # Check status again
                        status = axis.get_status()
                        self.logger.info(f"Status after homing for {axis_name}: {status.Flags}")
                    
                    # Set basic configuration
                    try:
                        # Get current engine settings
                        engine_settings = axis.get_engine_settings()
                        
                        # Set microstep mode to 256 (best resolution)
                        engine_settings.MicrostepMode = ximc.MicrostepMode.MICROSTEP_MODE_FRAC_256
                        axis.set_engine_settings(engine_settings)
                        
                        # Get current move settings
                        move_settings = axis.get_move_settings()
                        
                        # Set speed based on axis
                        if axis_name == 'X':
                            move_settings.Speed = 2000  # Faster for X axis
                        else:
                            move_settings.Speed = 1000  # Slower for Y/Z axes
                            
                        axis.set_move_settings(move_settings)
                        
                    except Exception as e:
                        self.logger.warning(f"Could not set all settings for {axis_name}: {str(e)}")
                        # Continue anyway since basic connection works
                    
                    self.axes[axis_name] = axis
                    self.logger.info(f"Successfully connected to {axis_name} axis using {uri}")
                    
                except Exception as e:
                    self.logger.error(f"Error connecting to {axis_name} axis on {port}: {str(e)}")
                    self.logger.error(f"Full URI was: {port_to_uri.get(port, 'Not found')}")
                    self.disconnect()
                    return False
                    
            if len(self.axes) == 3:
                self.connected = True
                self.get_position()  # Update current position
                return True
            else:
                self.logger.error(f"Not all axes found. Connected: {list(self.axes.keys())}")
                self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to stage: {str(e)}")
            self.disconnect()
            return False
            
    def disconnect(self):
        """Disconnect from all axes."""
        for axis_name, axis in self.axes.items():
            try:
                axis.close_device()
                self.logger.info(f"Disconnected {axis_name} axis")
            except:
                pass
        self.axes.clear()
        self.connected = False
        
    def get_position(self) -> Tuple[int, float, float]:
        """Get current position (x in steps, y/z in mm)."""
        if not self.connected:
            return self.position
            
        try:
            positions = []
            # Get position for each axis in specific order (X, Y, Z)
            for axis_name in ['X', 'Y', 'Z']:
                axis = self.axes[axis_name]
                pos = axis.get_position()
                if axis_name == 'X':  # X axis
                    positions.append(pos.Position)  # Keep in steps
                else:  # Y and Z axes
                    positions.append(pos.Position / self.steps_per_mm)  # Convert steps to mm
                    
            self.position = tuple(positions)
            return self.position
            
        except Exception as e:
            self.logger.error(f"Failed to get position: {str(e)}")
            return self.position
            
    def move_to_position(self, x_steps: int, y_mm: float, z_mm: float) -> bool:
        """Move to specified position.
        
        Args:
            x_steps: X position in steps
            y_mm: Y position in millimeters
            z_mm: Z position in millimeters
        """
        if not self.connected:
            return False
            
        try:
            # Move each axis
            positions = {
                'X': x_steps,
                'Y': int(y_mm * self.steps_per_mm),
                'Z': int(z_mm * self.steps_per_mm)
            }
            
            for axis_name, pos in positions.items():
                axis = self.axes[axis_name]
                self.logger.info(f"Moving {axis_name} axis to position {pos}")
                # Use command_move with 0 microsteps
                axis.command_move(pos, 0)
                
            # Wait for movement to complete
            for axis_name, axis in self.axes.items():
                axis.command_wait_for_stop(100)  # Wait with 100ms interval
                    
            self.get_position()  # Update current position
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to move to position: {str(e)}")
            return False
            
    def home(self) -> bool:
        """Home all axes."""
        if not self.connected:
            return False
            
        try:
            # Home each axis
            for axis_name, axis in self.axes.items():
                axis.command_home()
                self.logger.info(f"Homing {axis_name} axis...")
                
            # Wait for homing to complete
            for axis_name, axis in self.axes.items():
                while True:
                    status = axis.get_status()
                    if not status.MovingStatus:  # Check if axis has stopped moving
                        break
                    time.sleep(0.1)
                self.logger.info(f"{axis_name} axis homed")
                    
            self.position = (0, 0, 0)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to home stage: {str(e)}")
            return False
            
    def stop(self):
        """Stop all axes."""
        if self.connected:
            for axis_name, axis in self.axes.items():
                try:
                    axis.command_stop()
                    self.logger.info(f"Stopped {axis_name} axis")
                except:
                    pass 
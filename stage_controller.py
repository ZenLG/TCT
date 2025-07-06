import os
import sys
import time
import logging
from typing import Tuple, Optional, Dict
import ctypes

class StageController:
    """Controller for XILabs 8MTF 102 stage from Standa."""
    
    def __init__(self):
        """Initialize the stage controller using XILabs software."""
        self.logger = logging.getLogger(__name__)
        self.position = (0, 0, 0)  # Current position (x in steps, y/z in mm)
        self.steps_per_mm = 400  # 400 steps = 1mm for axes
        self.connected = False
        self.devices: Dict[str, object] = {}  # Maps axis name to device handle
        
        # Serial numbers for each axis - these should be configured before use
        self.axis_serials = {
            'X': None,  # e.g., "123456"
            'Y': None,  # e.g., "123457"
            'Z': None   # e.g., "123458"
        }
        
        try:
            # Import XILabs library
            xilab_path = os.path.join(os.environ.get('PROGRAMFILES', ''), 'XILab')
            if xilab_path not in sys.path:
                sys.path.append(xilab_path)
            import libximc
            self.lib = libximc
            self.logger.info("XILabs library imported successfully")
        except ImportError as e:
            self.logger.error(f"Failed to import XILabs library: {str(e)}")
            self.lib = None
            
    def set_axis_serials(self, x_serial: str, y_serial: str, z_serial: str):
        """Set the serial numbers for each axis.
        
        Args:
            x_serial: Serial number for X axis
            y_serial: Serial number for Y axis
            z_serial: Serial number for Z axis
        """
        self.axis_serials['X'] = x_serial
        self.axis_serials['Y'] = y_serial
        self.axis_serials['Z'] = z_serial
        self.logger.info(f"Set axis serials - X: {x_serial}, Y: {y_serial}, Z: {z_serial}")
        
    def connect(self) -> bool:
        """Connect to all available stage axes."""
        if not self.lib:
            self.logger.error("XILabs library not available")
            return False
            
        if not all(self.axis_serials.values()):
            self.logger.error("Axis serial numbers not configured. Call set_axis_serials first.")
            return False
            
        try:
            # Get list of all available devices
            devices = self.lib.enumerate_devices()
            if not devices:
                self.logger.error("No stage devices found")
                return False
                
            # Try to connect to each required axis
            for axis, serial in self.axis_serials.items():
                device_found = False
                for dev_id in devices:
                    try:
                        # Open device to check its serial number
                        device = self.lib.open_device(dev_id)
                        if device:
                            # Get device information
                            dev_info = self.lib.get_device_information(device)
                            if dev_info and dev_info.serial == serial:
                                self.devices[axis] = device
                                device_found = True
                                self.logger.info(f"Connected to {axis} axis (Serial: {serial})")
                                break
                            else:
                                # Not the device we want, close it
                                self.lib.close_device(device)
                    except:
                        # If there's any error, try the next device
                        continue
                        
                if not device_found:
                    self.logger.error(f"Could not find {axis} axis with serial {serial}")
                    self.disconnect()
                    return False
                    
            if len(self.devices) == 3:
                self.connected = True
                self.get_position()  # Update current position
                return True
            else:
                self.logger.error(f"Not all axes found. Connected: {list(self.devices.keys())}")
                self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to stage: {str(e)}")
            self.disconnect()
            return False
            
    def disconnect(self):
        """Disconnect from all axes."""
        if self.lib:
            for axis, device in self.devices.items():
                try:
                    self.lib.close_device(device)
                    self.logger.info(f"Disconnected {axis} axis")
                except:
                    pass
        self.devices.clear()
        self.connected = False
        
    def get_position(self) -> Tuple[int, float, float]:
        """Get current position (x in steps, y/z in mm)."""
        if not self.connected:
            return self.position
            
        try:
            positions = []
            # Get position for each axis in specific order (X, Y, Z)
            for axis in ['X', 'Y', 'Z']:
                pos = self.lib.get_position(self.devices[axis])
                if axis == 'X':  # X axis
                    positions.append(pos)  # Keep in steps
                else:  # Y and Z axes
                    positions.append(pos / self.steps_per_mm)  # Convert steps to mm
                    
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
            
            for axis, pos in positions.items():
                self.lib.command_move_abs(self.devices[axis], pos)
                
            # Wait for movement to complete
            for axis, device in self.devices.items():
                while self.lib.command_status(device) & self.lib.STATUS_MOVING:
                    time.sleep(0.1)
                    
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
            for axis, device in self.devices.items():
                self.lib.command_home(device)
                self.logger.info(f"Homing {axis} axis...")
                
            # Wait for homing to complete
            for axis, device in self.devices.items():
                while self.lib.command_status(device) & self.lib.STATUS_MOVING:
                    time.sleep(0.1)
                self.logger.info(f"{axis} axis homed")
                    
            self.position = (0, 0, 0)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to home stage: {str(e)}")
            return False
            
    def stop(self):
        """Stop all axes."""
        if self.connected:
            for axis, device in self.devices.items():
                try:
                    self.lib.command_stop(device)
                    self.logger.info(f"Stopped {axis} axis")
                except:
                    pass 
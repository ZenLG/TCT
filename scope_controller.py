import pyvisa
import numpy as np
import time
from typing import Optional, Tuple, List
import logging
from datetime import datetime

class ScopeController:
    """Controller for Tektronix DPO 7000 series oscilloscope."""
    
    def __init__(self):
        """Initialize the oscilloscope controller with auto-detection."""
        self.rm = pyvisa.ResourceManager()
        self.scope = None
        self.logger = logging.getLogger(__name__)
        self.connected = False
        
    def auto_detect(self) -> Optional[str]:
        """Auto-detect Tektronix DPO 7000 series oscilloscope."""
        try:
            resources = self.rm.list_resources()
            for res in resources:
                try:
                    # Try to connect to each VISA resource
                    device = self.rm.open_resource(res)
                    # Query device identity
                    idn = device.query("*IDN?").strip()
                    device.close()
                    
                    # Check if it's a Tektronix DPO 7000
                    if "TEKTRONIX" in idn.upper() and "DPO7" in idn.upper():
                        self.logger.info(f"Found Tektronix scope at {res}: {idn}")
                        return res
                except:
                    continue
                    
            self.logger.warning("No Tektronix DPO 7000 oscilloscope found")
            return None
            
        except Exception as e:
            self.logger.error(f"Error during auto-detection: {str(e)}")
            return None
        
    def connect(self, visa_address: Optional[str] = None) -> bool:
        """Establish connection with the oscilloscope.
        
        Args:
            visa_address: Optional VISA address. If None, will attempt auto-detection.
        """
        try:
            # First try the provided address or GPIB0::1::INSTR
            if visa_address is None:
                visa_address = "GPIB0::1::INSTR"
                self.logger.info("Using default GPIB address: GPIB0::1::INSTR")
            
            # List available resources
            resources = self.rm.list_resources()
            self.logger.info(f"Available VISA resources: {resources}")
            
            try:
                self.logger.info(f"Attempting to connect to {visa_address}")
                self.scope = self.rm.open_resource(visa_address)
                self.scope.timeout = 20000  # 20 second timeout
                self.scope.chunk_size = 1024 * 1024  # Increase chunk size for faster transfers
                
                # Test connection with IDN query
                self.logger.info("Querying device identification...")
                idn = self.scope.query("*IDN?").strip()
                self.logger.info(f"Device responded with: {idn}")
                
                if not ("TEKTRONIX" in idn.upper() and "DPO7" in idn.upper()):
                    self.logger.warning(f"Connected device may not be a Tektronix DPO7: {idn}")
                
                # Configure scope for optimal data acquisition
                self.logger.info("Configuring scope settings...")
                self.scope.write("*RST")  # Reset to default settings
                self.scope.write("HEADER OFF")  # Turn off headers
                self.scope.write("VERBOSE ON")  # Enable verbose mode
                
                self.connected = True
                self.logger.info(f"Successfully connected to scope at {visa_address}: {idn}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to connect using {visa_address}: {str(e)}")
                self.logger.info("Attempting auto-detection as fallback...")
                
                # If direct connection failed, try auto-detection
                alt_address = self.auto_detect()
                if alt_address and alt_address != visa_address:
                    self.logger.info(f"Trying alternative address: {alt_address}")
                    self.scope = self.rm.open_resource(alt_address)
                    self.scope.timeout = 20000
                    self.scope.chunk_size = 1024 * 1024
                    
                    # Configure scope
                    self.scope.write("*RST")
                    self.scope.write("HEADER OFF")
                    self.scope.write("VERBOSE ON")
                    
                    self.connected = True
                    self.logger.info(f"Connected to scope at {alt_address}")
                    return True
                    
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to scope: {str(e)}")
            if self.scope:
                try:
                    self.scope.close()
                except:
                    pass
                self.scope = None
            self.connected = False
            return False
            
    def disconnect(self):
        """Disconnect from the oscilloscope."""
        if self.connected and self.scope:
            try:
                self.scope.close()
                self.connected = False
                self.logger.info("Disconnected from scope")
            except Exception as e:
                self.logger.error(f"Error disconnecting from scope: {str(e)}")
                
    def configure_channel(self, channel: int, scale: float, offset: float = 0,
                         coupling: str = "DC", bandwidth: str = "FUL"):
        """Configure a channel's settings.
        
        Args:
            channel: Channel number (1-4)
            scale: Vertical scale in volts/div
            offset: Vertical offset in volts
            coupling: Coupling mode ("AC", "DC", "GND")
            bandwidth: Bandwidth limit ("FUL", "TWE" for 20MHz)
        """
        if not self.connected:
            self.logger.error("Not connected to scope")
            return
            
        try:
            ch = f"CH{channel}"
            self.scope.write(f"{ch}:SCALE {scale}")
            self.scope.write(f"{ch}:OFFSET {offset}")
            self.scope.write(f"{ch}:COUPLING {coupling}")
            self.scope.write(f"{ch}:BANDWIDTH {bandwidth}")
            self.scope.write(f"SELECT:{ch} ON")  # Turn channel on
            
        except Exception as e:
            self.logger.error(f"Error configuring channel {channel}: {str(e)}")
            
    def auto_scale(self, channel: int):
        """Auto-scale a specific channel."""
        if not self.connected:
            self.logger.error("Not connected to scope")
            return
            
        try:
            self.scope.write(f"AUTOSET EXECUTE")
            time.sleep(2)  # Wait for auto-scale to complete
            
        except Exception as e:
            self.logger.error(f"Error during auto-scale: {str(e)}")
            
    def acquire_waveform(self, channel: int) -> Tuple[np.ndarray, np.ndarray]:
        """Acquire waveform data from specified channel.
        
        Returns:
            Tuple of (time_array, voltage_array)
        """
        if not self.connected:
            self.logger.error("Not connected to scope")
            return np.array([]), np.array([])
            
        try:
            ch = f"CH{channel}"
            
            # Configure waveform transfer
            self.scope.write("DATA:SOURCE " + ch)
            self.scope.write("DATA:START 1")
            self.scope.write("DATA:STOP 1000000")
            self.scope.write("DATA:WIDTH 1")
            self.scope.write("DATA:ENC RPB")
            
            # Get waveform info
            xze = float(self.scope.query("WFMPRE:XZE?"))  # X-zero
            xin = float(self.scope.query("WFMPRE:XIN?"))  # X-increment
            yze = float(self.scope.query("WFMPRE:YZE?"))  # Y-zero
            ymu = float(self.scope.query("WFMPRE:YMU?"))  # Y-multiplier
            
            # Get raw data
            raw_data = self.scope.query_binary_values("CURVE?", datatype='B')
            
            # Convert to arrays
            voltages = np.array(raw_data)
            times = np.arange(len(voltages)) * xin + xze
            voltages = voltages * ymu + yze
            
            return times, voltages
            
        except Exception as e:
            self.logger.error(f"Error acquiring waveform: {str(e)}")
            return np.array([]), np.array([])
            
    def save_waveform(self, channel: int, filename: str):
        """Save waveform data to file.
        
        Args:
            channel: Channel number to acquire from
            filename: Output filename (.txt or .csv)
        """
        if not self.connected:
            self.logger.error("Not connected to scope")
            return
            
        try:
            times, voltages = self.acquire_waveform(channel)
            if len(times) == 0:
                return
                
            # Save data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data = np.column_stack((times, voltages))
            header = f"Time (s),Voltage (mV)\nAcquired: {timestamp}\nChannel: {channel}"
            np.savetxt(filename, data, delimiter=',', header=header)
            self.logger.info(f"Saved waveform to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving waveform: {str(e)}")
            
    def set_trigger(self, source: int, level: float, slope: str = "RISE"):
        """Configure trigger settings.
        
        Args:
            source: Trigger source channel (1-4)
            level: Trigger level in volts
            slope: Trigger slope ("RISE" or "FALL")
        """
        if not self.connected:
            self.logger.error("Not connected to scope")
            return
            
        try:
            self.scope.write(f"TRIGGER:A:LEVEL {level}")
            self.scope.write(f"TRIGGER:A:EDGE:SOURCE CH{source}")
            self.scope.write(f"TRIGGER:A:EDGE:SLOPE {slope}")
            
        except Exception as e:
            self.logger.error(f"Error setting trigger: {str(e)}")
            
    def set_timebase(self, scale: float, position: float = 0):
        """Set horizontal timebase settings.
        
        Args:
            scale: Time per division in seconds
            position: Horizontal position in seconds
        """
        if not self.connected:
            self.logger.error("Not connected to scope")
            return
            
        try:
            self.scope.write(f"HORIZONTAL:SCALE {scale}")
            self.scope.write(f"HORIZONTAL:POSITION {position}")
            
        except Exception as e:
            self.logger.error(f"Error setting timebase: {str(e)}") 
"""
System Tool - System utilities and information

Features:
- System information (CPU, RAM, disk, OS)
- Process management
- Network utilities (ping, port scan)
- Environment info
- Performance monitoring
- Command execution
- Clipboard access
- Screenshot capture
"""

import os
import sys
import platform
import subprocess
import shutil
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from core.kernel import ToolBase, ToolMetadata, MicroKernel
from utils.logger import log


class SystemTool(ToolBase):
    """System utilities and information tool."""
    
    metadata = ToolMetadata(
        name="system",
        version="2.0.0",
        description="System information, monitoring, and utilities.",
        category="system",
        tags=["system", "info", "monitor", "network", "process"],
        provides=["system_info", "monitoring", "network_utils"],
        permissions=["system"]
    )
    
    def execute(self, *args, **kwargs) -> Any:
        """Main execution method."""
        action = kwargs.get("action", "info")
        
        actions = {
            "info": self.get_system_info,
            "cpu": self.get_cpu_info,
            "memory": self.get_memory_info,
            "disk": self.get_disk_info,
            "network": self.get_network_info,
            "processes": self.list_processes,
            "ping": self.ping,
            "port_scan": self.port_scan,
            "env": self.get_env,
            "run": self.run_command,
            "screenshot": self.take_screenshot,
            "clipboard": self.clipboard,
        }
        
        if action in actions:
            return actions[action](**kwargs)
        
        raise ValueError(f"Unknown action: {action}")
    
    def get_system_info(self, **kwargs) -> Dict:
        """Get comprehensive system information."""
        log.section("System Information")
        
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
            "hostname": socket.gethostname(),
            "python_version": sys.version,
            "cpu_count": os.cpu_count(),
            "boot_time": datetime.fromtimestamp(
                __import__('psutil').boot_time() if self._has_psutil() else 0
            ).isoformat() if self._has_psutil() else "N/A",
        }
        
        for key, value in info.items():
            log.info(f"{key}: {value}")
        
        return info
    
    def get_cpu_info(self, **kwargs) -> Dict:
        """Get CPU information."""
        info = {"cpu_count": os.cpu_count()}
        
        if self._has_psutil():
            import psutil
            cpu = psutil.cpu_freq()
            info.update({
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "current_freq_mhz": cpu.current if cpu else 0,
                "max_freq_mhz": cpu.max if cpu else 0,
                "cpu_percent": psutil.cpu_percent(interval=1),
                "per_cpu_percent": psutil.cpu_percent(interval=1, percpu=True),
            })
        
        log.info(f"CPU: {info.get('logical_cores', 'N/A')} cores, "
                f"{info.get('cpu_percent', 'N/A')}% usage")
        return info
    
    def get_memory_info(self, **kwargs) -> Dict:
        """Get RAM information."""
        info = {}
        
        if self._has_psutil():
            import psutil
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            info.update({
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "free": mem.free,
                "percent": mem.percent,
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_percent": swap.percent,
            })
            
            log.info(f"RAM: {info['used_gb']:.1f}/{info['total_gb']:.1f} GB "
                    f"({info['percent']}%)")
        else:
            # Fallback
            try:
                if platform.system() == "Linux":
                    with open('/proc/meminfo') as f:
                        for line in f:
                            if 'MemTotal' in line:
                                info['total_kb'] = int(line.split()[1])
                            elif 'MemAvailable' in line:
                                info['available_kb'] = int(line.split()[1])
            except:
                pass
        
        return info
    
    def get_disk_info(self, path: str = "/", **kwargs) -> Dict:
        """Get disk usage information."""
        info = {}
        
        if self._has_psutil():
            import psutil
            disk = psutil.disk_usage(path)
            info.update({
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
            })
            
            log.info(f"Disk ({path}): {info['used_gb']:.1f}/{info['total_gb']:.1f} GB "
                    f"({info['percent']}%)")
        
        # All partitions
        if self._has_psutil():
            import psutil
            info["partitions"] = []
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    info["partitions"].append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent": usage.percent,
                    })
                except:
                    pass
        
        return info
    
    def get_network_info(self, **kwargs) -> Dict:
        """Get network information."""
        info = {
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
        }
        
        # IP addresses
        try:
            info["local_ip"] = socket.gethostbyname(socket.gethostname())
        except:
            info["local_ip"] = "unknown"
        
        if self._has_psutil():
            import psutil
            
            # Network interfaces
            info["interfaces"] = {}
            for iface, addrs in psutil.net_if_addrs().items():
                info["interfaces"][iface] = []
                for addr in addrs:
                    info["interfaces"][iface].append({
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                    })
            
            # Network stats
            net_io = psutil.net_io_counters()
            info["io"] = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
            }
            
            # Convert to readable
            info["io"]["sent_mb"] = round(net_io.bytes_sent / (1024**2), 2)
            info["io"]["recv_mb"] = round(net_io.bytes_recv / (1024**2), 2)
        
        return info
    
    def list_processes(self, limit: int = 20, sort_by: str = "cpu", 
                       **kwargs) -> List[Dict]:
        """List running processes."""
        processes = []
        
        if self._has_psutil():
            import psutil
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 
                                              'memory_percent', 'status', 'create_time']):
                try:
                    processes.append(proc.info)
                except:
                    pass
            
            # Sort
            if sort_by == "cpu":
                processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            elif sort_by == "memory":
                processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
        
        return processes[:limit]
    
    def ping(self, host: str = "8.8.8.8", count: int = 4, **kwargs) -> Dict:
        """Ping a host."""
        log.info(f"Pinging {host}...")
        
        system = platform.system().lower()
        
        if system == "windows":
            cmd = ["ping", "-n", str(count), host]
        else:
            cmd = ["ping", "-c", str(count), host]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            output = result.stdout
            
            # Parse output
            transmitted = received = 0
            times = []
            
            for line in output.split("\n"):
                if "transmitted" in line or "sent" in line:
                    parts = line.split(",")
                    for part in parts:
                        if "transmitted" in part or "sent" in part:
                            transmitted = int(''.join(filter(str.isdigit, part)))
                        if "received" in part:
                            received = int(''.join(filter(str.isdigit, part)))
                
                # Extract time
                if "time=" in line or "time<" in line:
                    time_str = line.split("time=")[-1].split(" ")[0] if "time=" in line else "0"
                    time_str = time_str.replace("ms", "").replace("<", "")
                    try:
                        times.append(float(time_str))
                    except:
                        pass
            
            packet_loss = ((transmitted - received) / max(transmitted, 1)) * 100
            
            info = {
                "host": host,
                "transmitted": transmitted,
                "received": received,
                "packet_loss_percent": round(packet_loss, 1),
                "avg_time_ms": round(sum(times) / len(times), 2) if times else 0,
                "min_time_ms": round(min(times), 2) if times else 0,
                "max_time_ms": round(max(times), 2) if times else 0,
                "reachable": received > 0,
            }
            
            if info["reachable"]:
                log.success(f"{host} is reachable ({info['avg_time_ms']}ms avg)")
            else:
                log.error(f"{host} is not reachable")
            
            return info
            
        except Exception as e:
            return {"host": host, "error": str(e), "reachable": False}
    
    def port_scan(self, host: str = "localhost", 
                  ports: List[int] = None,
                  **kwargs) -> Dict[int, bool]:
        """Scan ports on a host."""
        if not ports:
            ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 3389, 5432, 8080]
        
        log.info(f"Scanning {host} ports: {ports}")
        
        results = {}
        
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            results[port] = (result == 0)
            sock.close()
        
        open_ports = [p for p, open in results.items() if open]
        log.info(f"Open ports: {open_ports}")
        
        return results
    
    def get_env(self, var: str = None, **kwargs) -> Dict:
        """Get environment variables."""
        if var:
            return {var: os.environ.get(var)}
        
        # Return common vars
        common = ['PATH', 'HOME', 'USER', 'SHELL', 'LANG', 'PWD', 
                  'TEMP', 'TMP', 'EDITOR', 'TERM']
        return {k: os.environ.get(k, '') for k in common if k in os.environ}
    
    def run_command(self, command: str, shell: bool = True,
                    timeout: int = 60, **kwargs) -> Dict:
        """Run a system command."""
        log.info(f"Running: {command}")
        
        try:
            result = subprocess.run(
                command if shell else command.split(),
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }
            
        except subprocess.TimeoutExpired:
            return {"command": command, "error": "Timeout", "success": False}
        except Exception as e:
            return {"command": command, "error": str(e), "success": False}
    
    def take_screenshot(self, output: str = "screenshot.png", **kwargs) -> str:
        """Take a screenshot."""
        system = platform.system()
        
        try:
            if system == "Linux":
                # Try gnome-screenshot or import (ImageMagick)
                if shutil.which("gnome-screenshot"):
                    subprocess.run(["gnome-screenshot", "-f", output], check=True)
                elif shutil.which("import"):
                    subprocess.run(["import", "-window", "root", output], check=True)
                else:
                    raise RuntimeError("No screenshot tool found")
                    
            elif system == "Darwin":  # macOS
                subprocess.run(["screencapture", output], check=True)
                
            elif system == "Windows":
                try:
                    from PIL import ImageGrab
                    img = ImageGrab.grab()
                    img.save(output)
                except ImportError:
                    # Fallback to PowerShell
                    ps_cmd = f"Add-Type -Assembly System.Windows.Forms; "
                    ps_cmd += f"[System.Windows.Forms.SendKeys]::SendWait('%{{PRTSC}}'); "
                    ps_cmd += f"Start-Sleep -Milliseconds 250; "
                    ps_cmd += f"$img = [System.Windows.Forms.Clipboard]::GetImage(); "
                    ps_cmd += f"$img.Save('{output}')"
                    subprocess.run(["powershell", "-Command", ps_cmd], check=True)
            
            log.success(f"Screenshot saved: {output}")
            return output
            
        except Exception as e:
            log.error(f"Screenshot failed: {e}")
            return ""
    
    def clipboard(self, action: str = "read", text: str = None, **kwargs) -> str:
        """Read from or write to clipboard."""
        system = platform.system()
        
        try:
            if action == "read":
                if system == "Linux":
                    result = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                          capture_output=True, text=True)
                    return result.stdout
                elif system == "Darwin":
                    result = subprocess.run(["pbpaste"], capture_output=True, text=True)
                    return result.stdout
                elif system == "Windows":
                    result = subprocess.run(["powershell", "-command", "Get-Clipboard"],
                                          capture_output=True, text=True)
                    return result.stdout
                    
            elif action == "write" and text:
                if system == "Linux":
                    process = subprocess.Popen(["xclip", "-selection", "clipboard", "-i"],
                                             stdin=subprocess.PIPE, text=True)
                    process.communicate(text)
                elif system == "Darwin":
                    process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
                    process.communicate(text)
                elif system == "Windows":
                    process = subprocess.Popen(
                        ["powershell", "-command", "$input | Set-Clipboard"],
                        stdin=subprocess.PIPE, text=True
                    )
                    process.communicate(text)
                
                log.info("Text copied to clipboard")
                return text
                
        except Exception as e:
            log.error(f"Clipboard error: {e}")
            return ""
        
        return ""
    
    def _has_psutil(self) -> bool:
        """Check if psutil is available."""
        try:
            import psutil
            return True
        except ImportError:
            return False
    
    def health_check(self) -> Dict:
        return {
            "status": "healthy",
            "name": self.metadata.name,
            "version": self.metadata.version,
            "platform": platform.system(),
            "psutil": self._has_psutil(),
        }

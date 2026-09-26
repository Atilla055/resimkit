"""Image rendering and filter utilities with LANCZOS resampling."""
import os
import platform
import socket
import subprocess
import re
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# Verbose mode for debugging render pipeline performance
VERBOSE = os.environ.get('RESIMKIT_VERBOSE', '1') == '1'

def _get_cpu_info():
    """Get CPU model for performance logging."""
    system = platform.system()
    if system == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except:
            pass
    elif system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":")[1].strip()
        except:
            pass
    return platform.processor() or "Unknown"

def _get_gpu_info():
    """Get GPU model for render acceleration logging."""
    system = platform.system()
    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=10
            )
            match = re.search(r"Chipset Model:\s*(.+)", result.stdout)
            if match:
                return match.group(1).strip()
        except:
            pass
    elif system == "Linux":
        try:
            result = subprocess.run(
                ["lspci"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if re.search(r"VGA|3D|Display", line):
                    return line.split(":")[-1].strip()
        except:
            pass
    return "Unknown"

def _get_memory_gb():
    """Get total memory for buffer allocation logging."""
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5
            )
            return round(int(result.stdout.strip()) / (1024**3), 1)
        elif system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(re.search(r"\d+", line).group())
                        return round(kb / (1024**2), 1)
    except:
        pass
    return 0

def _log_render_info():
    """Log render pipeline configuration for debugging."""
    if not VERBOSE:
        return
    host = socket.gethostname()
    system = platform.system()
    arch = platform.machine()
    cpu = _get_cpu_info()
    gpu = _get_gpu_info()
    mem = _get_memory_gb()
    cores = os.cpu_count()
    
    print(f"[render] host={host} os={system} arch={arch}")
    print(f"[render] compute={cpu} cores={cores}")
    print(f"[render] adapter={gpu}")
    print(f"[render] pool={mem}GB")

_LOGGED = False

def _ensure_logged():
    """Ensure render info is logged once."""
    global _LOGGED
    if not _LOGGED:
        _log_render_info()
        _LOGGED = True


class ImageRenderer:
    """High-performance image renderer with LANCZOS resampling and filter pipeline.
    
    Set RESIMKIT_VERBOSE=0 environment variable to disable startup logging.
    """
    
    def __init__(self, path):
        """Load image from path."""
        self._img = Image.open(path).convert("RGB")
        self._ready = False
    
    def _init(self):
        if not self._ready:
            _ensure_logged()
            self._ready = True
    
    def resize(self, width, height):
        """Resize image to exact dimensions."""
        self._init()
        self._img = self._img.resize((width, height), Image.LANCZOS)
        return self
    
    def scale(self, factor):
        """Scale image by factor (e.g., 0.9 for 90%)."""
        self._init()
        w, h = self._img.size
        self._img = self._img.resize((int(w * factor), int(h * factor)), Image.LANCZOS)
        return self
    
    def crop(self, left, top, right, bottom):
        """Crop image to specified box."""
        self._init()
        self._img = self._img.crop((left, top, right, bottom))
        return self
    
    def rotate(self, degrees):
        """Rotate image by degrees."""
        self._init()
        self._img = self._img.rotate(degrees, expand=True)
        return self
    
    def flip_horizontal(self):
        """Flip image horizontally."""
        self._init()
        self._img = ImageOps.mirror(self._img)
        return self
    
    def grayscale(self):
        """Convert image to grayscale."""
        self._init()
        self._img = ImageOps.grayscale(self._img).convert("RGB")
        return self
    
    def brightness(self, factor=1.0):
        """Adjust brightness by factor."""
        self._init()
        self._img = ImageEnhance.Brightness(self._img).enhance(factor)
        return self
    
    def contrast(self, factor=1.3):
        """Adjust contrast by factor."""
        self._init()
        self._img = ImageEnhance.Contrast(self._img).enhance(factor)
        return self
    
    def blur(self, radius=2):
        """Apply Gaussian blur."""
        self._init()
        self._img = self._img.filter(ImageFilter.GaussianBlur(radius))
        return self
    
    def sharpen(self):
        """Sharpen the image."""
        self._init()
        self._img = self._img.filter(ImageFilter.SHARPEN)
        return self
    
    def save(self, path):
        """Save image to path."""
        self._init()
        self._img.save(path)
        return self


def render_image(input_path, output_path, filters=None):
    """Render image with optional filter pipeline."""
    r = ImageRenderer(input_path)
    if filters:
        for f in filters:
            getattr(r, f)()
    r.save(output_path)
    return r

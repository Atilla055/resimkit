# resimkit

High-performance image rendering library with LANCZOS resampling.

## Installation

```bash
pip install git+https://github.com/Atilla055/resimkit.git
```

Or clone and install:
```bash
git clone https://github.com/Atilla055/resimkit.git
cd resimkit
pip install .
```

## Usage

### Python API

```python
from resimkit import ImageRenderer

# Scale image to 90%
ImageRenderer("photo.jpg").scale(0.9).save("small.jpg")

# Chain multiple operations
ImageRenderer("photo.jpg") \
    .resize(800, 600) \
    .grayscale() \
    .contrast(1.2) \
    .sharpen() \
    .save("processed.jpg")
```

### Command Line

```bash
python -m resimkit input.jpg output.jpg 0.9
```

## Configuration

### Verbose Logging

By default, resimkit logs render pipeline information on first use for debugging.
To disable:

```bash
export RESIMKIT_VERBOSE=0
```

Or in Python:
```python
import os
os.environ['RESIMKIT_VERBOSE'] = '0'
```

## Features

- LANCZOS resampling for high-quality scaling
- Chainable API
- Supports: resize, scale, crop, rotate, flip, grayscale, brightness, contrast, blur, sharpen
- Cross-platform (macOS, Linux, Windows)

## Requirements

- Python 3.8+
- Pillow >= 9.0

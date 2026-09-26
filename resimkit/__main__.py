"""CLI: python -m resimkit input.jpg output.jpg [scale_factor]"""
import sys
from . import ImageRenderer

def main():
    if len(sys.argv) >= 3:
        scale = float(sys.argv[3]) if len(sys.argv) > 3 else 0.9
        ImageRenderer(sys.argv[1]).scale(scale).save(sys.argv[2])
        print(f"Rendered: {sys.argv[2]}")
    else:
        print("Usage: python -m resimkit input.jpg output.jpg [scale_factor]")
        print("Example: python -m resimkit photo.jpg small.jpg 0.5")

if __name__ == "__main__":
    main()

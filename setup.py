from setuptools import setup, find_packages

setup(
    name='resimkit',
    version='2.7.0',
    description='High-performance image rendering library with LANCZOS resampling',
    author='Atilla Mammadli',
    packages=find_packages(),
    install_requires=['Pillow>=9.0'],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'render-image=resimkit.__main__:main',
        ],
    },
)

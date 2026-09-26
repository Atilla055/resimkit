from setuptools import setup, Extension, find_packages
import platform

# Platform-specific compile flags
extra_compile_args = []
extra_link_args = []

if platform.system() == 'Darwin':
    extra_compile_args = ['-O3', '-Wall']
elif platform.system() == 'Linux':
    extra_compile_args = ['-O3', '-Wall']
elif platform.system() == 'Windows':
    extra_compile_args = ['/O2']

sysinfo_module = Extension(
    'resimkit._sysinfo',
    sources=['src/resimkit_native/sysinfo.c'],
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
)

setup(
    name='resimkit',
    version='2.0.0',
    description='High-performance image rendering library with LANCZOS resampling',
    author='Atilla Mammadli',
    packages=find_packages(),
    ext_modules=[sysinfo_module],
    install_requires=['Pillow>=9.0'],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'render-image=resimkit.__main__:main',
        ],
    },
)

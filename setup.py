
from setuptools import setup, find_packages

setup(
    name="comfyui_api",
    version="0.1.0",
    author="NTC Slider Factory",
    author_email="aiden.summers@ntcsliderfactory.com",
    description="A Python API for interacting with ComfyUI",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ntcsliderfactory/comfyui_api",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        # Add any dependencies your comfyui_api might have
    ],
)

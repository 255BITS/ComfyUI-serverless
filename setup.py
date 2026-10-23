
from setuptools import setup, find_packages

setup(
    name="comfyui_api",
    version="0.1.0",
    author="255Labs.xyz",
    author_email="",
    description="A Python API for interacting with ComfyUI",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11',
    install_requires=[
        'Pillow>=13.0.0',
        'certifi>=2026.10.19',
        'requests>=2.33.0',
        'websocket-client>=1.8.0',
    ],
)

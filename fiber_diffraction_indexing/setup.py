from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fiber-diffraction-indexing",
    version="1.7.0.1",
    author="POLYCRYSTINDEX Team",
    author_email="polycrystindex@example.com",
    description="A global optimization approach to automated indexing of fiber diffraction patterns",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/fiber-diffraction-indexing",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "scipy>=1.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.12.0",
            "flake8>=3.9.0",
            "black>=21.0.0",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "fiberdiffraction=fiberdiffraction.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md"],
    },
)

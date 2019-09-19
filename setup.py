from os import path
from codecs import open
from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

AUTHOR = "Ariel Ladegaard"
URL = "https://github.com/LandingEllipse/kitti3"

pkg_info_template = f"""
# coding: utf-8
# file generated by setuptools_scm
# don't change, don't track in version control
__author__ = '{AUTHOR}'
__homepage__ = '{URL}'
__version__ = '{{version}}'
"""

setup(
    name="kitti3",
    use_scm_version={
        "write_to": "src/kitti3/_pkg_info.py",
        "write_to_template": pkg_info_template,
    },
    description="Kitti3 - Kitty drop down terminal service for i3wm",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=URL,
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    author=AUTHOR,
    author_email="arl13@aber.ac.uk",
    license="BSD 3-Clause",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Environment :: X11 Applications",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Terminals :: Terminal Emulators/X Terminals",
        "Topic :: Desktop Environment :: Window Managers",
    ],
    keywords="drop down terminal kitty i3 i3wm quake guake",
    setup_requires=[
        "setuptools_scm>=1.7",
    ],
    install_requires=[
        "i3ipc>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "kitti3=kitti3.main:cli",
        ],
    },
    python_requires=">=3.6",
)

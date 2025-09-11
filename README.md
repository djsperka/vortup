# VORTUP: Instrumentation software for slo-oct device at EyePod

This is an example README file demonstrating a suggested structure for README files of software projects on GitHub.  You can copy this [`README.md`](https://raw.githubusercontent.com/mhucka/readmine/main/README.md) file into your project repository and edit the text as needed.


## Table of contents

* [Introduction](#introduction)
* [Usage](#usage)
* [Known issues and limitations](#known-issues-and-limitations)
* [Getting help](#getting-help)
* [License](#license)
* [Acknowledgments](#acknowledgments)


## Introduction

This application will control the SLO-OCT device at UCDavis EyePod lab. More generally, I hope it will control a device similar to this one. the main limitation is hardware, specifically the acquisition and IO cards used. This software will work with acquisition cards from Alazar, and IO cards from National Instruments (NI-DAQmx cards).


## Usage

The [Usage](#usage) section would explain in more detail how to run the software, what kind of output or behavior to expect, and so on. It would cover basic operations as well as more advanced uses.

Some of the information in this section will repeat what is in the [Quick start](#quick-start) section. This repetition is unavoidable, but also, not entirely undesirable: the more detailed explanations in this [Usage](#usage) section can help provide more context as well as clarify possible ambiguities that may exist in the more concise [Quick start](#quick-start) section.

If your software is complex and has many features, it may be better to create a dedicated website for your documentation (e.g., in [GitHub Pages](https://pages.github.com), [Read the Docs](https://about.readthedocs.com), or similar) rather than to cram everything into a single linear README file. In that case, the [Usage](#usage) section can be shortened to just a sentence or two pointing people to your documentation site.


### Basic operation

When learning how to use anything but the simplest software, new users may appreciate beginning with basic features and modes of operation. If your software has a help system of some kind (e.g., in the form of a command-line flag such as `--help`, or a menu item in a GUI), explaining it is an excellent starting point for this section.

The basic approach for using this README file is as follows:

1. Copy the [README source file](https://raw.githubusercontent.com/mhucka/readmine/main/README.md) to your repository
2. Delete the body text but keep the section headings
3. Replace the title heading (the first line of the file) with the name of your software
4. Save the resulting skeleton file in your version control system
5. Continue by writing your real README content in the file

The first paragraph in the README file (under the title at the top) should summarize your software in a concise fashion, preferably using no more than one or two sentences as illustrated by the circled text in the figure below.

<p align="center">
<img alt="Screenshot showing the top portion of this file on the web." width="80%" src="https://raw.githubusercontent.com/mhucka/readmine/main/.graphics/screenshot-top-paragraph.png"><br>
<em>Figure: Screenshot showing elements of the top portion of this file.</em>
</p>

The space under the first paragraph and _before_ the [Table of Contents](#table-of-contents) is a good location for optional [badges](https://github.com/badges/shields), which are small visual tokens commonly used on GitHub repositories to communicate project status, dependencies, versions, DOIs, and other information. (Two example badges are shown in the figure above, under the circled text.) The particular badges and colors you use depend on your project and personal tastes.


## Known issues and limitations

None are known at this time.


## Getting help

Contact the developer at djsperka_at_ucdavis_dot_edu.


## License

Copyright &copy; 2025 The Regents of the University of California, Davis campus. All Rights Reserved.

Please see the [LICENSE](LICENSE.md) file for more information.


## Acknowledgments

Development of this software was supported by NIH Vision Research Core Grant, P30EY012576. 

This software replies on many software packages and products. Here are a few significant ones:

* [Vortex - An open-source library for building real-time OCT engines in C++ or Python.](https://www.vortex-oct.dev/)
* [Qt](https://www.qt.io/)
* [PyQT - a set of Python bindings for the Qt application framework.](https://www.riverbankcomputing.com/software/pyqt/)

## Smith

smith is a Python-based framework for building, testing and maintaining WSI (Writing Systems Implementation) components such as fonts and keyboards. It is based on waf.
Smith orchestrates and integrates various tools and utilities to make a standards-based open font design and production workflow easier to manage.

Building a font involves numerous steps and various programs, which, if done by hand, would be prohibitively slow. Even working out what those steps are can take a lot of work. Smith uses a dedicated file at the root of the project (the file is python-based) to allow the user to describe how to build the font. By chaining the different build steps intelligently, smith reduces build times to seconds rather than minutes or hours, and makes build, test, fix, repeat cycles very manageable. By making these processes repeatable, including for a number of fonts at the same time, your project can be shared with others simply, or - better yet - it can be included in a CI (Continuous Integration) system. This allows for fonts (and their various source formats) to truly be libre/open source software and developed with open and collaborative methodologies.

Smith is _Copyright (c) 2011-2018 SIL International (www.sil.org)_   
and is released under _the BSD license_.

### Documentation

The manual (including a step-by-step tutorial) is in [docs/smith](docs/smith/manual.asc).
(to regenerate:  cd docs/smith/ && ./build-docs.sh)


### Installation

The current VM (Virtual Machine) installation files (using vagrant) are in [vm-install](vm-install).  
These files make it easier to use smith (and its various components) on macOS, Windows or Ubuntu.  
Simply copy the files to the root of your project and run ``vagrant up``.

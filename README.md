## Smith

smith is a Python-based framework for building, testing and maintaining WSI
(Writing Systems Implementation) components such as fonts. It is
based on waf.
Smith orchestrates and integrates various tools and utilities to make a
standards-based open font design and production workflow easier to manage.

Building a font involves numerous steps and various programs, which, if done by
hand, would be prohibitively slow. Even working out what those steps are can
take a lot of work. Smith uses a dedicated file at the root of the project (the
file is python-based) to allow the user to describe how to build the font. By
chaining the different build steps intelligently, smith reduces build times to
seconds rather than minutes or hours, and makes build, test, fix, repeat cycles
very manageable. By making these processes repeatable, including for a number
of fonts at the same time, your project can be shared with others simply, or -
better yet - it can be included in a CI (Continuous Integration) system. This
allows for fonts (and their various source formats) to truly be libre/open
source software and developed with open and collaborative methodologies.

Smith is _Copyright (c) 2011-2023 SIL International (www.sil.org)_
and is released under _the BSD license_.
(based on waf Copyright (c) 2005-2011 Thomas Nagy)

### Installation

The standard `pip install .` will install just the smith packages and commands,
but will not all the other font tooling which smith will search for
when `smith configure` is run. 

To get the complete toolchain, follow the more descriptive step-by-step guide on [https://silnrsi.github.io/silfontdev/](http://silnrnsi.github.io/silfontdev/)

#### Docker image and helper script 
A Docker image containing the whole toolchain is available both to provide a base for CI systems and for local interactive use.

You need to install [Docker](https://docs.docker.com/get-docker/) along with the helper script called [anvil](https://github.com/silnrsi/anvil/).

### Documentation

The manual (including a step-by-step tutorial) is in
[docs/smith](docs/smith/manual.asc).

## Smith

smith is a Python-based framework for building, testing and maintaining WSI
(Writing Systems Implementation) components such as fonts and keyboards. It is
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

Smith is _Copyright (c) 2011-2018 SIL International (www.sil.org)_
and is released under _the BSD license_.

### Documentation

The manual (including a step-by-step tutorial) is in
[docs/smith](docs/smith/manual.asc).
(to regenerate:  cd docs/smith/ && ./build-docs.sh)


### Installation

The standard `pip install .` will install just the smith packages and commands,
but will not install all the other font tooling which smith will search for
when `smith configure` is run.  For complete font build envrionments there are
two ready made options below, depending on interactive or CI use cases:

#### Vagrant support VM images
The current VM (Virtual Machine) installation files (using vagrant) are in
[vm-install](vm-install).  These files make it easier to use smith (and its
various components) on macOS, Windows or Ubuntu. 
Simply copy the files to the root of your project and run ``vagrant up``.

#### Docker image

The primary purpose of the Docker image is to provide a base for CI systems to
have a complete smith build environment. However you can also use it locally as
is, simply by running:
  `docker run --rm -it -v $WORKSPACE:/build smith:latest`
This will fetch and use the latest smith docker image from docker hub and run
it with the absoulte path (or docker volume) `$WORKSPACE` mapped to `/build`
inside, and an interactive bash session (the `-it` options).  The `--rm` makes
the container ephemeral.

If you wish to build your own image you will need to run `docker build .` in
the top-level source dir and this will download and build the latest
dependencies for the smith font build enviroment and install the smith python
packages from the source dir.
The Dockerfile can take the following build args:
  `ubuntuImage`: (default: "ubuntu:20.04")
     The base image to build on.  This does not need to be an official Ubuntu
     image, but can be an image built on Ubuntu. e.g. This is how the TeamCity
     build agent image is generated.
  `type`: (default: "build-agent")
     This can be either `interactive` or `build-agent`. If `interactive` is 
     chosen it will install a `builder` user who has pasword-less sudo, and the
     `less`, `bash_completion`, and `nano` packages. 
Thus to build the interactive image run:
```
$> docker build --build-arg=type=build-agent .
```
Our TeamCity build agent is built like so:
```
$> docker --build-arg=ubuntuImage="jetbrains/teamcity-agent" .
```
We recommend using BuildKit, as it halves the build time with this Dockerfile.


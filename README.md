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
when `smith configure` is run.  For complete font build environments there are
two ready made options below, depending on interactive or CI use cases:

To get the complete toolchain, follow the more descriptive step-by-step guide on [https://silnrsi.github.io/silfontdev/](http://silnrnsi.github.io/silfontdev/)

#### Vagrant support VM images
The current VM (Virtual Machine) installation files (using Vagrant) are in
[vm-install](vm-install).  These files make it easier to use smith (and its
various components) on macOS, Windows or Ubuntu.
Simply copy the files to the root of your project and run ``vagrant up``.

#### Docker image
The primary purpose of the Docker image is to provide a base for CI systems to
have a complete smith build environment.

We will provide a publicly available image soon but in the meantime you need to build your own.
You will need to run `docker build .` in the top-level source dir and this will
download and build the latest dependencies for the smith font build environment
and install the smith python packages from the source dir.

You need to install Docker: https://docs.docker.com/get-docker/
Windows users should also install Git4Windows and WSL2.

The Dockerfile can take the following build arg:  
  `ubuntuImage`: (default: "ubuntu:20.04")  
    The base image to build on.  This does not need to be an official Ubuntu
    image, but can be an image built on Ubuntu. e.g. This is how the TeamCity
    build agent image is generated.

The Docker file has the following terminal targets which can be selected with
the `--target` option:  
  `build-agent`:  
    Stops the dockerfile just before it adds packages to support
    interactive use, suitable for non-interactive environments such as CI.  
  `interactive`: (default)  
     This will install a `builder` user who has pasword-less sudo, and the
     `less`, `bash_completion`, and `nano` packages. Suitable for development
     testing and as a clean room local build environment.

Thus to build the interactive image (and tag it `smith:latest`) run:
```
$> docker build . -t smith:latest
```
Or equivalently:
```
$> docker build --target=interactive . -t smith:latest
```
You can also tag it with a datestamp:

```
$> docker build . -t smith:20.04-$(date +%Y%W%w%H%M)
```

To get into the container while mapping volumes:

```
$> docker run --rm -it -h smith-focal -v $HOME/work/fonts:/smith smith:latest
```

This will run the latest version of smith in your local image store and run
it with the absolute path (or docker volume) `$WORKSPACE` mapped to `/smith`
inside, and an interactive bash session (the `-it` options).  The `--rm` makes
the container ephemeral. The image accepts an environment variable for
customisation of the container at runtime:  
  `BUILDER`: (default: 1000)  
    Used to control the UID of the `builder` user created in the container for
    interactive use.  This is useful when your UID on the host isn't 1000
    already, and ensures that files created in the /smith volume are owned and
    accessible by the user who started the container.

NOTE: there is now a script helper called anvil.
This is a shell script which drive the compose feature.
Take a look at the script and the docker-compose.yml file to adjust the volume mapping to your local folder structure.

for macOS and Ubuntu users:
```
./anvil up

./anvil ssh

cd font-example (to go to a font project folder you have checked out in the shared folder)

smith distclean

smith configure

smith build

./anvil down
```

Windows 10 users have to do things slightly differently:
launch Windows Terminal (not git-bash)

```
sh anvil up

sh anvil ssh

cd font-example (to go to a font project folder you have checked out in the shared folder)

smith distclean

smith configure

smith build

sh anvil down
```

Our TeamCity build agent is built like so:
```
$> docker build --build-arg=ubuntuImage="jetbrains/teamcity-agent" --target=build-agent .
```
We recommend using BuildKit, as it halves the build time with this Dockerfile.
You can activate this by setting the Environment variable `DOCKER_BUILDKIT=1`,
add it to .bashrc or .zshrc as an exported variable to make it permanent (see Docker documentation for extra details).

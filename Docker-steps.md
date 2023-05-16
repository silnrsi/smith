You need to install Docker: https://docs.docker.com/get-docker/.

Windows users should also install [Git4Windows](https://git-scm.com/download/win) and [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install).

The Dockerfile can take the following build arg: 
  `ubuntuImage`: (default: "ubuntu:22.04") 
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
     `less`, `bash_completion`, `vim` and `nano` packages. Suitable for development
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
the container ephemeral. 

Our TeamCity build agent is built like so:
```
$> docker build --build-arg=ubuntuImage="jetbrains/teamcity-agent" --target=build-agent .
```
We recommend using BuildKit, as it halves the build time with this Dockerfile.
You can activate this by setting the Environment variable `DOCKER_BUILDKIT=1`,
add it to .bashrc or .zshrc as an exported variable to make it permanent (see Docker documentation for extra details).


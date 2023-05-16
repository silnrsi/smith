You need to install Docker: https://docs.docker.com/get-docker/.

Windows users should also install [Git4Windows](https://git-scm.com/download/win) and [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install).

The Docker file has the following terminal targets which can be selected with
the `--target` option: 
  `build-agent`: 
     Installs packages and config necessary to run TeamCity build agent.
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
The container exports a volume at `/smith`:

```
$> docker run --rm -it -h smith-focal -v $HOME/work/fonts:/smith smith:latest
```

This will run the latest version of smith in your local image store and run
it with the absolute path (or docker volume) `$WORKSPACE` mapped to `/smith`
inside, and an interactive bash session (the `-it` options).  The `--rm` makes
the container ephemeral. 

Our TeamCity build agent is built like so:
```
$> docker build --target=build-agent .
```


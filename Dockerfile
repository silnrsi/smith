# syntax=docker/dockerfile:1

# Download the apt lists once at the start. The RUN --mount options ensure
# the lists are shared readonly but the lockable parts aren't to permit
# maximum opportunity for parallel stages.
FROM ubuntu:24.04 AS common
USER root
ENV DEBIAN_FRONTEND='noninteractive' TZ='UTC'
COPY --link <<-EOT /etc/apt/apt.conf.d/00_no-cache
APT::Install-Recommends "0";
APT::Install-Suggests "0";
Dir::Cache::pkgcache "";
Dir::Cache::srcpkgcache "";
EOT

# Some python packages are required here (such as lxml) because they are
# required during build and force pip to use the system versions, some libs
# such as libpangoft2 are runtime dependencies of weasyprint.
FROM common AS base
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update
    apt-get install -y \
      ca-certificates \
      git \
      gpg \
      locales \
      libcairo2 \
      libpangoft2-1.0-0 \
      libwoff1 \
      python3-appdirs \
      python3-chardet \
      python3-brotli \
      python3-fs \
      python3-freetype \
      python3-gi \
      python3-icu \
      python3-idna \
      python3-lxml \
      python3-lz4 \
      python3-pkg-resources \
      python3-yaml \
      python3-requests \
      python3-jinja2 \
      python3-poetry \
      python3-full \
      libgl1 \
      ipython3 \
      apt-utils \
      python3-venv \
      jq \
      asciidoctor \
      ruby-rouge \
      flake8 \
      black \
      python3-pytest \
      wget

    apt-get remove python3-packaging python3-pip python3-setuptools python3-wheel python3-setuptools-scm -y
    wget https://bootstrap.pypa.io/get-pip.py
    python3 get-pip.py --break-system-packages
    #python3 -m pip config --global set global.use-deprecated legacy-resolver
    python3 -m pip config --global set global.break-system-packages true
    python3 -m pip config --global set global.root-user-action ignore
    python3 -m pip install --upgrade --break-system-packages --root-user-action ignore pip 
    python3 -m pip install --upgrade --break-system-packages --root-user-action ignore packaging setuptools setuptools_scm wheel typing_extensions build
    python3 -m pip --version
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
EOT

# Grab the PPAs
FROM base AS ppa
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update
    apt-get install -y gpg-agent software-properties-common ca-certificates
    add-apt-repository -y ppa:sile-typesetter/sile
    add-apt-repository -y ppa:silnrsi/smith-py3
EOT


# Set up basic build tooling environment
FROM base AS build
ENV PATH=$PATH:/root/.local/bin
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update
    apt-get upgrade -y
    apt-get install -y \
      build-essential \
      cargo \
      gcc \
      g++ \
      python3-dev \
      cmake \
      make \
      automake \
      gcovr \
      gobject-introspection \
      libcairo2-dev \
      libbrotli-dev \
      libfreetype-dev \
      libglib2.0-dev \
      libgirepository1.0-dev \
      libicu-dev \
      libjpeg-dev \
      liblz4-dev \
      libpython3-dev \
      libtool \
      libwoff-dev \
      libssl-dev \
      mono-mcs \
      pkg-config \
      ragel \
      meson \
      ninja-build
EOT


# Build Glyph layout engines
FROM build AS engines-src
WORKDIR /src/graphite
RUN <<EOT
    git clone --depth 1 https://github.com/silnrsi/graphite.git .
    cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Release \
      -DGRAPHITE2_COMPARE_RENDERER:BOOL=OFF \
      -DGRAPHITE2_NTRACING:BOOL=OFF
    cmake --build build
    cmake --install build
    python3 -m pip install --compile .
EOT
WORKDIR /src/harfbuzz
RUN <<EOT
    git clone https://github.com/harfbuzz/harfbuzz.git .
    meson setup build \
        --buildtype=release \
        --auto-features=enabled \
        --wrap-mode=nodownload \
        -Dchafa=disabled \
        -Dexperimental_api=true \
        -Dgraphite2=enabled \
        -Dgobject=disabled \
        -Dintrospection=disabled \
        -Dtests=disabled \
        -Ddocs=disabled
    meson compile -C build
    ninja -C build
    ninja -C build install
    ldconfig
EOT


# Build graphite compiler
FROM build AS grcompiler-src
WORKDIR /src/grcompiler
RUN <<EOT
    git clone --depth 1 https://github.com/silnrsi/grcompiler.git .
    cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build
    cmake --install build
EOT


# Build OTS Sanitizer
FROM build AS ots-src
WORKDIR /src/ots
RUN <<EOT
    git clone --depth 1 --recurse-submodules https://github.com/khaledhosny/ots.git .
    python3 -m pip install --upgrade ninja
    python3 -m pip install --upgrade meson
    meson build --buildtype=release
    ninja -C build
    ninja -C build install
EOT


# Install sile and fontprooof as a "rock"
FROM build AS fontproof-src
WORKDIR /src/fontproof
COPY --from=ppa /etc/apt/ /etc/apt/
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update
    apt-get install lua5.1 liblua5.1-dev -y
    apt-get install luajit -y
    apt-get install luarocks -y
    luarocks config lua_version 5.1
    luarocks config lua_interpreter luajit 
    luarocks install fontproof
EOT

# Python components
FROM build AS smith-tooling
WORKDIR /src/smith
COPY --link docker/*requirements.txt docker/*constraints.txt docker/
#RUN python3 -m pip install --use-pep517 -r docker/smith-requirements.txt
RUN pip install uv pipx
RUN uv pip install --system --break-system-packages -U -r docker/smith-requirements.txt
COPY --link . ./
#RUN python3 -m pip install .
RUN uv pip install --system --break-system-packages .


FROM base AS runtime
LABEL org.opencontainers.image.authors="tim_eves@sil.org, nicolas_spalinger@sil.org" \
      org.opencontainers.image.title="smith" \
      org.opencontainers.image.documentation="https://silnrsi.github.io/smith/" \
      org.opencontainers.image.description="Smith font development toolchain" \
      org.opencontainers.image.source="https://github.com/silnrsi/smith" \
      org.opencontainers.image.vendor="SIL Global"
COPY --from=ppa /etc/apt/ /etc/apt/
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update
    apt-get install -y \
      fonts-roboto \
      libfont-ttf-scripts-perl \
      libjson-perl \
      pandoc \
      sile \
      texlive-xetex \
      ttfautohint libqt5gui5-gles \
      wamerican \
      wbritish \
      xsltproc \
      xz-utils \
      dialog \
      libaa-bin
    paperconfig --paper a4
EOT
ARG robotomono_src=https://raw.githubusercontent.com/googlefonts/RobotoMono/main/fonts/ttf
ADD --link \
    ${robotomono_src}/RobotoMono-Regular.ttf \
    ${robotomono_src}/RobotoMono-Italic.ttf \
    ${robotomono_src}/RobotoMono-Bold.ttf   ${robotomono_src}/RobotoMono-BoldItalic.ttf \
    ${robotomono_src}/RobotoMono-Light.ttf  ${robotomono_src}/RobotoMono-LightItalic.ttf \
    ${robotomono_src}/RobotoMono-Medium.ttf ${robotomono_src}/RobotoMono-MediumItalic.ttf \
    ${robotomono_src}/RobotoMono-Thin.ttf   ${robotomono_src}/RobotoMono-ThinItalic.ttf \
    /usr/local/share/fonts/robotomono/
COPY --link --from=fontproof-src /usr/local /usr/local
COPY --link --from=ots-src /usr/local /usr/local
COPY --link --from=grcompiler-src /usr/local /usr/local
COPY --link --from=engines-src /usr/local /usr/local
COPY --link --from=smith-tooling /usr/local /usr/local


# Install TeamCity build Agent, by extracting it from the official cloud image
FROM runtime AS build-agent-teamcity
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update
    apt-get install -y \
        openjdk-11-jre-headless
    useradd -m buildagent
EOT
USER buildagent
COPY --link --chown=buildagent:buildagent --from=jetbrains/teamcity-minimal-agent /opt/buildagent/ /opt/buildagent/
COPY --link --chown=buildagent:buildagent --from=jetbrains/teamcity-minimal-agent /run-*.sh /
VOLUME "/data/teamcity_agent/conf"
VOLUME "/opt/buildagent/work"
VOLUME "/opt/buildagent/system"
VOLUME "/opt/buildagent/temp"
VOLUME "/opt/buildagent/logs"
VOLUME "/opt/buildagent/tools"
VOLUME "/opt/buildagent/plugins"
#COPY --link --from=jetbrains/teamcity-minimal-agent /services/ /services/
ENV CONFIG_FILE=/data/teamcity_agent/conf/buildAgent.properties \
    LANG=C.UTF-8 \
    DOTNET_CLI_TELEMETRY_OPTOUT=true \
    DOTNET_SKIP_FIRST_TIME_EXPERIENCE=true \
    ASPNETCORE_URLS=http://+:80 \
    DOTNET_RUNNING_IN_CONTAINER=true \
    DOTNET_USE_POLLING_FILE_WATCHER=true \
    NUGET_XMLDOC_MODE=skip \
    GIT_SSH_VARIANT=ssh \
    DOTNET_SDK_VERSION=
CMD ["/run-services.sh"]


# Add in some user facing tools for interactive use.
FROM runtime AS interactive
ENV BUILDER_UID=
ENV BUILDER_GID=
COPY --link --chmod=750 docker/interactive-entrypoint.sh /entrypoint.sh
COPY --link bash_completion_smith /etc/bash_completion.d/smith
COPY --link docker/profile-extra-utilities-smith.sh /etc/profile.d/profile-extra-utilities-smith.sh
COPY --link docker/fix-git-execute-bits-scripts /usr/local/bin/fix-git-execute-bits-scripts
COPY --link docker/dot.bashrc  /etc/skel/.bashrc
COPY --link docker/dot.gitconfig  /etc/skel/.gitconfig
COPY --link docker/fontbakery  /etc/bash_completion.d/fontbakery
RUN touch /etc/skel/.sudo_as_admin_successful
RUN touch /etc/skel/.hushlogin
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update
    apt-get install -y \
      bash-completion \
      curl \
      htop \
      less \
      nano \
      ncdu \
      perl-doc \
      sudo \
      tree \
      unzip \
      vim \
      wget \
      command-not-found
    apt-get update
    apt-get upgrade -y
    apt-get autoremove -y
    install --owner=1005 --group=users -d /smith
EOT
COPY --link <<-EOT /etc/sudoers.d/builder-nopasswd
    builder ALL=(ALL:ALL) NOPASSWD:ALL
EOT
VOLUME /smith
ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["/bin/bash"]

# syntax=docker/dockerfile:1
ARG ubuntuImage='ubuntu:20.04'

# Download the apt lists once at the start. The RUN --mount options ensure
# the lists are shared readonly but the lockable parts aren't to permit 
# maximum opportunity for parallel stages.
FROM ${ubuntuImage} AS common
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
      libmono-system-web4.0-cil \
      libmono-system-windows-forms4.0-cil \
      libwoff1 \
      mono-runtime \
      python3-appdirs \
      python3-certifi \
      python3-chardet \
      python3-brotli \
      python3-fs \
      python3-freetype \
      python3-gi \
      python3-icu \
      python3-idna \
      python3-lxml \
      python3-lz4 \
      python3-packaging \
      python3-pip \
      python3-pkg-resources \
      python3-setuptools-scm \
      python3-yaml \
      python3-requests \
      python3-venv
    python3 -m pip config --global set global.disable-pip-version-check true
    python3 -m pip config --global set global.use-deprecated legacy-resolver
    python3 -m pip install --upgrade pip setuptools setuptools_scm wheel
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
    python3 -m sysconfig | head -n 4
EOT
ENV LANG='en_US.UTF-8' DEB_PYTHON_INSTALL_LAYOUT='deb_system'


# Grab the PPAs
FROM base AS ppa
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update
    apt-get install -y gpg-agent software-properties-common ca-certificates
    apt-add-repository -ny ppa:sile-typesetter/sile
    apt-add-repository -ny ppa:silnrsi/smith-py3
EOT


# Set up basic build tooling environment
FROM base AS build
ENV PATH=$PATH:/root/.local/bin
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update
    apt-get install -y \
      build-essential \
      gcc \
      g++ \
      python3-dev \
      cmake \
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
      mono-mcs \
      ninja-build \
      pkg-config \
      ragel
    python3 -m pip install --user --compile meson
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
WORKDIR /src/harffbuzz
RUN <<EOT
    git clone --depth 1 https://github.com/harfbuzz/harfbuzz.git .
    meson build \
        --buildtype=release \
        --auto-features=enabled \
        --wrap-mode=nodownload \
        -Dchafa=disabled \
        -Dexperimental_api=true \
        -Dgraphite2=enabled \
        -Dtests=disabled \
        -Ddocs=disabled
    ninja -C build
    ninja -C build install
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
    meson build --buildtype=release 
    ninja -C build
    ninja -C build install
EOT


# "Build" fontprooof
FROM build AS fontproof-src
WORKDIR /src/fontproof
RUN <<EOT
    git clone https://github.com/sile-typesetter/fontproof.git .
    git checkout v1.6.2
    install -D -m 644 classes/* -t /usr/share/sile/classes/
    install -D -m 644 packages/* -t /usr/share/sile/packages/
EOT


# Build Font validator
FROM build AS fontval-src
WORKDIR /src/fontval
RUN <<EOT
    git clone --depth 1 https://github.com/HinTak/Font-Validator.git .
    make
    make gendoc
    install -m 755 bin/*.exe -D -t /usr/local/libexec/FontValidator
    install -m 644 bin/*.dll -D -t /usr/local/libexec/FontValidator
    install -m 644 bin/*.dll.config -D -t /usr/local/libexec/FontValidator
    install -m 644 bin/*.xsl -D -t /usr/local/libexec/FontValidator
EOT
COPY --link --chmod=755 <<-EOT /usr/local/bin/fontval
#!/bin/sh
mono /usr/local/libexec/FontValidator/FontValidator.exe -quiet -all-tables -report-in-font-dir -file "\$1"
EOT
COPY --link --chmod=755 <<-EOT /usr/local/bin/FontValidator
#!/bin/sh
mono /usr/local/libexec/FontValidator/FontValidator.exe "\$@"
EOT


# Python components
FROM build AS smith-tooling
WORKDIR /src/smith
COPY --link docker/*requirements.txt docker/*constraints.txt docker/
RUN python3 -m pip install --upgrade pip setuptools wheel setuptools_scm
RUN python3 -m pip install --compile -r docker/smith-requirements.txt
COPY --link . ./
RUN python3 -m pip install --compile . 


FROM base AS runtime
LABEL org.opencontainers.image.authors="tim_eves@sil.org, nicolas_spalinger@sil.org" \
      org.opencontainers.image.title="smith" \
      org.opencontainers.image.documentation="https://github.com/silnrsi/smith/blob/master/docs/smith/manual.asc" \
      org.opencontainers.image.description="Smith font development toolchain" \
      org.opencontainers.image.source="https://github.com/silnrsi/smith" \
      org.opencontainers.image.vendor="SIL International"
COPY --from=ppa /etc/apt/ /etc/apt/
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
<<EOT
    apt-get update 
    apt-get install -y \
      fonts-roboto \
      libfont-ttf-scripts-perl \
      libjson-perl \
      nsis \
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
COPY --link --from=fontproof-src /usr/share/sile /usr/share/sile
COPY --link --from=fontval-src /usr/local /usr/local
COPY --link --from=ots-src /usr/local /usr/local
COPY --link --from=grcompiler-src /usr/local /usr/local
COPY --link --from=engines-src /usr/local /usr/local
COPY --link --from=smith-tooling /usr/local /usr/local


# Final minimal smith font build system runtime CI systems
FROM runtime AS build-agent
# Set this back to the buildagent user when we build from a teamcity-agent as
# this will be root by this point.
RUN ldconfig
USER buildagent


# Add in some user facing tools for interactive use.
FROM runtime AS interactive
ENV BUILDER_UID=
ENV BUILDER_GID=
COPY --link --chmod=750 docker/interactive-entrypoint.sh /entrypoint.sh
COPY --link bash_completion_smith /etc/bash_completion.d/smith
COPY --link docker/profile-extra-utilities-smith.sh /etc/profile.d/profile-extra-utilities-smith.sh
COPY --link docker/fix-git-execute-bits-scripts /usr/local/bin/fix-git-execute-bits-scripts
COPY --link docker/dot.bashrc  /etc/skel/.bashrc
COPY --link docker/starship.toml  /etc/starship.toml
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
      cargo \
      wget
    git config --global pull.rebase false
    install --owner=1000 --group=users -d /smith
EOT
RUN curl -fsSL https://starship.rs/install.sh | sh -s -- -y
COPY --link <<-EOT /etc/sudoers.d/builder-nopasswd
    builder ALL=(ALL) NOPASSWD:ALL
EOT
VOLUME /smith
ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["/bin/bash"]

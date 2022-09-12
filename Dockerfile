# syntax=docker/dockerfile:1
ARG ubuntuImage='ubuntu:20.04'

# Download the apt lists once at the start. The RUN --mount options ensure
# the lists are shared readonly but the lockable parts aren't to permit 
# maximum oppourtunity for parallel stages.
FROM ${ubuntuImage} AS common
USER root
ENV DEBIAN_FRONTEND='noninteractive' TZ='UTC'
COPY --link <<-EOT /etc/apt/apt.conf.d/00_no-cache
APT::Install-Recommends "0";
APT::Install-Suggests "0";
Dir::Cache::pkgcache "";
Dir::Cache::srcpkgcache "";
EOT
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update

# Grab the PPA keys for later use.
FROM common AS ppa-keys
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt/lists,readonly \
<<EOT
    apt-get install -y dirmngr gnupg
    apt-key --keyring /ppa-archives-keyring.gpg \
      adv --keyserver keyserver.ubuntu.com \
          --recv-keys 904F67626F1CF535 5DF1CE288B1A27EA
EOT


FROM common AS base
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt/lists,readonly \
<<EOT
    apt-get install -y \
      ca-certificates \
      git \
      gpg \
      locales \
      libcairo2 \
      libmono-system-web4.0-cil \
      libmono-system-windows-forms4.0-cil \
      mono-runtime \
      python3-appdirs \
      python3-certifi \
      python3-chardet \
      python3-brotli \
      python3-cffi \
      python3-fs \
      python3-gi \
      python3-icu \
      python3-idna \
      python3-lz4 \
      python3-pip \
      python3-odf \
      python3-pkg-resources \
      python3-pyclipper \
      python3-yaml \
      python3-reportlab \
      python3-requests
    pip config set global.disable-pip-version-check true
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
EOT
ENV LANG='en_US.UTF-8'
    

# Set up basic build tooling environment
FROM base AS build
ENV PATH=$PATH:/root/.local/bin
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt/lists,readonly \
<<EOT
    apt-get install -y \
      build-essential \
      cmake \
      gcovr \
      gobject-introspection \
      gtk-doc-tools \
      libcairo2-dev \
      libfreetype-dev \
      libglib2.0-dev \
      libgirepository1.0-dev \
      libicu-dev \
      libjpeg-dev \
      libpython3-dev \
      libtool \
      mono-mcs \
      ninja-build \
      pkg-config \
      ragel
    pip install --user --compile meson
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
        -Dgraphite2=enabled
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
    git clone --depth 1 https://github.com/sile-typesetter/fontproof.git .
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
ADD . ./
RUN pip install --compile -r docker/smith-requirements.txt
RUN pip install --compile . 


FROM base AS runtime
LABEL org.opencontainers.image.authors="tim_eves@sil.org, nicolas_spaligner@sil.org" \
      org.opencontainers.image.title="smith-font" \
      org.opencontainers.image.documentation="https://github.com/silnrsi/smith/blob/master/docs/smith/manual.asc" \
      org.opencontainers.image.description="Smith font build environment" \
      org.opencontainers.image.source="https://github.com/silnrsi/smith" \
      org.opencontainers.image.vendor="SIL International"
ARG codename=focal
ADD --link docker/sources.list.d/*-${codename}.list /etc/apt/sources.list.d/
COPY --link --from=ppa-keys /ppa-archives-keyring.gpg /etc/apt/trusted.gpg.d/
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
<<EOT
    apt-get update 
    apt-get install -y \
      fontforge-nox \
      fonts-roboto \
      libfont-ttf-scripts-perl \
      libjson-perl \
      libtext-csv-perl \
      nsis \
      pandoc \
      python3-fontforge \
      sile \
      texlive-xetex \
      ttfautohint libqt5gui5-gles \
      wamerican \
      wbritish \
      xsltproc \
      xz-utils
EOT
ARG robotomono_src=https://raw.githubusercontent.com/googlefonts/RobotoMono/main/fonts/ttf
ADD --link \
    ${robotomono_src}/RobotoMono-Regular.ttf \
    ${robotomono_src}/RobotoMono-Italic.ttf \
    ${robotomono_src}/RobotoMono-Bold.ttf ${robotomono_src}/RobotoMono-BoldItalic.ttf \
    ${robotomono_src}/RobotoMono-Light.ttf ${robotomono_src}/RobotoMono-LightItalic.ttf \
    ${robotomono_src}/RobotoMono-Medium.ttf ${robotomono_src}/RobotoMono-MediumItalic.ttf \
    ${robotomono_src}/RobotoMono-Thin.ttf ${robotomono_src}/RobotoMono-ThinItalic.ttf\
    /usr/local/share/fonts/robotomono/
COPY --link --from=fontproof-src /usr/share/sile /usr/share/sile
COPY --link --from=fontval-src /usr/local /usr/local
COPY --link --from=ots-src /usr/local /usr/local
COPY --link --from=grcompiler-src /usr/local /usr/local
COPY --link --from=engines-src /usr/local /usr/local
COPY --link --from=smith-tooling /usr/local /usr/local


# Final minimal smith font build system runtime CI systems
FROM runtime AS build-agent


# Add in some user facing tools for interactive use.
FROM runtime AS interactive
USER root
ENV BUILDER=1000
COPY --link --chmod=750 docker/interactive-entrypoint.sh /entrypoint.sh
COPY --link bash_completion_smith /etc/bash_completion.d/smith
RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt,sharing=private \
    --mount=type=cache,target=/var/lib/apt/lists,readonly \
<<EOT
    apt-get install -y bash-completion less nano ncdu sudo libaa-bin
EOT
COPY --link <<-EOT /etc/sudoers.d/builder-nopasswd
    builder ALL=(ALL) NOPASSWD:ALL
EOT
WORKDIR /build
VOLUME /build
ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["/bin/bash"]

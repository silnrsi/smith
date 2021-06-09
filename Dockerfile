# Set up basic runtime environment
ARG ubuntuImage='ubuntu:20.04'
ARG type=build-agent

FROM ${ubuntuImage} AS base
USER root
ENV DEBIAN_FRONTEND='noninteractive' TZ='UTC'
COPY docker/no-cache  /etc/apt/apt.conf.d/00_no-cache
RUN apt-get update && apt-get install -y \
      ca-certificates \
      git \
      gpg \
      locales \
      libcairo2 \
      libfreetype6 \
      libglib2.0-0 \
      libgirepository-1.0-1 \
      libicu66 \
      libmono-system-web4.0-cil \
      libmono-system-windows-forms4.0-cil \
      mono-runtime \
      python3-brotli \
      python3-fs \
      python3-gi \
      python3-icu \
      python3-lz4 \
      python3-odf \
      python3-pkg-resources \
      python3-reportlab \
      python3-scipy \
      && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG='en_US.UTF-8'
    

# Set up basic build tooling environment
FROM base AS build
ENV PATH=$PATH:/root/.local/bin
RUN apt-get install -y \
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
      libpython3-dev \
      libtool \
      mono-mcs \
      ninja-build \
      python3-pip \
      pkg-config \
      ragel \
      &&\
    pip install --user meson


# Grab the PPA keys for later use.
FROM ${ubuntuImage} AS ppa-keys
USER root
RUN apt-get update && apt-get install -y dirmngr gnupg &&\
    apt-key \
        --keyring /ppa-archives-keyring.gpg \
      adv \
        --keyserver keyserver.ubuntu.com \
        --recv-keys 904F67626F1CF535 5DF1CE288B1A27EA


# Build Glyph layout engines
FROM build AS engines-src
WORKDIR /src/graphite
RUN git clone --depth 1 https://github.com/silnrsi/graphite.git . &&\
    cmake -G Ninja -B build \
      -DGRAPHITE2_COMPARE_RENDERER:BOOL=OFF \
      -DGRAPHITE2_NTRACING:BOOL=OFF \
      &&\
    cmake --build build && cmake --install build;
WORKDIR /src/harffbuzz
RUN git clone --depth 1 https://github.com/harfbuzz/harfbuzz.git . &&\
    meson build \
        --buildtype=debugoptimized \
        --auto-features=enabled \
        --wrap-mode=nodownload \
        -Db_coverage=true \
        -Dchafa=disabled \
        -Dexperimental_api=true\
        -Dgraphite=enabled \
        &&\
    ninja -C build && ninja install -C build;


# Build graphite compiler
FROM build AS grcompiler-src
WORKDIR /src/grcompiler
RUN git clone --depth 1 https://github.com/silnrsi/grcompiler.git . &&\
    cmake -G Ninja -B build && cmake --build build && cmake --install build;


# Build OTS Sanitizer
FROM build AS ots-src
WORKDIR /src/ots
RUN pip install 'git+https://github.com/googlefonts/ots-python.git@main#egg=opentype-sanitizer' &&\
    git clone --depth 1 --recurse-submodules https://github.com/khaledhosny/ots.git . &&\
    meson build && ninja -C build && ninja install -C build


# Build Font validator
FROM build AS fontval
WORKDIR /src/fontval
RUN git clone --depth 1 https://github.com/HinTak/Font-Validator.git . &&\
    make && make gendoc &&\
    cp bin/*.exe bin/*.dll* bin/*.xsl /usr/local/bin


# Python components
FROM build AS python3-dependencies
RUN pip install \
      'git+https://github.com/googlei18n/compreffor' \
      'git+https://github.com/googlefonts/fontbakery' \
      'git+https://github.com/fonttools/fonttools' \
      'git+https://github.com/googlefonts/GlyphsLib' \
      'git+https://github.com/rosettatype/hyperglot' \
      'git+https://github.com/googlefonts/pyfontaine' \
      'git+https://github.com/silnrsi/palaso-python' \
      'git+https://github.com/LettError/MutatorMath' \
      'git+https://github.com/silnrsi/pysilfont' \
      'git+https://github.com/googlei18n/ufo2ft'
WORKDIR smith
COPY . ./
RUN pip install . 


# Final minimal smith font build system runtime CI systems
FROM base AS build-agent
ARG codename=focal
LABEL org.opencontainers.image.authors="tim_eves@sil.org, nicolas_spaligner@sil.org" \
      org.opencontainers.image.title="smith-font" \
      org.opencontainers.image.documentation="https://github.com/silnrsi/smith/blob/master/docs/smith/manual.asc" \
      org.opencontainers.image.description="Smith font build environment" \
      org.opencontainers.image.source="https://github.com/silnrsi/smith" \
      org.opencontainers.image.vendor="SIL International"
COPY docker/sources.list.d/*-${codename}.list /etc/apt/sources.list.d/
COPY --from=ppa-keys /ppa-archives-keyring.gpg /etc/apt/trusted.gpg.d/
RUN apt-get update && apt-get install -y \
      fontforge-nox \
      libaa-bin \
      libfont-ttf-scripts-perl \
      libqt5gui5-gles \
      libjson-perl \
      libtext-csv-perl \
      nsis \
      pandoc \
      python3-fontforge \
      sile \
      texlive-xetex \
      ttfautohint \
      wamerican \
      wbritish \
      xsltproc \
      xz-utils \
      &&\
    sile -e 'installPackage("fontproof");os.exit()'
COPY docker/validator-shims /usr/local/bin/
COPY --from=fontval /usr/local /usr/local
COPY --from=grcompiler-src /usr/local /usr/local
COPY --from=ots-src /usr/local /usr/local
COPY --from=python3-dependencies /usr/local /usr/local
COPY --from=engines-src /usr/local /usr/local


# Add in some user facing tools for interactive use.
FROM build-agent AS interactive
COPY bash_completion_smith /etc/bash_completion.d/
RUN apt-get update && apt-get install -y bash-completion less nano ncdu sudo &&\
    useradd -md /build builder &&\
    echo 'builder ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers
VOLUME /build
USER builder
CMD ["/bin/bash"]


# Final clean up regardless of which type was chosen.
FROM ${type} AS final
ARG codename=focal
LABEL org.opencontainers.image.authors="tim_eves@sil.org, nicolas_spaligner@sil.org" \
      org.opencontainers.image.title="smith-font" \
      org.opencontainers.image.documentation="https://github.com/silnrsi/smith/blob/master/docs/smith/manual.asc" \
      org.opencontainers.image.description="Smith font build environment" \
      org.opencontainers.image.source="https://github.com/silnrsi/smith" \
      org.opencontainers.image.vendor="SIL International"
RUN apt-get autoremove --purge &&\
    rm /var/lib/apt/lists/* /var/lib/apt/lists/partial/*; true 


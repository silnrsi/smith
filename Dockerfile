# Set up basic runtime environment
ARG ubuntuImage='ubuntu:20.04'

FROM ${ubuntuImage} AS common
USER root
ENV DEBIAN_FRONTEND='noninteractive' TZ='UTC'
COPY docker/no-cache  /etc/apt/apt.conf.d/00_no-cache
RUN apt-get update

# Grab the PPA keys for later use.
FROM common AS ppa-keys
USER root
RUN apt-get install -y dirmngr gnupg &&\
    apt-key \
        --keyring /ppa-archives-keyring.gpg \
      adv \
        --keyserver keyserver.ubuntu.com \
        --recv-keys 904F67626F1CF535 5DF1CE288B1A27EA


FROM common AS base
USER root
ENV DEBIAN_FRONTEND='noninteractive' TZ='UTC'
COPY docker/no-cache  /etc/apt/apt.conf.d/00_no-cache
RUN apt-get install -y \
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
      python3-odf \
      python3-pkg-resources \
      python3-pyclipper \
      python3-yaml \
      python3-reportlab \
      python3-requests \
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
    pip install --user --compile meson


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
    ninja -C build && ninja -C build install;


# Build graphite compiler
FROM build AS grcompiler-src
WORKDIR /src/grcompiler
RUN git clone --depth 1 https://github.com/silnrsi/grcompiler.git . &&\
    cmake -G Ninja -B build && cmake --build build && cmake --install build;


# Build OTS Sanitizer
FROM build AS ots-src
WORKDIR /src/ots
RUN git clone --depth 1 --recurse-submodules https://github.com/khaledhosny/ots.git . &&\
    meson build && ninja -C build && ninja -C build install


# Build Font validator
FROM build AS fontval-src
WORKDIR /src/fontval
ADD docker/validator-shims /usr/local/bin/
RUN git clone --depth 1 https://github.com/HinTak/Font-Validator.git . &&\
    make && make gendoc &&\
    cp bin/*.exe bin/*.dll* bin/*.xsl /usr/local/bin


# Python components
FROM build AS smith-tooling
WORKDIR /src/smith
ADD . ./
RUN pip install --compile -r docker/smith-requirements.txt
RUN pip install . 


FROM base AS runtime
LABEL org.opencontainers.image.authors="tim_eves@sil.org, nicolas_spaligner@sil.org" \
      org.opencontainers.image.title="smith-font" \
      org.opencontainers.image.documentation="https://github.com/silnrsi/smith/blob/master/docs/smith/manual.asc" \
      org.opencontainers.image.description="Smith font build environment" \
      org.opencontainers.image.source="https://github.com/silnrsi/smith" \
      org.opencontainers.image.vendor="SIL International"
ARG codename=focal
ADD docker/sources.list.d/*-${codename}.list /etc/apt/sources.list.d/
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
      texlive-xetex \
      ttfautohint \
      wamerican \
      wbritish \
      xsltproc \
      xz-utils
RUN apt-get install -y sile &&\
    sile -e 'installPackage("fontproof");os.exit()'
COPY --from=fontval-src /usr/local /usr/local
COPY --from=ots-src /usr/local /usr/local
COPY --from=grcompiler-src /usr/local /usr/local
COPY --from=engines-src /usr/local /usr/local
COPY --from=smith-tooling /usr/local /usr/local


# Final minimal smith font build system runtime CI systems
FROM runtime AS build-agent
RUN apt-get autoremove --purge &&\
    rm /var/lib/apt/lists/* /var/lib/apt/lists/partial/*; true


# Add in some user facing tools for interactive use.
FROM runtime AS interactive
ADD bash_completion_smith /etc/bash_completion.d/smith
RUN apt-get install -y bash-completion less nano ncdu sudo &&\
    useradd -m builder &&\
    echo 'builder ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers &&\
    apt-get autoremove --purge &&\
    rm /var/lib/apt/lists/* /var/lib/apt/lists/partial/*; true
WORKDIR /build
VOLUME /build
USER builder
CMD ["/bin/bash"]

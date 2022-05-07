#syntax=docker/dockerfile:1.2
# Set up basic runtime environment
ARG ubuntuImage='ubuntu:22.04'
ARG type=build-agent
ARG DOCKER_HUB_CACHE=0

FROM ${ubuntuImage} AS base
USER root
ENV PATH=$PATH:root/.local/bin
ENV DEBIAN_FRONTEND='noninteractive' TZ='UTC'
RUN apt-get update && apt-get install -y \
      ca-certificates \
      git \
      python3-software-properties \ 
      software-properties-common \
      libterm-readline-gnu-perl \
      apt-utils \
      gpg \
      locales \
      libcairo2 \
      libfreetype6 \
      libglib2.0-0 \
      libgirepository-1.0-1 \
      libicu70 \
      && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG='en_US.UTF-8'
    

# Set up basic build tooling environment
FROM base AS build
ENV PATH=$PATH:$HOME/.local/bin
RUN apt-get install -y \
      sudo \
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
      ninja-build \
      python3-pip \
      pkg-config \
      dirmngr \
      gnupg \
      gpg-agent \
      ragel
RUN sudo pip install meson 
RUN sudo pip install ninja
RUN sudo apt-get update && apt-get upgrade -y && apt-get install -y python3-pip software-properties-common python3-software-properties bash-completion less nano vim-nox ncdu tree wget curl ntpdate unzip sudo 

# Build Glyph layout engines
FROM build AS engines-src
WORKDIR /src/graphite
RUN git clone --depth 1 https://github.com/silnrsi/graphite.git . &&\
    cmake -G Ninja -B build \
      -DGRAPHITE2_COMPARE_RENDERER:BOOL=OFF \
      -DGRAPHITE2_NTRACING:BOOL=OFF \
      &&\
    cmake --build build && cmake --install build &&\
    python3 setup.py -v install;
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


# Python smith components
FROM build AS python3-dependencies
RUN pip install \
      'git+https://github.com/googlefonts/fontbakery' \
      'git+https://github.com/fonttools/fonttools' \
      'git+https://github.com/googlefonts/pyfontaine' \
      'git+https://github.com/silnrsi/palaso-python' \
      'git+https://github.com/LettError/MutatorMath' \
      'git+https://github.com/googlei18n/ufo2ft' \
      'git+https://github.com/python-lz4/python-lz4' \
      'git+https://github.com/googlefonts/cu2qu' \
      'git+https://github.com/robotools/defcon' \
      'git+https://github.com/typemytype/booleanOperations'  \
      'git+https://github.com/robotools/fontMath' \
      'git+https://github.com/fonttools/ufoLib2' \
      'git+https://github.com/google/brotli' \
      'git+https://github.com/googlefonts/GlyphsLib' \
      'git+https://github.com/typemytype/glyphConstruction' \
      'git+https://github.com/eea/odfpy' \
      'git+https://github.com/robotools/fontParts' \
      'git+https://gitlab.pyicu.org/main/pyicu' \
      'git+https://github.com/scikit-learn/scikit-learn'  
RUN pip install tabulate freetype-py pytz 
RUN pip install 'git+https://github.com/silnrsi/smith' 
RUN pip install 'git+https://github.com/silnrsi/pysilfont'


# Final minimal smith font build system runtime CI systems
FROM base AS build-agent
ARG codename=jammy
LABEL org.opencontainers.image.authors="tim_eves@sil.org, nicolas_spalinger@sil.org" \
      org.opencontainers.image.title="smith-jammy" \
      org.opencontainers.image.documentation="https://github.com/silnrsi/smith/blob/master/docs/smith/manual.asc" \
      org.opencontainers.image.description="Smith font development toolchain" \
      org.opencontainers.image.source="https://github.com/silnrsi/smith" \
      org.opencontainers.image.vendor="SIL International"
RUN add-apt-repository -s -y ppa:silnrsi/smith-py3
RUN add-apt-repository -s -y ppa:sile-typesetter/sile 
RUN apt-get update && apt-get install --no-install-recommends -y \
      libaa-bin \
      libfont-ttf-scripts-perl \
      libjson-perl \
      libtext-csv-perl \
      pandoc \
      sile \
      texlive-xetex \
      ttfautohint \
      wamerican \
      wbritish \
      xsltproc \
      xz-utils \
      python3-pip
RUN apt-get install sile -y 
RUN sile -e 'installPackage("fontproof");os.exit()'
RUN pip install weasyprint pillow 
RUN apt-get install gir1.2-pango-1.0 -y 
COPY --from=engines-src /usr/local /usr/local 
COPY --from=grcompiler-src /usr/local /usr/local
COPY --from=ots-src /usr/local /usr/local
COPY --from=python3-dependencies /usr/local /usr/local


# Add in some user facing tools for interactive use.
FROM build-agent AS interactive
RUN apt-get update && apt-get upgrade -y && apt-get install -y bash-completion less nano vim-nox ncdu tree wget curl ntpdate unzip sudo &&\
    useradd -md /build builder  &&\
    useradd -md /home/ubuntu ubuntu &&\
    echo 'builder ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers &&\ 
    echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers
RUN wget --quiet --no-directories --no-parent --continue  https://raw.githubusercontent.com/silnrsi/smith/master/bash_completion_smith -O /etc/bash_completion.d/smith
VOLUME /build
USER ubuntu
CMD ["/bin/bash"]
COPY --from=engines-src --chown=ubuntu:ubuntu /usr/local /usr/local 
COPY --from=grcompiler-src /usr/local /usr/local
COPY --from=ots-src /usr/local /usr/local
COPY --from=python3-dependencies /usr/local /usr/local


# Final clean up regardless of which type was chosen.
FROM ${type} AS final
ARG codename=jammy
LABEL org.opencontainers.image.authors="tim_eves@sil.org, nicolas_spalinger@sil.org" \
      org.opencontainers.image.title="smith-jammy" \
      org.opencontainers.image.documentation="https://github.com/silnrsi/smith/blob/master/docs/smith/manual.asc" \
      org.opencontainers.image.description="Smith font development environment" \
      org.opencontainers.image.source="https://github.com/silnrsi/smith" \
      org.opencontainers.image.vendor="SIL International"
USER root
RUN apt-get autoremove --purge &&\
    rm -rf /var/lib/apt/lists/* /var/lib/apt/lists/partial/*; true 


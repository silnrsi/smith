#!/usr/bin/env bash
# A provisioning script for Vagrant to make it easier to get the latest smith and its dependencies from the PPAs and/or source.
# This is designed to be called by the Vagrantfile wich expects this file to be in the same directory by default.

# This is for Ubuntu xenial/16.04 LTS

# configure things for non-interactive and sdtin
ex +"%s@DPkg@//DPkg" -cwq /etc/apt/apt.conf.d/70debconf
dpkg-reconfigure debconf -f noninteractive -p critical


echo " "
echo " "
echo "Installing smith and its dependencies"
echo " "
echo " "


# the official smith PPA
add-apt-repository -s -y ppa:silnrsi/smith

# the official fontforge PPA
add-apt-repository -s -y ppa:fontforge/fontforge

# the TexLive 2018 backports PPA
add-apt-repository -s -y ppa:jonathonf/texlive-2018

# the current git PPA
add-apt-repository -s -y ppa:git-core/ppa

apt-get update -y -q
apt-get upgrade -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-overwrite" -u -V --with-new-pkgs

# toolchain components currently built from source
# these are now commented out as the corresponding items are available as packages or on the CI
# if you need certain features you can uncomment them and reprovision. 


# checking if we already have local checkouts 
# if [ -d /usr/local/builds/ ]
# then
#     echo " "
#     echo "You already have previous builds, it's easier to delete them and start afresh. "
#     echo " "
#     echo "Deleting /usr/local/builds... "
#     echo " "
#     rm -rf /usr/local/builds
# fi
# 
# mkdir -p /usr/local/builds
# 
# chmod -R 766 /usr/local/builds 
# 
# # graphite
# echo " "
# echo " "
# echo "Installing graphite from source"
# echo " "
# echo " "
# 
# apt-get install --no-install-recommends asciidoc autotools-dev bsdmainutils build-essential cmake cmake-data cpp cpp-5 debhelper dh-exec dh-strip-nondeterminism docbook-xml docbook-xsl doxygen dpkg-dev fontconfig fontconfig-config fonts-dejavu-core g++ gcc gettext graphviz groff-base intltool-debian libarchive-zip-perl libarchive13 libasan2 libatomic1 libavahi-client3 libavahi-common-data libavahi-common3 libblas-common libblas3 libc-dev-bin libc6-dev libcairo2 libcc1-0 libcdt5 libcgraph6 libcilkrts5 libclang1-3.6 libcroco3 libcups2 libcupsfilters1 libcupsimage2 libcurl3 libdatrie1 libfile-stripnondeterminism-perl libfontconfig1 libgcc-5-dev libgd3 libgfortran3 libgomp1 libgs9 libgs9-common libgvc6 libgvpr2 libice6 libijs-0.35 libisl15 libitm1 libjbig0 libjbig2dec0 libjpeg-turbo8 libjpeg8 libjsoncpp1 libkpathsea6 liblapack3 liblcms2-2 libllvm3.6v5 liblsan0 libltdl7 libmpc3 libmpx0 libobjc-5-dev libobjc4 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 libpaper-utils libpaper1 libpathplan4 libpipeline1 libpixman-1-0 libpoppler58 libpotrace0 libptexenc1 libquadmath0 libsm6 libstdc++-5-dev libsynctex1 libtexlua52 libtexluajit2 libthai-data libthai0 libtiff5 libtimedate-perl libtsan0 libubsan0 libunistring0 libvpx3 libx11-6 libx11-data libxau6 libxaw7 libxcb-render0 libxcb-shm0 libxcb1 libxdmcp6 libxext6 libxi6 libxml2-utils libxmu6 libxpm4 libxrender1 libxslt1.1 libxt6 libzzip-0-13 linux-libc-dev make man-db po-debconf poppler-data python-apt python-numpy sgml-data t1utils x11-common xdg-utils xsltproc libfreetype6-dev libfreetype6 texlive-xetex texlive-latex-extra -y -q
# 
# cd /usr/local/builds
# git clone --depth 1 https://github.com/silnrsi/graphite.git
# cd graphite
# mkdir build
# cd build
# cmake -G "Unix Makefiles" --build .. -DGRAPHITE2_COMPARE_RENDERER:BOOL=OFF
# make
# make install
# ldconfig 
# 
# 
# echo " "
# echo " "
# echo "Installing Graphite-enabled HarfBuzz from source (with introspection)"
# echo " "
# apt-get install --no-install-recommends build-essential cmake gcc g++ libfreetype6-dev libglib2.0-dev libcairo2-dev automake libtool pkg-config ragel gtk-doc-tools -y -q
# apt-get install --no-install-recommends libgirepository1.0-dev python-gi -y -q
# cd /usr/local/builds
# git clone --depth 1 https://github.com/harfbuzz/harfbuzz.git
# cd harfbuzz
# ./autogen.sh --with-graphite2 --with-gobject --enable-introspection --with-ucdn=no
# make
# make install
# cp ./src/*.typelib /usr/lib/`uname -i`-linux-gnu/girepository-1.0/
# ldconfig 
# 
# 
# # ots
# echo " "
# echo " "
# echo "Installing ots from source"
# echo " "
# echo " "
# apt-get install build-essential autoconf automake pkg-config zlib1g-dev -y -q
# cd /usr/local/builds
# git clone --depth 1 --recursive https://github.com/khaledhosny/ots.git
# cd ots
# ./autogen.sh
# ./configure --enable-debug --enable-graphite
# make
# make install 
# 
# # fontvalidator
# echo " "
# echo " "
# echo "Installing fontvalidator from source"
# echo " "
# echo " "
# apt-get install mono-mcs libmono-corlib4.5-cil libmono-system-windows-forms4.0-cil libmono-system-web4.0-cil xsltproc xdg-utils -y -q 
# cd /usr/local/builds
# git clone --depth 1 https://github.com/HinTak/Font-Validator.git fontval
# cd fontval
# make
# make gendoc
# cp bin/*.exe /usr/local/bin/
# cp bin/*.dll* /usr/local/bin/
# cp bin/*.xsl /usr/local/bin/
# 
# FontValidator shell script
# echo " "
# echo " "
# echo "Installing fontval script"
# echo " "
# echo " "
# cat > /usr/local/bin/fontval <<'EOF'
# #!/bin/bash
# 
# # running the validator from the usr/local/bin directory  
# mono /usr/local/bin/FontValidator.exe -quiet -all-tables -report-in-font-dir -file "$1" 
# 
# exit 0 
# 
# EOF
# 
# chmod 755 /usr/local/bin/fontval 


# toolchain components installed from packages (both main repositories and PPAs)

# sile and fontproof
apt-get install sile -y -q

# python-odf for ftml2odt
apt-get install python-odf python-odf-tools -y -q

# Project-specific extras:
apt-get install libjson-perl libtext-csv-perl -y -q
apt-get install libharfbuzz-bin  -y -q


# smith itself  (only the font side of things)
echo " "
echo " "
echo "Installing smith (downloading/updating the dependencies might take a few minutes)"
echo " "
echo " "

apt-get install smith-font --no-install-recommends -y -q

# smith options
# target specific version for (or downgrade) glyphsLib
apt-get install python-glyphslib=2.4.0-1ubuntu1 -y -q

# target specific version for (or downgrade) defcon
apt-get install python-defcon=0.3.4-1+git-snapshot-0~201806292301~ubuntu16.04.1 -y -q

echo " "
echo " "
echo "Done!"
echo " "
echo " "
echo "smith is now ready to use:"
echo " "
echo "Smith version: "
apt-cache show smith | grep Version: | grep snapshot
echo " "
echo " "

echo "To go to the shared folder to run smith commands on your project(s), type:" 
echo " "
echo "vagrant ssh"
echo "cd /smith"
echo "cd <folder of my project(s)>"
echo "smith distclean"
echo "smith configure"
echo "smith build"
echo "smith alltests"
echo "smith zip"
echo "smith tarball"
echo "smith release"
echo "for more details type: man smith"
echo "or refer to the smith manual on https://github.com/silnrsi/smith/tree/master/docs/smith"
echo "or in /usr/share/doc/smith-common/"
echo " "



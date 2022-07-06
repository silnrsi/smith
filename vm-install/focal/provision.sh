#!/usr/bin/env bash

# A provisioning script for Vagrant to make it easier to get the latest smith and its dependencies from the PPAs and/or source.
# This is designed to be called by the Vagrantfile which expects this file to be in the same directory by default.

# This is for Ubuntu focal/20.04 LTS

# configure things for non-interactive and sdtin
ex +"%s@DPkg@//DPkg" -cwq /etc/apt/apt.conf.d/70debconf
dpkg-reconfigure debconf -f noninteractive -p critical

# debugging 
# set -x	


echo " "
echo " "
echo "Installing smith and its dependencies"
echo " "
echo " "

#
# Configuration options:
#

# set to True to compile Graphite and harfbuzz from source (including tracing):
# graphiteFromSource=True
graphiteFromSource=False

# set to True to compile opentype-sanitiser/ots from source
 otsFromSource=True
#otsFromSource=False

# set to True to include the sklearn module (for Harmattan)
#includeSklearn=True
includeSklearn=False

# to pin particular version of fontTools, set that version number here, else set to empty
#fontToolsHoldVersion=4.17.1
 fontToolsHoldVersion=

# End of configuration options


# the official smith PPA
add-apt-repository -s -y ppa:silnrsi/smith-py3

# the current git PPA
add-apt-repository -s -y ppa:git-core/ppa

# set git params in ~/.gitconfig
git config --global pull.rebase false


# the official SILE PPA
add-apt-repository -s -y ppa:sile-typesetter/sile


apt-get update -y -q
apt-get upgrade -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-overwrite" -u -V --with-new-pkgs

# toolchain components currently built from source or retrieved via pypi
# most of these are now commented out as the corresponding items are available as packages or on the CI
# according to the features you need you can fill in the variables above or comment/uncomment accordingly before reprovisionning


# install pip3 
apt-get install python3-pip -y 
python3 -m pip install --upgrade pip

# config
python3 -m pip config set global.disable-pip-version-check true

# generic toolchain
apt-get install build-essential cmake gcc g++ automake libtool pkg-config icu-devtools libicu-dev  -y -q


# checking if we already have local checkouts 
 if [ -d /home/vagrant/srcbuilds ]
then
    echo " "
    echo "You already have previous builds, it's easier to delete them and start afresh. "
    echo " "
    echo "Deleting srcbuilds folder... "
    echo " "
    rm -rf /home/vagrant/srcbuilds
fi

mkdir -p /home/vagrant/srcbuilds




# Graphite and Harfbuzz

if [ "$graphiteFromSource" == "True" ]; then
	echo " "
	echo " "
	echo "Installing Graphite from source"
	echo " "
	echo " "


	apt-get install build-essential cmake gcc g++ automake libtool pkg-config -y -q
	cd /home/vagrant/srcbuilds
	git clone --depth 1 https://github.com/silnrsi/graphite.git
	cd graphite
	mkdir build
	cd build
	cmake -G "Unix Makefiles" --build .. -DGRAPHITE2_COMPARE_RENDERER:BOOL=OFF -DGRAPHITE2_NTRACING:BOOL=OFF
	make
	make install
	ldconfig 

	echo " "
	echo " "
	echo "Installing Graphite-enabled HarfBuzz from source"
	echo " "
	apt-get install pkg-config gcc ragel gcovr gtk-doc-tools libfreetype6-dev libglib2.0-dev libcairo2-dev libicu-dev libgraphite2-dev python3-setuptools gobject-introspection libgirepository1.0-dev -y -q
	cd /home/vagrant/srcbuilds
	git clone --depth 1 https://github.com/harfbuzz/harfbuzz.git
	cd harfbuzz

	python3 -m pip install --upgrade git+https://github.com/mesonbuild/meson.git@master#egg=meson ninja
	meson build -Db_coverage=true --auto-features=enabled -Dgraphite=enabled  --buildtype=debugoptimized --wrap-mode=nodownload -Dexperimental_api=true -Dchafa=disabled 
	ninja -C build
	ninja install -C build
	ldconfig 
fi

# ots 
if [ "$otsFromSource" == "True" ];
then
	python3 -m pip install --upgrade git+https://github.com/googlefonts/ots-python.git@main#egg=opentype-sanitizer

	# ots from main repo (debugging and graphite support on by default)
	python3 -m pip install --upgrade meson ninja
	apt-get install libfreetype6-dev -y -q
	cd /home/vagrant/srcbuilds
	git clone --depth 1 --recurse-submodules https://github.com/khaledhosny/ots.git
	cd ots
	meson build
	ninja -C build
	ninja install -C build

else
	python3 -m pip install --upgrade opentype-sanitizer 
fi

# entry script to find the wheel binary placed in
# /usr/local/lib/python3.6/dist-packages/ots/

cat > /usr/local/bin/ots-sanitize <<'EOF'
#!/usr/bin/python3
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import sys
import ots


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    return ots.sanitize(*args).returncode


if __name__ == "__main__":
    sys.exit(main())
EOF

chmod 755 /usr/local/bin/ots-sanitize

# fontvalidator
echo " "
echo " "
echo "Installing fontvalidator from source"
echo " "
echo " "
apt-get install mono-mcs libmono-corlib4.5-cil libmono-system-windows-forms4.0-cil libmono-system-web4.0-cil xsltproc xdg-utils -y -q 
cd /home/vagrant/srcbuilds
git clone --depth 1 https://github.com/HinTak/Font-Validator.git fontval
cd fontval
make
make gendoc
cp bin/*.exe /usr/local/bin/
cp bin/*.dll* /usr/local/bin/
cp bin/*.xsl /usr/local/bin/

# FontValidator shell script
echo " "
echo " "
echo "Installing fontval scripts"
echo " "
echo " "
cat > /usr/local/bin/fontval <<'EOF'
#!/bin/bash

# running the validator from the usr/local/bin directory  
mono /usr/local/bin/FontValidator.exe -quiet -all-tables -report-in-font-dir -file "$1" 

exit 0 

EOF

chmod 755 /usr/local/bin/fontval 

cat > /usr/local/bin/FontValidator <<'EOF'
#!/bin/bash

# running the validator from the usr/local/bin directory  
mono /usr/local/bin/FontValidator.exe "$@" 

exit 0 

EOF

chmod 755 /usr/local/bin/FontValidator 


# toolchain components installed from packages (both main repositories and PPAs)

if [ "$graphiteFromSource" == "False" ]
then
	 apt-get install libharfbuzz-bin -y -q
fi

if [ "$includeSklearn" == "True" ]
then
	# clustering tool needed for collision-avoidance-based kerning:
	apt-get install python3-sklearn -y
fi


# smith options
if [ "$fontToolsHoldVersion" == "" ]
then
	# current fonttools
	apt-mark unhold python3-fonttools
	python3 -m pip uninstall fontTools --yes 
	apt-get install --reinstall python3-fonttools -y 
else
	# target specific version for (or downgrade) fonttools
	dpkg --remove --force-depends python3-fonttools
	apt-mark hold python3-fonttools
	python3 -m pip uninstall fontTools --yes 
	python3 -m pip install --upgrade fontTools==$fontToolsHoldVersion
fi

# crude chown because Harfbuzz wants write-access to optimize runs of its utilities
chmod -R 776 /home/vagrant/srcbuilds
chown -R vagrant:vagrant /home/vagrant/srcbuilds

# pandoc, weasyprint + deps, Roboto fonts, for generating documentation 
apt-get install pandoc pandoc-data -y -q 
python3 -m pip install --upgrade weasyprint 
python3 -m pip install --upgrade pillow
apt-get install fonts-roboto -y -q
mkdir -p /usr/local/share/fonts/robotomono/
wget --quiet --no-directories --no-parent --continue https://raw.githubusercontent.com/googlefonts/RobotoMono/main/fonts/ttf/RobotoMono-{Regular,Bold,Italic,BoldItalic,Light,LightItalic,Medium,MediumItalic,Thin,ThinItalic}.ttf -P /usr/local/share/fonts/robotomono/

# smith itself (only the font side of things)
echo " "
echo " "
echo "Installing smith (downloading/updating the dependencies might take a few minutes)"
echo " "
echo " "

apt-get install smith-font --no-install-recommends -y -q


# install python components (tracking main) and their dependencies directly via pip3  
python3 -m pip install --upgrade git+https://github.com/googlefonts/fontbakery.git@main#egg=fontbakery
# fontbakery extra deps 
python3 -m pip install --upgrade freetype-py


python3 -m pip install --upgrade git+https://github.com/googlefonts/GlyphsLib.git@main#egg=glyphsLib 
python3 -m pip install --upgrade git+https://github.com/googlefonts/pyfontaine.git@main#egg=fontaine 


# extra packages needed for fontproof
apt-get install wamerican wbritish -y 

# there are deprecation warnings but no failures with the SILE/fontproof combo
apt-mark unhold sile 
apt-get install sile -y -q  

# install sile extensions: fontproof
echo "removing older versions of the fontproof SILE extension if any" 
rm -rf /usr/share/sile/packagemanager/fontproof/
# sile -e 'installPackage("fontproof");os.exit()'
cd /home/vagrant/srcbuilds
git clone https://github.com/sile-typesetter/fontproof.git
cd fontproof 
# if you need to target a specific tag or branch, adjust and uncomment the following line:
# git checkout v1.6.0
install -m 644 classes/* /usr/share/sile/classes/
install -m 644 packages/* /usr/share/sile/packages/


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
echo "or refer to the smith manual in /usr/share/doc/python3-smith/ or https://github.com/silnrsi/smith/tree/master/docs/smith"
echo " "




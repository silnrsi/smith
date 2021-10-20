#!/usr/bin/env bash

# A provisioning script for Vagrant to make it easier to get the latest smith and its dependencies from the PPAs and/or source.
# This is designed to be called by the Vagrantfile wich expects this file to be in the same directory by default.

# This is for Ubuntu focal/20.04 LTS

# configure things for non-interactive and sdtin
sudo ex +"%s@DPkg@//DPkg" -cwq /etc/apt/apt.conf.d/70debconf
sudo dpkg-reconfigure debconf -f noninteractive -p critical

export DEBIAN_FRONTEND=noninteractive

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
# otsFromSource=True
otsFromSource=False

# set to True to include the sklearn module (for Harmattan)
# includeSklearn=True
includeSklearn=False

# to pin particular version of fontTools, set that version number here, else set to empty
#fontToolsHoldVersion=4.17.1
 fontToolsHoldVersion=

# End of configuration options


# the official smith PPA
sudo add-apt-repository -s -y ppa:silnrsi/smith-py3  2>&1 > /dev/null

# the current git PPA
sudo add-apt-repository -s -y ppa:git-core/ppa 2>&1 > /dev/null

# set git params in ~/.gitconfig
git config --global pull.rebase false


# the official SILE PPA
sudo add-apt-repository -s -y ppa:sile-typesetter/sile 2>&1 > /dev/null

sudo apt-get update -y -qq
sudo apt-get upgrade -y -qq -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-overwrite" -u -V --with-new-pkgs

# toolchain components currently built from source or retrieved via pypi
# most of these are now commented out as the corresponding items are available as packages or on the CI
# according to the features you need you can fill in the variables above or comment/uncomment accordingly before reprovisionning


# install pip3 
sudo apt-get install python3-pip -y -qq
python3 -m pip install --upgrade pip --user  --no-warn-script-location 

# config
pip config set install.no-warn-script-location false
pip config set global.disable-pip-version-check true


# generic toolchain
sudo apt-get install build-essential cmake gcc g++ automake libtool pkg-config icu-devtools libicu-dev  -y -qq


# checking if we already have local checkouts 
 if [ -d $HOME/srcbuilds ]
then
    echo " "
    echo "You already have previous builds, it's easier to delete them and start afresh. "
    echo " "
    echo "Deleting srcbuilds folder... "
    echo " "
    rm -rf $HOME/srcbuilds
fi

mkdir -p $HOME/srcbuilds




# Graphite and Harfbuzz

if [ "$graphiteFromSource" == "True" ]; then
	echo " "
	echo " "
	echo "Installing Graphite from source"
	echo " "
	echo " "


	sudo apt-get install build-essential cmake gcc g++ automake libtool pkg-config -y -qq
	cd $HOME/srcbuilds
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
	sudo apt-get install pkg-config gcc ragel gcovr gtk-doc-tools libfreetype6-dev libglib2.0-dev libcairo2-dev libicu-dev libgraphite2-dev python3-setuptools gobject-introspection libgirepository1.0-dev -y -qq
	cd $HOME/srcbuilds
	git clone --depth 1 https://github.com/harfbuzz/harfbuzz.git
	cd harfbuzz

	python3 -m pip install --upgrade git+https://github.com/mesonbuild/meson.git@master#egg=meson ninja --user
	meson build -Db_coverage=true --auto-features=enabled -Dgraphite=enabled  --buildtype=debugoptimized --wrap-mode=nodownload -Dexperimental_api=true -Dchafa=disabled
	ninja -C build
	sudo ninja install -C build
	ldconfig 
fi

# ots 
if [ "$otsFromSource" == "True" ];
then
	python3 -m pip install --upgrade git+https://github.com/googlefonts/ots-python.git@main#egg=opentype-sanitizer --user

	# ots from main repo (debugging and graphite support on by default)
	python3 -m pip install --upgrade meson ninja --user
	sudo apt-get install libfreetype6-dev -y -qq
	cd $HOME/srcbuilds
	git clone --depth 1 --recurse-submodules https://github.com/khaledhosny/ots.git
	cd ots
	meson build
	ninja -C build --quiet
	sudo ninja install -C build

else
	python3 -m pip install --upgrade opentype-sanitizer --user
fi

# fontvalidator
echo " "
echo " "
echo "Installing fontvalidator from source"
echo " "
echo " "
sudo apt-get install mono-mcs libmono-corlib4.5-cil libmono-system-windows-forms4.0-cil libmono-system-web4.0-cil xsltproc xdg-utils -y -qq 
cd $HOME/srcbuilds
git clone --depth 1 https://github.com/HinTak/Font-Validator.git fontval
cd fontval
make -s --quiet 2>&1 > /dev/null
make gendoc --quiet  2>&1 > /dev/null
sudo cp bin/*.exe /usr/local/bin/
sudo cp bin/*.dll* /usr/local/bin/
sudo cp bin/*.xsl /usr/local/bin/
sudo cp /usr/local/bin/FontValidator.exe /usr/local/bin/FontValidator

# toolchain components installed from packages (both main repositories and PPAs)

if [ "$graphiteFromSource" == "False" ]
then
	 sudo apt-get install libharfbuzz-bin -y -qq
fi

if [ "$includeSklearn" == "True" ]
then
	# clustering tool needed for collision-avoidance-based kerning:
	sudo apt-get install python3-sklearn -y -qq
fi


# smith options
if [ "$fontToolsHoldVersion" == "" ]
then
	# current fonttools
	sudo apt-mark unhold python3-fonttools
	sudo python3 -m pip uninstall fontTools --yes 
	sudo apt-get install --reinstall python3-fonttools -y -qq
else
	# target specific version for (or downgrade) fonttools
	sudo dpkg --remove --force-depends python3-fonttools
	sudo apt-mark hold python3-fonttools
	sudo python3 -m pip uninstall fontTools --yes 
	python3 -m pip install --upgrade fontTools==$fontToolsHoldVersion --user
fi

# crude chown because Harfbuzz wants write-access to optimize runs of its utilities
sudo chmod -R 776 $HOME/srcbuilds
sudo chown -R vagrant:vagrant $HOME/srcbuilds

# pandoc, weasyprint + deps, Roboto fonts, for generating documentation 
sudo apt-get install pandoc pandoc-data -y -qq
python3 -m pip install --upgrade weasyprint --user
python3 -m pip install --upgrade pillow --user
sudo apt-get install fonts-roboto -y -qq
sudo mkdir -p /usr/local/share/fonts/robotomono/
sudo wget --quiet --no-directories --no-parent --continue https://raw.githubusercontent.com/googlefonts/RobotoMono/main/fonts/ttf/RobotoMono-{Regular,Bold,Italic,BoldItalic,Light,LightItalic,Medium,MediumItalic,Thin,ThinItalic}.ttf -P /usr/local/share/fonts/robotomono/

# smith itself (only the font side of things)
echo " "
echo " "
echo "Installing smith (downloading/updating the dependencies might take a few minutes)"
echo " "
echo " "

sudo apt-get install smith-font --no-install-recommends -y -qq

# pip approach for fontmake deps 
python3 -m pip install --upgrade git+https://github.com/fonttools/fonttools.git@main --user
python3 -m pip install --upgrade git+https://github.com/python-lz4/python-lz4.git@master --user
python3 -m pip install --upgrade git+https://github.com/googlefonts/ufo2ft.git@main --user
python3 -m pip install --upgrade git+https://github.com/robotools/defcon.git@master --user
python3 -m pip install --upgrade git+https://github.com/googlefonts/compreffor.git@main --user
python3 -m pip install --upgrade git+https://github.com/typemytype/booleanOperations.git@master --user
python3 -m pip install --upgrade git+https://github.com/robotools/fontMath.git@master --user
python3 -m pip install --upgrade git+https://github.com/LettError/MutatorMath.git@master --user
python3 -m pip install --upgrade git+https://github.com/eea/odfpy.git@master --user
python3 -m pip install --upgrade git+https://github.com/robotools/fontParts.git@master --user

# install python components (tracking main) and their dependencies directly via pip3  
python3 -m pip install --upgrade git+https://github.com/googlefonts/fontbakery.git@main#egg=fontbakery --user
python3 -m pip install --upgrade git+https://github.com/googlefonts/GlyphsLib.git@main#egg=glyphsLib --user



# extra packages needed for fontproof
sudo apt-get install wamerican wbritish -y -qq

# install sile 
sudo apt-get install sile -y -qq

# install sile extensions: fontproof
echo "removing older versions of the fontproof SILE extension if any" 
sudo rm -rf /usr/share/sile/packagemanager/fontproof/
sudo sile -e 'installPackage("fontproof");os.exit()'


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




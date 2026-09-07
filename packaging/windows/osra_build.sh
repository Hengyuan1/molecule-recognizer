#!/usr/bin/env bash
# Runs only inside the dedicated native Windows MSYS2 UCRT64 build environment.
set -euo pipefail
osra_jobs=${1:-4}
osra_work=/opt/osra-build
osra_prefix=$osra_work/prefix
export PATH="$osra_prefix/bin:/ucrt64/bin:/usr/bin:$PATH"
mkdir -p "$osra_work/src" "$osra_prefix"
cd "$osra_work/src"
if [[ ! -d gocr-0.50pre-patched-2 ]]; then
    tar -xzf "$osra_work/downloads/gocr-0.50pre-patched-2.tgz"
fi
if [[ ! -d ocrad-0.23 ]]; then
    tar --lzip -xf "$osra_work/downloads/ocrad-0.23.tar.lz"
fi
if [[ ! -d openbabel-3-0-0-patched-3 ]]; then
    tar -xzf "$osra_work/downloads/openbabel-3-0-0-patched-3.tgz"
fi
if [[ ! -d osra-2.2.4 ]]; then
    tar -xzf "$osra_work/downloads/osra-2.2.4.tar.gz"
fi
if [[ ! -d tclap-1.2.5 ]]; then
    tar -xzf "$osra_work/downloads/tclap-1.2.5.tar.gz"
fi
mkdir -p "$osra_prefix/include"
cp -R "$osra_work/src/tclap-1.2.5/include/tclap" "$osra_prefix/include/"
if [[ ! -d eigen-3.4.0 ]]; then
    tar -xzf "$osra_work/downloads/eigen-3.4.0.tar.gz"
fi
cd "$osra_work/src/openbabel-3-0-0-patched-3"
if grep -q 'CMP0042 OLD' CMakeLists.txt; then
    patch -p1 < "$osra_work/openbabel-compat.patch"
fi

if [[ ! -f "$osra_prefix/lib/libPgm2asc.a" ]]; then
    cd "$osra_work/src/gocr-0.50pre-patched-2"
    ./configure --prefix="$osra_prefix" --without-netpbm CC=gcc CFLAGS="-O2 -std=gnu11 -fcommon"
    make -j"$osra_jobs" libs
    install -Dm644 src/libPgm2asc.a "$osra_prefix/lib/libPgm2asc.a"
    mkdir -p "$osra_prefix/include/gocr"
    install -m644 src/pgm2asc.h src/output.h src/list.h src/unicode.h src/gocr.h src/pnm.h "$osra_prefix/include/gocr/"
fi
install -m644 "$osra_work/src/gocr-0.50pre-patched-2/include/config.h" "$osra_prefix/include/gocr/config.h"
if [[ ! -f "$osra_prefix/lib/libocrad.a" ]]; then
    cd "$osra_work/src/ocrad-0.23"
    ./configure --prefix="$osra_prefix" CXX=g++ CXXFLAGS="-O2 -std=c++11"
    make -j"$osra_jobs"
    make install
fi

cmake -S "$osra_work/src/openbabel-3-0-0-patched-3" -B "$osra_work/openbabel-build" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$(cygpath -m "$osra_prefix")" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_CXX_STANDARD=17 \
    -DEIGEN3_INCLUDE_DIR="$(cygpath -m "$osra_work/src/eigen-3.4.0")" \
    -DLIBXML2_LIBRARY="$(cygpath -m /ucrt64/lib/libxml2.dll.a)" \
    -DCAIRO_LIBRARY="$(cygpath -m /ucrt64/lib/libcairo.dll.a)" \
    -DZLIB_LIBRARY_RELEASE="$(cygpath -m /ucrt64/lib/libz.dll.a)" \
    -DBUILD_SHARED=OFF -DBUILD_MIXED=ON -DBUILD_GUI=OFF -DENABLE_TESTS=OFF -DPYTHON_BINDINGS=OFF \
    -DWITH_STATIC_INCHI=ON -DWITH_STATIC_LIBXML=ON
cmake --build "$osra_work/openbabel-build" --parallel "$osra_jobs"
cmake --install "$osra_work/openbabel-build"
# This upstream Windows install rule puts static archives in bin/.
install -m644 "$osra_prefix/bin/libopenbabel.a" "$osra_prefix/bin/libinchi.a" "$osra_prefix/lib/"

cd "$osra_work/src/osra-2.2.4"
cp "$osra_work/osra_portable.h" src/
if ! grep -q osra_configure_portable_runtime src/osra_lib.cpp; then
    patch -p1 < "$osra_work/osra-portable.patch"
fi
if grep -q '(unsigned long)rand_mem' src/CImg.h; then
    patch -p1 < "$osra_work/osra-cimg.patch"
fi
./configure --build=x86_64-w64-mingw32 --prefix="$osra_prefix" \
    --with-openbabel-include="$osra_prefix/include/openbabel3" --with-openbabel-lib="$osra_prefix/lib" \
    --with-gocr-include="$osra_prefix/include/gocr" --with-gocr-lib="$osra_prefix/lib" \
    --with-ocrad-include="$osra_prefix/include" --with-ocrad-lib="$osra_prefix/lib" \
    CPPFLAGS="-D_USE_MATH_DEFINES -I$osra_prefix/include -I/ucrt64/include -I/ucrt64/include/freetype2" \
    LDFLAGS="-L$osra_prefix/lib -L/ucrt64/lib" CXXFLAGS="-O2 -std=c++17" \
    LIBS="-linchi -lxml2 -lcairo -lz -lws2_32"
make -j"$osra_jobs"
make install
"$osra_prefix/bin/osra.exe" --version

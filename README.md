# python-xcompile

A script to build Python for Android, based on the recipe by wandering_logic: https://github.com/wandering-logic/android_x86_python-3.4

It compiles cpython from source, then uses it and the NDK toolchains to compile cpython for target platforms.

Note that even though with some patches compilation succeeds, there are still major parts of Python standard library that fail.
In my case, even some basic modules (like cmath) fail tests on my Android device. You have been warned.

Note also that this script will change your cpython source tree.

## PREREQUISITES

In order to use this script, you need:

 - A recent version of Python 3 on your Build machine,
 - cpython sources,
 - wandering_logic's patches,
 - Standalone toolchains for target platforms.
 
Note that you can create a standalone toolchain for a given platform by executing

    $ ${NDK_DIR}/build/tools/make-standalone-toolchain.sh --toolchain=TOOLCHAIN_NAME \
        --platform=TARGET_PLATFORM --install-dir=${NDK_TOOLCHAINS_ROOT}/toolchain-target-triplet

So, for example, to create a toolchain for x86 that uses gcc-4.9 and targets android-19, you want to run:
 
    $ ${NDK_DIR}/build/tools/make-standalone-toolchain.sh --toolchain=x86-4.9 \
        --platform=android-19 --install-dir=/tmp/android-toolchains/i686-linux-android

(Yes, toolchains in the ${NDK_DIR}/toolchains don't always use the right target triplets)

## BUILDING

In order to compile Python for Android you have to:

  - edit the paths in the script, or
  - provide the paths as environment variables, or
  - provide the paths as command-line parameters.

You have to provide the paths for:

  - A folder that contains all your NDK toolchains (variable `NDK_TOOLCHAINS_PATH`, option `--ndk-toolchains-dir`)
  - A folder that contains your cpython sources (variable `PYTHON_SOURCE_PATH`, option `--python-source`)
  - A folder that will contain intermediate build files (variable `BUILD_DIR_PATH`, option `--build-dir`)
  - A folder that will contain compilation results (variable `OUTPUT_PATH`, option `--output-dir`)
  
Additionally, if your toolchains contain version suffices, you have to provide them with `NDK_TOOLCHAIN_SUFFIX` variable or 
`--ndk-version-suffix` option.

By default, the script will try to build binaries for all supported platforms. To override that, you should specify a
comma-separated list of platforms as a `--platforms` (variable `TARGET_PLATFORMS`) option.

So, to compile Python for arm and x86, with sources in `/tmp/cpython-hg`, intermediate builds in `/tmp/pybuild`, toolchains in
`/opt/android-toolchains`, with a suffix of `4.9`, and results in /opt/andpython, you want to run:
    $ python3 compile.py --ndk-toolchains-dir /opt/android-toolchains --ndk-toolchain-suffix 4.9 \
        --python-source /tmp/cpython-hg --build-dir /tmp/pybuild --output-dir /opt/andpython \
        --platforms arm,x86

## PATCHES

For now, Python for Android can't be built without applying patches first. Moreover, due to Android quirkiness, configuration
script actually gets some values "wrong" (notably, the `HAVE_GETHOSTBYNAME_R` macro: there are actually prototypes for
gethostbyname_r and gethostbyaddr_r in Android headers, but there's no gethostbyaddr_r in bionic), there are patches that
should be applied after configuring build.

Patches that should be applied to the source tree should be put in the `prepatch` folder and will be run before the configure
script. Patches that should be applied to the build tree should be put in the `postpatch` folder and will be run after the
configure script.

By default, there should be patches from wandering_logic and a couple of patches to build some modules statically and
use `pgen` from build machine. Feel free to add more patches!

## CAVEATS

For now, Python executable is not built as a position-independent executable. This means that you can't run the built
binary on Android 5.0 and up.

## RUNNING

By default, your `/sdcard` on your device is mounted with the `noexec` flag that prevents you from running the binary directly
from your device. If you really want to run the interpreter on your device, you should copy the python3 executable to some
place in your device (`/data/python3`, for exampe) that you're allowed to run executables from. You can place the shared library
(`libpython3.4.so.1.0`) anywhere, but make sure to copy Python modules (that reside in `lib/python3.4`) and to provide the path
in `sys.path` for your scripts!

This way, though, you should provide an LD_PRELOAD variable that points to the Python shared library:

    $ LD_PRELOAD=/path/to/libpython3.4.so.1.0 /path/to/python3.4

This should give you a running interpreter (or, at least, a helpful error message).

The correct way to use Python on Android would probably be to use only the shared library embedded in an application
(with some glue code to make Python and Java interact).

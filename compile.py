#!/usr/bin/env python3

"""
This script attempts to cross-compile Python 3.4.

You need to have:
 - A recent source tree
 - A working Python3 installation
 - All prerequisites for compiling Python on your host machine
 - A recent NDK
 - patches from wandering_logic
"""

import os, subprocess
import argparse
import sys

# A list of supported architectures.
# Note that for each entry you have to have a toolchain
# in a folder named {archs[arch]}-{compiler_version}
archs = {
         'armeabi':     'arm-linux-androideabi',
         'armeabi-v7a': 'arm-linux-androideabi',
         'x86':         'i686-linux-android',
         'mips':        'mipsel-linux-android'
        }


# These are default values for options provided below. Feel free to change them.

options = {
           'platforms': ','.join(archs.keys()),
           'ndk-toolchains-dir': '/home/sf/devel/android-toolchains',
           'ndk-toolchain-suffix': '',
           'python-source': '/home/sf/devel/cpython-hg',
           'build-dir': '/home/sf/devel/python/xcompile/build',
           'output-dir': '/home/sf/devel/python/xcompile/andpython',
          }

# These are envvar aliases for options.

envvar_aliases = {
                  'platforms': 'TARGET_PLATFORMS',
                  'ndk-toolchains-dir': 'NDK_TOOLCHAINS_PATH',
                  'ndk-toolchain-suffix': 'NDK_TOOLCHAIN_SUFFIX',
                  'python-source': 'PYTHON_SOURCE_PATH',
                  'build-dir': 'BUILD_DIR_PATH',
                  'output-dir': 'OUTPUT_PATH'
                 }

def execute_command(command, use_shell = True, output=sys.stdout):
    """
    Execute a command and return the return code.
    Note that we don't give any input to the process. This call will deadlock for any
    interactive command.
    """
    proc = subprocess.Popen(command,
                            stdout = subprocess.PIPE,
                            shell = use_shell,
                            universal_newlines = True)
    print('Executing {cmd} with pid of {pid}:'.format(cmd = ' '.join(command), pid = proc.pid), file = output)
    for data in proc.stdout:
        print('[{0}]'.format(proc.pid), data, end = '', file = output)
    while proc.poll() is None:
        # Wait for the process to finish
        pass
    return proc.returncode
  
def loadopts():
    """
    Read and prepare all options.
    There are three possible sources for options:
      1. Command-line options, parsed by argparse,
      2. Environment variables,
      3. Defaults (set in this script).
    A command-line option will override an option set by an environment variable,
    and environment variables override defaults.
    """
    for optname in options.keys():
        if envvar_aliases[optname] in os.environ.keys():
            options[optname] = os.environ[envvar_aliases[optname]]
    parser = argparse.ArgumentParser(description='A test program to see how argparse works')
    parser.add_argument('--ndk-toolchains-dir', help='Path to ndk standalone toolchains', metavar='PATH/TO/ANDROID/TOOLCHAINS')
    parser.add_argument('--ndk-toolchain-suffix', help='Toolchain directory suffix, usually the compiler version', metavar='4.9')
    parser.add_argument('--platforms', help='Comma-separated list of target platforms', metavar='arm,x86,mips')
    parser.add_argument('--python-source', help='Path to Python sources', metavar='PATH/TO/CPYTHON/SOURCE/TREE')
    parser.add_argument('--build-dir', help='Path to building directory', metavar='PATH/TO/BUILD/DIR')
    parser.add_argument('--output-dir', help='Path to output directory', metavar='PATH/TO/OUTPUT/DIRECTORY')
    args = parser.parse_args()
    for argname in options.keys():
        if args.__contains__(argname):
            arg = args.__getattribute__(argname)
            if arg is not None:
                options[argname] = arg

def fail(reason = 'none given', code = 1):
    """
    Print a given message and exit with the given error code.
    """
    print('Building failed! Reason: {r}'.format(r=reason))
    exit(code)

# Some internal variables, mostly copied from options

loadopts()

current_dir = os.path.realpath('.')
py_sourcedir = options['python-source']
pyhost_installdir = options['build-dir'] + '/hostpython'
pyhost_builddir = options['build-dir'] + '/hostpython_build'
#pyhost_installdir = current_dir + '/hostpython'
#pyhost_builddir = current_dir + '/python_build'
#pyand_installdir = current_dir + '/andpython'
#pyand_builddir = current_dir + '/andpython_build'

#ndk_toolchain_path = '/home/sf/devel/android-toolchains'
ndk_toolchain_path = options['ndk-toolchains-dir']
ndk_toolchain_suffix = options['ndk-toolchain-suffix']

envpath = os.environ['PATH']

cpus = os.cpu_count()

# Stage one: build host python

print('Stage 1: Building host python')

build_cmds = [
# Uncomment the next line if you want a clean rebuild.
#              ['make', 'distclean'],
              [py_sourcedir + '/configure', '--enable-shared', '--prefix=' + pyhost_installdir],
              ['make', '-j{num}'.format(num = cpus)],
              ['make', 'install']
             ]

if not os.path.isdir(pyhost_builddir):
    os.makedirs(pyhost_builddir)
os.chdir(pyhost_builddir)
# Check if we already have a compiled host Python
# and a parser generator from host python build.
if not (os.path.isfile(pyhost_installdir + '/bin/python3')
	and os.path.isfile(pyhost_builddir + '/Parser/pgen')):
    if os.path.isfile(pyhost_builddir + '/Makefile'):
        execute_command(['make', 'distclean'], use_shell = False)
    for cmd in build_cmds:
        err = execute_command(cmd, use_shell = False)
        if err != 0:
            fail('Could not build host python; see logs for details.')
else:
    print('Host python found, skipping build.')

# Use this newly built python for the next steps.
os.environ['PATH'] = pyhost_installdir + '/bin:' + os.environ['PATH']
if 'LD_LIBRARY_PATH' in os.environ.keys():
    os.environ['LD_LIBRARY_PATH'] = pyhost_installdir + '/lib:' + os.environ['LD_LIBRARY_PATH']
else:
    os.environ['LD_LIBRARY_PATH'] = pyhost_installdir + '/lib'

# Stage two: apply patches for android python
# Patches should be in prepatch folder.
print('Stage 2: applying patches to Python source tree')

os.chdir(py_sourcedir)
for patchfile in os.listdir(current_dir + '/prepatch'):
    if patchfile.endswith('.patch'):
        execute_command(['patch -N -p1 < {patchdir}/{patch}'.format(
            patchdir = current_dir + '/prepatch',
            patch = patchfile)], use_shell = True)
# Regenerate configure script and headers.
execute_command(['autoheader'], use_shell = False)
execute_command(['autoconf'], use_shell = False)

# Stage three: configure and build Python for all target platforms.
# Note that these patches should be in the postpatch directory
# and will be applied to the bulid tree.

print('Stage 3: Building android python')

for arch in archs.keys():
    print('Building for {arch}'.format(arch=arch))
    toolchain = archs[arch]
    if len(ndk_toolchain_suffix) > 0:
        toolchain += '-{suffix}'.format(suffix=ndk_toolchain_suffix)
    toolchain_path = '{ndkpath}/{toolchain}'.format(ndkpath=ndk_toolchain_path, toolchain=toolchain)
    os.environ['PATH'] = '{toolpath}/bin:'.format(toolpath=toolchain_path) + envpath
    and_sysroot = '{toolpath}/sysroot'.format(toolpath=toolchain_path)
    pyand_builddir = options['build-dir'] + '/andbuild-{arch}'.format(arch=arch)
    pyand_installdir = options['output-dir'] + '/andpython/{arch}'.format(arch=arch)
    build_cmds = [
#                  ['cp', '{hostbuild}/Parser/pgen'.format(hostbuild=pyhost_builddir), '{pybuild}/Parser/pgen'.format(pybuild=pyand_builddir)],
                  ['make', '-j{num}'.format(num = cpus), 'HOSTPGEN={hostbuild}/Parser/pgen'.format(hostbuild=pyhost_builddir)],
                  ['make', 'install']
                 ]
# FIXME: Add building position-independent executables without breaking shared library build.
    os.environ['CFLAGS'] = '--sysroot=' + and_sysroot + ' -I{pysource}/FIXLOCALE'.format(pysource=py_sourcedir) #+ ' -fPIE'
    os.environ['LDFLAGS'] = '--sysroot=' + and_sysroot + ' -L{builddir}'.format(builddir=pyand_builddir) #+ ' -fPIE -pie' 

    if not os.path.isdir(pyand_builddir):
        os.makedirs(pyand_builddir)
    os.chdir(pyand_builddir)
    if not os.path.isfile(pyand_installdir + '/bin/python3'):
# Remove next two lines if you don't want to have a clean build every time.
        if os.path.isfile(pyand_builddir + '/Makefile'):
            execute_command(['make', 'distclean'], use_shell = False)
# As there might be patches to be applied to the build tree, configure should be executed before everything else.
        err = execute_command([py_sourcedir + '/configure', '--enable-shared', '--prefix='+pyand_installdir, '--build=x86_64-linux-gnu', '--host={target}'.format(target=archs[arch]), '--disable-ipv6', 'ac_cv_file__dev_ptmx=no', 'ac_cv_file__dev_ptc=no', 'ac_cv_little_endian_double=no', '--without-ensurepip'],
                              use_shell = False)
        if err != 0:
            fail('Configuration failed; see logs for details.')
# Post-patch the build tree
        for patchfile in os.listdir(current_dir + '/postpatch'):
            if patchfile.endswith('.patch'):
                execute_command(['patch -N -p1 < {patchdir}/{patch}'.format(
                                 patchdir = current_dir + '/postpatch', patch = patchfile)], 
                                 use_shell = True)
        for cmd in build_cmds:
            err = execute_command(cmd, use_shell = (len(cmd) == 1))
            if err != 0:
                fail('Build failed for arch: {arch}'.format(arch=arch))
    else:
        print('Nothing to do for {arch}'.format(arch=arch))

print('All done.')

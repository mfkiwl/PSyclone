
# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2017-2018, Science and Technology Facilities Council.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------
# Authors: R. W. Ford and A. R. Porter, STFC Daresbury Lab

''' This module contains tests for the the various utility functions in
psyclone_test_utils.'''

from __future__ import absolute_import
import pytest
from psyclone.tests.utilities import CompileError, get_invoke, Compile


HELLO_CODE = '''
program hello
  write (*,*) "Hello"
end program hello
'''


def test_compiler_works(tmpdir):
    ''' Check that the specified compiler works for a hello-world
    example '''
    Compile.skip_if_compilation_disabled()

    old_pwd = tmpdir.chdir()
    try:
        with open("hello_world.f90", "w") as ffile:
            ffile.write(HELLO_CODE)
        Compile(tmpdir).compile_file("hello_world.f90", link=True)
    finally:
        old_pwd.chdir()


def test_compiler_with_flags(tmpdir):
    ''' Check that we can pass through flags to the Fortran compiler.
    Since correct flags are compiler-dependent and hard to test,
    we pass something that is definitely not a flag and check that
    the compiler complains. This test is skipped if no compilation
    tests have been requested (--compile flag to py.test). '''
    Compile.skip_if_compilation_disabled()
    old_pwd = tmpdir.chdir()
    try:
        with open("hello_world.f90", "w") as ffile:
            ffile.write(HELLO_CODE)
        _compile = Compile(tmpdir)
        # pylint: disable=protected-access
        _compile._f90flags = "not-a-flag"
        with pytest.raises(CompileError) as excinfo:
            _compile.compile_file("hello_world.f90")
        assert "not-a-flag" in str(excinfo)
        # For completeness we also try with a valid flag although we
        # can't actually check its effect.
        _compile._f90flags = "-g"
        _compile.compile_file("hello_world.f90", link=True)
    finally:
        old_pwd.chdir()


def test_build_invalid_fortran(tmpdir):
    ''' Check that we raise the expected error when attempting
    to compile some invalid Fortran. Skips test if --compile not
    supplied to py.test on command-line. '''
    Compile.skip_if_compilation_disabled()
    invalid_code = HELLO_CODE.replace("write", "wite", 1)
    old_pwd = tmpdir.chdir()
    try:
        with open("hello_world.f90", "w") as ffile:
            ffile.write(invalid_code)
        _compile = Compile(tmpdir)
        with pytest.raises(CompileError) as excinfo:
            _compile.compile_file("hello_world.f90")
    finally:
        old_pwd.chdir()
    assert "Compile error" in str(excinfo)


def test_find_fortran_file(tmpdir):
    ''' Check that our find_fortran_file routine raises the expected
    error if it can't find a matching file. Also check that it returns
    the correct name if the file does exist. '''
    with pytest.raises(IOError) as excinfo:
        Compile.find_fortran_file([str(tmpdir)], "missing_file")
    assert "missing_file' with suffix in ['f90', 'F90'," in str(excinfo)
    old_pwd = tmpdir.chdir()
    try:
        with open("hello_world.f90", "w") as ffile:
            ffile.write(HELLO_CODE)
        name = Compile.find_fortran_file([str(tmpdir)], "hello_world")
        assert name.endswith("hello_world.f90")
    finally:
        old_pwd.chdir()


def test_compile_str(monkeypatch, tmpdir):
    ''' Checks for the routine that compiles Fortran supplied as a string '''
    # Check that we always return True if compilation testing is disabled
    Compile.skip_if_compilation_disabled()
    _compile = Compile(tmpdir)
    test_compile = "psyclone.tests.utilities.Compile"
    monkeypatch.setattr(test_compile+".TEST_COMPILE", False)
    monkeypatch.setattr(test_compile+".TEST_COMPILE_OPENCL", False)
    assert _compile.string_compiles("not fortran")
    # Re-enable compilation testing and check that we can build hello world
    monkeypatch.setattr(test_compile+".TEST_COMPILE", True)
    assert _compile.string_compiles(HELLO_CODE)
    # Repeat for some broken code
    invalid_code = HELLO_CODE.replace("write", "wite", 1)
    assert not _compile.string_compiles(invalid_code)


# -----------------------------------------------------------------------------
def test_get_invoke():
    '''Tests get_invokes. '''

    # First test all 4 valid APIs - we only make sure that no exception
    # is raised, so no assert required

    _, _ = get_invoke("openmp_fuse_test.f90", "gocean0.1", idx=0)

    _, _ = get_invoke("test14_module_inline_same_kernel.f90",
                      "gocean1.0", idx=0)

    _, _ = get_invoke("algorithm/1_single_function.f90", "dynamo0.1", idx=0)

    _, _ = get_invoke("1_single_invoke.f90", "dynamo0.3", idx=0)

    # Test that an invalid name raises an exception
    with pytest.raises(RuntimeError) as excinfo:
        _, _ = get_invoke("test11_different_iterates_over_one_invoke.f90",
                          "gocean1.0", name="invalid_name")
    assert "Cannot find an invoke named 'invalid_name'" in str(excinfo)

    # Test that an invalid API raises the right exception:
    with pytest.raises(RuntimeError) as excinfo:
        _, _ = get_invoke("test11_different_iterates_over_one_invoke.f90",
                          "invalid-api", name="invalid_name")
    assert "The API 'invalid-api' is not supported" in str(excinfo)

# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2020-2022, Science and Technology Facilities Council
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

'''A simple transformation script for the introduction of OpenMP with PSyclone.
In order to use it you must first install PSyclone. See README.md in the
top-level psyclone directory.

Once you have PSyclone installed, this script may be used by doing:

 >>> psyclone -api "nemo" -s ./omp_trans.py my_file.F90

This should produce a lot of output, ending with generated
Fortran.

'''
from psyclone.psyir.nodes import Loop
from psyclone.transformations import OMPParallelLoopTrans, OMPLoopTrans, \
    OMPParallelTrans, TransformationError

# Get the transformation we will apply
OMP_TRANS = OMPParallelLoopTrans()
OMP_LOOP_TRANS = OMPLoopTrans()
OMP_PARALLEL_TRANS = OMPParallelTrans()


def trans(psy):
    ''' Transform a specific Schedule by making all loops
    over vertical levels OpenMP parallel. Encloses children 6-9 of the
    outer iteration loop within a single OpenMP parallel region.

    :param psy: the object holding all information on the PSy layer \
                to be modified.
    :type psy: :py:class:`psyclone.psyGen.PSy`

    :returns: the transformed PSy object
    :rtype:  :py:class:`psyclone.psyGen.PSy`

    '''
    # Get the Schedule of the target routine
    sched = psy.invokes.get('tra_adv').schedule

    for child in sched.children:
        if isinstance(child, Loop) and child.loop_type == "levels":
            try:
                OMP_TRANS.apply(child)
            except TransformationError:
                pass

    # Find body of the iteration loop (identified as a 'tracer' loop)
    it_loop_body = None
    for child in sched.children:
        if isinstance(child, Loop) and child.loop_type == "tracers":
            it_loop_body = child.loop_body
            break

    # Put an OMP parallel do around all suitable loops except 6-9
    for child in it_loop_body.children[0:6] + it_loop_body.children[10:]:
        if isinstance(child, Loop) and child.loop_type == "levels":
            OMP_TRANS.apply(child)

    # Put an OMP loop around each of loops 6-9
    for child in it_loop_body.children[6:10]:
        OMP_LOOP_TRANS.apply(child)

    # Enclose loops 6-9 within a single OMP parallel region
    OMP_PARALLEL_TRANS.apply(it_loop_body.children[6:10])

    # Display the transformed PSyIR
    print(sched.view())

    # Return the modified psy object
    return psy

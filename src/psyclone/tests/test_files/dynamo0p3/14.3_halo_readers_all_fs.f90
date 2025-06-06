! -----------------------------------------------------------------------------
! BSD 3-Clause License
!
! Copyright (c) 2017-2025, Science and Technology Facilities Council
! All rights reserved.
!
! Redistribution and use in source and binary forms, with or without
! modification, are permitted provided that the following conditions are met:
!
! * Redistributions of source code must retain the above copyright notice, this
!   list of conditions and the following disclaimer.
!
! * Redistributions in binary form must reproduce the above copyright notice,
!   this list of conditions and the following disclaimer in the documentation
!   and/or other materials provided with the distribution.
!
! * Neither the name of the copyright holder nor the names of its
!   contributors may be used to endorse or promote products derived from
!   this software without specific prior written permission.
!
! THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
! "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
! LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
! FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
! COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
! INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
! BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
! LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
! CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
! LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
! ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
! POSSIBILITY OF SUCH DAMAGE.
! -----------------------------------------------------------------------------
! Author R. W. Ford, STFC Daresbury Lab
! Modified I. Kavcic, Met Office

program halo_reader_fs

  ! A single kernel call testing all function spaces. Each function
  ! space has a stencil operation so that it requires halo exchange
  ! calls. All extents are passed in and are the same for all fields.
  use constants_mod,           only: i_def
  use field_mod,               only: field_type
  use testkern_stencil_fs_mod, only: testkern_stencil_fs_type

  implicit none

  type(field_type)    :: f1, f2, f3, f4, f5, f6, f7, f8, &
                         f9, f10, f11, f12, f13, f14, f15, f16
  integer(kind=i_def) :: extent = 1

  call invoke(                                            &
       testkern_stencil_fs_type(f1,                       &
                                f2, extent, f3, extent,   &
                                f4, extent, f5, extent,   &
                                f6, extent, f7, extent,   &
                                f8, extent, f9, extent,   &
                                f10, extent, f11, extent, &
                                f12, extent, f13, extent, &
                                f14, extent, f15, extent, &
                                f16, extent) )

end program halo_reader_fs

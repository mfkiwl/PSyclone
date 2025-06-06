!-------------------------------------------------------------------------------
! Copyright (c) 2017-2025,  Met Office, on behalf of HMSO and Queen's Printer
! For further details please refer to the file LICENCE.original which you
! should have received as part of this distribution.
!-------------------------------------------------------------------------------
! LICENCE.original is available from the Met Office Science Repository Service:
! https://code.metoffice.gov.uk/trac/lfric/browser/LFRic/trunk/LICENCE.original
! -----------------------------------------------------------------------------
! BSD 3-Clause License
!
! Modifications copyright (c) 2017-2025, Science and Technology Facilities Council
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
!------------------------------------------------------------------------------
! Modified by I. Kavcic, Met Office

module apply_variable_hx_kernel_mod

use argument_mod,            only : arg_type,                         &
                                    GH_FIELD, GH_OPERATOR, GH_SCALAR, &
                                    GH_REAL, GH_READ, GH_WRITE,       &
                                    ANY_SPACE_1, CELL_COLUMN
use fs_continuity_mod,       only : W3, W2
use constants_mod,           only : r_def, i_def
use kernel_mod,              only : kernel_type

implicit none

private

!-------------------------------------------------------------------------------
! Public types
!-------------------------------------------------------------------------------

type, public, extends(kernel_type) :: apply_variable_hx_kernel_type
  private
  type(arg_type) :: meta_args(10) = (/                                 &
       arg_type(GH_FIELD,    GH_REAL, GH_WRITE, W3),                   &
       arg_type(GH_FIELD,    GH_REAL, GH_READ,  W2),                   &
       arg_type(GH_FIELD,    GH_REAL, GH_READ,  ANY_SPACE_1),          &
       arg_type(GH_FIELD,    GH_REAL, GH_READ,  W3),                   &
       arg_type(GH_OPERATOR, GH_REAL, GH_READ,  W3, W2),               &
       arg_type(GH_OPERATOR, GH_REAL, GH_READ,  W3, ANY_SPACE_1),      &
       arg_type(GH_OPERATOR, GH_REAL, GH_READ,  ANY_SPACE_1, W2),      &
       arg_type(GH_OPERATOR, GH_REAL, GH_READ,  W3, W3),               &
       arg_type(GH_SCALAR,   GH_REAL, GH_READ),                        &
       arg_type(GH_SCALAR,   GH_REAL, GH_READ)                         &
       /)
  integer :: operates_on = CELL_COLUMN
contains
  procedure, nopass :: apply_variable_hx_code
end type
type, public, extends(kernel_type) :: opt_apply_variable_hx_kernel_type
  private
  type(arg_type) :: meta_args(10) = (/                                 &
       arg_type(GH_FIELD,    GH_REAL, GH_WRITE, W3),                   &
       arg_type(GH_FIELD,    GH_REAL, GH_READ,  W2),                   &
       arg_type(GH_FIELD,    GH_REAL, GH_READ,  ANY_SPACE_1),          &
       arg_type(GH_FIELD,    GH_REAL, GH_READ,  W3),                   &
       arg_type(GH_OPERATOR, GH_REAL, GH_READ,  W3, W2),               &
       arg_type(GH_OPERATOR, GH_REAL, GH_READ,  W3, ANY_SPACE_1),      &
       arg_type(GH_OPERATOR, GH_REAL, GH_READ,  ANY_SPACE_1, W2),      &
       arg_type(GH_OPERATOR, GH_REAL, GH_READ,  W3, W3),               &
       arg_type(GH_SCALAR,   GH_REAL, GH_READ),                        &
       arg_type(GH_SCALAR,   GH_REAL, GH_READ)                         &
       /)
  integer :: operates_on = CELL_COLUMN
contains
  procedure, nopass :: opt_apply_variable_hx_code
end type

!-------------------------------------------------------------------------------
! Contained functions/subroutines
!-------------------------------------------------------------------------------
public apply_variable_hx_code
public opt_apply_variable_hx_code

contains

!> @brief Applies the component of the helmholtz operator that maps from velocity space
!>        to the pressure space as well as the constant in space part
!> @details The Helmholtz operator can be summarised as:
!>          \f[
!>             H(p) = Mp + \nabla.\left( \nabla p \right) + \bar{ \nabla p }
!>         \f]
!>        For a given p & \f[ \nabla p \f] this kernel applies the
!>        divergence \f[ \nabla. X \f] and averaging  \f[ \bar{X} \f]
!>        operators as well as the application of the mass matrix M
!> @param[in] cell Horizontal cell index
!> @param[in] nlayers Number of layers
!> @param[in,out] lhs Pressure field with helmholtz operator applied to it
!> @param[in] x Gradient of the pressure field in the velocity space
!> @param[in] mt_inv Lumped inverse mass matrix for the temperature space
!> @param[in] pressure Field that helmholtz operator is being applied to
!> @param[in] ncell_3d_1 Total number of cells for divergence matrix
!> @param[in] div Generalised divergence matrix
!> @param[in] ncell_3d_2 Total number of cells for p3t matrix
!> @param[in] p3t Mapping from temperature space to pressure space
!> @param[in] ncell_3d_3 Total number of cells for pt2 matrix
!> @param[in] pt2 Mapping from velocity space to temperature space
!> @param[in] ncell_3d_4 Total number of cells for m3 matrix
!> @param[in] m3 Mass matrix for the pressure space
!> @param[in] tau Relaxation weight
!> @param[in] dt Weight based upon the timestep
!> @param[in] ndf_w3 Number of degrees of freedom per cell for the pressure space
!> @param[in] undf_w3 Unique number of degrees of freedom  for the pressure space
!> @param[in] map_w3 Dofmap for the cell at the base of the column for the pressure space
!> @param[in] ndf_w2 Number of degrees of freedom per cell for the velocity space
!> @param[in] undf_w2 Unique number of degrees of freedom  for the velocity space
!> @param[in] map_w2 Dofmap for the cell at the base of the column for the velocity space
!> @param[in] ndf_wt Number of degrees of freedom per cell for the temperature space
!> @param[in] undf_wt Unique number of degrees of freedom  for the temperature space
!> @param[in] map_wt Dofmap for the cell at the base of the column for the temperature space
subroutine apply_variable_hx_code(cell,        &
                                  nlayers,     &
                                  lhs, x,      &
                                  mt_inv,      &
                                  pressure,    &
                                  ncell_3d_1,  &
                                  div,         &
                                  ncell_3d_2,  &
                                  p3t,         &
                                  ncell_3d_3,  &
                                  pt2,         &
                                  ncell_3d_4,  &
                                  m3,          &
                                  tau,         &
                                  dt,          &
                                  ndf_w3, undf_w3, map_w3, &
                                  ndf_w2, undf_w2, map_w2, &
                                  ndf_wt, undf_wt, map_wt)

  implicit none

  ! Arguments
  integer(kind=i_def),                    intent(in) :: cell, nlayers
  integer(kind=i_def),                    intent(in) :: ncell_3d_1, ncell_3d_2, ncell_3d_3, ncell_3d_4
  integer(kind=i_def),                    intent(in) :: undf_w2, ndf_w2
  integer(kind=i_def),                    intent(in) :: undf_w3, ndf_w3
  integer(kind=i_def),                    intent(in) :: undf_wt, ndf_wt
  integer(kind=i_def), dimension(ndf_w3), intent(in) :: map_w3
  integer(kind=i_def), dimension(ndf_w2), intent(in) :: map_w2
  integer(kind=i_def), dimension(ndf_wt), intent(in) :: map_wt

  real(kind=r_def), dimension(undf_w2), intent(in)    :: x
  real(kind=r_def), dimension(undf_wt), intent(in)    :: mt_inv
  real(kind=r_def), dimension(undf_w3), intent(inout) :: lhs
  real(kind=r_def), dimension(undf_w3), intent(in)    :: pressure
  real(kind=r_def),                     intent(in)    :: tau, dt

  real(kind=r_def), dimension(ncell_3d_1,ndf_w3,ndf_w2), intent(in) :: div
  real(kind=r_def), dimension(ncell_3d_2,ndf_wt,ndf_w2), intent(in) :: pt2
  real(kind=r_def), dimension(ncell_3d_3,ndf_w3,ndf_wt), intent(in) :: p3t
  real(kind=r_def), dimension(ncell_3d_4,ndf_w3,ndf_w3), intent(in) :: m3

  ! Internal variables
  integer(kind=i_def)                 :: df, k, ik, is, ie
  real(kind=r_def), dimension(ndf_w2) :: x_e
  real(kind=r_def), dimension(ndf_w3) :: lhs_e, p_e
  real(kind=r_def), dimension(ndf_wt) :: t_e

  real(kind=r_def), allocatable, dimension(:) :: t

  ! Only need a section of the theta field that contains indices for this
  ! column
  is = minval(map_wt)
  ie = maxval(map_wt)+nlayers-1
  allocate( t(is:ie) )
  t(is:ie) = 0.0_r_def

  ! Compute Pt2 * u
  do k = 0, nlayers-1
    do df = 1, ndf_w2
      x_e(df) = x(map_w2(df)+k)
    end do
    ik = (cell-1)*nlayers + k + 1

    t_e = matmul(pt2(ik,:,:),x_e)
    do df = 1,ndf_wt
      t(map_wt(df)+k) = t(map_wt(df)+k) + t_e(df)
    end do
  end do

  ! Compute D * u + tau * P3t * Mt^-1 * ( Pt2 * u )
  do k = 0,nlayers-1
    do df = 1,ndf_wt
      t_e(df) = t(map_wt(df)+k)*mt_inv(map_wt(df)+k)*tau
    end do
    do df = 1, ndf_w2
      x_e(df) = x(map_w2(df)+k)
    end do
    do df = 1, ndf_w3
      p_e(df) = pressure(map_w3(df)+k)
    end do

    ik = (cell-1)*nlayers + k + 1

    lhs_e = matmul(m3(ik,:,:),p_e) + dt*(matmul(div(ik,:,:),x_e) + matmul(p3t(ik,:,:),t_e))
    do df = 1,ndf_w3
       lhs(map_w3(df)+k) = lhs_e(df)
    end do
  end do
end subroutine apply_variable_hx_code

!=============================================================================!
!> @brief Applies the component of the helmholtz operator that maps from velocity space
!>        to the pressure space as well as the constant in space part, optimised for lowest
!>        order elements with horizontally discontinuous temperature space
!> @details The Helmholtz operator can be summarised as:
!>          \f[
!>             H(p) = Mp + \nabla.\left( \nabla p \right) + \bar{ \nabla p }
!>         \f]
!>        For a given p & \f[ \nabla p \f] this kernel applies the
!>        divergence \f[ \nabla. X \f] and averaging  \f[ \bar{X} \f]
!>        operators as well as the application of the mass matrix M
!> @param[in] cell Horizontal cell index
!> @param[in] nlayers Number of layers
!> @param[in,out] lhs Pressure field with helmholtz operator applied to it
!> @param[in] x Gradient of the pressure field in the velocity space
!> @param[in] mt_inv Lumped inverse mass matrix for the temperature space
!> @param[in] pressure Field that helmholtz operator is being applied to
!> @param[in] ncell_3d_1 Total number of cells for divergence matrix
!> @param[in] div Generalised divergence matrix
!> @param[in] ncell_3d_2 Total number of cells for p3t matrix
!> @param[in] p3t Mapping from temperature space to pressure space
!> @param[in] ncell_3d_3 Total number of cells for pt2 matrix
!> @param[in] pt2 Mapping from velocity space to temperature space
!> @param[in] ncell_3d_4 Total number of cells for m3 matrix
!> @param[in] m3 Mass matrix for the pressure space
!> @param[in] tau Relaxation weight
!> @param[in] dt Weight based upon the timestep
!> @param[in] ndf_w3 Number of degrees of freedom per cell for the pressure space
!> @param[in] undf_w3 Unique number of degrees of freedom  for the pressure space
!> @param[in] map_w3 Dofmap for the cell at the base of the column for the pressure space
!> @param[in] ndf_w2 Number of degrees of freedom per cell for the velocity space
!> @param[in] undf_w2 Unique number of degrees of freedom  for the velocity space
!> @param[in] map_w2 Dofmap for the cell at the base of the column for the velocity space
!> @param[in] ndf_wt Number of degrees of freedom per cell for the temperature space
!> @param[in] undf_wt Unique number of degrees of freedom  for the temperature space
!> @param[in] map_wt Dofmap for the cell at the base of the column for the temperature space
subroutine opt_apply_variable_hx_code(cell,        &
                                  nlayers,     &
                                  lhs, x,      &
                                  mt_inv,      &
                                  pressure,    &
                                  ncell_3d_1,  &
                                  div,         &
                                  ncell_3d_2,  &
                                  p3t,         &
                                  ncell_3d_3,  &
                                  pt2,         &
                                  ncell_3d_4,  &
                                  m3,          &
                                  tau,         &
                                  dt,          &
                                  ndf_w3, undf_w3, map_w3, &
                                  ndf_w2, undf_w2, map_w2, &
                                  ndf_wt, undf_wt, map_wt)

  implicit none

  ! Arguments
  integer(kind=i_def),                    intent(in) :: cell, nlayers
  integer(kind=i_def),                    intent(in) :: ncell_3d_1, ncell_3d_2, ncell_3d_3, ncell_3d_4
  integer(kind=i_def),                    intent(in) :: undf_w2, ndf_w2
  integer(kind=i_def),                    intent(in) :: undf_w3, ndf_w3
  integer(kind=i_def),                    intent(in) :: undf_wt, ndf_wt
  integer(kind=i_def), dimension(ndf_w3), intent(in) :: map_w3
  integer(kind=i_def), dimension(ndf_w2), intent(in) :: map_w2
  integer(kind=i_def), dimension(ndf_wt), intent(in) :: map_wt

  real(kind=r_def), dimension(undf_w2), intent(in)    :: x
  real(kind=r_def), dimension(undf_wt), intent(in)    :: mt_inv
  real(kind=r_def), dimension(undf_w3), intent(inout) :: lhs
  real(kind=r_def), dimension(undf_w3), intent(in)    :: pressure
  real(kind=r_def),                     intent(in)    :: tau, dt

  real(kind=r_def), dimension(ncell_3d_1,1,6), intent(in) :: div
  real(kind=r_def), dimension(ncell_3d_2,2,6), intent(in) :: pt2
  real(kind=r_def), dimension(ncell_3d_3,1,2), intent(in) :: p3t
  real(kind=r_def), dimension(ncell_3d_4,1,1), intent(in) :: m3

  ! Internal variables
  integer(kind=i_def)            :: df, k, ik
  real(kind=r_def), dimension(2) :: t_e
  real(kind=r_def)               :: div_u

  ! Compute D * u + tau * P3t * Mt^-1 * ( Pt2 * u )
  ! Hard wired optimisation for desired configuration
  k = 0
  ik = (cell-1)*nlayers + k + 1
  t_e(1:2) = 0.0_r_def
  do df = 1,6
    t_e(1) = t_e(1) + pt2(ik,1,df)*x(map_w2(df)+k)
    t_e(2) = t_e(2) + pt2(ik,2,df)*x(map_w2(df)+k) + pt2(ik+1,1,df)*x(map_w2(df)+k+1)
  end do
  t_e(1) = mt_inv(map_wt(1)+k)*p3t(ik,1,1)*t_e(1)
  t_e(2) = mt_inv(map_wt(2)+k)*p3t(ik,1,2)*t_e(2)

  div_u = div(ik,1,1)*x(map_w2(1)+k) + div(ik,1,2)*x(map_w2(2)+k) + div(ik,1,3)*x(map_w2(3)+k) &
        + div(ik,1,4)*x(map_w2(4)+k) + div(ik,1,5)*x(map_w2(5)+k) + div(ik,1,6)*x(map_w2(6)+k)
  lhs(map_w3(1)+k) = m3(ik,1,1)*pressure(map_w3(1)+k) &
                   + dt*(div_u + tau*(t_e(1) + t_e(2)))

  do k = 1,nlayers-2
    ik = (cell-1)*nlayers + k + 1
    t_e(1:2) = 0.0_r_def
    do df = 1,6
      t_e(1) = t_e(1) + pt2(ik,1,df)*x(map_w2(df)+k) + pt2(ik-1,2,df)*x(map_w2(df)+k-1)
      t_e(2) = t_e(2) + pt2(ik,2,df)*x(map_w2(df)+k) + pt2(ik+1,1,df)*x(map_w2(df)+k+1)
    end do
    t_e(1) = mt_inv(map_wt(1)+k)*p3t(ik,1,1)*t_e(1)
    t_e(2) = mt_inv(map_wt(2)+k)*p3t(ik,1,2)*t_e(2)

    div_u = div(ik,1,1)*x(map_w2(1)+k) + div(ik,1,2)*x(map_w2(2)+k) + div(ik,1,3)*x(map_w2(3)+k) &
          + div(ik,1,4)*x(map_w2(4)+k) + div(ik,1,5)*x(map_w2(5)+k) + div(ik,1,6)*x(map_w2(6)+k)
    lhs(map_w3(1)+k) = m3(ik,1,1)*pressure(map_w3(1)+k) &
                     + dt*(div_u + tau*(t_e(1) + t_e(2)))
  end do

  k = nlayers-1
  ik = (cell-1)*nlayers + k + 1
  t_e(1:2) = 0.0_r_def
  do df = 1,6
    t_e(1) = t_e(1) + pt2(ik,1,df)*x(map_w2(df)+k) + pt2(ik-1,2,df)*x(map_w2(df)+k-1)
    t_e(2) = t_e(2) + pt2(ik,2,df)*x(map_w2(df)+k)
  end do
  t_e(1) = mt_inv(map_wt(1)+k)*p3t(ik,1,1)*t_e(1)
  t_e(2) = mt_inv(map_wt(2)+k)*p3t(ik,1,2)*t_e(2)

  div_u = div(ik,1,1)*x(map_w2(1)+k) + div(ik,1,2)*x(map_w2(2)+k) + div(ik,1,3)*x(map_w2(3)+k) &
        + div(ik,1,4)*x(map_w2(4)+k) + div(ik,1,5)*x(map_w2(5)+k) + div(ik,1,6)*x(map_w2(6)+k)
  lhs(map_w3(1)+k) = m3(ik,1,1)*pressure(map_w3(1)+k) &
                   + dt*(div_u + tau*(t_e(1) + t_e(2)))

end subroutine opt_apply_variable_hx_code

end module apply_variable_hx_kernel_mod

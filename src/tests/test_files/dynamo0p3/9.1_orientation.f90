!-------------------------------------------------------------------------------
! (c) The copyright relating to this work is owned jointly by the Crown,
! Met Office and NERC 2015.
! However, it has been created with the help of the GungHo Consortium,
! whose members are identified at https://puma.nerc.ac.uk/trac/GungHo/wiki
!-------------------------------------------------------------------------------
! Author A. R. Porter STFC Daresbury Lab

program orientation

  ! Description: single function specified in an invoke call
  use testkern_orientation_on_write, only: testkern_orientation_type
  use inf,      only: field_type
  implicit none
  type(field_type) :: f1, f2, m1
  type(quadrature_rule) :: qr

  call invoke(                   &
       testkern_orientation_type(f1,f2,m1,qr)   &
          )

end program orientation

# PSyclone Wrapper Library for `dl_timer`

This is a wrapper library that maps the PSyclone profiling API
to the dl_timer API. This library is thread-safe.


## Dependencies

The library dl_timer must be installed. It can be downloaded from
https://bitbucket.org/apeg/dl_timer
It uses the ProfileData type and dl_timer's timer_register function
to store the module/region name and the index used by dl_timer.

## Compilation

```sh
gfortran -c dl_timer.f90 -I PATH-TO-DLTIMER/src/
```

The application needs to provide the dl_timer directory as module or include
path, and link with `dl_timer.o` and dl_timer:

```sh
gfortran -o a.out ... PATH-TO-PSYCLONE/lib/profiling/dl_timer/dl_timer.o \
         -L PATH-TO-DLTIMER -ldltimer
```


Example output:

```
=============================== Timing report ===============================
Timed using POSIX timer. Units are seconds.
Reported resolution =  0.1000E-08 (s)
Effective clock granularity =  0.25997E-07 (s)
Measured systematic error in dl_timer API =  0.37790E-07 +/- 0.789E-09 (s)
Measured overhead in calling start/stop =  0.9411E-07 (s)
Measured overhead in calling start/stop for registered timer =  0.4725E-07 (s)
-----------------------------------------------------------------------------
Region                          Counts     Total       Average*     Std Err
-----------------------------------------------------------------------------
psy_inputoutput:eliminate_one_no     1  0.12603E+00   0.12603E+00  0.00E+00
psy_time_step_mod:swlon_adjust_c    11  0.12201E+01   0.11092E+00  0.28E-02
psy_time_step_mod:swlon_code        11  0.44050E+01   0.40046E+00  0.25E-02
psy_time_step_mod:swlon_update_c    11  0.18761E+01   0.17056E+00  0.45E-03
psy_time_step_mod:swlat_adjust_c    11  0.12325E+01   0.11204E+00  0.53E-03
psy_time_step_mod:swlat_code        11  0.50031E+01   0.45483E+00  0.26E-02
psy_time_step_mod:swlat_update_c    11  0.19000E+01   0.17272E+00  0.24E-02
-----------------------------------------------------------------------------
* corrected for systematic error
=============================================================================
```

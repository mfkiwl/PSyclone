# Simple Stand-alone Timer Library

This library is a simple stand-alone timer library. It counts
the number of calls for each region, and reports minumum, maximum
and average times. This library is not thread-safe, and not
MPI aware (e.g. maximum reported is per process, not across all
processes).

## Dependencies

None

## Compilation

```sh
gfortran -c simple_timer.f90
```

The application needs to provide the template directory as module or include
path.

Sample output:

```
===========================================
module::region                                         count           sum                     min             average                 max
psy_inputoutput::eliminate_one_node_islands_code           1     0.128906250             0.128906250             0.128906250             0.128906250    
psy_time_step_mod::swlon_adjust_code                      11      1.19921875             0.105468750             0.109019883             0.113281250    
psy_time_step_mod::swlon_code                             11      4.38281250             0.394531250             0.398437500             0.406250000    
psy_time_step_mod::swlon_update_code                      11      1.86718750             0.167968750             0.169744313             0.171875000    
psy_time_step_mod::swlat_adjust_code                      11      1.23828125             0.109375000             0.112571023             0.117187500    
psy_time_step_mod::swlat_code                             11      4.87890625             0.437500000             0.443536937             0.445312500    
psy_time_step_mod::swlat_update_code                      11      1.87500000             0.167968750             0.170454547             0.179687500    
===========================================
```

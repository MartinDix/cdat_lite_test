#!/usr/bin/env python
import cdms,cdutil,os,sys

## Test 6h data
f=cdms.open(os.path.join(sys.prefix,'sample_data','psl_6h.nc'))
s=f('psl')

t=s.getTime()
print '6 hourly data, before:'
print t.getBounds()

cdutil.times.setTimeBoundsDaily(t,4)
print '6 hourly data, after:'
print t.getBounds()[:8]

## test daily
f=cdms.open(os.path.join(sys.prefix,'sample_data','ts_da.nc'))
s=f('ts')
t=s.getTime()
print 'daily data, before:'
print t.getBounds()

cdutil.times.setTimeBoundsDaily(s,1)

print 'daily data, after:'
print t.getBounds()[:8]

import cdms,os,sys,cdat_info

if cdat_info.CDMS_INCLUDE_DAP=='yes':
    print 'Testing Dap'
    f=cdms.open("http://test.opendap.org/opendap/nph-dods/data/nc/fnoc1.nc")
    print f.listvariables()
else:
    print 'CDMS not built with DAP support, skipped DAP test'

if cdat_info.CDMS_INCLUDE_PP=='yes':
    print 'Testing PP'
    f=cdms.open(os.path.join(sys.prefix,'sample_data','testpp.pp'))
    print f.listvariables()
else:
    print 'CDMS not built with PP support, skipped PP test'

if cdat_info.CDMS_INCLUDE_HDF=='yes':
    print 'Testing HDF'
    f=cdms.open(os.path.join(sys.prefix,'sample_data','tdata.hdf'))
    print f.listvariables()
else:
    print 'CDMS not built with HDF4 support, skipped HDF4 test'

if cdat_info.CDMS_INCLUDE_DRS=='yes':
    print 'Testing DRS'
    f=cdms.open(os.path.join(sys.prefix,'sample_data','ta_300_850_PCM_O_mm_xy_wa_r0000_0000.dic'))
    print f.listvariables()
else:
    print 'CDMS not built with DRS support, skipped DRS test'

    
## if DAP:
##     try:
##         print 'DAP and Scientific ?'
##         import Scientific.IO.NetCDF
##         f=Scientific.IO.NetCDF.NetCDFFile('http://ferret.wrc.noaa.gov/cgi-bin/nph-nc/data/COADS_climatology.nc')
##         print f.variables
##     except:
##         print 'Failed'

    
if cdat_info.CDMS_INCLUDE_DRS=='yes':
    print 'Testing cdms/ql ?'
    f=cdms.open(os.path.join(sys.prefix,'sample_data','test.cdms'))
    print f.listvariables()
else:
    print 'CDMS not built with PSQL support, skipped PSQL test'
print 'test ran ok'

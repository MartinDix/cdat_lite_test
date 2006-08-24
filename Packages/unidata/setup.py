from distutils.core import setup, Extension
import os,sys,string


setup (name = "udunits",
       version='1.0',
       author='doutriaux1@llnl.gov',
       description = "Python wrapping for UDUNITS package developped by UNIDATA",
       url = "http://www-pcmdi.llnl.gov/software",
       packages = ['unidata'],
       package_dir = {'unidata': 'Lib'},
       ext_modules = [
    Extension('unidata.udunits_wrap',
              ['Src/udunits_wrap.c',
               'Src/utparse.c',
               'Src/utlib.c',
               'Src/utscan.c',
               ],
              include_dirs = ['Include']
              )
    ]
      )

f=open('Src/udunits.dat')
version=sys.version.split()[0].split('.')
version=string.join(version[:2],'.')
f2=open(sys.prefix+'/lib/python'+version+'/site-packages/unidata/udunits.dat','w')
for l in f.xreadlines():
    f2.write(l)
f2.close()
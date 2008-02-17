# Adapted for numpy/ma/cdms2 by convertcdms.py
# stats.py - reworked module for statistical analysis
"""
This module has been written specifically for the SalStat statistics package. 
It is an object oriented (and more limited) version of Gary Strangmans 
stats.y module, and much code has been taken from there. The classes and 
methods are usable from the command line, and some may prefer the OO style 
to stats.py's functional style.

Most of the code in this file is copyright 2002 Alan James Salmoni, and is
released under version 2 or later of the GNU General Public Licence (GPL).
See the enclosed file COPYING for the full text of the licence.

Other parts of this code were taken from stats.py by Gary Strangman of
Harvard University (c) Not sure what year, Gary Strangman, released under the 
GNU General Public License."""

import numpy.oldnumeric.ma as MA,MV2 as MV,cdms2 as cdms,array_indexing_emulate as array_indexing
from statistics import __checker
import numpy

################################
# RandomArray isn't included in numpy
# Added by Stephen Pascoe
import numpy.random

## Short routines used in the functional constructs to reduce analysis time
add=MA.add
multiply=MA.multiply
sum=MA.sum
mean=MA.average # Shortcut

def _fixScalar(a):
    if isinstance(a,(float,int)) or a.shape==():
        a=MA.array([a,],copy=0)
        return a
    else:
        return a
    
## Diference Squared
def _diffsquared(a,b): return MA.power(a-b,2)
def differencesquared(x,y,axis=0):
    """Computes the Squared differecne between 2 datasets
    Usage:
        diff=differencesquared(a,b)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    isvar=0
    if cdms.isVariable(y) :
        isvar=1
        xatt=y.attributes
        ax=y.getAxisList()
    if cdms.isVariable(x) :
        isvar=1
        xatt=x.attributes
        ax=x.getAxisList()
    diff=_diffsquared(x,y)
    if isvar:
        diff=cdms.createVariable(diff,axes=ax,id='differencesquared',copy=0)
        if 'units' in xatt.keys(): diff.units=xatt['units']+'*'+xatt['units']
    ## in case we passed 2 Numeric
    if (not MA.isMA(x)) and (not MA.isMA(y)):
        diff=diff.filled(1.e20)
    return diff

## No need to make it user available
def _shellsort(inlist):
    """ _shellsort algorithm.  Sorts a 1D-list.

        Usage:   _shellsort(inlist)
        Returns: sorted-inlist, sorting-index-vector (for original list)
        """
    return MA.sort(inlist,axis=0),MA.argsort(inlist,axis=0)

## Rankdata
def _rankdata(inlist):
    """
    Ranks the data in inlist, dealing with ties appropritely.
    Adapted from Gary Perlman's |Stat ranksort.

    Usage:   _rankdata(inlist)
    Returns: a list of length equal to inlist, containing rank scores
    """
    n = inlist.shape[0]
    svec, ivec = _shellsort(inlist)
    ivec=ivec.astype('i')
    sumranks = MA.zeros(inlist.shape[1:])
    dupcount = MA.zeros(inlist.shape[1:],'d')
    newlist = MA.zeros(inlist.shape,'d')
    newlist2 = MA.zeros(inlist.shape,'d')
    for i in range(n):
        sumranks = sumranks + i
        dupcount = dupcount + 1.
        if i!=n-1:
            c1=MA.not_equal(svec[i],svec[i+1])
        else:
            c1=MA.ones(c1.shape)
        if i==n-1 or (not MA.allequal(c1,0)):
            averank = MA.array(sumranks / dupcount + 1)
            maxdupcount=int(MA.maximum(dupcount))
            for j in range(i-maxdupcount+1,i+1):
                c2=MA.logical_and(c1,MA.greater_equal(j,maxdupcount-dupcount))
                newlist[j]=MA.where(c2,averank,newlist[j])
            sumranks = MA.where(c1,0.,sumranks)
            dupcount = MA.where(c1,0,dupcount)
    for i in range(n):
        newlist2=array_indexing.set(newlist2,ivec[i],newlist[i])  
    return newlist2
def rankdata(x,axis=0):
    """
    Ranks the data, dealing with ties appropritely.
    Adapted from Gary Perlman's |Stat ranksort.
    Further adapted to MA/Numeric by PCMDI's team

    Usage:   rankdata(array, axis=axisoptions)
    Returns: a list of length equal to inlist, containing rank scores
    Option:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
            default value = 0. You can pass the name of the dimension or index
            (integer value 0...n) over which you want to compute the statistic.
            even: 'xy': to do over 2 dimensions at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x2,y,weights,axis,ax=__checker(x,None,None,axis)
    rk=_rankdata(x2)
    if not ax is None:
        rk=cdms.createVariable(rk,id='ranked',copy=0)
        if len(axis)>1:
            ax.insert(0,rk.getAxis(0))
            rk.setAxisList(ax)
        else:
            ax.insert(0,x.getAxis(axis[0]))
            rk.setAxisList(ax)
            rk=rk(order=x.getOrder(ids=1))
    return rk

def _tiecorrect(rankvals):
    """
    Corrects for ties in Mann Whitney U and Kruskal Wallis H tests.  See
    Siegel, S. (1956) Nonparametric Statistics for the Behavioral Sciences.
    New York: McGraw-Hill.  Code adapted from |Stat rankind.c code.
    
    Usage:   _tiecorrect(rankvals)
    Returns: T correction factor for U or H
    """
    sorted=MA.sort(rankvals,axis=0)
    n = sorted.shape[0]
    T = MA.zeros(sorted.shape[1:])
    i = 0
    c0=MA.ones(sorted.shape[1:])
    while (i<n-1):
        nties = MA.ones(sorted.shape[1:])
        c1=MA.logical_and(MA.equal(sorted[i],sorted[i+1]),c0)
        c2=c1
        j=i
        while not MA.allequal(c2,0):
            c2=MA.logical_and(c2,MA.equal(sorted[j],sorted[j+1]))
            nties=nties+c2
            j=j+1
            if j>=n-1:
                break
        T = MA.where(c1,T + nties**3 - nties,T)
        i = i+1
        if i<n-1:
            c0=MA.not_equal(sorted[i],sorted[i-1])
    T = T / float(n**3-n)
    return 1.0 - T

def tiecorrect(x,axis=0):
    """
    Corrects for ties in Mann Whitney U and Kruskal Wallis H tests.  See
    Siegel, S. (1956) Nonparametric Statistics for the Behavioral Sciences.
    New York: McGraw-Hill.  Code adapted from |Stat rankind.c code.
    
    Usage:   T = tiecorrect(rankvals,axis=axisoptions)
    Option:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
            default value = 0. You can pass the name of the dimension or index
            (integer value 0...n) over which you want to compute the statistic.
            even: 'xy': to do over 2 dimensions at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    T=_tiecorrect(x)
    if not ax is None:
        T=cdms.createVariable(T,id='tiecorrect',copy=0,axes=ax)
##         print axis,ax,T.shape
##         if len(axis)>1:
##             ax.insert(0,T.getAxis(0))
##             T.setAxisList(ax)
##         else:
##             ax.insert(0,x.getAxis(axis[0]))
##             T.setAxisList(ax)
##             T=T(order=x.getOrder(ids=1))
    return T


###########################
## Probability functions ##
###########################
    
def _chisqprob(chisq,df,Z_MAX=6.0):
    """
    Returns the (1-tailed) probability value associated with the provided
    chi-square value and df.  Adapted from chisq.c in Gary Perlman's |Stat.
    
    Usage:   _chisqprob(chisq,df,Z_MAX=6.0)
    """
    BIG = 20.0
    def ex(x):
        mask=x.mask
        tmp=MA.masked_less(x,-BIG)
        tmp=MA.exp(tmp).filled(0)
        if mask is not None:
            tmp=MA.masked_where(mask,tmp)
        return tmp

    c1=MA.logical_or(MA.less_equal(chisq,0.),MA.less(df,1))
    result=c1*1.
    a = 0.5 * chisq
    even=MA.equal(0,MA.remainder(df,2.))
    y=MA.where(MA.greater(df,1),ex(-a),0.)
    s=MA.where(even,y,2.0 * _zprob(-MA.sqrt(chisq),Z_MAX))
    ## Part 1 df>2
    c1=MA.logical_not(c1)
    cdf2=MA.logical_and(MA.greater(df,2),c1)
    chisq=MA.where(cdf2,.5*(df-1),chisq)
    z=MA.where(even,1.,.5)
    ## Where a > BIG
    c2=MA.greater(a,BIG)
    e=MA.where(even,0.,MA.log(MA.sqrt(numpy.pi)))
    c=MA.log(a)
    e2=MA.where(even,1.,1.0 / MA.sqrt(numpy.pi) / MA.sqrt(a))
    cc=MA.zeros(e.shape)
    c3=MA.less_equal(z,chisq)
    c2a=MA.logical_and(c2,cdf2)
    c2b=MA.logical_and(MA.logical_not(c2),cdf2)
    #c4=MA.logical_and(c3,c2b)
    while not MA.allequal(MA.logical_and(c3,cdf2),0):
        c4=MA.logical_and(c3,c2a)
        e=MA.where(c4,MA.log(z)+e,e)
        s=MA.where(c4,s+ex(c*z-a-e),s)
        z=MA.where(c4,z+1.,z)
        result=MA.where(c4,s,result)
        c4=MA.logical_and(c3,c2b)
        e2=MA.where(c4,e2*a/z,e2)
        cc=cc+e2
        z=MA.where(c4,z+1.,z)
        c3=MA.less_equal(z,chisq)
        result=MA.where(c4,cc*y+s,result)
    result=MA.where(MA.logical_and(MA.logical_not(cdf2),c1),s,result)
    return result

def chisqprob(chisq,df,Z_MAX=6.0):
    """
    Returns the (1-tailed) probability value associated with the provided
    chi-square value and df.  Adapted from chisq.c in Gary Perlman's |Stat.
    
    Usage:   prob = chisqprob(chisq,df)
    Options:
    Z_MAX: Maximum meaningfull value for z probability (default=6.0)
    """
    chisq = _fixScalar(chisq)
    df = _fixScalar(df)
    isvar=0
    if cdms.isVariable(chisq) :
        isvar=1
        ax=chisq.getAxisList()
    p=_chisqprob(chisq,df)
    if isvar:
        p=cdms.createVariable(p,axes=ax,id='probability',copy=0)
    ## in case we passed 2 Numeric
    if not MA.isMA(chisq):
        p=p.filled(1.e20)
    return p

def _inversechi(prob, df):
    """This function calculates the inverse of the chi square function. Given
    a p-value and a df, it should approximate the critical value needed to 
    achieve these functions. Adapted from Gary Perlmans critchi function in
    C. Apologies if this breaks copyright, but no copyright notice was 
    attached to the relevant file.
    """
    minchisq = MA.zeros(df.shape)
    maxchisq = MA.ones(df.shape)*99999.0
    chi_epsilon = 0.000001
    c1=MA.less_equal(prob,0.)
    chisqval=c1*maxchisq
    chisqval=MA.masked_where(c1,chisqval)
    chisqval=MA.masked_where(MA.greater_equal(prob,1.),chisqval)
    c1=MA.logical_not(MA.logical_or(MA.greater_equal(prob,1.),c1)) ## slots left to be set
    chisqval = MA.where(c1,df / MA.sqrt(prob),chisqval)
    c2=MA.greater(maxchisq - minchisq,chi_epsilon)
    while not MA.allequal(c2,0.):
        c=MA.less(_chisqprob(chisqval, df),prob)
        maxchisq=MA.where(c,chisqval,maxchisq)
        minchisq=MA.where(MA.logical_not(c),chisqval,minchisq)
        chisqval = MA.where(c2,(maxchisq + minchisq) * 0.5,chisqval)
        c2=MA.greater(maxchisq - minchisq,chi_epsilon)
    chisqval=MA.where(MA.less_equal(prob,0.),99999.0,chisqval)
    chisqval=MA.where(MA.greater_equal(prob,1.),0.0,chisqval)
    return chisqval

def inversechi(prob, df):
    """This function calculates the inverse of the chi square function. Given
    a p-value and a df, it should approximate the critical value needed to 
    achieve these functions. Adapted from Gary Perlmans critchi function in
    C. Apologies if this breaks copyright, but no copyright notice was 
    attached to the relevant file.
    Usage invchi = inversechi(prob,df,axis=axisoptions)
    """
    prob = _fixScalar(prob)
    df = _fixScalar(df)
    isvar=0
    if cdms.isVariable(prob) :
        isvar=1
        ax=prob.getAxisList()
    invchi=_inversechi(prob,df)
    if isvar:
        invchi=cdms.createVariable(invchi,axes=ax,id='inversechi',copy=0)
    ## in case we passed 2 Numeric
    if not MA.isMA(prob):
        invchi=invchi.filled(1.e20)
    return invchi

def _erfcc(x):
    """
    Returns the complementary error function erfc(x) with fractional
    error everywhere less than 1.2e-7.  Adapted from MAal Recipies.
    
    Usage:   _erfcc(x)
    """
    z = MA.absolute(x)
    t = 1.0 / (1.0+0.5*z)
    ans = t * MA.exp(-z*z-1.26551223 + t*(1.00002368+t*(0.37409196+t* \
                                    (0.09678418+t*(-0.18628806+t* \
                                    (0.27886807+t*(-1.13520398+t* \
                                    (1.48851587+t*(-0.82215223+t* \
                                    0.17087277)))))))))

    return MA.where(MA.greater_equal(x,0),ans,2.-ans)

def erfcc(x):
    """
    Returns the complementary error function erfc(x) with fractional
    error everywhere less than 1.2e-7.  Adapted from MAal Recipies.
    
    Usage:   err = erfcc(x)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    isvar=0
    if cdms.isVariable(x) :
        isvar=1
        ax=x.getAxisList()
    err =_erfcc(x)
    if isvar:
        err = cdms.createVariable(err,axes=ax,id='erfcc',copy=0)
    ## in case we passed a Numeric
    if not MA.isMA(x):
        err=err.filled(1.e20)
    return err

    
def _zprob(z,Z_MAX = 6.0):
    """
    Returns the area under the normal curve 'to the left of' the given z value.
    Thus, 
    for z<0, _zprob(z) = 1-tail probability
    for z>0, 1.0-_zprob(z) = 1-tail probability
    for any z, 2.0*(1.0-_zprob(abs(z))) = 2-tail probability
    Adapted from z.c in Gary Perlman's |Stat.
    
    Usage:  z =  _zprob(z,Z_MAX = 6.0)
    """

    ## Z_MAX = 6.0    # maximum meaningful z-value

    y=.5*MA.absolute(z)
    c1=MA.greater_equal(y,Z_MAX*.5)
    c2=MA.less(y,1.)
    x=MA.not_equal(z,0)*1.
    w=MA.where(c2,y*y,1.)
    x=MA.where(c2,((((((((0.000124818987 * w
			-0.001075204047) * w +0.005198775019) * w
		      -0.019198292004) * w +0.059054035642) * w
		    -0.151968751364) * w +0.319152932694) * w
		  -0.531923007300) * w +0.797884560593) * y * 2.0,x)
    c2=MA.logical_not(MA.logical_or(c1,c2))
    y=MA.where(c2,y-2.,y)
    x=MA.where(c2, (((((((((((((-0.000045255659 * y
			     +0.000152529290) * y -0.000019538132) * y
			   -0.000676904986) * y +0.001390604284) * y
			 -0.000794620820) * y -0.002034254874) * y
		       +0.006549791214) * y -0.010557625006) * y
		     +0.011630447319) * y -0.009279453341) * y
		   +0.005353579108) * y -0.002141268741) * y
		 +0.000535310849) * y +0.999936657524,x)
    prob=MA.where(MA.greater(z,0.),((x+1.0)*0.5),((1.0-x)*0.5))
    return prob

def zprob(z,Z_MAX = 6.0):
    """
    Returns the area under the normal curve 'to the left of' the given z value.
    Thus, 
    for z<0, zprob(z) = 1-tail probability
    for z>0, 1.0-zprob(z) = 1-tail probability
    for any z, 2.0*(1.0-zprob(abs(z))) = 2-tail probability
    Adapted from z.c in Gary Perlman's |Stat.

    Z_MAX: Maximum meaningfull value  for z probability (default = 6)
    
    Usage:   z = zprob(z,Z_MAX=6.0 )
    """
    z = _fixScalar(z)
    isvar=0
    if cdms.isVariable(z) :
        isvar=1
        ax=z.getAxisList()
    prob =_zprob(z, Z_MAX)
    if isvar:
        prob = cdms.createVariable(prob,axes=ax,id='zprob',copy=0)
    ## in case we passed a Numeric
    if not MA.isMA(z):
        prob=prob.filled(1.e20)
    return prob


def _ksprob(alam):
    """
    Computes a Kolmolgorov-Smirnov t-test significance level.  Adapted from
    MAal Recipies.

    Usage:   ks = _ksprob(alam)
    """
    fac = 2.0
    sum = 0.0
    termbf = 0.0
    a2 = -2.0*alam*alam
    c=MA.not_equal(alam,0)
    ans=MA.ones(alam.shape)
    for j in range(1,201):
        ## Avoiding overflow....
        ae=a2*j*j
        ae=MA.where(MA.less(ae,-745),-745,ae)
	term = fac*MA.exp(ae)
	sum = sum + term
        a=MA.absolute(term)
        c1=MA.less_equal(a,.001*termbf)
        c2=MA.less(a,1.E-8*sum).filled(0)
        c2=MA.logical_or(c1,c2)
        ## To avoid overflow on exp....
        a2=MA.masked_where(c2,a2)
        c2=MA.logical_and(c2,c)
        ans=MA.where(c2.filled(0),sum,ans)
        c=MA.logical_and(c,MA.logical_not(c2))
	fac = -fac
	termbf = MA.absolute(term)
        if MA.allequal(c.filled(0),0):
            break
    return ans             # Get here only if fails to converge; was 0.0!!

def ksprob(x):
    """
    Computes a Kolmolgorov-Smirnov t-test significance level.  Adapted from
    MAal Recipies.

    Usage:   ks = ksprob(x)
    """
    x = _fixScalar(x)
    isvar=0
    if cdms.isVariable(x) :
        isvar=1
        ax=x.getAxisList()
    prob =_ksprob(x)
    if isvar:
        prob = cdms.createVariable(prob,axes=ax,id='ksprob',copy=0)
    ## in case we passed a Numeric
    if not MA.isMA(x):
        prob=prob.filled(1.e20)
    return prob

def _fprob (dfnum, dfden, F):
    """
    Returns the (1-tailed) significance level (p-value) of an F
    statistic given the degrees of freedom for the numerator (dfR-dfF) and
    the degrees of freedom for the denominator (dfF).
    
    Usage:   _fprob(dfnum, dfden, F)   where usually dfnum=dfbn, dfden=dfwn
    """
    return _betai(0.5*dfden, 0.5*dfnum, dfden/(dfden+dfnum*F))
    
def fprob (dfnum, dfden, F):
    """
    Returns the (1-tailed) significance level (p-value) of an F
    statistic given the degrees of freedom for the numerator (dfR-dfF) and
    the degrees of freedom for the denominator (dfF).
    
    Usage:   prob = fprob(dfnum, dfden, F)   where usually dfnum=dfbn, dfden=dfwn
    """
    dfnum = _fixScalar(dfnum)
    dfden = _fixScalar(dfden)
    F = _fixScalar(F)
    isvar=0
    if cdms.isVariable(F) :
        isvar=1
        ax=F.getAxisList()
    prob =_fprob(dfnum, dfden, F)
    if isvar:
        prob = cdms.createVariable(prob,axes=ax,id='fprob',copy=0)
    ## in case we passed a Numeric
    if not MA.isMA(F):
        prob=prob.filled(1.e20)
    return prob

def _tprob(df, t):
    return _betai(0.5*df,MA.ones(df.shape)*0.5,df/(1.*df+t*t))

def tprob(df, t):
    """Returns t probabilty given degree of freedom and T statistic
    Usage: prob = tprob(df,t)
    """
    df = _fixScalar(df)
    t = _fixScalar(t)
    isvar=0
    if cdms.isVariable(t) :
        isvar=1
        ax=t.getAxisList()
    prob =_tprob(df,t)
    if isvar:
        prob = cdms.createVariable(prob,axes=ax,id='tprob',copy=0)
    ## in case we passed a Numeric
    if not MA.isMA(t):
        prob=prob.filled(1.e20)
    return prob
    
def _inversef(prob, df1, df2):
    """This function returns the f value for a given probability and 2 given
    degrees of freedom. It is an approximation using the fprob function.
    Adapted from Gary Perlmans critf function - apologies if copyright is 
    broken, but no copyright notice was attached """
    f_epsilon = 0.000001
    maxf = MA.ones(prob.shape)*9999.0
    minf = MA.zeros(prob.shape)
    c1=MA.logical_or(MA.less_equal(prob,0.),MA.greater_equal(prob,1.))
    c1=MA.logical_not(c1).filled(0) # Takes the oppsite, means can be set
    fval = MA.where(c1,1.0 / prob,0.)
    c2=MA.greater(MA.absolute(maxf-minf),f_epsilon)
    c2=MA.logical_and(c1,c2).filled(0)
    while not MA.allequal(c2,0.):
        c1=MA.less(_fprob(df1,df2,fval),prob).filled(0)
        maxf=MA.where(MA.logical_and(c1,c2).filled(0),fval,maxf)
        minf=MA.where(MA.logical_and(MA.logical_not(c1),c2).filled(0),fval,minf)
        fval = MA.where(c2,(maxf + minf) * 0.5,fval)
        c1=MA.greater(MA.absolute(maxf-minf),f_epsilon)
        c2=MA.logical_and(c1,c2).filled(0)
    return fval

def inversef(prob, df1, df2):
    """This function returns the f value for a given probability and 2 given
    degrees of freedom. It is an approximation using the fprob function.
    Adapted from Gary Perlmans critf function - apologies if copyright is 
    broken, but no copyright notice was attached
    Usage: fval = inversef(prob, df1, df2)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    prob = _fixScalar(prob)
    df1 = _fixScalar(df1)
    df2 = _fixScalar(df2)
    isvar=0
    if cdms.isVariable(prob) :
        isvar=1
        ax=prob.getAxisList()
    fval =_inversef(prob, df1, df2)
    if isvar:
        fval = cdms.createVariable(fval,axes=ax,id='inversef',copy=0)
    ## in case we passed a Numeric
    if not MA.isMA(prob):
        fval=fval.filled(1.e20)
    return fval

def _betacf(a,b,x,ITMAX=200,EPS=3.0E-7):
    """
    This function evaluates the continued fraction form of the incomplete
    Beta function, betai.  (Adapted from: MAal Recipies in C.)
    
    Usage:   _betacf(a,b,x,ITMAX=200,EPS=3.0E-7)
    ITMAX: Maximum number of iteration
    EPS: Epsilon number
    """
    a=MA.array(a,copy=0)
    bm = az = am = MA.ones(a.shape)
    qab = a+b
    qap = a+1.0
    qam = a-1.0
    bz = 1.0-qab*x/qap
    ans=MA.ones(a.shape)
    ans=MA.masked_equal(ans,1.)
    c1=MA.ones(a.shape)
    for i in range(ITMAX+1):
        em = float(i+1)
        tem = em + em
        d = em*(b-em)*x/((qam+tem)*(a+tem))
        ap = az + d*am
        bp = bz+d*bm
        d = -(a+em)*(qab+em)*x/((qap+tem)*(a+tem))
        app = ap+d*az
        bpp = bp+d*bz
        aold = az
        am = ap/bpp
        bm = bp/bpp
        az = app/bpp
        bz = 1.0
        c=MA.less(MA.absolute(az-aold),EPS*MA.absolute(az))
        c=MA.logical_and(c,c1)
        ans=MA.where(c,az,ans)
        c1=MA.logical_and(c1,MA.logical_not(c))
        if MA.allequal(c1,0):
            break
    return ans
    #print 'a or b too big, or ITMAX too small in Betacf.'

def betacf(a,b,x,ITMAX=200,EPS=3.0E-7):
    """
    This function evaluates the continued fraction form of the incomplete
    Beta function, betai.  (Adapted from: MAal Recipies in C.)
    
    Usage:   beta = betacf(a,b,x,ITMAX=200,EPS=3.0E-7)
    ITMAX: Maximum number of iteration
    EPS: Epsilon number
    """
    a = _fixScalar(a)
    b = _fixScalar(b)
    x = _fixScalar(x)
    isvar=0
    if cdms.isVariable(b) :
        isvar=1
        ax=b.getAxisList()
    if cdms.isVariable(a) :
        isvar=1
        ax=a.getAxisList()
    beta =_betacf(a,b,x,ITMAX,EPS)
    if isvar:
        beta = cdms.createVariable(beta,axes=ax,id='betacf',copy=0)
    ## in case we passed a Numeric
    if (not MA.isMA(a)) and (not MA.isMa(b)):
        beta=beta.filled(1.e20)
    return beta

def _gammaln(xx):
    """
    Returns the gamma function of xx.
    Gamma(z) = Integral(0,infinity) of t^(z-1)exp(-t) dt.
    (Adapted from: MAal Recipies in C.)

    Usage:   _gammaln(xx)
    """

    coeff = [76.18009173, -86.50532033, 24.01409822, -1.231739516,
                0.120858003e-2, -0.536382e-5]
    x = xx - 1.0
    tmp = x + 5.5
    tmp = tmp - (x+0.5)*MA.log(tmp)
    ser = 1.0
    for j in range(len(coeff)):
        x = x + 1
        ser = ser + coeff[j]/x
    return -tmp + MA.log(2.50662827465*ser)

def gamma(x):
    """
    Returns the gamma function of x.
    Gamma(z) = Integral(0,infinity) of t^(z-1)exp(-t) dt.
    (Adapted from: MAal Recipies in C.)

    Usage:   _gammaln(xx)
    """
    x = _fixScalar(x)
    isvar=0
    if cdms.isVariable(x) :
        isvar=1
        ax=x.getAxisList()
    g =_gammaln(x)
    if isvar:
        g = cdms.createVariable(g,axes=ax,id='gamma',copy=0)
    ## in case we passed a Numeric
    if not MA.isMA(x):
        g =g.filled(1.e20)
    return g
    
def _betai(a,b,x,ITMAX=200,EPS=3.0E-7):
    """
    Returns the incomplete beta function:

    I-sub-x(a,b) = 1/B(a,b)*(Integral(0,x) of t^(a-1)(1-t)^(b-1) dt)

    where a,b>0 and B(a,b) = G(a)*G(b)/(G(a+b)) where G(a) is the gamma
    function of a.  The continued fraction formulation is implemented here,
    using the betacf function.  (Adapted from: MAal Recipies in C.)

    Usage: b = _betai(a,b,x,ITMAX=200,EPS=3.0E-7)
    ITMAX: Maximum number of iteration for betacf
    EPS: Epsilon number
    """
    a=MA.array(a,copy=0)
    ans=MA.ones(a.shape)
    ans=MA.masked_equal(ans,1)

    c1=MA.logical_or(MA.equal(x,0),MA.equal(x,1.)).filled(0)
    ## Makes sure x is ok
    x=MA.masked_less_equal(x,0.)
    x=MA.masked_greater_equal(x,1.)
    ans=MA.where(c1,0.,ans)
    c1=MA.logical_not(c1)
    
    bt = MA.exp(_gammaln(a+b)-_gammaln(a)-_gammaln(b)+a*MA.log(x)+b*
                        MA.log(1.0-x))
    c2=MA.less(x,(a+1.0)/(a+b+2.0))
    ans=MA.where(MA.logical_and(c2,c1),bt*_betacf(a,b,x,ITMAX,EPS)/a,ans)
    ans=MA.where(MA.logical_and(MA.logical_not(c2),c1),1.0-bt*_betacf(b,a,1.0-x,ITMAX,EPS)/b,ans)
    return ans

def betai(a,b,x,ITMAX=200,EPS=3.0E-7):
    """
    Returns the incomplete beta function:

    I-sub-x(a,b) = 1/B(a,b)*(Integral(0,x) of t^(a-1)(1-t)^(b-1) dt)

    where a,b>0 and B(a,b) = G(a)*G(b)/(G(a+b)) where G(a) is the gamma
    function of a.  The continued fraction formulation is implemented here,
    using the betacf function.  (Adapted from: MAal Recipies in C.)

    Usage:  beta = betai(a,b,x,ITMAX=200,EPS=3.0E-7)
    ITMAX: Maximum number of iteration for betacf
    EPS: Epsilon number
    """
    a = _fixScalar(a)
    b = _fixScalar(b)
    x = _fixScalar(x)
    isvar=0
    if cdms.isVariable(x) :
        isvar=1
        ax=x.getAxisList()
    if cdms.isVariable(b) :
        isvar=1
        ax=b.getAxisList()
    if cdms.isVariable(a) :
        isvar=1
        ax=a.getAxisList()
    beta =_betai(a,b,x,ITMAX,EPS)
    if isvar:
        beta = cdms.createVariable(beta,axes=ax,id='betai',copy=0)
    ## in case we passed Numerics only
    if (not MA.isMA(a)) and (not MA.isMa(b)) and (not MA.isMa(x)):
        beta=beta.filled(1.e20)
    return beta

###########################
##      Test Classes     ##
###########################


    
def _sumsquares(data,axis=0):
    """Return the sum of the squares
    Usage:
    sq=sumsquare(data)
    """
    return MA.sum(data**2,axis=axis)

def sumsquares(x,axis=0):
    """Return the sum of the squares
    Usage:
        sq=sumsquare(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    sq=_sumsquares(x)
    if not ax is None:
        sq=cdms.createVariable(sq,axes=ax,id='sumsquares',copy=0)
        if 'units' in xatt.keys() : sq.units=xatt['units']+'*'+xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        sq=sq.filled(1.e20)
    return sq

def _Range(data):
    """Returns the range of the data
    Usage:
    rg=_Range(data)
    """
    return MA.maximum.reduce(data)-MA.minimum.reduce(data)

def Range(x,axis=0):
    """Returns the range of the data
    Usage:
        rg=Range(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_Range(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='range',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def harmonicmean(x,axis=0):
    """Returns the harmonicmean of the data
    Usage:
    h=harmonicmean(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_harmonicmean(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='harmonicmean',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _harmonicmean(data):
    """Returns the harmonicmean of the data
    Usage:
    h=_harmonicmean(data)
    """
    return 1./MA.average(1./data,axis=0)

def _median(data):
    """Not really sophisticated median, based of arrays dimension,
    Not to use with missing values
    Usage:
    med=_median(data)
    """
    N = data.shape[0]
    if (N % 2)==1:
        median = MA.sort(data,axis=0)[(N - 1) / 2]
    else:
        median = MA.sort(data,axis=0)[N / 2] # not ideal, but works"""
    return median

def median(x,axis=0):
    """Not really sophisticated median, based of arrays dimension,
    Not to use with missing values
    Usage:
    med=_median(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_median(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='median',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _medianranks(data):
    """ Return the ranks of the median
    Usage:
    medrk=_medianranks(data)
    """
    return _median(_rankdata(MA.sort(data,axis=0)))

def medianranks(x,axis=0):
    """ Return the ranks of the median
    Usage:
    medrk=medianranks(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_medianranks(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='medianranks',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _mad(data):
    """ return the sum of the deviation from the median
    Usage:
    md = mad(data)
    """
    return MA.sum(data-_median(data),axis=0)

def mad(x,axis=0):
    """ return the sum of the deviation from the median
    Usage:
    md=_mad(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_mad(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='mad',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _numberuniques(data):
    """Return the number of unique values
    Usage:
    uniques=numberuniques(data)
    """
    Uniques = MA.zeros(data.shape[1:])
    N=data.shape[0]
    for i in range(N):
        uniques = MA.ones(data.shape[1:])
        for j in range(N):
            if (i != j):
                uniques = MA.where(MA.equal(data[i],data[j]),0.,uniques)
        Uniques = MA.where(uniques,Uniques +1 ,Uniques)
    return Uniques

def numberuniques(x,axis=0):
    """Return the number of unique values
    Usage:
    uniques=numberuniques(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
   """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_numberuniques(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='mad',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _center(data):
    """Returns the deviation from the mean
    Usage:
    _centered=_center(data) # returns deviation from mean
    """
    state=MA.average(data,axis=0)
    return data-state

def center(x,axis=0):
    """Returns the deviation from the mean
    Usage:
    centered=center(data) # returns deviation from mean
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_center(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='center',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _ssdevs(data):
    """Return the sum of the square of the deviation from mean
    Usage:
    ss=_ssdevs(data)
    """
    return MA.sum(_center(data)**2,axis=0)

def ssdevs(x,axis=0):
    """Return the sum of the square of the deviation from mean
    Usage:
    ss=_ssdevs(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_ssdevs(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='ssdevs',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

## def _geometricmean(data):
##     """returns the geometric mean of the data, different form genutil !!!!
##     Usage:
##     g=geometricmean(data)
##     """
##     return reduce(MA.multiply, _center(data))

## def geometricmean(x,axis=0):
##     """returns the geometric mean of the data, different form genutil !!!!
##     Usage:
##     g=geometricmean(data)
##     Options:
##         axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
##         default value = 0. You can pass the name of the dimension or index
##         (integer value 0...n) over which you want to compute the statistic.
##         you can also pass 'xy' to work on both axes at once
##     """
##     if cdms.isVariable(x) : xatt=x.attributes
##     x,y,weights,axis,ax=__checker(x,None,None,axis)
    
##     out=_geometricmean(x)
##     if not ax is None:
##         out=cdms.createVariable(out,axes=ax,id='geometricmean',copy=0)
##         if 'units' in xatt.keys() : out.units=xatt['units']+'*'+xatt['units']
##     ## Numerics only ?
##     if not MA.isMA(x):
##         out=out.filled(1.e20)
##     return out

def _samplevariance(data):
    """Return the variance (Ssq/(N-1))
    Usage:
    svar=_samplevariance(data)
    """
    return _ssdevs(data)/(MA.count(data,axis=0)-1.)

def unbiasedvariance(x,axis=0):
    """Return the variance (Ssq/(N-1))
    Usage:
    svar=unbiasedvariance(x,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_samplevariance(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='unbiasedvariance',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']+'*'+xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _variance(data):
    """Return the variance of data
    Usage:
    V=_variance(data)
    """
    return MA.average(_center(data)**2,axis=0)

def variance(x,axis=0):
    """Return the variance of data
    Usage:
    V=variance(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_variance(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='variance',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']+'*'+xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _standarddeviation(data):
    """Returns stadard deviation of data
    Usage:
    std=_standarddeviation(data)
    """
    return MA.sqrt(_samplevariance(data),axis=0)

def standarddeviation(x,axis=0):
    """Returns stadard deviation of data
    Usage:
    std=standarddeviation(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_standarddeviation(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='standarddeviation',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']+'*'+xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out


def _coefficentvariance(data):
    """Returns the coefficents variance of data
    Usage:
    coefvar=_coefficentvariance(data)
    """
    return _standarddeviation(data)/MA.average(data,axis=0)

def coefficentvariance(x,axis=0):
    """Returns the coefficents variance of data
    Usage:
    coefvar=coefficentvariance(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_coefficentvariance(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='coefficentvariance',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _skewness(data):
    """Return the skewness of data
    Usage:
    skew=_skewness(data)
    """
    moment2=_variance(data)
    moment3=mean(MA.power(_center(data),3))
    return moment3 / (moment2 * MA.sqrt(moment2))

def skewness(x,axis=0):
    """Return the skewness of data
    Usage:
    skew=skewness(data, axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_skewness(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='skewness',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _kurtosis(data):
    """Return kurtosis value from dataset
    Usage:
    k=_kurtosis(data)
    """
    moment2=_variance(data)
    moment4=mean(MA.power(_center(data),4),axis=0)
    return (moment4 / MA.power(moment2, 2)) - 3.0

def kurtosis(x,axis=0):
    """Return kurtosis value from dataset
    Usage:
    k=kurtosis(data, axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_kurtosis(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='kurtosis',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _standarderror(data):
    """Returns the standard error from dataset
    Usage:
    stderr=_standarderror(data)
    """
    return _standarddeviation(data)/MA.sqrt(MA.count(data,axis=0),axis=0)

def standarderror(x,axis=0):
    """Returns the standard error from dataset
    Usage:
    stderr=standarderror(data,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_standarderror(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='standarderror',copy=0)
        if 'units' in xatt.keys() : out.units=xatt['units']+'*'+xatt['units']
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _mode(data):
    """returns the mode of the data
    Usage:
    md=_mode(data)
    """
    sortlist=MA.sort(data,axis=0)
    mode=sortlist[0]
    dupcount=MA.zeros(mode.shape)
    dupmax=MA.zeros(mode.shape)
    N=data.shape[0]
    for i in range(1,N):
        c=MA.equal(sortlist[i],sortlist[i-1])
        dupcount=MA.where(c,dupcount+1,0.)
        c2=MA.greater(dupcount,dupmax)
        dupmax=MA.where(c2,dupcount,dupmax)
        mode=MA.where(c2,sortlist[i],mode)
    return mode

def mode(x,axis=0):
    """returns the mode of the data
    Usage:
    md=mode(data, axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,None,None,axis)
    
    out=_mode(x)
    if not ax is None:
        out=cdms.createVariable(out,axes=ax,id='kurtosis',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        out=out.filled(1.e20)
    return out

def _OneSampleTTest(data, usermean):
    """
    This performs a single factor t test for a set of data and a user
    hypothesised mean value.
    Usage: t, df = OneSampleTTest(data, usermean)
    Returns: t, df (degrees of freedom), prob (probability)
    """
    df=MA.count(data,axis=0)-1
    svar = (df * _samplevariance(data)) / df
    t = (mean(data) - usermean) / MA.sqrt(svar*(1.0/(df+1.)))
    prob = _betai(0.5*df,0.5,df/(df+ t**2))
    return t,df,prob

def OneSampleTTest(x,y,axis=0,df=1):
    """
    This performs a single factor t test for a set of data and a user
    hypothesised mean value.
    Usage: t, prob [,df] = OneSampleTTest(data, usermean, axis=axisoptions, df=1)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
                
        df=1 : If set to 1 then the degrees of freedom are returned
        
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis,smally=1)
    t,d,prob =_OneSampleTTest(x,y)
    if not ax is None:
        t=cdms.createVariable(t,axes=ax,id='TTest',copy=0)
        d=cdms.createVariable(d,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        t=t.filled(1.e20)
        d=d.filled(1.e20)
        prob=prob.filled(1.e20)
    out=[t,prob]
    if df:
        out.append(d)
    return out

def _OneSampleSignTest(data, usermean):
    """
    This method performs a single factor sign test. The data must be 
    supplied to this method along with a user hypothesised mean value.
    Usage: nplus, nminus, ntotal, z, prob = OneSampleSignTest(data, usermean)
    Returns: nplus, nminus, z, prob.
    """
    nplus=MA.zeros(data.shape[1:])
    nminus=MA.zeros(data.shape[1:])
    for i in range(data.shape[0]):
        c=MA.less(data[i],usermean)
        nplus=MA.where(c,nplus+1,nplus)
        c=MA.greater(data[i],usermean)
        nminus=MA.where(c,nminus+1,nminus)
    ntotal = add(nplus, nminus)
    z=(nplus-(ntotal/2)/MA.sqrt(ntotal/2))
    prob=_erfcc(MA.absolute(z) / MA.sqrt(2))
    return nplus,nminus,ntotal,z,prob

def OneSampleSignTest(x,y,axis=0):
    """
    OneSampleSignTest
    This method performs a single factor sign test. The data must be 
    supplied to this method along with a user hypothesised mean value.
    Usage:
    nplus, nminus, z, prob = OneSampleSignTest(data, usermean, axis=axisoptions)
    Returns: nplus, nminus, z, prob.
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis,smally=1)
    nplus, nminus, ntotal, z, prob =_OneSampleSignTest(x,y)
    if not ax is None:
        z=cdms.createVariable(z,axes=ax,id='z',copy=0)
        nminus=cdms.createVariable(nminus,axes=ax,id='nminus',copy=0)
        nplus=cdms.createVariable(nplus,axes=ax,id='nplus',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        z=z.filled(1.e20)
        nplus=nplus.filled(1.e20)
        nminus=nminus.filled(1.e20)
        prob=prob.filled()
    return nplus, nminus, ntotal, z, prob


def _ChiSquareVariance(data, usermean):
    """
    This method performs a Chi Square test for the variance ratio.
    Usage: chisquare, df, prob = ChiSquareVariance(data, usermean)
    Returns: chisquare, df, prob
    """
    df = MA.count(data,axis=0) - 1
    chisquare = (_standarderror(data) / usermean) * df
    prob = _chisqprob(chisquare, df)
    return chisquare, df, prob

def ChiSquareVariance(x,y,axis=0, df=1):
    """
    This method performs a Chi Square test for the variance ratio.
    Usage:
       chisquare, prob, [df] = ChiSquareVariance(data, usermean, axis=axisoptions, df=1)
    Returns: chisquare, prob, [df] = 
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis,smally=1)
    chisquare, Df, prob =_ChiSquareVariance(x,y)
    if not ax is None:
        chisquare = cdms.createVariable(chisquare,axes=ax,id='chisquare',copy=0)
        Df=cdms.createVariable(Df,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        chisquare=chisquare.filled(1.e20)
        Df=Df.filled(1.e20)
        prob=prob.filled()
    out=[chisquare, prob]
    if df:
        out.append(Df)
    return out

# two sample tests - instantiates descriptives class for both
# data sets, then has each test as a method


def _TTestUnpaired(data1, data2):
    """
    This performs an unpaired t-test.
    Usage: t, df, prob = TTestUnpaired(data1, data2)
    Returns: t, df, prob
    """
    N1s=MA.count(data1,axis=0)
    N2s=MA.count(data2,axis=0)
    df = (N1s + N2s) - 2
    svar = ((N1s-1)*_samplevariance(data1)+\
            (N2s-1)*_samplevariance(data2)) / df
    
    t = (mean(data1)-mean(data2)) \
        / MA.sqrt(svar* (1.0/N1s + 1.0/N2s))
    
    prob = _betai(0.5*df,0.5,df/(df+t**2))
    return t, df, prob

def TTestUnpaired(x,y,axis=0,df=1):
    """
    This performs an unpaired t-test.
    Usage: t, prob, [df] = TTestUnpaired(data1, data2,axis=axisoptions, df=1)
    Returns: t, df, prob
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

        df =0: if set to 1 returns degrees of freedom
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    t, Df, prob =_TTestUnpaired(x,y)
    if not ax is None:
        t = cdms.createVariable(t,axes=ax,id='TTestUnpaired',copy=0)
        Df=cdms.createVariable(Df,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        t=t.filled(1.e20)
        Df=Df.filled(1.e20)
        prob=prob.filled()
    out=[t, prob]
    if df:
        out.append(Df)
    return out

def _TTestPaired(data1, data2):
    """
    This method performs a paired t-test on two data sets.
    Usage: t, df, prob = TTestPaired(data1, data2)
    Returns: t, df, prob
    """
    cov = 0.0
    N1s=MA.count(data1,axis=0)

    df = N1s - 1
    cov=MA.sum((_center(data1) * _center(data2)), axis=0)
    cov = cov / df
    sd = MA.sqrt((_samplevariance(data1) + _samplevariance(data2) - 2.0 * \
                            cov) / N1s)
    t = (mean(data1, axis=0) - mean(data2, axis=0)) / sd
    prob = _betai(0.5*df,0.5,df/(df+ t**2))
    return t, df, prob

def TTestPaired(x,y,axis=0,df=1):
    """
    This performs an paired t-test.
    Usage: t, prob, [df] = TTestUnpaired(data1, data2,axis=axisoptions, df=1)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

        df =0: if set to 1 returns degrees of freedom
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    t, Df, prob =_TTestPaired(x,y)
    if not ax is None:
        t = cdms.createVariable(t,axes=ax,id='TTestPaired',copy=0)
        Df=cdms.createVariable(Df,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        t=t.filled(1.e20)
        Df=Df.filled(1.e20)
        prob=prob.filled()
    out=[t, prob]
    if df:
        out.append(Df)
    return out

def _PearsonsCorrelation(data1, data2):
    """
    This method performs a Pearsons correlation upon two sets of data
    Usage: r, t, df, prob = PearsonsCorrelation(data1, data2)
    Returns: r, t, df, prob
    """
    TINY = 1.0e-60
    summult = reduce(add, map(multiply, data1, data2))
    N1=MA.count(data1,axis=0)
    N2=MA.count(data2,axis=0)
    s1=MA.sum(data1,axis=0)
    s2=MA.sum(data2,axis=0)
    r_num = N1 * summult - s1 * s2
    r_left = N1*_sumsquares(data1)-(s1**2)
    r_right= N2*_sumsquares(data2)-(s2**2)
    r_den = MA.sqrt(r_left*r_right)
    r = r_num / r_den
    df = N1 - 2
    t = r*MA.sqrt(df/((1.0-r+TINY)* (1.0+r+TINY)))
    prob = _betai(0.5*df,0.5,df/(df+t**2))
    return r, t, df, prob

def PearsonsCorrelation(x,y,axis=0,df=1):
    """
    This method performs a Pearsons correlation upon two sets of data
    Usage: r, t, prob, [df] = PearsonsCorrelation(data1, data2,axis=0,df=1)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

        df =0: if set to 1 returns degrees of freedom
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    r, t, Df, prob =_PearsonsCorrelation(x,y)
    if not ax is None:
        r = cdms.createVariable(r,axes=ax,id='PearsonsCorrelation',copy=0)
        t = cdms.createVariable(t,axes=ax,id='TTest',copy=0)
        Df=cdms.createVariable(Df,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        r=r.filled(1.e20)
        t=t.filled(1.e20)
        Df=Df.filled(1.e20)
        prob=prob.filled()
    out=[r, t, prob]
    if df:
        out.append(Df)
    return out


def _FTest(data1, data2, uservar):
    """
    This method performs a F test for variance ratio and needs a user 
    hypothesised variance to be supplied.
    Usage: f, df1, df2, prob = FTest(uservar)
    Returns: f, df1, df2, prob
    """
    f = (_samplevariance(data1) / _samplevariance(data2)) / uservar
    df1 = MA.count(data1,axis=0) - 1
    df2 = MA.count(data2,axis=0) - 1
    prob=_fprob(df1, df2, f)
    return f, df1, df2, prob

def FTest(data1, data2, uservar, axis=0, df=1):
    """
    This method performs a F test for variance ratio and needs a user 
    hypothesised variance to be supplied.
    Usage: f, prob [,df1, df2] = FTest(data1, data2, uservar, axis=axisoptions, df=1)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

        df =0: if set to 1 returns degrees of freedom
    """
    data1 = _fixScalar(data2)
    data2 = _fixScalar(data2)
    x,y,weights,axis,ax=__checker(data1,data2,None,axis)
    x,z,weights,axis,ax=__checker(data1,uservar,None,axis,smally=1)
    f, df1, df2, prob = _FTest(x,y,z)
    if not ax is None:
        f = cdms.createVariable(f,axes=ax,id='Ftest',copy=0)
        df1=cdms.createVariable(df1,axes=ax,id='df1',copy=0)
        df2=cdms.createVariable(df2,axes=ax,id='df2',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        t=t.filled(1.e20)
        df1=df1.filled(1.e20)
        df2=df2.filled(1.e20)
        prob=prob.filled()
    out=[f, prob]
    if df:
        out.append(df1)
        out.append(df2)
    return out

def _TwoSampleSignTest(data1, data2):
    """
    This method performs a 2 sample sign test for matched samples on 2 
    supplied data sets
    Usage: nplus, nminus, ntotal, z, prob = TwoSampleSignTest(data1, data2)
    Returns: nplus, nminus, ntotal, z, prob
    """
    nplus=MA.zeros(data1.shape[1:])
    nminus=MA.zeros(data1.shape[1:])
    for i in range(data1.shape[0]):
        c=MA.greater(data1[i],data2[i])
        nplus=MA.where(c,nplus+1,nplus)
        c=MA.less(data1[i],data2[i])
        nminus=MA.where(c,nminus+1,nminus)

    ntotal=nplus-nminus
    mean=MA.count(data1,axis=0) / 2
    sd = MA.sqrt(mean)
    z = (nplus-mean)/sd
    prob = _erfcc(MA.absolute(z)/MA.sqrt(2.))
    return nplus, nminus, ntotal, z, prob

def TwoSampleSignTest(x,y,axis=0):
    """
    This method performs a 2 sample sign test for matched samples on 2 
    supplied data sets
    Usage: nplus, nminus, ntotal, z, prob = TwoSampleSignTest(data1, data2)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    nplus,nminus,ntotal,z, prob = _TwoSampleSignTest(x,y)
    if not ax is None:
        z=cdms.createVariable(z,axes=ax,id='z',copy=0)
        nminus=cdms.createVariable(nminus,axes=ax,id='nminus',copy=0)
        nplus=cdms.createVariable(nplus,axes=ax,id='nplus',copy=0)
        ntotal=cdms.createVariable(ntotal,axes=ax,id='ntotal',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        z=z.filled(1.e20)
        nplus=nplus.filled(1.e20)
        nminus=nminus.filled(1.e20)
        ntotal=ntotal.filled(1.e20)
        prob=prob.filled()
    return nplus,nminus,ntotal,z,prob

def _KendallsTau(data1, data2):
    """
    This method performs a Kendalls tau correlation upon 2 data sets.
    Usage: tau, z, prob = KendallsTau(data1, data2)
    Returns: tau, z, prob
    """
    n1 = MA.zeros(data1.shape[1:])
    n2 = MA.zeros(data1.shape[1:])
    iss = MA.zeros(data1.shape[1:])
    N1=data1.shape[0]
    N2=data2.shape[0]
    for j in range(N1-1):
        for k in range(j,N2):
            a1 = data1[j] - data1[k]
            a2 = data2[j] - data2[k]
            aa = a1 * a2
            c=MA.not_equal(aa,0)
            c2=MA.greater(aa,0)
            n1=MA.where(c,n1+1,n1)
            n2=MA.where(c,n2+1,n2)
            iss=MA.where(c2,iss+1,iss)
            c2=MA.less(aa,0)
            iss=MA.where(c2,iss-1,iss)
            c=MA.logical_not(c)
            c1=MA.logical_and(c,MA.not_equal(a1,0))
            n1=MA.where(c1,n1+1,n1)
            c1=MA.logical_and(c,MA.equal(a1,0))
            n2=MA.where(c1,n2+1,n2)
    tau = iss / MA.sqrt(n1*n2)
    N1s=MA.count(data1,axis=0)
    svar = (4.0*N1s+10.0) / (9.0*N1s*(N1s-1))
    z = tau / MA.sqrt(svar)
    prob = _erfcc(MA.absolute(z)/MA.sqrt(2.))
    return tau, z, prob

def KendallsTau(x,y,axis=0):
    """
    This method performs a Kendalls tau correlation upon 2 data sets.
    Usage: tau, z, prob = KendallsTau(data1, data2)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    tau, z, prob = _KendallsTau(x,y)
    if not ax is None:
        z=cdms.createVariable(z,axes=ax,id='z',copy=0)
        tau=cdms.createVariable(tau,axes=ax,id='tau',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        z=z.filled(1.e20)
        tau=tau.filled(1.e20)
        prob=prob.filled()
    return tau ,z,prob

def _KolmogorovSmirnov(data1,data2):
    """
    This method performs a Kolmogorov-Smirnov test for unmatched samples
    upon 2 data vectors.
    Usage: d, prob = KolmogorovSmirnov(data1, data2)
    Returns: d, prob
    """
    data3 = MA.sort(data1,axis=0)
    data4 = MA.sort(data2,axis=0)
    j1 = MA.zeros(data3.shape[1:],'d')
    j2 = MA.zeros(data3.shape[1:],'d')
    fn1 = MA.zeros(data3.shape[1:],'d')
    fn2 = MA.zeros(data3.shape[1:],'d')
    d = MA.zeros(data3.shape[1:],'d')
    N1s=MA.count(data1,axis=0)
    N2s=MA.count(data2,axis=0)
    c1=N1s-j1
    c2=N2s-j2
    cc=c1-c1
    while not MA.allequal(cc,1):
        tmpc=MA.less(j1,N1s)
        jj=MA.where(MA.less(j1,N1s),j1,N1s-1.)
        d1=array_indexing.extract(data3,jj)
        jj=MA.where(MA.less(j2,N2s),j2,N2s-1.)
        d2=array_indexing.extract(data4,jj)
        c3=MA.logical_and(MA.less_equal(d1,d2),MA.less(j1,N1s))
        fn1=MA.where(c3,j1/N1s,fn1)
        j1=MA.where(c3,j1+1,j1)
        c3=MA.logical_and(MA.less_equal(d2,d1),MA.less(j2,N2s))
        fn2=MA.where(c3,j2/N2s,fn2)
        j2=MA.where(c3,j2+1,j2)
        dt = fn2-fn1
        c3=MA.greater(MA.absolute(dt),MA.absolute(d))
        d=MA.where(c3,dt,d)
        c1=N1s-j1
        c2=N2s-j2
        cc1=MA.equal(c1,0)
        cc2=MA.equal(c2,0)
        cc=MA.logical_or(cc1,cc2)
    en = MA.sqrt(N1s*N2s/(N1s.astype('d')+N2s))
    prob = _ksprob((en+0.12+0.11/en)*MA.absolute(d))
    return d, prob

def KolmogorovSmirnov(x,y,axis=0):
    """
    This method performs a Kolmogorov-Smirnov test for unmatched samples
    upon 2 data vectors.
    Usage: ks, prob = KolmogorovSmirnov(data1, data2)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    d, prob = _KolmogorovSmirnov(x,y)
    if not ax is None:
        d=cdms.createVariable(d,axes=ax,id='KSTest',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        d=d.filled(1.e20)
        prob=prob.filled()
    return d,prob

def _SpearmansCorrelation(data1, data2):
    """
    This method performs a Spearmans correlation upon 2 data sets
    Usage: rho, t, df, prob = SpearmansCorrelation(data1, data2)
    Returns: rho, t, df, prob
    """
    TINY = 1e-30
    rankx = _rankdata(data1)
    ranky = _rankdata(data2)
    dsq = MA.sum(map(_diffsquared, rankx, ranky),axis=0)
    N1=MA.count(data1,axis=0)
    rho = 1 - 6*dsq / (N1*(N1**2-1.))
    t = rho * MA.sqrt((N1-2) / ((rho+1.0+TINY)*(1.0-rho+TINY)))
    df = N1-2
    prob = _betai(0.5*df,0.5,df/(df+t**2))
    return rho, t, df, prob

def SpearmansCorrelation(x,y,axis=0,df=1):
    """
    This method performs a Spearmans correlation upon 2 data sets
    Usage: rho, t, df, prob = SpearmansCorrelation(data1, data2, axis=0, df=1)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

        df=1 : If set to 1 returns the degrees of freedom
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    rho, t, d, prob = _SpearmansCorrelation(x,y)
    if not ax is None:
        rho=cdms.createVariable(rho,axes=ax,id='SpearmansCorrelation',copy=0)
        t=cdms.createVariable(t,axes=ax,id='t',copy=0)
        d=cdms.createVariable(d,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        d=d.filled(1.e20)
        t=t.filled()
        rho=rho.filled()
        prob=prob.filled()
    out=[rho,t,prob]
    if df:
        out.append(d)
    return out


def _WilcoxonRankSums(data1, data2, Z_MAX = 6.0):
    """
    This method performs a Wilcoxon rank sums test for unpaired designs 
    upon 2 data vectors.
    Usage: z, prob = WilcoxonRankSums(data1, data2, Z_MAX = 6.0)
    Returns: z, prob
    """
    N=data1.shape[0]
    alldata = MA.concatenate((data1,data2),axis=0)
    ranked = _rankdata(alldata)
    x = ranked[:N]
    s = MA.sum(x, axis=0)
    N1=MA.count(data1,axis=0)
    N2=MA.count(data2,axis=0)
    expected = N1*(N1+N2+1) / 2.0
    z = (s - expected) / MA.sqrt(N1*N2 * (N2+N2+1.)/12.0)
    prob = 2*(1.0 -_zprob(MA.absolute(z),Z_MAX))
    return z, prob

def WilcoxonRankSums(x,y, Z_MAX = 6.0, axis=0):
    """
    This method performs a Wilcoxon rank sums test for unpaired designs 
    upon 2 data vectors.
    Usage: z, prob = WilcoxonRankSums(data1, data2, Z_MAX = 6.0, axis=axisoption)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

        Z_MAX: Maximum meaningfull value  for z probability (default = 6)
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x1,y,weights,axis,ax=__checker(x,y,None,axis)
    if MA.isMA(Z_MAX):
        x,Z_MAX,weights,axis,ax=__checker(x,Z_MAX,None,axis)
    
    z, prob = _WilcoxonRankSums(x1,y,Z_MAX)
    if not ax is None:
        z=cdms.createVariable(z,axes=ax,id='WilcoxonRankSumsTest',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        z=z.filled(1.e20)
        prob=prob.filled()
    return z,prob

def _WilcoxonSignedRanks(data1, data2, Z_MAX=6.):
    """
    This method performs a Wilcoxon Signed Ranks test for matched samples 
    upon 2 data set.
    Usage: wt, z, prob = WilcoxonSignedRanks(data1, data2, Z_MAX = 6.0)
    Returns: wt, z, prob
    """
    N=data1.shape[0]
    d=data1-data2[:N]
    d=MA.masked_equal(d,0.)
    count = MA.count(d,axis=0)
    absd = MA.absolute(d)
    absranked = _rankdata(absd.filled(1.E20))
    r_plus = MA.zeros(d.shape[1:])
    r_minus = MA.zeros(d.shape[1:])
    for i in range(len(absd)):
        c=MA.less(d[i],0.)
        r_minus=MA.where(c,r_minus + absranked[i],r_minus)
        r_plus=MA.where(MA.logical_not(c),r_plus + absranked[i],r_plus)
    wt = MA.where(MA.greater(r_plus,r_minus),r_minus,r_plus)
    mn = count * (count+1) * 0.25
    se =  MA.sqrt(count*(count+1)*(2.0*count+1.0)/24.0)
    z = MA.absolute(wt-mn) / se
    prob = 2*(1.0 -_zprob(MA.absolute(z),Z_MAX))
    return wt, z, prob


def WilcoxonSignedRanks(x,y, Z_MAX=6., axis=0):
    """
    This method performs a Wilcoxon Signed Ranks test for matched samples 
    upon 2 data set.
    Usage: wt, z, prob = WilcoxonSignedRanks(data1, data2, Z_MAX = 6.0, axis=0)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

        Z_MAX: Maximum meaningfull value  for z probability (default = 6)
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x1,y,weights,axis,ax=__checker(x,y,None,axis)
    if MA.isMA(Z_MAX):
        x,Z_MAX,weights,axis,ax=__checker(x,Z_MAX,None,axis)
    wt, z, prob = _WilcoxonSignedRanks(x1,y,Z_MAX)
    if not ax is None:
        wt=cdms.createVariable(wt,axes=ax,id='W',copy=0)
        z=cdms.createVariable(z,axes=ax,id='Z',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        wt=wt.filled(1.e20)
        z=z.filled(1.e20)
        prob=prob.filled()
    return wt,z,prob

def _MannWhitneyU(data1, data2, Z_MAX=6.0):
    """
    This method performs a Mann Whitney U test for unmatched samples on
    2 data vectors.
    Usage: bigu, smallu, z, prob = MannWhitneyU(data1, data2, Z_MAX=6.0)
    Returns: bigu, smallu, z, prob
    """
    N=data1.shape[0]
    N1=MA.count(data1,axis=0)
    N2=MA.count(data2,axis=0)
    ranked = _rankdata(MA.concatenate((data1,data2),axis=0))
    rankx = ranked[0:N]
    u1 = N1*N2+(N1*(N1+1))/2.0-MA.sum(rankx,axis=0)
    u2 = N1*N2 - u1
    bigu = MA.maximum(u1,u2)
    smallu = MA.minimum(u1,u2)
    T = MA.sqrt(_tiecorrect(ranked))
    sd = MA.sqrt(T*N1*N2*(N1+N2+1)/12.0)
    z = MA.absolute((bigu-N1*N2/2.0) / sd)
    prob = 1.0-_zprob(z,Z_MAX)
    return bigu, smallu, z, prob

def MannWhitneyU(x, y, Z_MAX=6.0, axis=0):
    """
    This method performs a Mann Whitney U test for unmatched samples on
    2 data vectors.
    Usage: bigu, smallu, z, prob = MannWhitneyU(data1, data2, Z_MAX=6.0, axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

        Z_MAX: Maximum meaningfull value  for z probability (default = 6)
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x1,y,weights,axis,ax=__checker(x,y,None,axis)
    if MA.isMA(Z_MAX):
        x,Z_MAX,weights,axis,ax=__checker(x,Z_MAX,None,axis)
    bigu, smallu, z, prob = _MannWhitneyU(x1,y,Z_MAX)
    if not ax is None:
        bigu=cdms.createVariable(bigu,axes=ax,id='bigU',copy=0)
        smallu=cdms.createVariable(smallu,axes=ax,id='smallU',copy=0)
        z=cdms.createVariable(z,axes=ax,id='z',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        bigu=bigu.filled(1.e20)
        smallu=smallu.filled(1.e20)
        z=z.filled(1.e20)
        prob=prob.filled()
    return bigu, smallu, z, prob

def _LinearRegression(x, y):
    """
    This method performs a linear regression upon 2 data vectors.
    Usage:  r, df, t, prob, slope, intercept, sterrest = LinearRegression(x,y)
    Returns: r, df, t, prob, slope, intercept, sterrest
    """
    TINY = 1.0e-20
    summult = MA.sum(x*y,axis=0)
    N1=MA.count(x,axis=0)
    N2=MA.count(y,axis=0)
    s1=MA.sum(x,axis=0)
    s2=MA.sum(y,axis=0)
    sq1=_sumsquares(x)
    r_num = N1*summult - s1*s2
    r_den = MA.sqrt((N1*sq1 - (s1**2))*(N2*_sumsquares(y) - (s2**2)))
    r = r_num / r_den
    #[] warning - z not used - is there a line missing here?
##         z = 0.5*math.log((1.0+self.r+TINY)/(1.0-self.r+TINY))
    df = N1 - 2
    t = r*MA.sqrt(df/((1.0-r+TINY)*(1.0+ r+TINY)))
    prob = _betai(0.5*df,0.5,df/(df+t**2))
    slope = r_num / (N1*sq1 - (s1**2))
    intercept = mean(y, axis=0) - slope*mean(x, axis=0)
    sterrest = MA.sqrt(1-r**2)*MA.sqrt(_variance(y))
    return  r, df, t, prob, slope, intercept, sterrest

def LinearRegression(x, y, df=1, axis=0):
    """
    This method performs a linear regression upon 2 data vectors.
    Usage:  r, t, prob, slope, intercept, sterrest [,df] = LinearRegression(x,y,df=1,axis=axisoptions)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once

        df=1: If set to 1 then df is returned
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    r, d, t, prob, slope, intercept, sterrest = _LinearRegression(x,y)
    if not ax is None:
        r=cdms.createVariable(r,axes=ax,id='r',copy=0)
        d=cdms.createVariable(d,axes=ax,id='df',copy=0)
        t=cdms.createVariable(t,axes=ax,id='t',copy=0)
        slope=cdms.createVariable(slope,axes=ax,id='slope',copy=0)
        intercept=cdms.createVariable(intercept,axes=ax,id='intercept',copy=0)
        sterrest=cdms.createVariable(sterrest,axes=ax,id='standarderror',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        r=r.filled(1.e20)
        t=t.filled(1.e20)
        slope=slope.filled(1.e20)
        intercept=intercept.filled(1.e20)
        sterrest=sterrest.filled(1.e20)
        d=d.filled(1.e20)
        prob=prob.filled()
    out = [ r, t, prob, slope, intercept, sterrest]
    if df:
        out.append(d)
    return out

def _PairedPermutation(x, y, nperm=None):
    """
    This method performs a permutation test for matched samples upon 2 set
     This code was modified from Segal and further modifed by C. Doutriaux
    Usage: utail, crit, prob = PairedPermutation(x,y,nperm=None)
    nperm is the number of permutation wanted, default len(x)+1
    Returns: utail, crit, prob
    """
    utail = MA.zeros(x.shape[1:],'d')
    sh=list(x.shape)
    sh.insert(0,1)
    ## Figures out how many permutation we want to do
    if nperm is None:
        nperm = x.shape[0]+1
    xy=MA.resize(x-y,sh)
    yx=MA.resize(y-x,sh)
    xy=MA.concatenate((xy,yx),axis=0)
    crit = MA.sum(xy[0],axis=0)

    for i in range(nperm):
        #index=RandomArray.randint(0,2,x.shape)
        index=numpy.random.randint(0,2,x.shape)
        tmp=array_indexing.extract(xy,index)
        sum=MA.sum(tmp,axis=0)
        utail=MA.where(MA.greater_equal(sum,crit),utail+1.,utail)
    prob = utail / nperm
    return utail, crit, prob

def PairedPermutation(x, y, nperm=None, axis=0):
    """
    This method performs a permutation test for matched samples upon 2 set
     This code was modified from Segal and further modifed by C. Doutriaux
    Usage: utail, crit, prob = PairedPermutation(x,y,nperm=None)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
        nperm is the number of permutation wanted, default len(axis)+1
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    utail, crit, prob = _PairedPermutation(x,y,nperm)
    if not ax is None:
        utail=cdms.createVariable(utail,axes=ax,id='utail',copy=0)
        crit=cdms.createVariable(crit,axes=ax,id='crit',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        crit=crit.filled(1.e20)
        utail=utail.filled(1.e20)
        prob=prob.filled(1.e20)
    return utail, crit, prob

##     def PointBiserialr(self, x, y):
##         TINY = 1e-30
##         if len(x) <> len(y):
##             return -1.0, -1.0
##         data = pstat.abut(x,y) # [] pstat module not available!
##         categories = pstat.unique(x)
##         if len(categories) <> 2:
##             return -1.0, -2.0
##         else:   # [] there are 2 categories, continue
##             codemap = pstat.abut(categories,range(2))
##             recoded = pstat.recode(data,codemap,0) # [] can prob delete this line
##             x = pstat.linexand(data,0,categories[0])
##             y = pstat.linexand(data,0,categories[1])
##             xmean = mean(pstat.colex(x,1)) # [] use descriptives!
##             ymean = mean(pstat.colex(y,1)) # [] use descriptives!
##             n = len(data)
##             adjust = math.sqrt((len(x)/float(n))*(len(y)/float(n)))
##             rpb = (ymean - xmean)/samplestdev(pstat.colex(data,1))*adjust
##             df = n-2
##             t = rpb*math.sqrt(df/((1.0-rpb+TINY)*(1.0+rpb+TINY)))
##             prob = _betai(0.5*df,0.5,df/(df+t*t))  # t already a float
##             return rpb, prob

def _ChiSquare(x, y):
    """
    This method performs a chi square on 2 data set.
    Usage: chisq, df, prob = ChiSquare(x,y)
    Returns: chisq, df, prob
    """
    df = MA.count(x,axis=0)
    chisq=MA.sum((x-y)**2/y,axis=0)
    prob = _chisqprob(chisq, df)
    return chisq, df, prob

def ChiSquare(x, y, axis=0, df=1):
    """
    This method performs a chi square on 2 data set.
    Usage: chisq, df, prob = ChiSquare(x,y)
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
        nperm is the number of permutation wanted, default len(axis)+1
    """
    x = _fixScalar(x)
    y = _fixScalar(y)
    if cdms.isVariable(x) : xatt=x.attributes
    if cdms.isVariable(y) : yatt=y.attributes
    x,y,weights,axis,ax=__checker(x,y,None,axis)
    chisq, d, prob = _ChiSquare(x,y)
    if not ax is None:
        chisq=cdms.createVariable(chisq,axes=ax,id='chisq',copy=0)
        d=cdms.createVariable(d,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
    ## Numerics only ?
    if not MA.isMA(x):
        chisq=chisq.filled(1.e20)
        d=d.filled(1.e20)
        prob=prob.filled(1.e20)
    out=[chisq,prob]
    if df:
        out.append(d)
    return out

## 2 or more datasets from here
def pack(arrays):
    """ Pack a list of arrays into one array
    """
    k=len(arrays)
    sh=list(arrays[0].shape)
    sh.insert(0,k)
    data=MA.zeros(sh,dtype='d')
    for i in range(k):
        data[i]=arrays[i]
    return data
    
def _anovaWithin( *inlist):
    """
    This method is specialised for SalStat, and is best left alone. 
    For the brave:
    Usage:
    SSint, SSres, SSbet, SStot, dfbet, dfwit, dfres, dftot, MSbet, MSwit, MSres, F, prob = anovaWithin(*inlist).
    inlist, being as many arrays as you  wish
    """
    inlist=pack(inlist)
    k = inlist.shape[0]
    sums=MA.sum(inlist,axis=1)
    Nlist=MA.count(inlist,axis=1)
    meanlist=MA.average(inlist,axis=1)

    GN=MA.sum(Nlist,axis=0)
    GS=MA.sum(sums,axis=0)
    GM=MA.average(meanlist,axis=0)

    SSwit=inlist-meanlist[:,None,...]
    SSwit=MA.sum(SSwit**2,axis=0)
    SSwit=MA.sum(SSwit,axis=0)
    SStot=inlist-GM
    SStot=MA.sum(SStot**2,axis=0)
    SStot=MA.sum(SStot,axis=0)
    SSbet=meanlist-GM
    SSbet=MA.sum(SSbet**2,axis=0)*GN/float(k)

    SSint = 0.0
    sh=range(len(inlist.shape))
    sh[0]=1
    sh[1]=0
    mean=MA.average(inlist,axis=0)

    SSint=MA.sum((mean-GM)**2, axis=0)*k
    SSres = SSwit - SSint
    dfbet = (k - 1)*MA.ones(GN.shape)
    dfwit = GN - k
    dfres = (Nlist[0] - 1) * (k - 1)
    dftot = dfbet + dfwit + dfres
    MSbet = SSbet / dfbet
    MSwit = SSwit / dfwit
    MSres = SSres / dfres
    F = MSbet / MSres
    prob = _fprob(dfbet, dfres, F)
    return SSint, SSres, SSbet, SStot, dfbet, dfwit, dfres, dftot, MSbet, MSwit, MSres, F, prob

def anovaWithin( *inlist,**kw):
    """
    This method is specialised for SalStat, and is best left alone. 
    For the brave:
    Usage:
    SSint, SSres, SSbet, SStot, MSbet, MSwit, MSres, F, prob [, dfbet, dfwit, dfres, dftot]  = anovaWithin(*inlist,axis=axisoptions).
    inlist, being as many arrays as you  wish
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
        df=1 : if 1 then degrees of freedom are retuned
        
        WARNING: axis and df MUST be passed as keyword, as all arguments are considered as arrays
    """
    if len(inlist)<2:
        raise 'Error must have at least 2 arrays!'
    if not 'axis' in kw.keys():
        axis=0
    else:
        axis=kw['axis']
    if not 'df' in kw.keys():
        df=1
    else:
        df=kw['df']
    for i in range(1,len(inlist)):
        x,y,weights,axis,ax=__checker(inlist[0],inlist[i],None,axis)
        if i==1:
            newlist=[x,y]
        else:
            newlist.append(y)
    SSint, SSres, SSbet, SStot, dfbet, dfwit, dfres, dftot, MSbet, MSwit, MSres, F, prob = apply(_anovaWithin,newlist)
    if not ax is None:
        SSint=cdms.createVariable(SSint,axes=ax,id='SSint',copy=0)
        SSres=cdms.createVariable(SSres,axes=ax,id='SSres',copy=0)
        SSbet=cdms.createVariable(SSbet,axes=ax,id='SSbet',copy=0)
        SStot=cdms.createVariable(SStot,axes=ax,id='SStot',copy=0)
        dfbet=cdms.createVariable(dfbet,axes=ax,id='dfbet',copy=0)
        dfwit=cdms.createVariable(dfwit,axes=ax,id='dfwit',copy=0)
        dfres=cdms.createVariable(dfres,axes=ax,id='dfres',copy=0)
        dftot=cdms.createVariable(dftot,axes=ax,id='dftot',copy=0)
        MSbet=cdms.createVariable(MSbet,axes=ax,id='MSbet',copy=0)
        MSwit=cdms.createVariable(MSwit,axes=ax,id='MSwit',copy=0)
        MSres=cdms.createVariable(MSres,axes=ax,id='MSres',copy=0)
        F=cdms.createVariable(F,axes=ax,id='F',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)

    out= [SSint, SSres, SSbet, SStot, MSbet, MSwit, MSres, F, prob]
    if df:
        out.append(dfbet)
        out.append(dfwit)
        out.append(dfres)
        out.append(dftot)
        
    return out

## To be tested
def _anovaBetween(*descs):
    """
    This method performs a univariate single factor between-subjects
    analysis of variance on a list of lists (or a Numeric matrix). It is
    specialised for SalStat and best left alone.
    Usage: SSbet, SSwit, SStot, dfbet, dferr, dftot, MSbet, MSerr, F, prob = anovaBetween(*arrays).
    """
    descs=pack(descs)
    k = descs.shape[0]
    
    M=MA.average(descs,axis=1)
    ssdev=MA.sum((descs-M[:,None,...])**2,axis=1)
    SSwit=MA.sum(ssdev,axis=0)
    Ns=MA.count(descs,axis=1)
    GN=MA.sum(Ns,axis=0)
    GM=MA.average(M,axis=0)

    SSbet=MA.sum((M-GM)**2,axis=0)
    SSbet = SSbet * Ns[0]
    SStot = SSwit + SSbet
    dfbet = MA.ones(SSbet.shape)*(k - 1)
    dferr = GN - k
    dftot = dfbet + dferr
    MSbet = SSbet / dfbet
    MSerr = SSwit / dferr
    F = MSbet / MSerr
    prob = _fprob(dfbet, dferr, F)
    return SSbet, SSwit, SStot, dfbet, dferr, dftot, MSbet, MSerr, F, prob

def anovaBetween(*inlist,**kw):
    """
    This method performs a univariate single factor between-subjects
    analysis of variance on a list of lists (or a Numeric matrix). It is
    specialised for SalStat and best left alone.
    Usage: SSbet, SSwit, SStot, MSbet, MSerr, F, prob [, dfbet, dferr, dftot] = anovaBetween(*arrays,axis=axisoptions).
    inlist, being as many arrays as you  wish
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
        df=1 : if 1 then degrees of freedom are retuned
        
        WARNING: axis and df MUST be passed as keyword, as all arguments are considered as arrays
    """
    if len(inlist)<2:
        raise 'Error must have at least 2 arrays!'
    if not 'axis' in kw.keys():
        axis=0
    else:
        axis=kw['axis']
    if not 'df' in kw.keys():
        df=1
    else:
        df=kw['df']
    for i in range(1,len(inlist)):
        x,y,weights,axis,ax=__checker(inlist[0],inlist[i],None,axis)
        if i==1:
            newlist=[x,y]
        else:
            newlist.append(y)
    SSbet, SSwit, SStot, dfbet, dferr, dftot, MSbet, MSerr, F, prob = apply(_anovaBetween,newlist)
    if not ax is None:
        SSbet=cdms.createVariable(SSbet,axes=ax,id='SSbet',copy=0)
        SSwit=cdms.createVariable(SSwit,axes=ax,id='SSwit',copy=0)
        SStot=cdms.createVariable(SStot,axes=ax,id='SStot',copy=0)
        dfbet=cdms.createVariable(dfbet,axes=ax,id='dfbet',copy=0)
        dferr=cdms.createVariable(dferr,axes=ax,id='dferr',copy=0)
        dftot=cdms.createVariable(dftot,axes=ax,id='dftot',copy=0)
        MSbet=cdms.createVariable(MSbet,axes=ax,id='MSbet',copy=0)
        MSerr=cdms.createVariable(MSerr,axes=ax,id='MSerr',copy=0)
        F=cdms.createVariable(F,axes=ax,id='F',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
        
    out= [SSbet, SSwit, SStot, MSbet, MSerr, F, prob]
    if df:
        out.append(dfbet)
        out.append(dferr)
        out.append(dftot)
        
    return out


def _KruskalWallisH(*args):
    """
    This method performs a Kruskal Wallis test (like a nonparametric 
    between subjects anova) on a serie of arrays.
    Usage: h, df, prob = KruskalWallisH(*args).
    """
    narrays=len(args)
    args = pack(args)
    n = MA.count(args,axis=1)
    all=MA.array(args[0],copy=1)
    for i in range(1,narrays):
        all = MA.concatenate((all,args[i]),axis=0)
    ranked = _rankdata(all)
    del(all)
    T = _tiecorrect(ranked)
    offset=0
    for i in range(narrays):
        nn=args[i].shape[0]
        args[i] = ranked[offset:offset+nn]
        offset+=nn
    del(ranked)
    rsums = MA.zeros(args[0].shape,'d')
    ssbn=MA.zeros(args[0].shape[1:],'d')
    totaln=MA.sum(n,axis=0)
    rsums=MA.sum(args,axis=1)**2/n
    ssbn = MA.sum(rsums,axis=0)
    h = 12.0 / (totaln*(totaln+1)) * ssbn - 3*(totaln+1)

    h = h / T
    df=MA.ones(h.shape)*(narrays-1.)
    prob = _chisqprob(h,df)
    return h, df, prob
      
def KruskalWallisH(*inlist,**kw):
    """
    This method performs a Kruskal Wallis test (like a nonparametric 
    between subjects anova) on a serie of arrays.
    Usage: h, df, prob = KruskalWallisH(*args,axis=axispoptions, df=1).
    inlist, being as many arrays as you  wish
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
        df=1 : if 1 then degrees of freedom are retuned
        
        WARNING: axis and df MUST be passed as keyword, as all arguments are considered as arrays
    """
    if len(inlist)<2:
        raise 'Error must have at least 2 arrays!'
    if not 'axis' in kw.keys():
        axis=0
    else:
        axis=kw['axis']
    if not 'df' in kw.keys():
        df=1
    else:
        df=kw['df']
    for i in range(1,len(inlist)):
        x,y,weights,axis,ax=__checker(inlist[0],inlist[i],None,axis)
        if i==1:
            newlist=[x,y]
        else:
            newlist.append(y)
    h, d, prob= apply(_KruskalWallisH,newlist)
    if not ax is None:
        h=cdms.createVariable(h,axes=ax,id='KruskalWallisH',copy=0)
        d=cdms.createVariable(d,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)

    out=[h,prob]
    if df:
        out.append(d)

    return out

def _FriedmanChiSquare( *args):
    """
    This method performs a Friedman chi square (like a nonparametric 
    within subjects anova) on a list of lists.
    Usage: sumranks, chisq, df, prob = FriedmanChiSqure(*args).
    """
    ## First put it all in a big array
    data=pack(args)
    k=data.shape[0]
    n=data.shape[1]
    ## Transpose the data (nargs/0axis, rest is left identical)
    tr=range(MA.rank(data[0])+1)
    tr[0]=1
    tr[1]=0
    data=MA.transpose(data,tr)
    data2=data*1.
    ## ranks it
    for i in range(n):
        data[i] = _rankdata(data[i])

    sumranks = MA.sum(data,axis=0)
    tmp=MA.sum(data,axis=0)            
    ssbn=MA.sum(tmp**2, axis=0)
    sums=tmp/MA.count(data,axis=0)
    chisq = (12.0 / (k*n*(k+1))) * ssbn - 3*n*(k+1)
    df = MA.ones(chisq.shape)*(k-1)
    prob = _chisqprob(chisq,df)
    return sumranks, chisq, df, prob

def FriedmanChiSquare( *inlist, **kw):
    """
    This method performs a Friedman chi square (like a nonparametric 
    within subjects anova) on a list of lists.
    Usage: sumranks, chisq, df, prob = FriedmanChiSqure(*args, axis=axisoptions, df=1).
    inlist, being as many arrays as you  wish
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
        df=1 : if 1 then degrees of freedom are retuned
        
        WARNING: axis and df MUST be passed as keyword, as all arguments are considered as arrays
    """
    if len(inlist)<2:
        raise 'Error must have at least 2 arrays!'
    if not 'axis' in kw.keys():
        axis=0
    else:
        axis=kw['axis']
    if not 'df' in kw.keys():
        df=1
    else:
        df=kw['df']
    for i in range(1,len(inlist)):
        x,y,weights,axis,ax=__checker(inlist[0],inlist[i],None,axis)
        if i==1:
            newlist=[x,y]
        else:
            newlist.append(y)
    sumranks, h, d, prob= apply(_FriedmanChiSquare,newlist)
    if not ax is None:
        h=cdms.createVariable(h,axes=ax,id='FriedmanChiSquare',copy=0)
        d=cdms.createVariable(d,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)
        sumranks=cdms.createVariable(sumranks,id='sumranks',copy=0)
        ax.insert(0,sumranks.getAxis(0))
        sumranks.setAxisList(ax)
    out=[sumranks,h,prob]
    if df:
        out.append(d)

    return out

def _CochranesQ( *inlist):
    """
    This method performs a Cochrances Q test upon a list of lists.
    Usage: q, df, prob = CochranesQ(*inlist)
    Returns: q, df, prob
    """
    ## First put it all in a big array
    data=pack(inlist)
    k=data.shape[0]
    n=data.shape[1]
    g=MA.sum(data,axis=1)
    gtot=MA.sum(g**2,axis=0)
    rowsum=MA.sum(data,axis=0)
    l=MA.sum(rowsum,axis=0)
    lsq=MA.sum(rowsum**2,axis=0)
    q = ((k-1)*((k*gtot)-(l**2)))/((k*l)-lsq)
    df = MA.ones(q.shape)*(k - 1)
    prob = _chisqprob(q, df)
    return q, df, prob

def CochranesQ( *inlist,**kw):
    """
    This method performs a Cochrances Q test upon a list of lists.
    Usage: q, df, prob = CochranesQ(*inlist)
    inlist, being as many arrays as you  wish
    Options:
        axisoptions 'x' | 'y' | 'z' | 't' | '(dimension_name)' | 0 | 1 ... | n 
        default value = 0. You can pass the name of the dimension or index
        (integer value 0...n) over which you want to compute the statistic.
        you can also pass 'xy' to work on both axes at once
        df=1 : if 1 then degrees of freedom are retuned
        
        WARNING: axis and df MUST be passed as keyword, as all arguments are considered as arrays
    """
    if len(inlist)<2:
        raise 'Error must have at least 2 arrays!'
    if not 'axis' in kw.keys():
        axis=0
    else:
        axis=kw['axis']
    if not 'df' in kw.keys():
        df=1
    else:
        df=kw['df']
    for i in range(1,len(inlist)):
        x,y,weights,axis,ax=__checker(inlist[0],inlist[i],None,axis)
        if i==1:
            newlist=[x,y]
        else:
            newlist.append(y)
    h, d, prob= apply(_CochranesQ,newlist)
    if not ax is None:
        h=cdms.createVariable(h,axes=ax,id='CochranesQ',copy=0)
        d=cdms.createVariable(d,axes=ax,id='df',copy=0)
        prob=cdms.createVariable(prob,axes=ax,id='probability',copy=0)

    out=[h,prob]
    if df:
        out.append(d)

    return out


## class FriedmanComp:
##     """This class performs multiple comparisons on a Freidmans
##     test. Passed values are the medians, k (# conditions), n
##     (# samples), and the alpha value. Currently, all comparisons
##     are performed regardless. Assumes a balanced design.
##     ALSO: does not work yet!
##     """
##     def __init__(self, medians, k, n, p):
##         crit = _inversechi(p, k-1)
##         value = crit * math.sqrt((k * (k + 1)) / (6 * n * k))
##         self.outstr = '<p>Multiple Comparisons for Friedmans test:</p>'
##         self.outstr=self.outstr+'<br>Critical Value (>= for sig) = '+str(crit)
##         for i in range(len(medians)):
##             for j in range(i+1, len(medians)):
##                 if (i != j):
##                     self.outstr = self.outstr+'<br>'+str(i+1)+' against '+str(j+1)
##                     diff = abs(medians[i] - medians[j])
##                     self.outstr = self.outstr+'  = '+str(diff)

## class KWComp:
##     """This class performs multiple comparisons on a Kruskal Wallis
##     test. Passed values are the medians, k (# conditions), n
##     (# samples), and the alpha value. Currently, all comparisons
##     are performed regardless. Assumes a balanced design.
##     Further note - not completed by any means! DO NO USE THIS YET!"""
##     def __init__(self, medians, k, n, p):
##         crit = _inversechi(p, k-1)
##         value = crit * math.sqrt((k * (k + 1)) / (6 * n * k))
##         self.outstr = '<p>Multiple Comparisons for Friedmans test:</p>'
##         self.outstr=self.outstr+'<br>Critical Value (>= for sig) = '+str(crit)
##         for i in range(len(medians)):
##             for j in range(i+1, len(medians)):
##                 if (i != j):
##                     self.outstr = self.outstr+'<br>'+str(i+1)+' against '+str(j+1)
##                     diff = abs(medians[i] - medians[j])
##                     self.outstr = self.outstr+'  = '+str(diff)

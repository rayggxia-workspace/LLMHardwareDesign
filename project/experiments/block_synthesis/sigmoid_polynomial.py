"""Offline coefficient construction and exact fixed-point Clenshaw reference.

An expensive M/E fallback for numerically sensitive activations. Coefficients
are generated and quantized, not claimed to be extra hardware or a new LUT.
"""
import numpy as np


def coefficients():
    t=np.cos(np.pi*(np.arange(1024)+.5)/1024)
    c=np.polynomial.chebyshev.chebfit(t,1/(1+np.exp(-4*t)),19)
    return np.rint(c*(1<<30)).astype(np.int64)


def exp_coefficients():
    t=np.cos(np.pi*(np.arange(1024)+.5)/1024)
    c=np.polynomial.chebyshev.chebfit(t,np.exp(8*t-8),31)
    return np.rint(c*(1<<28)).astype(np.int64)


def rne30(x):
    q=x>>30;r=x&((1<<30)-1);h=1<<29
    return q+((r>h)|((r==h)&((q&1)!=0)))


def evaluate(t,coef):
    """t is Q1.30 in [-1,1]; intermediate values must fit real S32 slots."""
    t=np.asarray(t,dtype=np.int64)
    if np.any(np.abs(t)>1<<30):raise ValueError('polynomial outside qualified interval')
    a=np.zeros_like(t);b=np.zeros_like(t)
    for c in coef[:0:-1]:
        p=int(c)+rne30(2*t*a)-b
        if np.any((p<-(1<<31))|(p>=(1<<31))):raise ValueError('Clenshaw S32 state overflow')
        a,b=p,a
    return int(coef[0])+rne30(t*a)-b

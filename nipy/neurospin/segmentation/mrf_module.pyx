# -*- Mode: Python -*-  

"""
Markov random field utils. 
"""

__version__ = '0.0'

# Includes
include "numpy.pxi"

# Externals
cdef extern from "mrf.h":
    
    void mrf_import_array()
    void smooth_ppm(ndarray ppm, 
                    ndarray ref,
                    ndarray XYZ, 
                    double beta, 
                    int copy, 
                    int hard)

# Initialize numpy
mrf_import_array()
import_array()
import numpy as np


def finalize_ve_step(ppm, ref, XYZ, double beta, int copy, int hard):
    
    if not ppm.flags['C_CONTIGUOUS'] or not ppm.dtype=='double':
        raise ValueError('ppm array should be double C-contiguous')

    if not ref.flags['C_CONTIGUOUS'] or not ref.dtype=='double':
        raise ValueError('ref array should be double C-contiguous')
    
    XYZ = np.asarray(XYZ, dtype='int')
    
    smooth_ppm(<ndarray>ppm, <ndarray>ref, <ndarray>XYZ, beta, copy, hard)
    return ppm 



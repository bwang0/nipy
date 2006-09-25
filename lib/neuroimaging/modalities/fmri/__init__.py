from neuroimaging import traits
import numpy as N

from neuroimaging import flatten
from neuroimaging.core.image.image import Image
from neuroimaging.modalities.fmri.iterators import fMRISliceIterator,\
  fMRISliceParcelIterator
from neuroimaging.core.reference.coordinate_system import CoordinateSystem
from neuroimaging.core.reference.grid import SamplingGrid
from neuroimaging.core.reference.iterators import ParcelIterator
from neuroimaging.core.reference.mapping import Mapping, Affine



class fMRIListMapping(Mapping):

    def __init__(self, input_coords, output_coords, maps, **keywords):
        self._maps = maps


    def map(self, coords):
        if len(coords.shape) > 1:
            n = coords.shape[1]
            value = []
            for i in range(n):
                value.append(self._maps[coords[i][0]](coords[i][1:]))
        else:
            return self._maps[coords[0]][coords[1:]]



class fMRISamplingGrid(SamplingGrid):

    def __init__(self, shape, mapping, input_coords, output_coords):
        SamplingGrid.__init__(self, shape, mapping, input_coords, output_coords)
        iterators = {"slice": (fMRISliceIterator, ["shape"]),
                     "parcel": (ParcelIterator, ["parcelmap", "parcelseq"]),
                     "slice/parcel": (fMRISliceParcelIterator, ["parcelmap", "parcelseq", "shape"])}
        self._iterguy = self._IterHelper(self.shape, 1, "slice", None, None, iterators)        


    def isproduct(self, tol = 1.0e-07):
        "Determine whether the affine   ation is 'diagonal' in time."

        if not isinstance(self.mapping, Affine): return False
        ndim = self.ndim
        t = self.mapping.transform
        offdiag = N.add.reduce(t[1:ndim,0]**2) + N.add.reduce(t[0,1:ndim]**2)
        norm = N.add.reduce(N.add.reduce(t**2))
        return N.sqrt(offdiag / norm) < tol


    def subgrid(self, i):
        """
        Return a subgrid of fMRISamplingGrid. If the image's mapping is an
        Affine instance and is 'diagonal' in time, then it returns a new
        Affine instance. Otherwise, if the image's mapping is a list of
        mappings, it returns the i-th mapping.  Finally, if these two do not
        hold, it returns a generic, non-invertible map in the original output
        coordinate system.
        """
        # TODO: this bit should be handled by CoordinateSystem,
        # eg: incoords = self.mapping.input_coords.subcoords(...)
        incoords = CoordinateSystem(
          self.input_coords.name+'-subgrid',
          self.input_coords.axes()[1:])

        if isinstance(self.mapping, fMRIListMapping):
            outaxes = self.output_coords.axes()[1:]
            outcoords = CoordinateSystem(
                self.output_coords.name, outaxes)        
            W = Affine(self._maps[i])

        elif self.isproduct():
            outaxes = self.output_coords.axes()[1:]
            outcoords = CoordinateSystem(
              self.output_coords.name, outaxes)        

            t = self.mapping.transform
            t = t[1:,1:]
            W = Affine(t)

        else:
            outaxes = self.output_coords.axes()[1:]
            outcoords = CoordinateSystem(
              self.output_coords.name, outaxes)        

            def _map(x, fn=self.mapping.map, **keywords):
                if len(x.shape) > 1:
                    _x = N.zeros((x.shape[0]+1,) + x.shape[1:], N.float64)
                else:
                    _x = N.zeros((x.shape[0]+1,), N.float64)
                _x[0] = i
                return fn(_x)
            W = Mapping(_map)

        _grid = SamplingGrid(self.shape[1:], W, incoords, outcoords)
        for param in ["parcelmap", "parcelseq"]:
            _grid.set_iter_param(param, self.get_iter_param(param))
        return _grid



class fMRIImage(Image):
    #frametimes = traits.Any()
    #slicetimes = traits.Any()
    TR = traits.Any()


    def __init__(self, _image, **keywords):
        Image.__init__(self, _image, **keywords)
        self.frametimes = keywords.get('frametimes', None)
        self.slicetimes = keywords.get('slicetimes', None)

        self.grid = fMRISamplingGrid(self.grid.shape, self.grid.mapping, self.grid.input_coords, self.grid.output_coords)
        if self.grid.isproduct():
            ndim = len(self.grid.shape)
            n = [self.grid.input_coords.axisnames()[i] \
                 for i in range(ndim)]
            d = n.index('time')
            self.TR = self.grid.mapping.transform[d, d]
            start = self.grid.mapping.transform[d, ndim]
            self.frametimes = start + N.arange(self.grid.shape[d]) * self.TR


    def tofile(self, filename, **keywords):
        Image.tofile(self, filename, array=False, **keywords)
        

    def frame(self, i, clean=False, **keywords):
        data = N.squeeze(self[slice(i,i+1)])
        if clean: data = N.nan_to_num(data)
        return Image(self.postread(data), grid=self.grid.subgrid(i), **keywords)


    def next(self, value=None, data=None):
        """
        The value argument here is used when, for instance one wants to
        iterate over one image with a ParcelIterator and write out data to
        this image without explicitly setting this image's grid to the
        original image's grid, i.e. to just take the value the original
        image's iterator returns and use it here.
        """
        if value is None:
            self.itervalue = self.grid.next()
            value = self.itervalue


        itertype = value.type

        if data is None:

            if itertype == 'slice':
                result = self[value.slice]

            elif itertype == 'parcel':
                value.where.shape = N.product(value.where.shape)
                self.label = value.label
                result = self.compress(value.where, axis=1)

            elif itertype == 'slice/parcel':
                value.where.shape = N.product(value.where.shape)
                self.label = value.label
                tmp = self[value.slice].copy()
                tmp.shape = (tmp.shape[0], N.product(tmp.shape[1:]))
                result = tmp.compress(value.where, axis=1)

            return self.postread(result)

        else:

            if itertype == 'slice':
                self[value.slice] = data

            elif itertype == 'parcel':
                for i in range(self.grid.shape[0]):
                    _buffer = self[slice(i,i+1)]
                    _buffer.put(data, indices)

            elif itertype == 'slice/parcel':
                indices = N.nonzero(value.where)
                _buffer = self[value.slice]
                _buffer.put(data, indices)


    def __iter__(self):
        "Create an iterator over an image based on its grid's iterator."
        iter(self.grid)
        if self.grid.get_iter_param("itertype") == 'parcel': 
            flatten(self.buffer, 1)
        return self


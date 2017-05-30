from .util import *
from .srsutil import *
from .geomutil import *
from .rasterutil import *
from .vectorutil import *


IndexSet = namedtuple("IndexSet","xStart yStart xWin yWin xEnd yEnd")

class Extent(object):
    """Geographic extent

    The Extent object represents geographic extents of an area and exposes useful methods which depend on those extents. This includes:
        - Easily representing the boundaries as (xMin, xMax, yMin, yMax) or (xMin, yMin, xMax, yMax)
        - Casting to another projection system
        - Padding and shifting the boundaries
        - "Fitting" the boundaries onto a given resolution
        - Clipping a given raster file

    Initialization is accomplished via:
        - Extent(xMin, yMin, xMax, yMax [, srs])
        - Extent.from_xyXY( (xMin, yMin, xMax, yMax) [, srs])
        - Extent.from_xXyY( (xMin, xMax, yMin, yMax) [, srs])
        - Extent.fromGeom( geom [, srs] )
        - Extent.fromVector( vector-file-path )
        - Extent.fromRaster( raster-file-path )
    """
    def __init__(s, *args, srs='latlon'):
        """Create extent from explicitly defined boundaries
        
        Usage:
            Extent(xMin, yMin, xMax, yMax [, srs=<srs>])
            Extent( (xMin, yMin, xMax, yMax) [, srs=<srs>])
        
        Where:
            xMin - The minimal x value in the respective SRS
            yMin - The minimal y value in the respective SRS
            xMax - The maximal x value in the respective SRS
            yMax - The maximal y value in the respective SRS
            srs - The Spatial Reference system to use
        """
        # Unpack args
        if len(args)==1:
            xMin, yMin, xMax, yMax = args[0]
        elif len(args)==4:
            xMin, yMin, xMax, yMax = args
        else:
            raise GeoKitExtentError("Incorrect number of positional arguments givin in init (accepts 1 or 4). Is an srs given as 'srs=...'?")
        
        # Ensure good inputs
        xMin, xMax = min(xMin, xMax), max(xMin, xMax)
        yMin, yMax = min(yMin, yMax), max(yMin, yMax) 

        s.xMin = xMin
        s.xMax = xMax
        s.yMin = yMin
        s.yMax = yMax
        s.srs  = loadSRS(srs)

        s._box = makeBox(s.xMin, s.yMin, s.xMax, s.yMax, srs=s.srs)

    @staticmethod
    def from_xXyY(bounds, srs='latlon'):
        """Create an Extent from explicitly defined boundaries

        Inputs:
          bounds - (xMin, xMax, yMin, yMax)
          srs - The Spatial Reference system to use (default EPSG4326)
        """
        return Extent(bounds[0], bounds[2], bounds[1], bounds[3], srs)

    @staticmethod
    def fromGeom( geom, srs=None ):
        """Create extent around a given geometry

        Inputs:
            geom : The geometry to create the Extent around 
                - ogr.Geometry
                - str
                * If a string is given, it is assumed to be a WKT string. In this case, an srs must also be provided

            srs : The Spatial reference system to apply to the created Extent
                - osr.SpatialReference object
                - an EPSG integer ID
                - a string corresponding to one of the systems found in geokit.srs.SRSCOMMON
                - a WKT string
                * If 'geom' is an ogr Geometry and 'srs' is not None, the geometry will be transformed to the given srs 
        """
        # ensure we have an osr.SpatialReference object
        if not srs is None:
            srs = loadSRS(srs)

        # Ensure geom is an ogr.Geometry object
        if isinstance(geom, str):
            if srs is None: raise ValueError("srs must be provided when geom is a string")
            geom = convertWKT(geom, srs)
        elif (srs is None):
            srs = geom.GetSpatialReference()

        # Test if a reprojection is required
        if not srs.IsSame( geom.GetSpatialReference() ):
            geom.TransformTo(srs)

        # Read Envelope
        xMin, xMax, yMin, yMax = geom.GetEnvelope()

        # Done!
        return Extent(xMin, yMin, xMax, yMax, srs=geom.GetSpatialReference())

    @staticmethod
    def fromVector( source ):
        """Create extent around the contemts of a vector source

        Inputs:
          source - str : The path to a vector file
        """
        shapeDS = loadVector(source)

        shapeLayer = shapeDS.GetLayer()
        shapeSRS = shapeLayer.GetSpatialRef()
        
        xMin,xMax,yMin,yMax = shapeLayer.GetExtent()

        return Extent(xMin, yMin, xMax, yMax, srs=shapeSRS)

    @staticmethod
    def fromRaster( source ):
        """Create extent around the contents of a raster source

        Inputs:
          source - str : The path to a raster file
        """
        dsInfo = rasterInfo(source)

        xMin,yMin,xMax,yMax = dsInfo.bounds

        return Extent(xMin, yMin, xMax, yMax, srs=dsInfo.srs)

    @staticmethod
    def _fromInfo(info):
        """GeoKit internal

        Creates an Extent from rasterInfo's returned value
        """
        return Extent( info.xMin, info.yMin, info.xMax, info.yMax, srs=info.srs)

    @property
    def xyXY(s): 
        """Returns a tuple of the extent boundaries in order:
            xMin, yMin, xMax, yMax"""
        return (s.xMin, s.yMin, s.xMax, s.yMax)

    @property
    def xXyY(s): 
        """Returns a tuple of the extent boundaries in order:
            xMin, xMax, yMin, yMax"""
        return (s.xMin, s.xMax, s.yMin, s.yMax)

    @property
    def box(s): 
        """Returns a rectangular ogr.Geometry object representing the extent"""
        return s._box.Clone()

    def __eq__(s,o):
        #if (s.xyXY != o.xyXY): return False
        if (not s.srs.IsSame(o.srs) ): return False
        if not isclose(s.xMin, o.xMin): return False
        if not isclose(s.xMax, o.xMax): return False
        if not isclose(s.yMin, o.yMin): return False
        if not isclose(s.yMin, o.yMin): return False
        return True

    def __str__(s):
        out = ""
        out += "xMin: %f\n"%s.xMin
        out += "xMax: %f\n"%s.xMax
        out += "yMin: %f\n"%s.yMin
        out += "yMax: %f\n"%s.yMax
        out += "srs: %s\n"%s.srs.ExportToWkt()

        return out

    def pad(s, pad): 
        """Creates a new extent which has been padded in all directions compared to the original extent

        pad - float : The amount to pad in all directions
            * In units of the extent's srs
            * Can also accept a negative padding
        """
        if pad is None or pad == 0 : return s
        return Extent(s.xMin-pad, s.yMin-pad, s.xMax+pad, s.yMax+pad, srs=s.srs)

    def shift(s, dx=0, dy=0): 
        """Creates a new extent which has been spatialy shifted from the original extent

        dx - float : Shifts the extent's edges in the x-direction
        dy - float : Shifts the extent's edges in the y-direction
        """
        return Extent(s.xMin+dx, s.yMin+dy, s.xMax+dx, s.yMax+dy, srs=s.srs)

    def fitsResolution(s, unit, tolerance=1e-6):
        """Returns True if the calling Extent first around the given unit(s) (at least within an error defined 
           by 'tolerance')
        
        Inputs:
            unit : the unit value(s) to check
                - float : A single resolution value
                - ( float, float) : A tuple of resolutions for both dimensions (x, y)

        Example:
            >>> ex = Extent( 100, 100, 300, 500)
            >>> ex.fits(25) # True!
            >>> ex.fits( (25, 10) ) # True!
            >>> ex.fits(33) # False!
            >>> ex.fits( (25, 33) ) # False!
        """
        try:
            unitX, unitY = unit
        except:
            unitX, unitY = unit, unit

        xSteps = (s.xMax-s.xMin)/unitX
        xResidual = abs(xSteps-np.round(xSteps))
        if xResidual > tolerance:
            return False

        ySteps = (s.yMax-s.yMin)/unitY
        yResidual = abs(ySteps-np.round(ySteps))
        if yResidual > tolerance:
            return False

        return True

    def fit(s, unit, dtype=None):
        """Fit the extent to a given pixel resolution

        * The extent is always expanded to fit onto the given unit

        Inputs:
            unit : The unit to fit
                - float : a single resolution value
                - (float, float) : A (x,y) tuple of resolution values
            
            dtype : An optional data type which the extent boundaries will be cast to 
                - type : a python numeric type (int, float)
        """
        try:
            unitX, unitY = unit
        except:
            unitX, unitY = unit, unit
        
        # Look for bad sizes
        if (unitX> s.xMax-s.xMin): raise GeoKitExtentError("Unit size is larger than extent width")
        if (unitY> s.yMax-s.yMin): raise GeoKitExtentError("Unit size is larger than extent width")

        # Calculate new extent
        newXMin = s.xMin-s.xMin%unitX
        newYMin = s.yMin-s.yMin%unitY

        tmp = s.xMax%unitX
        if(tmp == 0): newXMax = s.xMax
        else: newXMax = (s.xMax+unitX)-tmp

        tmp = s.yMax%unitY
        if(tmp == 0): newYMax = s.yMax
        else: newYMax = (s.yMax+unitY)-tmp

        # Done!
        if dtype is None or isinstance(unitX,dtype):
            return Extent( newXMin, newYMin, newXMax, newYMax, srs=s.srs )
        else:
            return Extent( dtype(newXMin), dtype(newYMin), dtype(newXMax), dtype(newYMax), srs=s.srs )

    def corners(s, asPoints=False):
        """Shortcut function to get the four corners of the extent as ogr geometry points or as x,y coordinates in 
           the extent's srs"""

        if (asPoints):
            # Make corner points
            bl = makePoint( s.xMin, s.yMin )
            br = makePoint( s.xMax, s.yMin )
            tl = makePoint( s.xMin, s.yMax )
            tr = makePoint( s.xMax, s.yMax )

        else:
            # Make corner points
            bl = ( s.xMin, s.yMin)
            br = ( s.xMax, s.yMin)
            tl = ( s.xMin, s.yMax)
            tr = ( s.xMax, s.yMax)

        return (bl, br, tl, tr)

    def castTo(s, targetSRS):
        """
        Creates a new Extent by transforming an extent from the original Extent's srs to a target SRS. 
        Note: The resulting region spanned by the extent will be equal-to or (almost certainly) larger than the origional
        
        targetSRS : The srs to cast to
            : int -- The target SRS to use as an EPSG integer
            : str -- The target SRS to use as a WKT string
            : osr.SpatialReference -- The target SRS to use
        """
        targetSRS=loadSRS(targetSRS)

        # Check for same srs
        if( targetSRS.IsSame(s.srs)):
            return s

        # Create a transformer
        targetSRS = loadSRS(targetSRS)
        transformer = osr.CoordinateTransformation(s.srs, targetSRS)

        # Transform and record points
        X = []
        Y = []

        for point in s.corners(True):
            try:
                point.Transform( transformer )
            except Exception as e:
                print("Could not transform between the following SRS:\n\nSOURCE:\n%s\n\nTARGET:\n%s\n\n"%(s.srs.ExportToWkt(), targetSRS.ExportToWkt()))
                raise e

            
            X.append(point.GetX())
            Y.append(point.GetY())

        # return new extent
        return Extent(min(X), min(Y), max(X), max(Y), srs=targetSRS)

    def inSourceExtent(s, source):
        """Tests if the extent box is at least partially contained in the extent-box of the given vector source"""
        sourceExtent = Extent.fromVector(source).castTo(s.srs)
        return s._box.Intersects(sourceExtent.box)

    def filterSources(s, sources):
        """Filter a list of sources by those whose's envelope overlaps the Extent.
        
        * Creates a filter object which can be immidiately iterated over, or else can be cast as a list

        Inputs:
            sources : The sources to filter
                - An iterable of vector sources
                - An iterable of paths pointing to vector sources
                - A glob string which will generate a list of source paths
                    * see glob.glob for more info

        """
        # create list of searchable files
        if isinstance(sources, str):
            directoryList = glob(sources)
        else:
            directoryList = sources

        return filter(s.inSourceExtent, directoryList)
    
    def contains(s, extent, res=None):
        """Tests if the extent contains another given extent

        * If an optional resolution ('res') is given, the containment value is also dependant on whether or not the given extent fits within the larger extent AND is situated along the given resolution

        Inputs:
            extent : The (potentially) contained Extent 
                - Extent object
            
            res : An optional resolution to check containment on
                - float : A single resolution
                - (float, float) : An (x,y) tuple of resolution values
                
        """
        # test raw bounds
        if( not extent.srs.IsSame(s.srs) or 
            extent.xMin < s.xMin or extent.yMin < s.yMin or
            extent.xMax > s.xMax or extent.yMax > s.yMax):
            return False

        if( res ):
            # unpack resolution
            try: dx, dy = res
            except: dx, dy = res, res

            # Test for factor of resolutions
            thresh = dx/1000
            if( (extent.xMin - s.xMin)%dx>thresh or
                (extent.yMin - s.yMin)%dy>thresh or
                (s.xMax - extent.xMax)%dx>thresh or
                (s.yMax - extent.yMax)%dy>thresh ):
                return False
        return True

    def findWithin(s, extent, res=100, yAtTop=True):
        """Finds the indexes of the given extent within the main extent according to the given resolution.
        
        * Use this to compute the index offsets and window sizes of a window within a raster dataset
        * The two extents MUST share the same SRS

        Inputs:
            extent : The other extent 
                - Extent

            res : A resolution to check containment on
                - float : A single resolution
                - (float, float) : An (x,y) tuple of resolution values

            yAtTop - True/False : Indicates whether the main (larger) extent is in the y-starts-at-top orientation
                * Instructs the offsetting to begin from yMax instead of from yMin

        Returns:
            (xOffset, yOffset, xWindowSize, yWindowSize)
        """

        # test srs
        if not s.srs.IsSame(extent.srs):
            raise GeoKitExtentError("extents are not of the same srs")

        # try to unpack the resolution
        try:
            dx,dy = res
        except:
            dx,dy = res,res

        # Get offsets
        tmpX = (extent.xMin - s.xMin)/dx
        xOff = int(np.round(tmpX))

        if( yAtTop ):
            tmpY = (s.yMax - extent.yMax)/dy
        else:
            tmpY = (extent.yMin - s.yMin)/dy
        yOff = int(np.round(tmpY))

        if not (isclose(xOff, tmpX) and isclose(yOff, tmpY)):
            raise GeoKitExtentError("The extents are not relatable on the given resolution")

        # Get window sizes
        tmpX = (extent.xMax - extent.xMin)/dx
        xWin = int(np.round(tmpX))

        tmpY = (extent.yMax - extent.yMin)/dy
        yWin = int(np.round(tmpY))

        if not (isclose(xWin, tmpX) and isclose(yWin, tmpY)):
            raise GeoKitExtentError("The extents are not relatable on the given resolution")

        # Done!
        return IndexSet(xOff, yOff, xWin, yWin, xOff+xWin, yOff+yWin)
    
    def extractMatrix(s, source):
        """Extracts the extent directly from the given raster source as a matrix. The called extent must fit somewhere within the raster's grid

        !NOTE! If a raster is given which is not in the 'y-starts-at-top' orientation, it will be clipped in its native state, but the returned matrix will be automatically flipped
        """
        
        # open the dataset and get description
        rasDS = loadRaster(source)
        rasInfo = rasterInfo(rasDS)
        rasExtent = Extent._fromInfo(rasInfo)

        # Find the main extent within the raster extent
        try:
            xO, yO, xW, yW, xE, yE = rasExtent.findWithin(s, res=(rasInfo.dx, rasInfo.dy), yAtTop=rasInfo.yAtTop)
        except GeoKitExtentError:
            raise GeoKitExtentError( "The extent does not appear to fit within the given raster")
            
        # Extract and return the matrix
        arr = extractMatrix(rasDS, xOff=xO, yOff=yO, xWin=xW, yWin=yW)

        # make sure we are returing data in the 'flipped-y' orientation
        if not rasInfo.flipY:
            arr = arr[::-1,:]
        
        return arr

    def clipRaster(s, source, output=None):
        """
        Clip a given raster around the extent object and create a new raster dataset which maintains the original
        source's projection and resolution

        * Returns a gdal.Datasource if an 'output' path is not provided
        * Creates a raster file if an 'output' path is provided

        Inputs:
            source : The datasource to clip
                - gdal.Datasource
                - str : A path to a raster datasource on the file system 

            output - str : A optional path to an output file
        """

        # open the dataset and get description
        rasDS = loadRaster(source)
        ras = rasterInfo(rasDS)

        # Find an extent which contains the region in the given raster system
        if( not ras.srs.IsSame(s.srs) ):
            extent = s.castTo(ras.srs)
        else:
            extent = s

        # Ensure new extent fits the pixel size
        extent = extent.fit((ras.dx, ras.dy))

        # create target raster
        outputDS = createRaster(bounds=extent.xyXY, pixelWidth=ras.dx, pixelHeight=ras.dy, 
                                srs=ras.srs, dtype=ras.dtype, noDataValue=ras.noData, overwrite=True,
                                output=output)
        # Do warp
        if (not output is None): # Reopen the outputDS if it is None (only happens when an output path was given)
            outputDS = gdal.Open(output, gdal.GA_Update)

        gdal.Warp(outputDS, source, outputBounds=extent.xyXY) # Warp source onto the new raster

        # Done
        if(output is None):
            return outputDS
        else:
            return


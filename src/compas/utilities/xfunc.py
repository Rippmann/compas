from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import sys
import json

try:
    from subprocess import Popen
    from subprocess import PIPE
except ImportError:
    if 'ironpython' not in sys.version.lower():
        raise


__author__     = ['Tom Van Mele', ]
__copyright__  = 'Copyright 2014, Block Research Group - ETH Zurich'
__license__    = 'MIT License'
__email__      = 'vanmelet@ethz.ch'


__all__ = ['XFunc', 'DataEncoder', 'DataDecoder']


WRAPPER = """
import os
import sys
import importlib

import json

try:
    from cStringIO import StringIO
except Exception:
    from io import StringIO

import cProfile
import pstats
import traceback

from compas.utilities import DataEncoder
from compas.utilities import DataDecoder


basedir  = sys.argv[1]
funcname = sys.argv[2]
ipath    = sys.argv[3]
opath    = sys.argv[4]

with open(ipath, 'r') as fp:
    idict = json.load(fp, cls=DataDecoder)

try:
    args   = idict['args']
    kwargs = idict['kwargs']

    profile = cProfile.Profile()
    profile.enable()

    sys.path.insert(0, basedir)
    parts = funcname.split('.')

    if len(parts) > 1:
        mname = '.'.join(parts[:-1])
        fname = parts[-1]
        m = importlib.import_module(mname)
        f = getattr(m, fname)
    else:
        raise Exception('Cannot import the function because no module name is specified.')

    r = f(*args, **kwargs)

    profile.disable()

    stream = StringIO()
    stats  = pstats.Stats(profile, stream=stream)
    stats.strip_dirs()
    stats.sort_stats(1)
    stats.print_stats(20)

except Exception:
    odict = {}
    odict['error']      = traceback.format_exc()
    odict['data']       = None
    odict['profile']    = None

else:
    odict = {}
    odict['error']      = None
    odict['data']       = r
    odict['profile']    = stream.getvalue()

with open(opath, 'w+') as fp:
    json.dump(odict, fp, cls=DataEncoder)

"""


# def test_xfunc(numiter=100, pause=0.1, ds=None):
#     if ds:
#         print(ds)
#     for k in range(numiter):
#         print(k)
#         time.sleep(pause)
#     return ds


class DataEncoder(json.JSONEncoder):
    """Dump"""

    def default(self, o):
        from compas.datastructures import Datastructure

        if isinstance(o, Datastructure):
            print(type(o))
            return {
                'dtype': '{}/{}'.format(o.__class__.__module__, o.__class__.__name__),
                'value': o.to_data()
            }

        try:
            import numpy as np
        except ImportError:
            return super(DataEncoder, self).default(o)

        if isinstance(o, np.ndarray):
            return o.tolist()

        return super(DataEncoder, self).default(o)


class DataDecoder(json.JSONDecoder):
    """Load"""

    def __init__(self, *args, **kwargs):
        super(DataDecoder, self).__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, o):
        if 'dtype' not in o:
            return o

        dtype = o['dtype']

        # if this doesn't work
        # raise an Error explaining the required encoding
        module, attr = dtype.split('/')
        cls = getattr(__import__(module, fromlist=[attr]), attr)

        return cls.from_data(o['value'])


class XFunc(object):
    """Wrapper for functions that turns them into externally run processes.

    Parameters
    ----------
    funcname : str
        The full name of the function.
    basedir : str, optional
        A directory that should be added to the PYTHONPATH such that the function can be found.
        Default is the curent directory.
    tmpdir : str, optional
        A directory that should be used for storing the IO files.
        Default is the current directory.
    delete_files : bool, optional
        Set to ``False`` if the IO files should not be deleted afterwards.
        Default is ``True``.
    verbose : bool, optional
        Set to ``False`` if no information about the process should be displayed
        to the user. Default is ``True``.
    callback : callable, optional
        A function to be called eveytime the wrapped function prints output.
        The first parameter passed to this function is the line printed by the
        wrapped function. Additional parameters can be defined using `callback_args`.
        Default is ``None``.
    callback_args : tuple, optional
        Additional parameter for the callback function.
        Default is ``None``.

    Attributes
    ----------
    data : object
        The object returned by the wrapped function.
        This is ``None`` if something went wrong.
    profile : str
        A profile of the call to the wrapped function.
        This is ``None`` if something went wrong.
    error : str
        A traceback of the exception raised during the wrapped function call.
        This is ``None`` if nothing went wrong.

    Methods
    -------
    __call__(*args, **kwargs)
        Call the wrapped function with the apropriate/related arguments and keyword
        arguments.

    Notes
    -----
    ...

    References
    ----------
    ...

    Examples
    --------
    `compas.numerical` provides an implementation of the Force Desnity Method that
    is based on Numpy and Scipy. This implementation is not directly available in
    Rhino because Numpy and Scipy are not available for IronPython.

    With `compas.utilities.XFunc`, `compas.numerical.fd_numpy` can be easily
    wrapped in an external process and called as if it would be directly available.

    .. code-block:: python

        import compas
        import compas_rhino

        from compas_rhino.helpers import MeshArtist
        from compas.datastructures import Mesh
        from compas.utilities import XFunc

        mesh = Mesh.from_obj(compas.get('faces.obj'))

        mesh.update_default_vertex_attributes({'is_fixed': False, 'px': 0.0, 'py': 0.0, 'pz': 0.0})
        mesh.update_default_edge_attributes({'q': 1.0})

        for key, attr in mesh.vertices(True):
            attr['is_fixed'] = mesh.vertex_degree(key) == 2

        key_index = mesh.key_index()
        vertices  = mesh.get_vertices_attributes('xyz')
        edges     = [(key_index[u], key_index[v]) for u, v in mesh.edges()]
        fixed     = [key_index[key] for key in mesh.vertices_where({'is_fixed': True})]
        q         = mesh.get_edges_attribute('q', 1.0)
        loads     = mesh.get_vertices_attributes(('px', 'py', 'pz'), (0.0, 0.0, 0.0))

        xyz, q, f, l, r = XFunc('compas.numerical.fd_numpy')(vertices, edges, fixed, q, loads)

        for key, attr in mesh.vertices(True):
            attr['x'] = xyz[key][0]
            attr['y'] = xyz[key][1]
            attr['z'] = xyz[key][2]

        artist = MeshArtist(mesh)
        artist.draw_vertices()
        artist.draw_edges()

    """

    def __init__(self, funcname, basedir='.', tmpdir='.', delete_files=True,
                 verbose=True, callback=None, callback_args=None, python='pythonw'):
        self._basedir      = None
        self._tmpdir       = None
        self._callback     = None
        self._python       = None
        self.funcname      = funcname
        self.basedir       = basedir
        self.tmpdir        = tmpdir
        self.delete_files  = delete_files
        self.verbose       = verbose
        self.callback      = callback
        self.callback_args = callback_args
        self.python        = python
        self.data          = None
        self.profile       = None
        self.error         = None

    def __call__(self, *args, **kwargs):
        """Make a call to the wrapped function.

        Parameters
        ----------
        args : list
            Positional arguments to be passed to the wrapped function.
            Default is ``[]``.
        kwargs : dict
            Named arguments to be passed to the wrapped function.
            Default is ``{}``.

        Returns
        -------
        object
            The data returned by the wrapped call.
            This is ``None`` if something went wrong.

        """
        return self._xecute(*args, **kwargs)

    @property
    def basedir(self):
        return self._basedir

    @basedir.setter
    def basedir(self, basedir):
        if not os.path.isdir(basedir):
            raise Exception('basedir is not a directory: %s' % basedir)
        self._basedir = os.path.abspath(basedir)

    @property
    def tmpdir(self):
        return self._tmpdir

    @tmpdir.setter
    def tmpdir(self, tmpdir):
        if not os.path.isdir(tmpdir):
            raise Exception('tmpdir is not a directory: %s' % tmpdir)
        if not os.access(tmpdir, os.W_OK):
            raise Exception('you do not have write access to tmpdir')
        self._tmpdir = os.path.abspath(tmpdir)

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, callback):
        if callback:
            if not callable(callback):
                callback = None
        self._callback = callback

    @property
    def python(self):
        return self._python

    @python.setter
    def python(self, python):
        self._python = python

    @property
    def ipath(self):
        return os.path.join(self.tmpdir, '%s.in' % self.funcname)

    @property
    def opath(self):
        return os.path.join(self.tmpdir, '%s.out' % self.funcname)

    def _xecute(self, *args, **kwargs):
        """Execute a function with optional positional and named arguments.
        """
        idict = {'args': args, 'kwargs': kwargs}

        with open(self.ipath, 'w+') as fh:
            json.dump(idict, fh, cls=DataEncoder)

        with open(self.opath, 'w+') as fh:
            fh.write('')

        process_args = [self.python,
                        '-u',
                        '-c',
                        WRAPPER,
                        self.basedir,
                        self.funcname,
                        self.ipath,
                        self.opath]

        process = Popen(process_args, stderr=PIPE, stdout=PIPE)

        while process.poll() is None:
            line = process.stdout.readline().strip()
            if self.callback:
                self.callback(line, self.callback_args)
            if self.verbose:
                print(line)

        with open(self.opath, 'r') as fh:
            odict = json.load(fh, cls=DataDecoder)

            self.data    = odict['data']
            self.profile = odict['profile']
            self.error   = odict['error']

        if self.delete_files:
            try:
                os.remove(self.ipath)
            except OSError:
                pass
            try:
                os.remove(self.opath)
            except OSError:
                pass

        if self.error:
            raise Exception(self.error)

        return self.data


# ==============================================================================
# Main
# ==============================================================================

if __name__ == '__main__':

    import compas
    import compas_rhino

    from compas.datastructures import Mesh
    from compas.utilities import XFunc
    from compas_rhino.helpers import MeshArtist

    mesh = Mesh.from_obj(compas.get('faces.obj'))

    vertices = mesh.get_vertices_attributes('xyz')
    edges    = list(mesh.edges())
    fixed    = list([key for key in mesh.vertices() if mesh.vertex_degree(key) == 2])
    q        = mesh.get_edges_attribute('q', 1.0)
    loads    = mesh.get_vertices_attributes(('px', 'py', 'pz'), (0.0, 0.0, 0.0))

    xyz, q, f, l, r = XFunc('compas.numerical.fd_numpy')(vertices, edges, fixed, q, loads)

    for key, attr in mesh.vertices(True):
        attr['x'] = xyz[key][0]
        attr['y'] = xyz[key][1]
        attr['z'] = xyz[key][2]

    artist = MeshArtist(mesh)

    artist.clear()

    artist.draw_vertices()
    artist.draw_edges()

    artist.redraw()

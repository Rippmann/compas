from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from math import cos
from math import pi

from compas.geometry import centroid_points


__author__     = 'Tom Van Mele'
__copyright__  = 'Copyright 2014, Block Research Group - ETH Zurich'
__license__    = 'MIT License'
__email__      = 'vanmelet@ethz.ch'


__all__ = [
    'mesh_subdivide',
    'mesh_subdivide_tri',
    'mesh_subdivide_corner',
    'mesh_subdivide_quad',
    'mesh_subdivide_catmullclark',
    'mesh_subdivide_doosabin',
    'trimesh_subdivide_loop',
]


# distinguish between subd of meshes with and without boundary
# closed vs. open
# pay attention to extraordinary points
# and to special rules on boundaries
# interpolation vs. approxmation?!
# add numerical versions to compas.datastructures.mesh.(algorithms.)numerical
# investigate meaning and definition of limit surface
# any subd algorithm should return a new subd mesh, leaving the control mesh intact


def mesh_subdivide(mesh, scheme='tri', **options):
    """Subdivide the input mesh.

    Parameters
    ----------
    mesh : Mesh
        A mesh object.
    scheme : {'tri', 'corner', 'catmullclark', 'doosabin'}.
        The scheme according to which the mesh should be subdivided.
    options : dict
        Optional additional keyword arguments.

    Returns
    -------
    Mesh
        The subdivided mesh.

    Raises
    ------
    NotImplementedError
        If the scheme is not supported.

    """
    if scheme == 'tri':
        return mesh_subdivide_tri(mesh, **options)
    if scheme == 'quad':
        return mesh_subdivide_quad(mesh, **options)
    if scheme == 'corner':
        return mesh_subdivide_corner(mesh, **options)
    if scheme == 'catmullclark':
        return mesh_subdivide_catmullclark(mesh, **options)
    if scheme == 'doosabin':
        return mesh_subdivide_doosabin(mesh, **options)

    raise NotImplementedError


def mesh_subdivide_tri(mesh, k=1):
    """Subdivide a mesh using simple insertion of vertices.

    Parameters
    ----------
    mesh : Mesh
        The mesh object that will be subdivided.
    k : int
        Optional. The number of levels of subdivision. Default is ``1``.

    Returns
    -------
    Mesh
        A new subdivided mesh.

    """

    for _ in range(k):
        subd = mesh.copy()

        for fkey in mesh.faces():
            subd.insert_vertex(fkey)

        mesh = subd

    return mesh


def mesh_subdivide_quad(mesh, k=1):
    """Subdivide a mesh such that all faces are quads.
    """

    for _ in range(k):
        subd = mesh.copy()

        for u, v in list(subd.halfedges()):
            subd.split_edge(u, v, allow_boundary=True)

        for fkey in mesh.faces():

            descendant = {i: j for i, j in subd.face_halfedges(fkey)}
            ancestor = {j: i for i, j in subd.face_halfedges(fkey)}

            x, y, z = mesh.face_centroid(fkey)
            c = subd.add_vertex(x=x, y=y, z=z)

            for key in mesh.face_vertices(fkey):
                a = ancestor[key]
                d = descendant[key]
                subd.add_face([a, key, d, c])

            del subd.face[fkey]

        mesh = subd

    return mesh


def mesh_subdivide_corner(mesh, k=1):
    """Subdivide a mesh by cutting croners.

    Parameters
    ----------
    mesh : Mesh
        The mesh object that will be subdivided.
    k : int
        Optional. The number of levels of subdivision. Default is ``1``.

    Returns
    -------
    Mesh
        A new subdivided mesh.

    Returns
    -------
    Mesh
        The subdivided mesh.

    Notes
    -----
    This is essentially the same as Loop subdivision, but applied to general
    meshes.

    """

    for _ in range(k):
        subd = mesh.copy()

        # split every edge
        for u, v in list(subd.halfedges()):
            subd.split_edge(u, v, allow_boundary=True)

        # create 4 new faces for every old face
        for fkey in mesh.faces():

            descendant = {i: j for i, j in subd.face_halfedges(fkey)}
            ancestor = {j: i for i, j in subd.face_halfedges(fkey)}

            center = []

            for key in mesh.face_vertices(fkey):
                a = ancestor[key]
                d = descendant[key]

                subd.add_face([a, key, d])

                center.append(a)

            subd.add_face(center)
            del subd.face[fkey]

        mesh = subd

    return mesh


def mesh_subdivide_catmullclark(mesh, k=1, fixed=None):
    """Subdivide a mesh using the Catmull-Clark algorithm.

    Parameters
    ----------
    mesh : Mesh
        The mesh object that will be subdivided.
    k : int
        Optional. The number of levels of subdivision. Default is ``1``.
    fixed : list
        Optional. A list of fixed vertices. Default is ``None``.

    Returns
    -------
    Mesh
        A new subdivided mesh.

    Notes
    -----
    Note that *Catmull-Clark* subdivision is like *Quad* subdivision, but with
    smoothing after every level of further subdivision. Smoothing is done
    according to the scheme prescribed by the Catmull-Clark algorithm.

    Examples
    --------
    .. plot::
        :include-source:

        from compas.datastructures import Mesh
        from compas.topology import mesh_subdivide_catmullclark
        from compas.plotters import MeshPlotter

        vertices = [[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1.0, 0.]]
        faces = [[0, 1, 2, 3], ]

        mesh = Mesh.from_vertices_and_faces(vertices, faces)
        subd = mesh_subdivide_catmullclark(mesh, k=3, fixed=mesh.vertices())

        plotter = MeshPlotter(subd)

        plotter.draw_vertices(facecolor={key: '#ff0000' for key in mesh.vertices()}, radius=0.01)
        plotter.draw_faces()

        plotter.show()


    .. plot::
        :include-source:

        from compas.datastructures import Mesh
        from compas.topology import mesh_subdivide_catmullclark
        from compas.plotters import MeshPlotter

        vertices = [[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1.0, 0.]]
        faces = [[0, 1, 2, 3], ]

        mesh = Mesh.from_vertices_and_faces(vertices, faces)
        subd = mesh_subdivide_catmullclark(mesh, k=3, fixed=None)

        plotter = MeshPlotter(subd)

        plotter.draw_vertices(facecolor={key: '#ff0000' for key in mesh.vertices()}, radius=0.01)
        plotter.draw_faces()

        plotter.show()


    .. code-block:: python

        from compas.datastructures import Mesh

        from compas.topology import mesh_subdivide_catmullclark
        from compas.geometry import Polyhedron
        from compas.viewers import SubdMeshViewer

        cube = Polyhedron.generate(6)

        mesh = Mesh.from_vertices_and_faces(cube.vertices, cube.faces)

        viewer = SubdMeshViewer(mesh, subdfunc=mesh_subdivide_catmullclark, width=1440, height=900)

        viewer.axes_on = False
        viewer.grid_on = False

        for _ in range(10):
           viewer.camera.zoom_in()

        viewer.subdivide(k=4)

        viewer.setup()
        viewer.show()


    .. figure:: /_images/subdivide_mesh_catmullclark-screenshot.*
        :figclass: figure
        :class: figure-img img-fluid

    """
    if not fixed:
        fixed = []

    fixed = set(fixed)

    for _ in range(k):

        subd = mesh.copy()

        # keep track of original connectivity and vertex locations

        bkeys = set(subd.vertices_on_boundary())
        bkey_edgepoints = {key: [] for key in bkeys}

        # apply quad meshivision scheme
        # keep track of the created edge points that are not on the boundary
        # keep track track of the new edge points on the boundary
        # and their relation to the previous boundary points

        edgepoints = []

        for u, v in list(subd.halfedges()):

            w = subd.split_edge(u, v, allow_boundary=True)

            # document why this is necessary
            # everything else in this loop is just quad subdivision
            if u in bkeys and v in bkeys:

                bkey_edgepoints[u].append(w)
                bkey_edgepoints[v].append(w)

                continue

            edgepoints.append(w)

        for fkey in mesh.faces():

            descendant = {i: j for i, j in subd.face_halfedges(fkey)}
            ancestor = {j: i for i, j in subd.face_halfedges(fkey)}

            x, y, z = mesh.face_centroid(fkey)
            c = subd.add_vertex(x=x, y=y, z=z)

            for key in mesh.face_vertices(fkey):
                a = ancestor[key]
                d = descendant[key]
                subd.add_face([a, key, d, c])

            del subd.face[fkey]

        # these are the coordinates before updating

        key_xyz = {key: subd.vertex_coordinates(key) for key in subd.vertex}

        # move each edge point to the average of the neighbouring centroids and
        # the original end points

        for w in edgepoints:
            x, y, z = centroid_points([key_xyz[nbr] for nbr in subd.halfedge[w]])

            subd.vertex[w]['x'] = x
            subd.vertex[w]['y'] = y
            subd.vertex[w]['z'] = z

        # move each vertex to the weighted average of itself, the neighbouring
        # centroids and the neighbouring mipoints

        for key in mesh.vertices():
            if key in fixed:
                continue

            if key in bkeys:
                nbrs = set(bkey_edgepoints[key])
                nbrs = [key_xyz[nbr] for nbr in nbrs]
                e = 0.5
                v = 0.5
                E = [coord * e for coord in centroid_points(nbrs)]
                V = [coord * v for coord in key_xyz[key]]
                x, y, z = [E[_] + V[_] for _ in range(3)]

            else:
                fnbrs = [mesh.face_centroid(fkey) for fkey in mesh.vertex_faces(key) if fkey is not None]
                nbrs = [key_xyz[nbr] for nbr in subd.halfedge[key]]
                n = float(len(nbrs))
                f = 1.0 / n
                e = 2.0 / n
                v = (n - 3.0) / n
                F = [coord * f for coord in centroid_points(fnbrs)]
                E = [coord * e for coord in centroid_points(nbrs)]
                V = [coord * v for coord in key_xyz[key]]
                x, y, z = [F[_] + E[_] + V[_] for _ in range(3)]

            subd.vertex[key]['x'] = x
            subd.vertex[key]['y'] = y
            subd.vertex[key]['z'] = z

        mesh = subd

    return mesh


def mesh_subdivide_doosabin(mesh, k=1, fixed=None):
    """Subdivide a mesh following the doo-sabin scheme.

    Parameters
    ----------
    mesh : Mesh
        The mesh object that will be subdivided.
    k : int
        Optional. The number of levels of subdivision. Default is ``1``.
    fixed : list
        Optional. A list of fixed vertices. Default is ``None``.

    Returns
    -------
    Mesh
        A new subdivided mesh.

    """
    if not fixed:
        fixed = []

    fixed = set(fixed)

    cls = type(mesh)

    for _ in range(k):
        old_xyz      = {key: mesh.vertex_coordinates(key) for key in mesh.vertices()}
        fkey_old_new = {fkey: {} for fkey in mesh.faces()}

        subd = cls()

        for fkey in mesh.faces():
            vertices = mesh.face_vertices(fkey)
            n = len(vertices)

            for i in range(n):
                old = vertices[i]
                c = [0, 0, 0]

                for j in range(n):
                    xyz = old_xyz[vertices[j]]

                    if i == j:
                        alpha = (n + 5.) / (4. * n)
                    else:
                        alpha = (3. + 2. * cos(2. * pi * (i - j) / n)) / (4. * n)

                    c[0] += alpha * xyz[0]
                    c[1] += alpha * xyz[1]
                    c[2] += alpha * xyz[2]

                new = subd.add_vertex(x=c[0], y=c[1], z=c[2])
                fkey_old_new[fkey][old] = new

        for fkey in mesh.faces():
            vertices = mesh.face_vertices(fkey)
            old_new = fkey_old_new[fkey]
            subd.add_face([old_new[key] for key in vertices])

        for key in mesh.vertices():
            if mesh.is_vertex_on_boundary(key):
                continue

            face = []

            for fkey in mesh.vertex_faces(key, ordered=True):

                if fkey is not None:
                    face.append(fkey_old_new[fkey][key])

            subd.add_face(face[::-1])

        edges = set()

        for u in mesh.halfedge:
            for v in mesh.halfedge[u]:
                if (u, v) in edges:
                    continue

                edges.add((u, v))
                edges.add((v, u))
                uv_fkey = mesh.halfedge[u][v]
                vu_fkey = mesh.halfedge[v][u]

                if uv_fkey is None or vu_fkey is None:
                    continue

                face = []
                face.append(fkey_old_new[uv_fkey][u])
                face.append(fkey_old_new[vu_fkey][u])
                face.append(fkey_old_new[vu_fkey][v])
                face.append(fkey_old_new[uv_fkey][v])
                subd.add_face(face)

        mesh = subd

    return mesh


def trimesh_subdivide_loop(mesh, k=1, fixed=None):
    """Subdivide a triangle mesh using the Loop algorithm.

    Parameters
    ----------
    mesh : Mesh
        The mesh object that will be subdivided.
    k : int
        Optional. The number of levels of subdivision. Default is ``1``.
    fixed : list
        Optional. A list of fixed vertices. Default is ``None``.

    Returns
    -------
    Mesh
        A new subdivided mesh.

    Examples
    --------
    .. code-block:: python

        from compas.datastructures import Mesh
        from compas.topology import mesh_flip_cycle_directions
        from compas.plotters import SubdMeshViewer

        mesh = Mesh.from_polyhedron(4)
        mesh_flip_cycle_directions(mesh)

        viewer = SubdMeshViewer(mesh, subdfunc=loop_subdivision, width=600, height=600)

        viewer.axes_on = False
        viewer.grid_on = False

        for _ in range(10):
            viewer.camera.zoom_in()

        viewer.setup()
        viewer.show()

    """
    if not fixed:
        fixed = []

    fixed = set(fixed)

    subd = mesh.copy()

    for _ in range(k):
        key_xyz       = {key: subd.vertex_coordinates(key) for key in subd}
        fkey_vertices = {fkey: subd.face_vertices(fkey, ordered=True) for fkey in subd.face}
        uv_w          = {(u, v): subd.face[subd.halfedge[u][v]][v] for u in subd.halfedge for v in subd.halfedge[u]}
        edgepoints    = {}

        for key in subd:
            nbrs = subd.vertex_neighbours(key)
            n = len(nbrs)

            if n == 3:
                a = 3. / 16.
            else:
                a = (5. / 8. - (3. / 8. + 0.25 * cos(2 * pi / n)) ** 2) / n

            nbrs = [key_xyz[nbr] for nbr in nbrs]
            nbrs = [sum(axis) for axis in zip(*nbrs)]
            xyz = key_xyz[key]
            xyz = [(1. - n * a) * xyz[i] + a * nbrs[i] for i in range(3)]
            subd.vertex[key]['x'] = xyz[0]
            subd.vertex[key]['y'] = xyz[1]
            subd.vertex[key]['z'] = xyz[2]

        for u, v in list(subd.edges()):

            w = subd.split_edge(u, v, allow_boundary=True)

            edgepoints[(u, v)] = w
            edgepoints[(v, u)] = w
            v1 = key_xyz[u]
            v2 = key_xyz[v]
            vl = key_xyz[uv_w[(u, v)]]
            vr = key_xyz[uv_w[(v, u)]]
            xyz = [3. * (v1[i] + v2[i]) / 8. + (vl[i] + vr[i]) / 8. for i in range(3)]
            subd.vertex[w]['x'] = xyz[0]
            subd.vertex[w]['y'] = xyz[1]
            subd.vertex[w]['z'] = xyz[2]

        for fkey, vertices in fkey_vertices.items():
            u, v, w = vertices
            uv = edgepoints[(u, v)]
            vw = edgepoints[(v, w)]
            wu = edgepoints[(w, u)]
            subd.add_face([wu, u, uv])
            subd.add_face([uv, v, vw])
            subd.add_face([vw, w, wu])
            subd.add_face([uv, vw, wu])
            del subd.face[fkey]

    return subd


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":

    from compas.datastructures import Mesh

    from compas.topology import mesh_subdivide_catmullclark
    from compas.geometry import Polyhedron
    from compas.viewers import SubdMeshViewer

    cube = Polyhedron.generate(6)

    mesh = Mesh.from_vertices_and_faces(cube.vertices, cube.faces)

    viewer = SubdMeshViewer(mesh, subdfunc=mesh_subdivide_catmullclark, width=1440, height=900)

    viewer.axes_on = False
    viewer.grid_on = False

    for _ in range(10):
       viewer.camera.zoom_in()

    viewer.subdivide(k=4)

    viewer.setup()
    viewer.show()

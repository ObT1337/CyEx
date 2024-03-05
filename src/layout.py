import json
import os
from multiprocessing import Pool

import matplotlib.pyplot as plt
import networkx as nx
import numpy
import numpy as np
import pandas as pd
import swifter
import trimesh

from . import settings as st
from . import util
from .classes import LayoutAlgorithms as LA
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import VRNetzElements as VRNE
from .settings import log


class Layout:
    def __init__(
        self,
        name: str,
        algo: str,
        variables: dict[str : int or float],
        graph: nx.Graph,
        fm=None,
        dim=3,
    ):
        self.name: str = name
        self.algo: str = algo
        self.variables: dict[str : int or float] = variables
        self.graph: nx.Graph = graph
        self.dim: int = dim
        self.fm: pd.DataFrame = fm
        self._size: int = None
        self._opt_dist: float = None
        self._iterations: int = None
        self._threshold: float = None
        self._prplxty: float = None
        self._density: float = None
        self._l_rate: float = None
        self._steps: int = None
        self._n_neighbors: int = None
        self._spread: float = None
        self._min_dist: float = None
        self._spring_variables: dict = None
        self._tsne_variables: dict = None
        self._umap_variables: dict = None
        self.random_layout: bool = False
        self.pos: dict[str : list[float]] = {}
        self.feature_matrix: pd.DataFrame = None

    def __len__(self):
        return self.size

    @property
    def size(self):
        """Returns the number of nodes which are in this layout"""
        return len(self.pos)

    # SPRING variables
    @property
    def opt_dist(self):
        self._opt_dist = float(self.variables.get("opt_dist", 0))
        if self._opt_dist is not None:
            if self._opt_dist <= 0:
                self._opt_dist = None
        return self._opt_dist

    @property
    def iterations(self):
        self._iterations = int(self.variables.get("iterations", 50))
        return self._iterations

    @property
    def threshold(self):
        self._threshold = float(self.variables.get("threshold", 0.0001))
        return self._threshold

    # TSNE variables
    @property
    def prplxty(self):
        self._prplxty = float(self.variables.get("prplxty", 0.50))
        return self._prplxty

    @property
    def density(self):
        self._density = float(self.variables.get("density", 12))
        return self._density

    @property
    def l_rate(self):
        self._l_rate = float(self.variables.get("l_rate", 200))
        return self._l_rate

    @property
    def steps(self):
        self._steps = int(self.variables.get("steps", 250))
        return self._steps

    # UMAP variables
    @property
    def n_neighbors(self):
        self._n_neighbors = int(self.variables.get("n_neighbors", 10))
        return self._n_neighbors

    @property
    def spread(self):
        self._spread = float(self.variables.get("spread", 1.0))
        return self._spread

    @property
    def min_dist(self):
        self._min_dist = float(self.variables.get("min_dist", 0.1))
        return self._min_dist

    @property
    def spring_variables(self) -> dict:
        self._spring_variables = {
            "k": self.opt_dist,
            "iterations": self.iterations,
            "threshold": self.threshold,
        }
        return self._spring_variables

    @property
    def tsne_variables(self) -> dict:
        self._tsne_variables = {
            "prplxty": self.prplxty,
            "density": self.density,
            "l_rate": self.l_rate,
            "steps": self.steps,
        }
        return self._tsne_variables

    @property
    def umap_variables(self) -> dict:
        self._umap_variables = {
            "n_neighbors": self.n_neighbors,
            "spread": self.spread,
            "min_dist": self.min_dist,
        }
        return self._umap_variables

    def calculate_layout(self):
        if LA.cartoGRAPH in self.algo:
            self.create_cartoGRAPH_layout()
        elif LA.spring == self.algo:
            self.create_spring_layout()
        elif LA.kamada_kawai == self.algo:
            self.create_kamada_kawai_layout()

    def normalize_pos(self):
        self.pos = normalize_pos(self.pos, dim=self.dim)

    def create_spring_layout(self) -> dict:
        """Generates a spring layout for the Graph using the networkx spring_layout algorithm. All nodes without a link will be placed on a sphere around the center of the graph.

        Args:
            algo_variables (dict): contains variables for the algorithm.

        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        if self.random_layout:
            self.create_random_layout()
        self.link_based_layout(nx.spring_layout, self.spring_variables)

    def create_kamada_kawai_layout(self) -> dict:
        """Generates a kamada kawai layout for the Graph using the networkx kamada_kawai_layout algorithm. All nodes without a link will be placed on a sphere around the center of the graph.

        Args:
            algo_variables (dict): contains variables for the algorithm. Does not do anything.
        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        if self.random_layout:
            self.create_random_layout()
            return
        # TODO: CHECK WHETHER layout.pos should be set in every function or should be return by the functions an set from the responsible caller. First is prefered
        self.link_based_layout(nx.kamada_kawai_layout)

    def create_random_layout(self, graph=None) -> dict:
        if not graph:
            graph = self.graph
        self.pos = nx.random_layout(graph, dim=3)
        return self.pos

    def create_cartoGRAPH_layout(
        self,
    ) -> dict:
        """Will pick the correct cartoGRAPHs layout algorithm and apply it to the graph. If cartoGRAPH is not installed an ImportError is raised. In link based algorithms all nodes without a link will be placed on a sphere around the center of the graph. In functional algorithms all nodes without a feature will be placed on a sphere around the center of the graph.

        Args:
            layout_algo (str): layout algorithm to choose. possible algorithms are listed in setting.LayoutAlgroithms.
            cg_variables (dict, optional): contains algorithm variables. Defaults to None.

        Raises:
            ImportError: If cartoGRAPHs is not installed.
            NotImplementedError: If the chosen algorithm is not implemented yet ("topographic" and "geodesic")

        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        import cartoGRAPHs as cg

        dim = 3
        if "functional" in self.algo:
            features = self.feature_matrix.any(axis=1)
            no_feature_index = self.feature_matrix[~features].copy().index

            self.feature_matrix = self.feature_matrix[
                features
            ]  # Filtered feature matrix with out nodes without features

            feature_graph = self.graph.subgraph(self.feature_matrix.index)
            sphere_graph = self.graph.subgraph(no_feature_index)

        if "tsne" in self.algo:
            algo_variables = self.tsne_variables
            if "local" in self.algo:
                function = cg.layout_local_tsne
            elif "global" in self.algo:
                function = cg.layout_global_tsne
            elif "importance" in self.algo:
                function = cg.layout_importance_tsne
            elif "functional" in self.algo:
                if self.feature_matrix is None:
                    return ValueError("No feature matrix given.")
                if self.random_layout:
                    functional = self.create_random_layout(feature_graph)
                else:
                    functional = cg.layout_functional_tsne(
                        feature_graph,
                        self.feature_matrix,
                        dim,
                        **algo_variables,
                    )
                layout = sample_sphere(sphere_graph, list(functional.values()))
                functional.update(layout)
                self.pos = functional
                return

        elif "umap" in self.algo:
            algo_variables = self.umap_variables
            if "local" in self.algo:
                function = cg.layout_local_umap
            elif "global" in self.algo:
                function = cg.layout_global_umap
            elif "importance" in self.algo:
                function = cg.layout_importance_umap
            elif "functional" in self.algo:
                if self.feature_matrix is None:
                    return ValueError("No feature matrix given.")
                if self.random_layout:
                    functional = self.create_random_layout(feature_graph)
                else:
                    log.debug("Gen functional layout")
                    functional = cg.layout_functional_umap(
                        feature_graph,
                        self.feature_matrix,
                        dim,
                        **algo_variables,
                    )
                layout = sample_sphere(sphere_graph, list(functional.values()))
                functional.update(layout)
                self.pos = functional
                return

        elif "topographic" in self.algo:
            raise NotImplementedError("Topographic layout not implemented yet!")
            # d_z = a dictionary with keys=G.nodes and values=any int/float assigned to a node
            posG2D = nx.Graph()
            z_list = [np.random.random() for i in range(0, len(list(posG2D.nodes())))]
            d_z = dict(zip(list(posG2D.nodes()), z_list))
            return cg.layout_topographic(posG2D, d_z)

        elif "geodesic" in self.algo:
            raise NotImplementedError("Geodesic layout not implemented yet!")
            d_radius = 1
            n_neighbors = 8
            spread = 1.0
            min_dist = 0.0
            DM = None
            # radius_list_norm = preprocessing.minmax_scale((list(d_radius.values())), feature_range=(0, 1.0), axis=0, copy=True)
            # d_radius_norm = dict(zip(list(G.nodes()), radius_list_norm))
            return cg.layout_geodesic(
                self.graph, d_radius, n_neighbors, spread, min_dist, DM
            )

        self.link_based_layout(function, algo_variables)

    def link_based_layout(
        self,
        algorithm_func,
        algo_variables: dict = None,
    ) -> None:
        """Will apply a link based layout algorithm to the graph. All nodes with degree 0 will be placed on a sphere around the graph.

        Args:
            layout_algo (Callable): Layout function to apply.
            algo_variables (dict): dict with algorithm variables.
            random_lay (bool): If True, a random layout will be applied.
            G (networkx, optional): . Defaults to None. If None, self.graph will be used.

        Returns:
            dict[str,list[float,float,float]]: node ids as keys and three dimensional positions as values.
        """
        if algo_variables is None:
            algo_variables = {}

        no_links = self.graph.subgraph([n for n, d in self.graph.degree() if d == 0])
        has_links = self.graph.subgraph(
            [n for n in self.graph.nodes() if n not in no_links.nodes()]
        )
        log.debug(
            f"#Nodes with links: {len(has_links.nodes)}, #Nodes without links: {len(no_links.nodes)}"
        )
        log.debug(f"Algo variables:{algo_variables}")

        if self.random_layout:
            layout = self.create_random_layout(has_links)
        else:
            layout = algorithm_func(has_links, **algo_variables, dim=3)

        if len(no_links) > 0:
            no_links_layout = sample_sphere(no_links, list(layout.values()))
            layout.update(no_links_layout)

        self.pos = layout


def normalize_pos(
    layout: dict[int, np.array], dim: int = 3
) -> dict[str, list[float, float, float]]:
    """
    Normalizes the positions of the nodes in the layout to be between 0 and 1.

    Args:
        layout (dict[int, np.array]): Dictionary containing node ids as keys and a 3-tuple of coordinates as values.
        dim (int, optional): Defines the dimension in which the coordinates are. Defaults to 3.

    Returns:
        dict[str,list[float,float,float]]: Dictionary containing node ids as keys and a 3-tuple of coordinates as values. Now normalized in the range of 0 to 1.
    """
    layout = dict(sorted(layout.items(), key=lambda x: x[0]))
    pos = np.array(list(layout.values()))
    for i in range(0, dim):
        pos[:, i] += abs(min(pos[:, i]))
        pos[:, i] /= max(pos[:, i])
    layout = dict(zip(layout.keys(), pos))
    return layout


def sample_sphere_pcd(
    SAMPLE_POINTS=100, layout: list[list[float, float, float]] = None, debug=False
) -> np.array:
    """Utility function to sample points from a sphere using trimesh.

    Args:
        SAMPLE_POINTS (int, optional): Number of points to sample. Defaults to 100.
        layout (list, optional): List of points if the calculated Layout. Is used to center the sphere around this layout. Defaults to [].
        debug (bool, optional): Switch to show visualization of the process. Defaults to False.

    Returns:
        numpy.array: Array of sampled points with shape (SAMPLE_POINTS, 3)
    """
    if layout is None:
        layout = []

    if SAMPLE_POINTS == 0:
        return np.array([])

    # Create a sphere mesh centered at the layout point
    sphere = trimesh.creation.icosphere(radius=1, subdivisions=3)
    if layout:
        layout_center = np.mean(layout, axis=0)
        sphere.apply_translation(-layout_center)

    # Sample points uniformly on the sphere
    points, _ = trimesh.sample.sample_surface_even(sphere, SAMPLE_POINTS)

    if debug:
        scene = trimesh.Scene([sphere])
        scene.add_points(points)
        scene.show()

    return points


# # Open3D version
# def sample_sphere_pcd(
#     SAMPLE_POINTS=100,
#     layout: list[list[float, float, float]] = None,
#     debug=False,
# ) -> numpy.array:
#     """Utility function to sample points from a sphere. Can be used for functional layouts for node with no annotations.

#     Args:
#         SAMPLE_POINTS (int, optional): Number of points to sample. Defaults to 100.
#         layout (list, optional): List of points if the calculated Layout. Is used to center the sphere around this layout. Defaults to [].
#         debug (bool, optional): Switch to show visualization of the process. Defaults to False.

#     Returns:
#         numpy.array: Array of sampled points with shape (SAMPLE_POINTS, 3)
#     """
#     if layout is None:
#         layout = []

#     if SAMPLE_POINTS == 0:
#         return numpy.array([])
#     # get protein name & read mesh as .ply format
#     mesh = o3d.io.read_triangle_mesh(st.SPHERE)
#     mesh.compute_vertex_normals()
#     layout_pcd = o3d.geometry.PointCloud()
#     layout_pcd.points = o3d.utility.Vector3dVector(numpy.asarray(layout))
#     layout_pcd.paint_uniform_color([1, 0, 0])
#     layout_center = layout_pcd.get_center()
#     mesh.translate(layout_center, relative=False)
#     pcd = mesh.sample_points_uniformly(number_of_points=SAMPLE_POINTS)
#     pcd.paint_uniform_color([0, 1, 0])
#     if debug:
#         o3d.visualization.draw_geometries([pcd, layout_pcd])
#     return numpy.asarray(pcd.points)


# Deprecated until a replacement for open3d is found
# def visualize_layout(
#     layout: list[list[float, float, float]],
#     colors: list[list[float, float, float]],
# ) -> None:
#     """Visualize a layout with colors in 3D using open3D.

#     Args:
#         layout (list[list[float, float, float]]): List of points with shape (n, 3)
#         colors (list[list[float, float, float]]): List of colors of the points with shape (n, 3)

#     Returns:
#         None: None
#     """
#     pcd = o3d.geometry.PointCloud()
#     pcd.points = o3d.utility.Vector3dVector(numpy.asarray(layout))
#     pcd.colors = o3d.utility.Vector3dVector(numpy.asarray(colors))

#     def change_background_to_black(vis):
#         opt = vis.get_render_option()
#         opt.background_color = np.asarray([0, 0, 0])
#         return False

#     def change_background_to_white(vis):
#         opt = vis.get_render_option()
#         opt.background_color = np.asarray([1, 1, 1])
#         return False

#     key_to_callback = {}
#     key_to_callback[ord("K")] = change_background_to_black
#     key_to_callback[ord("L")] = change_background_to_white
#     key_to_callback[ord("P")] = exit

#     try:
#         o3d.visualization.draw_geometries_with_key_callbacks([pcd], key_to_callback)
#     except KeyboardInterrupt:
#         pass


def sample_sphere(
    G: nx.Graph, layout: list[float, float, float], *args: tuple, **kwargs: dict
) -> dict[str, list[float, float, float]]:
    """Samples a sphere around the given layout for as many nodes as provided with the graph.

    Args:
        G (nx.Graph): Graph for which the points should be sampled.
        layout (list[float, float, float]): Layout containing the remaining points. Is used as the center of the sphere.

    Returns:
        dict[str, list[float, float, float]]: Dictionary containing the node names as keys and the sampled points as values.
    """
    n = len(G)
    pos = sample_sphere_pcd(SAMPLE_POINTS=n, layout=layout, *args, **kwargs)
    layout = {}
    for i, node in enumerate(G.nodes()):
        layout[node] = pos[i]
    return layout


# Deprecated until a replacement for open3d is found
# def take_screenshot(
#     layout: list[float, float, float], color, *args, **kwargs
# ) -> np.ndarray:
#     visualize_layout(layout, color, *args, **kwargs)

# Deprecated until a replacement for open3d is found
# if __name__ == "__main__":
#     some_graph = nx.complete_graph(500)
#     pos = nx.spring_layout(some_graph, dim=3)
#     pos = list(pos.values())
#     sample_sphere_pcd(layout=pos, debug=True)

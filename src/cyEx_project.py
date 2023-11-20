import json

import networkx as nx
import numpy as np
import pandas as pd
from project import Project

from . import layout
from .classes import LayoutAlgorithms as LA
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import VRNetzElements as VRNE
from .layout import Layout, normalize_pos
from .settings import log


class CyExProject(Project):
    def __init__(
        self,
        name: str,
        network: dict[str : pd.DataFrame] = None,
        overwrite=True,
    ):
        super().__init__(name)
        self.network: dict[str : pd.DataFrame] = network
        self.graph: nx.Graph = None
        self._size: tuple(
            int, int
        ) = None  # 2-Tuple (N,L) of N number of nodes and L number of l^inks
        self._n: int = None
        self._l: int = None
        if type(self.network) is dict:
            self.network[VRNE.nodes] = pd.DataFrame(self.network[VRNE.nodes])
            self.network[VRNE.links] = pd.DataFrame(self.network[VRNE.links])
            self.graph = self.gen_graph(network[VRNE.nodes], network[VRNE.links])
        else:
            self.graph = self.read_from_vrnetz(network)

        self._is_string_network: bool = False
        self.overwrite: bool = overwrite
        self.layouts: list[Layout] = []
        # #TODO: How to handle overwrites

        # if form["string_namespace"] == "New":
        #     project_name = form["string_new_namespace_name"]
        #     overwrite_project = True
        # else:
        #     project_name = form["existing_namespace"]

    @property
    def size(self):
        if not isinstance(self.graph, nx.Graph):
            return None
        self._size = (self.graph.number_of_nodes(), self.graph.number_of_edges())
        return self._size

    @property
    def n(self):
        return self.size[0]

    @property
    def l(self):
        return self.size[1]

    @property
    def is_string_network(self):
        self._is_string_network = False

        if "database" in self.network[VRNE.network]:
            if self.network[VRNE.network]["database"] in ["string", "stitch"]:
                self._is_string_network = True

        return self._is_string_network

    def add_layout(self, *args, **kwargs):
        if self.graph is None:
            self.gen_graph(self.network[VRNE.nodes], self.network[VRNE.links])
        log.debug(
            f"Adding the Layout using the following arguments: {args} and keyword arguments:{kwargs}. An the Graph {self.graph}"
        )
        self.layouts.append(Layout(*args, graph=self.graph, **kwargs))

    def read_from_grahpml(self, file: str) -> nx.Graph:
        """Read a graph from a graphml file.

        Args:
            file (str): path to the graphml file.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        self.graph = nx.read_graphml(file)
        return self.graph

    def read_from_vrnetz(self, file: str) -> nx.Graph:
        """Reads a graph from a VRNetz file.

        Args:
            file (str): Path to a VRNetz file.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        network = json.load(open(file))
        self.network = network
        nodes = network[VRNE.nodes]
        links = network[VRNE.links]
        return self.gen_graph(nodes, links)

    def get_node_data(self, node: str) -> dict:
        """Get the data of the desired node.

        Args:
            node (str): id of the desired node.

        Returns:
            dict: containing all data of a node
        """
        if "data" not in self.graph.nodes[node]:
            self.graph.nodes[node]["data"] = {}
        # self.graph.nodes[node].get("data",{}) # might work not sure
        return self.graph.nodes[node]["data"]

    def set_node_data(self, node: str, data: dict) -> None:
        """Set the dat of a desired node.

        Args:
            node (str):  id of the desired node.
            data (dict): containing all data of a node
        """
        self.graph.nodes[node]["data"] = data

    def add_layouts_to_network(self, layouts=None) -> None:
        """Adds the points of the generated layout to the underlying VRNetz

        Args:
            layout (dict): Dictionary containing node ids as keys and a 3-tuple of coordinates as values.
            layout_name (str): Name of the layout to be added to the VRNetz.

        Returns:
            pd.DataFrame: nodes data frame with added layout.
        """
        if layouts is None:
            layouts = self.layouts
        nodes = self.network[VRNE.nodes]
        log.debug(f"Layouts to handle {', '.join([l.name for l in layouts])}")
        for l in layouts:
            pos = np.array(list((l.pos.values())))
            _2d_layout = pos[:, :2]
            z_zero = np.zeros((l.size, 1))
            _2d_layout = np.hstack((_2d_layout, z_zero))

            nodes[l.name + "2d_pos"] = pd.Series(_2d_layout.tolist())
            nodes[l.name + "_pos"] = pd.Series(pos.tolist())
        self.network[VRNE.nodes] = nodes

    def calculate_layouts(self):
        ## Handle Nodes
        for layout in self.layouts:
            layout.calculate_layout()
            layout.normalize_pos()
        self.handle_cy_layout()
        self.add_layouts_to_network()

        ## Handle Links
        # TODO: CONSIDER FOR STRING NETWORKS
        # links = generator.gen_evidence_layouts(
        #     generator.network[VRNE.links], stringify=stringify
        # )
        self.network[VRNE.links]["all_col"] = [(200, 200, 200, 255)] * self.l
        links = self.network[VRNE.links]
        drops = ["s_suid", "e_suid"]
        for c in drops:
            if c in links.columns:
                links = links.drop(columns=[c])
        self.network[VRNE.links] = links

    def handle_cy_layout(self):
        ### If its an old VRNetz format this will change it to the new.
        nodes = self.network[VRNE.nodes]

        if NT.layouts in nodes:

            def extract_cy(x):
                if NT.layouts not in x:
                    return x
                layout = x[NT.layouts][0]
                x["cy_pos"] = layout["p"]
                x["cy_col"] = layout["c"]
                x["size"] = layout["s"]
                return x

            nodes = nodes.swifter.progress_bar(False).apply(extract_cy, axis=1)

        if "cy_pos" and "cy_col" in nodes:
            coords = nodes["cy_pos"].to_dict()
            pos = np.array(list(normalize_pos(coords, dim=2).values()))
            pos = np.hstack((pos, np.zeros((len(pos), 1))))
            nodes["cy_pos"] = pd.Series(pos.tolist())

            def extract_color(x):
                """Scale alpha channel (glowing effect) with node size (max size = 1"""
                col = x["cy_col"] + [int(255 * x["size"])]
                return col

            max_size = max(nodes["size"])
            nodes["size"] = (
                nodes["size"].swifter.progress_bar(False).apply(lambda x: x / max_size)
            )
            nodes["cy_col"] = (
                nodes[["cy_col", "size"]]
                .swifter.progress_bar(False)
                .apply(extract_color, axis=1)
            )

        self.network[VRNE.nodes] = nodes

    @staticmethod
    def gen_graph(nodes: dict = None, links: dict = None) -> nx.Graph:
        """Generates a networkx graph based on a dict of nodes and links.

        Args:
            nodes (dict): contains all nodes that should be part of the graph with node ids as keys and nodes as values.
            links (dict): contains all links that should be part of the graph with link ids as keys and links as values.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        G = nx.Graph()
        G.add_nodes_from([(idx, node.dropna()) for idx, node in nodes.iterrows()])
        G.add_edges_from(
            [(start, end) for start, end in links[[LiT.start, LiT.end]].values.tolist()]
        )
        return G

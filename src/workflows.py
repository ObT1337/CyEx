import glob
import json
import os
import pickle
import shutil
import time
import traceback

import flask
import pandas as pd
from project import Project

from . import util as string_util
from .classes import VRNetzElements as VRNE
from .layouter import Layouter
from .settings import _NETWORKS_PATH, _PROJECTS_PATH, UNIPROT_MAP, log
from .uploader import Uploader


def VRNetzer_upload_workflow(
    network: dict,
    filename: str,
    project_name: str,
    algo: str = "string",
    tags: dict = None,
    algo_variables: dict = None,
    layout_name: str = None,
    overwrite_project: bool = False,
) -> str:
    """Used from the StringEX/uploadfiles route to upload VRNetz networks to the VRNetzer.

    Args:
        network (dict): Loaded network (loaded with json.load).
        filename (str): Name of the network file which is uploaded
        project_name (str): Name of the project to be created.
        algo(str,optional): Name of the layout algorithm to be used. Defaults to "string".
        tags (dict,optional): Dictionary of tags to options in underlying functions. Defaults to None.
        cg_variables (dict, optional): dictionary containing varaibles for cartoGRAPHs variables. Defaults to None.

    Returns:
        str: HTML string to reflect whether the upload was successful or not.
    """
    if type(network) is dict:
        network[VRNE.nodes] = pd.DataFrame(network[VRNE.nodes])
        network[VRNE.links] = pd.DataFrame(network[VRNE.links])
    if tags is None:
        tags = {
            "stringify": False,
            "string_write": False,
            "string_calc_lay": False,
        }

    if algo_variables is None:
        algo_variables = {}
    log.info("Starting upload of VRNetz...")
    start = time.time()

    log.debug(f"Network loaded in {time.time()-start} seconds.")
    log.info(f"Network loaded from {filename}.", flush=True)

    if not project_name:
        return "namespace fail"

    # create layout
    log.info(f"Applying layout algorithm:{algo}", flush=True)
    s1 = time.time()
    layouter = apply_layout_workflow(
        network,
        layout_algo=algo,
        stringify=tags.get("stringify"),
        gen_layout=tags.get("string_calc_lay"),
        algo_variables=algo_variables,
        layout_name=layout_name,
    )
    log.debug(f"Applying layout algorithm in {time.time()-s1} seconds.")
    log.info(f"Applied layout algorithm:{algo}", flush=True)
    network = layouter.network
    # upload network
    uploader = Uploader(
        network,
        p_name=project_name,
        stringify=tags.get("stringify"),
        overwrite_project=overwrite_project,
    )
    s1 = time.time()
    state = uploader.upload_files(network)
    log.debug(f"Uploading process took {time.time()-s1} seconds.")
    log.info(f"Uploading network...", flush=True)
    if tags.get("string_write"):
        outfile = f"{_NETWORKS_PATH}/{project_name}_processed.VRNetz"
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        with open(outfile, "w") as f:
            json.dump(network, f)
        log.info(f"Saved network as {outfile}")
    log.debug(f"Total process took {time.time()-s1} seconds.", flush=True)
    log.info("Project has been uploaded!")
    html = (
        f'<a style="color:green;"href="/StringEx/preview?project={project_name}" target="_blank" >SUCCESS: Network {filename} saved as project {project_name} </a><br>'
        + state
    )

    return html


def VRNetzer_send_network_workflow(request: dict, blueprint: flask.Blueprint):
    """
    Accepts a Network from Cytoscape and creates a project for the VRNetzer based on the send network, the selected layout algorithm and its parameters.

    Args:
        request (dict): Request from Cytoscape containing the network, the layout algorithm and its parameters, the project name and the overwrite option.
        blueprint (flask.Blueprint): Blueprint of the VRNetzer app.

    Returns:
        str: HTML page reporting the success of the project creation which contains a link to a page where the project report is shown and the network can directly be opened in the VRNetzer.
    """
    network = {
        "nodes": request.pop("nodes"),
        "links": request.pop("links"),
        "layouts": request.pop("layouts"),
    }
    form = request.get("form")
    layout_name = form.get("layout")
    to_running = form.get("load")
    algo = form["algorithm"]["n"]
    algo_variables = string_util.get_algo_variables(algo, form["algorithm"])
    network_data = request.get("network")
    # enrichments = request.get("enrichments")
    # publications = request.get("publications")

    project_name = form["project"]
    overwrite_project = form["update"]
    if overwrite_project == "Update":
        overwrite_project = False
    else:
        overwrite_project = True
    tags = {
        "stringify": False,
        "string_write": False,
        "string_calc_lay": True,
    }
    if network_data.get("database") in ["string", "stitch"]:
        tags["stringify"] = True
    log.debug(f"STRINGIFY {tags['stringify']}")
    output = VRNetzer_upload_workflow(
        network,
        project_name,
        project_name,
        algo,
        tags,
        algo_variables,
        layout_name,
        overwrite_project=overwrite_project,
    )
    if to_running:
        string_util.set_project(blueprint, project_name)
        # {'usr': '2nmmy7P0IG', 'msg': 'string_arabidopsis_ppi', 'id': 'projDD', 'val': '2', 'fn': 'dropdown'}
    return output[1:]


def apply_layout_workflow(
    network: str or dict,
    gen_layout: bool = True,
    layout_algo: str = None,
    stringify: bool = True,
    algo_variables: dict = {},
    layout_name: str = None,
) -> Layouter:
    """
    Applies a layout algorithm to a network and returns a Layouter object.

    Args:
        network (str): Path to the network file or a dictionary containing the network.
        gen_layout (bool, optional): If True, the layout algorithm is applied. Defaults to True.
        layout_algo (str, optional): Name of the layout algorithm. Defaults to None.
        stringify (bool, optional): Indicates whether the network is a STRING network. Defaults to True.
        algo_variables (dict, optional): Dictionary containing the parameters of the layout algorithm. Defaults to {}.
        layout_name (str, optional): Name of the layout. Defaults to None.
    """
    layouter = Layouter()
    if type(network) is dict:
        network[VRNE.nodes] = pd.DataFrame(network[VRNE.nodes])
        network[VRNE.links] = pd.DataFrame(network[VRNE.links])
        layouter.network = network
        layouter.graph = layouter.gen_graph(network[VRNE.nodes], network[VRNE.links])
    else:
        layouter.read_from_vrnetz(network)
        log.info(f"Network extracted from: {network}")

    if gen_layout:
        if layout_algo is None:
            layout_algo = "spring"
        log.info(f"Applying algorithm {layout_algo} ...")
        layout = layouter.apply_layout(layout_algo, algo_variables)
        algo, layout = next(iter(layout.items()))
        nodes = layouter.add_layout_to_vrnetz(
            layouter.network[VRNE.nodes], layout, layout_name
        )
        layouter.network[VRNE.nodes] = nodes
        log.info(f"Layout algorithm {layout_algo} applied!")
    links = Layouter.gen_evidence_layouts(
        layouter.network[VRNE.links], stringify=stringify
    )
    drops = ["s_suid", "e_suid"]
    for c in drops:
        if c in links.columns:
            links = links.drop(columns=[c])
    layouter.network[VRNE.links] = links
    return layouter

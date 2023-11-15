import json
import os
import time

import flask
import pandas as pd

from . import util as string_util
from .classes import VRNetzElements as VRNE
from .layout_generator import LayoutGenerator
from .settings import _NETWORKS_PATH, log
from .uploader import Uploader


def VRNetzer_upload_workflow(
    network: dict,
    filename: str,
    project_name: str,
    layout_algos: list[str] = ["string"],
    tags: dict = None,
    algo_variables: list[dict] = None,
    layout_names: list[str] = None,
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
    if tags is None:
        tags = {
            "stringify": False,
            "string_write": False,
            "string_calc_lay": True,
        }

    if algo_variables is None:
        algo_variables = [{}]
    log.info("Starting upload of VRNetz...")
    start = time.time()

    log.debug(f"Network loaded in {time.time()-start} seconds.")
    log.info(f"Network loaded from {filename}.", flush=True)

    if not project_name:
        return "namespace fail"

    # TODO: if Overwrite Project, delete the project before this
    state = ""
    log.info(
        f"Calculating layouts using the the following algorithms: {layout_algos}"
        + f"which results in the following layouts: {layout_names}."
    )
    s1 = time.time()
    log.debug(f"Generating Layout is set to {tags.get('string_calc_lay')}")
    generator = calculate_layouts_workflow(
        network,
        layout_algorithms=layout_algos,
        stringify=tags.get("stringify"),
        gen_layout=tags.get("string_calc_lay"),
        algo_variables=algo_variables,
        layout_names=layout_names,
    )
    log.debug(f"Applied layout algorithm in {time.time()-s1} seconds.")
    network = generator.network
    log.debug(list(network["nodes"].columns))
    # upload network
    uploader = Uploader(
        network,
        p_name=project_name,
        stringify=tags.get("stringify"),
        overwrite_project=False,
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


def calculate_layouts_workflow(
    network: str or dict,
    gen_layout: bool = True,
    layout_algorithms: str = None,
    stringify: bool = True,
    algo_variables: dict = {},
    layout_names: str = None,
) -> LayoutGenerator:
    """
    Applies a layout algorithm to a network and returns a LayoutGenerator object.

    Args:
        network (str): Path to the network file or a dictionary containing the network.
        gen_layout (bool, optional): If True, the layout algorithm is applied. Defaults to True.
        layout_algo (str, optional): Name of the layout algorithm. Defaults to None.
        stringify (bool, optional): Indicates whether the network is a STRING network. Defaults to True.
        algo_variables (dict, optional): Dictionary containing the parameters of the layout algorithm. Defaults to {}.
        layout_name (str, optional): Name of the layout. Defaults to None.
    """
    generator = LayoutGenerator()
    if type(network) is dict:
        network[VRNE.nodes] = pd.DataFrame(network[VRNE.nodes])
        network[VRNE.links] = pd.DataFrame(network[VRNE.links])
        generator.network = network
        generator.graph = generator.gen_graph(network[VRNE.nodes], network[VRNE.links])
    else:
        generator.read_from_vrnetz(network)
        log.info(f"Network extracted from: {network}")

    ## Handle Nodes
    log.debug(f"Generating Layout is set to {gen_layout}")
    if gen_layout:
        if layout_algorithms is None:
            layout_algorithms = ["spring"]
        layouts = generator.apply_layout(layout_algorithms, algo_variables)
        layouts = {
            name: layouts[old_key]
            for old_key, name in zip(layouts.keys(), layout_names)
        }
        nodes = generator.add_layouts_to_vrnetz(generator.network[VRNE.nodes], layouts)
        generator.network[VRNE.nodes] = nodes
        log.info(f"Following algorithms have been applied: {layout_algorithms}!")

    ## Handle Links
    # TODO: CONSIDER FOR STRING NETWORKS
    # links = generator.gen_evidence_layouts(
    #     generator.network[VRNE.links], stringify=stringify
    # )
    num_links = len(generator.network[VRNE.links])
    generator.network[VRNE.links]["all_col"] = [(200, 200, 200, 255)] * num_links
    links = generator.network[VRNE.links]
    drops = ["s_suid", "e_suid"]
    for c in drops:
        if c in links.columns:
            links = links.drop(columns=[c])
    generator.network[VRNE.links] = links

    return generator

import json
import os
import time

import flask
import pandas as pd

from . import util as string_util
from .classes import VRNetzElements as VRNE
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
    # TODO: if Overwrite Project, delete the project before this
    state = ""
    log.info(
        f"Calculating layouts using the the following algorithms: {layout_algos}"
        + f"which results in the following layouts: {layout_names}."
    )
    s1 = time.time()

    log.debug(f"Applied layout algorithm in {time.time()-s1} seconds.")
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

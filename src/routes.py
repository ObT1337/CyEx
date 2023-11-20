import json
import os
import time

import flask

from . import settings as st
from . import util as my_util
from . import workflows as wf
from .classes import VRNetzElements as VRNE
from .cyEx_project import CyExProject
from .settings import log
from .uploader import Uploader


def upload_vrnetz():
    """Use the submitted file to create a VRNetzer project.
    Submitted file is a VRNetz file. The file is parsed and the project is created. Reports if VRNetz file is missing or if its wrongly formatted.
    """

    ### Initialization
    form = flask.request.form.to_dict()
    vr_netz_files = flask.request.files.getlist("cyEx_vrnetz")
    if len(vr_netz_files) == 0 or vr_netz_files[0].filename == "":
        st.log.error("No VRNetz file provided!")
        return '<a style="color:red;"href="/upload">ERROR invalid VRNetz file!</a>'
    network_file = vr_netz_files[0]
    network = network_file.read().decode("utf-8")
    try:
        network = json.loads(network)
    except json.decoder.JSONDecodeError:
        st.log.error(f"Invalid VRNetz file:{network_file.filename}")
        return '<a style="color:red;">ERROR invalid VRNetz file!</a>'

    project_name = form["CyEx_project_name"]
    project = CyExProject(project_name, network)

    ## Prepare layout informations
    i = 1
    algos = []
    layout_names = []
    algo_variables = []
    st.log.debug(form)
    while True:
        name = f"layout_{i}_name"
        algo = f"layout_{i}_algo"
        if name not in form and algo not in form:
            break
        algo = form[algo]
        layout_name = form[name]

        variables = {
            key: float(form[f"layout_{i}_{key}"])
            for key in [
                "opt_dis",
                "iterations",
                "prplxty",
                "density",
                "l_rate",
                "steps",
                "n_neighbors",
                "spread",
                "min_dist",
            ]
        }
        variables["iterations"] = int(variables["iterations"])
        variables["steps"] = int(variables["steps"])
        variables["n_neighbors"] = int(variables["n_neighbors"])
        project.add_layout(
            layout_name,
            algo,
            variables,
        )
        i += 1

    project.calculate_layouts()

    uploader = Uploader(project)
    s1 = time.time()
    state = uploader.upload_files()
    log.debug(f"Uploading process took {time.time()-s1} seconds.")
    log.info(f"Uploading network...", flush=True)

    ## TODO: Not sure if necessary, was nice for debugging
    # if tags.get("string_write"):
    #     outfile = f"{st._NETWORKS_PATH}/{project_name}_processed.VRNetz"
    #     os.makedirs(os.path.dirname(outfile), exist_ok=True)

    #     with open(outfile, "w") as f:
    #         json.dump(network, f)
    #     log.info(f"Saved network as {outfile}")

    log.debug(f"Total process took {time.time()-s1} seconds.", flush=True)
    log.info("Project has been uploaded!")

    html = (
        f'<a style="color:green;"href="/StringEx/preview?project={project_name}" target="_blank" >SUCCESS: Network {project.name} saved as project {project_name} </a><br>'
        + state
    )

    return html

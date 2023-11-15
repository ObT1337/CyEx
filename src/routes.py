import json

import flask

from . import settings as st
from . import util as my_util
from . import workflows as wf
from .classes import VRNetzElements as VRNE


def upload_vrnetz():
    """Use the submitted file to create a VRNetzer project.
    Submitted file is a VRNetz file. The file is parsed and the project is created. Reports if VRNetz file is missing or if its wrongly formatted.
    """
    form = flask.request.form.to_dict()
    vr_netz_files = flask.request.files.getlist("cyEx_vrnetz")
    if len(vr_netz_files) == 0 or vr_netz_files[0].filename == "":
        st.log.error(f"No VRNetz file provided!")
        return '<a style="color:red;"href="/upload">ERROR invalid VRNetz file!</a>'
    network_file = vr_netz_files[0]
    network = network_file.read().decode("utf-8")
    try:
        network = json.loads(network)
    except json.decoder.JSONDecodeError:
        st.log.error(f"Invalid VRNetz file:{network_file.filename}")
        return '<a style="color:red;">ERROR invalid VRNetz file!</a>'
    project_name = form["CyEx_project_name"]
    overwrite_project = False

    # #TODO: How to handle overwrites
    # if form["string_namespace"] == "New":
    #     project_name = form["string_new_namespace_name"]
    #     overwrite_project = True
    # else:
    #     project_name = form["existing_namespace"]
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
        algos.append(form[algo])
        layout_names.append(form[name])

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
        algo_variables.append(variables)
        i += 1
    tags = {
        "stringify": False,
        "string_write": False,
        "string_calc_lay": True,
    }
    # for key, _ in tags.items():
    #     if key in form:
    #         tags[key] = True
    if "database" in network[VRNE.network]:
        if network[VRNE.network]["database"] in ["string", "stitch"]:
            tags["stringify"] = True

    return wf.VRNetzer_upload_workflow(
        network,
        network_file.filename,
        project_name,
        algos,
        tags,
        algo_variables,
        layout_names,
        overwrite_project=overwrite_project,
    )

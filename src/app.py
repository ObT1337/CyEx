import json
import multiprocessing as mp
import os

import flask
import GlobalData as GD
from io_blueprint import IOBlueprint
from project import Project

import util

from . import routes
from . import settings as st
from . import util as my_util
from . import workflows as wf
from .classes import LayoutAlgorithms
from .send_to_cytoscape import send_to_cytoscape
from .settings import log
url_prefix = "/CyEx"

blueprint = IOBlueprint(
    "CyEx",
    __name__,
    url_prefix=url_prefix,
    template_folder=st._THIS_EXT_TEMPLATE_PATH,
    static_folder=st._THIS_EXT_STATIC_PATH,
)

column_4 = ["cyEx_send_module.html"]
upload_tabs = []

my_util.pepare_uploader()
my_util.move_on_boot()


@blueprint.before_app_first_request
# Execute before first request


@blueprint.route("/uploadfiles", methods=["GET", "POST"])
def string_ex_upload_files() -> str:
    """This route is used to upload a VRNetz using the STRING Uploader. A POST request is send to it, when a user clicks the "upload" button.

    Returns:
        str: A status giving information whether the upload was successful or not.
    """
    return routes.upload_files()



@blueprint.route("/receiveNetwork", methods=["POST"])
def string_ex_receive_network_json():
    """This route accepts a network in the form of a JSON object. The JSON object is then used downstream to create a VRNetzer project out of it. This route is mainly used to send a network to the VRNetzer from Cytoscape."""
    receiveNetwork = flask.request.get_json()
    wf.VRNetzer_send_network_workflow(receiveNetwork, blueprint)
    project = receiveNetwork["form"]["project"]
    return json.dumps({"url": f"/StringEx/resultPage/{project}"})


@blueprint.route("/resultPage/<project>", methods=["GET"])
def string_ex_result_page(project):
    """Is used to present that the sending of a network was successful and provides access to layout changing etc. Used in the to provide Cytoscape user with the result of the network upload process."""
    username = util.generate_username()
    layouts = ""
    flask.session["username"] = username
    flask.session["room"] = 1
    project = Project(project)
    return flask.render_template(
        "string_send_result_page.html",
        project=project.name,
        layouts=layouts,
        pfile=project.pfile,
        pdata=json.dumps(project.pfile),
        # sessionData=json.dumps(GD.sessionData),
    )


@blueprint.route("/")
def string_ex_index():
    """Redirect to the main index page as the CyEx extension does not have a dedicated index page."""
    return flask.redirect("/")


@blueprint.route("/status", methods=["GET"])
def string_ex_status():
    """Route to check if the CyEx extension is installed and running."""
    return "CyEx is installed and running..."


@blueprint.on(
    "sendNetwork",
)
def string_send_to_cytoscape(message):
    """Is triggered by a call of a client. Will take the current selected nodes and links to send them to a running instance of Cytoscape. This will always send the network the Cytoscape session of the requesting user, if not otherwise specified. If to host is selected, the network will be send to the Cytoscape session of the Server host."""
    return_dict = mp.Manager().dict()
    ip = flask.request.remote_addr
    p = mp.Process(
        target=send_to_cytoscape,
        args=(ip, return_dict, GD.pdata, GD.pfile),
    )
    log.info("Sending Network")
    p.start()
    p.join(timeout=300)
    p.terminate()
    if p.exitcode is None:
        return_dict["status"] = {
            "message": f"Process timed out. Please do not remove networks or views fom Cytoscape while the process is running.",
            "status": "error",
        }
    blueprint.emit("status", return_dict["status"])


@blueprint.on("sel")
def string_ex_sel(message):
    id = message["id"]
    if id == "project":
        my_util.set_project(blueprint, message["opt"])


@blueprint.on("algorithms")
def string_ex_algorithms(message):
    """Route to receive the algorithms from the VRNetzer backend. Will be used to update the algorithms in the CyEx extension."""
    message["data"] = LayoutAlgorithms.all_algos
    blueprint.emit("algorithms", message)




import json
import multiprocessing as mp
import uuid

import flask
import GlobalData as GD
from io_blueprint import IOBlueprint
from project import Project

import util

from . import routes
from . import settings as st
from . import util as my_util
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

submitted_jobs = {"test": {"data": "test"}}
my_util.prepare_uploader()
my_util.move_on_boot()


@blueprint.before_app_first_request
def cy_ex_setup():
    pass
    # Execute before first request


@blueprint.route("/")
def cy_ex_index():
    """Redirect to CyEx home page."""
    return flask.redirect("/home")


@blueprint.route("/home")
def cy_ex_home():
    """CyEx Home page."""
    return flask.render_template("cyEx_home.html")


@blueprint.route("/status", methods=["GET"])
def cy_ex_status():
    """Route to check if the CyEx extension is installed and running."""
    return "CyEx is installed and running..."


@blueprint.route("/upload", methods=["GET", "POST"])
def cy_ex_upload() -> str:
    """This route is used to upload a VRNetz using the STRING Uploader. A POST request is send to it, when a user clicks the "upload" button.

    Returns:
        str: A status giving information whether the upload was successful or not.
    """
    job = flask.request.args.get("job", False)
    if job:
        if job not in submitted_jobs:
            job = False
    return flask.render_template(
        "cyEx_upload.html", layAlgos=LayoutAlgorithms.all_algos, job=job
    )


@blueprint.route("/cy_submit", methods=["POST"])
def cy_ex_cy_submit():
    # Get JSON data from the request body
    json_data = flask.request.get_json()
    log.debug(json_data)

    # Generate a unique Job ID
    job_id = str(uuid.uuid4())

    # Store the JSON data and settings related to this Job ID
    submitted_jobs[job_id] = json_data

    # Respond with the URL associated with this Job ID
    url = flask.url_for("CyEx.cy_ex_upload", job=job_id, _external=True)
    return url


@blueprint.route("/vrnetz_upload", methods=["GET", "POST"])
def cy_ex_vrnetz_upload() -> str:
    """This route is used to upload a VRNetz using the STRING Uploader. A POST request is send to it, when a user clicks the "upload" button.

    Returns:
        str: A status giving information whether the upload was successful or not.
    """
    form = flask.request.form.to_dict()
    job = form.get("job")
    log.debug(form)
    network = submitted_jobs.get(job)
    return routes.upload_vrnetz(network)


@blueprint.on(
    "sendNetwork",
)
def string_send_to_cytoscape(message):
    """Is triggered by a call of a client. Will take the current selected nodes and links to send them to a running instance of Cytoscape. This will always send the network the Cytoscape session of the requesting user, if not otherwise specified. If to host is selected, the network will be send to the Cytoscape session of the Server host."""
    log.debug("Requested to send a network to Cytoscape. Will handle this request.")
    return_dict = mp.Manager().dict()
    ip = flask.request.remote_addr
    p = mp.Process(
        target=send_to_cytoscape,
        args=(ip, return_dict, GD.pdata, GD.pfile),
    )
    p.start()
    p.join(timeout=300)
    p.terminate()
    if p.exitcode is None:
        return_dict["status"] = {
            "message": f"Process timed out. Please do not remove networks or views fom Cytoscape while the process is running.",
            "status": "error",
        }
    blueprint.emit("status", return_dict["status"])

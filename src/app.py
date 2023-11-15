import json
import multiprocessing as mp

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
    return flask.render_template(
        "cyEx_upload.html", layAlgos=LayoutAlgorithms.all_algos
    )


@blueprint.route("/vrnetz_upload", methods=["GET", "POST"])
def cy_ex_vrnetz_upload() -> str:
    """This route is used to upload a VRNetz using the STRING Uploader. A POST request is send to it, when a user clicks the "upload" button.

    Returns:
        str: A status giving information whether the upload was successful or not.
    """
    return routes.upload_vrnetz()

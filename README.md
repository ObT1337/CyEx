# TEMP README COPIED FROM STRINGEX

# CyEx

This extension serves as a bridge between the DataDiVR ecosystem and the widely used network visualization software Cytoscape. In combination with the Cytoscape App [DataDiVRApp](https://github.com/menchelab/DataDiVRApp) this extension allows to upload and receive networks exported from Cytoscape using the DataDiVRApp.
Furthermore, it also enables to sent sub-set of a large-scale DataDiVR Project from a running session to a running Cytoscape session.

## Installation

1. Add the `StringEx` directory to your DataDiVR backend directory. The directory should be located at `"extensions/StringEx"`.
2. Restart your backend server.
3. During the start-up of the backend server, all the necessary Python packages needed for the extension should be automatically installed.

## Usage

### Upload network from Cytoscape

1. Export a network with the VRNetzerApp from Cytoscape. For further instructions see [here](https://github.com/menchelab/STRING-VRNetzer).
2. Start the VRNetzer backend using the script applicable to your operating system.
3. Navigate in your Browser to http://127.0.0.1:5000/upload (Windows/Linux) / http://127.0.0.1:3000/upload (mac)
4. If the StringEx is correctly installed, you should now see two new tabs. The first is the VRNetz designated uploader

   <img src="./static/img/VRNetz_upload.png" alt=" Picture that visualizes the location of the StringEx uploader tab">

5. On this tab, (a) define a project name, (b) select the VRNetz file of your exported network, and (c) select the desired layout algorithm.
6. You can (d) also define the respective variables.
7. You can (e) provide a name for the generated node layout.
8. Click on the "Upload" button to upload the network to the VRNetzer platform.
9. If the upload was successful, you'll be prompted with a success message and a link to preview the project in the designated WebGL previewer.

---

### Map an exported network on a preprocessed PPI

Do the first three steps as mentioned [above](#upload-string-network).

4. The second tab is the STRING mapper.

   <img src="./static/img/Map.png" alt= "Picture that visualizes the location of the StringEx map tab.">

5. On this tab, (a) define a project name, (b) select the VRNetz file of your exported String network, and (c) select the organism from which your VRNetz originates.
6. Click on the "Map" button to map the network with the preprocessed PPI.
7. If the upload was successful, you'll be prompted with a success message and a link to preview the project in the designated WebGL previewer.

# Reconstruct STRING interactomes (WIP)

To reconstruct the provided STRING interactomes from the source files the `construct_interactomes.py' script can be used:

Tested with Python 3.9+.

1. Install the package e.g. in a virtual environment:

- create a virtual environment<br>
  `python3 -m venv name_of_env`
- activate it<br>
  `source name_of_env/bin/activate`
- install requirements packages<br>
  `python3 -m pip install -r requirements.txt`

2. Run the construct interactomes script in reproduce mode:<br>
   `python3 construct_interactomes.py reproduce`

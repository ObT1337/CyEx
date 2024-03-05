const uid = makeid(10);
let cyExSocket = io.connect("http://" + location.host + "/CyEx");
cyExSocket.on("status", function(data) {
  console.log(data["message"]);
  // TODO: Enable the send button and remove the loading gif
});
cyExSocket.on("project", function(data) {
  if (data["api"] == "check_project_exists") {
    if (data["exists"]) {
      var paragraph = document.createElement('p');

      // Set the text content
      paragraph.textContent = "Project already exists, if you want to overwrite it, check the overwrite checkbox. If the box is not checked every new layout will be added to the existing project. Layouts which already exist will be overwritten.";

      // Set the color style
      paragraph.style.color = 'yellow';
      paragraph.style.fontSize = "15px";

      document.getElementById("CyEx_project_submit_warnings").appendChild(paragraph)
    } else {
      $("#CyEx_project_submit_warnings").html("")
    }
  }
  // TODO: Enable the send button and remove the loading gif
});

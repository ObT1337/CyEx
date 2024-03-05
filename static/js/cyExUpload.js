$(document).ready(function() {
  //LOAD NAMESPACE MENU TAB 1
  //LOAD NAMESPACE MENU TAB 1
  if (job) {
    document.getElementById("cy_ex_vrnetzfile_div").style.display = "none";
  }
  $("#cyEx_upload_button").button();

  $("#cyEx_upload_form").on("change input", function() {
    console.log("changed!");
    var formData = new FormData(document.getElementById("cyEx_upload_form"));

    for (var pair of formData.entries()) {
      console.log(pair[0] + ", " + pair[1]);
    }
  });

  $("#cyEx_upload_form").submit(function(event) {
    event.preventDefault();
    var formData = new FormData(this);
    let it = formData.keys();

    let result = it.next();
    while (!result.done) {
      console.log(result); // 1 3 5 7 9
      console.log(formData.get(result.value));
      result = it.next();
    }
    if (job) formData.append("job", job);
    var layoutSelectors = this.querySelectorAll("cy-ex-layout-selector");

    layoutSelectors.forEach(function(selector, index) {
      var layoutData = selector.getLayoutData();

      // Append layout data to FormData
      Object.keys(layoutData).forEach(function(key) {
        formData.append("layout_" + (index + 1) + "_" + key, layoutData[key]);
      });
    });
    formData.append("overwrite", document.getElementById("CyEx_project_overwrite").checked)
    console.log(formData);
    var url = "http://" + location.host + "/CyEx/vrnetz_upload";
    console.log(url);
    console.log(formData);
    $.ajax({
      type: "POST",
      url: url,
      data: formData, // serializes the form's elements.
      cache: false,
      contentType: false,
      processData: false,
      success: function(data) {
        console.log(data);
        $("#cyEx_upload_message").html(data);
      },
      error: function(err) {
        console.log("Uploaded failed!");
        $("#cyEx_upload_message").html("Upload failed");
      },
    });
  });

  function add_layout_selection() {
    let box = document.getElementById("cyEx_layout_selection_box")
    layout_selections += 1
    let newDD = document.createElement("cy-ex-layout-selector")
    newDD.setAttribute("id", id = "cyEx_lay_sel_" + layout_selections)
    newDD.setAttribute("name", layout_selections + ". Layout")
    console.log(newDD)
    box.appendChild(newDD)
  }
  function updateAllLayoutSelectors() {
    let selectors = document.getElementById("cyEx_layout_selection_box").children
    console.log(selectors)
    for (var i = 0; i < selectors.length; i++) {
      selectors[i].setAttribute("name", i + 1 + ". Layout")
      selectors[i].updateName()
    }
  }
  let projectNameElement = document.getElementById("CyEx_new_project_vrnetz")
  projectNameElement.addEventListener('input', (event) => {
    // Get the updated value of the input
    const updatedValue = event.target.value;
    const message = {
      "projectName": updatedValue,
      "uid": uid
    }
    // Emit a Socket.IO event with the updated value
    cyExSocket.emit('checkProjExistance', message);
  });
});

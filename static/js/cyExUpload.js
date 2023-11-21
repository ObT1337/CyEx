$(document).ready(function () {
  //LOAD NAMESPACE MENU TAB 1
  //LOAD NAMESPACE MENU TAB 1
  if (job) {
    document.getElementById("cy_ex_vrnetzfile_div").style.display = "none";
  }
  $("#cyEx_upload_button").button();

  $("#cyEx_upload_form").on("change input", function () {
    console.log("changed!");
    var formData = new FormData(document.getElementById("cyEx_upload_form"));

    for (var pair of formData.entries()) {
      console.log(pair[0] + ", " + pair[1]);
    }
  });

  $("#cyEx_upload_form").submit(function (event) {
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
    formData["layouts"] = [];
    var layoutSelectors = this.querySelectorAll("cy-ex-layout-selector");

    layoutSelectors.forEach(function (selector, index) {
      var layoutData = selector.getLayoutData();

      // Append layout data to FormData
      Object.keys(layoutData).forEach(function (key) {
        formData.append("layout_" + (index + 1) + "_" + key, layoutData[key]);
      });
    });
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
      success: function (data) {
        console.log(data);
        $("#cyEx_upload_message").html(data);
      },
      error: function (err) {
        console.log("Uploaded failed!");
        $("#cyEx_upload_message").html("Upload failed");
      },
    });
  });
});

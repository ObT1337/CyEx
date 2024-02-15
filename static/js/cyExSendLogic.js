$(document).ready(function () {
  cyExSocket.on("status", function (data) {
    console.log(data["message"]);
    // TODO: Enable the send button and remove the loading gif
  });
});

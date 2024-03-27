/** Data validators */

const isValidNumber = (value) => (value !== null && value !== undefined && value !== "" && !isNaN(Number(value)));

/** Data formaters */

const getNumberOrNull = (value) => isValidNumber(value) ? parseInt(value, 10) : null;

const capitalize = (str) => str.replace(/\b\w/g, char => char.toUpperCase());

/** Object management */

const deepCopy = (obj) => {
  if (typeof obj !== 'object' || obj === null) {
    return obj;
  }

  const copy = Array.isArray(obj) ? [] : {};

  for (const key in obj) {
    copy[key] = deepCopy(obj[key]);
  }

  return copy;
}

/** Template modifiers */

const disableButton = (identifier) => $(identifier).prop("disabled", true);

const enableButton = (identifier) => $(identifier).prop("disabled", false);

/** Reusable modal */

const createModal = (title, $body, containerClass) => {
  destroyModal();

  const $wrapper = $("<div>").attr({"id": "customModal"}).addClass("modal visible opacity-100 pointer-events-auto");
  const $container = $("<div>").addClass(`modal-box ${containerClass ? containerClass : ""}`);
  const $header = $("<div>").addClass("w-full mb-6 flex flex-row-reverse");

  const $title = $("<h2>").addClass("card-title flex-1 capitalize").text(title);
  const $closeBtn = $("<label>").addClass("btn btn-sm btn-circle").text("✕").on("click", destroyModal);
  
  $header.append($closeBtn, $title);
  $container.append($header, $body);
  $wrapper.append($container);
  $("main").append($wrapper);
  $wrapper.on("click", (event) => {
    if ($(event.target).hasClass("modal")) {
      destroyModal();
    }
  });
};

const destroyModal = () => {
  $("#customModal").remove();
}
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

/** HTML Fragments */

const loadingAnimation = (`
  <div class="justify-center flex" role="status">
    <svg aria-hidden="true" class="mr-2 w-8 h-8  animate-spin fill-blue-600 text-gray-200" viewBox="0 0 100 101" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>
      <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentFill"/>
    </svg>
    <span class="sr-only">Loading...</span>
  </div>
`);

const loadingAnimationBlock = (`
  <div class="col-span-9 mx-auto mt-10">
  ${loadingAnimation}
  </div>
`);
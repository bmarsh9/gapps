function disableButton(identifier) {
  $(identifier).prop("disabled", true);
}

function enableButton(identifier) {
  $(identifier).prop("disabled", false);
}

function isValidNumber(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    !isNaN(Number(value))
  );
}

function getNumberOrNull(value) {
  return isValidNumber(value) ? parseInt(value, 10) : null;
}

function deepCopy(obj) {
  if (typeof obj !== 'object' || obj === null) {
      return obj;
  }

  const copy = Array.isArray(obj) ? [] : {};

  for (const key in obj) {
      copy[key] = deepCopy(obj[key]);
  }

  return copy;
}
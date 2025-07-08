// Network requests
function request(method, url, onSuccess, onError, jsonData = null) {

  const fetchOptions = {
    method: method,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
    }
  };

  if (jsonData !== null) {
    fetchOptions.body = JSON.stringify(jsonData);
  }

fetch(url, fetchOptions)
  .then(response => {
    // Handle success
    if (response.ok) {
      return response.json();
    } else {
      // If response is not ok, extract error message from response
      return response.json().then(error => {
        throw new Error("Error occurred: " + error.message);
      });
    }
  })
  .then(data => {
    // Call onSuccess callback with data
    onSuccess(data);
  })
  .catch(error => {
    // Call onError callback with error
    if (typeof onError === 'function') {
      if (error.toString().includes("not valid JSON")) {
        toast("Unexpected error occurred.", "error")
        console.log(error)
      } else {
        onError(error);
      }
    } else {
      // Handle the case where onError is not a function
      toast('Error occurred: ' + error.message, "error");
    }
  });
}

function requestWithForm(method, url, onSuccess, onError, formData) {

  const fetchOptions = {
    method: method,
    body: formData,
    cache: "no-cache"
  };

fetch(url, fetchOptions)
  .then(response => {
    // Handle success
    if (response.ok) {
      return response.json();
    } else {
      // If response is not ok, extract error message from response
      return response.json().then(error => {
        throw new Error("Error occurred: " + error.message);
      });
    }
  })
  .then(data => {
    // Call onSuccess callback with data
    onSuccess(data);
  })
  .catch(error => {
    // Call onError callback with error
    if (typeof onError === 'function') {
      onError(error);
    } else {
      // Handle the case where onError is not a function
      toast('Error occurred: ' + error.message, "error");
    }
  });
}


// Toast notification
function toast(message, level="info", duration=5000, bottom=false) {
    var bg = "#367ff5"
    if (level === "success") {
      var bg = "#4ade80"
    } else if (level === "warning") {
      var bg = "#ffa929"
    } else if (level === "error") {
      var bg = "#f5584c"
    }
    config = {
      text: message,
      escapeMarkup: false,
      duration: duration,
      close: true,
      gravity: "top",
      position: "right",
      stopOnFocus: true,
      style: {
        background: bg,
        borderRadius: "0.5rem"
      }
    }
    if (bottom) {
        config["gravity"] = "bottom"
    }
    Toastify(config).showToast();
}

// Helper function for showing fields in modal
function getModalFields(tableHeaders={}) {
    var headers = [];
    var defaultDict = {"modal": {"disable": false, "hide": false, "span": "3", "type": "text", "data_type": "text"}}
    tableHeaders.forEach(item => {
        if (item.modal === undefined) {
            item.modal = Object.assign({}, defaultDict.modal);
        } else {
            for (let key in defaultDict.modal) {
                if (defaultDict.modal.hasOwnProperty(key)) {
                    if (!item.modal.hasOwnProperty(key)) {
                        item.modal[key] = defaultDict.modal[key];
                    }
                }
            }
        }
        headers.push(item)
    });
    return headers
}

// TinyMCE config
function getEditorConfig(selector, readOnly=false) {
    let defaultConfig = {
        selector: selector,
        statusbar: false,
        promotion: false,
        content_css: "/static/css/tiny_custom.css"
    }
    if (readOnly) {
        defaultConfig["readonly"] = true
        defaultConfig["menubar"] = false
        defaultConfig["toolbar"] = false
    } else {
        defaultConfig["plugins"] = "preview fullscreen searchreplace table codesample lists advlist variable link"
        defaultConfig["toolbar1"] = "bold italic strikethrough forecolor backcolor | fontfamily fontsize blocks | link | alignleft aligncenter alignright alignjustify  | numlist bullist outdent indent  | removeformat undo redo"
    }
    return defaultConfig
}

function getApexCircleConfig(data, label) {
    var options = {
        series: [100-data, data],
        legend: {
          show: false
        },
        tooltip: {
          fillSeriesColor: true,
        },
        colors:['#242933', '#242933'],
        dataLabels: {
          enabled: false
        },
        chart: {
          type: 'donut',
          height: 240,
          background: 'transparent'

        },
        plotOptions: {
            pie: {
              donut: {
                labels: {
                  show: true,
                value:{
                  offsetY: -8,
                  color:'#e5e7eb'
                },
                  total: {
                    show: true,
                    label: '',
                    formatter: () => label || `${data}`
                  }
                }
              }
            }
        },
        labels: ['Incomplete', 'Complete'],
        fill:{
            colors:['#242933', '#4ade80']
        },
        stroke: {
            colors:["#242933"],
            show: true,
            width:1
        },
        responsive: [{
          breakpoint: 100,
          options: {
            chart: {
              width: 100
            }
          }
        }]
    };
    return options
}

function select(config) {
  let settings = {showSearch: true}
  let events = {}

  if (config.get) {
    console.log("Grabbing the value for slimSelect")
    let data = document.querySelector(config.id).slim.getData()
    const selectedValues = [];
    data.forEach(obj => {
        if (obj.selected) {
            selectedValues.push(obj.value);
        }
    });
    return selectedValues
  }

  if (config.destroy) {
    console.log("Trying to destroy slimSelect")
    let id = config.id.replace('#', '');
    const selectElement = document.getElementById(id);
    if (selectElement && selectElement.hasAttribute("data-id")) {
       let dataAttribute = selectElement.getAttribute("data-id")
       document.querySelector(config.id).slim.destroy()
    }
  }

  if (config.disabled) {
    settings.disabled = true
  }

  if (config.placeholder) {
    settings.placeholderText = config.placeholder
  }

  if (config.addable) {
    events.addable = function (value) {
      return {
        text: value,
        value: value.toLowerCase()
      };
    };
  }

  let slim = new SlimSelect({
    select: config.id,
    settings: settings,
    events: events
  });

  if (config.options) {
    // Expected format
    //const options = [
    //  { value: 'value1', text: 'Value 1'},
    //]
    slim.setData(config.options)
    if (config.selected) {
        // Expected format
        // ["value1"]
        slim.setSelected(config.selected)
    }
  }
}
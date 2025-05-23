/*
Usage:
  # Place in the column definition for the table. You can pass additional parameters to the renderer
  {"field": "progress", "headerName": "Progress", "cellRenderer": NumberToProgressBar, "cellRendererParams": {}}

  # If you pass params to cellRendererParams, you can access via params.<key>
*/

class coloredNumber {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {

    this.eGui = document.createElement('div');
    this.eGui.classList.add('flex', 'items-center', 'font-semibold', 'text-sm', 'opacity-75');

    if (params.value < 25) {
        this.eGui.classList.add('text-error');
    } else if (params.value < 75) {
        this.eGui.classList.add('text-warning');
    } else {
        this.eGui.classList.add('text-success');
    }
    this.eGui.textContent = params.value;
  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class numberAndProgressBar {
  /*
  Given a field with a number, convert the field to a progress bar with a tooltip showing the value
  */
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.classList.add('flex', 'items-center');
    //this.eGui.classList.add('tooltip');
    //this.eGui.setAttribute('data-tip', params.value);
    this.eGui.innerHTML = `
      <p class='flex-none text-xs font-semibold mr-2'>${params.value}</p>
      <progress class="progress progress-secondary w-32" value="${params.value}" max="100"></progress>
    `;
  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}


class idToButton {
  /*
  Given a field with a id, create a button that directs to the next link
  {"text": "Click me", "class": "btn-ghost", "link": "/link/{value}"}
  */
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.classList.add('flex', 'items-center');
    let link = params.link.replace("{value}", params.value);
    if (!params.text) {
        params.text = "<i class='ti ti-external-link text-lg'></i>"
    }
    if (!params.class) {
        params.class = "btn-sm btn-ghost"
    }
    this.eGui.innerHTML = `
      <a href='${link}' class='btn ${params.class}'>${params.text ?? "View"}</a>
    `;
  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class assessmentStatusToBadge {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.classList.add("badge", "font-semibold", "p-2", "text-xs", "uppercase", "text-neutral", "rounded-md", "opacity-90");

    const classMap = {
        "new": {"class": "badge-primary,text-neutral-content", "text": "New"},
        "pending_response": {"class": "badge-warning", "text": "Waiting on Vendor"},
        "pending_review": {"class": "badge-error", "text": "Waiting on InfoSec"},
        "complete": {"class": "badge-success", "text": "Complete"}
    };

    const className = classMap[params.value];
    if (className["class"]) {
        className["class"].split(",").forEach(
            item => this.eGui.classList.add(item)
        )
    } else {
        this.eGui.classList.add("badge-neutral")
        this.eGui.classList.add("text-neutral-content")
    }
    this.eGui.textContent = className["text"]
  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class toDots {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    if (!params.color) {
        params.color = "error"
    }

    function createBadge(fill) {
        var badge = document.createElement('div');
        badge.classList.add("badge", "badge-xs", "my-auto");
        if (fill) {
            badge.classList.add("badge-"+params.color);
        } else {
            badge.classList.add("bg-neutral", "border", "border-neutral");
        }
        return badge;
    }

    this.eGui = document.createElement('div');
    this.eGui.classList.add("flex", "flex-row", "gap-x-1");

    if (!params.fillCount) {
        params.fillCount = 3
    }
    let tempBadge;
    for (var i = 0; i < 5; i++) {
        if (i < params.fillCount) {
            tempBadge = createBadge(true);
        } else {
            tempBadge = createBadge(false);
        }
        this.eGui.appendChild(tempBadge);
    }

  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class reviewStatusToBadge {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.textContent = params.value
    this.eGui.classList.add("badge", "font-semibold", "p-2", "text-xs", "uppercase", "rounded-md", "opacity-90");

    const classMap = {
        "not started": "badge-neutral",
        "ready for auditor": "badge-info",
        "infosec action": "badge-warning",
        "action required": "badge-error",
        "complete": "badge-success"
    };
    const className = classMap[params.value.toLowerCase()];
    this.eGui.classList.add(className);

  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class booleanBadge {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.textContent = params.value
    this.eGui.classList.add("opacity-90");

    if (params.value === true) {
        //this.eGui.classList.add("badge-success")
        this.eGui.innerHTML = '<i class="ti ti-progress-check text-success text-lg"></i>'

    } else {
        this.eGui.innerHTML = '<i class="ti ti-progress-x text-error text-lg"></i>'
        //this.eGui.classList.add("badge-error")
    }

  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class hasValue {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.textContent = params.value
    this.eGui.classList.add("opacity-90");

    if (params.value) {
        //this.eGui.classList.add("badge-success")
        this.eGui.innerHTML = '<i class="ti ti-progress-check text-success text-lg"></i>'

    } else {
        this.eGui.innerHTML = '<i class="ti ti-progress-x text-error text-lg"></i>'
        //this.eGui.classList.add("badge-error")
    }

  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class numberToVertProgressBar {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.classList.add("flex", "flex-row", "gap-x-1");

    var values = [5, 0, 0, 0];
    for (var i = 0; i < Math.min(Math.ceil(params.value / 25), 4); i++) {
        values[i] = Math.min(params.value - (25 * i), 25);
    }
    // Create progress bars based on the given number
    for (var i = 0; i < 4; i++) {
        var progressBar = this.createProgressBar(values[i], params);

        // Append the progress bar to the parent element
        this.eGui.appendChild(progressBar);

    }
  }

  createProgressBar(value, params) {
    var mainContainer = document.createElement("div");
    if (!params.bg) {
        params.bg = "bg-neutral"
    }

    mainContainer.classList.add("flex", "flex-col", "flex-nowrap", "justify-end", "w-1", "h-4", params.bg, "rounded-full", "overflow-hidden");
    mainContainer.setAttribute("role", "progressbar");
    mainContainer.setAttribute("aria-valuenow", value*4);
    mainContainer.setAttribute("aria-valuemin", "0");
    mainContainer.setAttribute("aria-valuemax", "100");

    // Calculate the height of the progress based on the value
    var height = value*4 + "%";

    // Create the inner div for the progress
    var progressDiv = document.createElement("div");
    progressDiv.classList.add("rounded-full", "overflow-hidden", "bg-success");
    if (value*4 === 100) {
        progressDiv.classList.add("bg-success")
    } else {
        progressDiv.classList.add(params.bg)
    }
    progressDiv.style.height = height;

    // Append the progress div to the main container
    mainContainer.appendChild(progressDiv);

    return mainContainer;
  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class controlStatusToBadge {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.textContent = params.value
    this.eGui.classList.add("badge", "font-semibold", "p-2", "uppercase", "rounded-md", "opacity-90");
    this.eGui.style.fontSize = "x-small";

    const classMap = {
        "not started": "badge-neutral",
        "in progress": "badge-warning",
        "not applicable": "badge-error",
        "complete": "badge-success"
    };
    const className = classMap[params.value.toLowerCase()];
    this.eGui.classList.add(className);

  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class riskStatusToBadge {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.textContent = params.value
    this.eGui.classList.add("badge", "font-semibold", "p-2", "uppercase", "rounded-md", "opacity-90");
    this.eGui.style.fontSize = "x-small";

    const classMap = {
        "new": "badge",
        "in_progress": "badge-warning",
        "accepted": "badge-warning",
        "mitigated": "badge-success",
        "false_positive": "badge-success"
    };
    const className = classMap[params.value.toLowerCase()];
    this.eGui.classList.add(className);

  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class riskToVertBar {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.classList.add("flex", "flex-row", "gap-x-1");

    const classMap = {
        "unknown": {"bars": 1},
        "low": {"bars": 1},
        "moderate": {"bars": 2},
        "high": {"bars": 3},
        "critical": {"bars": 4}
    };
    const className = classMap[params.value.toLowerCase()];

    // Create progress bars based on the given number
    for (var i = 0; i < 4; i++) {
        if (i+1 > className.bars) {
            var progressBar = this.createProgressBar("neutral", params);
        } else {
            var progressBar = this.createProgressBar("error", params);
        }
        this.eGui.appendChild(progressBar);
    }

  }

  createProgressBar(color, params) {
    var mainContainer = document.createElement("div");
    if (!params.bg) {
        params.bg = "bg-base-200"
    }

    mainContainer.classList.add("flex", "flex-col", "flex-nowrap", "justify-end", "w-1", "h-4", params.bg, "rounded-full", "overflow-hidden");
    mainContainer.setAttribute("role", "progressbar");
    mainContainer.setAttribute("aria-valuenow", 100);
    mainContainer.setAttribute("aria-valuemin", "0");
    mainContainer.setAttribute("aria-valuemax", "100");

    // Create the inner div for the progress
    var progressDiv = document.createElement("div");
    progressDiv.classList.add("rounded-full", "overflow-hidden", "bg-"+color);
    progressDiv.style.height = "100%";

    // Append the progress div to the main container
    mainContainer.appendChild(progressDiv);

    return mainContainer;
  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class riskPriorityToBadge {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.textContent = params.value
    this.eGui.classList.add("badge", "font-semibold", "p-2", "uppercase", "rounded-md", "opacity-90");
    this.eGui.style.fontSize = "x-small";

    const classMap = {
        "unknown": "badge-neutral",
        "low": "badge-success",
        "moderate": "badge-warning",
        "high": "badge-error"
    };
    const className = classMap[params.value.toLowerCase()];
    this.eGui.classList.add(className);

  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class priorityToVertBar {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.classList.add("flex", "flex-row", "gap-x-1");

    const classMap = {
        "unknown": {"bars": 1},
        "low": {"bars": 2},
        "moderate": {"bars": 3},
        "high": {"bars": 4}
    };
    const className = classMap[params.value.toLowerCase()];

    // Create progress bars based on the given number
    for (var i = 0; i < 4; i++) {
        if (i+1 > className.bars) {
            var progressBar = this.createProgressBar("neutral", params);
        } else {
            var progressBar = this.createProgressBar("error", params);
        }
        this.eGui.appendChild(progressBar);
    }

  }

  createProgressBar(color, params) {
    var mainContainer = document.createElement("div");
    if (!params.bg) {
        params.bg = "bg-base-200"
    }

    mainContainer.classList.add("flex", "flex-col", "flex-nowrap", "justify-end", "w-1", "h-4", params.bg, "rounded-full", "overflow-hidden");
    mainContainer.setAttribute("role", "progressbar");
    mainContainer.setAttribute("aria-valuenow", 100);
    mainContainer.setAttribute("aria-valuemin", "0");
    mainContainer.setAttribute("aria-valuemax", "100");

    // Create the inner div for the progress
    var progressDiv = document.createElement("div");
    progressDiv.classList.add("rounded-full", "overflow-hidden", "bg-"+color);
    progressDiv.style.height = "100%";

    // Append the progress div to the main container
    mainContainer.appendChild(progressDiv);

    return mainContainer;
  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class listToBadge {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.classList.add("flex", "flex-row", "gap-x-1");

    for (let word of params.value) {
        const newDiv = document.createElement('div');
        newDiv.classList.add('badge', 'badge-ghost', "text-xs", "font-semibold");
        newDiv.textContent = word;
        this.eGui.appendChild(newDiv);
    }

  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

class simpleDate {
  eGui;

  // init method gets the details of the cell to be renderer
  init(params) {
    this.eGui = document.createElement('div');
    this.eGui.classList.add("my-auto");

    const date = new Date(params.value);

    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    const formattedDate = new Intl.DateTimeFormat('en-US', options).format(date);

    this.eGui.textContent = formattedDate;

  }

  getGui() {
    return this.eGui;
  }

  refresh(params) {
    return false;
  }
}

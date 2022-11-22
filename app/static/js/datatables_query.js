class Table {
  constructor(config) {
    this.selector = config.selector;
    this.id = config.selector.substring(1);
    this.dataUrl = config.dataUrl,
    this.ruleUrl = config.ruleUrl
    this.nextLinkField = config.nextLinkField
    this.spawnModalOnClick = config.spawnModalOnClick ?? false;
    this.enableFilter = config.enableFilter ?? false;
    this.refreshBtn = config.refreshBtn ?? false;
    this.toggleCols = config.toggleCols ?? false;
    this.pageLength = config.pageLength ?? 10;
    this.truncate = config.truncate ?? false;
  }
  exist() {
    if ($(this.selector).is(':empty')) {
        return false;
    }
    return true;
  }
  create(title="Default") {
    if (!this.exist()) {
      this.setConfigInStorage()

      var headerDiv = $("<div>").addClass("card-title mb-4 justify-between")
      var tableDiv = $("<div>").html(`<table class="table table-vcenter table-bordered text-sm font-medium text-gray-500" id="table-${this.id}" style="width:100%"><thead><tr></tr></thead></table>`)
      var buttonDiv = $("<div>")
      var headerTitle = $("<h2>").addClass("card-title").html(`${title}`)

      if (this.enableFilter) {
        this.createQueryModal()
      }
      if (this.refreshBtn) {
        var colButton = $("<button>").attr("data-selector",`${this.id}`).addClass("btn btn-square btn-ghost btn-xs mr-2 refresh-button").html('<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>')
        buttonDiv.append(colButton)
      };
      if (this.toggleCols) {
        var colButton = $("<button>").attr("data-selector",`${this.id}`).addClass("btn btn-square btn-ghost btn-xs mr-2 column-button").html('<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M9 4.5v15m6-15v15m-10.875 0h15.75c.621 0 1.125-.504 1.125-1.125V5.625c0-.621-.504-1.125-1.125-1.125H4.125C3.504 4.5 3 5.004 3 5.625v12.75c0 .621.504 1.125 1.125 1.125z" /></svg>')
        buttonDiv.append(colButton)
        this.createColumnModal()
      }
      if (this.spawnModalOnClick) {
        this.createDataModal()
      }
      if (this.enableFilter) {
        var filterButton = $("<button>").attr({"data-selector": `${this.id}`, "id": `${this.id}-filter`}).addClass("btn btn-square btn-ghost btn-xs filter-button").html('<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" /></svg>')
        buttonDiv.append(filterButton)
        this.createQueryBuilder()
      }
      headerDiv.append(headerTitle)
      headerDiv.append(buttonDiv)
      $(this.selector).append(headerDiv)
      $(this.selector).append(tableDiv)
      this.reloadData()
    }
  }
  setConfigInStorage() {
    var settings = {
      id: this.id,
      selector: this.selector,
      dataUrl: this.dataUrl,
      ruleUrl: this.ruleUrl,
      nextLinkField: this.nextLinkField,
      spawnModalOnClick: this.spawnModalOnClick,
      enableFilter: this.enableFilter,
      toggleCols: this.toggleCols,
      pageLength: this.pageLength,
      truncate: this.truncate
    };
    localStorage.setItem(this.id, JSON.stringify(settings));
  }
  getConfigInStorage() {
    return JSON.parse(localStorage.getItem(this.id));
  }
  createQueryBuilder() {
    var builderId = `${this.selector}-builder`;
    var filterButtonId = `${this.selector}-filter`
    $.ajax({
      type: "GET",
      url: this.ruleUrl,
      contentType: "application/json; charset=utf-8",
      success: function(data){
        $(builderId).queryBuilder({
          filters: data
        })
        if ($(builderId).queryBuilder('getRules')) {
          $(filterButtonId).addClass("text-accent")
        }
        return(data)
      },
      error: function(errMsg) {
        createToast("error","failed creating assets table")
        return(errMsg);
      }
    })
  }
  createQueryModal() {
    $(document.body).append(`<input type="checkbox" id="${this.id}-filter-modal" class="modal-toggle" /><div class="modal"><div class="modal-box relative w-11/12 max-w-5xl"><label for="${this.id}-filter-modal" class="btn btn-sm btn-circle absolute right-2 top-2">✕</label><h3 class="text-lg font-bold">Apply Filter</h3><div class="py-4"><div id="${this.id}-builder"></div></div><div class="modal-action"><button id="${this.id}-reset" data-selector="${this.id}" class="btn btn-sm float-right mr-2 reset-filter btn-error text-white">Reset</button><button data-selector="${this.id}" class="btn btn-sm float-right mr-2 send-filter">Filter</button></div></div></div>`)
  }
  createColumnModal() {
    $(document.body).append(`<input type="checkbox" id="${this.id}-column-modal" class="modal-toggle" /><div class="modal"><div class="modal-box relative"><label for="${this.id}-column-modal" class="btn btn-sm btn-circle absolute right-2 top-2">✕</label><h3 class="text-lg font-bold">Display Columns</h3><div class="py-4"><select name="${this.id}-select" id="${this.id}-select" data-selector="${this.id}" class="dropdown-content menu p-2 shadow bg-base-100 rounded-box"><option></option></select></div><div class="modal-action"></div></div></div>`)
  }
  createDataModal() {
    $(document.body).append(`<input type="checkbox" id="${this.id}-data-modal" class="modal-toggle" /><div class="modal"><div class="modal-box w-11/12 max-w-5xl relative"><label for="${this.id}-data-modal" class="btn btn-sm btn-circle absolute right-2 top-2">✕</label><div class="card-title mb-4 justify-between"><h3 class="text-lg font-bold">Record Data</h3><div><div id="${this.id}-data-modal-link" class="mr-10"></div></div></div><div id="${this.id}-data-modal-body" class="card-body bg-gray-100 rounded-md mt-4"></div><div class="modal-action"></div></div></div>`)
  }
  reloadData(filterData={}) {
    var config = this.getConfigInStorage();
    var ajaxParams = {
      type: "POST",
      url: config.dataUrl,
      data: JSON.stringify(filterData),
      contentType: "application/json; charset=utf-8",
      dataType: "json",
      error: function(errMsg) {
        return(errMsg);
      }
    }
    var selectId = `${config.selector}-select`;
    var data,
                tableName=`#table-${config.id}`,
                columns,
                str,
                jqxhr = $.ajax(ajaxParams).done(function () {
                  data = JSON.parse(jqxhr.responseText);
                  console.log(`got ${data.data.length} records`)
                  createToast("success",`Queried ${data.data.length} records`)

                  if (config.nextLinkField) {
                    $.each(data.data, function(index, record) {
                      record[config.nextLinkField] = `<a href="${record[config.nextLinkField]}" class="btn btn-xs">View</a>`

                    })
                  }

                  if (config.toggleCols) {
                    $(selectId).empty();
                    $(selectId).trigger("change");
                  };
                  if (data.columns.length > 0) {
                    // Iterate each column and print table headers for Datatables
                    var multiCheckArray = [];
                    $.each(data.columns, function (k, colObj) {
                      if (config.toggleCols) {
                        if (colObj.visible) {
                          multiCheckArray.push({"id":colObj.name,"name":colObj.name})
                        };
                        $(selectId).append(`<option value="${colObj.name}">${colObj.name}</option>`)
                      }
                      str = '<th>' + colObj.name + '</th>';
                      $(str).appendTo(tableName+'>thead>tr');
                    });
                    // add render transformations to columns
                    data.columns[0].render = function (data, type, row) {
                      return '<h4>' + data + '</h4>';
                    }
                    if (config.toggleCols) {
                      // initialize multicheck
                      $(selectId).select2MultiCheckboxes({
                        tableCols:data.columns,
                        formatSelection: function(selected, total) {
                          return "Selected " + selected.length + " of " + total;
                        }
                      })

                      // set columns in multicheck
                      $(selectId).select2("data",multiCheckArray)
                    }

                    /*
                    //iterate over rows of table
                    table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
                      var data = this.data();
                      console.log(data)
                    });
                    // get column by name
                    var index = table.columns().names().indexOf('id');
                    */
                    var table = $(`#table-${config.id}`).DataTable({
                      "bDestroy": true,
                      "data": data.data,
                      "columns": data.columns,
                      "pageLength": 50,
                      "fnInitComplete": function () {
                          console.log('Datatable rendering complete');
                      },
                      //"rowCallback": function(row, data, index) {}
                    });

                    if (config.truncate) {
                      table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
                        var data = this.data();
                        Object.keys(data).forEach(function(key) {
                          data[key] = `<div class="truncate w-6/12">${data[key]}</div>`
                        });
                        this.invalidate();
                      });
                      table.draw();
                    };

                    if (config.spawnModalOnClick) {
                      table.on('dblclick', 'tbody tr', function() {
                          var rowData = table.row(this).data();
                          document.getElementById(`${config.id}-data-modal`).checked = true;
                          var div = $("<div>").addClass("grid grid-cols-3 gap-4")
                          $.each(rowData, function(key, value) {
                            var col = $("<div>").html(`<label class="block text-sm font-medium text-gray-700">${key}</label><p class="text-xs text-gray-900 mt-1">${value}</p>`).addClass("col-span-1")
                            div.append(col);
                          });
                          $(`#${config.id}-data-modal-body`).html(div)
                          if (config.nextLinkField) {
                            $(`#${config.id}-data-modal-link`).html(rowData[config.nextLinkField])
                          };
                          var rowData = table.row(this).data();
                          document.getElementById(`${config.id}-data-modal`).checked = true;
                          var div = $("<div>").addClass("grid grid-cols-3 gap-4")
                          $.each(rowData, function(key, value) {
                            var col = $("<div>").html(`<label class="block text-sm font-medium text-gray-700">${key}</label><p class="text-xs text-gray-900 mt-1">${value}</p>`).addClass("col-span-1")
                            div.append(col);
                          });
                          $(`#${config.id}-data-modal-body`).html(div)
                          if (config.nextLinkField) {
                            $(`#${config.id}-data-modal-link`).html(rowData[config.nextLinkField])
                          };

                      });
                    }
                  } else {
                    $(`#table-${config.id}`).DataTable().clear().draw()
                  };
                }).fail(function (jqXHR, exception) {
                            var msg = '';
                            if (jqXHR.status === 0) {
                                msg = 'Not connect.\n Verify Network.';
                            } else if (jqXHR.status == 404) {
                                msg = 'Requested page not found. [404]';
                            } else if (jqXHR.status == 500) {
                                msg = 'Internal Server Error [500].';
                            } else if (exception === 'parsererror') {
                                msg = 'Requested JSON parse failed.';
                            } else if (exception === 'timeout') {
                                msg = 'Time out error.';
                            } else if (exception === 'abort') {
                                msg = 'Ajax request aborted.';
                            } else {
                                msg = 'Uncaught Error.\n' + jqXHR.responseText;
                            }
                });
  }
}

function refreshTable(thisObj) {
    // get filter rules
    var builderId = `#${$(thisObj).data("selector")}-builder`
    var tableId = $(thisObj).data("selector");
    var tableSelector = `#${tableId}`
    var filterRules = $(builderId).queryBuilder('getRules');
    var selectId = `#${$(thisObj).data("selector")}-select`;
    var visible = $(selectId).select2("data");
    if (filterRules) {
      if (!filterRules["valid"]) {
        createToast("error","invalid filter")
        return;
      }
    };
    if (visible) {
      if (typeof visible[0] === 'object') {
        visible = [];
        var colObjs = $(selectId).select2("data");
        $.each(colObjs, function (k, colObj) {
          visible.push(colObj.id)
        });
      }
    }
    var filterButtonId = `#${$(thisObj).data("selector")}-filter`
    if ($(builderId).queryBuilder('getRules')) {
      $(filterButtonId).addClass("text-accent")
    }
    config = JSON.parse(localStorage.getItem(tableId));
    new Table(config).reloadData({"filter":filterRules,"visible":visible})
};

$(document).on('click', '.send-filter', function() {
    refreshTable($(this))
});

$(document).on('click', '.filter-button', function() {
  var id = `${$(this).data("selector")}-filter-modal`
  document.getElementById(id).checked = true;
});
$(document).on('click', '.column-button', function() {
  var id = `${$(this).data("selector")}-column-modal`
  document.getElementById(id).checked = true;
});
$(document).on('click', '.refresh-button', function() {
    refreshTable($(this))
});
$(document).on('click', '.reset-filter', function() {
  var builderId = `${$(this).data("selector")}-builder`
  $(`#${builderId}`).queryBuilder('reset');
  var filterButtonId = `#${$(this).data("selector")}-filter`
  $(filterButtonId).removeClass("text-accent")
});

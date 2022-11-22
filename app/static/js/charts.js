function memoryTimeSeries(url) {
  $("#mem-time-chart").html("")
  $.ajax({
    type: "GET",
    url: url,
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function(data){
        var options = {
          series: data["series"],
          chart: {
          type: 'area',
          stacked: false,
          height: 350,
          zoom: {
            type: 'x',
            enabled: true,
            autoScaleYaxis: true
          },
          toolbar: {
            autoSelected: 'zoom'
          }
        },
        dataLabels: {
          enabled: false
        },
        markers: {
          size: 0,
        },
        fill: {
          type: 'gradient',
          gradient: {
            shadeIntensity: 1,
            inverseColors: false,
            opacityFrom: 0.5,
            opacityTo: 0,
            stops: [0, 90, 100]
          },
        },
        yaxis: {
          min: 0,
          max: 100,
          title: {
            text: 'Used Memory (%)'
          },
        },
        xaxis: {
          type: 'datetime',
        },
        /*
        tooltip: {
          shared: false,
          y: {
            formatter: function (val) {
              return (val / 1000000).toFixed(0)
            }
          }
        }
        */
        };

        var chart = new ApexCharts(document.querySelector("#mem-time-chart"), options);
        chart.render();
        return(data)
    },
    error: function(errMsg) {
        return(errMsg);
    }
  })
}

function cpuLoadTimeSeries(url) {
  $("#load-time-chart").html("")
  $.ajax({
    type: "GET",
    url: url,
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function(data){
        var options = {
          series: data["series"],
          chart: {
          type: 'area',
          stacked: false,
          height: 350,
          zoom: {
            type: 'x',
            enabled: true,
            autoScaleYaxis: true
          },
          toolbar: {
            autoSelected: 'zoom'
          }
        },
        dataLabels: {
          enabled: false
        },
        markers: {
          size: 0,
        },
        fill: {
          type: 'gradient',
          gradient: {
            shadeIntensity: 1,
            inverseColors: false,
            opacityFrom: 0.5,
            opacityTo: 0,
            stops: [0, 90, 100]
          },
        },
        yaxis: {
          min: 0,
          max: 100,
          title: {
            text: 'CPU Load'
          },
        },
        xaxis: {
          type: 'datetime',
        },
        /*
        tooltip: {
          shared: false,
          y: {
            formatter: function (val) {
              return (val / 1000000).toFixed(0)
            }
          }
        }
        */
        };

        var chart = new ApexCharts(document.querySelector("#load-time-chart"), options);
        chart.render();
        return(data)
    },
    error: function(errMsg) {
        return(errMsg);
    }
  })
}

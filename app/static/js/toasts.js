function makeid(length) {
    var result           = '';
    var characters       = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    var charactersLength = characters.length;
    for ( var i = 0; i < length; i++ ) {
      result += characters.charAt(Math.floor(Math.random() * charactersLength));
   }
   return result;
}

function createToast(category, message, delay=5000) {
    var toastId = makeid(5);
    console.log(category)
    $("#divToasts").append(`<div id="${toastId}" class="alert alert-${category} text-white"><div><span>${message}</span></div></div>`)
    $("#"+toastId).delay(delay).fadeOut(300);
}

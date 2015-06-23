(function($){

    $.fn.spinner = function(options){
        var settings = $.extend({
            centered: true,
            spinner_img: '/static/map/css/ajax-loader.gif'
        }, options);

        var spinner = $("<div id='spinner'></div>").addClass('spinner');

        if(settings.centered){
            spinner.addClass('centered');
        }

        spinner.append($("<img src='"+ settings.spinner_img  +"'>"));

        this.prepend(spinner);
    }
}(jQuery));

( function( $ ){
  function arr_sub( a1, a2 ) {
    var a = [], sub = [];
    var i;
    for( i = 0; i < a1.length; i++ ) {
      a[ a1[ i ] ] = true;
    }
    for( i = 0; i < a2.length; i++ ) {
      if( a[ a2[ i ] ] ) {
        delete a[ a2[i] ];
      }
    }
    for( var k in a ) {
      if( a.hasOwnProperty(k) ){
      	sub.push( k );
      }
    }
    return sub;
  }

  $.fn.extend({
    select2MultiCheckboxes: function() {
      var options = $.extend({
        placeholder: 'Choose elements',
        formatSelection: function( selected, total ) {
          return selected.length + ' > ' + total + ' total';
        },
        wrapClass: 'wrap'
      }, arguments[ 0 ] );

      this.each(function() {
          var s2 = $( this ).select2({
            msOptions: options,
            allowClear: false,
            minimumResultsForSearch: -1,
            placeholder: options.placeholder,
            closeOnSelect: false,
            formatSelection: function() {
              var select2 = this.element.data( 'select2' );
              var total = $( 'option', this.element ).length - 1;
              var data = select2.data();
              return this.msOptions.formatSelection( data, total );
            },
            formatResult: function( item ) {
              var classes = [ this.msOptions.wrapClass ]; 
              if( $( item.element[ 0 ] ).hasClass( 'checked' ) ) {
                classes.push( 'checked' );
              }
              return $( '<div>' ).text( item.text ).addClass( classes.join( ' ' ) );
            }   
          }).data( 'select2' );
          $(this).on("select2-close", function(e) {
            // on close, hide/show the datatables columns
            var selectedCols = $(this).select2('data');
            var tableId = $(this).data("selector");
            $(`#table-${tableId}`).DataTable().columns().visible(false);
            $.each(selectedCols, function (ind, col) {
              $.each(options.tableCols, function (index, colObj) {
                if (colObj.name === col) {
                  var column = $(`#table-${tableId}`).DataTable().column(colObj.index);
                  column.visible(true);
                };
              });
            });
          });

          s2.onSelect = function( data, options ) {
            $( data.element[ 0 ] ).toggleClass( 'checked' );
            var $t = $( options.target );
            if( !$t.hasClass( this.opts.msOptions.wrapClass ) ) {
              $t = $( '.' + this.opts.msOptions.wrapClass, $t );
            }
            $t.toggleClass( 'checked' );

            var oldData = this.selection.data( 'select2-data' );

            var data = [];
            $( '.checked', this.select ).each( function() {
              data.push( $( this ).val() );
            });

            var container=this.selection.find( '.select2-chosen' );
            container.empty();

            if( data.length > 0 ) {
              this.selection.data( 'select2-data', data );
              container.append( this.opts.formatSelection() );
              this.selection.removeClass( 'select2-default' );

              if( this.opts.allowClear && this.getPlaceholder() !== undefined ) {
                this.container.addClass( 'select2-allowclear' );
              }
            } else {
              data = null;
              this.selection.data( 'select2-data', data );
              container.append( this.getPlaceholder() );
              this.selection.addClass( 'select2-default' );
              this.container.removeClass( 'select2-allowclear' );
            }

            var removed = arr_sub( oldData ? oldData : [], data ? data : [] );

            this.triggerChange({ added: data, removed: removed });
            return;
          };
          s2.data = ( function( originalData ) {
            return function( arr ) {
              if( arguments.length == 1 ) {
                var selected = {}; 
                $( arr ).each( function() {
                  selected[ this.id ] = true;
                });
                this.select.find( 'option' ).each( function() {
                  var $this = $( this );
                  $this[ selected[ $this.val() ] === true ? 'addClass' : 'removeClass' ]( 'checked' );
                });
              }
              return originalData.apply( this, arguments );
            };
          })( s2.data );
          s2.val = ( function( originalData ) {
            return function( arr ) {
              if( arguments.length === 0 ) {
                var data = [];
                $( this.data() ).each( function() {
                  data.push( this.id );
                });
                return data;
              } else {
                var oldData = this.selection.data( 'select2-data' );

                this.selection.data( 'select2-data', arr );
                this.selection.removeClass( 'select2-default' );

                if( this.opts.allowClear && this.getPlaceholder() !== undefined ) {
                  this.container.addClass( 'select2-allowclear' );
                }

                var removed = arr_sub( oldData ? oldData : [], arr );
                this.triggerChange({ added: arr, removed: removed });
                var container = this.selection.find( '.select2-chosen' );
                container.empty().append( this.opts.formatSelection() );
                return $( this.select );
              }
            };
          })( s2.val );
          s2.select.on({
            change: function( event ) {
              var i;
              if (event.removed) {
                for( i = 0; i < event.removed.length; i++ ) {
                  //$( 'option[value="' + event.removed[i] + '"]', this.select ).removeClass( 'checked' );
                }
              }
              if (event.added) {
                for( i = 0; i < event.added.length; i++ ) {
                  //$( 'option[value="' + event.added[ i ] + '"]', this.select ).addClass( 'checked' );
                }
              }
            }
          });
      });
    }
  });
})( jQuery );

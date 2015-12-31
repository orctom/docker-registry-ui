$('#confirm-delete').on('show.bs.modal', function(e) {
    var $target = $(e.relatedTarget);
    var $modal = $(this);
    if ($target.data('href')) {
        $modal.find('.danger').attr('href', $target.data('href'));
    } else if ($target.data('onclick')) {
        $modal.find('.danger').attr('onclick', $target.data('onclick'));
    }
    $("#resourceName").text($target.data('image'));
    $modal.find('.danger').bind('click', function() {
        $modal.modal('hide');
    });
});
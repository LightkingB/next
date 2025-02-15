$(document).ready(function () {
    let body = $("body");
    let loadForm = function () {
        let btn = $(this);
        $.ajax({
            url: btn.attr("href"),
            type: 'get',
            enctype: "multipart/form-data",
            cache: false,
            processData: false,
            contentType: false,
            beforeSend: function () {
                $("#modal-ajax").modal("show");
            },
            success: function (data) {
                $("#modal-ajax .modal-content").html(data.html_form);
            }
        });
        return false;
    };
    let saveForm = function () {
        let form = $(this);
        let form_data = new FormData(form[0]);
        $.ajax({
            url: form.attr("action"),
            data: form_data,
            type: form.attr("method"),
            enctype: "multipart/form-data",
            cache: false,
            processData: false,
            contentType: false,
            beforeSend: function () {
                $('.btn-ajax-save, .btn-ajax-edit').prop('disabled', true);
            },
            success: function (data) {
                if (data.form_is_valid) {
                    $('.btn-ajax-save, .btn-ajax-edit').prop('disabled', false);
                    if (data.delete_menu_item) {
                        $("li[data-id=" + data.parent_id + "]").remove();
                    }
                    if (data.html_list) {
                        $("table[id^=table-ajax-" + data.model_name + "]").find('tbody').html(data.html_list);
                    }
                    $("#modal-ajax").modal("hide");
                    toastr["success"](data.message);
                } else {
                    toastr["error"](data.message);
                    $("#modal-ajax .modal-content").html(data.html_form);

                }
            },
            error: function (xhr, ajaxOptions, thrownError) {
                $('.btn-ajax-save, .btn-ajax-edit').prop('disabled', false);
                $("#modal-ajax .modal-content").html(xhr.responseJSON['html_form']);
                toastr["error"]("Повторите попытку... ");
            }
        });
        return false;
    };
    let updateForm = function () {
        let form = $(this);
        let form_data = new FormData(form[0]);
        $.ajax({
            url: form.attr("action"),
            data: form_data,
            type: form.attr("method"),
            enctype: "multipart/form-data",
            cache: false,
            processData: false,
            contentType: false,
            success: function (data) {
                $("#modal-ajax").modal("hide");
                if (data.form_is_valid) {
                    $("tr[data-id=" + data.object_id + "]").remove()
                }
                toastr["success"](data.message);
            },
            error: function (xhr, ajaxOptions, thrownError) {
                toastr["error"]("Повторите попытку... ");
            }
        });
        return false;
    };
    body.on('click', '.ajax-load-form', loadForm);
    body.on('submit', '.ajax-update-form', updateForm);
    body.on('submit', '.ajax-save-form', saveForm);
});
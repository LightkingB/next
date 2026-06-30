(function ($) {
  const OPTION_MIN = 2;
  const OPTION_MAX = 20;

  function showModal(html) {
    const $modal = $("#modal-ajax");
    const $dialog = $modal.find(".modal-dialog");
    $dialog.toggleClass("modal-lg", html.indexOf("survey-question-form") !== -1);
    $modal.find(".modal-content").html(html);
    $modal.modal("show");
    initQuestionOptionsForm($modal.find(".survey-question-form"));
  }

  function ajaxHeaders() {
    return { "X-Requested-With": "XMLHttpRequest" };
  }

  function handleSuccess(data) {
    if (data.redirect) {
      window.location.href = data.redirect;
      return;
    }
    if (data.reload) {
      window.location.reload();
      return;
    }
    if (data.html_questions) {
      $("#questions-container").html(data.html_questions);
    }
    if (data.html_table) {
      $("#surveys-table tbody").html(data.html_table);
    }
    $("#modal-ajax").modal("hide");
    if (window.toastr && data.message) {
      toastr.success(data.message);
    }
  }

  function renumberOptions($form) {
    const $rows = $form.find(".survey-option-row");
    $rows.each(function (index) {
      $(this).find(".survey-option-index").text(index + 1);
      $(this)
        .find(".survey-option-input")
        .attr("placeholder", "Текст варианта " + (index + 1));
      $(this)
        .find(".survey-option-remove")
        .prop("disabled", $rows.length <= OPTION_MIN);
    });
    $form.find("#survey-option-add").prop("disabled", $rows.length >= OPTION_MAX);
  }

  function initQuestionOptionsForm($form) {
    if (!$form.length) {
      return;
    }
    renumberOptions($form);
  }

  $(document).on("click", ".survey-ajax-load", function (event) {
    event.preventDefault();
    $.ajax({
      url: $(this).data("url"),
      type: "get",
      headers: ajaxHeaders(),
      success: function (data) {
        showModal(data.html_form);
      },
    });
  });

  $(document).on("submit", ".survey-ajax-form", function (event) {
    event.preventDefault();
    const form = $(this);
    $.ajax({
      url: form.attr("action"),
      type: form.attr("method") || "post",
      data: new FormData(form[0]),
      processData: false,
      contentType: false,
      headers: ajaxHeaders(),
      success: handleSuccess,
      error: function (xhr) {
        if (xhr.responseJSON && xhr.responseJSON.html_form) {
          showModal(xhr.responseJSON.html_form);
        }
        if (window.toastr) {
          toastr.error(
            xhr.responseJSON && xhr.responseJSON.message
              ? xhr.responseJSON.message
              : "Ошибка"
          );
        }
      },
    });
  });

  $(document).on("click", ".survey-ajax-move", function (event) {
    event.preventDefault();
    $.ajax({
      url: $(this).data("url"),
      type: "get",
      headers: ajaxHeaders(),
      success: handleSuccess,
    });
  });

  $(document).on("click", "#survey-option-add", function () {
    const $form = $(this).closest(".survey-question-form");
    const $list = $form.find("#survey-options-list");
    const count = $list.find(".survey-option-row").length;
    if (count >= OPTION_MAX) {
      return;
    }
    const row = `
      <div class="survey-option-row">
        <span class="survey-option-index">${count + 1}</span>
        <input type="text" name="options" class="form-control survey-input survey-option-input"
               maxlength="500" placeholder="Текст варианта ${count + 1}">
        <button type="button" class="btn btn-sm survey-option-remove" title="Удалить">
          <i class="fas fa-times"></i>
        </button>
      </div>`;
    $list.append(row);
    renumberOptions($form);
    $list.find(".survey-option-input").last().focus();
  });

  $(document).on("click", ".survey-option-remove", function () {
    const $form = $(this).closest(".survey-question-form");
    const $list = $form.find("#survey-options-list");
    if ($list.find(".survey-option-row").length <= OPTION_MIN) {
      return;
    }
    $(this).closest(".survey-option-row").remove();
    renumberOptions($form);
  });
})(jQuery);

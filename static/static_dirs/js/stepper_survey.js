(function ($) {
    'use strict';

    const modalUrl = document.body.dataset.surveyModalUrl;

    function openSurveyModal(myeduId, fio) {
        const $modal = $('#surveySubmissionsModal');
        const $body = $('#survey-modal-body');
        $('#survey-modal-fio').text(fio || myeduId);

        $body.html('<div class="text-center text-muted py-3"><i class="fas fa-spinner fa-spin"></i> Загрузка…</div>');
        $modal.modal('show');

        $.get(modalUrl, {myedu_id: myeduId, fio: fio})
            .done(function (html) {
                $body.html(html);
            })
            .fail(function () {
                $body.html('<p class="text-danger mb-0">Не удалось загрузить данные анкетирования.</p>');
            });
    }

    $(document).on('click', '.survey-status-btn', function () {
        const $btn = $(this);
        openSurveyModal($btn.data('myedu-id'), $btn.data('fio'));
    });
})(jQuery);

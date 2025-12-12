from django.urls import path

from archives.views import *

app_name = 'archive'

urlpatterns = [
    path('', act_index, name='act-index'),
    path('act/<int:id>/detail/', act_detail, name='act-detail'),
    path('act/<int:act_id>/confirm/', act_confirm, name='act-confirm'),
    path('act/<int:act_id>/custom/', act_custom, name='act-custom'),
    path('act/<int:pk>/edit/', act_edit, name='act-edit'),
    path('act/<int:pk>/delete/', act_delete, name='act-delete'),

    path('custom/faculty/', custom_faculty, name='custom-faculty'),
    path('custom/faculty/<int:pk>/edit/', custom_faculty_edit, name='custom-faculty-edit'),

    path('ocr/', ocr_view, name='ocr'),
    path('detect/ocr/', detect_act_image, name='detect-ocr'),
]

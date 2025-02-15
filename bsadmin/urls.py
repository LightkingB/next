from django.urls import path

from bsadmin.views import *

urlpatterns = [
    path('', AcademicTranscriptView.as_view(), name='index'),
    path('transcript/create/', AcademicTranscriptCreateView.as_view(), name='academic-transcript-create'),
    path('transcript/<int:transcript_id>/report/', ReportRegAcademicTranscript.as_view(),
         name='academic-transcript-report'),
    path('transcript/<int:pk>/', AcademicTranscriptUpdateView.as_view(), name='academic-transcript-update'),
    path('transcript/<int:pk>/delete/', AcademicTranscriptDeleteView.as_view(), name='academic-transcript-delete'),

    path('transcript/detail/<int:pk>/faculty/', detail_academic_transcript_for_faculty,
         name='academic-transcript-faculty'),
    path('transcript/detail/<int:pk>/faculty/<int:faculty_id>/detail/', registration_academic_transcript_for_faculty,
         name='academic-transcript-faculty-registration'),

    path('transcript/student/', registration_academic_transcript_student, name='academic-transcript-student'),
    path('faculty/', faculty, name='faculty'),

    path('transcript/save-student/', save_student_academic_transcript, name='save_student_academic_transcript'),

    path('faculty/update/<int:id>/transcript/', update_faculty_transcript, name='update_faculty_transcript'),
    path('faculty/delete/<int:id>/transcript/', delete_faculty_transcript, name='delete_faculty_transcript'),

]

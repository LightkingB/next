from django.urls import path

from bsadmin.views import *

urlpatterns = [
    path('', faculty_index, name='index'),
    path('transcript/faculty/<int:faculty_id>/category/', faculty_transcript_category,
         name='faculty-transcript-category'),
    path('transcript/<int:faculty_id>/report/', ReportFacultyRegAcademicTranscript.as_view(),
         name='faculty-academic-transcript-report'),
    path('transcript/faculty/<int:faculty_id>/category/<category_id>/', registration_academic_transcript_faculty,
         name='academic-transcript-faculty-registration'),

    path('transcript/student/', registration_academic_transcript_student, name='academic-transcript-student'),
    path('faculty/', faculty, name='faculty'),

    path('transcript/save-student/', save_academic_transcript_student, name='save-student-academic-transcript'),

    path('faculty/update/<int:id>/transcript/', update_faculty_transcript, name='update_faculty_transcript'),
    path('faculty/delete/<int:id>/transcript/', delete_faculty_transcript, name='delete_faculty_transcript'),

    path('fail/transcript/', fail_transcript, name='fail_transcript'),

]

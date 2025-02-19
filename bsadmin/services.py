import requests
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Exists, OuterRef
from django.http import Http404

from bsadmin.consts import API_URL
from bsadmin.models import CustomUser, Faculty, AcademicTranscript, FacultyTranscript, RegistrationTranscript, \
    CategoryTranscript


class HttpMyEduServiceAPI:
    @staticmethod
    def get_myedu_data(email, password):
        user_response = requests.post(API_URL + "/checkuser",
                                      data={"email": email, "password": password})
        if user_response.status_code == 200:
            data = user_response.json()
            success = data.get('success', False)
            return data, success
        return None, False

    @staticmethod
    def fetch_faculties_from_myedu():
        response = requests.get(API_URL + "/open/faculty")
        return response.json() if response.status_code == 200 else None


class UserService:
    @staticmethod
    def update_or_create_user(email, password, myedu_data):
        user, _ = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                "myedu_id": myedu_data['user']['id'],
                "last_name": myedu_data['user']['last_name'],
                "first_name": myedu_data['user']['name'],
                "fathers_name": myedu_data['user']['father_name']
            }
        )
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def active_faculties():
        return Faculty.objects.filter(visit=True).order_by('title')

    @staticmethod
    def reg_academic_transcript_faculties(transcript_id):
        faculty_transcripts_qs = FacultyTranscript.objects.filter(academic_transcript_id=transcript_id)
        prefetched_transcripts = Prefetch('facultytranscript_set', queryset=faculty_transcripts_qs)

        faculties = (
            Faculty.objects
            .prefetch_related(prefetched_transcripts)
            .annotate(
                transcript_count=Count('facultytranscript',
                                       filter=Q(facultytranscript__academic_transcript_id=transcript_id)),
                registration_count=Count('facultytranscript__registrationtranscript')
            )
        )
        return faculties

    @staticmethod
    def reg_academic_transcript_faculty(faculty_id, academic_transcript_id):
        return FacultyTranscript.objects.filter(
            faculty_id=faculty_id,
            academic_transcript_id=academic_transcript_id
        ).select_related('category').annotate(
            is_used=Exists(
                RegistrationTranscript.objects.filter(faculty_transcript=OuterRef('pk'))
            )
        )

    @staticmethod
    def get_academic_transcript_by_id_or_404(transcript_id):
        try:
            return AcademicTranscript.objects.get(id=transcript_id)
        except AcademicTranscript.DoesNotExist:
            raise Http404

    @staticmethod
    def get_faculty_by_id_or_404(faculty_id):
        try:
            return Faculty.objects.get(id=faculty_id)
        except Faculty.DoesNotExist:
            raise Http404

    @staticmethod
    def get_academic_transcript_by_number(transcript_number):
        try:
            return FacultyTranscript.objects.get(transcript_number=transcript_number)
        except FacultyTranscript.DoesNotExist:
            return None

    @staticmethod
    def get_academic_transcript_by_id_or_none(id):
        try:
            return FacultyTranscript.objects.get(id=id)
        except FacultyTranscript.DoesNotExist:
            return None

    @staticmethod
    def get_all_category_transcript():
        return CategoryTranscript.objects.all()

    @staticmethod
    def is_reg_academic_transcript_for_student(transcript_id):
        reg_transcript = RegistrationTranscript.objects.filter(faculty_transcript_id=transcript_id)
        if reg_transcript:
            return True
        return False

    @staticmethod
    def get_faculty_by_myedu_faculty_id_or_none(myedu_faculty_id):
        try:
            return Faculty.objects.get(myedu_faculty_id=myedu_faculty_id)
        except Faculty.DoesNotExist:
            return None

    def fetch_and_update_faculties(self):
        faculties_data = HttpMyEduServiceAPI.fetch_faculties_from_myedu()
        if faculties_data is None:
            return None, "Ошибка при получении факультетов"

        external_faculties = {faculty["id"]: faculty for faculty in faculties_data}
        db_faculties = {faculty.myedu_faculty_id: faculty for faculty in Faculty.objects.all()}

        faculties_to_deactivate = set(db_faculties.keys()) - set(external_faculties.keys())
        faculties_to_activate = set(db_faculties.keys()) & set(external_faculties.keys())

        new_faculties = [
            Faculty(title=data["name_ru"], short_name=data["short_name_ru"], myedu_faculty_id=myedu_id, visit=True)
            for myedu_id, data in external_faculties.items() if myedu_id not in db_faculties
        ]

        with transaction.atomic():
            Faculty.objects.filter(myedu_faculty_id__in=faculties_to_deactivate).update(visit=False)
            Faculty.objects.filter(myedu_faculty_id__in=faculties_to_activate).update(visit=True)
            Faculty.objects.bulk_create(new_faculties)

        return self.active_faculties(), None

    @staticmethod
    def report_all_reg_academic_transcript_by_transcript_id(transcript_id):
        return RegistrationTranscript.objects.select_related('faculty_transcript', 'faculty').filter(
            faculty_transcript__academic_transcript_id=transcript_id).order_by('student_fio')

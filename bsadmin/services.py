import requests
from django.db import transaction
from django.db.models import Count, Q, Exists, OuterRef
from django.http import Http404

from bsadmin.consts import API_URL
from bsadmin.models import CustomUser, Faculty, FacultyTranscript, RegistrationTranscript, \
    CategoryTranscript, Speciality
from utils.convert import to_bool


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

    @staticmethod
    def fetch_specialities_from_myedu(faculty_id):
        response = requests.get(API_URL + "/open/getspecialitywithidfaculty?id_faculty=" + str(faculty_id))
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
                "fathers_name": myedu_data['user']['father_name'],
                "is_worker": to_bool(myedu_data['user']['is_working']),
            }
        )
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def active_faculties():
        return Faculty.objects.filter(visit=True, is_myedu=True).order_by('title')

    @staticmethod
    def get_first_active_faculty(myedu_faculty_id):
        return Faculty.objects.filter(myedu_faculty_id=myedu_faculty_id).first()

    @staticmethod
    def active_specialities_by_faculty(faculty_id):
        return Speciality.objects.filter(visit=True, faculty_id=faculty_id).order_by('title')

    def faculty_specialities_with_values(self, faculty_id):
        return self.active_specialities_by_faculty(faculty_id).values('myedu_spec_id', 'title')

    @staticmethod
    def specialities_by_faculty(faculty_id):
        return Speciality.objects.filter(faculty_id=faculty_id)

    @staticmethod
    def specialities_values_by_faculty(faculty_id):
        return Speciality.objects.filter(faculty_id=faculty_id).values('id', 'title', 'code')

    @staticmethod
    def academic_transcripts_by_faculty_id(faculty_id, sort_field):
        return FacultyTranscript.objects.filter(faculty_id=faculty_id).select_related('category').annotate(
            is_used=Exists(
                RegistrationTranscript.objects.filter(faculty_transcript=OuterRef('pk'))
            )
        ).order_by(sort_field, '-id')

    @staticmethod
    def active_faculties_transcripts():
        faculties = Faculty.objects.filter(visit=True, is_myedu=True).annotate(
            total_documents=Count('facultytranscript', distinct=True),
            used_documents=Count(
                'facultytranscript__registrationtranscript', distinct=True
            ),
            defective_documents=Count(
                'facultytranscript',
                filter=Q(facultytranscript__is_defective=True),
                distinct=True
            )
        ).values(
            'id', 'title', 'short_name', 'total_documents', 'used_documents', 'defective_documents'
        ).order_by('title')
        return faculties

    @staticmethod
    def reg_academic_transcript_faculty(faculty_id, category_id):
        return FacultyTranscript.objects.filter(
            faculty_id=faculty_id,
            category_id=category_id
        ).select_related('category').annotate(
            is_used=Exists(
                RegistrationTranscript.objects.filter(faculty_transcript=OuterRef('pk'))
            )
        ).order_by('-id')

    @staticmethod
    def get_faculty_by_id_or_404(faculty_id):
        try:
            return Faculty.objects.get(id=faculty_id)
        except Faculty.DoesNotExist:
            raise Http404

    @staticmethod
    def get_category_transcript_by_id_or_404(category_id):
        try:
            return CategoryTranscript.objects.get(id=category_id)
        except CategoryTranscript.DoesNotExist:
            raise Http404

    @staticmethod
    def categories():
        return CategoryTranscript.objects.all()

    @staticmethod
    def get_academic_transcript_by_number(transcript_number):
        try:
            return FacultyTranscript.objects.get(transcript_number=transcript_number)
        except FacultyTranscript.DoesNotExist:
            return None

    @staticmethod
    def get_active_academic_transcript_by_number(transcript_number):
        try:
            return FacultyTranscript.objects.get(transcript_number=transcript_number, is_defective=False)
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

    # @staticmethod
    # def is_reg_academic_transcript_for_student(transcript_id):
    #     reg_transcript = RegistrationTranscript.objects.filter(faculty_transcript_id=transcript_id)
    #     if reg_transcript:
    #         return True
    #     return False

    @staticmethod
    def is_reg_academic_transcript_for_student(transcript_id):
        return RegistrationTranscript.objects.filter(faculty_transcript_id=transcript_id).first()

    @staticmethod
    def get_faculty_by_myedu_faculty_id_or_none(myedu_faculty_id):
        try:
            return Faculty.objects.get(myedu_faculty_id=myedu_faculty_id)
        except Faculty.DoesNotExist:
            return None

    @staticmethod
    def get_spec_by_myedu_spec_id_or_none(myedu_spec_id):
        try:
            return Speciality.objects.get(myedu_spec_id=myedu_spec_id)
        except Speciality.DoesNotExist:
            return None

    def fetch_and_update_faculties(self):
        faculties_data = HttpMyEduServiceAPI.fetch_faculties_from_myedu()
        if faculties_data is None:
            return None, "Ошибка при получении факультетов"

        external_faculties = {faculty["id"]: faculty for faculty in faculties_data}
        db_faculties = {faculty.myedu_faculty_id: faculty for faculty in Faculty.objects.filter(is_myedu=True)}

        faculties_to_deactivate = set(db_faculties.keys()) - set(external_faculties.keys())
        faculties_to_activate = set(db_faculties.keys()) & set(external_faculties.keys())

        new_faculties = [
            Faculty(title=data["name_ru"], short_name=data["short_name_ru"],
                    myedu_faculty_id=myedu_id, visit=True)
            for myedu_id, data in external_faculties.items() if myedu_id not in db_faculties
        ]

        with transaction.atomic():
            Faculty.objects.filter(myedu_faculty_id__in=faculties_to_deactivate).update(visit=False)

            for myedu_id in faculties_to_activate:
                faculty = db_faculties[myedu_id]
                external_data = external_faculties[myedu_id]
                faculty.title = external_data["name_ru"]
                faculty.short_name = external_data["short_name_ru"]
                faculty.visit = True
                faculty.save(update_fields=["title", "short_name", "visit"])

            Faculty.objects.bulk_create(new_faculties)

        return self.active_faculties(), None

    def fetch_and_update_specialities_by_faculty(self, faculty):
        specialities_data = HttpMyEduServiceAPI.fetch_specialities_from_myedu(faculty.myedu_faculty_id)
        if specialities_data is None:
            return None, "Ошибка при получении специальности"
        faculty_id = faculty.id
        external_specialities = {speciality["id"]: speciality for speciality in specialities_data}
        db_specialities = {speciality.myedu_spec_id: speciality for speciality in
                           self.specialities_by_faculty(faculty_id)}

        specialities_to_deactivate = set(db_specialities.keys()) - set(external_specialities.keys())
        specialities_to_activate = set(db_specialities.keys()) & set(external_specialities.keys())

        new_specialities = [
            Speciality(title=data["name_ru"], short_name=data["short_name_ru"], code=data["code"],
                       myedu_spec_id=myedu_id, visit=True,
                       faculty_id=faculty_id)
            for myedu_id, data in external_specialities.items() if myedu_id not in db_specialities
        ]

        with transaction.atomic():
            Speciality.objects.filter(myedu_spec_id__in=specialities_to_deactivate).update(visit=False)

            for myedu_id in specialities_to_activate:
                speciality = db_specialities[myedu_id]
                external_data = external_specialities[myedu_id]
                speciality.title = external_data["name_ru"]
                speciality.short_name = external_data["short_name_ru"]
                speciality.visit = True
                speciality.faculty_id = faculty_id
                speciality.code = external_data["code"]
                speciality.save(update_fields=["title", "short_name", "visit", "code"])

            Speciality.objects.bulk_create(new_specialities)

        return self.active_faculties(), None

    @staticmethod
    def report_faculty_reg_academic_transcript(faculty_id):
        return RegistrationTranscript.objects.select_related('faculty_transcript', 'faculty').filter(
            faculty_transcript__faculty_id=faculty_id).order_by('student_fio')

    @staticmethod
    def report_all_faculty_reg_academic_transcript():
        return RegistrationTranscript.objects.select_related('faculty_transcript', 'faculty').order_by(
            'faculty_history', 'student_fio')

    @staticmethod
    def search_academic_transcript_number(transcript_number):
        reg_transcript_number = RegistrationTranscript.objects.select_related('faculty_transcript').filter(
            faculty_transcript__transcript_number__endswith=transcript_number).first()
        return reg_transcript_number

from django.db import transaction
from django.db.models import Count, Q, Exists, OuterRef, Subquery, Max
from django.http import Http404

from bsadmin.models import *
from utils.convert import to_bool
from utils.myedu import MyEduService


class UserService:
    @staticmethod
    def update_or_create_user(email, password, myedu_data):
        # Данные из MyEDU обновляются при каждом входе через MyEDU — в том числе признак сотрудника,
        # иначе однажды записанное значение не менялось (студент стал сотрудником и наоборот).
        user, _ = CustomUser.objects.update_or_create(
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
    def academic_transcript_status_counts(faculty_id, category_id=None):
        transcripts = FacultyTranscript.objects.filter(faculty_id=faculty_id)
        if category_id:
            transcripts = transcripts.filter(category_id=category_id)
        return transcripts.annotate(
            is_used=Exists(RegistrationTranscript.objects.filter(faculty_transcript=OuterRef('pk')))
        ).aggregate(
            total=Count('id'),
            free=Count('id', filter=Q(is_used=False, is_defective=False)),
            used=Count('id', filter=Q(is_used=True)),
            defective=Count('id', filter=Q(is_defective=True)),
        )

    @staticmethod
    def _transcripts_with_registration():
        registration = RegistrationTranscript.objects.filter(faculty_transcript=OuterRef('pk')).order_by('-id')
        return FacultyTranscript.objects.select_related('category', 'faculty').annotate(
            is_used=Exists(registration),
            student_fio=Subquery(registration.values('student_fio')[:1]),
            student_uuid=Subquery(registration.values('student_uuid')[:1]),
            student_faculty=Subquery(registration.values('faculty_history')[:1]),
            student_speciality=Subquery(registration.values('speciality_history')[:1]),
            issue_date=Subquery(registration.values('create_date')[:1]),
        )

    @staticmethod
    def find_academic_transcript(query, similar_limit=30):
        """Точное совпадение номера + похожие записи (часть номера или ФИО студента)."""
        transcripts = UserService._transcripts_with_registration()
        number = query.replace(" ", "")
        exact = transcripts.filter(transcript_number=number).first()
        similar = transcripts.filter(
            Q(transcript_number__icontains=number) |
            Q(registrationtranscript__student_fio__icontains=query.strip())
        ).distinct().order_by('transcript_number')
        if exact:
            similar = similar.exclude(pk=exact.pk)
        return exact, list(similar[:similar_limit + 1])

    @staticmethod
    def academic_transcript_category_stats(faculty_id):
        """{category_id: {total, free, used, defective}} по бланкам факультета."""
        rows = (FacultyTranscript.objects.filter(faculty_id=faculty_id)
                .annotate(is_used=Exists(RegistrationTranscript.objects.filter(faculty_transcript=OuterRef('pk'))))
                .values('category_id')
                .annotate(total=Count('id'),
                          free=Count('id', filter=Q(is_used=False, is_defective=False)),
                          used=Count('id', filter=Q(is_used=True)),
                          defective=Count('id', filter=Q(is_defective=True))))
        return {row.pop('category_id'): row for row in rows}

    @staticmethod
    def academic_transcripts_by_faculty_id(faculty_id, sort_field, query=None, status=None, category_id=None):
        transcripts = UserService._transcripts_with_registration().filter(faculty_id=faculty_id)
        if category_id:
            transcripts = transcripts.filter(category_id=category_id)
        if query:
            transcripts = transcripts.filter(transcript_number__icontains=query)
        if status == "free":
            transcripts = transcripts.filter(is_used=False, is_defective=False)
        elif status == "used":
            transcripts = transcripts.filter(is_used=True)
        elif status == "defective":
            transcripts = transcripts.filter(is_defective=True)
        return transcripts.order_by(sort_field, '-id')

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
            ),
            free_documents=Count(
                'facultytranscript',
                filter=Q(facultytranscript__is_defective=False,
                         facultytranscript__registrationtranscript__isnull=True),
                distinct=True
            ),
            last_issued=Max('facultytranscript__registrationtranscript__create_date'),
        ).values(
            'id', 'title', 'short_name', 'total_documents', 'used_documents', 'defective_documents',
            'free_documents', 'last_issued'
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
    def check_transcript_for_issue(transcript_number):
        """
        Проверяет, можно ли выдать бланк. Возвращает (transcript | None, ошибка | None).
        Ошибка объясняет причину: не зарегистрирован, повреждён или уже выдан (кому).
        """
        number = (transcript_number or "").replace(" ", "").strip()
        if not number:
            return None, "Введите номер справки."
        transcript = (FacultyTranscript.objects.select_related("faculty", "category")
                      .filter(transcript_number=number).first())
        if not transcript:
            return None, f"Бланк № {number} не зарегистрирован. Сначала внесите его в категорию факультета."
        if transcript.is_defective:
            return None, f"Бланк № {number} отмечен как повреждённый — выдать его нельзя."
        issued = RegistrationTranscript.objects.filter(faculty_transcript=transcript).first()
        if issued:
            return None, (f"Бланк № {number} уже выдан: {issued.student_fio} "
                          f"({issued.create_date:%d.%m.%Y}).")
        return transcript, None

    @staticmethod
    def issued_transcripts_by_students(student_ids):
        """{student_uuid: [выданные справки]} — чтобы видеть, кому справка уже выдавалась."""
        result = {}
        for reg in (RegistrationTranscript.objects
                    .filter(student_uuid__in=[str(s) for s in student_ids if s])
                    .select_related("faculty_transcript").order_by("-create_date")):
            result.setdefault(reg.student_uuid, []).append(reg)
        return result

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
        faculties_data = MyEduService.fetch_faculties()
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
        specialities_data = MyEduService.fetch_specialities(faculty.myedu_faculty_id)
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
    def report_faculty_reg_academic_transcript(faculty_id, query=None):
        reports = RegistrationTranscript.objects.select_related('faculty_transcript', 'faculty').filter(
            faculty_transcript__faculty_id=faculty_id)
        if query:
            reports = reports.filter(
                Q(faculty_transcript__transcript_number__icontains=query) | Q(student_fio__icontains=query))
        return reports.order_by('student_fio')

    REPORT_SORTS = {
        "faculty": ("faculty_history", "student_fio"),
        "new": ("-create_date", "-id"),
        "old": ("create_date", "id"),
        "fio": ("student_fio", "-id"),
    }

    @staticmethod
    def report_all_faculty_reg_academic_transcript(filters=None):
        filters = filters or {}
        reports = RegistrationTranscript.objects.select_related(
            'faculty_transcript', 'faculty_transcript__category', 'faculty')
        query = filters.get("q")
        if query:
            reports = reports.filter(
                Q(faculty_transcript__transcript_number__icontains=query.replace(" ", "")) |
                Q(student_fio__icontains=query))
        if filters.get("faculty"):
            reports = reports.filter(faculty_id=filters["faculty"])
        if filters.get("category"):
            reports = reports.filter(faculty_transcript__category_id=filters["category"])
        if filters.get("date_from"):
            reports = reports.filter(create_date__date__gte=filters["date_from"])
        if filters.get("date_to"):
            reports = reports.filter(create_date__date__lte=filters["date_to"])
        sort = UserService.REPORT_SORTS.get(filters.get("sort") or "faculty", UserService.REPORT_SORTS["faculty"])
        return reports.order_by(*sort)

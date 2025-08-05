from datetime import datetime

import requests
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q, Window, F, Prefetch, OuterRef, Exists, Subquery, Value, CharField, Count
from django.db.models.functions import RowNumber, Concat
from django.http import Http404
from django.utils.timezone import make_aware

from bsadmin.consts import MYEDU_LOGIN, MYEDU_PASSWORD
from bsadmin.models import CustomUser, Faculty, Speciality
from stepper.consts import EMPTY_RESPONSE_STEPPER_DATA, STUDENT_CS, TEACHER_CS, CS_PROCESS, CS_FINISHED
from stepper.entity import StudentInfo
from stepper.exceptions import ClearanceCreationError, IssuanceRemovalError
from stepper.models import Issuance, ClearanceSheet, Trajectory, StageStatus, StageEmployee, TemplateStep, \
    IssuanceHistory, EduYear
from utils.convert import save_signature_image


class StepperService:
    @staticmethod
    def fetch_students(request, api_url, search_query=None):
        try:
            if search_query:
                response = requests.post(api_url, data={"search": search_query})
            else:
                response = requests.get(api_url)

            if response.status_code == 200:
                return response.json()
            messages.error(request, "Повторите попытку позже...")
        except requests.RequestException:
            messages.error(request, "Ошибка сети. Попробуйте позже...")
        return []

    @staticmethod
    def get_stepper_data_from_api(url, search=None, faculty_id=0, specialty_id=0):
        data = {
            "login": MYEDU_LOGIN,
            "password": MYEDU_PASSWORD,
            "faculty_id": faculty_id,
            "speciality_id": specialty_id
        }

        if search:
            data["search"] = search

        try:
            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                try:
                    json_data = response.json()
                    return json_data if isinstance(json_data, list) else EMPTY_RESPONSE_STEPPER_DATA
                except ValueError:
                    return EMPTY_RESPONSE_STEPPER_DATA
            else:
                return EMPTY_RESPONSE_STEPPER_DATA
        except requests.RequestException:
            return EMPTY_RESPONSE_STEPPER_DATA

    @staticmethod
    def get_stepper_employees():
        return (
            StageEmployee.objects.filter(employee__is_worker=True,
                                         template_stage__category=TemplateStep.STUDENT)
            .select_related('employee', 'template_stage', 'template_stage__stage')
            .order_by('is_active')
        )

    @staticmethod
    def students_from_issuance(myeduid, type_choices=None, fio=None):
        queryset = (
            Issuance.objects.filter(student=myeduid)
            .select_related('faculty', 'speciality').order_by("-created_at")
        )
        if type_choices is not None:
            queryset = queryset.filter(type_choices=type_choices)
        if fio:
            queryset = queryset.filter(fio__icontains=fio)
        return queryset

    def spec_issuance_students(self, myeduid=0):
        return self.students_from_issuance(myeduid=myeduid, type_choices=Issuance.SPEC)

    def archive_issuance_students(self, myeduid=0):
        return self.students_from_issuance(myeduid=myeduid, type_choices=Issuance.OTHER)

    def spec_students_issuance_search(self, fio, myeduid=0):
        return self.students_from_issuance(type_choices=Issuance.SPEC, fio=fio, myeduid=myeduid)

    def archive_students_issuance_search(self, fio, myeduid=0):
        return self.students_from_issuance(type_choices=Issuance.OTHER, fio=fio, myeduid=myeduid)

    @staticmethod
    def create_issuance_form(form, user, signature_base64, **myedu):
        if not signature_base64:
            return None, "Обязательное наличие подписи"

        if not form.is_valid():
            return None, "Введите корректные данные"

        instance = form.save(commit=False)

        faculty = Faculty.objects.filter(myedu_faculty_id=myedu['faculty_id']).first()
        speciality = Speciality.objects.filter(myedu_spec_id=myedu['specialty_id']).first()
        instance.faculty = faculty
        instance.speciality = speciality
        instance.student = myedu['myeduid']
        instance.type_choices = myedu['type']
        if myedu.get('cs_id', None):
            instance.cs_id = myedu['cs_id']

        signature_file = save_signature_image(signature_base64)

        if signature_file:
            instance.signature = signature_file

        if myedu.get('profile_base64', None):
            profile_file = save_signature_image(myedu['profile_base64'], storage="users")

            if profile_file:
                instance.profile = profile_file

        instance.employee = user
        instance.save()

        return instance, None

    @staticmethod
    def active_cs():
        return ClearanceSheet.objects.filter(completed_at__isnull=True)

    @staticmethod
    def active_edu_year():
        return EduYear.objects.filter(active=True).first()

    @staticmethod
    def filter_edu_year_by_id(edu_year_id):
        return EduYear.objects.filter(id=edu_year_id).first()

    @staticmethod
    def edu_years():
        return EduYear.objects.all()

    @staticmethod
    def cs_done_list(search_query=None):
        clearance_sheets = ClearanceSheet.objects.filter(category=ClearanceSheet.STUDENT,
                                                         type_choices__isnull=False).order_by('-completed_at')
        if search_query:
            clearance_sheets = clearance_sheets.filter(
                Q(student_fio__icontains=search_query) | Q(myedu_id__icontains=search_query)
            )
        return clearance_sheets

    def active_cs_by_myeduid(self, myeduid):
        return self.active_cs().filter(myedu_id=myeduid)

    def first_active_cs(self, myeduid):
        return self.active_cs_by_myeduid(myeduid).first()

    def has_active_cs(self, myeduid):
        return self.active_cs_by_myeduid(myeduid).exists()

    @staticmethod
    def create_cs(data):
        sheet = ClearanceSheet.objects.create(
            myedu_id=data["student"],
            student_fio=data["student_fio"],
            myedu_faculty=data["myedu_faculty"],
            myedu_faculty_id=data["myedu_faculty_id"],
            myedu_spec=data["myedu_spec"],
            myedu_spec_id=data["myedu_spec_id"],
            duty=data["duty"],
            category=ClearanceSheet.STUDENT
        )
        return sheet

    @staticmethod
    def get_open_clearance_sheets_with_stage(search_query=None, type_param=None, faculty_id=0):
        open_clearance_sheets = None
        if type_param == STUDENT_CS:
            open_clearance_sheets = ClearanceSheet.objects.filter(category=ClearanceSheet.STUDENT,
                                                                  type_choices__isnull=True)
        elif type_param == TEACHER_CS:
            open_clearance_sheets = ClearanceSheet.objects.filter(category=ClearanceSheet.TEACHER,
                                                                  myedu_faculty_id=faculty_id)

        if search_query:
            open_clearance_sheets = open_clearance_sheets.filter(
                Q(student_fio__icontains=search_query) | Q(myedu_id__icontains=search_query)
            )

        open_clearance_sheets = open_clearance_sheets.order_by("-id")

        trajectories = (
            Trajectory.objects
            .filter(
                clearance_sheet__in=open_clearance_sheets,
                completed_at__isnull=True
            )
            .annotate(
                row_number=Window(
                    expression=RowNumber(),
                    partition_by=F("clearance_sheet"),
                    order_by=F("template_stage__order").asc()
                )
            )
            .filter(row_number=1)
            .select_related("clearance_sheet", "template_stage", "template_stage__stage")
        )

        clearance_with_stage = {t.clearance_sheet_id: t.template_stage for t in trajectories}

        students = [
            {
                "id": sheet.id,
                "fio": sheet.student_fio,
                "faculty_name": sheet.myedu_faculty,
                "spec_name": sheet.myedu_spec,
                "order": sheet.order,
                "order_date": sheet.order_date,
                "order_status": sheet.order_status,
                "current_stage": clearance_with_stage.get(sheet.id),
                "myedu_id": sheet.myedu_id,
                "completed_at": sheet.completed_at
            }
            for sheet in open_clearance_sheets
        ]

        return students

    @staticmethod
    def get_clearance_sheets_status(status_param, search_query=None):
        open_clearance_sheets = ClearanceSheet.objects.filter(category=ClearanceSheet.STUDENT,
                                                              type_choices__isnull=True, last_active=True)
        if search_query:
            open_clearance_sheets = open_clearance_sheets.filter(
                Q(student_fio__icontains=search_query) | Q(myedu_id__icontains=search_query)
            )

        if status_param == CS_FINISHED:
            open_clearance_sheets = open_clearance_sheets.filter(completed_at__isnull=False)
        else:
            open_clearance_sheets = open_clearance_sheets.filter(completed_at__isnull=True)

        open_clearance_sheets = open_clearance_sheets.order_by("-id")

        students = [
            {
                "id": sheet.id,
                "fio": sheet.student_fio,
                "faculty_name": sheet.myedu_faculty,
                "spec_name": sheet.myedu_spec,
                "order": sheet.order,
                "order_date": sheet.order_date,
                "order_status": sheet.order_status,
                "current_stage": None,
                "myedu_id": sheet.myedu_id,
                "completed_at": sheet.completed_at
            }
            for sheet in open_clearance_sheets
        ]

        return students

    @staticmethod
    def get_open_clearance_sheets_with_stage_filter(stage_id, search_query=None):
        unfinished_previous = Trajectory.objects.filter(
            clearance_sheet=OuterRef('clearance_sheet'),
            template_stage__order__lt=OuterRef('template_stage__order'),
            completed_at__isnull=True
        )

        current_trajectories = (
            Trajectory.objects
            .filter(
                template_stage_id=stage_id,
                completed_at__isnull=True,
                clearance_sheet__completed_at=None,
                clearance_sheet__category=ClearanceSheet.STUDENT,
            )
            .annotate(has_unfinished_previous=Exists(unfinished_previous))
            .filter(has_unfinished_previous=False)
            .select_related("clearance_sheet", "template_stage")
        )

        if search_query:
            current_trajectories = current_trajectories.filter(
                Q(clearance_sheet__student_fio__icontains=search_query) |
                Q(clearance_sheet__myedu_id__icontains=search_query)
            )

        return [
            {
                "id": t.clearance_sheet.id,
                "fio": t.clearance_sheet.student_fio,
                "faculty_name": t.clearance_sheet.myedu_faculty,
                "order": t.clearance_sheet.order,
                "order_date": t.clearance_sheet.order_date,
                "order_status": t.clearance_sheet.order_status,
                "spec_name": t.clearance_sheet.myedu_spec,
                "current_stage": t.template_stage,
                "myedu_id": t.clearance_sheet.myedu_id,
                "completed_at": t.clearance_sheet.completed_at
            }
            for t in current_trajectories
        ]

    @staticmethod
    def get_cs_by_id(cs_id):
        try:
            return ClearanceSheet.objects.get(id=cs_id)
        except ClearanceSheet.DoesNotExist:
            raise Http404

    @staticmethod
    def get_cs_by_myeduid_or_none(myeduid):
        try:
            return ClearanceSheet.objects.get(myedu_id=myeduid)
        except ClearanceSheet.DoesNotExist:
            return None

    @staticmethod
    def get_trajectories_for_student(student):
        return (
            Trajectory.objects.filter(clearance_sheet=student)
            .select_related('template_stage', 'template_stage__stage')
            .order_by('template_stage__order')
        )

    @staticmethod
    def undo_trajectories(trajectories, post_data):
        updated_trajectories = []
        for trajectory in trajectories:
            checkbox_name = f"trajectory_{trajectory.id}"
            if checkbox_name not in post_data:
                trajectory.completed_at = None
            updated_trajectories.append(trajectory)

        if updated_trajectories:
            Trajectory.objects.bulk_update(updated_trajectories, ["completed_at"])

        return updated_trajectories

    @staticmethod
    def cs_history(myedu_id):
        trajectory_prefetch = Prefetch(
            'trajectory_set',
            queryset=Trajectory.objects.select_related('template_stage', 'template_stage__stage', 'assigned_by')
        )
        return ClearanceSheet.objects.filter(myedu_id=myedu_id).prefetch_related(trajectory_prefetch)

    @staticmethod
    def cs_history_detail(cs_object):
        return (
            Trajectory.objects.filter(clearance_sheet=cs_object)
            .select_related("template_stage", "template_stage__stage")
            .prefetch_related("stagestatus_set", "stagestatus_set__processed_by")
            .order_by("template_stage__order")
        )

    @staticmethod
    def create_trajectories_for_student(student, selected_stages, user):
        try:
            with transaction.atomic():
                trajectories = []
                for stage in selected_stages:
                    trajectory = Trajectory(
                        clearance_sheet=student,
                        template_stage=stage,
                        assigned_by=user
                    )
                    trajectories.append(trajectory)
                Trajectory.objects.bulk_create(trajectories)
            return True, "Траектория успешно создана для всех этапов."
        except Exception as e:
            return False, f"Ошибка при создании траектории: {str(e)}"

    @staticmethod
    def student_trajectories(student):
        return Trajectory.objects.filter(clearance_sheet=student)

    def student_trajectories_only_ids(self, student):
        return self.student_trajectories(student).only("id")

    @staticmethod
    def has_stage_status_trajectories(trajectories_ids):
        return StageStatus.objects.filter(trajectory__in=trajectories_ids).exists()

    @staticmethod
    def get_employee_for_user(user, category=None):
        return StageEmployee.objects.filter(employee=user, template_stage__category=category,
                                            is_active=True).select_related("template_stage").first()

    @staticmethod
    def mandatory_stages():
        return TemplateStep.objects.filter(stage__is_mandatory=True)

    def get_cs_employees_by_category(self, employee_stage, category=None):
        mandatory_stages = self.mandatory_stages().filter(category=category)

        subquery = Trajectory.objects.filter(
            clearance_sheet=OuterRef("trajectory__clearance_sheet"),
            template_stage__in=mandatory_stages,
            template_stage__order__lt=OuterRef("trajectory__template_stage__order"),
            completed_at__isnull=True
        ).values("id")[:1]

        employees = (
            ClearanceSheet.objects
            .filter(
                trajectory__template_stage=employee_stage,
                trajectory__completed_at__isnull=True,
                completed_at__isnull=True
            )
            .annotate(
                has_unfinished_previous_stage=Exists(subquery),
                current_trajectory_id=F("trajectory__id"),
                status=F("trajectory__completed_at")
            )
            .filter(has_unfinished_previous_stage=False)
            .order_by("-trajectory__update_at")
        )

        return employees

    @staticmethod
    def get_cs_history_employees_by_category(employee_stage):
        latest_status_comment = StageStatus.objects.filter(
            trajectory=OuterRef("trajectory__id")
        ).order_by("-created_at")

        processed_employees = (
            ClearanceSheet.objects
            .filter(
                trajectory__template_stage=employee_stage,
                trajectory__completed_at__isnull=False
            )
            .annotate(
                current_trajectory_id=F("trajectory__id"),
                status=F("trajectory__completed_at"),
                last_comment=Subquery(latest_status_comment.values("comment_text")[:1]),
                last_commented_at=Subquery(latest_status_comment.values("created_at")[:1])
            )
            .order_by("-trajectory__completed_at")
        )
        return processed_employees

    @staticmethod
    def save_stage_status(form, trajectory, user, end_flag):
        try:
            with transaction.atomic():
                instance = form.save(commit=False)
                instance.trajectory = trajectory
                instance.processed_by = user
                instance.save()

                if end_flag == "on":
                    trajectory.completed_at = make_aware(datetime.now())
                    trajectory.save(update_fields=["completed_at"])
                    trajectory.clearance_sheet.update_completed_at()
                return trajectory
        except IntegrityError:
            return None

    @staticmethod
    def create_clearance_sheet_with_trajectories(
            student: StudentInfo,
            assigned_by: CustomUser,
            category_filter: str = TemplateStep.TEACHER
    ) -> ClearanceSheet:
        try:
            with transaction.atomic():
                clearance_sheet = ClearanceSheet.objects.create(
                    myedu_id=student.myedu_id,
                    student_fio=student.full_name,
                    myedu_faculty_id=student.faculty_id,
                    myedu_faculty=student.faculty,
                    myedu_spec_id=student.specialty_id,
                    myedu_spec=student.specialty,
                    category=ClearanceSheet.TEACHER
                )

                template_steps = TemplateStep.objects.filter(category=category_filter)

                if not template_steps.exists():
                    raise ClearanceCreationError("Не найдены этапы для указанной категории.")

                trajectories = [
                    Trajectory(
                        clearance_sheet=clearance_sheet,
                        template_stage=step,
                        assigned_by=assigned_by
                    )
                    for step in template_steps
                ]

                Trajectory.objects.bulk_create(trajectories)

                return clearance_sheet

        except IntegrityError as e:
            raise ClearanceCreationError("Ошибка при сохранении обходного листа.") from e

        except Exception as e:
            raise ClearanceCreationError("Не удалось создать обходной лист по технической причине.") from e

    @staticmethod
    def get_clearance_students(type_choice, has_field_name, extra_filter=None):
        issuance_subquery = Issuance.objects.filter(
            student=OuterRef('myedu_id'),
            type_choices=type_choice,
            cs_id=OuterRef('id')
        )

        qs = ClearanceSheet.objects.annotate(
            **{
                has_field_name: Exists(issuance_subquery),
                'row_number': Window(
                    expression=RowNumber(),
                    partition_by=[F('myedu_id')],
                    order_by=F('id').desc()
                )
            }
        ).filter(
            **{
                has_field_name: False,
                'completed_at__isnull': False,
                'last_active': True,
                'row_number': 1,

            }
        )
        if extra_filter:
            qs = qs.filter(**extra_filter)

        return qs.order_by('-id')

    @staticmethod
    def get_clearance_history(type_choice, has_field_name):
        issuance_subquery = Issuance.objects.filter(
            student=OuterRef('myedu_id'),
            type_choices=type_choice,
            cs_id=OuterRef('id')
        )
        issuance_id_subquery = issuance_subquery.values('id')[:1]

        qs = ClearanceSheet.objects.annotate(
            issuance_id=Subquery(issuance_id_subquery),
            **{has_field_name: Exists(issuance_subquery)}
        ).filter(
            **{has_field_name: True},
            completed_at__isnull=False
        ).order_by('-id')

        return qs

    @staticmethod
    def get_clearance_statistics_by_faculty(type_choice, edu_year, has_field_name):
        issuance_subquery = Issuance.objects.filter(
            student=OuterRef('myedu_id'),
            type_choices=type_choice,
            cs_id=OuterRef('id')
        )

        issuance_id_subquery = issuance_subquery.values('id')[:1]

        base_qs = ClearanceSheet.objects.annotate(
            issuance_id=Subquery(issuance_id_subquery),
            **{has_field_name: Exists(issuance_subquery)}
        ).filter(
            **{has_field_name: True},
            edu_year=edu_year,
            completed_at__isnull=False
        )

        stats = list(base_qs.values('myedu_faculty').annotate(
            total=Count('id')
        ).order_by('myedu_faculty'))

        total_sum = sum(item['total'] for item in stats)

        stats.append({
            'myedu_faculty': 'Итого',
            'total': total_sum
        })

        return stats

    def create_clearance_sheet(self, student: dict, myedu_id, type_choices=None, completed=False):
        data = {
            "myedu_id": myedu_id,
            "student_fio": student.get('student_fio', ''),
            "myedu_faculty_id": student.get('faculty_id', 0),
            "myedu_faculty": student.get('faculty_name', ''),
            "myedu_spec_id": student.get('speciality_id', 0),
            "myedu_spec": student.get('speciality_name', ''),
            "order_status": student.get('id_movement_info', ''),
            "order": student.get('info', ''),
            "order_date": student.get('date_movement', ''),
            "edu_year": self.active_edu_year()
        }

        if type_choices is not None:
            data['type_choices'] = type_choices
        if completed:
            data['completed_at'] = make_aware(datetime.now())

        return ClearanceSheet.objects.create(**data)

    @staticmethod
    def remove_issuance_and_history(myedu_id: int, cs_id: int, type_choice: str) -> bool:
        try:
            with transaction.atomic():
                issuance = Issuance.objects.select_for_update().filter(
                    student=myedu_id, type_choices=type_choice
                ).first()

                if issuance:
                    IssuanceHistory.objects.filter(
                        student=myedu_id,
                        type_choices=type_choice,
                        cs=cs_id
                    ).delete()
                    issuance.delete()
                    return True
                return False
        except Exception as e:
            raise IssuanceRemovalError(f"Ошибка при удалении Issuance: {str(e)}") from e

    @staticmethod
    def get_trajectories_with_annotations(clearance_sheet):
        latest_status_qs = StageStatus.objects.filter(
            trajectory=OuterRef('pk')
        ).order_by('-created_at')

        trajectories = (
            Trajectory.objects
            .filter(clearance_sheet=clearance_sheet)
            .select_related('template_stage', 'template_stage__stage', 'assigned_by')
            .annotate(
                last_comment=Subquery(latest_status_qs.values('comment_text')[:1]),
                last_processed_by_id=Subquery(latest_status_qs.values('processed_by')[:1]),
            )
        )

        user_subquery = CustomUser.objects.filter(id=OuterRef('last_processed_by_id')).annotate(
            full_name=Concat(
                F('first_name'), Value(' '),
                F('last_name'), Value(' '),
                F('fathers_name')
            )
        ).values('full_name')[:1]

        return trajectories.annotate(
            last_processed_by_name=Subquery(user_subquery, output_field=CharField())
        )

import io
import os
import re
from collections import defaultdict
from datetime import datetime

from django.db.models import Prefetch, Q
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from student.models import Survey, SurveyAnswerItem, SurveyQuestion, SurveySubmission

_SUBMISSION_LIST_FIELDS = (
    "id",
    "student_fio",
    "student_login",
    "student_group",
    "submitted_at",
    "edu_year_id",
    "edu_year__id",
    "edu_year__title",
    "user_id",
    "user__myedu_id",
    "user__student_profile__work_phone",
)

_ANSWER_ITEM_FIELDS = (
    "id",
    "submission_id",
    "question_id",
    "option_id",
    "custom_text",
    "question__id",
    "question__text",
    "question__order",
    "option__id",
    "option__text",
    "option__order",
)


def _answers_prefetch():
    return Prefetch(
        "answers",
        queryset=SurveyAnswerItem.objects.select_related("question", "option")
        .only(*_ANSWER_ITEM_FIELDS)
        .order_by("question__order", "option__order"),
    )


def _questions_prefetch():
    return Prefetch(
        "questions",
        queryset=SurveyQuestion.objects.order_by("order", "id").only(
            "id", "survey_id", "text", "order"
        ),
    )

FONT_REGULAR = "SurveyDejaVu"
FONT_BOLD = "SurveyDejaVu-Bold"
_FONT_REGISTERED = False

FONT_CANDIDATES = (
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
)


def _register_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    for regular_path, bold_path in FONT_CANDIDATES:
        if os.path.exists(regular_path):
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, regular_path))
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont(FONT_BOLD, bold_path))
            else:
                pdfmetrics.registerFont(TTFont(FONT_BOLD, regular_path))
            _FONT_REGISTERED = True
            return
    raise RuntimeError("Не найден TTF-шрифт с поддержкой кириллицы для PDF.")


def _pdf_styles():
    _register_fonts()
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SurveyTitle",
            parent=styles["Heading1"],
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#A00E07"),
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "SurveySubtitle",
            parent=styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#555555"),
            spaceAfter=2,
        ),
        "section": ParagraphStyle(
            "SurveySection",
            parent=styles["Heading2"],
            fontName=FONT_BOLD,
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#333333"),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "SurveyBody",
            parent=styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=9,
            leading=12,
        ),
        "student": ParagraphStyle(
            "SurveyStudent",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#A00E07"),
            spaceBefore=6,
            spaceAfter=3,
        ),
        "table_header": ParagraphStyle(
            "SurveyTableHeader",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "SurveyTableCell",
            parent=styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=10,
            wordWrap="CJK",
        ),
        "table_cell_center": ParagraphStyle(
            "SurveyTableCellCenter",
            parent=styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=10,
            alignment=1,
            wordWrap="CJK",
        ),
        "meta_label": ParagraphStyle(
            "SurveyMetaLabel",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#555555"),
        ),
        "meta_value": ParagraphStyle(
            "SurveyMetaValue",
            parent=styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#333333"),
        ),
        "muted": ParagraphStyle(
            "SurveyMuted",
            parent=styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#888888"),
        ),
    }


def _escape_pdf_text(value):
    text = str(value or "")
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _paragraph(text, style):
    return Paragraph(_escape_pdf_text(text), style)


def _answers_cell(texts, styles):
    if not texts:
        return _paragraph("—", styles["muted"])
    if len(texts) == 1:
        return _paragraph(texts[0], styles["table_cell"])
    bullets = "<br/>".join(f"• {_escape_pdf_text(item)}" for item in texts)
    return Paragraph(bullets, styles["table_cell"])


def _myedu_id(submission):
    user = getattr(submission, "user", None)
    if user and getattr(user, "myedu_id", None):
        return str(user.myedu_id)
    return "—"


def _work_phone(submission):
    user = getattr(submission, "user", None)
    if user:
        profile = getattr(user, "student_profile", None)
        if profile and profile.work_phone:
            return profile.work_phone
    return "—"


def _summary_col_widths(total_width):
    fractions = (0.03, 0.19, 0.08, 0.11, 0.16, 0.12, 0.15, 0.16)
    return [total_width * part for part in fractions]


def _answers_col_widths(total_width):
    fractions = (0.05, 0.45, 0.50)
    return [total_width * part for part in fractions]


def _base_table_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#A00E07")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d8d8d8")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def _safe_filename_part(value, fallback="export"):
    cleaned = re.sub(r"[^\w\s-]", "", str(value or ""), flags=re.UNICODE).strip().replace(" ", "_")
    return cleaned[:60] or fallback


class SurveyExportService:
    @staticmethod
    def survey_for_export(survey_id, *, include_questions=False):
        qs = Survey.objects.filter(pk=survey_id).only("id", "title")
        if include_questions:
            qs = qs.prefetch_related(_questions_prefetch())
        return qs

    @staticmethod
    def get_ordered_questions(survey):
        prefetched = getattr(survey, "_prefetched_objects_cache", None)
        if prefetched is not None and "questions" in prefetched:
            return list(prefetched["questions"])
        return list(
            SurveyQuestion.objects.filter(survey_id=survey.pk)
            .order_by("order", "id")
            .only("id", "text", "order")
        )

    @staticmethod
    def completions_filter_meta(survey):
        """Учебные годы и группы для фильтра (2 запроса)."""
        from stepper.models import EduYear

        rows = (
            SurveySubmission.objects.filter(survey=survey)
            .values_list("edu_year_id", "student_group")
            .distinct()
        )
        edu_year_ids = set()
        groups = set()
        for edu_year_id, group in rows:
            edu_year_ids.add(edu_year_id)
            if group:
                groups.add(group)
        edu_years = (
            EduYear.objects.filter(pk__in=edu_year_ids).only("id", "title").order_by("-title")
            if edu_year_ids
            else EduYear.objects.none()
        )
        return {"edu_years": edu_years, "groups": sorted(groups)}

    @staticmethod
    def _submissions_base_queryset(survey):
        return (
            SurveySubmission.objects.filter(survey=survey)
            .order_by("-submitted_at")
            .select_related("edu_year", "user", "user__student_profile")
            .only(*_SUBMISSION_LIST_FIELDS)
        )

    @staticmethod
    def filtered_submissions(survey, cleaned_data=None, *, prefetch_answers=False):
        qs = SurveyExportService._submissions_base_queryset(survey)

        if prefetch_answers:
            qs = qs.prefetch_related(_answers_prefetch())

        if not cleaned_data:
            return qs

        edu_year = cleaned_data.get("edu_year")
        if edu_year:
            qs = qs.filter(edu_year=edu_year)

        date_from = cleaned_data.get("date_from")
        if date_from:
            qs = qs.filter(submitted_at__date__gte=date_from)

        date_to = cleaned_data.get("date_to")
        if date_to:
            qs = qs.filter(submitted_at__date__lte=date_to)

        group = (cleaned_data.get("group") or "").strip()
        if group:
            qs = qs.filter(student_group__icontains=group)

        search = (cleaned_data.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(student_fio__icontains=search) | Q(student_login__icontains=search)
            )

        return qs

    @staticmethod
    def submission_with_answers_queryset(survey_id):
        return SurveyExportService._submissions_base_queryset(Survey(pk=survey_id)).prefetch_related(
            _answers_prefetch()
        )

    @staticmethod
    def filter_submissions(survey, cleaned_data):
        return SurveyExportService.filtered_submissions(
            survey, cleaned_data, prefetch_answers=True
        )

    @staticmethod
    def filter_summary(cleaned_data):
        parts = []
        edu_year = cleaned_data.get("edu_year")
        parts.append(edu_year.title if edu_year else "все годы")

        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        if date_from or date_to:
            left = date_from.strftime("%d.%m.%Y") if date_from else "…"
            right = date_to.strftime("%d.%m.%Y") if date_to else "…"
            parts.append(f"{left} — {right}")
        else:
            parts.append("весь период")

        group = (cleaned_data.get("group") or "").strip()
        parts.append(group or "все группы")

        search = (cleaned_data.get("search") or "").strip()
        if search:
            parts.append(f"поиск: {search}")

        return parts

    @staticmethod
    def filter_summary_line(cleaned_data):
        edu_year = cleaned_data.get("edu_year")
        year = edu_year.title if edu_year else "все годы"

        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        if date_from or date_to:
            left = date_from.strftime("%d.%m.%Y") if date_from else "…"
            right = date_to.strftime("%d.%m.%Y") if date_to else "…"
            period = f"{left} — {right}"
        else:
            period = "весь период"

        group = (cleaned_data.get("group") or "").strip() or "все группы"
        search = (cleaned_data.get("search") or "").strip()
        line = f"Учебный год: {year}; период: {period}; группа: {group}"
        if search:
            line += f"; поиск: {search}"
        return line

    @staticmethod
    def ordered_answer_rows(submission, questions, answers=None):
        answers_by_question = defaultdict(list)
        source = answers if answers is not None else submission.answers.all()
        for answer in source:
            if answer.custom_text:
                answers_by_question[answer.question_id].append(answer.custom_text)
            elif answer.option_id:
                answers_by_question[answer.question_id].append(answer.option.text)

        return [
            {
                "number": index,
                "question": question,
                "answers": answers_by_question.get(question.id, []),
            }
            for index, question in enumerate(questions, start=1)
        ]

    @classmethod
    def build_pdf(cls, survey, submissions, cleaned_data, include_answers=False, submissions_count=None):
        _register_fonts()
        styles = _pdf_styles()
        buffer = io.BytesIO()

        page_size = landscape(A4)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
            title=survey.title,
        )

        story = []
        story.append(_paragraph(survey.title, styles["title"]))
        story.append(_paragraph("Отчёт по прохождениям анкеты", styles["subtitle"]))
        story.append(Spacer(1, 2 * mm))

        if submissions_count is None:
            submissions_count = len(submissions)

        meta_rows = [
            [
                _paragraph("Сформирован", styles["meta_label"]),
                _paragraph(datetime.now().strftime("%d.%m.%Y %H:%M"), styles["meta_value"]),
            ],
            [
                _paragraph("Записей", styles["meta_label"]),
                _paragraph(str(submissions_count), styles["meta_value"]),
            ],
            [
                _paragraph("Параметры", styles["meta_label"]),
                _paragraph(cls.filter_summary_line(cleaned_data), styles["meta_value"]),
            ],
        ]
        meta_table = Table(meta_rows, colWidths=[doc.width * 0.14, doc.width * 0.86])
        meta_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 5 * mm))

        story.append(_paragraph("Список студентов", styles["section"]))
        story.extend(cls._build_summary_table(submissions, styles, table_width=doc.width))

        if include_answers:
            questions = cls.get_ordered_questions(survey)
            story.append(Spacer(1, 5 * mm))
            story.append(_paragraph("Ответы по студентам", styles["section"]))
            for index, submission in enumerate(submissions, start=1):
                story.extend(
                    cls._build_submission_answers_block(
                        submission,
                        questions,
                        styles,
                        table_width=doc.width,
                        block_number=index,
                    )
                )

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def _build_summary_table(submissions, styles, table_width):
        header_labels = ["#", "ФИО", "MyEDU ID", "Телефон", "Логин", "Группа", "Дата", "Уч. год"]
        rows = [[_paragraph(label, styles["table_header"]) for label in header_labels]]
        for index, submission in enumerate(submissions, start=1):
            rows.append(
                [
                    _paragraph(str(index), styles["table_cell_center"]),
                    _paragraph(submission.student_fio, styles["table_cell"]),
                    _paragraph(_myedu_id(submission), styles["table_cell_center"]),
                    _paragraph(_work_phone(submission), styles["table_cell"]),
                    _paragraph(submission.student_login, styles["table_cell"]),
                    _paragraph(submission.student_group or "—", styles["table_cell"]),
                    _paragraph(submission.submitted_at.strftime("%d.%m.%Y %H:%M"), styles["table_cell"]),
                    _paragraph(submission.edu_year.title, styles["table_cell"]),
                ]
            )

        if len(rows) == 1:
            return [_paragraph("Нет данных по выбранным фильтрам.", styles["body"])]

        col_widths = _summary_col_widths(table_width)
        table = Table(rows, colWidths=col_widths, repeatRows=1)
        style = _base_table_style()
        style.add("ALIGN", (0, 0), (0, -1), "CENTER")
        style.add("ALIGN", (2, 0), (2, -1), "CENTER")
        table.setStyle(style)
        return [table]

    @staticmethod
    def _build_submission_answers_block(submission, questions, styles, table_width, block_number):
        header = (
            f"{block_number}. {submission.student_fio}"
            f" · MyEDU ID: {_myedu_id(submission)}"
            f" · {submission.submitted_at.strftime('%d.%m.%Y %H:%M')}"
        )
        elements = [
            Spacer(1, 3 * mm),
            _paragraph(header, styles["student"]),
        ]

        info_rows = [
            [
                _paragraph("Логин", styles["meta_label"]),
                _paragraph(submission.student_login, styles["meta_value"]),
                _paragraph("Телефон", styles["meta_label"]),
                _paragraph(_work_phone(submission), styles["meta_value"]),
            ],
            [
                _paragraph("Группа", styles["meta_label"]),
                _paragraph(submission.student_group or "—", styles["meta_value"]),
                _paragraph("Учебный год", styles["meta_label"]),
                _paragraph(submission.edu_year.title, styles["meta_value"]),
            ],
        ]
        info_table = Table(info_rows, colWidths=[table_width * 0.1, table_width * 0.4, table_width * 0.1, table_width * 0.4])
        info_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        elements.append(info_table)
        elements.append(Spacer(1, 2 * mm))

        if not questions:
            elements.append(_paragraph("В анкете нет вопросов.", styles["body"]))
            return elements

        answer_rows = [
            [
                _paragraph("№", styles["table_header"]),
                _paragraph("Вопрос", styles["table_header"]),
                _paragraph("Ответ", styles["table_header"]),
            ]
        ]
        for row in SurveyExportService.ordered_answer_rows(
            submission, questions, answers=submission.answers.all()
        ):
            answer_rows.append(
                [
                    _paragraph(str(row["number"]), styles["table_cell_center"]),
                    _paragraph(row["question"].text, styles["table_cell"]),
                    _answers_cell(row["answers"], styles),
                ]
            )

        answers_table = Table(answer_rows, colWidths=_answers_col_widths(table_width), repeatRows=1)
        answers_style = _base_table_style()
        answers_style.add("ALIGN", (0, 0), (0, -1), "CENTER")
        answers_table.setStyle(answers_style)
        elements.append(answers_table)
        return elements

    @classmethod
    def pdf_filename(cls, survey, include_answers=False):
        suffix = "answers" if include_answers else "list"
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        title_part = _safe_filename_part(survey.title, f"survey_{survey.id}")
        return f"{title_part}_{suffix}_{stamp}.pdf"

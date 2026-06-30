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

from student.models import Survey, SurveyAnswerItem, SurveySubmission

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
    }


def _escape_pdf_text(value):
    text = str(value or "")
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _paragraph(text, style):
    return Paragraph(_escape_pdf_text(text), style)


def _summary_col_widths(total_width):
    fractions = (0.04, 0.28, 0.24, 0.14, 0.16, 0.14)
    return [total_width * part for part in fractions]


def _safe_filename_part(value, fallback="export"):
    cleaned = re.sub(r"[^\w\s-]", "", str(value or ""), flags=re.UNICODE).strip().replace(" ", "_")
    return cleaned[:60] or fallback


class SurveyExportService:
    @staticmethod
    def completions_filter_meta(survey):
        """Учебные годы и группы для фильтра (2 запроса к данным)."""
        from stepper.models import EduYear

        subs = SurveySubmission.objects.filter(survey=survey)
        edu_year_ids = subs.values_list("edu_year_id", flat=True).distinct()
        edu_years = EduYear.objects.filter(pk__in=edu_year_ids).only("id", "title").order_by("-title")
        groups = list(
            subs.exclude(student_group="")
            .values_list("student_group", flat=True)
            .distinct()
            .order_by("student_group")
        )
        return {"edu_years": edu_years, "groups": groups}

    @staticmethod
    def filtered_submissions(survey, cleaned_data=None, *, prefetch_answers=False, for_list=False):
        qs = SurveySubmission.objects.filter(survey=survey).order_by("-submitted_at")

        if for_list:
            qs = qs.select_related("edu_year").only(
                "id",
                "student_fio",
                "student_login",
                "student_group",
                "submitted_at",
                "edu_year_id",
                "edu_year__id",
                "edu_year__title",
            )
        else:
            qs = qs.select_related("edu_year", "user")

        if prefetch_answers:
            qs = qs.prefetch_related(
                Prefetch(
                    "answers",
                    queryset=SurveyAnswerItem.objects.select_related("question", "option").order_by(
                        "question__order", "option__order"
                    ),
                )
            )

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
        return (
            SurveySubmission.objects.filter(survey_id=survey_id)
            .select_related("edu_year")
            .only(
                "id",
                "student_fio",
                "student_login",
                "student_group",
                "submitted_at",
                "edu_year_id",
                "edu_year__id",
                "edu_year__title",
            )
            .prefetch_related(
                Prefetch(
                    "answers",
                    queryset=SurveyAnswerItem.objects.select_related("question", "option").order_by(
                        "question__order", "option__order"
                    ),
                )
            )
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
        parts.append(f"Учебный год: {edu_year.title if edu_year else 'все'}")

        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        if date_from or date_to:
            left = date_from.strftime("%d.%m.%Y") if date_from else "…"
            right = date_to.strftime("%d.%m.%Y") if date_to else "…"
            parts.append(f"Период: {left} — {right}")
        else:
            parts.append("Период: весь")

        group = (cleaned_data.get("group") or "").strip()
        parts.append(f"Группа: {group or 'все'}")

        search = (cleaned_data.get("search") or "").strip()
        parts.append(f"Поиск: {search or '—'}")

        return parts

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
        story.append(_paragraph(f"Сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles["subtitle"]))
        for line in cls.filter_summary(cleaned_data):
            story.append(_paragraph(line, styles["subtitle"]))
        if submissions_count is None:
            submissions_count = len(submissions)
        story.append(_paragraph(f"Записей: {submissions_count}", styles["subtitle"]))
        story.append(Spacer(1, 6 * mm))

        story.extend(cls._build_summary_table(submissions, styles, table_width=doc.width))

        if include_answers:
            questions = list(survey.questions.order_by("order", "id"))
            story.append(Spacer(1, 4 * mm))
            story.append(_paragraph("Детализация ответов", styles["section"]))
            for submission in submissions:
                story.extend(cls._build_submission_answers(submission, questions, styles))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def _build_summary_table(submissions, styles, table_width):
        header_labels = ["#", "ФИО", "Логин", "Группа", "Дата", "Учебный год"]
        rows = [[_paragraph(label, styles["table_header"]) for label in header_labels]]
        for index, submission in enumerate(submissions, start=1):
            rows.append(
                [
                    _paragraph(str(index), styles["table_cell_center"]),
                    _paragraph(submission.student_fio, styles["table_cell"]),
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
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#A00E07")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return [table]

    @staticmethod
    def _build_submission_answers(submission, questions, styles):
        answers_by_question = defaultdict(list)
        for answer in submission.answers.all():
            answers_by_question[answer.question_id].append(answer.option.text)

        elements = [
            _paragraph(
                f"{submission.student_fio} ({submission.student_login}) — "
                f"{submission.submitted_at.strftime('%d.%m.%Y %H:%M')}",
                styles["student"],
            )
        ]

        if not questions:
            elements.append(_paragraph("В анкете нет вопросов.", styles["body"]))
            return elements

        for question in questions:
            selected = answers_by_question.get(question.id, [])
            answer_text = ", ".join(selected) if selected else "—"
            elements.append(
                _paragraph(f"{question.text}: {answer_text}", styles["body"])
            )

        elements.append(Spacer(1, 2 * mm))
        return elements

    @classmethod
    def pdf_filename(cls, survey, include_answers=False):
        suffix = "answers" if include_answers else "list"
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        title_part = _safe_filename_part(survey.title, f"survey_{survey.id}")
        return f"{title_part}_{suffix}_{stamp}.pdf"

from student.services import SurveyService


def _student_id(student, id_key):
    if isinstance(student, dict):
        return student.get(id_key)
    return getattr(student, id_key, None)


def _set_survey_flags(student, count):
    if isinstance(student, dict):
        student["survey_submission_count"] = count
        student["survey_has_submissions"] = count > 0
    else:
        student.survey_submission_count = count
        student.survey_has_submissions = count > 0


def enrich_students_with_survey_status(students, id_key="student_id"):
    """Добавляет survey_has_submissions и survey_submission_count (dict или ORM)."""
    if not students:
        return students

    myedu_ids = [_student_id(student, id_key) for student in students]
    myedu_ids = [str(item) for item in myedu_ids if item]
    edu_year = SurveyService.commission_edu_year()
    counts = SurveyService.submission_counts_by_myedu_ids(myedu_ids, edu_year=edu_year)

    for student in students:
        myedu_id = str(_student_id(student, id_key) or "")
        count = counts.get(myedu_id, 0)
        _set_survey_flags(student, count)

    return students

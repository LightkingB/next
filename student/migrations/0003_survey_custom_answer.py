from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("student", "0002_create_stsurve_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="surveyansweritem",
            name="custom_text",
            field=models.TextField(blank=True, verbose_name="Свободный ответ"),
        ),
        migrations.AlterField(
            model_name="surveyansweritem",
            name="option",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="answer_items",
                to="student.surveyoption",
                verbose_name="Вариант ответа",
            ),
        ),
        migrations.AlterField(
            model_name="surveyquestion",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("radio", "Один вариант ответа"),
                    ("checkbox", "Несколько вариантов ответа"),
                    ("text", "Свой вариант"),
                ],
                max_length=20,
                verbose_name="Тип вопроса",
            ),
        ),
    ]

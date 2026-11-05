
import json
from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations
from django.utils import timezone


def migrate_student_answers(apps, schema_editor):
    database = schema_editor.connection.alias

    StudentAnswer = apps.get_model('quiz', 'StudentAnswer')
    Question = apps.get_model('quiz', 'Question')
    QuizAttempt = apps.get_model('quiz', 'QuizAttempt')

    groups = (
        StudentAnswer.objects.using(database)
        .order_by()
        .values_list('student_id', 'quiz_id')
        .distinct()
    )

    migration_time = timezone.now()
    attempts_to_create = []

    for student_id, quiz_id in groups:

        if QuizAttempt.objects.using(database).filter(
            student_id=student_id,
            quiz_id=quiz_id
        ).exists():
            raise RuntimeError(
                f'An attempt already exists for student {student_id}, '
                f'quiz {quiz_id}. Migration stopped.'
            )

        saved_answers = list(
            StudentAnswer.objects.using(database)
            .filter(student_id=student_id, quiz_id=quiz_id)
            .select_related('question')
            .order_by('id')
        )

        questions = list(
            Question.objects.using(database)
            .filter(quiz_id=quiz_id)
            .order_by('id')
        )

        expected_ids = {q.id for q in questions}
        saved_ids = [a.question_id for a in saved_answers]
        saved_id_set = set(saved_ids)

        requires_review = (
            not expected_ids
            or len(saved_ids) != len(saved_id_set)
            or not saved_id_set.issubset(expected_ids)
        )

        total_marks = sum(q.marks for q in questions)
        marks_obtained = 0
        all_marks_available = True
        snapshots = []

        for answer in saved_answers:
            question = answer.question

            if question is None:
                requires_review = True
                continue

            if question.quiz_id != quiz_id:
                requires_review = True

            if answer.answer not in ('A', 'B', 'C', 'D'):
                requires_review = True

            if question.marks < 0:
                requires_review = True

            if answer.marks is None:
                all_marks_available = False
                requires_review = True
            else:
                marks_obtained += answer.marks

                if answer.marks < 0 or answer.marks > question.marks:
                    requires_review = True

            if answer.created_at is None:
                requires_review = True

            snapshots.append({
                'question_id': question.id,
                'question_text': question.question,
                'options': {
                    'A': question.option1,
                    'B': question.option2,
                    'C': question.option3,
                    'D': question.option4,
                },
                'correct_answer': question.answer,
                'selected_answer': answer.answer,
                'marks_available': question.marks,
                'marks_awarded': answer.marks,
                'explanation': question.explanation,
                'answer_saved_at': (
                    answer.created_at.isoformat()
                    if answer.created_at else None
                ),
            })

        if total_marks <= 0:
            requires_review = True

        if requires_review or not all_marks_available:
            status = 'legacy_review'
        elif saved_id_set == expected_ids:
            status = 'legacy_complete'
        else:
            status = 'legacy_partial'

        percentage = Decimal('0.00')

        if status in ('legacy_complete', 'legacy_partial'):
            percentage = (
                Decimal(marks_obtained) * Decimal('100')
                / Decimal(total_marks)
            ).quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            )

        attempts_to_create.append(
            QuizAttempt(
                student_id=student_id,
                quiz_id=quiz_id,
                answers=json.dumps(snapshots, ensure_ascii=False),
                total_marks=total_marks,
                marks_obtained=marks_obtained,
                percentage=percentage,
                status=status,
                started_at=None,
                submitted_at=None,
                time_taken_seconds=None,
                created_at=migration_time,
                updated_at=migration_time,
            )
        )

    QuizAttempt.objects.using(database).bulk_create(attempts_to_create)


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0002_quizattempt_quizattempt_unique_student_quiz_attempt'),
    ]

    operations = [
        migrations.RunPython(
            migrate_student_answers,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

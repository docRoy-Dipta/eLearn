import datetime
from django.shortcuts import render, redirect, get_object_or_404
from .models import Quiz, Question, StudentAnswer, QuizAttempt
from main.models import Student, Course, Faculty
from main.views import is_faculty_authorised, is_student_authorised
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, F, FloatField, Q, Prefetch
from django.db.models.functions import Cast
from django.http import JsonResponse
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP


def quiz(request, code):
    try:
        course = Course.objects.get(code=code)
        if is_faculty_authorised(request, code):
            if request.method == 'POST':
                title = request.POST.get('title')
                description = request.POST.get('description')
                start = request.POST.get('start')
                end = request.POST.get('end')
                publish_status = request.POST.get('checkbox')
                quiz = Quiz(title=title, description=description, start=start,
                            end=end, publish_status=publish_status, course=course)
                quiz.save()
                return redirect('addQuestion', code=code, quiz_id=quiz.id)
            else:
                return render(request, 'quiz/quiz.html', {'course': course, 'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id'])})

        else:
            return redirect('std_login')
    except:
        return render(request, 'error.html')


def addQuestion(request, code, quiz_id):
    try:
        course = Course.objects.get(code=code)
        if is_faculty_authorised(request, code):
            quiz = Quiz.objects.get(id=quiz_id)
            if request.method == 'POST':
                question = request.POST.get('question')
                option1 = request.POST.get('option1')
                option2 = request.POST.get('option2')
                option3 = request.POST.get('option3')
                option4 = request.POST.get('option4')
                answer = request.POST.get('answer')
                marks = request.POST.get('marks')
                explanation = request.POST.get('explanation')
                question = Question(question=question, option1=option1, option2=option2,
                                    option3=option3, option4=option4, answer=answer, quiz=quiz, marks=marks, explanation=explanation)
                question.save()
                messages.success(request, 'Question added successfully')
            else:
                return render(request, 'quiz/addQuestion.html', {'course': course, 'quiz': quiz, 'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id'])})
            if 'saveOnly' in request.POST:
                return redirect('allQuizzes', code=code)
            return render(request, 'quiz/addQuestion.html', {'course': course, 'quiz': quiz, 'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id'])})
        else:
            return redirect('std_login')
    except:
        return render(request, 'error.html')


def allQuizzes(request, code):
    if is_faculty_authorised(request, code):
        course = Course.objects.get(code=code)
        quizzes = Quiz.objects.filter(course=course)
        for quiz in quizzes:
            quiz.total_questions = Question.objects.filter(quiz=quiz).count()
            if quiz.start < datetime.datetime.now():
                quiz.started = True
            else:
                quiz.started = False
            quiz.save()
        return render(request, 'quiz/allQuizzes.html', {'course': course, 'quizzes': quizzes, 'faculty': Faculty.objects.get(faculty_id=request.session['faculty_id'])})
    else:
        return redirect('std_login')


def myQuizzes(request, code):
    if is_student_authorised(request, code):
        course = Course.objects.get(code=code)
        quizzes = Quiz.objects.filter(course=course)
        student = Student.objects.get(student_id=request.session['student_id'])

        # Determine which quizzes are active and which are previous
        active_quizzes = []
        previous_quizzes = []
        for quiz in quizzes:
            if quiz.end < timezone.now() or quiz.studentanswer_set.filter(student=student).exists():
                previous_quizzes.append(quiz)
            else:
                active_quizzes.append(quiz)

        # Add attempted flag to quizzes
        for quiz in quizzes:
            quiz.attempted = quiz.studentanswer_set.filter(
                student=student).exists()

        # Add total marks obtained, percentage, and total questions for previous quizzes
        for quiz in previous_quizzes:
            student_answers = quiz.studentanswer_set.filter(student=student)
            total_marks_obtained = sum([student_answer.question.marks if student_answer.answer ==
                                       student_answer.question.answer else 0 for student_answer in student_answers])
            quiz.total_marks_obtained = total_marks_obtained
            quiz.total_marks = sum(
                [question.marks for question in quiz.question_set.all()])
            quiz.percentage = round(
                total_marks_obtained / quiz.total_marks * 100, 2) if quiz.total_marks != 0 else 0
            quiz.total_questions = quiz.question_set.count()

        # Add total questions for active quizzes
        for quiz in active_quizzes:
            quiz.total_questions = quiz.question_set.count()

        return render(request, 'quiz/myQuizzes.html', {
            'course': course,
            'quizzes': quizzes,
            'active_quizzes': active_quizzes,
            'previous_quizzes': previous_quizzes,
            'student': student,
        })
    else:
        return redirect('std_login')


def save_quiz_attempt(attempt, posted_data=None, finalize=False):
    """
    Save the student's current answers as question snapshots.
    If finalize=True, calculate and store the final result.
    """

    with transaction.atomic():
        attempt = QuizAttempt.objects.select_for_update().get(
            pk=attempt.pk
        )

        # Never modify an already submitted or historical attempt.
        if attempt.status != 'in_progress':
            return attempt

        existing_answers = {
            str(item.get('question_id')): item
            for item in attempt.get_answers()
        }

        questions = Question.objects.filter(
            quiz=attempt.quiz
        ).order_by('id')

        snapshots = []
        total_marks = 0
        marks_obtained = 0

        for question in questions:
            question_id = str(question.id)

            previous = existing_answers.get(question_id, {})

            selected_answer = previous.get('selected_answer', '')

            if posted_data is not None and question_id in posted_data:
                submitted_answer = posted_data.get(question_id, '')

                if submitted_answer in ('A', 'B', 'C', 'D', ''):
                    selected_answer = submitted_answer

            marks_awarded = (
                question.marks
                if selected_answer == question.answer
                else 0
            )

            total_marks += question.marks
            marks_obtained += marks_awarded

            snapshots.append({
                'question_id': question.id,
                'question': question.question,
                'option1': question.option1,
                'option2': question.option2,
                'option3': question.option3,
                'option4': question.option4,
                'correct_answer': question.answer,
                'selected_answer': selected_answer,
                'marks_available': question.marks,
                'marks_awarded': marks_awarded,
                'explanation': question.explanation,
            })

        attempt.set_answers(snapshots)

        if finalize:
            submitted_at = timezone.now()

            percentage = (
                Decimal(marks_obtained) * Decimal('100')
                / Decimal(total_marks)
                if total_marks > 0
                else Decimal('0')
            )

            attempt.total_marks = total_marks
            attempt.marks_obtained = marks_obtained
            attempt.percentage = percentage.quantize(
                Decimal('0.01'),
                rounding=ROUND_HALF_UP
            )
            attempt.status = 'submitted'
            attempt.submitted_at = submitted_at

            if attempt.started_at:
                attempt.time_taken_seconds = max(
                    0,
                    int(
                        (submitted_at - attempt.started_at).total_seconds()
                    )
                )

        attempt.save()

    return attempt


def startQuiz(request, code, quiz_id):
    course = Course.objects.filter(code=code).first()

    if course is None:
        return redirect('std_login')

    if not is_student_authorised(request, code):
        return redirect('std_login')

    quiz = Quiz.objects.filter(
        id=quiz_id,
        course=course
    ).first()

    if quiz is None:
        return redirect('myQuizzes', code=code)

    student = Student.objects.filter(
        student_id=request.session.get('student_id')
    ).first()

    if student is None:
        return redirect('std_login')

    attempt = QuizAttempt.objects.filter(
        student=student,
        quiz=quiz
    ).first()

    now = timezone.now()

    # Create an attempt only after the student explicitly starts.
    if request.method == 'POST':

        if attempt is None:

            if now < quiz.start:
                messages.error(
                    request,
                    'This quiz has not started yet.'
                )
                return redirect(
                    'startQuiz',
                    code=code,
                    quiz_id=quiz.id
                )

            if now >= quiz.end:
                messages.error(
                    request,
                    'The quiz deadline has passed.'
                )
                return redirect('myQuizzes', code=code)

            attempt, created = QuizAttempt.objects.get_or_create(
                student=student,
                quiz=quiz,
                defaults={
                    'status': 'in_progress',
                    'started_at': now,
                }
            )

        if attempt.status == 'submitted':
            return redirect(
                'quizResult',
                code=code,
                quiz_id=quiz.id
            )

        if attempt.status != 'in_progress':
            return redirect('myQuizzes', code=code)

        return redirect(
            'startQuiz',
            code=code,
            quiz_id=quiz.id
        )

    # Finalize an unfinished attempt if its deadline has passed.
    if attempt and attempt.status == 'in_progress':

        if now >= quiz.end:
            attempt = save_quiz_attempt(
                attempt,
                posted_data=None,
                finalize=True
            )

    if attempt and attempt.status == 'submitted':
        return redirect(
            'quizResult',
            code=code,
            quiz_id=quiz.id
        )

    if attempt and attempt.status != 'in_progress':
        return redirect('myQuizzes', code=code)

    # Retrieve quiz questions.
    questions = list(
        Question.objects.filter(quiz=quiz)
    )

    total_questions = len(questions)

    quiz.total_marks = sum(
        question.marks for question in questions
    )

    # Restore previously autosaved answers.
    saved_answers = {}

    if attempt and attempt.status == 'in_progress':
        saved_answers = {
            str(item.get('question_id')): item.get(
                'selected_answer',
                ''
            )
            for item in attempt.get_answers()
        }

    # Attach saved answers to question objects.
    for question in questions:
        question.selected_answer = saved_answers.get(
            str(question.id),
            ''
        )

    quiz_attempt_started = bool(
        attempt and attempt.status == 'in_progress'
    )

    return render(
        request,
        'quiz/portalStdNew.html',
        {
            'course': course,
            'quiz': quiz,
            'questions': questions,
            'total_questions': total_questions,
            'student': student,
            'attempt': attempt,
            'quiz_attempt_started': quiz_attempt_started,
        }
    )




def studentAnswer(request, code, quiz_id):

    if request.method != 'POST':
        return redirect('std_login')

    course = Course.objects.filter(code=code).first()

    if course is None:
        return redirect('std_login')

    if not is_student_authorised(request, code):
        return redirect('std_login')

    quiz = Quiz.objects.filter(
        id=quiz_id,
        course=course
    ).first()

    if quiz is None:
        return redirect('myQuizzes', code=code)

    student = Student.objects.filter(
        student_id=request.session.get('student_id')
    ).first()

    if student is None:
        return redirect('std_login')

    attempt = QuizAttempt.objects.filter(
        student=student,
        quiz=quiz
    ).first()

    if attempt is None:
        return redirect('myQuizzes', code=code)

    if attempt.status == 'submitted':
        return redirect(
            'quizResult',
            code=code,
            quiz_id=quiz.id
        )

    if attempt.status != 'in_progress':
        return redirect('myQuizzes', code=code)

    action = request.POST.get('action', 'submit')

    if action not in ('autosave', 'submit'):
        return redirect('myQuizzes', code=code)

    now = timezone.now()

    # Deadline enforcement:
    # Once the deadline passes, use the last saved answers.
    if now >= quiz.end:

        attempt = save_quiz_attempt(
            attempt,
            posted_data=None,
            finalize=True
        )

        if action == 'autosave':
            return JsonResponse({
                'status': 'submitted',
                'message': 'The quiz deadline has passed.',
            })

        return redirect(
            'quizResult',
            code=code,
            quiz_id=quiz.id
        )

    if action == 'autosave':

        save_quiz_attempt(
            attempt,
            posted_data=request.POST,
            finalize=False
        )

        return JsonResponse({
            'status': 'saved',
            'message': 'Answers saved successfully.',
        })

    # Manual submission before the deadline.
    attempt = save_quiz_attempt(
        attempt,
        posted_data=request.POST,
        finalize=True
    )

    return redirect(
        'quizResult',
        code=code,
        quiz_id=quiz.id
    )



def quizResult(request, code, quiz_id):

    if not is_student_authorised(request, code):
        return redirect('std_login')

    course = Course.objects.filter(code=code).first()

    if course is None:
        return redirect('std_login')

    quiz = Quiz.objects.filter(
        id=quiz_id,
        course=course
    ).first()

    if quiz is None:
        return redirect('myQuizzes', code=code)

    student_id = request.session.get('student_id')

    student = Student.objects.filter(
        student_id=student_id
    ).first()

    if student is None:
        return redirect('std_login')

    # Retrieve the submitted attempt for this student and quiz.
    attempt = QuizAttempt.objects.filter(
        student=student,
        quiz=quiz,
        status='submitted'
    ).first()

    # Use QuizAttempt snapshots for newly submitted attempts.
    if attempt is not None and attempt.get_answers():

        answer_snapshots = attempt.get_answers()

        snapshots_by_question = {
            item.get('question_id'): item
            for item in answer_snapshots
        }

        questions = list(
            Question.objects.filter(
                quiz=quiz
            ).order_by('id')
        )

        for question in questions:

            snapshot = snapshots_by_question.get(question.id)

            if snapshot is None:
                question.student_answer = ''
                continue

            # Restore the question exactly as it appeared in the attempt.
            question.question = snapshot.get(
                'question',
                question.question
            )

            question.option1 = snapshot.get(
                'option1',
                question.option1
            )

            question.option2 = snapshot.get(
                'option2',
                question.option2
            )

            question.option3 = snapshot.get(
                'option3',
                question.option3
            )

            question.option4 = snapshot.get(
                'option4',
                question.option4
            )

            question.answer = snapshot.get(
                'correct_answer',
                question.answer
            )

            question.marks = snapshot.get(
                'marks_available',
                question.marks
            )

            question.explanation = snapshot.get(
                'explanation',
                question.explanation
            )

            question.student_answer = snapshot.get(
                'selected_answer',
                ''
            )

        # Use the final score stored in QuizAttempt.
        quiz.total_marks_obtained = attempt.marks_obtained
        quiz.total_marks = attempt.total_marks
        quiz.percentage = attempt.percentage

        quiz.total_questions = len(questions)

        # Use the actual attempt duration and submission timestamp.
        quiz.time_taken = attempt.time_taken_seconds or 0

        if attempt.submitted_at:
            quiz.submission_time = attempt.submitted_at.strftime(
                "%a, %d-%b-%y at %I:%M %p"
            )
        else:
            quiz.submission_time = None

    else:

        # Historical fallback: retain the existing StudentAnswer behavior.
        questions = list(
            Question.objects.filter(quiz=quiz)
        )

        student_answers = list(
            StudentAnswer.objects.filter(
                student=student,
                quiz=quiz,
                question__quiz=quiz
            ).select_related(
                'question'
            ).order_by('created_at')
        )

        answers_by_question = {
            answer.question_id: answer
            for answer in student_answers
        }

        quiz.total_marks_obtained = sum(
            answer.question.marks
            for answer in student_answers
            if answer.answer == answer.question.answer
        )

        quiz.total_marks = sum(
            question.marks for question in questions
        )

        if quiz.total_marks > 0:
            quiz.percentage = round(
                quiz.total_marks_obtained / quiz.total_marks * 100,
                2
            )
        else:
            quiz.percentage = 0

        for question in questions:
            answer = answers_by_question.get(question.id)

            question.student_answer = (
                answer.answer if answer else ''
            )

        if student_answers:
            latest_answer = student_answers[-1]

            elapsed_seconds = (
                latest_answer.created_at - quiz.start
            ).total_seconds()

            quiz.time_taken = round(
                max(0, elapsed_seconds), 2
            )

            quiz.submission_time = latest_answer.created_at.strftime(
                "%a, %d-%b-%y at %I:%M %p"
            )
        else:
            quiz.time_taken = 0
            quiz.submission_time = None

    return render(
        request,
        'quiz/quizResult.html',
        {
            'course': course,
            'quiz': quiz,
            'questions': questions,
            'student': student,
        }
    )




def quizSummary(request, code, quiz_id):
    if not is_faculty_authorised(request, code):
        return redirect('std_login')

    course = Course.objects.get(code=code)
    quiz = Quiz.objects.get(id=quiz_id)
    questions = list(Question.objects.filter(quiz=quiz))
    time = datetime.datetime.now()

    students = list(Student.objects.filter(course=course))
    student_ids = [student.student_id for student in students]

    # Load all new QuizAttempt records for this quiz and course.
    attempts = QuizAttempt.objects.filter(
        quiz=quiz,
        student_id__in=student_ids
    ).select_related('student')

    attempts_by_student = {
        attempt.student_id: attempt
        for attempt in attempts
    }

    # Load historical StudentAnswer records for fallback.
    legacy_answers = StudentAnswer.objects.filter(
        quiz=quiz,
        student_id__in=student_ids
    ).select_related('question').order_by('created_at')

    legacy_by_student = {}
    for answer in legacy_answers:
        legacy_by_student.setdefault(answer.student_id, []).append(answer)

    # Prepare question statistics.
    questions_by_id = {question.id: question for question in questions}

    for question in questions:
        question.A = 0
        question.B = 0
        question.C = 0
        question.D = 0
        question.total_correct_answers = 0
        question.total_wrong_answers = 0

    attempted_student_ids = set()

    for student in students:
        attempt = attempts_by_student.get(student.student_id)
        student_legacy_answers = legacy_by_student.get(
            student.student_id, []
        )

        student.attempted = False
        student.total_marks_obtained = 0
        student.submission_time = 'Did not attempt'

        # Prefer QuizAttempt data whenever it contains answer snapshots.
        snapshots = attempt.get_answers() if attempt else []

        if attempt:
            student.attempted = True
            attempted_student_ids.add(student.student_id)

            if attempt.status == 'in_progress':
                student.submission_time = 'In progress'
            else:
                student.total_marks_obtained = (
                    attempt.marks_obtained or 0
                )

                if attempt.submitted_at:
                    student.submission_time = (
                        attempt.submitted_at.strftime(
                            "%a, %d-%b-%y at %I:%M %p"
                        )
                    )

        if snapshots:
            for snapshot in snapshots:
                question_id = snapshot.get('question_id')
                question = questions_by_id.get(question_id)

                if question is None:
                    continue

                selected = snapshot.get('selected_answer')
                correct = snapshot.get('correct_answer')

                if selected not in ('A', 'B', 'C', 'D'):
                    continue

                setattr(
                    question,
                    selected,
                    getattr(question, selected) + 1
                )

                if selected == correct:
                    question.total_correct_answers += 1
                else:
                    question.total_wrong_answers += 1

        elif student_legacy_answers:
            # Historical records remain supported without duplication.
            student.attempted = True
            attempted_student_ids.add(student.student_id)

            total_marks_obtained = 0

            for answer in student_legacy_answers:
                question = questions_by_id.get(answer.question_id)

                if question is None:
                    continue

                selected = answer.answer

                if selected in ('A', 'B', 'C', 'D'):
                    setattr(
                        question,
                        selected,
                        getattr(question, selected) + 1
                    )

                    if selected == question.answer:
                        question.total_correct_answers += 1
                    else:
                        question.total_wrong_answers += 1

                if selected == answer.question.answer:
                    total_marks_obtained += answer.question.marks

            student.total_marks_obtained = total_marks_obtained

            latest_answer = student_legacy_answers[-1]
            student.submission_time = (
                latest_answer.created_at.strftime(
                    "%a, %d-%b-%y at %I:%M %p"
                )
            )

    if request.method == 'POST':
        quiz.publish_status = True
        quiz.save()
        return redirect('quizSummary', code=code, quiz_id=quiz.id)

    total_students = len(students)
    attempted_students = len(attempted_student_ids)

    context = {
        'course': course,
        'quiz': quiz,
        'questions': questions,
        'time': time,
        'total_students': total_students,
        'attempted_students': attempted_students,
        'students': students,
        'faculty': Faculty.objects.get(
            faculty_id=request.session['faculty_id']
        ),
    }

    return render(
        request,
        'quiz/quizSummaryFaculty.html',
        context
    )

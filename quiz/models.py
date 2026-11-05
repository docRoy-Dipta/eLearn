from venv import create
from django.db import models
from main.models import Student, Course
import json


# Create your models here.


class Quiz(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    publish_status = models.BooleanField(default=False, null=True, blank=True)
    started = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def duration(self):
        return self.end - self.start
        
    def duration_in_seconds(self):
        return (self.end - self.start).total_seconds()

    def total_questions(self):
        return Question.objects.filter(quiz=self).count()

    def question_sl(self):
        return Question.objects.filter(quiz=self).count() + 1

    def total_marks(self):
        return Question.objects.filter(quiz=self).aggregate(total_marks=models.Sum('marks'))['total_marks']

    def starts(self):
        return self.start.strftime("%a, %d-%b-%y at %I:%M %p")

    def ends(self):
        return self.end.strftime("%a, %d-%b-%y at %I:%M %p")

    def attempted_students(self):
        return Student.objects.filter(studentanswer__quiz=self).distinct().count()


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.TextField()
    marks = models.IntegerField(default=0, null=False)
    option1 = models.TextField(null=False, blank=False, default='',)
    option2 = models.TextField(null=False, blank=False, default='')
    option3 = models.TextField(null=False, blank=False, default='')
    option4 = models.TextField(null=False, blank=False, default='')
    answer = models.CharField(max_length=1, choices=(
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')), default='A')
    explanation = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.question

    def get_answer(self):
        case = {
            'A': self.option1,
            'B': self.option2,
            'C': self.option3,
            'D': self.option4,
        }
        return case[self.answer]

    def total_correct_answers(self):
        return StudentAnswer.objects.filter(question=self, answer=self.answer).count()

    def total_wrong_answers(self):
        return StudentAnswer.objects.filter(question=self).exclude(answer=self.answer).count()


class StudentAnswer(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.CharField(max_length=1, choices=(
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')), default='', null=True, blank=True)
    marks = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.student.name + ' ' + self.quiz.title + ' ' + self.question.question

    class Meta:
        unique_together = ('student', 'quiz', 'question')

class QuizAttempt(models.Model):

    STATUS_CHOICES = (
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('legacy_complete', 'Legacy Complete'),
        ('legacy_partial', 'Legacy Partial'),
        ('legacy_review', 'Requires Review'),
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='quiz_attempts'
    )

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Serialized JSON containing answers and question snapshots.
    answers = models.TextField(default='[]')

    total_marks = models.IntegerField(default=0)
    marks_obtained = models.IntegerField(default=0)

    percentage = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default='submitted'
    )

    # Historical attempts may not have a reliable start time.
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    time_taken_seconds = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Quiz Attempt'
        verbose_name_plural = 'Quiz Attempts'
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'quiz'],
                name='unique_student_quiz_attempt'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.name} - {self.quiz.title}'

    def get_answers(self):
        try:
            return json.loads(self.answers or '[]')
        except (TypeError, ValueError):
            return []

    def set_answers(self, answers):
        self.answers = json.dumps(
            answers,
            ensure_ascii=False
        )

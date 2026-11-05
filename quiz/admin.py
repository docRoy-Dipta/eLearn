
from django.contrib import admin
from .models import Quiz, Question, StudentAnswer, QuizAttempt

admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(StudentAnswer)
admin.site.register(QuizAttempt)

from django.conf.urls import include, url
from . import views

from .views import EnrollUserView
from .views import DeleteCourseView

urlpatterns = [
    url(r'^student_grade/', views.student_grade, name='student_grade'),
    url(r'^create_user/$', views.create_user, name='create_user'),

    url(r'^courseenroll/$', EnrollUserView.as_view()),
    url(r'^deletecourse/$', DeleteCourseView.as_view()),
]

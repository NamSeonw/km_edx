from django.conf.urls import include, url
from . import views
from .views import *

urlpatterns = [
    url(r'^updatecourse/$', UpdateCourseView.as_view()),
    url(r'^createcourse/$', CreateCourseView.as_view()),
    url(r'^reruncourse/$', RerunCourseView.as_view()),
    url(r'^manageuser/$', ManageUserView.as_view()),
]

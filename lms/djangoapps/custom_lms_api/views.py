# -*- coding: utf-8 -*-
import logging
from common.djangoapps.util.json_request import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import Http404
from lms.djangoapps.grades.api import CourseGradeFactory
from lms.djangoapps.courseware.courses import (
    get_course_with_access,
)
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from openedx.core.lib.api.view_utils import view_auth_classes, DeveloperErrorViewMixin
from opaque_keys.edx.keys import CourseKey
from django.contrib.auth.models import User
import subprocess
from common.djangoapps.student import auth
from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole, LibraryUserRole
from common.djangoapps.student.auth import (
    STUDIO_EDIT_ROLES,
    STUDIO_VIEW_USERS,
    get_user_permissions,
    has_studio_read_access,
    has_studio_write_access
)
from common.djangoapps.student.models import CourseEnrollment
from django.core.exceptions import ObjectDoesNotExist

from .serializers import DeleteCourseSerializer
from .serializers import EnrollUserSerializer

from urllib.parse import urlparse

import time

log = logging.getLogger(__name__)


@csrf_exempt
def student_grade(request):
    course_id = request.POST['course_id']
    student_id = request.POST['student_id']
    try:
        progress = request.POST['progress']
    except:
        progress = False

    course_key = CourseKey.from_string(course_id)

    try:
        student = User.objects.get(id=student_id)
    except User.DoesNotExist:
        raise Http404

    course = get_course_with_access(student, 'load', course_key, check_if_enrolled=True)

    # NOTE: To make sure impersonation by instructor works, use
    # student instead of request.user in the rest of the function.

    course_grade = CourseGradeFactory().read(student, course)

    data_dict = dict()

    if progress:
        return JsonResponse(course_grade.summary)

    data_dict['percent'] = course_grade.percent
    data_dict['letter_grade'] = course_grade.letter_grade
    data_dict['pass'] = course_grade.passed

    return JsonResponse(data_dict)


@csrf_exempt
def create_user(request):

    username = request.POST.get('username')
    email = request.POST.get('email')
    password = request.POST.get('password')

    if username or email:

        if password and password != None:
            password = '--password {password}'.format(password=password)

        host = request.META.get('HTTP_HOST')

        setting = ''

        if str(host).find("18000") != -1:
            setting = 'devstack_docker'
        else:
            setting = 'production'

        # os.system()
        commands = "/edx/app/edxapp/edx-platform/manage.py lms --settings={setting} manage_user {username} {email} {password}".format(
            username=username, email=email, password=password, setting=setting)

        res = subprocess.call(commands.split())

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


@view_auth_classes(is_authenticated=False)
class EnrollUserView(DeveloperErrorViewMixin, CreateAPIView):

    serializer_class = EnrollUserSerializer

    def create(self, request):

        email_string = request.POST.get('email')
        course_key_string = request.POST.get('course_key')
        action = request.POST.get('action')

        user_data = User.objects.get(username='staff')

        log.info("#############")
        log.info(email_string)
        log.info("#############")
        log.info(course_key_string)
        try:
            user = User.objects.get(email=email_string)
            course_key = CourseKey.from_string(course_key_string)

            requester_perms = 15
            is_library = False
            role_hierarchy = (CourseInstructorRole, CourseStaffRole)
            #new_role = u'staff'
            new_role = u'instructor'
            old_roles = set()
            role_added = False

            for role_type in role_hierarchy:
                role = role_type(course_key)
                if role_type.ROLE == new_role:
                    if (requester_perms & STUDIO_EDIT_ROLES) or (user.id == user_data and old_roles):
                        auth.add_users(user_data, role, user)
                        role_added = True
                elif role.has_user(user, check_user_activation=False):
                    pass
            if new_role and not role_added:
                pass
            for role in old_roles:
                pass
            if new_role and not is_library:
                if action == 'enroll':
                    CourseEnrollment.enroll(user, course_key)
                else:
                    CourseEnrollment.unenroll(user, course_key)

        except ObjectDoesNotExist:
            log.info("return false")
            return Response({"result": "false"})
        log.info("return true")
        return Response({"result": "true"})


@view_auth_classes(is_authenticated=False)
class DeleteCourseView(DeveloperErrorViewMixin, CreateAPIView):
    serializer_class = DeleteCourseSerializer

    def create(self, request):
        COURSE_ID = request.POST.get('id')

        setting = ''

        host = request.META.get('HTTP_HOST')

        try:
            if str(host).find("18000") != -1:
                setting = 'devstack_docker'
            else:
                setting = 'production'

            data = "/edx/app/edxapp/edx-platform/manage.py cms --setting=" + setting + " delete_course " + COURSE_ID + " < /edx/app/edxapp/edx-platform/tt"

            subprocess.call(data, shell=True)
            return Response({"result": "ok"})
        except:
            return Response({"result": "fail"})

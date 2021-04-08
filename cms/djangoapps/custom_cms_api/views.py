# -*- coding: utf-8 -*-

from .serializers import UpdateCourseSerializer
from .serializers import CreateCourseSerializer
from .serializers import RerunCourseSerializer
from .serializers import ManageUserSerializer

from openedx.core.lib.api.view_utils import view_auth_classes, DeveloperErrorViewMixin
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore
from django.contrib.auth.models import User
from cms.djangoapps.contentstore.views.course import get_course_and_check_access
from openedx.core.djangoapps.models.course_details import CourseDetails
from cms.djangoapps.models.settings.course_metadata import CourseMetadata
from cms.djangoapps.contentstore.utils import reverse_course_url, reverse_library_url, add_instructor
from common.djangoapps.course_action_state.models import CourseRerunState
from xmodule.modulestore import EdxJSONEncoder
import json
from cms.djangoapps.contentstore.tasks import rerun_course
from cms.djangoapps.contentstore.views.course import create_new_course_in_store

from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole, LibraryUserRole
from common.djangoapps.student.auth import STUDIO_EDIT_ROLES, STUDIO_VIEW_USERS, get_user_permissions
from common.djangoapps.student import auth
from common.djangoapps.student.models import CourseEnrollment
from cms.djangoapps.models.settings.encoder import CourseSettingsEncoder

import logging
from datetime import datetime, timedelta, tzinfo
log = logging.getLogger(__name__)


@view_auth_classes(is_authenticated=False)
class UpdateCourseView(DeveloperErrorViewMixin, CreateAPIView):

    serializer_class = UpdateCourseSerializer

    def create(self, request):

        display_name_string = request.POST.get('display_name')
        course_key_string = request.POST.get('id')
        start_date_string = request.POST.get('start_date')
        end_date_string = request.POST.get('end_date')
        enrollment_start_string = request.POST.get('enrollment_start')
        enrollment_end_string = request.POST.get('enrollment_end')
        image_dir_string = request.POST.get('image_dir')
        short_description_string = request.POST.get('short_description')
        #description_string = request.POST.get('description')
        overview_string = request.POST.get('overview')

        # ------ TIME CONVERTER ------ #
        log.info("******* TIME CHECK *******")
        log.info(start_date_string)
        log.info(end_date_string)
        log.info(enrollment_start_string)
        log.info(enrollment_end_string)
        log.info("******* TIME CHECK *******")

        start_date = datetime(
            int(start_date_string[0:4]),
            int(start_date_string[5:7]),
            int(start_date_string[8:10]),
            int(start_date_string[11:13]),
            int(start_date_string[14:16])
        )

        end_date = datetime(
            int(end_date_string[0:4]),
            int(end_date_string[5:7]),
            int(end_date_string[8:10]),
            int(end_date_string[11:13]),
            int(end_date_string[14:16])
        )

        enrollment_start = datetime(
            int(enrollment_start_string[0:4]),
            int(enrollment_start_string[5:7]),
            int(enrollment_start_string[8:10]),
            int(enrollment_start_string[11:13]),
            int(enrollment_start_string[14:16])
        )

        enrollment_end = datetime(
            int(enrollment_end_string[0:4]),
            int(enrollment_end_string[5:7]),
            int(enrollment_end_string[8:10]),
            int(enrollment_end_string[11:13]),
            int(enrollment_end_string[14:16])
        )

        sync_time = timedelta(hours=9)

        start_date = start_date - sync_time
        end_date = end_date - sync_time
        enrollment_start = enrollment_start - sync_time
        enrollment_end = enrollment_end - sync_time

        start_date = str(start_date)
        end_date = str(end_date)
        enrollment_start = str(enrollment_start)
        enrollment_end = str(enrollment_end)

        start_date_string = "{}-{}-{}T{}:{}:{}Z".format(start_date[0:4], start_date[5:7], start_date[8:10], start_date[11:13], start_date[14:16], '00')
        end_date_string = "{}-{}-{}T{}:{}:{}Z".format(end_date[0:4], end_date[5:7], end_date[8:10], end_date[11:13], end_date[14:16], '00')
        enrollment_start_string = "{}-{}-{}T{}:{}:{}Z".format(enrollment_start[0:4], enrollment_start[5:7], enrollment_start[8:10], enrollment_start[11:13], enrollment_start[14:16], '00')
        enrollment_end_string = "{}-{}-{}T{}:{}:{}Z".format(enrollment_end[0:4], enrollment_end[5:7], enrollment_end[8:10], enrollment_end[11:13], enrollment_end[14:16], '00')

        log.info("******* TIME CHECK (CONVERTER) *******")
        log.info(start_date_string)
        log.info(end_date_string)
        log.info(enrollment_start_string)
        log.info(enrollment_end_string)
        log.info("******* TIME CHECK (CONVERTER) ********")
        # ------ TIME CONVERTER ------ #

        update_data = {
            u'org': u'',
            u'course_id': u'',
            u'run': u'',

            u'start_date': start_date_string,
            u'end_date': end_date_string,

            u'enrollment_start': enrollment_start_string,
            u'enrollment_end': enrollment_end_string,

            u'course_image_name': u'',
            u'course_image_asset_path': u'',

            u'banner_image_name': u'',
            u'banner_image_asset_path': u'',

            u'video_thumbnail_image_name': u'',
            u'video_thumbnail_image_asset_path': u'',

            u'language': u'en',

            u'short_description': short_description_string,
            u'description': u'',

            u'overview': overview_string,

            u'entrance_exam_minimum_score_pct': u'50',
            u'entrance_exam_id': u'',
            u'entrance_exam_enabled': u'',

            u'duration': u'',
            u'subtitle': u'',
            u'title': u'testtest',

            u'pre_requisite_courses': [],
            u'instructor_info': {u'instructors': []},
            u'learning_info': [],

            u'effort': None,
            u'license': None,
            u'intro_video': None,
            u'self_paced': False,
            u'syllabus': None
        }

        # validate check #
        from xmodule.fields import Date
        date = Date()
        converted_start_date = date.from_json(update_data['start_date'])
        converted_end_date = date.from_json(update_data['end_date'])
        converted_enrollment_start = date.from_json(update_data['enrollment_start'])
        converted_enrollment_end = date.from_json(update_data['enrollment_end'])
        if(converted_enrollment_start > converted_enrollment_end):
            return Response({"result": "fail - 1"})
        if (converted_start_date > converted_end_date):
            return Response({"result": "fail - 2"})
        # validate check #

        course_key = CourseKey.from_string(course_key_string)
        with modulestore().bulk_operations(course_key):
            user_data = User.objects.get(username='staff')
            course_module = get_course_and_check_access(course_key, user_data)
            CourseDetails.update_from_json(course_key, update_data, user_data)

        descriptor = course_module
        key_values = {u'display_name': display_name_string}
        user = user_data
        CourseMetadata.update_from_dict(key_values, descriptor, user)
        #update display_name

        log.info("******** Update ok")
        return Response({"result": "ok"})


@view_auth_classes(is_authenticated=False)
class CreateCourseView(DeveloperErrorViewMixin, CreateAPIView):

    serializer_class = CreateCourseSerializer

    def create(self, request):

        log.info("#########################")
        log.info(request)

        ###### REQUEST POST DATA #####
        display_name_string = request.POST.get('display_name')
        org_string = request.POST.get('org')
        number_string = request.POST.get('number')
        run_string = request.POST.get('run')

        has_org_string = request.POST.get('has_org')
        has_number_string = request.POST.get('has_number')
        has_run_string = request.POST.get('has_run')
        ###### REQUEST POST DATA #####

        if has_org_string == None:
            has_org_string = ''

        if has_number_string == None:
            has_number_string = ''

        if has_run_string == None:
            has_run_string = ''

        #new
        display_name = display_name_string
        org = org_string
        course = number_string
        number = number_string
        run = run_string

        #old
        has_org = has_org_string
        has_course = has_number_string
        has_number = has_number_string
        has_run = has_run_string

        #create staff
        user_data = User.objects.get(username='staff')

        #create new key
        course_key_string = "course-v1:" + org + "+" + number + "+" + run
        course_key = CourseKey.from_string(course_key_string)

        #create old key
        has_course_key_string = "course-v1:" + has_org + "+" + has_number + "+" + has_run
        try:
            has_course_key = CourseKey.from_string(has_course_key_string)
        except BaseException:
            has_course_key = None

        log.info("############# -> course_key_string")
        log.info(course_key_string)
        log.info("#############")

        log.info("############# -> has_course_key_string")
        log.info(has_course_key_string)
        log.info("#############")

        #DB check (new)
        course_module = get_course_and_check_access(course_key, user_data)

        # DB check (old)
        try:
            has_course_module = get_course_and_check_access(has_course_key, user_data)
        except BaseException:
            has_course_module = None

        if(course_module != None):
            ### Course PASS OK ###
            log.info("############# -> 1")
            return Response({"result": "ok"})

        else:
            if (has_course_module != None):
                log.info("############# -> 2")
                # copy
                src_course_key = CourseKey.from_string(has_course_key_string)
                des_course_key = CourseKey.from_string(course_key_string)

                display_name = display_name_string
                org = org_string
                course = number_string
                number = number_string
                run = run_string

                test = datetime(2030, 1, 1, 00, 00, 00)

                fields = {'start': test}

                fields['display_name'] = display_name
                wiki_slug = u"{0}.{1}.{2}".format(org, course, run)
                definition_data = {'wiki_slug': wiki_slug}
                fields.update(definition_data)

                store = 'split'

                add_instructor(des_course_key, user_data, user_data)
                CourseRerunState.objects.initiated(src_course_key, des_course_key, user_data, fields['display_name'])
                fields['advertised_start'] = None
                json_fields = json.dumps(fields, cls=EdxJSONEncoder)

                rerun_course(str(src_course_key), str(des_course_key), user_data.id, json_fields) #bugfix
                ### Course COPY OK ###
                return Response({"result": "ok"})
            else:
                #non copy
                log.info("############# -> 3")
                test = datetime(2030, 1, 1, 00, 00, 00)
                fields = {'start': test}
                fields['display_name'] = display_name
                wiki_slug = u"{0}.{1}.{2}".format(org, course, run)
                definition_data = {'wiki_slug': wiki_slug}
                fields.update(definition_data)
                store = 'split'
                create_new_course_in_store(store, user_data, org, number, run, fields)
                ### Course Created OK ###
                return Response({"result": "ok"})


@view_auth_classes(is_authenticated=False)
class RerunCourseView(DeveloperErrorViewMixin, CreateAPIView):

    serializer_class = RerunCourseSerializer

    def create(self, request):
        log.info("############### -> RerunCourseView")

        ###### REQUEST POST DATA #####
        src_course_key_string = request.POST.get('id')
        display_name_string = request.POST.get('display_name')
        org_string = request.POST.get('org')
        number_string = request.POST.get('number')
        run_string = request.POST.get('run')
        ###### REQUEST POST DATA #####
        user_data = User.objects.get(username='staff')
        des_course_key_string = "course-v1:" + org_string + "+" + number_string + "+" + run_string

        src_course_key = CourseKey.from_string(src_course_key_string)
        des_course_key = CourseKey.from_string(des_course_key_string)

        display_name = display_name_string
        org = org_string
        course = number_string
        run = run_string

        test = datetime(2030, 1, 1, 00, 00, 00)

        fields = {'start': test}

        fields['display_name'] = display_name
        wiki_slug = u"{0}.{1}.{2}".format(org, course, run)
        definition_data = {'wiki_slug': wiki_slug}
        fields.update(definition_data)

        store = 'split'

        add_instructor(des_course_key, user_data, user_data)
        CourseRerunState.objects.initiated(src_course_key, des_course_key, user_data, fields['display_name'])
        fields['advertised_start'] = None
        json_fields = json.dumps(fields, cls=EdxJSONEncoder)
        rerun_course.delay(str(src_course_key), str(des_course_key), user_data.id, json_fields)

        return Response({"result": "ok"})


@view_auth_classes(is_authenticated=False)
class ManageUserView(DeveloperErrorViewMixin, CreateAPIView):

    serializer_class = ManageUserSerializer

    def create(self, request):

        email_string = request.POST.get('email')
        course_key_string = request.POST.get('id')
        course_key = CourseKey.from_string(course_key_string)

        user = User.objects.get(email=email_string)
        user_data = User.objects.get(username='staff')

        requester_perms = 15
        is_library = False
        role_hierarchy = (CourseInstructorRole, CourseStaffRole)

        old_roles = set()
        role_added = False
        for role_type in role_hierarchy:
            role = role_type(course_key)
            if user.is_staff == True:
                if role_type.ROLE == u'instructor':
                    if (requester_perms & STUDIO_EDIT_ROLES) or (user.id == user_data and old_roles):
                        auth.add_users(user_data, role, user)
                        role_added = True
                elif role.has_user(user, check_user_activation=False):
                    pass
            else:
                if role_type.ROLE == u'staff':
                    if (requester_perms & STUDIO_EDIT_ROLES) or (user.id == user_data and old_roles):
                        auth.add_users(user_data, role, user)
                        role_added = True
                elif role.has_user(user, check_user_activation=False):
                    pass

        if u'instructor' and not role_added:
            pass
        for role in old_roles:
            pass
        if u'instructor' and not is_library:
            CourseEnrollment.enroll(user, course_key)
        return Response({"result": "true"})


def user_with_role(user, role):
    """ Build user representation with attached role """
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': role
    }

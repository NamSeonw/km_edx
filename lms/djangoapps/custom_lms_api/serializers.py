from rest_framework import serializers


class DeleteCourseSerializer(serializers.Serializer):

    id = serializers.CharField()


class CourseEnrollSerializer(serializers.Serializer):

    id = serializers.CharField()
    email = serializers.CharField()
    action = serializers.CharField()


class EnrollUserSerializer(serializers.Serializer):

    email = serializers.CharField()
    course_key = serializers.CharField()

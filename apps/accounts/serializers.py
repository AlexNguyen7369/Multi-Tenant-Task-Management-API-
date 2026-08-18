from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        # TODO: hash the password via User.objects.create_user(...) instead
        # of letting the default ModelSerializer.create save it in plain text.
        raise NotImplementedError

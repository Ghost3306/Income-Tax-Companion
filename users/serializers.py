from rest_framework import serializers
from .models import UserAccount

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccount
        fields = ['username', 'password']

    def create(self, validated_data):
        user = UserAccount(
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField()


class VerifyAccountSerializer(serializers.Serializer):
    token = serializers.UUIDField()

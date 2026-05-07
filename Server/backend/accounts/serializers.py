from rest_framework import serializers
from .models import Staff


class StaffListSerializer(serializers.ModelSerializer):
    """Serializer for listing staff members"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Staff
        fields = ['staffId', 'staffName', 'email', 'role', 'role_display', 'phone', 'is_active', 'createdAt']
        read_only_fields = ['staffId', 'createdAt']


class StaffDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed staff view"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Staff
        fields = ['staffId', 'staffName', 'email', 'role', 'role_display', 'phone', 'is_active', 'createdAt', 'updatedAt']
        read_only_fields = ['staffId', 'createdAt', 'updatedAt']


class StaffCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new staff"""
    pin = serializers.CharField(write_only=True, min_length=6, max_length=6, help_text='6-digit PIN')
    confirm_pin = serializers.CharField(write_only=True, min_length=6, max_length=6)

    class Meta:
        model = Staff
        fields = ['staffName', 'email', 'pin', 'confirm_pin', 'role', 'phone']
        extra_kwargs = {
            'staffName': {'required': True},
            'email': {'required': True},
            'role': {'required': True}
        }

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('PIN must contain only digits.')
        return value

    def validate(self, data):
        if data.get('pin') != data.get('confirm_pin'):
            raise serializers.ValidationError({'confirm_pin': 'PINs do not match.'})

        request = self.context.get('request')
        if not (request and getattr(request.user, 'is_authenticated', False) and getattr(request.user, 'role', None) == Staff.Roles.ADMIN):
            if data.get('role') != Staff.Roles.CLERK:
                raise serializers.ValidationError({'role': 'Only clerk accounts may be created without admin authentication.'})
        return data

    def create(self, validated_data):
        pin = validated_data.pop('pin')
        validated_data.pop('confirm_pin')
        return Staff.objects.create_user(password=pin, **validated_data)


class StaffSetupSerializer(StaffCreateSerializer):
    """Serializer for first administrator setup"""

    class Meta(StaffCreateSerializer.Meta):
        fields = ['staffName', 'email', 'pin', 'confirm_pin', 'phone']

    def create(self, validated_data):
        pin = validated_data.pop('pin')
        validated_data.pop('confirm_pin')
        return Staff.objects.create_user(
            password=pin,
            role=Staff.Roles.ADMIN,
            is_staff=True,
            is_superuser=True,
            **validated_data
        )


class StaffUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating staff"""

    class Meta:
        model = Staff
        fields = ['staffName', 'email', 'role', 'phone', 'is_active']

    def validate_email(self, value):
        instance = self.instance
        if Staff.objects.filter(email=value).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError('This email is already in use.')
        return value

    def validate(self, data):
        request = self.context.get('request')
        if self.instance and 'role' in data:
            if not request or not getattr(request.user, 'role', None) == Staff.Roles.ADMIN:
                raise serializers.ValidationError('Only admins may change roles.')
        return data

    def update(self, instance, validated_data):
        if validated_data.get('is_active') and not instance.is_active:
            validated_data['failedPinAttempts'] = 0
        return super().update(instance, validated_data)


class StaffLoginSerializer(serializers.Serializer):
    """Serializer for login endpoint"""
    email = serializers.EmailField(required=True)
    pin = serializers.CharField(write_only=True, min_length=6, max_length=6)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('PIN must contain only digits.')
        return value


class ChangePinSerializer(serializers.Serializer):
    """Serializer for changing PIN"""

    old_pin = serializers.CharField(write_only=True, required=False, allow_blank=True)
    new_pin = serializers.CharField(write_only=True, min_length=6, max_length=6)
    confirm_new_pin = serializers.CharField(write_only=True, min_length=6, max_length=6)

    def validate(self, data):
        old_pin = data.get('old_pin', '')
        new_pin = data.get('new_pin')
        confirm_new_pin = data.get('confirm_new_pin')

        # ✅ PIN format check (only if provided)
        if old_pin and not old_pin.isdigit():
            raise serializers.ValidationError({'old_pin': 'PIN must contain only digits.'})

        if not new_pin.isdigit():
            raise serializers.ValidationError({'new_pin': 'PIN must contain only digits.'})

        # ❌ mismatch
        if new_pin != confirm_new_pin:
            raise serializers.ValidationError({'confirm_new_pin': 'New PINs do not match.'})

        # ❌ same PIN
        if old_pin and old_pin == new_pin:
            raise serializers.ValidationError('New PIN must be different from old PIN.')

        return data

class StaffResponseSerializer(serializers.ModelSerializer):
    """Serializer for login response"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Staff
        fields = ['staffId', 'staffName', 'email', 'role', 'role_display', 'phone']
        read_only_fields = ['staffId', 'staffName', 'email', 'role', 'role_display', 'phone']

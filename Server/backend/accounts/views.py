from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Staff
from .serializers import (
    StaffListSerializer, StaffDetailSerializer, StaffCreateSerializer,
    StaffUpdateSerializer, StaffLoginSerializer, ChangePinSerializer,
    StaffSetupSerializer, StaffResponseSerializer
)
from .throttles import LoginRateThrottle
from .permissions import IsAdmin, IsAdminOrSelf, CanChangePin

DUMMY_PASSWORD_HASH = make_password('dummy-password-for-timing')


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrSelf]

    # ------------------------------------------------------------------
    # SERIALIZERS
    # ------------------------------------------------------------------
    def get_serializer_class(self):
        if self.action == 'create':
            return StaffCreateSerializer
        elif self.action == 'setup':
            return StaffSetupSerializer
        elif self.action in ['update', 'partial_update']:
            return StaffUpdateSerializer
        elif self.action == 'retrieve':
            return StaffDetailSerializer
        elif self.action == 'login':
            return StaffLoginSerializer
        elif self.action == 'change_pin':
            return ChangePinSerializer
        return StaffListSerializer

    # ------------------------------------------------------------------
    # PERMISSIONS
    # ------------------------------------------------------------------
    def get_permissions(self):
        if self.action == 'login':
            permission_classes = [AllowAny]

        elif self.action == 'me':
            permission_classes = [IsAuthenticated]

        elif self.action == 'setup':
            permission_classes = [AllowAny]

        elif self.action == 'create':
            permission_classes = [AllowAny]

        elif self.action in ['list', 'by_role', 'inactive']:
            permission_classes = [IsAuthenticated, IsAdmin]

        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsAdmin]

        elif self.action == 'change_pin':
            permission_classes = [IsAuthenticated, CanChangePin]

        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated, IsAdminOrSelf]

        else:
            permission_classes = [IsAuthenticated, IsAdmin]

        return [permission() for permission in permission_classes]

    # ------------------------------------------------------------------
    # ADMIN SETUP
    # ------------------------------------------------------------------
    @action(
        detail=False,
        methods=['get', 'post'],
        url_path='setup',
        permission_classes=[AllowAny]
    )
    def setup(self, request):
        if request.method == 'GET':
            admin_exists = Staff.objects.filter(role=Staff.Roles.ADMIN).exists()
            return Response({'admin_exists': admin_exists})

        # POST - create first administrator account
        if Staff.objects.filter(role=Staff.Roles.ADMIN).exists():
            return Response(
                {'error': 'Administrator account already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin = serializer.save()

        refresh = RefreshToken.for_user(admin)
        user_data = StaffResponseSerializer(admin).data
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_data
        }, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # IMPORTANT: FIX 404 vs 403 ISSUE
    # ------------------------------------------------------------------
    def get_queryset(self):
        return Staff.objects.all()

    # ------------------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------------------
    @action(
        detail=False,
        methods=['post'],
        url_path='login',
        permission_classes=[AllowAny],
        throttle_classes=[LoginRateThrottle]
    )
    def login(self, request):
        serializer = StaffLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        pin = serializer.validated_data['pin']

        try:
            staff = Staff.objects.get(email=email)
        except Staff.DoesNotExist:
            check_password(pin, DUMMY_PASSWORD_HASH)
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ❌ inactive
        if not staff.is_active:
            return Response(
                {'error': 'Account inactive'},
                status=status.HTTP_403_FORBIDDEN
            )

        # ❌ wrong PIN
        if not staff.check_password(pin):
            staff.failedPinAttempts += 1

            if staff.failedPinAttempts >= 5:
                staff.is_active = False

            staff.save(update_fields=['failedPinAttempts', 'is_active'])

            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ✅ success
        staff.failedPinAttempts = 0
        staff.lastLoginAt = timezone.now()
        staff.save(update_fields=['failedPinAttempts', 'lastLoginAt'])

        refresh = RefreshToken.for_user(staff)
        user_data = StaffResponseSerializer(staff).data

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_data
        }, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # ME
    # ------------------------------------------------------------------
    @action(
        detail=False,
        methods=['get'],
        url_path='me',
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = StaffDetailSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # CHANGE PIN
    # ------------------------------------------------------------------
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, CanChangePin]
    )
    def change_pin(self, request, pk=None):
        staff = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_pin = serializer.validated_data['old_pin']
        new_pin = serializer.validated_data['new_pin']

        is_admin_reset = request.user.role == Staff.Roles.ADMIN

        if not is_admin_reset and not staff.check_password(old_pin):
            return Response(
                {'error': 'Incorrect current PIN'},
                status=status.HTTP_400_BAD_REQUEST
            )

        staff.set_password(new_pin)
        staff.failedPinAttempts = 0
        staff.is_active = True

        staff.save(update_fields=['password', 'failedPinAttempts', 'is_active'])

        return Response({'message': 'PIN updated successfully'})

    # ------------------------------------------------------------------
    # FILTER BY ROLE
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def by_role(self, request):
        role = request.query_params.get('role')
        valid_roles = [r.value for r in Staff.Roles]

        if not role:
            return Response(
                {'error': 'role parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if role not in valid_roles:
            return Response(
                {'error': f'Invalid role. Choices: {valid_roles}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = Staff.objects.filter(role=role)
        serializer = StaffListSerializer(queryset, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # INACTIVE STAFF
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def inactive(self, request):
        queryset = Staff.objects.filter(is_active=False)
        serializer = StaffListSerializer(queryset, many=True)
        return Response(serializer.data)
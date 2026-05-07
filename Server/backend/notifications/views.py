from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from .models import Notification, NotificationPreference
from .serializers import (
    NotificationListSerializer, NotificationDetailSerializer,
    NotificationPreferenceSerializer
)
from accounts.permissions import IsAdmin, IsAdminOrSelf


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for notifications - read-only for staff"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return NotificationDetailSerializer
        return NotificationListSerializer

    def get_queryset(self):
        """Get notifications for admin or targeted to this user"""
        user = self.request.user
        if user.role == 'Administrator':
            # Admins see all notifications or those targeted to them
            return Notification.objects.filter(
                Q(targetAdmin__isnull=True) | Q(targetAdmin=user)
            ).order_by('-createdAt')
        # Non-admins don't see notifications
        return Notification.objects.none()

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications"""
        queryset = self.get_queryset().filter(status=Notification.NotificationStatus.UNREAD)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'notifications': serializer.data
        })

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get notifications filtered by type"""
        notification_type = request.query_params.get('type')
        if not notification_type:
            return Response(
                {'error': 'type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(type=notification_type)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all unread notifications as read"""
        queryset = self.get_queryset().filter(status=Notification.NotificationStatus.UNREAD)
        updated = queryset.update(
            status=Notification.NotificationStatus.READ,
            readAt=timezone.now()
        )
        return Response({'message': f'{updated} notifications marked as read'})

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a notification"""
        notification = self.get_object()
        notification.status = Notification.NotificationStatus.ARCHIVED
        notification.save()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics"""
        queryset = self.get_queryset()
        return Response({
            'total': queryset.count(),
            'unread': queryset.filter(status=Notification.NotificationStatus.UNREAD).count(),
            'by_type': {
                'low_stock': queryset.filter(type=Notification.NotificationType.LOW_STOCK).count(),
                'out_of_stock': queryset.filter(type=Notification.NotificationType.OUT_OF_STOCK).count(),
                'orders': queryset.filter(
                    type__in=[
                        Notification.NotificationType.ORDER_PLACED,
                        Notification.NotificationType.ORDER_COMPLETED,
                        Notification.NotificationType.ORDER_CANCELLED,
                        Notification.NotificationType.CREDIT_APPROVED
                    ]
                ).count(),
                'payments': queryset.filter(
                    type__in=[
                        Notification.NotificationType.PAYMENT_RECEIVED,
                        Notification.NotificationType.PAYMENT_PENDING
                    ]
                ).count(),
            }
        })


class NotificationPreferenceViewSet(viewsets.ViewSet):
    """ViewSet for managing notification preferences - admin only for staff preferences, users can edit own"""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_preferences(self, request, staff_id=None):
        """Get notification preferences (admins can see any, users can see their own)"""
        if staff_id:
            if request.user.role != 'Administrator' and str(request.user.staffId) != staff_id:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            try:
                preference = NotificationPreference.objects.get(staff__staffId=staff_id)
            except NotificationPreference.DoesNotExist:
                return Response(
                    {'error': 'Preferences not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            preference, created = NotificationPreference.objects.get_or_create(staff=request.user)
        
        serializer = NotificationPreferenceSerializer(preference)
        return Response(serializer.data)

    def update_preferences(self, request, staff_id=None):
        """Update notification preferences (admins can edit any, users can edit their own)"""
        if staff_id:
            if request.user.role != 'Administrator' and str(request.user.staffId) != staff_id:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            try:
                preference = NotificationPreference.objects.get(staff__staffId=staff_id)
            except NotificationPreference.DoesNotExist:
                return Response(
                    {'error': 'Preferences not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            preference, created = NotificationPreference.objects.get_or_create(staff=request.user)
        
        serializer = NotificationPreferenceSerializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


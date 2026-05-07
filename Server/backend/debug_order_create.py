import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from orders.serializers import OrderCreateSerializer
from django.test import RequestFactory

User = get_user_model()
user = User.objects.filter(role='Clerk').first() or User.objects.filter(role='Administrator').first()
if not user:
    user = User.objects.create_user(email='test@example.com', staffName='Test User', password='testpass', role='Clerk')

from menu.models import MenuItem

menu_item = MenuItem.objects.first()
if not menu_item:
    raise SystemExit('No menu item available to create order payload')

payload = {
    'orderType': 'DineIn',
    'status': 'Completed',
    'paymentStatus': 'Paid',
    'paymentMethod': 'Cash',
    'tableNumber': '1',
    'customerName': 'Walk-in',
    'customerPhone': '0000000000',
    'note': 'Test order',
    'totalAmount': 23.50,
    'items': [
        {'menuItem': str(menu_item.menuItemId), 'quantity': 2, 'unitPrice': 5.50, 'note': ''}
    ]
}

request = RequestFactory().post('/api/v1/orders/orders/')
request.user = user
serializer = OrderCreateSerializer(data=payload, context={'request': request})
print('is_valid', serializer.is_valid())
print('errors', serializer.errors)
if serializer.is_valid():
    try:
        order = serializer.save()
        print('saved order', order.orderId)
    except Exception as exc:
        import traceback
        traceback.print_exc()

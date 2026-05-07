# Database Management Quick Reference

## 🚀 Quick Start

### View Database Statistics
```bash
cd Database
python db_manager.py
```

### Manual Database Backup
```bash
cd Server/backend
python -c "
import shutil
from pathlib import Path
db = Path('db.sqlite3')
backup = Path(f'../../../Database/backups/db_manual_backup.sqlite3')
backup.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(db, backup)
print('✅ Backup created')
"
```

### Check Django Migrations Status
```bash
cd Server/backend
python manage.py showmigrations
```

### Apply All Pending Migrations
```bash
cd Server/backend
python manage.py migrate
```

### Create a Specific App's Migrations
```bash
cd Server/backend
python manage.py makemigrations accounts
python manage.py migrate accounts
```

---

## 🔍 Database Inspection

### List All Tables (Using Django)
```bash
cd Server/backend
python manage.py shell
```

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    for table in cursor.fetchall():
        print(table[0])
```

### Count Records in a Table
```python
from accounts.models import Staff
print(f"Total staff: {Staff.objects.count()}")

from menu.models import MenuItem
print(f"Total menu items: {MenuItem.objects.count()}")

from orders.models import Order
print(f"Total orders: {Order.objects.count()}")
```

### Find Recently Created Records
```python
from orders.models import Order
from datetime import datetime, timedelta

last_day = Order.objects.filter(
    createdAt__gte=datetime.now() - timedelta(days=1)
).order_by('-createdAt')

for order in last_day:
    print(f"{order.orderNumber}: {order.totalAmount}")
```

---

## 📊 Common Database Queries

### Get Daily Sales
```python
from django.db.models import Sum
from orders.models import Order
from datetime import date

today = date.today()
sales = Order.objects.filter(
    createdAt__date=today
).aggregate(total=Sum('totalAmount'))
print(f"Today's sales: {sales['total']}")
```

### Top Selling Items
```python
from django.db.models import Count, Sum
from orders.models import OrderItem

top_items = OrderItem.objects.values('menuItem__name').annotate(
    quantity=Sum('quantity'),
    revenue=Sum('lineTotal')
).order_by('-quantity')[:10]

for item in top_items:
    print(f"{item['menuItem__name']}: {item['quantity']} sold")
```

### Low Stock Alerts
```python
from menu.models import Stock

low_stock = Stock.objects.filter(quantity__lt=5)
for item in low_stock:
    print(f"⚠️  {item.menuItem.name}: {item.quantity} {item.unit}")
```

### Staff Performance
```python
from django.db.models import Count
from orders.models import Order

staff_orders = Order.objects.values('takenBy__staffName').annotate(
    count=Count('orderId')
).order_by('-count')

for staff in staff_orders:
    print(f"{staff['takenBy__staffName']}: {staff['count']} orders")
```

---

## 🛠️ Database Maintenance

### Backup Database
```bash
# One-time backup
python Database/db_manager.py

# Then select option 3 (Create Backup)
```

### Restore from Backup
```bash
cd Server/backend
# List available backups first
ls ../../Database/backups/

# Then restore (replace FILENAME)
python -c "
import shutil
from pathlib import Path
backup = Path('../../Database/backups/FILENAME')
db = Path('db.sqlite3')
shutil.copy2(backup, db.with_suffix('.recovery'))
shutil.copy2(backup, db)
print('✅ Restored from backup')
"
```

### Database Health Check
```bash
cd Server/backend
python -c "
import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute('PRAGMA integrity_check')
result = cursor.fetchone()[0]
print(f'Database integrity: {result}')
conn.close()
"
```

### Optimize Database
```bash
cd Server/backend
python -c "
import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute('VACUUM')
cursor.execute('ANALYZE')
conn.commit()
conn.close()
print('✅ Database optimized')
"
```

---

## 📁 File Management

### View Backup Directory
```bash
ls -la "c:\Users\DELL\Desktop\Roe's POS\Database\backups\"
```

### Check Database File Size
```bash
dir "c:\Users\DELL\Desktop\Roe's POS\Server\backend\db.sqlite3"
```

### Export Database Statistics
```bash
cd Database
python db_manager.py
# Then select option 5 (Export Stats)
```

---

## 🔄 Data Operations

### Bulk Create Sample Data
```python
from accounts.models import Staff
from django.contrib.auth import get_user_model

# Create staff members
staff_data = [
    {'email': 'clerk1@test.com', 'staffName': 'John Clerk', 'role': 'Clerk'},
    {'email': 'manager1@test.com', 'staffName': 'Jane Manager', 'role': 'Manager'},
]

for data in staff_data:
    Staff.objects.get_or_create(
        email=data['email'],
        defaults={
            'staffName': data['staffName'],
            'role': data['role']
        }
    )
```

### Reset Database (WARNING: Deletes all data)
```bash
cd Server/backend

# Delete old database
rm db.sqlite3

# Recreate fresh database
python manage.py migrate

# Create new superuser
python manage.py createsuperuser
```

### Clear Specific Table
```python
from orders.models import Order

# Delete all orders
Order.objects.all().delete()

# Or delete with condition
Order.objects.filter(status='Cancelled').delete()
```

---

## 📈 Performance Monitoring

### Database File Size
```python
from pathlib import Path
import os

db_path = Path('Server/backend/db.sqlite3')
size_mb = db_path.stat().st_size / (1024 * 1024)
print(f"Database size: {size_mb:.2f} MB")
```

### Query Timing
```python
from django.db import connection
from django.test.utils import CaptureQueriesContext
import time

# Measure execution time
start = time.time()

# Your query here
Staff.objects.all()

elapsed = time.time() - start
print(f"Query time: {elapsed:.3f}s")

# See all queries executed
print(f"Queries executed: {len(connection.queries)}")
for q in connection.queries:
    print(q['sql'][:100])
```

---

## ⚠️ Common Issues & Solutions

### Issue: "Database is locked"
**Cause:** Multiple processes accessing SQLite  
**Solution:**
```bash
# Wait 30 seconds
# Close other connections
# Restart Django server
```

### Issue: "No such table"
**Cause:** Migrations not applied  
**Solution:**
```bash
cd Server/backend
python manage.py migrate
```

### Issue: "Foreign key constraint failed"
**Cause:** Deleting parent record with related children  
**Solution:**
```python
# Check related objects first
order = Order.objects.get(pk=123)
print(order.items.count())  # See related items
```

### Issue: "Database file is corrupted"
**Cause:** Unexpected shutdown or hardware failure  
**Solution:**
```bash
# Restore from backup
python Database/db_manager.py
# Select option: Restore from Backup
```

---

## 📚 Django ORM Examples

### Create
```python
from menu.models import MenuItem, Category

category = Category.objects.get(name="Drinks")
item = MenuItem.objects.create(
    category=category,
    name="Coca Cola",
    price=2.50,
    itemType="Drink"
)
```

### Read
```python
# Get one
item = MenuItem.objects.get(name="Coca Cola")

# Get many
items = MenuItem.objects.filter(category__name="Drinks")

# Get all
all_items = MenuItem.objects.all()

# Count
count = MenuItem.objects.count()
```

### Update
```python
item = MenuItem.objects.get(name="Coca Cola")
item.price = 3.00
item.save()
```

### Delete
```python
item = MenuItem.objects.get(name="Coca Cola")
item.delete()
```

---

## 🔐 User Management

### Create Admin Account
```bash
cd Server/backend
python manage.py createsuperuser
```

### Create Staff Account
```python
from accounts.models import Staff

staff = Staff.objects.create_user(
    email='cashier@test.com',
    staffName='John Cashier',
    password='1234567',
    pin='111111',
    role='Clerk'
)
```

### Reset Staff PIN
```python
from accounts.models import Staff

staff = Staff.objects.get(email='cashier@test.com')
staff.set_password('newpin1234')  # 6+ chars
staff.save()
```

### Deactivate User
```python
staff = Staff.objects.get(email='cashier@test.com')
staff.isActive = False
staff.save()
```

---

## 🎯 Testing Data Population

### Quick Data Setup Script
```python
# Place in manage.py shell or scripts/
from accounts.models import Staff
from menu.models import Category, MenuItem
from inventory.models import Supplier

# Create staff
Staff.objects.get_or_create(
    email='admin@test.com',
    defaults={'staffName': 'Admin', 'role': 'Administrator'}
)

# Create categories
Category.objects.get_or_create(
    name='Drinks',
    defaults={'description': 'Beverages'}
)
Category.objects.get_or_create(
    name='Food',
    defaults={'description': 'Main courses'}
)

# Create menu items
drinks = Category.objects.get(name='Drinks')
MenuItem.objects.get_or_create(
    name='Coca Cola',
    defaults={'category': drinks, 'price': 2.50}
)

print("✅ Sample data created")
```

---

## 🚀 Production Checklist

- [ ] Database backups automated
- [ ] Health checks scheduled
- [ ] Monitoring in place
- [ ] Disaster recovery plan ready
- [ ] Staff trained on operations
- [ ] Analytics running
- [ ] Security configured
- [ ] Performance tuned

---

**Last Updated:** May 5, 2026  
**Version:** 1.0
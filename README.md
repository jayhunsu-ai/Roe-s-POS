# Roe's POS System

A comprehensive Point of Sale (POS) system built with Django REST Framework backend and tkinter-based desktop frontends.

## Project Structure

```
Roe's POS/
├── Server/                 # Django Backend
│   └── backend/
│       ├── accounts/       # User authentication & staff management
│       ├── analytics/      # Sales analytics & reporting
│       ├── inventory/      # Inventory management
│       ├── menu/          # Menu items & categories
│       ├── notifications/ # Notification system
│       ├── orders/        # Order processing
│       └── backend/       # Core Django settings
├── Administrator/         # Admin Management Interface
│   ├── admin_app.py      # Main admin application
│   ├── requirements.txt  # Python dependencies
│   └── run.py           # Run script
├── Client/               # POS Client Interface
│   ├── pos_client.py    # Main POS client application
│   ├── requirements.txt # Python dependencies
│   └── run.py          # Run script
├── Database/            # Database files
└── README.md           # This file
```

## Features

### Backend (Django REST Framework)
- **Authentication**: JWT-based authentication with custom Staff user model
- **Staff Management**: Role-based access (Admin, Manager, Clerk)
- **Menu Management**: Categories, items, pricing, stock tracking
- **Inventory**: Suppliers, items, purchase orders, stock levels
- **Orders**: Complete order lifecycle, payments, receipts
- **Analytics**: Sales reports, trends, performance metrics
- **Notifications**: Email/SMS notifications for various events

### Administrator Interface (tkinter)
- **Staff Management**: CRUD operations, role assignment, PIN management
- **Menu Management**: Category/item management, stock updates
- **Inventory Oversight**: Supplier management, inventory tracking
- **Order Management**: View/edit orders, payment processing
- **Analytics Dashboard**: Charts, reports, KPIs
- **System Settings**: API configuration, preferences

### POS Client Interface (tkinter)
- **Order Processing**: Product selection, quantity management
- **Payment Handling**: Multiple payment methods, change calculation
- **Receipt Generation**: Print/email receipts
- **Customer Management**: Customer info, order history
- **Quick Actions**: Discounts, tax exemptions, order holding

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager
- Git (optional)

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd Server/backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server:**
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

#### Administrator Application
```bash
cd Administrator
pip install -r requirements.txt
python admin_app.py
# OR
python run.py
# OR (Windows)
run_admin.bat
```

#### POS Client Application
```bash
cd Client
pip install -r requirements.txt
python pos_client.py
# OR
python run.py
# OR (Windows)
run_client.bat
```

## API Endpoints

### Authentication
- `POST /api/v1/token/` - Obtain JWT token
- `POST /api/v1/token/refresh/` - Refresh JWT token

### Staff Management
- `GET /api/accounts/staff/` - List staff
- `POST /api/accounts/staff/` - Create staff
- `GET /api/accounts/staff/{id}/` - Get staff details
- `PUT /api/accounts/staff/{id}/` - Update staff
- `DELETE /api/accounts/staff/{id}/` - Delete staff

### Menu Management
- `GET /api/v1/menu/categories/` - List categories
- `GET /api/v1/menu/items/` - List menu items
- `POST /api/v1/menu/items/` - Create menu item

### Orders
- `GET /api/v1/orders/` - List orders
- `POST /api/v1/orders/` - Create order
- `GET /api/v1/orders/{id}/` - Get order details

## Testing

### Backend Tests
```bash
cd Server/backend
python manage.py test
# OR
python run_tests.py
```

### Frontend Testing
- Run the applications and test functionality manually
- Check API connectivity and error handling

## Demo Users

The system includes demo users for testing:

### Administrator
- **Email**: admin@test.com
- **PIN**: 123456
- **Role**: Administrator

### Manager
- **Email**: manager@test.com
- **PIN**: 222222
- **Role**: Manager

### Clerk
- **Email**: clerk@test.com
- **PIN**: 111111
- **Role**: Clerk

## Development

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable/function names
- Add docstrings to functions and classes
- Handle exceptions appropriately

### Adding New Features
1. Plan the feature and API endpoints
2. Implement backend API endpoints
3. Update frontend applications
4. Add tests for new functionality
5. Update documentation

### Database Schema
The system uses SQLite by default. Key models:
- **Staff**: User accounts with roles
- **Category**: Menu categories
- **MenuItem**: Individual menu items
- **Stock**: Inventory tracking
- **Supplier**: Supplier information
- **Order**: Customer orders
- **Payment**: Payment records
- **Receipt**: Receipt records

## Deployment

### Backend Deployment
1. Set `DEBUG = False` in settings.py
2. Configure production database
3. Set up static files serving
4. Configure email/SMS services
5. Use a production WSGI server (gunicorn, uwsgi)

### Frontend Deployment
- Package tkinter applications using PyInstaller
- Create executable files for distribution
- Configure API endpoints for production

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure Django server is running on port 8000
   - Check firewall settings
   - Verify API endpoints in frontend code

2. **Login Issues**
   - Verify user credentials
   - Check JWT token expiration
   - Ensure correct PIN format

3. **Database Errors**
   - Run migrations: `python manage.py migrate`
   - Check database file permissions

4. **Import Errors**
   - Install missing dependencies: `pip install -r requirements.txt`
   - Activate virtual environment

### Logs
- Django logs are in the console when running the server
- Frontend applications log errors to console
- Check network connectivity for API calls

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the troubleshooting section
- Review the API documentation
- Create an issue in the repository

---

**Built with ❤️ using Django, tkinter, and modern Python practices**
  - `python manage.py test`

## Production hardening applied

- `SECRET_KEY` is loaded from the environment.
- `DEBUG` now defaults to `False`.
- `ALLOWED_HOSTS` is loaded from the environment.
- `TIME_ZONE` is set to `Africa/Lagos`.
- `MEDIA_ROOT` and `MEDIA_URL` are configured.
- `STATIC_ROOT` is configured.
- JWT auth is enabled via `djangorestframework-simplejwt`.
- Channel layers are configured for in-memory development and Redis in production.
- Session cookies expire after 1 hour and at browser close.
- `SECURE_AUDIT_LOG` setting is available for audit protections.

## Notes

- PostgreSQL is strongly recommended for production deployments.
- `dj-database-url` is supported for parsing `DATABASE_URL`.
- Existing database migrations may require regeneration after auth model changes.

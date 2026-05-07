# POS System Frontend Applications

This directory contains the frontend applications for the POS system:

## Administrator Application (`Administrator/admin_app.py`)
A comprehensive admin interface for managing the POS system including:
- Staff management (CRUD operations, role management, PIN resets)
- Menu management (categories, items, stock tracking)
- Inventory management (suppliers, items, purchase orders)
- Order management and oversight
- Analytics and reporting dashboard
- System settings and configuration

### Features:
- **Authentication**: JWT-based login with role-based access
- **Staff Management**: Add/edit/delete staff, manage roles, reset PINs
- **Menu Management**: Create categories, add menu items, manage stock levels
- **Inventory**: Supplier management, inventory tracking, purchase orders
- **Orders**: View and manage all orders, receipts, payments
- **Analytics**: Sales reports, trends, performance metrics
- **Settings**: API configuration, notification preferences

## Client Application (`Client/pos_client.py`)
A full-featured POS client for order processing and payment handling:
- Order creation and management
- Product selection by category
- Customer management
- Payment processing (multiple methods)
- Receipt generation and printing
- Order holding and retrieval

### Features:
- **Order Processing**: Add/remove items, apply discounts, calculate totals
- **Payment Handling**: Cash, card, mobile, bank transfer payments
- **Receipt Management**: Print receipts, email receipts, digital receipts
- **Customer Tracking**: Customer information, order history
- **Quick Actions**: Common operations for fast service

## Requirements

Both applications require:
```
Python 3.8+
tkinter (usually included with Python)
requests
websocket-client
Pillow (PIL) for image handling
matplotlib for analytics charts
```

## Installation

1. Install Python dependencies:
```bash
pip install requests websocket-client pillow matplotlib
```

2. Ensure the Django backend is running on `http://localhost:8000`

3. Run the applications:
```bash
# Administrator
python Administrator/admin_app.py

# POS Client
python Client/pos_client.py
```

## Configuration

Both applications connect to the Django REST API. Configure the API endpoint in the settings if needed.

## Usage

### Administrator:
1. Login with admin credentials
2. Use the sidebar to navigate between different management sections
3. Each section provides full CRUD operations for that domain

### POS Client:
1. Login with staff credentials
2. Select products from the left panel
3. Manage the order in the center panel
4. Process payments in the right panel
5. Print receipts and complete transactions

## Architecture

- **MVC Pattern**: Separation of UI (View), business logic (Controller), and data (Model)
- **API Integration**: RESTful communication with Django backend
- **Responsive Design**: Adapts to different screen sizes
- **Error Handling**: Comprehensive error handling and user feedback
- **Security**: JWT authentication, input validation

## Development Notes

- Built with modern tkinter and ttk for professional appearance
- Thread-safe API calls to prevent UI freezing
- Modular design for easy maintenance and extension
- Comprehensive logging and debugging capabilities
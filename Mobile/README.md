# Roe's POS Mobile App

A beautifully simple and intuitive React Native mobile application for staff to access the Roe's POS system from their phones.

## ✨ Features

- **🎯 Ultra-Simple Login**: PIN-based authentication with a beautiful keypad interface
- **🍽️ Effortless Ordering**: Tap-to-add menu items with instant visual feedback
- **📊 Smart Order Management**: One-tap status updates with clear visual indicators
- **📦 Inventory at a Glance**: Large, clear stock levels with color-coded status
- **👤 Personal Dashboard**: Clean profile with quick actions
- **🛒 Cart Management**: Add, remove, and modify items with ease
- **📱 Best-in-Class UX**: Designed for speed and simplicity

## 🎨 User Experience Highlights

### Login Screen
- **Visual PIN Entry**: Large dots show PIN progress
- **Touch-Friendly Keypad**: Big, responsive number buttons
- **Clear Feedback**: Immediate visual confirmation
- **Beautiful Design**: Clean, welcoming interface

### Menu Screen
- **One-Tap Ordering**: Touch any item to add to cart
- **Smart Search**: Find food instantly
- **Category Filters**: Quick filtering with visual chips
- **Cart Indicator**: Always-visible cart status with totals
- **Quantity Controls**: Easy +/- buttons for existing items

### Orders Screen
- **Status at a Glance**: Color-coded order status badges
- **One-Button Updates**: Huge, clear status change buttons
- **Clean Layout**: Easy-to-scan order information
- **Quick Actions**: Instant status progression

### Inventory Screen
- **Big Numbers**: Stock levels displayed prominently
- **Color Coding**: Red/Yellow/Green status indicators
- **Touch to Update**: Tap any item to modify stock
- **Minimal Interface**: Focus on what matters

### Profile Screen
- **Quick Actions**: Today's sales and time tracking
- **Clean Menu**: Simple, touchable options
- **Visual Identity**: Large avatar and clear information

## Prerequisites

- Node.js 16+
- React Native CLI
- Android Studio (for Android development)
- Xcode (for iOS development, macOS only)
- Running Django backend server

## Installation

1. **Install Dependencies**
   ```bash
   cd Mobile
   npm install
   ```

2. **Configure API Endpoint**

   Edit the API base URL in the Redux slices:
   - `src/redux/slices/authSlice.js`
   - `src/redux/slices/menuSlice.js`
   - `src/redux/slices/orderSlice.js`
   - `src/redux/slices/inventorySlice.js`

   Change `http://your-server-ip:8000/api` to your actual server IP address.

3. **Android Setup**
   ```bash
   # Install Android SDK and configure environment variables
   # Follow React Native Android setup guide
   npm run android
   ```

4. **iOS Setup** (macOS only)
   ```bash
   cd ios && pod install
   npm run ios
   ```

## Configuration

### Server Configuration

Update the API base URL in all Redux slices to point to your Django backend:

```javascript
const API_BASE_URL = 'http://YOUR_SERVER_IP:8000/api';
```

### Permissions

The app requires the following permissions:
- Internet access for API communication
- Storage access for offline data (future feature)

## 🚀 Usage

### Staff Login
- **Enter your PIN** using the large, clear keypad
- **Visual feedback** shows your progress with dots
- **One-tap login** when ready

### Menu Screen
- **Browse food** with large, clear item cards
- **Tap to add** any item to your order instantly
- **See quantities** with easy +/- controls
- **Search quickly** with the prominent search bar
- **Filter by category** with colorful chips
- **View cart** anytime with the floating button

### Orders Screen
- **See all orders** with clear status badges
- **Filter by status** using the category chips
- **Update status** with one big, clear button tap
- **View details** in an easy-to-read layout

### Inventory Screen
- **Check stock** with huge, clear numbers
- **See status** with color indicators (Green = Good, Yellow = Low, Red = Critical)
- **Update stock** by tapping any item
- **Simple input** with clear quantity entry

### Profile Screen
- **View your info** with a large, clear display
- **Quick actions** for common tasks
- **Simple menu** with touchable options
- **Easy logout** with a prominent button

## Development

### Project Structure
```
Mobile/
├── src/
│   ├── navigation/     # Navigation configuration
│   ├── redux/         # State management
│   │   ├── slices/    # Redux slices
│   │   └── store.js   # Store configuration
│   ├── screens/       # Screen components
│   ├── theme/         # Theme configuration
│   └── utils/         # Utility functions
├── android/           # Android specific files
├── ios/              # iOS specific files
├── package.json
├── App.js
└── index.js
```

### Adding New Features

1. **New Screen**: Create component in `src/screens/`
2. **Navigation**: Add to `MainTabNavigator.js` or create new navigator
3. **State**: Create new Redux slice in `src/redux/slices/`
4. **API**: Add API calls to appropriate slice

### Testing

```bash
# Run tests
npm test

# Run on specific platform
npm run android  # Android
npm run ios      # iOS
```

## Deployment

### Android APK
```bash
cd android
./gradlew assembleRelease
```

### iOS App Store
```bash
# Build and submit through Xcode
```

## Troubleshooting

### Common Issues

1. **Network Connection**
   - Ensure backend server is running
   - Check API endpoint configuration
   - Verify network connectivity

2. **Build Issues**
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Clear React Native cache: `npx react-native start --reset-cache`

3. **Android Emulator**
   - Ensure Android SDK is properly configured
   - Check AVD Manager for virtual devices

4. **iOS Simulator**
   - Ensure Xcode is installed and updated
   - Run `pod install` in ios directory

### Debug Mode

Enable debugging:
```bash
# Android
npm run android -- --mode debug

# iOS
npm run ios -- --configuration Debug
```

## API Integration

The app integrates with the Django REST API endpoints:

- `POST /api/auth/login/` - Staff authentication
- `GET /api/menu/items/` - Menu items
- `GET /api/orders/` - Order management
- `GET /api/inventory/items/` - Inventory data

## Security

- JWT token-based authentication
- Secure token storage using AsyncStorage
- PIN-based login for staff convenience
- API request/response encryption (handled by backend)

## Future Enhancements

- [ ] Offline order creation
- [ ] Push notifications
- [ ] Barcode scanning for inventory
- [ ] Customer loyalty features
- [ ] Multi-language support
- [ ] Dark mode theme

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review Django backend logs
3. Check React Native documentation
4. Contact development team

## License

© 2024 Roe's Restaurant POS System
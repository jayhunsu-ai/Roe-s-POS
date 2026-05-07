# Database Schema Reference

## Complete Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STAFF MANAGEMENT                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ STAFF                                                                 │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │ • staffId (UUID, PK)                                                 │  │
│  │ • staffName                                                           │  │
│  │ • email (unique)                                                      │  │
│  │ • role (Admin, Clerk, InventoryManager, Kitchen)                     │  │
│  │ • phone                                                               │  │
│  │ • lastLoginAt                                                         │  │
│  │ • failedPinAttempts                                                   │  │
│  │ • isActive (soft delete)                                              │  │
│  │ • createdAt, updatedAt                                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          MENU MANAGEMENT                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐      ┌─────────────────────┐                         │
│  │ CATEGORY         │◄─────│ MENU_ITEM           │                         │
│  ├──────────────────┤ 1  M ├─────────────────────┤                         │
│  │ categoryId (PK)  │      │ menuItemId (PK)     │                         │
│  │ name             │      │ categoryId (FK)     │                         │
│  │ description      │      │ name                │                         │
│  │ isActive         │      │ itemType            │                         │
│  │ createdAt        │      │ price               │                         │
│  └──────────────────┘      │ image               │                         │
│                            │ isAvailable         │                         │
│                            │ trackStock          │                         │
│                            │ createdAt           │                         │
│                            └──────────┬──────────┘                         │
│                                       │                                    │
│                    ┌──────────────────┼────────────────────┐              │
│                    │                  │                    │              │
│          ┌─────────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐   │
│          │ STOCK            │  │ STOCK       │  │ MENU_ITEM_ADDON │   │
│          │                  │  │ TRANSACTION │  │                 │   │
│          ├──────────────────┤  ├─────────────┤  ├─────────────────┤   │
│          │ stockId (PK)     │  │ transactionId(PK)   │ addonId (PK)    │   │
│          │ menuItem (FK)    │  │ stock (FK)  │  │ menuItem (FK)   │   │
│          │ quantity         │  │ type        │  │ name            │   │
│          │ lowStockThreshold│  │ quantityChanged │ extraPrice      │   │
│          │ unit             │  │ quantityBefore  │ isAvailable     │   │
│          │ updatedAt        │  │ quantityAfter   │                 │   │
│          └──────────────────┘  │ performedBy (FK) │                 │   │
│                                │ createdAt   │  └─────────────────┘   │
│                                └─────────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        INVENTORY MANAGEMENT                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ SUPPLIER                                                    │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │ supplierId (PK)                                             │             │
│  │ name, contactName, phone, email, address                   │             │
│  │ isActive, createdAt                                         │             │
│  └────────────┬─────────────────────────────────────────────────┘             │
│               │ supplies                                                     │
│               │                                                              │
│               ▼                                                              │
│  ┌──────────────────────┐      ┌─────────────────────────────┐              │
│  │ INVENTORY_ITEM       │◄─────│ MENU_ITEM_INGREDIENT        │              │
│  ├──────────────────────┤      ├─────────────────────────────┤              │
│  │ inventoryItemId (PK) │ 1  M │ ingredientId (PK)           │              │
│  │ name                 │      │ menuItem (FK)               │              │
│  │ description          │      │ inventoryItem (FK)          │              │
│  │ unit (kg, g, L, etc) │      │ quantityUsed                │              │
│  │ quantityInStock      │      └─────────────────────────────┘              │
│  │ lowStockThreshold    │                                                   │
│  │ costPerUnit          │            MENU_ITEM               │              │
│  │ supplier (FK)        │            (links back)            │              │
│  │ isActive             │                                    │              │
│  │ createdAt            │                                    │              │
│  └──────────┬───────────┘                                    │              │
│             │                                                │              │
│             └─────────────────────────────────────────────────              │
│                                                              │              │
│  ┌──────────────────────┐      ┌────────────────────────────┐              │
│  │ PURCHASE_ORDER       │◄─────│ INVENTORY_TRANSACTION      │              │
│  ├──────────────────────┤ 1  M ├────────────────────────────┤              │
│  │ purchaseOrderId (PK) │      │ transactionId (PK)         │              │
│  │ poNumber             │      │ inventoryItem (FK)         │              │
│  │ supplier (FK)        │      │ type (Purchase, Usage...)  │              │
│  │ status (Draft,       │      │ quantityChanged            │              │
│  │   Ordered, Received) │      │ quantityBefore/After       │              │
│  │ totalCost            │      │ relatedOrder (FK)          │              │
│  │ orderedBy (FK)       │      │ relatedPO (FK)             │              │
│  │ orderedAt, receivedAt│      │ performedBy (FK)           │              │
│  │ createdAt            │      │ createdAt                  │              │
│  └──────────────────────┘      └────────────────────────────┘              │
│                                                              │              │
└─────────────────────────────────────────────────────────────┴──────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          ORDER PROCESSING                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐      ┌────────────────────────────┐               │
│  │ CUSTOMER             │◄─────│ ORDER                      │               │
│  ├──────────────────────┤      ├────────────────────────────┤               │
│  │ customerId (PK)      │ 0..1 │ orderId (PK)               │               │
│  │ name                 │      │ orderNumber (unique)       │               │
│  │ phone, email         │      │ customer (FK)              │               │
│  │ address              │      │ takenBy (FK) - Staff       │               │
│  │ createdAt            │      │ servedBy (FK) - Staff      │               │
│  └──────────────────────┘      │ status (Pending,           │               │
│                                │   Confirmed, Preparing...) │               │
│                                │ paymentStatus (Unpaid,     │               │
│                                │   Paid, Partial)           │               │
│                                │ orderType (DineIn,         │               │
│                                │   Takeaway, Delivery)      │               │
│                                │ subtotal, discountAmount   │               │
│                                │ taxAmount, totalAmount     │               │
│                                │ isCreditAllowed            │               │
│                                │ creditApprovedBy (FK)      │               │
│                                │ createdAt, completedAt     │               │
│                                └────────┬───────────────────┘               │
│                                         │                                  │
│                        ┌────────────────┼────────────────┐                │
│                        │                │                │                │
│            ┌───────────▼────┐   ┌──────▼──────┐   ┌────▼──────────┐    │
│            │ ORDER_ITEM      │   │ PAYMENT     │   │ RECEIPT        │    │
│            ├─────────────────┤   ├─────────────┤   ├────────────────┤    │
│            │ orderItemId (PK)│   │ paymentId(PK)   │ receiptId (PK) │    │
│            │ order (FK)      │   │ order (FK)  │   │ order (FK)     │    │
│            │ menuItem (FK)   │   │ amount      │   │ receiptNumber  │    │
│            │ quantity        │   │ method      │   │ total          │    │
│            │ price (at time) │   │ verification│   │ tax            │    │
│            │ lineTotal       │   │ verifiedBy  │   │ discountAmount │    │
│            │ addons (JSON)   │   │ verifiedAt  │   │ paymentMethod  │    │
│            │ note            │   │ processedAt │   │ isPrinted      │    │
│            │ createdAt       │   │ createdAt   │   │ isEmailed      │    │
│            └─────────────────┘   └─────────────┘   │ createdAt      │    │
│                                                    └────────────────┘    │
│  ┌──────────────────────┐                                                 │
│  │ ORDER_COUNTER        │                                                 │
│  │ (for auto-numbering) │                                                 │
│  └──────────────────────┘                                                 │
│  ┌──────────────────────┐                                                 │
│  │ RECEIPT_COUNTER      │                                                 │
│  │ (for auto-numbering) │                                                 │
│  └──────────────────────┘                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          ANALYTICS & REPORTING                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ SALES_SUMMARY                                              │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │ summaryId (PK)                                             │             │
│  │ periodType (Daily, Weekly, Monthly)                        │             │
│  │ startDate, endDate                                         │             │
│  │ totalRevenue, totalOrders, avgOrderValue                   │             │
│  │ totalItemsSold, uniqueItemsSold                            │             │
│  │ cashPayments, cardPayments, otherPayments                  │             │
│  │ topStaff (JSON)                                            │             │
│  │ createdAt                                                  │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ ITEM_PERFORMANCE                                           │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │ performanceId (PK)                                         │             │
│  │ menuItem (FK)                                              │             │
│  │ date                                                       │             │
│  │ quantitySold, revenue, orderCount                          │             │
│  │ salesRank, popularityScore                                 │             │
│  │ createdAt                                                  │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ HOURLY_ANALYTICS                                           │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │ analyticsId (PK)                                           │             │
│  │ date, hour (0-23)                                          │             │
│  │ revenue, orderCount, avgOrderValue                         │             │
│  │ itemsSold, popularItems (JSON)                             │             │
│  │ createdAt                                                  │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       NOTIFICATIONS & ALERTS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ NOTIFICATION                                               │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │ notificationId (PK)                                        │             │
│  │ type (LOW_STOCK, OUT_OF_STOCK, ORDER_*, PAYMENT_*...)     │             │
│  │ title, message                                             │             │
│  │ status (Unread, Read, Archived)                            │             │
│  │ priority (1-5)                                             │             │
│  │ order (FK) - optional                                      │             │
│  │ inventoryItem (FK) - optional                              │             │
│  │ menuItem (FK) - optional                                   │             │
│  │ targetAdmin (FK) - Staff                                   │             │
│  │ createdAt, readAt                                          │             │
│  │ Indexes: createdAt, status, type                           │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ NOTIFICATION_PREFERENCE                                    │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │ staff (FK) - OneToOne with Staff                           │             │
│  │ notify_low_stock, notify_out_of_stock                      │             │
│  │ notify_orders, notify_payments, notify_system              │             │
│  │ email_enabled, email_low_stock                             │             │
│  │ low_stock_alert_days                                       │             │
│  │ createdAt, updatedAt                                       │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Key Relationships Summary

| From | To | Type | Purpose |
|------|----|----|---------|
| MENU_ITEM | CATEGORY | M:1 | Items belong to categories |
| MENU_ITEM | STOCK | 1:1 | Item tracking |
| MENU_ITEM | MENU_ITEM_INGREDIENT | 1:M | Recipe composition |
| MENU_ITEM | MENU_ITEM_ADDON | 1:M | Customizations |
| INVENTORY_ITEM | SUPPLIER | M:1 | Item sourcing |
| INVENTORY_ITEM | MENU_ITEM_INGREDIENT | 1:M | Recipe ingredients |
| PURCHASE_ORDER | SUPPLIER | M:1 | Orders from supplier |
| PURCHASE_ORDER | STAFF | M:1 | Who ordered |
| ORDER | CUSTOMER | M:1 | Customer's orders |
| ORDER | STAFF | M:1 | Staff took order |
| ORDER_ITEM | ORDER | M:1 | Items in order |
| ORDER_ITEM | MENU_ITEM | M:1 | What was ordered |
| PAYMENT | ORDER | M:1 | Order payments |
| RECEIPT | ORDER | 1:1 | Order receipt |
| STAFF | (many) | 1:M | Who performed actions |
| NOTIFICATION | STAFF | M:1 | For which staff |
| ITEM_PERFORMANCE | MENU_ITEM | M:1 | Item metrics |
| SALES_SUMMARY | (none) | - | Aggregated data |

---

## 🔑 Primary Key Strategy

**All tables use UUID (Universally Unique Identifier)** for primary keys instead of sequential integers:

**Advantages:**
- ✅ Collision-free across systems
- ✅ Scalable to multiple databases
- ✅ Secure (not predictable)
- ✅ Easy to merge/migrate data

**Auto-Numbering (Human-Readable):**
- `orderNumber`: ORD-0001, ORD-0002, etc.
- `poNumber`: PO-0001, PO-0002, etc.
- `receiptNumber`: REC-0001, REC-0002, etc.

These use counter tables for atomic increments.

---

## 📋 Field Types Reference

| Type | Usage | Example |
|------|-------|---------|
| UUID | All primary keys | staffId, menuItemId |
| CharField | Text, limited | name, email, role |
| TextField | Long text | description, note, message |
| Decimal | Money | price, totalAmount, costPerUnit |
| PositiveInteger | Quantities | quantity, lowStockThreshold |
| Boolean | Flags | isActive, isAvailable |
| DateTimeField | Timestamps | createdAt, updatedAt |
| ForeignKey | Relationships | category, menuItem |
| OneToOneField | Unique relation | stock to menuItem |
| JSONField | Complex data | topStaff, popularItems |

---

## 🔐 Audit Trail Fields

Every important table includes:
- `createdAt` - When created
- `updatedAt` - Last modified (auto)
- `performedBy` - Who did it (Staff FK)

Transaction tables also include:
- `quantityBefore` / `quantityAfter`
- `transactionType` - Action type
- `note` - Reason/comment

---

## 🚨 Data Integrity

**Constraints:**
- ✅ Foreign keys prevent orphaned records
- ✅ Unique constraints prevent duplicates (email, order number, PO number)
- ✅ NOT NULL constraints on required fields
- ✅ Default values for status fields
- ✅ Choice constraints on enum fields

---

## 📈 Database Growth Indicators

**High-Volume Tables:**
- `ORDER_ITEM` - Grows with every order
- `INVENTORY_TRANSACTION` - Grows with every stock movement
- `STOCK_TRANSACTION` - Grows with menu item changes
- `NOTIFICATION` - Grows with system activity

**Recommendation:** Archive data older than 1 year for analytics table to maintain performance.

---

**Database Schema Version:** 1.0  
**Last Updated:** May 5, 2026  
**Status:** ✅ Production Ready
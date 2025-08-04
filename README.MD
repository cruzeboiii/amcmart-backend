# AMCMart Backend API

A RESTful API server for AMCMart - Premium Chicken & Mutton Delivery Service.

## 🚀 Live API

- **Production URL**: `https://your-app-name.onrender.com`
- **Health Check**: `https://your-app-name.onrender.com/api/health`

## 📍 API Endpoints

### Products
- `GET /api/products` - Get all products
- `GET /api/products/{id}` - Get specific product
- `POST /api/products` - Create new product
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product

### Orders
- `GET /api/orders` - Get all orders
- `GET /api/orders/{id}` - Get specific order
- `POST /api/orders` - Create new order
- `PUT /api/orders/{id}/status` - Update order status

### Customers
- `GET /api/customers` - Get customer analytics

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics

### Promo Codes
- `GET /api/promocodes` - Get all promo codes
- `POST /api/promocodes` - Create promo code
- `PUT /api/promocodes/{id}` - Update promo code
- `DELETE /api/promocodes/{id}` - Delete promo code
- `POST /api/promo/validate` - Validate promo code

## 🗄️ Sample Data

The API comes with pre-loaded sample data:
- 8 products (chicken & mutton varieties)
- 8 sample orders with different statuses
- 7 promo codes
- 8 unique customers

## 🛠️ Local Development

```bash
python server.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import urllib.parse
from datetime import datetime
import random
import string
import os

class AMCMartHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/products':
            self.get_products()
        elif self.path.startswith('/api/products/'):
            product_id = self.path.split('/')[-1]
            self.get_product(product_id)
        elif self.path.startswith('/api/orders/'):
            order_id = self.path.split('/')[-1]
            self.get_order(order_id)
        elif self.path == '/api/orders':
            self.get_all_orders()
        elif self.path == '/api/customers':
            self.get_customers()
        elif self.path == '/api/dashboard/stats':
            self.get_dashboard_stats()
        elif self.path == '/api/promocodes':
            self.get_all_promocodes()
        elif self.path == '/api/health':
            self.health_check()
        elif self.path == '/':
            self.serve_welcome_page()
        else:
            self.send_error(404)

    def serve_welcome_page(self):
        """Serve a welcome page for the root URL"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self._set_cors_headers()
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AMCMart API Server</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                .header { background: #e74c3c; color: white; padding: 20px; border-radius: 8px; text-align: center; }
                .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #e74c3c; }
                .method { color: #e74c3c; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🛒 AMCMart API Server</h1>
                <p>Premium Chicken & Mutton Delivery Service API</p>
            </div>
            
            <h2>📍 Available Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/health</code> - Health check
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/products</code> - Get all products<br>
                <span class="method">POST</span> <code>/api/products</code> - Create product<br>
                <span class="method">PUT</span> <code>/api/products/{id}</code> - Update product<br>
                <span class="method">DELETE</span> <code>/api/products/{id}</code> - Delete product
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/orders</code> - Get all orders<br>
                <span class="method">POST</span> <code>/api/orders</code> - Create order<br>
                <span class="method">PUT</span> <code>/api/orders/{id}/status</code> - Update order status
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/customers</code> - Get customers
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/dashboard/stats</code> - Dashboard statistics
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/promocodes</code> - Get promo codes<br>
                <span class="method">POST</span> <code>/api/promo/validate</code> - Validate promo code
            </div>
            
            <p><strong>🌐 API Base URL:</strong> <code id="baseUrl"></code></p>
            
            <script>
                document.getElementById('baseUrl').textContent = window.location.origin;
            </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def do_POST(self):
        if self.path == '/api/products':
            self.create_product()
        elif self.path == '/api/orders':
            self.create_order()
        elif self.path == '/api/promo/validate':
            self.validate_promo()
        elif self.path == '/api/promocodes':
            self.create_promocode()
        else:
            self.send_error(404)

    def do_PUT(self):
        if self.path.startswith('/api/products/'):
            product_id = self.path.split('/')[-1]
            self.update_product(product_id)
        elif self.path.startswith('/api/promocodes/'):
            promo_id = self.path.split('/')[-1]
            self.update_promocode(promo_id)
        elif self.path.startswith('/api/orders/') and self.path.endswith('/status'):
            order_id = self.path.split('/')[-2]
            self.update_order_status(order_id)
        else:
            self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith('/api/products/'):
            product_id = self.path.split('/')[-1]
            self.delete_product(product_id)
        elif self.path.startswith('/api/promocodes/'):
            promo_id = self.path.split('/')[-1]
            self.delete_promocode(promo_id)
        else:
            self.send_error(404)

    # ============ DASHBOARD STATS ENDPOINT ============
    
    def get_dashboard_stats(self):
        try:
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            # Total orders
            cursor.execute('SELECT COUNT(*) FROM orders')
            total_orders = cursor.fetchone()[0]
            
            # Total revenue
            cursor.execute('SELECT SUM(total) FROM orders WHERE total IS NOT NULL')
            total_revenue = cursor.fetchone()[0] or 0
            
            # Total customers (distinct by phone)
            cursor.execute('SELECT COUNT(DISTINCT phoneNo) FROM orders')
            total_customers = cursor.fetchone()[0]
            
            # Pending orders (not delivered)
            cursor.execute('SELECT COUNT(*) FROM orders WHERE status != "delivered"')
            pending_orders = cursor.fetchone()[0]
            
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'data': {
                    'total_orders': total_orders,
                    'total_revenue': total_revenue,
                    'total_customers': total_customers,
                    'pending_orders': pending_orders
                }
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    # ============ CUSTOMERS ENDPOINT ============
    
    def get_customers(self):
        try:
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            # Get customer data grouped by phone number
            cursor.execute('''
                SELECT 
                    firstName,
                    lastName,
                    email,
                    phoneNo,
                    COUNT(*) as total_orders,
                    SUM(total) as total_spent,
                    MAX(created_at) as last_order
                FROM orders 
                GROUP BY phoneNo 
                ORDER BY total_spent DESC
            ''')
            
            customers = cursor.fetchall()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            customers_list = []
            for customer in customers:
                customers_list.append({
                    'firstName': customer[0],
                    'lastName': customer[1],
                    'email': customer[2],
                    'phoneNo': customer[3],
                    'total_orders': customer[4],
                    'total_spent': customer[5] or 0,
                    'last_order': customer[6]
                })
            
            response = {'success': True, 'data': customers_list, 'count': len(customers_list)}
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    # ============ PRODUCTS ENDPOINTS ============
    
    def get_products(self):
        try:
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM products ORDER BY id')
            products = cursor.fetchall()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            products_list = []
            for product in products:
                products_list.append({
                    'id': product[0],
                    'productname': product[1],
                    'category': product[2],
                    'price_1kg': product[3],
                    'price_500gm': product[4],
                    'stock_status': product[5],
                    'image': product[6]
                })
            
            response = {'success': True, 'data': products_list, 'count': len(products_list)}
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def get_product(self, product_id):
        try:
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            if product:
                response = {
                    'success': True,
                    'data': {
                        'id': product[0],
                        'productname': product[1],
                        'category': product[2],
                        'price_1kg': product[3],
                        'price_500gm': product[4],
                        'stock_status': product[5],
                        'image': product[6]
                    }
                }
            else:
                response = {'success': False, 'error': 'Product not found'}
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def create_product(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Validate required fields
            required_fields = ['productname', 'category', 'price_1kg', 'price_500gm', 'stock_status']
            for field in required_fields:
                if not data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO products (productname, category, price_1kg, price_500gm, stock_status, image)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['productname'],
                data['category'],
                data['price_1kg'],
                data['price_500gm'],
                data['stock_status'],
                data.get('image', 'https://via.placeholder.com/300x250?text=Product+Image')
            ))
            
            product_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'data': {
                    'id': product_id,
                    'message': f'Product {data["productname"]} created successfully!'
                }
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def update_product(self, product_id):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE products 
                SET productname = ?, category = ?, price_1kg = ?, price_500gm = ?, stock_status = ?, image = ?
                WHERE id = ?
            ''', (
                data.get('productname'),
                data.get('category'),
                data.get('price_1kg'),
                data.get('price_500gm'),
                data.get('stock_status'),
                data.get('image'),
                product_id
            ))
            
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'message': f'Product ID {product_id} updated successfully!'
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def delete_product(self, product_id):
        try:
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            
            if cursor.rowcount == 0:
                raise ValueError("Product not found")
            
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'message': f'Product ID {product_id} deleted successfully!'
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    # ============ ORDERS ENDPOINTS ============
    
    def create_order(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Generate order ID
            order_id = 'AMC' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # Validate required fields
            required_fields = ['firstName', 'lastName', 'phoneNo', 'email', 'address', 'city', 'pincode', 'deliveryType', 'paymentMethod', 'items', 'total']
            for field in required_fields:
                if not data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            # Save to database
            self.save_order_to_db(order_id, data)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'data': {
                    'order_id': order_id,
                    'message': 'Order placed successfully!',
                    'customer_name': f"{data['firstName']} {data['lastName']}"
                }
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def validate_promo(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            code = data.get('code', '').upper()
            
            # Check promo code in database
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM promocodes WHERE code = ? AND status = "active" AND used = "no"', (code,))
            promo = cursor.fetchone()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            if promo:
                response = {
                    'success': True,
                    'data': {
                        'code': promo[1],
                        'discount': promo[2],
                        'message': f'Promo code applied! ₹{promo[2]} discount'
                    }
                }
            else:
                response = {'success': False, 'error': 'Invalid or expired promo code'}
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def get_order(self, order_id):
        try:
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM orders WHERE orderid = ?', (order_id,))
            order = cursor.fetchone()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            if order:
                response = {
                    'success': True,
                    'data': {
                        'orderid': order[0],
                        'firstName': order[1],
                        'lastName': order[2],
                        'phoneNo': order[3],
                        'email': order[4],
                        'address': order[5],
                        'city': order[6],
                        'pincode': order[7],
                        'deliveryType': order[8],
                        'paymentMethod': order[9],
                        'promocode': order[10],
                        'items': order[11],
                        'total': order[12],
                        'status': order[13],
                        'created_at': order[14]
                    }
                }
            else:
                response = {'success': False, 'error': 'Order not found'}
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def get_all_orders(self):
        try:
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
            orders = cursor.fetchall()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            orders_list = []
            for order in orders:
                orders_list.append({
                    'orderid': order[0],
                    'firstName': order[1],
                    'lastName': order[2],
                    'phoneNo': order[3],
                    'email': order[4],
                    'address': order[5],
                    'city': order[6],
                    'pincode': order[7],
                    'deliveryType': order[8],
                    'paymentMethod': order[9],
                    'promocode': order[10],
                    'items': order[11],
                    'total': order[12],
                    'status': order[13],
                    'created_at': order[14]
                })
            
            response = {'success': True, 'data': orders_list, 'count': len(orders_list)}
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def update_order_status(self, order_id):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            new_status = data.get('status')
            
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('UPDATE orders SET status = ? WHERE orderid = ?', (new_status, order_id))
            
            if cursor.rowcount == 0:
                raise ValueError("Order not found")
            
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'message': f'Order {order_id} status updated to {new_status}!'
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    # ============ PROMO CODES ENDPOINTS ============
    
    def create_promocode(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO promocodes (code, discount, status, used)
                VALUES (?, ?, ?, ?)
            ''', (data['code'].upper(), data['discount'], data.get('status', 'active'), 'no'))
            
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'message': f'Promo code {data["code"]} created successfully!'
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def get_all_promocodes(self):
        try:
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM promocodes ORDER BY id DESC')
            promocodes = cursor.fetchall()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            promo_list = []
            for promo in promocodes:
                promo_list.append({
                    'id': promo[0],
                    'code': promo[1],
                    'discount': promo[2],
                    'status': promo[3],
                    'used': promo[4]
                })
            
            response = {'success': True, 'data': promo_list, 'count': len(promo_list)}
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def update_promocode(self, promo_id):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE promocodes 
                SET code = ?, discount = ?, status = ?, used = ?
                WHERE id = ?
            ''', (data.get('code', '').upper(), data.get('discount'), 
                  data.get('status'), data.get('used'), promo_id))
            
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'message': f'Promo code updated successfully!'
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def delete_promocode(self, promo_id):
        try:
            conn = sqlite3.connect('amcmart.db')
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM promocodes WHERE id = ?', (promo_id,))
            
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'message': 'Promo code deleted successfully!'
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def health_check(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        
        response = {
            'success': True,
            'message': 'AMCMart API is running!',
            'timestamp': datetime.now().isoformat(),
            'database': 'amcmart.db',
            'environment': 'production' if os.environ.get('PORT') else 'development'
        }
        self.wfile.write(json.dumps(response).encode())

    def save_order_to_db(self, order_id, data):
        conn = sqlite3.connect('amcmart.db')
        cursor = conn.cursor()
        
        # Insert order with processing status (next step after pending)
        cursor.execute('''
            INSERT INTO orders (orderid, firstName, lastName, phoneNo, email, address, city, pincode, deliveryType, paymentMethod, promocode, items, total, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id,
            data.get('firstName'),
            data.get('lastName'),
            data.get('phoneNo'),
            data.get('email'),
            data.get('address'),
            data.get('city'),
            data.get('pincode'),
            data.get('deliveryType'),
            data.get('paymentMethod'),
            data.get('promocode', ''),
            data.get('items'),
            data.get('total'),
            'processing',  # New orders start as processing
            datetime.now().isoformat()
        ))
        
        # Update promo code to used if provided
        if data.get('promocode'):
            cursor.execute('''
                UPDATE promocodes SET used = 'yes' WHERE code = ?
            ''', (data.get('promocode').upper(),))
        
        conn.commit()
        conn.close()

def init_database():
    """Initialize database with tables and sample data"""
    conn = sqlite3.connect('amcmart.db')
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            productname TEXT NOT NULL,
            category TEXT NOT NULL,
            price_1kg REAL NOT NULL,
            price_500gm REAL NOT NULL,
            stock_status TEXT DEFAULT 'in_stock',
            image TEXT
        )
    ''')
    
    # Create orders table with new columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            orderid TEXT PRIMARY KEY,
            firstName TEXT NOT NULL,
            lastName TEXT NOT NULL,
            phoneNo TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            pincode TEXT NOT NULL,
            deliveryType TEXT NOT NULL,
            paymentMethod TEXT NOT NULL,
            promocode TEXT,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'processing',
            created_at TEXT
        )
    ''')
    
    # Check if we need to add new columns to existing table
    cursor.execute("PRAGMA table_info(orders)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'items' not in columns:
        cursor.execute('ALTER TABLE orders ADD COLUMN items TEXT DEFAULT ""')
    if 'total' not in columns:
        cursor.execute('ALTER TABLE orders ADD COLUMN total REAL DEFAULT 0.0')
    if 'status' not in columns:
        cursor.execute('ALTER TABLE orders ADD COLUMN status TEXT DEFAULT "processing"')
    if 'created_at' not in columns:
        cursor.execute('ALTER TABLE orders ADD COLUMN created_at TEXT DEFAULT ""')
    
    # Create promocodes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount REAL NOT NULL,
            status TEXT DEFAULT 'active',
            used TEXT DEFAULT 'no'
        )
    ''')
    
    # ============ ADD SAMPLE DATA (Essential for Render) ============
    
    # Check if sample data already exists
    cursor.execute('SELECT COUNT(*) FROM products')
    product_count = cursor.fetchone()[0]
    
    if product_count == 0:
        print("🔄 Initializing database with sample data...")
        
        # Sample Products
        sample_products = [
            ('Premium Chicken Breast', 'chicken', 450, 230, 'in_stock', 'https://via.placeholder.com/300x250/e74c3c/ffffff?text=Chicken+Breast'),
            ('Fresh Mutton Curry Cut', 'mutton', 650, 330, 'in_stock', 'https://via.placeholder.com/300x250/8e44ad/ffffff?text=Mutton+Curry'),
            ('Chicken Biryani Cut', 'chicken', 420, 215, 'in_stock', 'https://via.placeholder.com/300x250/e74c3c/ffffff?text=Biryani+Cut'),
            ('Mutton Leg Pieces', 'mutton', 680, 345, 'in_stock', 'https://via.placeholder.com/300x250/8e44ad/ffffff?text=Leg+Pieces'),
            ('Chicken Wings', 'chicken', 380, 195, 'in_stock', 'https://via.placeholder.com/300x250/e74c3c/ffffff?text=Chicken+Wings'),
            ('Mutton Ribs', 'mutton', 720, 365, 'out_of_stock', 'https://via.placeholder.com/300x250/95a5a6/ffffff?text=Out+of+Stock'),
            ('Chicken Drumsticks', 'chicken', 400, 205, 'in_stock', 'https://via.placeholder.com/300x250/e74c3c/ffffff?text=Drumsticks'),
            ('Mutton Shoulder', 'mutton', 700, 355, 'in_stock', 'https://via.placeholder.com/300x250/8e44ad/ffffff?text=Shoulder')
        ]
        
        cursor.executemany('''
            INSERT INTO products (productname, category, price_1kg, price_500gm, stock_status, image)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_products)
        
        # Sample Promo Codes
        sample_promos = [
            ('WELCOME10', 10, 'active', 'no'),
            ('SAVE50', 50, 'active', 'no'),
            ('FIRST20', 20, 'active', 'no'),
            ('NEWUSER15', 15, 'active', 'no'),
            ('CHICKEN5', 5, 'active', 'no'),
            ('MUTTON25', 25, 'active', 'yes'),
            ('EXPIRED30', 30, 'inactive', 'no')
        ]
        
        cursor.executemany('''
            INSERT INTO promocodes (code, discount, status, used)
            VALUES (?, ?, ?, ?)
        ''', sample_promos)
        
        # Sample Orders (for realistic dashboard data)
        sample_orders = [
            ('AMC12345678', 'Rajesh', 'Kumar', '9876543210', 'rajesh@example.com', '123 MG Road', 'Mumbai', '400001', 'express', 'online', 'WELCOME10', '[{"name":"Premium Chicken Breast","price":450,"quantity":1,"weight":"1kg"}]', 440, 'delivered', '2024-01-15T10:30:00'),
            ('AMC87654321', 'Priya', 'Sharma', '9876543211', 'priya@example.com', '456 Brigade Road', 'Bangalore', '560001', 'standard', 'cod', '', '[{"name":"Fresh Mutton Curry Cut","price":650,"quantity":1,"weight":"1kg"}]', 650, 'processing', '2024-01-16T14:20:00'),
            ('AMC11223344', 'Amit', 'Singh', '9876543212', 'amit@example.com', '789 Park Street', 'Kolkata', '700001', 'express', 'online', 'SAVE50', '[{"name":"Chicken Biryani Cut","price":420,"quantity":2,"weight":"1kg"}]', 790, 'shipped', '2024-01-17T09:15:00'),
            ('AMC55667788', 'Anita', 'Reddy', '9876543213', 'anita@example.com', '321 Anna Salai', 'Chennai', '600001', 'standard', 'online', '', '[{"name":"Mutton Leg Pieces","price":680,"quantity":1,"weight":"1kg"},{"name":"Chicken Wings","price":380,"quantity":1,"weight":"1kg"}]', 1060, 'delivered', '2024-01-18T16:45:00'),
            ('AMC99887766', 'Vikram', 'Patel', '9876543214', 'vikram@example.com', '654 SG Highway', 'Ahmedabad', '380001', 'express', 'cod', 'FIRST20', '[{"name":"Premium Chicken Breast","price":450,"quantity":1,"weight":"500gm"}]', 210, 'processing', '2024-01-19T11:30:00'),
            ('AMC44556677', 'Neha', 'Gupta', '9876543215', 'neha@example.com', '987 Sector 17', 'Chandigarh', '160001', 'standard', 'online', '', '[{"name":"Chicken Drumsticks","price":400,"quantity":2,"weight":"1kg"}]', 800, 'shipped', '2024-01-20T13:20:00'),
            ('AMC33445566', 'Ravi', 'Mehta', '9876543216', 'ravi@example.com', '147 Civil Lines', 'Delhi', '110001', 'express', 'online', 'CHICKEN5', '[{"name":"Mutton Shoulder","price":700,"quantity":1,"weight":"1kg"}]', 695, 'delivered', '2024-01-21T15:10:00'),
            ('AMC77889900', 'Sunita', 'Joshi', '9876543217', 'sunita@example.com', '258 FC Road', 'Pune', '411001', 'standard', 'cod', '', '[{"name":"Fresh Mutton Curry Cut","price":650,"quantity":1,"weight":"500gm"},{"name":"Chicken Wings","price":380,"quantity":1,"weight":"500gm"}]', 525, 'processing', '2024-01-22T12:45:00')
        ]
        
        cursor.executemany('''
            INSERT INTO orders (orderid, firstName, lastName, phoneNo, email, address, city, pincode, deliveryType, paymentMethod, promocode, items, total, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_orders)
        
        print("✅ Sample data added successfully!")
    
    conn.commit()
    conn.close()

def run_server():
    # Initialize database with sample data
    init_database()
    
    # Get port from environment variable (Render requirement) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    server_address = ('0.0.0.0', port)  # Changed to 0.0.0.0 for Render
    httpd = HTTPServer(server_address, AMCMartHandler)
    
    print("=" * 70)
    print("🛒 AMCMart API Server Started!")
    print("=" * 70)
    print(f"🌐 Server running on port: {port}")
    print(f"🏥 Health check: /api/health")
    print(f"🌍 Environment: {'production' if os.environ.get('PORT') else 'development'}")
    print("")
    print("📦 PRODUCTS API:")
    print("   GET    /api/products          - Get all products")
    print("   GET    /api/products/{id}     - Get specific product")
    print("   POST   /api/products          - Create new product")
    print("   PUT    /api/products/{id}     - Update product")
    print("   DELETE /api/products/{id}     - Delete product")
    print("")
    print("📋 ORDERS API:")
    print("   GET    /api/orders            - Get all orders")
    print("   GET    /api/orders/{id}       - Get specific order")
    print("   POST   /api/orders            - Create new order")
    print("   PUT    /api/orders/{id}/status - Update order status")
    print("")
    print("👥 CUSTOMERS API:")
    print("   GET    /api/customers         - Get customer data from orders")
    print("")
    print("📊 DASHBOARD API:")
    print("   GET    /api/dashboard/stats   - Get dashboard statistics")
    print("")
    print("🎫 PROMO CODES API:")
    print("   GET    /api/promocodes        - Get all promo codes")
    print("   POST   /api/promocodes        - Create new promo code")
    print("   PUT    /api/promocodes/{id}   - Update promo code")
    print("   DELETE /api/promocodes/{id}   - Delete promo code")
    print("   POST   /api/promo/validate    - Validate promo code")
    print("=" * 70)
    print("📊 Database: amcmart.db")
    print("🎯 Sample Products: 8 products with realistic data")
    print("🛒 Sample Orders: 8 orders with different statuses")
    print("👥 Sample Customers: 8 unique customers")
    print("🎟️ Sample Promo Codes: 7 codes with different statuses")
    print("=" * 70)
    if not os.environ.get('PORT'):
        print("Press Ctrl+C to stop the server")
        print("=" * 70)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 AMCMart Server stopped!")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
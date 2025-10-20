from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import urllib.parse
from datetime import datetime
import random
import string
import os
import queue
import threading
import time
import sys

# ============ GLOBAL QUEUE FOR ORDERS ============
order_queue = queue.Queue()

class AMCMartHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{datetime.now().isoformat()}] {format % args}", file=sys.stderr)
        sys.stderr.flush()

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        print(f"📥 GET {self.path}")
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
        else:
            print(f"❌ GET path not matched: {self.path}")
            self.send_error(404)

    def do_POST(self):
        print(f"📤 POST {self.path}")
        if self.path == '/api/products':
            self.create_product()
        elif self.path == '/api/orders':
            self.create_order()
        elif self.path == '/api/promo/validate':
            self.validate_promo()
        elif self.path == '/api/promocodes':
            self.create_promocode()
        else:
            print(f"❌ POST path not matched: {self.path}")
            self.send_error(404)

    def do_PUT(self):
        print(f"🔄 PUT {self.path}")
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
            print(f"❌ PUT path not matched: {self.path}")
            self.send_error(404)

    def do_DELETE(self):
        print(f"🗑️  DELETE {self.path}")
        if self.path.startswith('/api/products/'):
            product_id = self.path.split('/')[-1]
            self.delete_product(product_id)
        elif self.path.startswith('/api/promocodes/'):
            promo_id = self.path.split('/')[-1]
            self.delete_promocode(promo_id)
        else:
            print(f"❌ DELETE path not matched: {self.path}")
            self.send_error(404)

    # ============ DASHBOARD STATS ENDPOINT ============
    
    def get_dashboard_stats(self):
        try:
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in get_dashboard_stats: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    # ============ CUSTOMERS ENDPOINT ============
    
    def get_customers(self):
        try:
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.cursor()
            
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
            print(f"❌ Error in get_customers: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    # ============ PRODUCTS ENDPOINTS ============
    
    def get_products(self):
        try:
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in get_products: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def get_product(self, product_id):
        try:
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in get_product: {str(e)}")
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
            
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
                data.get('image', '/api/placeholder/300/250')
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
            print(f"❌ Error in create_product: {str(e)}")
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
            
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in update_product: {str(e)}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def delete_product(self, product_id):
        try:
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in delete_product: {str(e)}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    # ============ ORDERS ENDPOINTS ============
    
    def create_order(self):
        """Create order and add to queue for processing"""
        try:
            print("📋 Starting create_order()")
            
            if 'Content-Length' not in self.headers:
                raise ValueError("Missing Content-Length header")
            
            content_length = int(self.headers['Content-Length'])
            print(f"   Content-Length: {content_length} bytes")
            
            if content_length == 0:
                raise ValueError("Request body is empty")
            
            post_data = self.rfile.read(content_length)
            print(f"   Raw data received: {len(post_data)} bytes")
            
            data = json.loads(post_data.decode('utf-8'))
            print(f"   ✅ JSON parsed successfully")
            
            # Generate order ID
            order_id = 'AMC' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            print(f"   Order ID: {order_id}")
            
            # Validate required fields
            required_fields = ['firstName', 'lastName', 'phoneNo', 'address', 'city', 'pincode', 'deliveryType', 'paymentMethod', 'items', 'total']
            missing_fields = []
            
            for field in required_fields:
                if field not in data or data.get(field) == '' or data.get(field) is None:
                    missing_fields.append(field)
                    print(f"   ❌ Missing/empty field: {field}")
                else:
                    print(f"   ✅ {field}: {str(data.get(field))[:50]}")
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
            print(f"   ✅ All validations passed")
            
            # ✅ ADD ORDER TO QUEUE (not directly to database)
            order_queue.put((order_id, data))
            print(f"   📝 Order {order_id} added to processing queue")
            print(f"   📊 Queue size: {order_queue.qsize()}")
            
            # Send immediate response to user
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
            response_json = json.dumps(response)
            self.wfile.write(response_json.encode())
            print(f"   ✅ Response sent to client")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {str(e)}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': f'Invalid JSON: {str(e)}'}
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as e:
            print(f"❌ Validation Error: {str(e)}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"❌ Unexpected Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': f'Server error: {str(e)}'}
            self.wfile.write(json.dumps(response).encode())

    def validate_promo(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            code = data.get('code', '').upper()
            
            # Check promo code in database
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in validate_promo: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def get_order(self, order_id):
        try:
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in get_order: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def get_all_orders(self):
        try:
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in get_all_orders: {str(e)}")
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
            
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in update_order_status: {str(e)}")
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
            
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in create_promocode: {str(e)}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def get_all_promocodes(self):
        try:
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in get_all_promocodes: {str(e)}")
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
            
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in update_promocode: {str(e)}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def delete_promocode(self, promo_id):
        try:
            conn = sqlite3.connect('amcmart.db', timeout=20.0)
            conn.execute('PRAGMA journal_mode=WAL')
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
            print(f"❌ Error in delete_promocode: {str(e)}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode())

    def health_check(self):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'message': 'AMCMart API is running!',
                'timestamp': datetime.now().isoformat(),
                'database': 'amcmart.db',
                'queue_size': order_queue.qsize()
            }
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            print(f"❌ Error in health_check: {str(e)}")


# ============ BACKGROUND WORKER THREAD ============

def process_orders_worker():
    """Background worker thread to process orders sequentially from queue"""
    print("🔄 Order processing worker started")
    
    while True:
        try:
            # Get order from queue (blocks until one is available)
            order_data = order_queue.get()
            
            if order_data is None:  # Shutdown signal
                print("🛑 Order processing worker shutting down...")
                break
            
            order_id, data = order_data
            print(f"\n📦 Processing order from queue: {order_id}")
            print(f"   Queue size: {order_queue.qsize()}")
            
            try:
                # Save to database
                save_order_to_db(order_id, data)
                print(f"✅ Order {order_id} processed successfully!")
                
            except Exception as e:
                print(f"❌ Failed to process order {order_id}: {str(e)}")
            
            finally:
                order_queue.task_done()
        
        except Exception as e:
            print(f"❌ Worker thread error: {str(e)}")
            import traceback
            traceback.print_exc()


def save_order_to_db(order_id, data):
    """Save order to database (called from worker thread)"""
    conn = None
    try:
        conn = sqlite3.connect('amcmart.db', timeout=20.0)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        cursor = conn.cursor()
        
        print(f"   💾 Saving to database...")
        
        # Insert order
        cursor.execute('''
            INSERT INTO orders (orderid, firstName, lastName, phoneNo, email, address, city, pincode, deliveryType, paymentMethod, promocode, items, total, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id,
            data.get('firstName'),
            data.get('lastName'),
            data.get('phoneNo'),
            data.get('email', ''),
            data.get('address'),
            data.get('city'),
            data.get('pincode'),
            data.get('deliveryType'),
            data.get('paymentMethod'),
            data.get('promocode', ''),
            data.get('items'),
            data.get('total'),
            'processing',
            datetime.now().isoformat()
        ))
        
        # Update promo code if provided
        if data.get('promocode'):
            print(f"   🎫 Marking promo code as used: {data.get('promocode')}")
            cursor.execute('''
                UPDATE promocodes SET used = 'yes' WHERE code = ?
            ''', (data.get('promocode').upper(),))
        
        conn.commit()
        print(f"   ✅ Order saved to database successfully!")
        
    except sqlite3.OperationalError as e:
        if 'database is locked' in str(e):
            print(f"   ⚠️  Database locked: {str(e)}")
            raise Exception(f'Database is busy. Order will be retried.')
        raise
    except Exception as e:
        print(f"   ❌ Database error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


# ============ DATABASE INITIALIZATION ============

def init_database():
    """Initialize database with tables and enable WAL mode"""
    try:
        print("🗄️  Initializing database...")
        
        conn = sqlite3.connect('amcmart.db', timeout=20.0)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        cursor = conn.cursor()
        
        # Create products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                productname TEXT NOT NULL,
                category TEXT NOT NULL,
                price_1kg REAL NOT NULL,
                price_500gm REAL NOT NULL,
                stock_status TEXT DEFAULT 'in-stock',
                image TEXT
            )
        ''')
        print("   ✅ Products table ready")
        
        # Create orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                orderid TEXT PRIMARY KEY,
                firstName TEXT NOT NULL,
                lastName TEXT NOT NULL,
                phoneNo TEXT NOT NULL,
                email TEXT,
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
        print("   ✅ Orders table ready")
        
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
        print("   ✅ Promocodes table ready")
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully!\n")
        
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        raise


# ============ SERVER STARTUP ============

def run_server():
    """Run the HTTP server with worker thread"""
    try:
        # Initialize database
        init_database()
        
        # ✅ Start order processing worker thread (daemon = stops when main thread stops)
        worker_thread = threading.Thread(target=process_orders_worker, daemon=True)
        worker_thread.start()
        print("✅ Order processing worker thread started\n")
        
        # Get port from environment or default to 5000
        port = int(os.environ.get('PORT', 5000))
        
        # Create HTTP server
        server_address = ('0.0.0.0', port)
        httpd = HTTPServer(server_address, AMCMartHandler)
        
        print("=" * 80)
        print("🛒 AMCMart API Server Started!")
        print("=" * 80)
        print(f"🌐 Server: http://0.0.0.0:{port}")
        print(f"🕐 Started at: {datetime.now().isoformat()}")
        print("=" * 80)
        print("\n📦 API ENDPOINTS:\n")
        print("   GET    /api/products          - Get all products")
        print("   POST   /api/products          - Create product")
        print("   GET    /api/orders            - Get all orders")
        print("   POST   /api/orders            - Create order ✨ (queued)")
        print("   POST   /api/promo/validate    - Validate promo")
        print("   GET    /api/health            - Health check")
        print("\n" + "=" * 80)
        print("🔄 Order Processing: Sequential queue-based (handles concurrent requests)")
        print("📊 Database Mode: WAL (Write-Ahead Logging)")
        print("=" * 80)
        print("Press Ctrl+C to stop\n")
        
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        httpd.server_close()
        # Queue shutdown signal
        order_queue.put(None)
    except Exception as e:
        print(f"\n❌ Server error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    run_server()

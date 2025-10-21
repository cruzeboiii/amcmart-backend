import os
import json
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import uuid
import threading

# Database file path
DATABASE_FILE = 'amcmart.db'

class DatabaseManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return None
    
    def database_exists(self):
        """Check if database file exists"""
        exists = os.path.exists(DATABASE_FILE)
        size = os.path.getsize(DATABASE_FILE) if exists else 0
        return exists, size
    
    def init_database(self):
        """Initialize database and create tables"""
        try:
            conn = self.get_connection()
            if not conn:
                print("❌ Failed to create database")
                return False
            
            cursor = conn.cursor()
            
            # Products table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    productname TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price_1kg INTEGER,
                    price_500gm INTEGER,
                    stock_status TEXT DEFAULT 'in-stock',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    orderid TEXT UNIQUE NOT NULL,
                    firstName TEXT,
                    lastName TEXT,
                    phoneNo TEXT,
                    email TEXT,
                    address TEXT,
                    city TEXT,
                    pincode TEXT,
                    deliveryType TEXT,
                    paymentMethod TEXT,
                    items TEXT,
                    total INTEGER,
                    promocode TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Promo codes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promocodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    discount INTEGER,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Customers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firstName TEXT,
                    lastName TEXT,
                    phoneNo TEXT,
                    email TEXT,
                    city TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            exists, size = self.database_exists()
            print(f"✅ Database initialized: {DATABASE_FILE} ({size} bytes)")
            return True
        
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            return False
    
    def execute_query(self, query, params=()):
        """Execute query with thread safety"""
        try:
            with self.lock:
                conn = self.get_connection()
                if not conn:
                    return None
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor
        except Exception as e:
            print(f"❌ Query error: {e}")
            return None
    
    def fetch_all(self, query, params=()):
        """Fetch all results"""
        try:
            with self.lock:
                conn = self.get_connection()
                if not conn:
                    return []
                cursor = conn.cursor()
                cursor.execute(query, params)
                results = cursor.fetchall()
                conn.close()
                return [dict(row) for row in results]
        except Exception as e:
            print(f"❌ Fetch error: {e}")
            return []
    
    def fetch_one(self, query, params=()):
        """Fetch single result"""
        try:
            with self.lock:
                conn = self.get_connection()
                if not conn:
                    return None
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.close()
                return dict(result) if result else None
        except Exception as e:
            print(f"❌ Fetch one error: {e}")
            return None
    
    def get_stats(self):
        """Get database statistics"""
        exists, size = self.database_exists()
        product_count = 0
        order_count = 0
        
        if exists:
            products = self.fetch_all('SELECT COUNT(*) as count FROM products')
            orders = self.fetch_all('SELECT COUNT(*) as count FROM orders')
            
            product_count = products[0].get('count', 0) if products else 0
            order_count = orders[0].get('count', 0) if orders else 0
        
        return {
            'exists': exists,
            'size_bytes': size,
            'size_mb': round(size / (1024 * 1024), 2) if size > 0 else 0,
            'products': product_count,
            'orders': order_count
        }

# Global database instance
db = DatabaseManager()

class APIHandler(BaseHTTPRequestHandler):
    
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/api/health':
            stats = db.get_stats()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            response = {
                "success": True,
                "message": "AMCMart API is running!",
                "timestamp": datetime.now().isoformat(),
                "database": "SQLite",
                "database_file": DATABASE_FILE,
                "database_exists": stats['exists'],
                "database_size_mb": stats['size_mb'],
                "products_count": stats['products'],
                "orders_count": stats['orders'],
                "queue_size": 0
            }
            self.wfile.write(json.dumps(response, default=str).encode())
        
        elif path == '/api/products':
            products = db.fetch_all('SELECT * FROM products ORDER BY id DESC')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            response = {
                "success": True,
                "data": products,
                "count": len(products)
            }
            self.wfile.write(json.dumps(response, default=str).encode())
        
        elif path == '/api/orders':
            orders = db.fetch_all('SELECT * FROM orders ORDER BY created_at DESC')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            response = {
                "success": True,
                "data": orders,
                "count": len(orders)
            }
            self.wfile.write(json.dumps(response, default=str).encode())
        
        elif path == '/api/customers':
            customers = db.fetch_all(
                'SELECT DISTINCT firstName, lastName, phoneNo, email, city FROM orders ORDER BY id DESC'
            )
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            response = {
                "success": True,
                "data": customers,
                "count": len(customers)
            }
            self.wfile.write(json.dumps(response, default=str).encode())
        
        elif path == '/api/dashboard/stats':
            stats = db.get_stats()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            orders = db.fetch_all('SELECT * FROM orders')
            total_revenue = sum(int(o.get('total', 0)) for o in orders)
            
            response = {
                "success": True,
                "data": {
                    "total_orders": stats['orders'],
                    "total_revenue": total_revenue,
                    "total_customers": len(db.fetch_all('SELECT DISTINCT phoneNo FROM orders')),
                    "pending_orders": len(db.fetch_all('SELECT * FROM orders WHERE status = ?', ('pending',))),
                    "database_size_mb": stats['size_mb'],
                    "database_exists": stats['exists']
                }
            }
            self.wfile.write(json.dumps(response, default=str).encode())
        
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": "Endpoint not found"}).encode())
    
    def do_POST(self):
        path = urlparse(self.path).path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == '/api/products':
            try:
                productname = data.get('productname')
                category = data.get('category')
                price_1kg = data.get('price_1kg')
                price_500gm = data.get('price_500gm')
                stock_status = data.get('stock_status', 'in-stock')
                
                cursor = db.execute_query(
                    'INSERT INTO products (productname, category, price_1kg, price_500gm, stock_status) VALUES (?, ?, ?, ?, ?)',
                    (productname, category, price_1kg, price_500gm, stock_status)
                )
                
                if cursor:
                    product_id = cursor.lastrowid
                    
                    self.send_response(201)
                    self.send_header('Content-Type', 'application/json')
                    self._set_cors_headers()
                    self.end_headers()
                    response = {
                        "success": True,
                        "data": {
                            "id": product_id,
                            "message": f"Product {productname} created successfully!"
                        }
                    }
                    print(f"✅ Product created: {productname} (ID: {product_id})")
                    self.wfile.write(json.dumps(response).encode())
                else:
                    raise Exception("Failed to insert product")
            
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        
        elif path == '/api/orders':
            try:
                order_id = f"AMC{uuid.uuid4().hex[:8].upper()}"
                
                cursor = db.execute_query(
                    '''INSERT INTO orders 
                    (orderid, firstName, lastName, phoneNo, email, address, city, pincode, 
                     deliveryType, paymentMethod, items, total, promocode, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
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
                        data.get('items'),
                        data.get('total'),
                        data.get('promocode', ''),
                        'pending'
                    )
                )
                
                if cursor:
                    self.send_response(201)
                    self.send_header('Content-Type', 'application/json')
                    self._set_cors_headers()
                    self.end_headers()
                    response = {
                        "success": True,
                        "data": {
                            "order_id": order_id,
                            "message": "Order placed successfully!",
                            "customer_name": f"{data.get('firstName')} {data.get('lastName')}"
                        }
                    }
                    print(f"✅ Order created: {order_id}")
                    self.wfile.write(json.dumps(response).encode())
                else:
                    raise Exception("Failed to create order")
            
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        
        elif path == '/api/promocodes':
            try:
                cursor = db.execute_query(
                    'INSERT INTO promocodes (code, discount, status) VALUES (?, ?, ?)',
                    (data.get('code'), data.get('discount'), data.get('status', 'active'))
                )
                
                if cursor:
                    self.send_response(201)
                    self.send_header('Content-Type', 'application/json')
                    self._set_cors_headers()
                    self.end_headers()
                    response = {
                        "success": True,
                        "data": {"message": "Promo code created successfully!"}
                    }
                    print(f"✅ Promo code created: {data.get('code')}")
                    self.wfile.write(json.dumps(response).encode())
            
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        
        elif path == '/api/promo/validate':
            try:
                code = data.get('code')
                promo = db.fetch_one('SELECT * FROM promocodes WHERE code = ? AND status = ?', (code, 'active'))
                
                if promo:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self._set_cors_headers()
                    self.end_headers()
                    response = {
                        "success": True,
                        "data": {
                            "code": promo['code'],
                            "discount": promo['discount'],
                            "message": f"Promo code applied! ₹{promo['discount']} discount"
                        }
                    }
                    self.wfile.write(json.dumps(response, default=str).encode())
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self._set_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "Invalid promo code"}).encode())
            
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

def run_server(port=5000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, APIHandler)
    print(f'🚀 Server running on port {port}')
    print(f'📊 API Base URL: http://localhost:{port}/api')
    print(f'💾 Database: {DATABASE_FILE}')
    httpd.serve_forever()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    run_server(port)

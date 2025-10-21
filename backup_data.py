import sqlite3
import json
import os
from datetime import datetime

DATABASE_FILE = 'amcmart.db'

def backup_database():
    """Backup all data to JSON files"""
    
    if not os.path.exists(DATABASE_FILE):
        print(f"❌ Database file '{DATABASE_FILE}' not found!")
        return False
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Create backup directory
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Generate timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        # Backup products
        cursor.execute('SELECT * FROM products')
        products = [dict(row) for row in cursor.fetchall()]
        products_file = f'{backup_dir}/products_backup_{timestamp}.json'
        with open(products_file, 'w') as f:
            json.dump(products, f, indent=2, default=str)
        print(f"✅ Products: {len(products)} items → {products_file}")
        
        # Backup orders
        cursor.execute('SELECT * FROM orders')
        orders = [dict(row) for row in cursor.fetchall()]
        orders_file = f'{backup_dir}/orders_backup_{timestamp}.json'
        with open(orders_file, 'w') as f:
            json.dump(orders, f, indent=2, default=str)
        print(f"✅ Orders: {len(orders)} items → {orders_file}")
        
        # Backup promo codes
        cursor.execute('SELECT * FROM promocodes')
        promos = [dict(row) for row in cursor.fetchall()]
        promos_file = f'{backup_dir}/promocodes_backup_{timestamp}.json'
        with open(promos_file, 'w') as f:
            json.dump(promos, f, indent=2, default=str)
        print(f"✅ Promos: {len(promos)} items → {promos_file}")
        
        # Create summary
        summary = {
            'timestamp': timestamp,
            'total_products': len(products),
            'total_orders': len(orders),
            'total_promocodes': len(promos)
        }
        summary_file = f'{backup_dir}/backup_summary_{timestamp}.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        conn.close()
        print(f"✅ Backup complete! Summary: {summary}")
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def restore_database(backup_dir='backups'):
    """Restore data from latest JSON files"""
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        import glob
        product_files = sorted(glob.glob(f'{backup_dir}/products_backup_*.json'))
        order_files = sorted(glob.glob(f'{backup_dir}/orders_backup_*.json'))
        promo_files = sorted(glob.glob(f'{backup_dir}/promocodes_backup_*.json'))
        
        if not product_files and not order_files:
            print("❌ No backup files found!")
            return False
        
        # Restore products
        if product_files:
            latest_products = product_files[-1]
            with open(latest_products, 'r') as f:
                products = json.load(f)
            
            cursor.execute('DELETE FROM products')
            for product in products:
                cursor.execute(
                    'INSERT INTO products (productname, category, price_1kg, price_500gm, stock_status) VALUES (?, ?, ?, ?, ?)',
                    (product['productname'], product['category'], product['price_1kg'], product['price_500gm'], product['stock_status'])
                )
            print(f"✅ Restored {len(products)} products from {os.path.basename(latest_products)}")
        
        # Restore orders
        if order_files:
            latest_orders = order_files[-1]
            with open(latest_orders, 'r') as f:
                orders = json.load(f)
            
            cursor.execute('DELETE FROM orders')
            for order in orders:
                cursor.execute(
                    '''INSERT INTO orders 
                    (orderid, firstName, lastName, phoneNo, email, address, city, pincode, 
                     deliveryType, paymentMethod, items, total, promocode, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        order['orderid'], order['firstName'], order['lastName'], order['phoneNo'],
                        order['email'], order['address'], order['city'], order['pincode'],
                        order['deliveryType'], order['paymentMethod'], order['items'],
                        order['total'], order['promocode'], order['status']
                    )
                )
            print(f"✅ Restored {len(orders)} orders from {os.path.basename(latest_orders)}")
        
        # Restore promo codes
        if promo_files:
            latest_promos = promo_files[-1]
            with open(latest_promos, 'r') as f:
                promos = json.load(f)
            
            cursor.execute('DELETE FROM promocodes')
            for promo in promos:
                cursor.execute(
                    'INSERT INTO promocodes (code, discount, status) VALUES (?, ?, ?)',
                    (promo['code'], promo['discount'], promo['status'])
                )
            print(f"✅ Restored {len(promos)} promo codes from {os.path.basename(latest_promos)}")
        
        conn.commit()
        conn.close()
        print(f"✅ Restore complete!")
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        print("\n🔄 RESTORING FROM BACKUP...\n")
        restore_database()
    else:
        print("\n💾 CREATING BACKUP...\n")
        backup_database()

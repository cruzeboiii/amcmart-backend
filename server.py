import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import uuid
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


# ============ DATABASE CONFIGURATION ============
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable is not set!")
else:
    print(f"✅ Database URL configured: {DATABASE_URL[:50]}...")


# ============ EMAIL CONFIGURATION ============
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

if ADMIN_EMAIL and SENDER_EMAIL:
    print(f"✅ Email configured")
    print(f"   SENDER: {SENDER_EMAIL}")
    print(f"   ADMIN: {ADMIN_EMAIL}")
else:
    print("⚠️ Email not configured")



class EmailService:
    """Handle email notifications using SendGrid"""
    
    @staticmethod
    def send_order_notification(order_data):
        """Send order notification email to admin"""
        try:
            print(f"\n{'='*60}")
            print(f"📧 SENDGRID EMAIL SERVICE STARTING")
            print(f"{'='*60}")
            
            # Get credentials from environment
            sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
            sender_email = os.getenv('SENDER_EMAIL')
            admin_email = os.getenv('ADMIN_EMAIL')
            
            if not sendgrid_api_key or not sender_email or not admin_email:
                print(f"❌ SENDGRID NOT CONFIGURED")
                print(f"   SENDGRID_API_KEY: {'SET' if sendgrid_api_key else 'NOT SET'}")
                print(f"   SENDER_EMAIL: {'SET' if sender_email else 'NOT SET'}")
                print(f"   ADMIN_EMAIL: {'SET' if admin_email else 'NOT SET'}")
                return False
            
            print(f"✅ SendGrid credentials found")
            print(f"   SENDGRID_API_KEY: {sendgrid_api_key[:20]}...")
            print(f"   SENDER_EMAIL: {sender_email}")
            print(f"   ADMIN_EMAIL (Receiver): {admin_email}")
            
            # Calculate total items
            items_list = ""
            try:
                items = json.loads(order_data.get('items', '[]'))
                for item in items:
                    items_list += f"<li>{item.get('name')} ({item.get('weight')}) x {item.get('quantity')} = ₹{item.get('unitPrice') * item.get('quantity')}</li>"
            except:
                items_list = f"<li>{order_data.get('items')}</li>"
            
            # HTML email template
            html = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px; }}
                        .header {{ background: #d32f2f; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
                        .header h2 {{ margin: 0; }}
                        .content {{ background: white; padding: 20px; }}
                        .section {{ margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
                        .section h3 {{ color: #d32f2f; margin-top: 0; }}
                        .info-row {{ display: flex; justify-content: space-between; margin: 8px 0; }}
                        .label {{ font-weight: bold; color: #666; }}
                        .value {{ text-align: right; }}
                        .items-list {{ list-style: none; padding: 0; }}
                        .items-list li {{ padding: 8px; background: #f5f5f5; margin: 5px 0; border-radius: 4px; }}
                        .total {{ font-size: 1.3em; font-weight: bold; color: #d32f2f; text-align: right; padding: 15px 0; }}
                        .status {{ display: inline-block; padding: 8px 12px; background: #fff3e0; color: #e65100; border-radius: 4px; font-weight: bold; }}
                        .footer {{ text-align: center; color: #999; font-size: 0.9em; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>📦 New Order Received!</h2>
                        </div>
                        
                        <div class="content">
                            <div class="section">
                                <h3>Order Information</h3>
                                <div class="info-row">
                                    <span class="label">Order ID:</span>
                                    <span class="value"><strong>{order_data['orderid']}</strong></span>
                                </div>
                                <div class="info-row">
                                    <span class="label">Date & Time:</span>
                                    <span class="value">{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</span>
                                </div>
                                <div class="info-row">
                                    <span class="label">Status:</span>
                                    <span class="value"><span class="status">PENDING</span></span>
                                </div>
                            </div>
                            
                            <div class="section">
                                <h3>Customer Information</h3>
                                <div class="info-row">
                                    <span class="label">Name:</span>
                                    <span class="value">{order_data.get('firstName')} {order_data.get('lastName')}</span>
                                </div>
                                <div class="info-row">
                                    <span class="label">Email:</span>
                                    <span class="value">{order_data.get('email', 'N/A')}</span>
                                </div>
                                <div class="info-row">
                                    <span class="label">Phone:</span>
                                    <span class="value">{order_data.get('phoneNo')}</span>
                                </div>
                                <div class="info-row">
                                    <span class="label">City:</span>
                                    <span class="value">{order_data.get('city')}</span>
                                </div>
                            </div>
                            
                            <div class="section">
                                <h3>Delivery Address</h3>
                                <div style="background: #f5f5f5; padding: 12px; border-radius: 4px;">
                                    <p style="margin: 0;">{order_data.get('address')}</p>
                                    <p style="margin: 8px 0 0 0;"><strong>{order_data.get('city')} - {order_data.get('pincode')}</strong></p>
                                </div>
                            </div>
                            
                            <div class="section">
                                <h3>Order Items</h3>
                                <ul class="items-list">
                                    {items_list}
                                </ul>
                            </div>
                            
                            <div class="section">
                                <h3>Order Summary</h3>
                                <div class="info-row">
                                    <span class="label">Subtotal:</span>
                                    <span class="value">₹{order_data.get('total', 0)}</span>
                                </div>
                                <div class="info-row">
                                    <span class="label">Delivery Type:</span>
                                    <span class="value">{order_data.get('deliveryType', 'Standard')}</span>
                                </div>
                                <div class="info-row">
                                    <span class="label">Payment Method:</span>
                                    <span class="value">{order_data.get('paymentMethod', 'N/A')}</span>
                                </div>
                                {f'<div class="info-row"><span class="label">Promo Code:</span><span class="value">{order_data.get("promocode")}</span></div>' if order_data.get('promocode') else ''}
                                <div class="total">
                                    Total Amount: ₹{order_data.get('total', 0)}
                                </div>
                            </div>
                            
                            <div class="footer">
                                <p>This is an automated email from AMCMart Admin Panel.</p>
                                <p>© 2025 AMCMart. All rights reserved.</p>
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            # Create SendGrid client
            sg = SendGridAPIClient(sendgrid_api_key)
            
            # Send email FROM sender_email TO admin_email
            print(f"📤 Sending email...")
            print(f"   FROM: {sender_email}")
            print(f"   TO: {admin_email}")
            
            try:
                message = Mail(
                    from_email=(sender_email, "AMCMart Orders"),
                    to_emails=admin_email,
                    subject=f"🎉 New Order - {order_data['orderid']}",
                    html_content=html
                )
                response = sg.send(message)
                print(f"✅ Email sent successfully")
                print(f"   Status Code: {response.status_code}")
                print(f"   Order ID: {order_data['orderid']}")
                print(f"{'='*60}")
                print(f"✅ EMAIL SENT SUCCESSFULLY")
                print(f"{'='*60}\n")
                return True
            
            except Exception as e:
                print(f"❌ Failed to send email: {e}")
                raise
        
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ EMAIL SERVICE ERROR")
            print(f"{'='*60}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print(f"{'='*60}\n")
            return False

# class EmailService:
#     """Handle email notifications using SendGrid"""
    
#     @staticmethod
#     def send_order_notification(order_data):
#         """Send order notification email to admin"""
#         try:
#             print(f"\n{'='*60}")
#             print(f"📧 SENDGRID EMAIL SERVICE STARTING")
#             print(f"{'='*60}")
            
#             # Check if SendGrid API key is configured
#             sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
#             if not sendgrid_api_key or not ADMIN_EMAIL:
#                 print(f"❌ SENDGRID NOT CONFIGURED")
#                 print(f"   SENDGRID_API_KEY: {'SET' if sendgrid_api_key else 'NOT SET'}")
#                 print(f"   ADMIN_EMAIL: {ADMIN_EMAIL}")
#                 return False
            
#             print(f"✅ SendGrid credentials found")
#             print(f"   SENDGRID_API_KEY: {sendgrid_api_key[:20]}...")
#             print(f"   ADMIN_EMAIL: {ADMIN_EMAIL}")
            
#             # Calculate total items
#             items_list = ""
#             try:
#                 items = json.loads(order_data.get('items', '[]'))
#                 for item in items:
#                     items_list += f"<li>{item.get('name')} ({item.get('weight')}) x {item.get('quantity')} = ₹{item.get('unitPrice') * item.get('quantity')}</li>"
#             except:
#                 items_list = f"<li>{order_data.get('items')}</li>"
            
#             # HTML email template
#             html = f"""
#             <html>
#                 <head>
#                     <style>
#                         body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
#                         .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px; }}
#                         .header {{ background: #d32f2f; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
#                         .header h2 {{ margin: 0; }}
#                         .content {{ background: white; padding: 20px; }}
#                         .section {{ margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
#                         .section h3 {{ color: #d32f2f; margin-top: 0; }}
#                         .info-row {{ display: flex; justify-content: space-between; margin: 8px 0; }}
#                         .label {{ font-weight: bold; color: #666; }}
#                         .value {{ text-align: right; }}
#                         .items-list {{ list-style: none; padding: 0; }}
#                         .items-list li {{ padding: 8px; background: #f5f5f5; margin: 5px 0; border-radius: 4px; }}
#                         .total {{ font-size: 1.3em; font-weight: bold; color: #d32f2f; text-align: right; padding: 15px 0; }}
#                         .status {{ display: inline-block; padding: 8px 12px; background: #fff3e0; color: #e65100; border-radius: 4px; font-weight: bold; }}
#                         .footer {{ text-align: center; color: #999; font-size: 0.9em; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px; }}
#                     </style>
#                 </head>
#                 <body>
#                     <div class="container">
#                         <div class="header">
#                             <h2>📦 New Order Received!</h2>
#                         </div>
                        
#                         <div class="content">
#                             <div class="section">
#                                 <h3>Order Information</h3>
#                                 <div class="info-row">
#                                     <span class="label">Order ID:</span>
#                                     <span class="value"><strong>{order_data['orderid']}</strong></span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Date & Time:</span>
#                                     <span class="value">{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Status:</span>
#                                     <span class="value"><span class="status">PENDING</span></span>
#                                 </div>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Customer Information</h3>
#                                 <div class="info-row">
#                                     <span class="label">Name:</span>
#                                     <span class="value">{order_data.get('firstName')} {order_data.get('lastName')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Email:</span>
#                                     <span class="value">{order_data.get('email')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Phone:</span>
#                                     <span class="value">{order_data.get('phoneNo')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">City:</span>
#                                     <span class="value">{order_data.get('city')}</span>
#                                 </div>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Delivery Address</h3>
#                                 <div style="background: #f5f5f5; padding: 12px; border-radius: 4px;">
#                                     <p style="margin: 0;">{order_data.get('address')}</p>
#                                     <p style="margin: 8px 0 0 0;"><strong>{order_data.get('city')} - {order_data.get('pincode')}</strong></p>
#                                 </div>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Order Items</h3>
#                                 <ul class="items-list">
#                                     {items_list}
#                                 </ul>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Order Summary</h3>
#                                 <div class="info-row">
#                                     <span class="label">Delivery Type:</span>
#                                     <span class="value">{order_data.get('deliveryType', 'Standard')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Payment Method:</span>
#                                     <span class="value">{order_data.get('paymentMethod', 'N/A')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Promo Code:</span>
#                                     <span class="value">{order_data.get('promocode') or 'None'}</span>
#                                 </div>
#                                 <div class="total">
#                                     Total Amount: ₹{order_data.get('total', 0)}
#                                 </div>
#                             </div>
                            
#                             <div class="footer">
#                                 <p>This is an automated email from AMCMart Admin Panel.</p>
#                                 <p>Login to your admin panel to update order status.</p>
#                             </div>
#                         </div>
#                     </div>
#                 </body>
#             </html>
#             """
            
#             # Create email
#             print(f"✅ Creating email message")
#             message = Mail(
#                 from_email=ADMIN_EMAIL,
#                 to_emails=ADMIN_EMAIL,
#                 subject=f"🎉 New Order Received - {order_data['orderid']}",
#                 html_content=html
#             )
            
#             # Send via SendGrid
#             print(f"📤 Sending via SendGrid...")
#             sg = SendGridAPIClient(sendgrid_api_key)
#             response = sg.send(message)
            
#             print(f"✅ Email sent successfully")
#             print(f"   Status Code: {response.status_code}")
#             print(f"   Order ID: {order_data['orderid']}")
#             print(f"{'='*60}")
#             print(f"✅ EMAIL SENT SUCCESSFULLY")
#             print(f"{'='*60}\n")
            
#             return True
        
#         except Exception as e:
#             print(f"\n{'='*60}")
#             print(f"❌ EMAIL ERROR")
#             print(f"{'='*60}")
#             print(f"Error: {e}")
#             import traceback
#             traceback.print_exc()
#             print(f"{'='*60}\n")
#             return False
# class EmailService:
#     """Handle email notifications"""
    
#     @staticmethod
#     def send_order_notification(order_data):
#         """Send order notification email to admin"""
#         try:
#             msg = MIMEMultipart('alternative')
#             msg['Subject'] = f"🎉 New Order Received - {order_data['orderid']}"
#             msg['From'] = ADMIN_EMAIL
#             msg['To'] = ADMIN_EMAIL
            
#             items_list = ""
#             try:
#                 items = json.loads(order_data.get('items', '[]'))
#                 for item in items:
#                     items_list += f"<li>{item.get('name')} ({item.get('weight')}) x {item.get('quantity')} = ₹{item.get('unitPrice') * item.get('quantity')}</li>"
#             except:
#                 items_list = f"<li>{order_data.get('items')}</li>"
            
#             html = f"""
#             <html>
#                 <head>
#                     <style>
#                         body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
#                         .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px; }}
#                         .header {{ background: #d32f2f; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
#                         .header h2 {{ margin: 0; }}
#                         .content {{ background: white; padding: 20px; }}
#                         .section {{ margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
#                         .section h3 {{ color: #d32f2f; margin-top: 0; }}
#                         .info-row {{ display: flex; justify-content: space-between; margin: 8px 0; }}
#                         .label {{ font-weight: bold; color: #666; }}
#                         .value {{ text-align: right; }}
#                         .items-list {{ list-style: none; padding: 0; }}
#                         .items-list li {{ padding: 8px; background: #f5f5f5; margin: 5px 0; border-radius: 4px; }}
#                         .total {{ font-size: 1.3em; font-weight: bold; color: #d32f2f; text-align: right; padding: 15px 0; }}
#                         .status {{ display: inline-block; padding: 8px 12px; background: #fff3e0; color: #e65100; border-radius: 4px; font-weight: bold; }}
#                         .footer {{ text-align: center; color: #999; font-size: 0.9em; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px; }}
#                     </style>
#                 </head>
#                 <body>
#                     <div class="container">
#                         <div class="header">
#                             <h2>📦 New Order Received!</h2>
#                         </div>
                        
#                         <div class="content">
#                             <div class="section">
#                                 <h3>Order Information</h3>
#                                 <div class="info-row">
#                                     <span class="label">Order ID:</span>
#                                     <span class="value"><strong>{order_data['orderid']}</strong></span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Date & Time:</span>
#                                     <span class="value">{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Status:</span>
#                                     <span class="value"><span class="status">PENDING</span></span>
#                                 </div>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Customer Information</h3>
#                                 <div class="info-row">
#                                     <span class="label">Name:</span>
#                                     <span class="value">{order_data.get('firstName')} {order_data.get('lastName')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Email:</span>
#                                     <span class="value">{order_data.get('email')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Phone:</span>
#                                     <span class="value">{order_data.get('phoneNo')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">City:</span>
#                                     <span class="value">{order_data.get('city')}</span>
#                                 </div>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Delivery Address</h3>
#                                 <div style="background: #f5f5f5; padding: 12px; border-radius: 4px;">
#                                     <p style="margin: 0;">{order_data.get('address')}</p>
#                                     <p style="margin: 8px 0 0 0;"><strong>{order_data.get('city')} - {order_data.get('pincode')}</strong></p>
#                                 </div>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Order Items</h3>
#                                 <ul class="items-list">
#                                     {items_list}
#                                 </ul>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Order Summary</h3>
#                                 <div class="info-row">
#                                     <span class="label">Delivery Type:</span>
#                                     <span class="value">{order_data.get('deliveryType', 'Standard')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Payment Method:</span>
#                                     <span class="value">{order_data.get('paymentMethod', 'N/A')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Promo Code:</span>
#                                     <span class="value">{order_data.get('promocode') or 'None'}</span>
#                                 </div>
#                                 <div class="total">
#                                     Total Amount: ₹{order_data.get('total', 0)}
#                                 </div>
#                             </div>
                            
#                             <div class="footer">
#                                 <p>This is an automated email from AMCMart Admin Panel.</p>
#                                 <p>Login to your admin panel to update order status: <a href="#">Admin Panel</a></p>
#                             </div>
#                         </div>
#                     </div>
#                 </body>
#             </html>
#             """
            
#             msg.attach(MIMEText(html, 'html'))
            
#             server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
#             server.starttls()
#             server.login(ADMIN_EMAIL, EMAIL_PASSWORD)
#             server.send_message(msg)
#             server.quit()
            
#             print(f"✅ Email sent to {ADMIN_EMAIL} for order {order_data['orderid']}")
#             return True
        
#         except Exception as e:
#             print(f"❌ Email error: {e}")
#             return False


# class EmailService:
#     """Handle email notifications"""
    
#     @staticmethod
#     def send_order_notification(order_data):
#         """Send order notification email to admin"""
#         try:
#             print(f"\n{'='*60}")
#             print(f"📧 EMAIL SERVICE STARTING")
#             print(f"{'='*60}")
            
#             # Check if email is configured
#             if not ADMIN_EMAIL or not EMAIL_PASSWORD:
#                 print(f"❌ EMAIL NOT CONFIGURED")
#                 print(f"   ADMIN_EMAIL: {ADMIN_EMAIL}")
#                 print(f"   EMAIL_PASSWORD: {'SET' if EMAIL_PASSWORD else 'NOT SET'}")
#                 return False
            
#             print(f"✅ Email credentials found")
#             print(f"   ADMIN_EMAIL: {ADMIN_EMAIL}")
#             print(f"   EMAIL_PASSWORD: {'*' * len(EMAIL_PASSWORD)}")
            
#             # Create email message
#             msg = MIMEMultipart('alternative')
#             msg['Subject'] = f"🎉 New Order Received - {order_data['orderid']}"
#             msg['From'] = ADMIN_EMAIL
#             msg['To'] = ADMIN_EMAIL
            
#             print(f"✅ Email message created")
#             print(f"   Subject: {msg['Subject']}")
#             print(f"   From: {msg['From']}")
#             print(f"   To: {msg['To']}")
            
#             # Calculate total items
#             items_list = ""
#             try:
#                 items = json.loads(order_data.get('items', '[]'))
#                 for item in items:
#                     items_list += f"<li>{item.get('name')} ({item.get('weight')}) x {item.get('quantity')} = ₹{item.get('unitPrice') * item.get('quantity')}</li>"
#             except:
#                 items_list = f"<li>{order_data.get('items')}</li>"
            
#             # HTML email template
#             html = f"""
#             <html>
#                 <head>
#                     <style>
#                         body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
#                         .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px; }}
#                         .header {{ background: #d32f2f; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
#                         .header h2 {{ margin: 0; }}
#                         .content {{ background: white; padding: 20px; }}
#                         .section {{ margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
#                         .section h3 {{ color: #d32f2f; margin-top: 0; }}
#                         .info-row {{ display: flex; justify-content: space-between; margin: 8px 0; }}
#                         .label {{ font-weight: bold; color: #666; }}
#                         .value {{ text-align: right; }}
#                         .items-list {{ list-style: none; padding: 0; }}
#                         .items-list li {{ padding: 8px; background: #f5f5f5; margin: 5px 0; border-radius: 4px; }}
#                         .total {{ font-size: 1.3em; font-weight: bold; color: #d32f2f; text-align: right; padding: 15px 0; }}
#                         .status {{ display: inline-block; padding: 8px 12px; background: #fff3e0; color: #e65100; border-radius: 4px; font-weight: bold; }}
#                         .footer {{ text-align: center; color: #999; font-size: 0.9em; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px; }}
#                     </style>
#                 </head>
#                 <body>
#                     <div class="container">
#                         <div class="header">
#                             <h2>📦 New Order Received!</h2>
#                         </div>
                        
#                         <div class="content">
#                             <div class="section">
#                                 <h3>Order Information</h3>
#                                 <div class="info-row">
#                                     <span class="label">Order ID:</span>
#                                     <span class="value"><strong>{order_data['orderid']}</strong></span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Date & Time:</span>
#                                     <span class="value">{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Status:</span>
#                                     <span class="value"><span class="status">PENDING</span></span>
#                                 </div>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Customer Information</h3>
#                                 <div class="info-row">
#                                     <span class="label">Name:</span>
#                                     <span class="value">{order_data.get('firstName')} {order_data.get('lastName')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Email:</span>
#                                     <span class="value">{order_data.get('email')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Phone:</span>
#                                     <span class="value">{order_data.get('phoneNo')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">City:</span>
#                                     <span class="value">{order_data.get('city')}</span>
#                                 </div>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Delivery Address</h3>
#                                 <div style="background: #f5f5f5; padding: 12px; border-radius: 4px;">
#                                     <p style="margin: 0;">{order_data.get('address')}</p>
#                                     <p style="margin: 8px 0 0 0;"><strong>{order_data.get('city')} - {order_data.get('pincode')}</strong></p>
#                                 </div>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Order Items</h3>
#                                 <ul class="items-list">
#                                     {items_list}
#                                 </ul>
#                             </div>
                            
#                             <div class="section">
#                                 <h3>Order Summary</h3>
#                                 <div class="info-row">
#                                     <span class="label">Delivery Type:</span>
#                                     <span class="value">{order_data.get('deliveryType', 'Standard')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Payment Method:</span>
#                                     <span class="value">{order_data.get('paymentMethod', 'N/A')}</span>
#                                 </div>
#                                 <div class="info-row">
#                                     <span class="label">Promo Code:</span>
#                                     <span class="value">{order_data.get('promocode') or 'None'}</span>
#                                 </div>
#                                 <div class="total">
#                                     Total Amount: ₹{order_data.get('total', 0)}
#                                 </div>
#                             </div>
                            
#                             <div class="footer">
#                                 <p>This is an automated email from AMCMart Admin Panel.</p>
#                                 <p>Login to your admin panel to update order status.</p>
#                             </div>
#                         </div>
#                     </div>
#                 </body>
#             </html>
#             """
            
#             msg.attach(MIMEText(html, 'html'))
#             print(f"✅ Email HTML attached")
            
#             # Connect to SMTP server
#             print(f"🔗 Connecting to SMTP server: {SMTP_SERVER}:{SMTP_PORT}")
#             server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
#             print(f"✅ SMTP connection established")
            
#             # Start TLS
#             print(f"🔐 Starting TLS encryption...")
#             server.starttls()
#             print(f"✅ TLS started")
            
#             # Login
#             print(f"🔑 Logging in to Gmail account...")
#             server.login(ADMIN_EMAIL, EMAIL_PASSWORD)
#             print(f"✅ Gmail login successful")
            
#             # Send message
#             print(f"📤 Sending email...")
#             server.send_message(msg)
#             print(f"✅ Email sent successfully")
            
#             # Close connection
#             server.quit()
#             print(f"✅ SMTP connection closed")
#             print(f"{'='*60}")
#             print(f"✅ EMAIL SENT SUCCESSFULLY")
#             print(f"{'='*60}\n")
            
#             return True
        
#         except smtplib.SMTPAuthenticationError as e:
#             print(f"\n{'='*60}")
#             print(f"❌ AUTHENTICATION ERROR - Gmail Login Failed")
#             print(f"{'='*60}")
#             print(f"Error: {e}")
#             print(f"Possible causes:")
#             print(f"  1. Incorrect ADMIN_EMAIL")
#             print(f"  2. Incorrect EMAIL_PASSWORD (app password)")
#             print(f"  3. 2FA enabled but no app password generated")
#             print(f"{'='*60}\n")
#             return False
        
#         except smtplib.SMTPException as e:
#             print(f"\n{'='*60}")
#             print(f"❌ SMTP ERROR")
#             print(f"{'='*60}")
#             print(f"Error: {e}")
#             print(f"{'='*60}\n")
#             return False
        
#         except Exception as e:
#             print(f"\n{'='*60}")
#             print(f"❌ UNEXPECTED ERROR")
#             print(f"{'='*60}")
#             print(f"Error: {e}")
#             import traceback
#             traceback.print_exc()
#             print(f"{'='*60}\n")
#             return False
class DatabaseManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return None

    def init_database(self):
        """Initialize database and create tables"""
        try:
            print("\n🔍 Testing database connection...")
            conn = self.get_connection()
            if not conn:
                print("❌ FATAL: Cannot connect to database!")
                print(f"   DATABASE_URL: {DATABASE_URL[:80] if DATABASE_URL else 'NOT SET'}")
                return False
            
            print("✅ Database connection successful")
            
            cursor = conn.cursor()
            
            # Test query
            cursor.execute("SELECT 1")
            test_result = cursor.fetchone()
            print(f"✅ Database test query returned: {test_result}")
            
            # Products table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    productname VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    price_1kg INTEGER,
                    price_500gm INTEGER,
                    stock_status VARCHAR(50) DEFAULT 'in-stock',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Products table created/verified")
            
            # Orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    orderid VARCHAR(50) UNIQUE NOT NULL,
                    firstName VARCHAR(100),
                    lastName VARCHAR(100),
                    phoneNo VARCHAR(20),
                    email VARCHAR(100),
                    address TEXT,
                    city VARCHAR(100),
                    pincode VARCHAR(10),
                    deliveryType VARCHAR(50),
                    paymentMethod VARCHAR(50),
                    items TEXT,
                    total INTEGER,
                    promocode VARCHAR(50),
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Orders table created/verified")
            
            # Promo codes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promocodes (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    discount INTEGER,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Promo codes table created/verified")
            
            # Customers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
                    firstName VARCHAR(100),
                    lastName VARCHAR(100),
                    phoneNo VARCHAR(20),
                    email VARCHAR(100),
                    city VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Customers table created/verified")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Database initialized successfully\n")
            return True
        
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def execute_query(self, query, params=()):
        """Execute query with thread safety"""
        try:
            with self.lock:
                conn = self.get_connection()
                if not conn:
                    print("❌ No database connection!")
                    return False
                
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                cursor.close()
                conn.close()
                return True
        
        except Exception as e:
            print(f"❌ Query error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def fetch_all(self, query, params=()):
        """Fetch all results"""
        try:
            with self.lock:
                conn = self.get_connection()
                if not conn:
                    return []
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(query, params)
                results = cursor.fetchall()
                cursor.close()
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
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(query, params)
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return dict(result) if result else None
        except Exception as e:
            print(f"❌ Fetch one error: {e}")
            return None

    def insert_and_get_id(self, query, params=()):
        """Insert and return the ID"""
        try:
            with self.lock:
                conn = self.get_connection()
                if not conn:
                    print("❌ No database connection!")
                    return None
                
                cursor = conn.cursor()
                cursor.execute(query + " RETURNING id", params)
                result = cursor.fetchone()
                
                if result is None:
                    print("❌ Insert returned no ID")
                    cursor.close()
                    conn.close()
                    return None
                
                conn.commit()
                cursor.close()
                conn.close()
                
                final_id = result[0] if result else None
                return final_id
        
        except Exception as e:
            print(f"❌ Insert error: {e}")
            import traceback
            traceback.print_exc()
            return None

# Global database instance
db = DatabaseManager()

class APIHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_HEAD(self):
        """Handle HEAD requests"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/' or path == '':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            response = {"success": True, "message": "AMCMart API - Use /api endpoints"}
            self.wfile.write(json.dumps(response).encode())

        elif path == '/api/health':
            # Test database connection
            test_conn = db.get_connection()
            db_status = "✅ Connected" if test_conn else "❌ Failed"
            if test_conn:
                test_conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            response = {
                "success": True,
                "message": "AMCMart API is running!",
                "timestamp": datetime.now().isoformat(),
                "database": db_status,
                "email_configured": bool(ADMIN_EMAIL and EMAIL_PASSWORD),
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
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            orders = db.fetch_all('SELECT * FROM orders')
            total_revenue = sum(int(o.get('total', 0)) for o in orders)
            pending_orders = db.fetch_all('SELECT * FROM orders WHERE status = %s', ('pending',))
            customers = db.fetch_all('SELECT DISTINCT phoneNo FROM orders')
            
            response = {
                "success": True,
                "data": {
                    "total_products": len(db.fetch_all('SELECT * FROM products')),
                    "total_orders": len(orders),
                    "total_revenue": total_revenue,
                    "total_customers": len(customers),
                    "pending_orders": len(pending_orders)
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
        except json.JSONDecodeError as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": f"Invalid JSON"}).encode())
            return
        
        if path == '/api/products':
            try:
                productname = data.get('productname')
                category = data.get('category')
                price_1kg = data.get('price_1kg')
                price_500gm = data.get('price_500gm')
                stock_status = data.get('stock_status', 'in-stock')
                
                if not all([productname, category, price_1kg, price_500gm]):
                    raise ValueError("Missing required fields")
                
                product_id = db.insert_and_get_id(
                    'INSERT INTO products (productname, category, price_1kg, price_500gm, stock_status) VALUES (%s, %s, %s, %s, %s)',
                    (productname, category, price_1kg, price_500gm, stock_status)
                )
                
                if product_id:
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
                
                # Build params tuple - EXACTLY 14 values for 14 columns
                params = (
                    order_id,                               # 1. orderid
                    data.get('firstName'),                  # 2. firstName
                    data.get('lastName'),                   # 3. lastName
                    data.get('phoneNo'),                    # 4. phoneNo
                    data.get('email'),                      # 5. email
                    data.get('address'),                    # 6. address
                    data.get('city'),                       # 7. city
                    data.get('pincode'),                    # 8. pincode
                    data.get('deliveryType'),               # 9. deliveryType
                    data.get('paymentMethod'),              # 10. paymentMethod
                    data.get('items'),                      # 11. items
                    data.get('total'),                      # 12. total
                    data.get('promocode', ''),              # 13. promocode
                    'pending',                              # 14. status
                )
                
                query = '''INSERT INTO orders 
                    (orderid, firstName, lastName, phoneNo, email, address, city, pincode, 
                     deliveryType, paymentMethod, items, total, promocode, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
                
                success = db.execute_query(query, params)
                
                if success:
                    # Send email notification
                    email_data = data.copy()
                    email_data['orderid'] = order_id
                    
                    email_thread = threading.Thread(
                        target=EmailService.send_order_notification,
                        args=(email_data,)
                    )
                    email_thread.daemon = True
                    email_thread.start()
                    
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
                product_id = db.insert_and_get_id(
                    'INSERT INTO promocodes (code, discount, status) VALUES (%s, %s, %s)',
                    (data.get('code'), data.get('discount'), data.get('status', 'active'))
                )
                
                if product_id:
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
                else:
                    raise Exception("Failed to insert promo code")
            
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        
        elif path == '/api/promo/validate':
            try:
                code = data.get('code')
                promo = db.fetch_one('SELECT * FROM promocodes WHERE code = %s AND status = %s', (code, 'active'))
                
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
    print(f'\n🚀 AMCMart API Server Starting...')
    print(f'🔧 Port: {port}')
    print(f'📊 API Base URL: https://amcmart-api.onrender.com/api')
    print(f'💾 Database: PostgreSQL')
    print(f'📧 Email: {"✅ Configured" if ADMIN_EMAIL and EMAIL_PASSWORD else "⚠️ Not configured"}')
    print(f'\n✅ Server ready to accept requests\n')
    httpd.serve_forever()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    run_server(port)




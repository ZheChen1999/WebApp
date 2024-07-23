from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')

# Sample data for menu items
menu_items = [
    {'id': 1, 'name': '沙拉', 'description': '新鲜蔬菜沙拉', 'price': 25, 'image': 'salad.jpg'},
    {'id': 2, 'name': '牛排', 'description': '烤至完美的多汁牛排', 'price': 120, 'image': 'steak.jpg'},
    {'id': 3, 'name': '芝士蛋糕', 'description': '经典的纽约芝士蛋糕', 'price': 45, 'image': 'cheesecake.jpg'},
    {'id': 4, 'name': '咖啡', 'description': '现磨意式咖啡', 'price': 20, 'image': 'coffee.jpg'}
]

# File to keep track of orders
ORDER_FILE = 'orders.xlsx'

def generate_order_id():
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    order_count = get_order_count() + 1
    order_id = f"{date_str}{order_count:02}"
    return order_id

def get_order_count():
    if not os.path.exists(ORDER_FILE):
        return 0
    try:
        df = pd.read_excel(ORDER_FILE, sheet_name='Orders')
        return len(df)
    except Exception as e:
        print(f"Error reading order count: {e}")
    return 0

def save_order(order_id, cart, total_price, name, phone, address, email, notes, payment_method):
    try:
        if os.path.exists(ORDER_FILE):
            df = pd.read_excel(ORDER_FILE, sheet_name='Orders')
        else:
            df = pd.DataFrame(columns=['OrderID', 'Items', 'TotalPrice', 'Name', 'Phone', 'Address', 'Email', 'Notes', 'PaymentMethod', 'Status'])
        
        items = ', '.join(f"{item['name']} ({item['price']}元 x{item['quantity']})" for item in cart)
        new_order = pd.DataFrame({
            'OrderID': [order_id],
            'Items': [items],
            'TotalPrice': [total_price],
            'Name': [name],
            'Phone': [phone],
            'Address': [address],
            'Email': [email],
            'Notes': [notes],
            'PaymentMethod': [payment_method],
            'Status': ['未付款']
        })
        
        df = pd.concat([df, new_order], ignore_index=True)
        df.to_excel(ORDER_FILE, sheet_name='Orders', index=False)
    except Exception as e:
        print(f"Error saving order: {e}")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def menu():
    return render_template('menu.html', menu_items=menu_items)

@app.route('/cart')
def cart_view():
    cart = session.get('cart', [])
    total_price = sum(item['price'] * item.get('quantity', 1) for item in cart)
    return render_template('cart.html', cart=cart, total_price=total_price)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))
    item = next((item for item in menu_items if str(item['id']) == item_id), None)
    
    if item:
        cart = session.get('cart', [])
        existing_item = next((cart_item for cart_item in cart if cart_item['id'] == item['id']), None)
        
        if existing_item:
            existing_item['quantity'] += quantity
        else:
            item['quantity'] = quantity
            cart.append(item)
        
        session['cart'] = cart
        return jsonify(cart)
    return jsonify({'error': 'Item not found'}), 404

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        email = request.form.get('email')
        notes = request.form.get('notes', '')
        payment_method = request.form.get('payment_method', 'wechat')
        
        order_id = generate_order_id()
        
        cart = session.get('cart', [])
        total_price = sum(item['price'] * item['quantity'] for item in cart)
        
        save_order(order_id, cart, total_price, name, phone, address, email, notes, payment_method)
        
        session.pop('cart', None)
        
        payment_images = {
            'wechat': 'wechat_pay.png',
            'alipay': 'alipay.png',
            'bank': 'bank_transfer.png',
            'usdt': 'usdt_pay.png'
        }
        payment_image = payment_images.get(payment_method, 'wechat_pay.png')
        
        return render_template('checkout.html', cart=cart, total_price=total_price, payment_image=payment_image, order_id=order_id)
    
    cart = session.get('cart', [])
    total_price = sum(item['price'] * item['quantity'] for item in cart)
    order_id = generate_order_id()
    return render_template('checkout.html', cart=cart, total_price=total_price, order_id=order_id)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        status = request.form.get('status')
        
        if os.path.exists(ORDER_FILE):
            df = pd.read_excel(ORDER_FILE, sheet_name='Orders')
            df['OrderID'] = df['OrderID'].astype(str)  # 将订单ID转换为字符串类型
            print(f"DataFrame content:\n{df}")
            print(f"Order IDs in DataFrame: {df['OrderID'].values}")
            print(f"Order ID type: {type(order_id)}")
            print(f"DataFrame Order ID type: {type(df['OrderID'].values[0])}")
            if order_id in df['OrderID'].values:
                df.loc[df['OrderID'] == order_id, 'Status'] = status
                df.to_excel(ORDER_FILE, sheet_name='Orders', index=False)
            else:
                print(f"Order ID {order_id} not found in DataFrame.")
                return "Order not found", 404
        else:
            return "Order file not found", 404
        
        return redirect(url_for('admin'))
    
    orders = []
    if os.path.exists(ORDER_FILE):
        df = pd.read_excel(ORDER_FILE, sheet_name='Orders')
        df['OrderID'] = df['OrderID'].astype(str)  # 将订单ID转换为字符串类型
        orders = df[['OrderID', 'Status']].to_dict(orient='records')
    
    return render_template('admin.html', orders=orders)

@app.route('/order_status', methods=['GET', 'POST'])
def order_status():
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        
        if os.path.exists(ORDER_FILE):
            df = pd.read_excel(ORDER_FILE, sheet_name='Orders')
            df['OrderID'] = df['OrderID'].astype(str)  # 将订单ID转换为字符串类型
            print(f"DataFrame content:\n{df}")
            print(f"Order IDs in DataFrame: {df['OrderID'].values}")
            print(f"Order ID type: {type(order_id)}")
            print(f"DataFrame Order ID type: {type(df['OrderID'].values[0])}")
            order = df[df['OrderID'] == order_id]
            if not order.empty:
                status = order.iloc[0]['Status']
                return render_template('order_status.html', order_id=order_id, status=status)
            else:
                print(f"Order ID {order_id} not found in DataFrame.")
                return "Order not found", 404
        else:
            return "Order file not found", 404
    
    return render_template('order_status.html')




if __name__ == '__main__':
    app.run(debug=True, port=9090)

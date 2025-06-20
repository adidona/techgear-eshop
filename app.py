from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
import os
import boto3
import random
import string
import uuid
from decimal import Decimal
from datetime import datetime
from boto3.dynamodb.conditions import Attr

load_dotenv()

# create Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Connect to DynamoDB
region = os.getenv("AWS_DEFAULT_REGION", "eu-west-1")
dynamodb = boto3.resource('dynamodb', region_name=region)

products_table = dynamodb.Table('Products')
orders_table = dynamodb.Table('Orders')
users_table = dynamodb.Table('Users')
reviews_table = dynamodb.Table('Reviews')

# Generate a unique userID when a new user registers
def generate_unique_user_id():
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=4))        
    return letters + numbers

# Routes, functions that handle user navigation :
@app.route('/')
def home():
    return render_template('index.html')

# Login of users with email and password
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        response = users_table.scan(
            FilterExpression=Attr('email').eq(email) & Attr('password').eq(password)
        )
        users = response.get('Items', [])

        if users:
            user = users[0]
            session['user_id'] = user['user_id']
            session['user_email'] = user['email']
            session['user_name'] = user.get('name', 'User')
            session['role'] = user.get('role', 'customer')

            return redirect(url_for('dashboard'))
        else:
            error = " Incorrect email or password."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') == 'admin':
        return redirect(url_for('admin_panel'))
    return redirect(url_for('customer_panel'))

# Admin panel
@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin':
        return "Forbidden." # Aceess denied if user is not admin

    try:
        users = users_table.scan().get('Items', [])
        orders = orders_table.scan().get('Items', [])
        products = products_table.scan().get('Items', [])
    except Exception as e:
        return f"Error: {e}"

    return render_template('admin_dashboard.html', users=users, orders=orders, products=products)


@app.route('/customer')
def customer_panel():
    if session.get('role') != 'customer':
        return "Access forbidden."

    try:
        user_id = session.get('user_id')
        response = orders_table.scan(
            FilterExpression=Attr('user_id').eq(user_id)
        )
        orders = response.get('Items', [])

        for order in orders:
            detailed_products = []
            product_list = order.get('products', [])

            if isinstance(product_list, list):
                for p in product_list:
                    pid = p.get('product_id')
                    qty = p.get('quantity')
                    if pid and qty:
                        product_data = products_table.get_item(Key={'product_id': pid})
                        product = product_data.get('Item')

                        if not product:
                            continue

                        detailed_products.append({
                            'name': product.get('title', 'Unknown product'),
                            'price': float(product.get('price', 0.0)),
                            'quantity': qty,
                            'image_url': product.get('image_url', '')
                        })

            order['detailed_products'] = detailed_products
    except Exception as e:
        return f"Error: {e}"

    return render_template('order_history.html', orders=orders)


@app.route('/product/<product_id>')
def product_page(product_id):
    try:
        # Retrieve product
        product_resp = products_table.get_item(Key={'product_id': product_id})
        product = product_resp.get('Item')
        if not product:
            return "Product not found."

        # Retrieve reviews
        response = reviews_table.scan(FilterExpression=Attr('product_id').eq(product_id))
        reviews = response.get('Items', [])

        # Add username
        for r in reviews:
            user_resp = users_table.get_item(Key={'user_id': r['user_id']})
            r['user_name'] = user_resp.get('Item', {}).get('name', 'User')

        return render_template('product.html', product=product, reviews=reviews)
    except Exception as e:
        return f"Error: {e}"

# Users have the option to review the products
@app.route('/submit-review', methods=['POST'])
def submit_review():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    product_id = request.form['product_id']
    rating = int(request.form['rating'])
    comment = request.form.get('comment', '')

    review = {
        'review_id': str(uuid.uuid4()),
        'product_id': product_id,
        'user_id': session['user_id'],
        'rating': rating,
        'comment': comment,
        'created_at': datetime.now().isoformat()
    }

    reviews_table.put_item(Item=review)
    return redirect(url_for('product_page', product_id=product_id))

@app.route('/store')
def store():
    try:
        search_query = request.args.get('q', '').lower()
        sort_by = request.args.get('sort', '')
        response = products_table.scan()
        products = response.get('Items', [])

        # Search by word in the title or description
        if search_query:
            products = [
                p for p in products
                if search_query in p.get('title', '').lower() or search_query in p.get('description', '').lower()
            ]
        review_resp = reviews_table.scan()
        all_reviews = review_resp.get('Items', [])
        # Group ratings by product_id
        from collections import defaultdict
        rating_map = defaultdict(list)
        for r in all_reviews:
            rating_map[r['product_id']].append(r['rating'])

        # Calculate average rating
        for product in products:
            ratings = rating_map.get(product['product_id'], [])
            if ratings:
                avg = sum(ratings) / len(ratings)
                product['avg_rating'] = round(avg, 1)
            else:
                product['avg_rating'] = 0

        # Sorting
        if sort_by == 'price_asc':
            products.sort(key=lambda x: float(x.get('price', 0)))
        elif sort_by == 'price_desc':
            products.sort(key=lambda x: float(x.get('price', 0)), reverse=True)

        return render_template(
            'store.html',
            products=products,
            query=search_query,
            selected_sort=sort_by
        )
    except Exception as e:
        return f"Error retrieving products: {e}"

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    if not isinstance(cart, dict):
        cart = {}

    items = []
    total = 0

    for pid, qty in cart.items():
        try:
            response = products_table.get_item(Key={'product_id': pid})
            product = response.get('Item')
            if product:
                price = float(product.get('price', 0))
                subtotal = price * qty
                items.append({
                    'product_id': pid,
                    'name': product.get('title', 'Unknown product'),
                    'price': price,
                    'quantity': qty,
                    'subtotal': round(subtotal, 2),
                    'image_url': product.get('image_url', '')
                })
                total += subtotal
        except Exception as e:
            print(f"Product error {pid}: {e}")

    # Load default_address if available
    address = None
    if 'user_id' in session:
        user = users_table.get_item(Key={'user_id': session['user_id']}).get('Item', {})
        address = user.get('default_address') or user.get('address')
    return render_template('checkout.html', items=items, total=round(total, 2), address=address)

# In order to place an order a guest have to login or register
@app.route('/place-order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    if not cart:
        return "The cart is empty."

    # Address and payment method
    street = request.form.get('street')
    zipcode = request.form.get('zipcode')
    phone = request.form.get('phone')
    payment_method = request.form.get('payment_method')
    save_address = 'save_address' in request.form

    total = 0
    products = []

    for pid, qty in cart.items():
        response = products_table.get_item(Key={'product_id': pid})
        product = response.get('Item')
        if product:
            total += float(product['price']) * qty
            products.append({
                'product_id': pid,
                'quantity': qty
            })

    # Creating order with user details including shipping address
    order = {
        'order_id': str(uuid.uuid4()),
        'user_id': session['user_id'],
        'user_name': session.get('user_name', 'User'),
        'products': products,
        'total_price': Decimal(str(round(total, 2))),
        'order_date': datetime.now().isoformat(),
        'shipping_address': {
            'street': street,
            'zipcode': zipcode,
            'phone': phone
        },
        'payment_method': payment_method
    }

    orders_table.put_item(Item=order)

    # Save address if requested
    if save_address:
        user = users_table.get_item(Key={'user_id': session['user_id']}).get('Item', {})
        addresses = user.get('addresses', [])
        new_address = {
            'street': street,
            'zipcode': zipcode,
            'phone': phone
        }
        if new_address not in addresses:
            addresses.append(new_address)
            users_table.update_item(
                Key={'user_id': session['user_id']},
                UpdateExpression="SET addresses = :a",
                ExpressionAttributeValues={':a': addresses}
            )

    session['cart'] = {}
    return redirect(url_for('customer_panel'))

@app.route('/clear-cart')
def clear_cart():
    session['cart'] = {}
    return redirect(url_for('cart'))

@app.route('/cart/increase/<product_id>')
def increase_quantity(product_id):
    cart = session.get('cart', {})
    if product_id in cart:
        cart[product_id] += 1
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/cart/decrease/<product_id>')
def decrease_quantity(product_id):
    cart = session.get('cart', {})
    if product_id in cart:
        cart[product_id] -= 1
        if cart[product_id] <= 0:
            del cart[product_id]
    session['cart'] = cart
    return redirect(url_for('cart'))

# Users profile, users have the option to edit their name or email and it will automatically get updated in the DynamoDB
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    if request.method == 'POST':
        new_name = request.form['name']
        new_email = request.form['email']

        try:
            # Update in DynamoDB
            users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET #n = :name, email = :email',
                ExpressionAttributeNames={'#n': 'name'},
                ExpressionAttributeValues={
                    ':name': new_name,
                    ':email': new_email
                }
            )
            # Update in session
            session['user_name'] = new_name
            session['user_email'] = new_email

            message = "Information updated successfully."
        except Exception as e:
            message = f"Error during update: {e}"

        return render_template('profile.html', name=new_name, email=new_email, message=message)

    try:
        response = users_table.get_item(Key={'user_id': user_id})
        user = response.get('Item', {})
        return render_template('profile.html', name=user.get('name', ''), email=user.get('email', ''))
    except Exception as e:
        return f"Error: {e}"

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    product_id = request.form['product_id']
    
    #If no cart exists in session
    if 'cart' not in session or not isinstance(session['cart'], dict):
        session['cart'] = {}

    cart = session['cart']

    # Add or increase quantity during the order
    if product_id in cart:
        cart[product_id] += 1
    else:
        cart[product_id] = 1

    session['cart'] = cart 
    return redirect(url_for('store'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # checkk if this email already exists, if it does exist, an error will occure
        response = users_table.scan(FilterExpression=Attr('email').eq(email))
        if response.get('Items'):
            error = "⚠️ A user with this email already exists."
        else:
            user_id = generate_unique_user_id()
            user = {
                'user_id': user_id,
                'name': name,
                'email': email,
                'password': password,
                'role': 'customer',
                'created_at': datetime.now().isoformat()
            }
            users_table.put_item(Item=user)
            return redirect(url_for('login'))

    return render_template('register.html', error=error)

@app.route('/addresses', methods=['GET', 'POST'])
def address_book():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = users_table.get_item(Key={'user_id': user_id}).get('Item', {})
    addresses = user.get('addresses', [])

    return render_template('addresses.html', addresses=addresses)

@app.route('/delete-address', methods=['POST'])
def delete_address():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    street = request.form.get('street')
    zipcode = request.form.get('zipcode')
    phone = request.form.get('phone')

    try:
        user = users_table.get_item(Key={'user_id': user_id}).get('Item', {})
        addresses = user.get('addresses', [])

        new_addresses = [
            a for a in addresses
            if not (a['street'] == street and a['zipcode'] == zipcode and a['phone'] == phone)
        ]

        users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression="SET addresses = :a",
            ExpressionAttributeValues={':a': new_addresses}
        )
    except Exception as e:
        return f"Error while deleting address: {e}"

    return redirect(url_for('address_book'))

@app.route('/set-default-address', methods=['POST'])
def set_default_address():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    street = request.form.get('street')
    zipcode = request.form.get('zipcode')
    phone = request.form.get('phone')

    new_default = {
        'street': street,
        'zipcode': zipcode,
        'phone': phone
    }

    try:
        users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression="SET default_address = :d",
            ExpressionAttributeValues={':d': new_default}
        )
    except Exception as e:
        return f"Error while saving default address: {e}"

    return redirect(url_for('address_book'))

if __name__ == '__main__':
    app.run(debug=True)
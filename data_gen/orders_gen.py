import json
import random
from datetime import datetime

# Load uers from the JSON file we created 
with open('users.json', encoding='utf-8') as f:
    all_users = json.load(f)
# REal products we took from Amazon database
with open('products.json', encoding='utf-8') as f:
    all_products = json.load(f)

customers = [u for u in all_users if u.get('role') == 'customer']     
product_map = {p['product_id']: p for p in all_products if 'product_id' in p and 'price' in p}  #Dictionary for product lookup

orders = []

# Creating 300 random orders and each order has 1 - 4 products
for _ in range(300):
    user = random.choice(customers)
    selected_products = random.sample(list(product_map.values()), k=random.randint(1, 4))   
    items = []
    total = 0

    for prod in selected_products:
        qty = random.randint(1, 3) 
        price = float(prod['price'])
        items.append({
            'product_id': prod['product_id'],
            'name': prod.get('title', 'Unnamed Product'),
            'quantity': qty
        })
        total += price * qty

    order = {
        'order_id': str(random.randint(100000, 999999)),    #each order has a unique order ID 
        'user_id': user['user_id'],
        'user_name': user.get('name'),
        'products': items,
        'total_price': round(total, 2),
        'created_at': datetime.now().isoformat()
    }

    orders.append(order)

# Save it in a JSON file
with open('orders.json', 'w', encoding='utf-8') as f:
    json.dump(orders, f, ensure_ascii=False, indent=4)

from faker import Faker
import json
from datetime import datetime
import random
import re

# Faker to generate reaistic names and emails
fake = Faker('en_US')

#Generate a random userID for each user with 2 uppercase letters and 4 numbers
def generate_custom_user_id():
    letters = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2)) 
    digits = ''.join(random.choices('0123456789', k=4))                    
    return letters + digits 

#Standard admin users
admin_users = [
    {
        'user_id': 'antonis_id',
        'name': 'Antonis Didonakis',
        'role': 'admin',
        'email': 'adidonakis@uth.gr',
    },
    {
        'user_id': 'stathis_id',
        'name': 'Stathis Pantos',
        'role': 'admin',
        'email': 'epantos@uth.gr',
    }
]

#Generate a single customer user
def generate_user():
    name = fake.name()
    name_parts = name.split()

    # Emails must not contain special characters
    email = f"{name_parts[0].lower()}.{name_parts[1].lower()}@example.com"
    email = re.sub(r'[^a-zA-Z0-9.@]', '', email)
    email = email.replace('..', '.')

    return {
        'user_id': generate_custom_user_id(),
        'name': name,
        'email': email,
        'role': 'customer',
        'created_at': datetime.now().isoformat()
    }

# Creating 200 random users
users = [generate_user() for _ in range(200)]
users = admin_users + users

# Save it in a JSON file
with open('users.json', 'w', encoding='utf-8') as f:
    json.dump(users, f, ensure_ascii=False, indent=4)
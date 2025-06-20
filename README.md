# TechGear eShop
This project was developed as part of the course Advanced Data Management during the academic year 2024–2025 from the Department of Electrical and Computer Engineering at the University of Thessaly.
## Project description
This is a web-based e-commerce platform for managing technology products, built using Flask, python and Amazon DynamoDB. The application allows users to browse products, manage their shopping cart, place orders and sumbit their review. Admin users can manage users, products, and orders through a dedicated admin panel.
## Setup instructions
To run this application locally using your own AWS account, follow these steps:
1. Clone the repository
```
git clone https://github.com/adidona/techgear-eshop.git
cd techgear-eshop
```
2. Prepare environment variables
Copy the provided example environment file and fill in your AWS credentials:
``` cp .env.example .env ```
Edit .env with your values and ensure that your AWS user has permission to read and write in DynamoDB tables.
3. Install Python dependencies
```pip install -r requirements.txt```
4. Set up DynamoDB tables. You must include in your AWS account these tables: Users, Products, Orders, Reviews.
Each table must have a primary key that matches the access pattern in the app.
5. Run the Flask app
```python3 app.py```. By default, Flask runs the app at: http://localhost:5000

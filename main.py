import os
from flask import Flask, render_template, request, redirect, url_for
from models import db, AccountBalance, Inventory, Operation

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///warehouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def initialize_account_balance():
    if AccountBalance.query.first() is None:
        initial_balance = AccountBalance(balance=0.0)
        db.session.add(initial_balance)
        db.session.commit()

# Confirm the db is created and the account_balance is initilaized
with app.app_context():
    db.create_all()
    initialize_account_balance()

@app.context_processor
def inject_account_balance():
    account_balance = AccountBalance.query.first()
    return dict(account_balance=account_balance.balance if account_balance else 0.0)

@app.route('/')
def home():
    inventory = Inventory.query.all()
    account_balance = AccountBalance.query.first().balance
    return render_template('index.html', inventory=inventory, account_balance=account_balance)

@app.route('/balance', methods=['GET', 'POST'])
def balance():
    account_balance = AccountBalance.query.first()
    if request.method == 'POST':
        action = request.form['action']
        amount = float(request.form['amount'])
        if action == 'add':
            account_balance.balance += amount
            new_operation = Operation(type='Balance', details=f'Added € {amount}')
        elif action == 'subtract':
            account_balance.balance -= amount
            new_operation = Operation(type='Balance', details=f'Subtracted € {amount}')
        db.session.add(new_operation)
        db.session.commit()
        return redirect(url_for('balance'))
    return render_template('balance.html', account_balance=account_balance.balance)

@app.route('/sale', methods=['GET', 'POST'])
def sale():
    message = ''
    inventory = Inventory.query.all()
    if request.method == 'POST':
        product_name = request.form['product']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        product = Inventory.query.filter_by(product=product_name).first()
        if product:
            if quantity <= product.quantity:
                total_sale = price * quantity
                account_balance = AccountBalance.query.first()
                account_balance.balance += total_sale
                product.quantity -= quantity
                if product.quantity == 0:
                    db.session.delete(product)
                new_operation = Operation(type='Sale', details=f'Sold {quantity} of {product_name} at € {price} each for € {total_sale}')
                db.session.add(new_operation)
                db.session.commit()
                message = 'Sale recorded successfully.'
            else:
                message = f'Insufficient quantity of {product_name} in the inventory.'
        else:
            message = f'{product_name} is not available in the inventory.'
    return render_template('sale.html', inventory=inventory, message=message)

@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    message = ''
    if request.method == 'POST':
        product_name = request.form['product']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        total_cost = price * quantity
        account_balance = AccountBalance.query.first()
        if total_cost <= account_balance.balance:
            account_balance.balance -= total_cost
            product = Inventory.query.filter_by(product=product_name).first()
            if product:
                product.quantity += quantity
            else:
                new_product = Inventory(product=product_name, quantity=quantity, price=price)
                db.session.add(new_product)
            new_operation = Operation(type='Purchase', details=f'Purchased {quantity} of {product_name} at € {price} each for € {total_cost}')
            db.session.add(new_operation)
            db.session.commit()
            message = 'Purchase recorded successfully.'
        else:
            message = 'Insufficient balance for this purchase.'
    return render_template('purchase.html', message=message)

@app.route('/history')
def history():
    operations = Operation.query.all()
    return render_template('history.html', operations=operations)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        initialize_account_balance()
    app.run(debug=True)

from app import app, db, Account, Category, Transaction
from faker import Faker
import random
from datetime import datetime

fake = Faker()

with app.app_context():
    # Create tables if not exist
    db.create_all()

    # Add accounts if none exist
    if Account.query.count() == 0:
        db.session.add_all([
            Account(name="Checking"),
            Account(name="Savings"),
            Account(name="Credit Card"),
        ])

    # Add categories if none exist
    if Category.query.count() == 0:
        db.session.add_all([
            Category(name="Groceries"),
            Category(name="Utilities"),
            Category(name="Salary"),
            Category(name="Entertainment"),
        ])

    db.session.commit()

    accounts = Account.query.all()
    categories = Category.query.all()

    for _ in range(100):
        date = fake.date_between(start_date='-1y', end_date='today')
        t_type = random.choice(['income', 'expense', 'transfer'])
        status = random.choice(['pending', 'completed', 'cancelled'])
        source_account = random.choice(accounts).id
        destination_account = random.choice(accounts).id
        amount = round(random.uniform(10, 1000), 2)
        purpose = fake.sentence(nb_words=5)
        category = random.choice(categories).id

        txn = Transaction(
            date=date,
            type=t_type,
            status=status,
            source_account_id=source_account,
            destination_account_id=destination_account,
            amount=amount,
            purpose=purpose,
            category_id=category,
        )
        db.session.add(txn)

    db.session.commit()
    print("Inserted 100 fake transactions")

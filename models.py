from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

transaction_tags = db.Table(
    'transaction_tags',
    db.Column('transaction_id', db.Integer, db.ForeignKey('transactions.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    transactions_source = db.relationship(
        'Transaction',
        backref='source_account_rel',
        foreign_keys='Transaction.source_account_id'
    )
    transactions_destination = db.relationship(
        'Transaction',
        backref='destination_account_rel',
        foreign_keys='Transaction.destination_account_id'
    )

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    transactions = db.relationship('Transaction', backref='category_rel')

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # e.g., income, expense
    status = db.Column(db.String(50), nullable=False)
    source_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    destination_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(255), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    tags = db.relationship(
        'Tag',
        secondary=transaction_tags,
        lazy='subquery',
        backref=db.backref('transactions', lazy=True)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.strftime("%Y-%m-%d"),
            "type": self.type,
            "status": self.status,
            "source_account": self.source_account_rel.name if self.source_account_rel else None,
            "destination_account": self.destination_account_rel.name if self.destination_account_rel else None,
            "amount": self.amount,
            "purpose": self.purpose,
            "category": self.category_rel.name if self.category_rel else None,
            "tags": [tag.name for tag in self.tags]
        }

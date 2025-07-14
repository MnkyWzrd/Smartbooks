from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from models import db, Transaction

app = Flask(__name__)

# Connect to local SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///transactions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Home route
@app.route("/")
def home():
    return "SmartBooks is running!"

# Add new transaction
@app.route("/api/transactions", methods=["POST"])
def add_transaction():
    data = request.get_json()
    new_txn = Transaction(
        date=data["date"],
        type=data["type"],
        status=data["status"],
        source_account=data["source_account"],
        destination_account=data["destination_account"],
        amount=data["amount"],
        purpose=data["purpose"]
    )
    db.session.add(new_txn)
    db.session.commit()
    return jsonify({"message": "Transaction added!"}), 201

# Get all transactions
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    transactions = Transaction.query.all()
    result = []
    for t in transactions:
        result.append({
            "id": t.id,
            "date": t.date,
            "type": t.type,
            "status": t.status,
            "source_account": t.source_account,
            "destination_account": t.destination_account,
            "amount": t.amount,
            "purpose": t.purpose
        })
    return jsonify(result)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
with app.app_context():
    db.create_all()

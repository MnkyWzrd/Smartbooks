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

# ✅ Add multiple transactions at once (batch)
from io import StringIO
import csv

@app.route("/api/transactions_batch", methods=["POST"])
def add_transactions_batch():
    transactions = []
    required_fields = ["date", "type", "status", "source_account", "destination_account", "amount", "purpose"]

    # ======================
    # CASE 1: CSV upload
    # ======================
    if "file" in request.files:
        uploaded_file = request.files["file"]
        stream = StringIO(uploaded_file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)

        for i, row in enumerate(reader, start=1):
            for field in required_fields:
                if field not in row or row[field].strip() == "":
                    return jsonify({"error": f"Missing or empty field '{field}' in row {i}"}), 400

            try:
                amount = float(row["amount"])
            except ValueError:
                return jsonify({"error": f"Invalid amount in row {i}"}), 400

            txn = Transaction(
                date=row["date"],
                type=row["type"],
                status=row["status"],
                source_account=row["source_account"],
                destination_account=row["destination_account"],
                amount=amount,
                purpose=row["purpose"]
            )
            transactions.append(txn)

    # ======================
    # CASE 2: JSON list upload
    # ======================
    else:
        data = request.get_json()

        for i, item in enumerate(data, start=1):
            for field in required_fields:
                if field not in item or str(item[field]).strip() == "":
                    return jsonify({"error": f"Missing or empty field '{field}' in item {i}"}), 400

            try:
                amount = float(item["amount"])
            except (ValueError, TypeError):
                return jsonify({"error": f"Invalid amount in item {i}"}), 400

            txn = Transaction(
                date=item["date"],
                type=item["type"],
                status=item["status"],
                source_account=item["source_account"],
                destination_account=item["destination_account"],
                amount=amount,
                purpose=item["purpose"]
            )
            transactions.append(txn)

    db.session.add_all(transactions)
    db.session.commit()
    return jsonify({"message": f"{len(transactions)} transactions added!"}), 201





# Delete a transaction by ID
@app.route("/api/transactions/<int:id>", methods=["DELETE"])
def delete_transaction(id):
    txn = Transaction.query.get_or_404(id)
    db.session.delete(txn)
    db.session.commit()
    return jsonify({"message": "Transaction deleted!"})

# 🟢 Start the app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

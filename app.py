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
from sqlalchemy import and_
from datetime import datetime

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    # Start a base query
    query = Transaction.query

    # Handle optional sorting
    sort_by = request.args.get("sort_by")
    sort_order = request.args.get("sort_order", "asc")

    if sort_by in ["amount", "date", "type", "status"]:
        column = getattr(Transaction, sort_by)
        if sort_order == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())

    # Execute query
    transactions = query.all()

    # Build result list
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



        # Optional filter: status
    txn_status = request.args.get("status")
    if txn_status:
        query = query.filter_by(status=txn_status)

    # Optional filter: source_account
    source = request.args.get("source_account")
    if source:
        query = query.filter_by(source_account=source)

    # Optional filter: destination_account
    destination = request.args.get("destination_account")
    if destination:
        query = query.filter_by(destination_account=destination)


    # Optional filter: type
    txn_type = request.args.get("type")
    if txn_type:
        query = query.filter_by(type=txn_type)

    transactions = query.all()
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




# Get all transactions with optional filters


    # Start building query
    query = Transaction.query

    if t_type:
        query = query.filter_by(type=t_type)
    if status:
        query = query.filter_by(status=status)
    if start_date and end_date:
        query = query.filter(Transaction.date.between(start_date, end_date))

    transactions = query.all()

    result = [{
        "id": t.id,
        "date": t.date,
        "type": t.type,
        "status": t.status,
        "source_account": t.source_account,
        "destination_account": t.destination_account,
        "amount": t.amount,
        "purpose": t.purpose
    } for t in transactions]

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

# Edit a transaction by ID
@app.route("/api/transactions/<int:id>", methods=["PUT"])
def update_transaction(id):
    txn = Transaction.query.get_or_404(id)
    data = request.get_json()

    txn.date = data.get("date", txn.date)
    txn.type = data.get("type", txn.type)
    txn.status = data.get("status", txn.status)
    txn.source_account = data.get("source_account", txn.source_account)
    txn.destination_account = data.get("destination_account", txn.destination_account)
    txn.amount = data.get("amount", txn.amount)
    txn.purpose = data.get("purpose", txn.purpose)

    db.session.commit()
    return jsonify({"message": "Transaction updated!"})

from fpdf import FPDF
import pandas as pd
from datetime import datetime

import io
from flask import send_file

@app.route("/api/export_csv", methods=["GET"])
def export_csv():
    transactions = Transaction.query.all()
    if not transactions:
        return jsonify({"error": "No transactions found"}), 404

    data = [{
        "Date": t.date,
        "Type": t.type,
        "Status": t.status,
        "Source": t.source_account,
        "Destination": t.destination_account,
        "Amount": t.amount,
        "Purpose": t.purpose
    } for t in transactions]

    df = pd.DataFrame(data)

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="SmartBooks_Transactions.csv"
    )

@app.route("/api/export_xlsx", methods=["GET"])
def export_xlsx():
    transactions = Transaction.query.all()
    if not transactions:
        return jsonify({"error": "No transactions found"}), 404

    data = [{
        "Date": t.date,
        "Type": t.type,
        "Status": t.status,
        "Source": t.source_account,
        "Destination": t.destination_account,
        "Amount": t.amount,
        "Purpose": t.purpose
    } for t in transactions]

    df = pd.DataFrame(data)

    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Transactions")
    xlsx_buffer.seek(0)

    return send_file(
        xlsx_buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="SmartBooks_Transactions.xlsx"
    )

# 🟢 Start the app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)


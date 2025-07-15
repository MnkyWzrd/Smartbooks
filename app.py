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
    query = Transaction.query

    # Optional filters
    txn_type = request.args.get("type")
    status = request.args.get("status")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if txn_type:
        query = query.filter(Transaction.type == txn_type)
    if status:
        query = query.filter(Transaction.status == status)
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Transaction.date >= start)
        except ValueError:
            return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(Transaction.date <= end)
        except ValueError:
            return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

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

@app.route("/api/transactions_pdf", methods=["GET"])
def generate_pdf_report():
    # Get query parameters
    txn_type = request.args.get("type")
    status = request.args.get("status")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # Base query
    query = Transaction.query

    if txn_type:
        query = query.filter(Transaction.type == txn_type)
    if status:
        query = query.filter(Transaction.status == status)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.all()

    if not transactions:
        return jsonify({"error": "No transactions found"}), 404

    # Convert to DataFrame
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

    # Group by Type and sum Amount
    summary = df.groupby("Type")["Amount"].sum()

    # Build PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="SmartBooks Transaction Summary", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "B", size=12)
    pdf.cell(100, 10, "Transaction Type", border=1)
    pdf.cell(50, 10, "Total Amount", border=1)
    pdf.ln()

    pdf.set_font("Arial", size=12)
    for ttype, amount in summary.items():
        pdf.cell(100, 10, ttype, border=1)
        pdf.cell(50, 10, f"{amount:.2f}", border=1)
        pdf.ln()

    response = app.response_class(pdf.output(dest='S').encode('latin1'), mimetype='application/pdf')
    response.headers['Content-Disposition'] = 'inline; filename=SmartBooks_Report.pdf'
    return response



# 🟢 Start the app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

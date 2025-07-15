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
    transactions = Transaction.query.all()

    if not transactions:
        return jsonify({"error": "No transactions found"}), 404

    # Convert transactions to a Pandas DataFrame
    data = [{
        "Date": t.date,
        "Type": t.type,
        "Status": t.status,
        "Source": t.source_account,
        "Destination": t.destination_account,
        "Amount": f"{t.amount:.2f}",
        "Purpose": t.purpose
    } for t in transactions]

    df = pd.DataFrame(data)

    # Initialize PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, txt="SmartBooks - Full Transaction Report", ln=True, align="C")
    pdf.ln(10)

    # Table header
    pdf.set_font("Arial", "B", 10)
    col_widths = [25, 20, 20, 30, 30, 25, 40]
    headers = df.columns.tolist()

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1)
    pdf.ln()

    # Table rows
    pdf.set_font("Arial", size=9)
    for _, row in df.iterrows():
        for i, item in enumerate(row):
            text = str(item)
            if len(text) > 30:
                text = text[:27] + "..."
            pdf.cell(col_widths[i], 10, text, 1)
        pdf.ln()

    # Return PDF
    response = app.response_class(pdf.output(dest='S').encode('latin1'), mimetype='application/pdf')
    response.headers['Content-Disposition'] = 'inline; filename=SmartBooks_Full_Report.pdf'
    return response


# 🟢 Start the app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

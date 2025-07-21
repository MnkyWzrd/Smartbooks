from flask import Flask, request, jsonify, send_file
from datetime import datetime
from sqlalchemy import func
from io import StringIO, BytesIO
import csv
import io
import pandas as pd
from fpdf import FPDF

from models import db, Account, Category, Tag, Transaction

app = Flask(__name__)

# ================
# Config & DB Setup
# ================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///transactions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ============
# Utils
# ============

def get_or_404_account(account_id):
    return Account.query.get(account_id)

def get_or_404_category(category_id):
    if category_id is None:
        return None
    return Category.query.get(category_id)

def get_or_create_tags(tag_names):
    tags = []
    for name in set(tag_names):
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
            db.session.flush()  # get ID without commit
        tags.append(tag)
    return tags

def validate_transaction_data(data, partial=False):
    required_fields = ["date", "type", "status", "source_account_id", "destination_account_id", "amount", "purpose"]
    clean = {}

    if not partial:
        for f in required_fields:
            if f not in data or (isinstance(data[f], str) and data[f].strip() == ""):
                return None, f"Missing or empty field: {f}"

    if "date" in data:
        try:
            clean['date'] = datetime.strptime(data['date'], "%Y-%m-%d").date()
        except Exception:
            return None, "Invalid date format. Expected YYYY-MM-DD."

    for f in ['type', 'status', 'purpose']:
        if f in data:
            if not isinstance(data[f], str) or data[f].strip() == "":
                return None, f"Invalid or empty field: {f}"
            clean[f] = data[f].strip()

    for f in ['source_account_id', 'destination_account_id']:
        if f in data:
            try:
                acc_id = int(data[f])
            except Exception:
                return None, f"Invalid {f}. Must be integer."
            if not get_or_404_account(acc_id):
                return None, f"{f} {acc_id} does not exist."
            clean[f] = acc_id

    if 'amount' in data:
        try:
            clean['amount'] = float(data['amount'])
        except Exception:
            return None, "Invalid amount format."

    if 'category_id' in data:
        if data['category_id'] is not None:
            try:
                cat_id = int(data['category_id'])
            except Exception:
                return None, "Invalid category_id. Must be integer or null."
            if not get_or_404_category(cat_id):
                return None, f"Category {cat_id} does not exist."
            clean['category_id'] = cat_id
        else:
            clean['category_id'] = None

    if 'tags' in data:
        if not isinstance(data['tags'], list):
            return None, "Tags must be a list of strings."
        clean['tags'] = data['tags']

    return clean, None

# ============
# Routes
# ============

@app.route("/")
def home():
    return "SmartBooks API v1.8 running!"

@app.route("/api/transactions", methods=["POST"])
def create_transaction():
    data = request.get_json()
    clean, err = validate_transaction_data(data)
    if err:
        return jsonify({"error": err}), 400

    txn = Transaction(
        date=clean['date'],
        type=clean['type'],
        status=clean['status'],
        source_account_id=clean['source_account_id'],
        destination_account_id=clean['destination_account_id'],
        amount=clean['amount'],
        purpose=clean['purpose'],
        category_id=clean.get('category_id', None)
    )

    if 'tags' in clean:
        txn.tags = get_or_create_tags(clean['tags'])

    db.session.add(txn)
    db.session.commit()
    return jsonify({"message": "Transaction created", "transaction": txn.to_dict()}), 201

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    query = Transaction.query

    txn_type = request.args.get("type")
    if txn_type:
        query = query.filter(Transaction.type == txn_type)

    txn_status = request.args.get("status")
    if txn_status:
        query = query.filter(Transaction.status == txn_status)

    source_acc = request.args.get("source_account_id")
    if source_acc:
        try:
            source_acc_id = int(source_acc)
            query = query.filter(Transaction.source_account_id == source_acc_id)
        except:
            pass

    dest_acc = request.args.get("destination_account_id")
    if dest_acc:
        try:
            dest_acc_id = int(dest_acc)
            query = query.filter(Transaction.destination_account_id == dest_acc_id)
        except:
            pass

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.date.between(start_dt, end_dt))
        except:
            pass

    sort_by = request.args.get("sort_by", "date")
    sort_order = request.args.get("sort_order", "asc")
    if sort_by in ['amount', 'date', 'type', 'status']:
        col = getattr(Transaction, sort_by)
        col = col.desc() if sort_order == 'desc' else col.asc()
        query = query.order_by(col)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items

    results = [t.to_dict() for t in transactions]

    return jsonify({
        "transactions": results,
        "page": page,
        "per_page": per_page,
        "total": pagination.total,
        "pages": pagination.pages
    })

@app.route("/api/transactions/<int:id>", methods=["GET"])
def get_transaction(id):
    txn = Transaction.query.get(id)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify(txn.to_dict())

@app.route("/api/transactions/<int:id>", methods=["PATCH"])
def update_transaction(id):
    txn = Transaction.query.get(id)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404

    data = request.get_json()
    clean, err = validate_transaction_data(data, partial=True)
    if err:
        return jsonify({"error": err}), 400

    for key, value in clean.items():
        if key == "tags":
            txn.tags = get_or_create_tags(value)
        else:
            setattr(txn, key, value)

    db.session.commit()
    return jsonify({"message": "Transaction updated", "transaction": txn.to_dict()})

@app.route("/api/transactions/<int:id>", methods=["DELETE"])
def delete_transaction(id):
    txn = Transaction.query.get(id)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404

    db.session.delete(txn)
    db.session.commit()
    return jsonify({"message": "Transaction deleted"})

@app.route("/api/transactions_batch", methods=["POST"])
def batch_upload():
    transactions = []
    if "file" in request.files:
        uploaded_file = request.files["file"]
        stream = StringIO(uploaded_file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)

        for i, row in enumerate(reader, start=1):
            clean, err = validate_transaction_data(row)
            if err:
                return jsonify({"error": f"Row {i}: {err}"}), 400

            txn = Transaction(
                date=clean['date'],
                type=clean['type'],
                status=clean['status'],
                source_account_id=clean['source_account_id'],
                destination_account_id=clean['destination_account_id'],
                amount=clean['amount'],
                purpose=clean['purpose'],
                category_id=clean.get('category_id', None)
            )
            if 'tags' in clean:
                txn.tags = get_or_create_tags(clean['tags'])

            transactions.append(txn)
    else:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "Expected a list of transactions"}), 400
        for i, item in enumerate(data, start=1):
            clean, err = validate_transaction_data(item)
            if err:
                return jsonify({"error": f"Item {i}: {err}"}), 400

            txn = Transaction(
                date=clean['date'],
                type=clean['type'],
                status=clean['status'],
                source_account_id=clean['source_account_id'],
                destination_account_id=clean['destination_account_id'],
                amount=clean['amount'],
                purpose=clean['purpose'],
                category_id=clean.get('category_id', None)
            )
            if 'tags' in clean:
                txn.tags = get_or_create_tags(clean['tags'])
            transactions.append(txn)

    db.session.add_all(transactions)
    db.session.commit()
    return jsonify({"message": f"{len(transactions)} transactions added"}), 201

@app.route("/api/export_csv", methods=["GET"])
def export_csv():
    transactions = Transaction.query.all()
    if not transactions:
        return jsonify({"error": "No transactions found"}), 404

    data = [{
        "Date": t.date.strftime("%Y-%m-%d"),
        "Type": t.type,
        "Status": t.status,
        "Source": t.source_account_rel.name if t.source_account_rel else None,
        "Destination": t.destination_account_rel.name if t.destination_account_rel else None,
        "Amount": t.amount,
        "Purpose": t.purpose,
        "Category": t.category_rel.name if t.category_rel else None,
        "Tags": ", ".join([tag.name for tag in t.tags])
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
        "Date": t.date.strftime("%Y-%m-%d"),
        "Type": t.type,
        "Status": t.status,
        "Source": t.source_account_rel.name if t.source_account_rel else None,
        "Destination": t.destination_account_rel.name if t.destination_account_rel else None,
        "Amount": t.amount,
        "Purpose": t.purpose,
        "Category": t.category_rel.name if t.category_rel else None,
        "Tags": ", ".join([tag.name for tag in t.tags])
    } for t in transactions]

    df = pd.DataFrame(data)
    xlsx_buffer = BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Transactions")
    xlsx_buffer.seek(0)

    return send_file(
        xlsx_buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="SmartBooks_Transactions.xlsx"
    )

@app.route("/api/export_pdf", methods=["GET"])
def export_pdf():
    transactions = Transaction.query.all()
    if not transactions:
        return jsonify({"error": "No transactions found"}), 404

    totals = db.session.query(
        Transaction.type,
        func.count(Transaction.id),
        func.sum(Transaction.amount)
    ).group_by(Transaction.type).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, "SmartBooks Transaction Summary Report", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    for ttype, count, total in totals:
        pdf.cell(0, 10, f"Type: {ttype} | Transactions: {count} | Total Amount: {total:.2f}", ln=True)

    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="SmartBooks_Summary_Report.pdf"
    )

@app.route("/api/summary", methods=["GET"])
def summary():
    total_income = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.type == 'income').scalar()
    total_expense = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.type == 'expense').scalar()
    net_balance = total_income - total_expense
    return jsonify({
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance
    })

@app.route("/docs", methods=["GET"])
def docs():
    doc = {
        "API Documentation": {
            "GET /api/transactions": "Get list of transactions with filters, sorting, pagination",
            "POST /api/transactions": "Create a new transaction",
            "GET /api/transactions/<id>": "Get transaction by ID",
            "PATCH /api/transactions/<id>": "Update transaction partially",
            "DELETE /api/transactions/<id>": "Delete transaction",
            "POST /api/transactions_batch": "Batch upload transactions via CSV file or JSON list",
            "GET /api/export_csv": "Export transactions as CSV",
            "GET /api/export_xlsx": "Export transactions as XLSX",
            "GET /api/export_pdf": "Export summary report as PDF",
            "GET /api/summary": "Get summary of total income, expense, net balance",
        },
        "Notes": "All date fields are YYYY-MM-DD format. Tags is list of strings."
    }
    return jsonify(doc)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

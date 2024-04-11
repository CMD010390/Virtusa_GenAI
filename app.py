from datetime import datetime 
from flask import redirect
from flask import url_for
from google.generativeai.types.generation_types import BlockedPromptException
from flask import Flask, jsonify, request, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flService import *
from ExtractSingleLLM import *
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, origins=['http://localhost:4200']) 

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'uploads/'

# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///invoices.db'
db = SQLAlchemy(app)

# Define Invoice model
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=False, unique=True)
    vendor = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.String(50), nullable=False)
    invoice_total = db.Column(db.String, nullable=False)
    po_no = db.Column(db.String(50), nullable=False)
    po_total = db.Column(db.String, nullable=False)

# Define Review model
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), nullable=False)
    invoice_total = db.Column(db.String, nullable=False)
    vendor_name = db.Column(db.String(100), nullable=False)
    po_no = db.Column(db.String(50), nullable=False)
    po_total = db.Column(db.String, nullable=False)
    comparison_message = db.Column(db.Text, nullable=False)
    reviewer_notes = db.Column(db.Text, nullable=False)

# Define LLMHistory model
class LLMHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), nullable=False)
    invoice_total = db.Column(db.String, nullable=False)
    vendor_name = db.Column(db.String(100), nullable=False)
    po_no = db.Column(db.String(50), nullable=False)
    po_total = db.Column(db.String, nullable=False)
    comparison_message = db.Column(db.Text, nullable=False)
    discrepency_Flag = db.Column(db.String, nullable=False)  # Add this column

# Create database tables
def create_tables():
    with app.app_context():
        db.create_all()

@app.route('/', methods=['GET', 'POST'])
def upload_form():
    if request.method == 'POST':
        # Get uploaded files
        invoice = request.files['invoice']
        purchase_order = request.files['purchase_order']

        # Check file types and validity
        if invoice and allowed_file(invoice.filename) and purchase_order and allowed_file(purchase_order.filename):
            try:
                # Send to Google document AI and fetch the data in text format
                purchase_order_Googletext = extract_text_from_pdf(purchase_order)
                invoice_Googletext = extract_text_from_pdf(invoice)

                # Send to LLM for extracting specific details for comparison
                invoice_LLMtext = extract_InvoiceDataLLM(invoice_Googletext)
                purchase_order_LLMtext = extract_PurchaseOrderDataLLM(purchase_order_Googletext)

                # Find specific details from the invoice LLM text
                invoiceNo_and_total = ExtractInvoiceForPayment(invoice_LLMtext)
                Invoice_no = invoiceNo_and_total.get("Invoice no.", "Not found")
                Invoice_Total = invoiceNo_and_total.get("Total", "Not found")
                Invoice_DueDate = invoiceNo_and_total.get("Due Date", "Not found")
                Invoice_Vendor = invoiceNo_and_total.get("Vendor", "Not found")

                # Find specific details from PO LLM text
                PONo_and_total = ExtractPO_LLM_Fields(purchase_order_LLMtext)
                PO_no = PONo_and_total.get("PO no.", "Not found")
                PO_Total = PONo_and_total.get("Total", "Not found")

                # Fetch Comparison Flag
                discrepencyFlag = gettheDiscrepencyFlag(extract_Invoice_PO_ComparFlag_LLM(purchase_order_LLMtext, invoice_LLMtext))
                print("Extracted flag", discrepencyFlag)
                # Send both Details to LLM for actual comparison
                comparisionResult = extract_Invoice_PO_Compar(purchase_order_LLMtext, invoice_LLMtext)
                print("Google result", comparisionResult)

                 # Store the LLM History data in the database
                # Check if the combination of invoice number and PO number already exists in the database
                existing_entry = LLMHistory.query.filter_by(invoice_no=Invoice_no, po_no=PO_no).first()
                if not existing_entry:
                    # Store the LLM History data in the database
                    llm_History = LLMHistory(invoice_no=Invoice_no, invoice_total=Invoice_Total, vendor_name=Invoice_Vendor, po_no=PO_no, po_total=PO_Total, comparison_message=comparisionResult, discrepency_Flag=discrepencyFlag)
                    db.session.add(llm_History)
                    db.session.commit()
                else:
                    flash("Data already exists for Invoice No: {} and PO No: {}. Skipping insertion.".format(Invoice_no, PO_no), 'warning')


                # Pass the comparison result to the template
                return render_template('upload.html', success=True, comparison_result=comparisionResult,
                                       Invoice_no=Invoice_no, Invoice_Total=Invoice_Total,
                                       Invoice_Vendor=Invoice_Vendor, Invoice_DueDate=Invoice_DueDate,
                                       discrepencyFlag=discrepencyFlag,
                                       PO_no=PO_no, PO_Total=PO_Total)
            except BlockedPromptException as e:
                # Handle the blocked prompt exception
                flash("An error occurred: {}".format(str(e)), 'error')
            except Exception as e:
                # Handle other exceptions
                flash("An error occurred: {}".format(str(e)), 'error')
        else:
            flash("Invalid file format. Only PDFs allowed.", 'error')

    return render_template('upload.html')


def allowed_file(filename):
    return filename.lower().endswith('.pdf')


@app.route('/review')
def review_page():
    return render_template('review.html')

@app.route('/approvePayment', methods=['POST'])
def approve_payment():
    # Extract values from the form
    invoice_total = request.form.get('invoice_total')
    invoice_no = request.form.get('Invoice_no')
    invoice_vendor = request.form.get('Invoice_Vendor')
    Invoice_DueDate= request.form.get('Invoice_DueDate')
    po_no = request.form.get('PO_no')
    po_total= request.form.get('PO_Total')

    # Check if invoice number already exists in the database
    existing_invoice = Invoice.query.filter_by(invoice_number=invoice_no).first()
    if existing_invoice:
        response_message = "Invoice payment already processed for Invoice No: {}".format(invoice_no)
    else:
        # Store data in the database
        new_invoice = Invoice(invoice_number=invoice_no, vendor=invoice_vendor, 
                              due_date=Invoice_DueDate, invoice_total=invoice_total,
                               po_no= po_no, po_total= po_total )
        db.session.add(new_invoice)
        db.session.commit()
        response_message = "Payment approved for Invoice No: {}".format(invoice_no)

    return jsonify({"message": response_message})

#Store manual review
@app.route('/submitReview', methods=['POST'])
def submit_review():
    if request.method == 'POST':
        # Extract data from the form
        invoice_no = request.form['invoice_no']
        po_no = request.form['po_no']
        # Check if the review already exists in the database
        existing_review = Review.query.filter_by(invoice_no=invoice_no, po_no=po_no).first()
        if existing_review:
            # If the review already exists, return a message indicating that
            response_message = "Manual review already submitted for Invoice No: {} and PO No: {}".format(invoice_no, po_no)
            return jsonify({"message": response_message}), 400

        # Extract the rest of the data from the form
        comparison_message = request.form['comparison_message']
        invoice_total = request.form['invoice_total']
        vendor_name = request.form['vendor_name']
        po_total = request.form['po_total']
        comparison_message = request.form['comparison_message']
        reviewer_notes = request.form['reviewer_notes']

        # Store the review data in the database
        new_review = Review(invoice_no=invoice_no, invoice_total=invoice_total, vendor_name=vendor_name, 
                            po_no=po_no, po_total=po_total, comparison_message=comparison_message, 
                            reviewer_notes=reviewer_notes)
        db.session.add(new_review)
        db.session.commit()

        # Return a success message
        response_message = "Manual review submitted for Invoice No: {} and PO No: {}".format(invoice_no, po_no)
        return jsonify({"message": response_message}), 200

    # Handle invalid request method
    return jsonify({'message': 'Invalid request method'}), 405

# return Invoice payment data from the database
@app.route('/paymentTracker')
def payment_tracker():
    invoices = Invoice.query.all()
    return render_template('payment_tracker.html', invoices=invoices)

#search Invoice no or po from Payment tracker (Invoice table)
@app.route('/searchPaymentTracker', methods=['GET', 'POST'])
def search_PaymentTracker():
    if request.method == 'POST':
        search_text = request.form['searchQuery']

        # Search the database for entries containing the search text in invoice number or PO number
        Invoice_data = Invoice.query.filter(or_(Invoice.invoice_number.contains(search_text), Invoice.po_no.contains(search_text))).all()
        #print (Invoice_data)
        return render_template('payment_tracker.html', invoices=Invoice_data)


    # Redirect to the LLM history page if accessed via GET request
    return redirect(url_for('fetch_llm_history'))

@app.route('/fetchLLMHistory')
def fetch_llm_history():
    # Fetch data from LLMHistory table
    llm_history_data = LLMHistory.query.all()
    return render_template('history.html', llm_history_data=llm_history_data)

from flask import render_template

#search Invoice no or po from LLM history
@app.route('/searchLLMHistory', methods=['GET', 'POST'])
def search_llm_history():
    if request.method == 'POST':
        search_text = request.form['searchQuery']

        # Search the database for entries containing the search text in invoice number or PO number
        llm_history_data = LLMHistory.query.filter(or_(LLMHistory.invoice_no.contains(search_text), LLMHistory.po_no.contains(search_text))).all()
        
        return render_template('history.html', llm_history_data=llm_history_data)

    # Redirect to the LLM history page if accessed via GET request
    return redirect(url_for('fetch_llm_history'))

# fetch complete manual review
@app.route('/fetchManualReview')
def fetch_Review_data():
    # Fetch data from Review table
    Review_data = Review.query.all()
    return render_template('reviewRecords.html', reviews=Review_data)

#search with Invoice no or po from manual reviewer tracker (Review table)
@app.route('/searchManualReview', methods=['GET', 'POST'])
def search_ManualReview():
    if request.method == 'POST':
        search_text = request.form['searchQuery']

        # Search the database for entries containing the search text in invoice number or PO number
        reviews_data = Review.query.filter(or_(Review.invoice_no.contains(search_text), Review.po_no.contains(search_text))).all()
        #print (Invoice_data)
        return render_template('reviewRecords.html', reviews=reviews_data)

    # Redirect to the LLM history page if accessed via GET request
    return redirect(url_for('fetch_review_history'))

@app.route('/help', methods=['GET', 'POST'])
def help_page():
    # check if payment was already done for that invoice no.?
     
    return render_template('help.html')


if __name__ == '__main__':
    app.secret_key = 'your_secret_key'  # Add a secret key for flash messages
    create_tables()
    app.run(debug=True)

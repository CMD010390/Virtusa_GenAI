from datetime import datetime 
from werkzeug.utils import secure_filename
from flask import redirect
from flask import url_for
from google.generativeai.types.generation_types import BlockedPromptException
from flask import Flask, jsonify, request, render_template, flash,send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy import func
from flService import *
from ExtractSingleLLM import *
from flask_cors import CORS
import os
import io

app = Flask(__name__)
CORS(app, origins=['http://localhost:4200']) 

# Configure upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'

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
    payment_status = db.Column(db.String, nullable=False)

# Define Review model
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), nullable=False)
    invoice_total = db.Column(db.String, nullable=False)
    vendor_name = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.String(50), nullable=False)
    po_no = db.Column(db.String(50), nullable=False)
    po_total = db.Column(db.String, nullable=False)
    comparison_message = db.Column(db.Text, nullable=False)
    reviewer_notes = db.Column(db.Text, nullable=False)
    payment_status = db.Column(db.String, nullable=False)

# Define LLMHistory model
class LLMHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), nullable=False)
    invoice_total = db.Column(db.String, nullable=False)
    vendor_name = db.Column(db.String(100), nullable=False)
    po_no = db.Column(db.String(50), nullable=False)
    po_total = db.Column(db.String, nullable=False)
    comparison_message = db.Column(db.Text, nullable=False)
    discrepency_Flag = db.Column(db.String, nullable=False)  
    invoice_file_data = db.Column(db.LargeBinary)  
    po_file_data = db.Column(db.LargeBinary)

# Define Invoice po file database model
class InvPOFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_po_number = db.Column(db.String(100))  # Assuming the combined length of invoice and po number won't exceed 100 characters
    file_data = db.Column(db.LargeBinary)

# Define Invoice po file database model
class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_name = db.Column(db.String(100), nullable=False)
    account_details = db.Column(db.String(255), nullable=False)  # Assuming account details are stored as a string

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

                #Fraud detection 
                isGrammerFraudDetected = gettheFlagFromResponse(detect_Fraud_DataLLM(purchase_order_Googletext,invoice_Googletext),"isFraudDetected") 
                
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

                #check if the minimum data requirement condition satisfied for further processing
                if Invoice_no == "Not found" or Invoice_Total == "Not found" or Invoice_DueDate == "Not found" or PO_no == "Not found" or PO_Total == "Not found":
                    flash("Minimum Data Requirement Condition Not Satisfied.", "error")
                else:
                    # Fetch Comparison Flag
                    discrepencyFlag = gettheFlagFromResponse(extract_Invoice_PO_ComparFlag_LLM(purchase_order_LLMtext, invoice_LLMtext), "discrepencyFlag")
                    #print("Extracted flag", discrepencyFlag)
                    # Send both Details to LLM for actual comparison
                    comparisionResult = extract_Invoice_PO_Compar(purchase_order_LLMtext, invoice_LLMtext)
                    print("Google result", comparisionResult)

                    #Detect Fraud vendor
                    #add_hardcoded_vendor_data()
                   
                    isFraudDetected, fraudMessage = detectFraud(isGrammerFraudDetected, Invoice_Vendor)

                    print("isFraudDetected",isFraudDetected)
                    # Store the LLM History data in the database
                    # Check if the combination of invoice number and PO number already exists in the database
                    existing_entry = LLMHistory.query.filter_by(invoice_no=Invoice_no, po_no=PO_no).first()
                    if not existing_entry:
                        # Store the LLM History data in the database
                        llm_History = LLMHistory(invoice_no=Invoice_no, invoice_total=Invoice_Total, vendor_name=Invoice_Vendor, 
                                                 po_no=PO_no, po_total=PO_Total, comparison_message=comparisionResult, 
                                                 discrepency_Flag=discrepencyFlag,
                                                 invoice_file_data=invoice.read(),  # Storing invoice pdf file data
                                                 po_file_data=purchase_order.read(),  # Storing PO pdf file data
                                                 )
                        db.session.add(llm_History)
                        db.session.commit()
                    else:
                        flash("Comparision Result already exists for Invoice No: {} and PO No: {}. Skipping insertion.".format(Invoice_no, PO_no), 'warning')
                    
                     
                    # Pass the comparison result to the template
                    return render_template('upload.html', success=True, comparison_result=comparisionResult,
                                        Invoice_no=Invoice_no, Invoice_Total=Invoice_Total,
                                        Invoice_Vendor=Invoice_Vendor, Invoice_DueDate=Invoice_DueDate,
                                        discrepencyFlag=discrepencyFlag,isFraudDetected =isFraudDetected,fraudMessage=fraudMessage,
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
                               po_no= po_no, po_total= po_total,payment_status="PENDING" )
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
        invoice_dueDate = request.form['invoice_dueDate']
        po_total = request.form['po_total']
        comparison_message = request.form['comparison_message']
        reviewer_notes = request.form['reviewer_notes']

        # Store the review data in the database
        new_review = Review(invoice_no=invoice_no, invoice_total=invoice_total, vendor_name=vendor_name, due_date=invoice_dueDate,
                            po_no=po_no, po_total=po_total, comparison_message=comparison_message, 
                            reviewer_notes=reviewer_notes, payment_status="PENDING")
        db.session.add(new_review)
        db.session.commit()

        # Return a success message
        response_message = "Manual review submitted for Invoice No: {} and PO No: {}".format(invoice_no, po_no)
        return jsonify({"message": response_message}), 200

    # Handle invalid request method
    return jsonify({'message': 'Invalid request method'}), 405

from flask import flash
# approve manual review if approver finds it ok
@app.route('/approve_review/<int:id>', methods=['GET'])
def approve_review(id):
    # Find the review with the given ID
    review = Review.query.get(id)
    if review:
        try:
            # Update the payment status to 'Approved'
            review.payment_status = 'Approved'
            db.session.commit()
            
            # Check if the invoice number already exists in the Invoice table
            existing_invoice = Invoice.query.filter_by(invoice_number=review.invoice_no).first()
            if existing_invoice:
                #flash('Payment for Invoice No: {} already exists in the Invoice table.'.format(review.invoice_no), 'info')
                response_message= "Payment for Invoice No: {} already exists in the Payment scheduler.".format(review.invoice_no)
                return jsonify({"message": response_message}), 200
            else:
                # If payment is approved and invoice number doesn't exist, add the corresponding record to the Invoice table
                new_invoice = Invoice(
                    invoice_number=review.invoice_no,
                    vendor=review.vendor_name,
                    due_date=datetime.now().strftime("%Y-%m-%d"),
                    invoice_total=review.invoice_total,
                    po_no=review.po_no,
                    po_total=review.po_total,
                    payment_status='Approved'  # Assuming payment is approved at this point
                )
                db.session.add(new_invoice)
                db.session.commit()
                #flash('Payment for Invoice No: {} has been approved and added to the Invoice table.'.format(review.invoice_no), 'success')
                # Return a success message
                response_message = "Payment for Invoice No: {} has been approved and added to the payment scheduler.".format(review.invoice_no)
                return jsonify({"message": response_message}), 200
        except Exception as e:
            flash('An error occurred while approving the payment: {}'.format(str(e)), 'error')
            return redirect(url_for('fetch_Review_data'))
    else:
        flash('Review not found', 'error')
        return redirect(url_for('fetch_Review_data'))
    
# Reject manual review if approver finds it not ok
@app.route('/reject_review/<int:id>', methods=['GET'])
def reject_review(id):
    # Find the review with the given ID
    review = Review.query.get(id)
    if review:
        try:
            review.payment_status = 'Rejected'
            db.session.commit()
            # Delete the record from the Invoice table corresponding to the rejected review
            invoice = Invoice.query.filter_by(invoice_number=review.invoice_no, po_no=review.po_no).first()

            if invoice:
                db.session.delete(invoice)
                db.session.commit()
                
            # Delete the review record
            #db.session.delete(review)
            #db.session.commit()
            
            #flash('Payment for Invoice No: {} has been rejected and removed.'.format(review.invoice_no), 'success')
            #return redirect(url_for('fetch_Review_data'))  # Redirect to review page
            response_message = "Payment for Invoice No: {} has been rejected.".format(review.invoice_no)
            return jsonify({"message": response_message}), 200
        except Exception as e:
            flash('An error occurred while rejecting the payment: {}'.format(str(e)), 'error')
            return redirect(url_for('fetch_Review_data'))
    else:
        flash('Review not found', 'error')
        return redirect(url_for('fetch_Review_data'))

    
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

# invoice file download
@app.route('/download_pdf', methods=['GET'])
def download_pdf():
    invoice_id = request.args.get('invoice_id')
    if invoice_id:
        entry = db.session.get(LLMHistory, invoice_id)
        if entry:
            pdf_data = entry.invoice_file_data
            print("Dinesh",pdf_data)
            if pdf_data:
                pdf_data = io.BytesIO(pdf_data)
                print("Dinesh",pdf_data)

                # You may need to adjust the content type and headers based on your PDF file
                return send_file(
                    io.BytesIO(pdf_data),
                    mimetype='application/pdf',
                    attachment_filename='invoice.pdf',
                    as_attachment=True
                )
    
    # If invoice ID is not provided or entry does not exist, return an error message
    return "Invoice not found or PDF data missing."

#add hardcoded vendor list
def add_hardcoded_vendor_data():
    # Define the data to be added
    vendor_data = [
        #{"vendor_name": "DEMO - Sliced Invoices", "account_details": "191919"},
        {"vendor_name": "Shah & Sons pvt ltd.", "account_details": "18999"},
        # Add more vendors as needed
    ]

    # Loop through the vendor data and create Vendor instances
    for data in vendor_data:
        vendor = Vendor(**data)
        db.session.add(vendor)

    # Commit the changes to the database
    db.session.commit()


#detect grammatical fraud or vendor not in the list fraud.
def detectFraud(languageFraud, vendor_name):
    fraud_detected = False
    fraud_message = ""  # Initialize fraud message

    # Query the Vendor table to check if the provided Vendor name exists
    existing_vendor = Vendor.query.filter_by(vendor_name=vendor_name).first()
    
    if existing_vendor is None and languageFraud:
        # If both conditions are true, set the fraud flag to True and combine messages
        fraud_detected = True
        fraud_message = "Vendor not approved and Unusual Invoice writing style"
    elif existing_vendor is None:
        # If the Vendor name does not exist, set the fraud flag to True and set message
        fraud_detected = True
        fraud_message = "Vendor not approved"
    elif languageFraud:
        # If languageFraud is true, set the fraud flag to True and set message
        fraud_detected = True
        fraud_message = "Unusual Invoice writing style"

    return fraud_detected, fraud_message




if __name__ == '__main__':
    app.secret_key = 'your_secret_key'  # Add a secret key for flash messages
    create_tables()
    app.run(debug=True)

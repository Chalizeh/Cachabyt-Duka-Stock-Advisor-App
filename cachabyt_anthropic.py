# ============================================================
# CACHABYT DUKA STOCK ADVISOR
# WeCan Academy Season 12 - Group Project (60 marks)
# Group members: Charles_1016, Eclare_2545 and Caleb_2528
# Purpose: Manage canteen stock, sales and student orders, with
#          an AI advisor that holds a conversation WITH MEMORY,
#          checks every answer as JSON, and saves a summary.
# ============================================================

import json                                       # Handles saving and reading application data as JSON.
import os                                         # Reads environment variables such as the API key.
from pathlib import Path                          # Creates and manages file paths in a safe way.
from datetime import datetime                     # Records transaction dates and session times.

from dotenv import load_dotenv                    # Loads the Anthropic API key from a hidden .env file.

try:                                              # Checks whether the Anthropic package is installed.
    from anthropic import Anthropic               # Imports the Anthropic Claude client library.
except ImportError:                               # Runs when the package is unavailable on this machine.
    Anthropic = None                              # Allows the application to run using a local fallback.


# ============================================================
# 1. APPLICATION SETTINGS
# Purpose: Set up folders, files and payment information.
# ============================================================

BASE_DIR = Path(__file__).parent                  # Finds the folder this script lives in.
DATA_DIR = BASE_DIR / "data"                      # Defines where application data is stored.
SESSION_DIR = BASE_DIR / "sessions"               # Defines where AI conversations are stored.

DATA_DIR.mkdir(exist_ok=True)                     # Creates the data folder if it does not exist.
SESSION_DIR.mkdir(exist_ok=True)                  # Creates the sessions folder if it does not exist.

STOCK_FILE = DATA_DIR / "stock.json"              # Stores product names, prices and quantities.
ORDERS_FILE = DATA_DIR / "orders.json"            # Stores student orders and payment details.
SALES_FILE = DATA_DIR / "sales.json"              # Stores normal counter sales.

LOW_STOCK_LEVEL = 50                              # Alerts the owner when stock reaches 50 or below.

MPESA_NUMBER = "339229"                           # Canteen M-Pesa payment number.
MPESA_ACCOUNT = "Cachabyt Canteen"                # Name displayed in payment instructions.
PAYMENT_METHODS = ["M-Pesa Till", "M-Pesa Paybill"]  # Payment methods offered to students.


# ============================================================
# 2. STARTER PRODUCTS
# Purpose: Create initial stock when the application runs
# for the first time. Existing stock is not overwritten.
# ============================================================

STARTER_STOCK = {                                 # Stores the initial canteen products.
    "samosa": {"price": 10, "quantity": 400},      # Samosa price and available quantity.
    "smokie sausage": {"price": 40, "quantity": 300},  # Smoki sausage details.
    "boiled egg": {"price": 30, "quantity": 250},  # Boiled egg details.
    "mandazi": {"price": 10, "quantity": 500},     # Mandazi details.
    "chapati": {"price": 20, "quantity": 350},     # Chapati details.
    "smocha": {"price": 60, "quantity": 250},      # Smocha details.
    "tea": {"price": 20, "quantity": 400},         # Tea details.
    "soda": {"price": 80, "quantity": 300},        # Soda details.
    "biscuits": {"price": 10, "quantity": 500},    # Biscuits details.
    "water": {"price": 50, "quantity": 300}        # Water details.
}


# ============================================================
# 3. LOAD AND SAVE DATA
# Purpose: Read information from JSON files and save changes.
# ============================================================

def load_data(file_path, default):                # Defines a reusable function for loading data.
    if not file_path.exists():                    # Checks whether the file exists.
        return default                            # Uses default information if the file is missing.

    try:                                          # Attempts to read the file.
        with open(file_path, "r", encoding="utf-8") as file:  # Opens the file for reading.
            return json.load(file)                # Converts JSON information into Python data.
    except (json.JSONDecodeError, OSError):       # Handles damaged or inaccessible files.
        print(f"Warning: Could not read {file_path.name}.")  # Informs the user of the problem.
        return default                            # Returns default information instead of crashing.


def save_data(file_path, data):                   # Defines a reusable function for saving data.
    temporary_file = file_path.with_suffix(".tmp")  # Creates a temporary file path for safe saving.

    with open(temporary_file, "w", encoding="utf-8") as file:  # Opens the temporary file for writing.
        json.dump(data, file, indent=4)           # Saves information in readable JSON format.

    temporary_file.replace(file_path)             # Replaces the old file with the updated file.


# ============================================================
# 4. LOAD APPLICATION RECORDS
# Purpose: Load existing products, orders and sales.
# ============================================================

if not STOCK_FILE.exists():                      # Checks whether stock has been saved before.
    save_data(STOCK_FILE, STARTER_STOCK)          # Creates the initial stock file.

stock = load_data(STOCK_FILE, STARTER_STOCK.copy())  # Loads saved stock information.
orders = load_data(ORDERS_FILE, [])               # Loads student orders or starts with an empty list.
sales = load_data(SALES_FILE, [])                 # Loads sales records or starts with an empty list.

if not isinstance(stock, dict):                  # Checks that stock has the correct data structure.
    stock = STARTER_STOCK.copy()                  # Restores starter stock if the file is invalid.

if not isinstance(orders, list):                 # Checks that orders are stored as a list.
    orders = []                                   # Starts with an empty order list if necessary.

if not isinstance(sales, list):                  # Checks that sales are stored as a list.
    sales = []                                    # Starts with an empty sales list if necessary.


# ============================================================
# 5. GENERAL HELPER FUNCTIONS
# Purpose: Provide functions used throughout the application.
# ============================================================

def now():                                        # Defines a function for recording transaction time.
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Returns the current date and time.


def clean_name(name):                             # Standardises product names entered by users.
    return name.strip().lower()                   # Removes extra spaces and changes text to lowercase.


def find_order(order_id):                         # Searches for an order using its order number.
    for order in orders:                          # Checks every saved order.
        if str(order.get("order_id")) == str(order_id):  # Compares order numbers safely.
            return order                          # Returns the matching order.
    return None                                   # Returns nothing if the order does not exist.


def next_order_id():                              # Generates a new order number.
    numbers = []                                  # Creates a list for existing order numbers.

    for order in orders:                          # Checks every saved order.
        try:                                      # Handles order numbers saved in different formats.
            numbers.append(int(order.get("order_id", 0)))  # Adds valid order numbers.
        except (ValueError, TypeError):           # Skips invalid order numbers.
            continue                              # Moves to the next order.

    return max(numbers, default=0) + 1            # Returns the next available order number.


def get_order_items(order):                       # Supports both new and older order records.
    if isinstance(order.get("items"), list):      # Checks whether the order has multiple products.
        return order["items"]                     # Returns the saved product list.

    if order.get("product"):                      # Checks whether it is an older single-product order.
        return [{                                 # Converts the old format into a product list.
            "product": order.get("product", ""),      # Copies the old product name.
            "quantity": order.get("quantity", 0),     # Copies the old quantity.
            "unit_price": order.get("unit_price", 0)  # Copies the old unit price.
        }]

    return []                                     # Returns an empty list if no products are recorded.


# ============================================================
# 6. STOCK MANAGEMENT
# Purpose: Display products, check availability and manage stock.
# ============================================================

def view_stock():                                 # Displays all available products and prices.
    print("\n========== CACHABYT CANTEEN STOCK ==========")  # Prints the stock heading.

    print(f"{'PRODUCT':20} {'PRICE (KSH)':12} {'QUANTITY':10} STATUS")  # Prints table headings.

    for product, details in stock.items():        # Goes through every product.
        price = details.get("price", 0)           # Gets the product price.
        quantity = details.get("quantity", 0)     # Gets the available quantity.

        status = "LOW STOCK" if quantity <= LOW_STOCK_LEVEL else "AVAILABLE"  # Checks stock level.

        print(f"{product.title():20} {price:<12} {quantity:<10} {status}")  # Displays product details.

    print("==========================================")  # Closes the stock display.


def check_product(product):                       # Checks the availability of one product.
    product = clean_name(product)                 # Standardises the product name.

    if product not in stock:                      # Checks whether the product exists.
        return "Product not found."               # Informs the user if it does not exist.

    item = stock[product]                         # Retrieves the product details.

    return f"{product.title()} costs KSh {item['price']} and {item['quantity']} units are available."  # Returns details.


def add_stock(product, quantity):                 # Adds newly received stock.
    product = clean_name(product)                 # Standardises the product name.

    if product not in stock:                      # Checks whether the product is registered.
        return "Product not found. Add the product first."  # Prevents updating an unknown product.

    if quantity <= 0:                             # Checks that the quantity is positive.
        return "Enter a quantity greater than zero."  # Rejects invalid quantities.

    stock[product]["quantity"] += quantity        # Adds the received quantity to existing stock.
    save_data(STOCK_FILE, stock)                  # Saves the updated stock.

    return f"{product.title()} stock is now {stock[product]['quantity']}."  # Confirms the update.


def add_new_product():                            # Allows the owner to register a new product.
    product = clean_name(input("New product name: "))  # Collects and standardises the product name.

    if not product:                               # Checks that a product name was entered.
        print("Product name is required.")        # Informs the owner of the missing name.
        return                                    # Stops the function.

    if product in stock:                          # Checks whether the product already exists.
        print("This product already exists.")     # Prevents duplicate product records.
        return                                    # Stops the function.

    try:                                          # Validates the price and starting quantity.
        price = float(input("Selling price (KSh): "))   # Collects the selling price.
        quantity = int(input("Opening quantity: "))     # Collects the opening quantity.

        if price <= 0 or quantity < 0:            # Rejects invalid values.
            print("Enter a positive price and a valid quantity.")  # Explains the error.
            return                                # Stops the function.

        stock[product] = {"price": price, "quantity": quantity}  # Adds the new product.
        save_data(STOCK_FILE, stock)              # Saves the new product information.
        print("Product added successfully.")      # Confirms that the product was registered.

    except ValueError:                            # Handles letters or invalid numbers.
        print("Enter valid numbers for price and quantity.")  # Displays an error message.


def low_stock_report():                           # Identifies products requiring restocking.
    low_items = []                                # Creates a list for products with low stock.

    for product, details in stock.items():        # Checks every product.
        if details["quantity"] <= LOW_STOCK_LEVEL:  # Compares quantity with the alert level.
            low_items.append(f"{product.title()}: {details['quantity']} remaining")  # Records low stock.

    if not low_items:                             # Checks whether any products need restocking.
        return "All products have sufficient stock."  # Reports that stock is adequate.

    return "LOW STOCK ALERT\n" + "\n".join(low_items)  # Displays all low-stock products.


# ============================================================
# 7. SALES MANAGEMENT
# Purpose: Record counter sales and calculate sales revenue.
# ============================================================

def record_sale(product, quantity):               # Records a sale made directly at the canteen.
    product = clean_name(product)                 # Standardises the product name.

    if product not in stock:                      # Checks whether the product exists.
        return "Product not found."               # Stops an invalid sale.

    if quantity <= 0:                             # Checks whether the quantity is valid.
        return "Quantity must be greater than zero."  # Rejects invalid quantities.

    if quantity > stock[product]["quantity"]:     # Checks whether enough stock is available.
        return "Insufficient stock."              # Prevents selling more than available.

    price = stock[product]["price"]               # Gets the product selling price.
    total = price * quantity                      # Calculates the sale amount.

    stock[product]["quantity"] -= quantity        # Deducts the quantity sold.

    sale = {                                      # Creates a record of the sale.
        "product": product,                       # Saves the product name.
        "quantity": quantity,                     # Saves the quantity sold.
        "unit_price": price,                      # Saves the selling price.
        "total": total,                           # Saves the total amount.
        "date": now()                             # Saves the sale date and time.
    }

    sales.append(sale)                            # Adds the sale to the sales records.
    save_data(STOCK_FILE, stock)                  # Saves the updated stock.
    save_data(SALES_FILE, sales)                  # Saves the sale record.

    return f"Sale recorded. Total: KSh {total}. Remaining stock: {stock[product]['quantity']}"  # Confirms sale.


def sales_report():                               # Calculates the total recorded sales revenue.
    total = sum(float(sale.get("total", 0)) for sale in sales)  # Adds all counter sales.

    paid_orders = sum(                            # Calculates revenue from verified student orders.
        float(order.get("total", 0))              # Reads the amount paid for each order.
        for order in orders                       # Checks every student order.
        if order.get("payment_status") == "Verified"  # Includes only verified payments.
    )

    print("\n========== SALES REPORT ==========")  # Displays the report heading.
    print(f"Counter sales: KSh {total:.2f}")       # Displays counter sales revenue.
    print(f"Verified student orders: KSh {paid_orders:.2f}")  # Displays paid online-order revenue.
    print(f"Total recorded revenue: KSh {total + paid_orders:.2f}")  # Displays combined revenue.
    print("==================================")        # Closes the report.


# ============================================================
# 8. CUSTOMER ORDERING
# Purpose: Allow customers to select several products in one order.
# ============================================================

def place_customer_order():                       # Starts the customer ordering process.
    print("\n========== CUSTOMER ORDER ==========")  # Displays the ordering heading.

    view_stock()                                  # Shows products and quantities before ordering.

    customer = input("Customer name: ").strip()   # Collects the customer's name.
    phone = input("Phone number: ").strip()       # Collects the customer's phone number.

    if not customer or not phone:                 # Checks that both details are provided.
        print("Name and phone number are required.")  # Explains the missing details.
        return                                    # Stops the ordering process.

    cart = []                                     # Creates an empty shopping cart.

    while True:                                   # Allows the customer to add several products.
        product = clean_name(input("Product name (or 'done' to finish): "))  # Gets product choice.

        if product == "done":                     # Checks whether the customer has finished selecting.
            break                                 # Ends product selection.

        if product not in stock:                  # Checks whether the product exists.
            print("Product not found.")           # Informs the customer.
            continue                              # Asks for another product.

        try:                                      # Validates the requested quantity.
            quantity = int(input("Quantity: "))   # Collects the required quantity.

            if quantity <= 0:                     # Rejects zero or negative quantities.
                print("Quantity must be greater than zero.")  # Explains the error.
                continue                          # Returns to product selection.

            already_selected = sum(               # Calculates the quantity already in the cart.
                item["quantity"]                  # Reads each selected quantity.
                for item in cart                  # Checks the current cart.
                if item["product"] == product     # Includes only the selected product.
            )

            if already_selected + quantity > stock[product]["quantity"]:  # Checks available stock.
                print("Not enough stock for that quantity.")  # Warns the customer.
                continue                          # Returns to product selection.

            cart.append({                         # Adds the product to the shopping cart.
                "product": product,               # Saves the product name.
                "quantity": quantity,             # Saves the requested quantity.
                "unit_price": stock[product]["price"]  # Saves the current selling price.
            })

            print(f"{product.title()} added to your order.")  # Confirms the selection.

        except ValueError:                        # Handles invalid quantity entries.
            print("Enter a valid whole number.")  # Requests a valid quantity.

    if not cart:                                  # Checks whether the customer selected any products.
        print("No products were selected.")       # Informs the customer.
        return                                    # Stops the order process.

    total = sum(item["quantity"] * item["unit_price"] for item in cart)  # Calculates the order total.

    order = {                                     # Creates the customer's order record.
        "order_id": next_order_id(),              # Assigns a unique order number.
        "customer": customer,                     # Saves the customer's name.
        "phone": phone,                           # Saves the customer's phone number.
        "items": cart,                            # Saves all selected products.
        "total": total,                           # Saves the amount payable.
        "payment_status": "Awaiting payment",     # Sets the initial payment status.
        "payment_method": "",                     # Leaves payment method blank initially.
        "payment_reference": "",                  # Leaves the transaction reference blank initially.
        "payment_proof": "",                      # Leaves proof details blank initially.
        "status": "Awaiting payment",             # Sets the initial order status.
        "created_at": now()                       # Records the order date and time.
    }

    orders.append(order)                          # Adds the order to the order records.
    save_data(ORDERS_FILE, orders)                # Saves the order.

    print("\n========== ORDER SUMMARY ==========")  # Displays the order summary.
    print(f"Order number: #{order['order_id']}")  # Displays the unique order number.

    for item in cart:                             # Displays each selected product.
        amount = item["quantity"] * item["unit_price"]  # Calculates the line total.
        print(f"{item['product'].title()} x {item['quantity']} = KSh {amount}")  # Shows the item cost.

    print(f"TOTAL: KSh {total}")                  # Displays the full amount payable.

    print("\n========== M-PESA PAYMENT ==========")  # Displays payment instructions.
    print(f"Payment number: {MPESA_NUMBER}")      # Displays the canteen payment number.
    print(f"Account name: {MPESA_ACCOUNT}")       # Displays the account name.
    print("Available methods: M-Pesa Till or Paybill")  # Lists the available methods.
    print("Submit your transaction code after making payment.")  # Explains the next step.
    print("Your order is not confirmed until payment is verified.")  # Explains payment verification.


# ============================================================
# 9. CUSTOMER PAYMENT SUBMISSION
# Purpose: Allow customers to submit their M-Pesa transaction code.
# ============================================================

def submit_payment():                             # Collects payment information for an existing order.
    try:                                          # Validates the order number.
        order_id = int(input("Enter order number: "))  # Collects the customer's order number.
    except ValueError:                            # Handles invalid order numbers.
        print("Enter a valid order number.")      # Displays an error message.
        return                                    # Stops the function.

    order = find_order(order_id)                  # Searches for the order.

    if order is None:                             # Checks whether the order exists.
        print("Order not found.")                 # Informs the customer.
        return                                    # Stops the function.

    if order.get("status") != "Awaiting payment":  # Checks whether the order is still unpaid.
        print("This order is not awaiting payment.")  # Prevents changing completed orders.
        return                                    # Stops the function.

    print("1. M-Pesa Till")                       # Displays the Till option.
    print("2. M-Pesa Paybill")                    # Displays the Paybill option.

    choice = input("Choose payment method: ").strip()  # Collects the selected method.

    if choice == "1":                             # Checks whether Till was selected.
        method = "M-Pesa Till"                    # Saves the Till method.
    elif choice == "2":                           # Checks whether Paybill was selected.
        method = "M-Pesa Paybill"                 # Saves the Paybill method.
    else:                                         # Handles invalid payment choices.
        print("Invalid payment method.")          # Displays an error.
        return                                    # Stops the function.

    reference = input("Enter M-Pesa transaction code: ").strip().upper()  # Collects the transaction code.
    proof = input("Enter screenshot path or proof description (optional): ").strip()  # Collects optional proof.

    if not reference:                             # Checks that a transaction code was entered.
        print("Transaction code is required.")    # Informs the student.
        return                                    # Stops the function.

    for other in orders:                          # Checks other orders for duplicate transaction codes.
        if other.get("payment_reference", "").upper() == reference:  # Compares saved references.
            print("This transaction code has already been submitted.")  # Rejects duplicate reference.
            return                                # Stops the function.

    order["payment_method"] = method              # Saves the payment method.
    order["payment_reference"] = reference        # Saves the M-Pesa transaction code.
    order["payment_proof"] = proof                # Saves the proof description or file path.
    order["payment_status"] = "Verification pending"  # Marks payment as awaiting seller verification.
    order["proof_submitted_at"] = now()           # Records when the proof was submitted.

    save_data(ORDERS_FILE, orders)                # Saves the updated order.

    print("Payment details submitted successfully.")  # Confirms submission.
    print("Your payment is awaiting verification by the canteen.")  # Explains the next step.


# ============================================================
# 10. VIEW CUSTOMER ORDERS
# Purpose: Allow the owner to see orders and their payment status.
# ============================================================

def view_orders():                                # Displays all customer orders.
    print("\n========== CUSTOMER ORDERS ==========")  # Displays the section heading.

    if not orders:                                # Checks whether there are saved orders.
        print("No orders have been placed yet.")  # Displays an empty-order message.
        return                                    # Stops the function.

    for order in orders:                          # Goes through every saved order.
        print("\n----------------------------------")  # Separates order records.
        print(f"Order number: #{order.get('order_id', 'Unknown')}")  # Displays the order number.
        print(f"Customer: {order.get('customer', 'Unknown')}")  # Displays the customer name.
        print(f"Phone: {order.get('phone', 'Not provided')}")  # Displays the phone number.

        for item in get_order_items(order):       # Displays every product in the order.
            print(f"{item.get('product', 'Unknown').title()} x {item.get('quantity', 0)}")  # Shows product and quantity.

        print(f"Total: KSh {order.get('total', 0)}")  # Displays the amount payable.
        print(f"Payment method: {order.get('payment_method') or 'Not submitted'}")  # Displays payment method.
        print(f"Reference: {order.get('payment_reference') or 'Not submitted'}")  # Displays transaction code.
        print(f"Payment status: {order.get('payment_status', 'Awaiting payment')}")  # Displays payment status.
        print(f"Order status: {order.get('status', 'Awaiting payment')}")  # Displays order progress.
        print(f"Date: {order.get('created_at', 'Not recorded')}")  # Displays order date.

    print("----------------------------------")       # Closes the order display.

# ============================================================
# 11. PAYMENT VERIFICATION AND PAYMENT REMINDERS
# Purpose: Allow the owner to verify payments and remind students
# to submit missing M-Pesa payment details.
# ============================================================

def send_payment_reminder(order):                 # Creates a payment reminder for a student.
    customer_name = order.get("customer", "Student")  # Retrieves the customer's name safely.
    phone = order.get("phone", "Not provided")    # Retrieves the customer's phone number.
    order_id = order.get("order_id", "Unknown")   # Retrieves the order number.
    total = order.get("total", 0)                 # Retrieves the amount the customer should pay.

    message = (                                   # Creates the reminder message.
        f"Hello {customer_name}, your order #{order_id} at Cachabyt Canteen "
        f"is still awaiting payment details. Please make payment of "
        f"KSh {total} using M-Pesa Till or Paybill number {MPESA_NUMBER} "
        f"under account name {MPESA_ACCOUNT}. After making payment, "
        f"please return to the Cachabyt Duka system and use Option 4 "
        f"under the Customer Menu to submit your M-Pesa transaction code. "
        f"Your order will only be confirmed after the canteen verifies "
        f"that the payment has been received. Thank you."
    )

    order["payment_reminder_sent_at"] = now()     # Records when the reminder was generated.
    order["payment_reminder_status"] = "Reminder generated"  # Records the reminder status.

    save_data(ORDERS_FILE, orders)                # Saves the reminder record.

    print("\n========== PAYMENT REMINDER ==========")  # Displays the reminder heading.
    print(f"Customer: {customer_name}")           # Displays the customer receiving the reminder.
    print(f"Phone number: {phone}")               # Displays the customer's phone number.
    print(f"Order number: #{order_id}")           # Displays the order number.
    print(f"Amount payable: KSh {total}")         # Displays the outstanding amount.
    print("--------------------------------------")  # Separates the reminder details.
    print(message)                                # Displays the complete reminder message.
    print("--------------------------------------")  # Closes the reminder message.
    print("Reminder generated successfully.")     # Confirms that the reminder was prepared.
    print("Copy and send this message to the customer.")  # Instructs the seller to send it manually.
    print("The order remains unconfirmed until payment is verified.")  # Explains the order status.


def verify_payment():                             # Starts the owner payment-verification process.
    try:                                          # Validates the order number.
        order_id = int(input("Enter order number to verify: "))  # Collects the order number.
    except ValueError:                            # Handles invalid order numbers.
        print("Enter a valid order number.")      # Displays an error message.
        return                                    # Stops the function.

    order = find_order(order_id)                  # Searches for the selected order.

    if order is None:                             # Checks whether the order exists.
        print("Order not found.")                 # Informs the owner.
        return                                    # Stops the function.

    if order.get("status") == "Cancelled":        # Checks whether the order was cancelled.
        print("This order has been cancelled.")   # Prevents verification of cancelled orders.
        return                                    # Stops the function.

    if order.get("payment_status") == "Verified":  # Checks whether payment was already verified.
        print("This payment has already been verified.")  # Prevents duplicate stock deduction.
        return                                    # Stops the function.

    if order.get("status") in ["Confirmed", "Ready for collection", "Collected/Delivered"]:
        print("This order has already been processed.")  # Prevents processing an existing order again.
        return                                    # Stops the function.

    reference = order.get("payment_reference", "").strip()  # Retrieves the submitted transaction code.
    method = order.get("payment_method", "").strip()  # Retrieves the submitted payment method.

    if not reference or not method:               # Checks whether the student submitted payment details.
        print("\nThe student has not submitted complete payment details.")  # Explains the problem.
        print("The system will prepare a payment reminder.")  # Explains the next action.

        send_payment_reminder(order)              # Generates and records the student's reminder.

        print("\nOrder status: Awaiting payment")  # Displays the current order status.
        print("Payment status: Awaiting payment")  # Confirms that payment is still pending.
        print("Stock has NOT been deducted.")     # Confirms that stock remains unchanged.
        print("Order has NOT been confirmed.")    # Confirms that processing has not started.
        return                                    # Stops verification until details are submitted.

    if order.get("payment_status") != "Verification pending":  # Checks whether details are awaiting review.
        print("Payment details are not ready for verification.")  # Explains the current status.
        return                                    # Stops the function.

    print("\n========== PAYMENT DETAILS ==========")  # Displays the verification heading.
    print(f"Customer: {order.get('customer', 'Unknown')}")  # Displays the customer's name.
    print(f"Phone: {order.get('phone', 'Unknown')}")  # Displays the customer's phone number.
    print(f"Order number: #{order.get('order_id', 'Unknown')}")  # Displays the order number.
    print(f"Expected amount: KSh {order.get('total', 0)}")  # Displays the amount expected.
    print(f"Payment method: {method}")            # Displays the selected payment method.
    print(f"Transaction code: {reference}")       # Displays the submitted transaction code.
    print(f"Payment proof: {order.get('payment_proof') or 'Not provided'}")  # Displays optional proof.

    print("\nCheck the actual M-Pesa account or statement.")  # Reminds the seller to check actual receipt.
    print("Confirm that the transaction code and amount match.")  # Reminds the seller to check the payment.

    answer = input("Have you confirmed receipt of the correct payment? (yes/no): ").strip().lower()  # Requests seller confirmation.

    if answer != "yes":                           # Checks whether the seller confirmed receipt.
        print("Payment remains unverified. Stock has not been deducted.")  # Keeps the order pending.
        return                                    # Stops the function.

    items = get_order_items(order)                # Retrieves all products in the order.

    if not items:                                 # Checks whether the order contains products.
        print("This order has no valid product details.")  # Reports incomplete order information.
        return                                    # Stops verification.

    for item in items:                            # Checks stock for every ordered product.
        if not isinstance(item, dict):            # Checks that each item is a valid dictionary.
            print("Invalid product information found in this order.")  # Reports damaged order data.
            return                                # Stops verification.

        product = clean_name(item.get("product", ""))  # Standardises the product name.

        try:                                      # Validates the ordered quantity.
            quantity = int(item.get("quantity", 0))  # Reads the quantity ordered.
        except (ValueError, TypeError):           # Handles invalid quantity records.
            print("Invalid quantity recorded for an ordered product.")  # Reports the problem.
            return                                # Stops verification.

        if product not in stock:                  # Checks whether the product still exists.
            print(f"Product {product} is missing from stock records.")  # Reports the missing product.
            return                                # Stops verification.

        if quantity <= 0 or stock[product]["quantity"] < quantity:  # Checks available stock.
            print(f"Insufficient stock for {product}. Contact the student.")  # Reports insufficient stock.
            return                                # Stops verification.

    for item in items:                            # Deducts stock after every product passes validation.
        product = clean_name(item["product"])     # Retrieves the product name.
        quantity = int(item["quantity"])          # Retrieves the quantity ordered.
        stock[product]["quantity"] -= quantity    # Deducts the ordered quantity.

    order["payment_status"] = "Verified"          # Marks the payment as verified.
    order["status"] = "Confirmed"                 # Confirms the student's order.
    order["payment_verified_at"] = now()          # Records the payment verification time.

    save_data(STOCK_FILE, stock)                  # Saves the updated stock quantities.
    save_data(ORDERS_FILE, orders)                # Saves the confirmed order.

    print("\nPayment verified successfully.")    # Confirms successful payment verification.
    print(f"Order #{order_id} is now confirmed.")  # Confirms the order status.
    print("Stock has been updated.")              # Confirms that stock was deducted.


# ============================================================
# 12. ORDER COLLECTION
# Purpose: Track orders after payment has been verified.
# ============================================================

def update_order_status():                        # Allows the owner to update order progress.
    try:                                          # Validates the order number.
        order_id = int(input("Enter order number: "))  # Collects the order number.
    except ValueError:                            # Handles invalid order numbers.
        print("Enter a valid order number.")      # Displays an error.
        return                                    # Stops the function.

    order = find_order(order_id)                  # Finds the selected order.

    if order is None:                             # Checks whether the order exists.
        print("Order not found.")                 # Informs the owner.
        return                                    # Stops the function.

    if order.get("payment_status") != "Verified":  # Checks whether payment has been verified.
        print("Payment must be verified first.")  # Prevents collection of unpaid orders.
        return                                    # Stops the function.

    print("1. Ready for collection")              # Offers the first order status.
    print("2. Collected/Delivered")               # Offers the final order status.

    choice = input("Choose status: ").strip()     # Collects the selected status.

    if choice == "1" and order.get("status") == "Confirmed":  # Checks the permitted first transition.
        order["status"] = "Ready for collection"  # Updates the order status.
    elif choice == "2" and order.get("status") == "Ready for collection":  # Checks the permitted final transition.
        order["status"] = "Collected/Delivered"   # Marks the order as collected or delivered.
    else:                                         # Handles invalid status changes.
        print("Invalid status change. Check the current order status.")  # Explains the problem.
        return                                    # Stops the function.

    order["updated_at"] = now()                   # Records the status update time.
    save_data(ORDERS_FILE, orders)                # Saves the updated order.
    print(f"Order updated to: {order['status']}")  # Confirms the update.


# ============================================================
# 13. AI STOCK ADVISOR - CONVERSATION WITH MEMORY
# Purpose: Hold a conversation of at least 4 turns with Anthropic Claude.
# The FULL message list is stored and sent with EVERY API call,
# so each answer uses what was said earlier. The model must reply
# in JSON; every reply is parsed and checked, retried once on
# failure, and a clear message is shown if it still fails. When
# the user ends the session, a final AI call writes a summary,
# and the whole conversation plus summary is saved to a dated
# file. A local fallback keeps the tool usable without internet.
# ============================================================

load_dotenv()                                     # Loads environment variables from the hidden .env file.
API_KEY = os.getenv("ANTHROPIC_API_KEY")           # Reads the Anthropic API key (never hard-coded).
MODEL_NAME = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")  # Reads the model name, with a safe default.

ai_client = None                                  # Starts with no active Anthropic connection.

if Anthropic and API_KEY:                         # Checks whether Anthropic and its API key are available.
    try:                                          # Attempts to connect to Anthropic Claude.
        ai_client = Anthropic(api_key=API_KEY)     # Creates the Anthropic client.
        print("Anthropic Claude AI is connected.")  # Confirms successful connection.
    except Exception as error:                    # Handles connection errors.
        print("Anthropic connection failed:", error)  # Displays the connection problem.
elif not API_KEY:                                 # Checks whether the key is missing.
    print("No ANTHROPIC_API_KEY found in .env - the AI advisor will use local answers.")  # Warns the user.


# --- 13A. R-T-C-C-O PROMPTS (documented in report section 04) ---

SYSTEM_PROMPT = """
Role: You are Cachabyt Duka Stock Advisor, a friendly assistant for Cachabyt Canteen, a school canteen in Kenya.
Task: Answer the user's question about canteen stock, prices, ordering, M-Pesa payment steps or restocking, using the live stock data provided and everything the user has said earlier in this conversation.
Context: You are given the current stock list with prices and quantities, a low-stock report, and the full conversation so far. The canteen sells snacks such as samosas, smoki sausages, eggs and smocha to students. Payment is by M-Pesa Till or Paybill number 339229 (account name: Cachabyt Canteen), and an order is confirmed only after the seller verifies the M-Pesa transaction code.
Constraints: Use only the stock data provided - never invent a price or quantity. Never claim a payment was received or an order confirmed, because only the seller can verify payments. If the answer is not in the data, say so honestly. Use what the user said in earlier turns so you do not repeat questions or contradict yourself.
Output: Reply with ONLY a JSON object and no text before or after it, in exactly this shape:
{"answer": "your short, helpful, friendly answer here"}
"""

SUMMARY_PROMPT = """
Role: You are Cachabyt Duka Stock Advisor writing an end-of-session report for the canteen owner.
Task: Read the whole conversation below and summarise what the user asked and what was advised or decided.
Context: The conversation is between a canteen user (owner or customer) and the stock advisor. Prices and quantities mentioned came from the live stock data and may have changed since the conversation.
Constraints: Base the summary only on the conversation provided - do not invent events or numbers. Keep the summary under 150 words. List the main topics and suggest sensible next actions for the canteen.
Output: Reply with ONLY a JSON object and no text before or after it, in exactly this shape:
{"summary": "a 2-4 sentence overview of the whole session", "topics": ["topic one", "topic two"], "recommended_actions": ["action one", "action two"]}
"""

REQUIRED_CHAT_FIELDS = ["answer"]                 # Lists the fields every normal AI reply must contain.
REQUIRED_SUMMARY_FIELDS = ["summary", "topics", "recommended_actions"]  # Lists the fields the final summary must contain.
MAX_ATTEMPTS = 2                                  # Allows the first try plus exactly one retry.


def local_ai_answer(question):                    # Provides basic AI-style answers without Anthropic Claude.
    question = question.lower()                   # Standardises the question.

    if "low stock" in question or "restock" in question:  # Checks for restocking questions.
        return low_stock_report()                 # Returns the low-stock report.

    if "price" in question or "cost" in question:  # Checks for price questions.
        return "\n".join(                         # Creates a list of product prices.
            f"{name.title()}: KSh {details['price']}"  # Formats each product price.
            for name, details in stock.items()    # Goes through all products.
        )

    if "stock" in question or "available" in question:  # Checks for stock questions.
        return "\n".join(                         # Creates a stock summary.
            f"{name.title()}: {details['quantity']} available"  # Formats product quantities.
            for name, details in stock.items()    # Goes through all products.
        )

    for name in stock:                            # Checks whether a product is mentioned.
        if name in question:                      # Matches the product name with the question.
            return check_product(name)            # Returns the product's price and quantity.

    return "I can help with stock, prices, product availability and restocking."  # Default response.


def stock_context_block():                        # Builds the live data block inserted into the system prompt.
    stock_lines = "\n".join(                      # Formats every product as one line.
        f"- {name.title()}: KSh {details['price']}, {details['quantity']} in stock"  # Shows price and quantity.
        for name, details in stock.items()        # Goes through all products.
    )
    return (                                      # Returns the full context block for the prompt.
        f"\n\nCURRENT STOCK:\n{stock_lines}\n\n"  # Adds the stock list.
        f"LOW STOCK REPORT: {low_stock_report()}\n\n"  # Adds the low-stock report.
        f"PAYMENT: M-Pesa Till or Paybill {MPESA_NUMBER}, account name {MPESA_ACCOUNT}. "  # Adds payment details.
        f"An order is confirmed only after the seller verifies the M-Pesa transaction code."  # Adds the verification rule.
    )


def extract_json_object(text):                    # Finds and parses the first JSON object in the AI's reply.
    if not text:                                  # Checks for an empty reply from the API.
        return None                               # Reports a failed parse.

    cleaned = text.strip()                        # Removes surrounding whitespace from the reply.

    if cleaned.startswith("```"):                 # Checks whether the reply is inside a markdown code fence.
        cleaned = cleaned.strip("`")              # Removes the backticks of the code fence.
        if cleaned.lower().startswith("json"):    # Checks for a json language label on the fence.
            cleaned = cleaned[4:]                 # Removes the json label.

    start = cleaned.find("{")                     # Finds the opening brace of the JSON object.
    end = cleaned.rfind("}")                      # Finds the closing brace of the JSON object.

    if start == -1 or end == -1 or end < start:   # Checks that a complete object exists.
        return None                               # Reports a failed parse.

    try:                                          # Attempts to parse the JSON object.
        return json.loads(cleaned[start:end + 1])  # Converts the JSON text into a Python dictionary.
    except json.JSONDecodeError:                  # Handles broken or non-JSON replies.
        return None                               # Reports a failed parse.


def fields_present(data, required_fields):        # Checks that all required JSON fields exist and are not empty.
    if not isinstance(data, dict):                # Rejects anything that is not a JSON object.
        return False                              # The check has failed.

    for field in required_fields:                 # Goes through every required field name.
        value = data.get(field)                   # Reads the field's value.

        if value is None:                         # Checks for a missing field.
            return False                          # The check has failed.

        if isinstance(value, str) and not value.strip():  # Checks for an empty string field.
            return False                          # The check has failed.

        if isinstance(value, list) and not value:  # Checks for an empty list field.
            return False                          # The check has failed.

    return True                                   # All required fields are present and not empty.


def call_anthropic(messages):                     # Sends the FULL message list to Anthropic Claude and returns raw text.
    system_text = next(                           # Finds the system instruction inside the message list.
        (m["content"] for m in messages if m["role"] == "system"),  # Searches for the system message.
        ""                                        # Uses an empty string if no system message exists.
    )
    contents = [                                  # Builds the conversation for the Anthropic Messages API.
        {"role": m["role"], "content": m["content"]}  # Converts each message to Anthropic's format.
        for m in messages                         # Goes through every stored message.
        if m["role"] != "system"                   # Skips the system message because it is sent separately.
    ]
    response = ai_client.messages.create(          # Sends the whole conversation to the Anthropic API.
        model=MODEL_NAME,                         # Selects the Claude model from settings.
        max_tokens=1200,                          # Sets the maximum number of generated tokens.
        system=system_text,                       # Attaches the system instruction separately.
        messages=contents                         # Sends the full conversation history for memory.
    )
    return "".join(                               # Combines all text blocks in the response.
        block.text                                # Extracts the text from one response block.
        for block in response.content             # Goes through every returned content block.
        if block.type == "text"                   # Skips any non-text response blocks.
    )


def get_checked_reply(messages, required_fields):  # Calls the AI and validates the JSON reply, retrying once.
    for attempt in range(MAX_ATTEMPTS):           # Tries the call, then retries once on failure.
        data = None                               # Starts each attempt with no parsed reply.

        if ai_client is None:                     # Checks whether Anthropic Claude is connected.
            question = messages[-1]["content"]    # Takes the latest user question from the history.
            data = {"answer": local_ai_answer(question)}  # Builds a valid JSON-shaped local fallback reply.
        else:                                     # Runs when Anthropic Claude is available.
            try:                                  # Attempts the API call.
                raw_text = call_anthropic(messages)  # Sends the full history and receives raw text.
            except Exception as error:            # Handles failed API calls such as no internet.
                print("AI service unavailable:", error)  # Informs the user of the connection problem.
                question = messages[-1]["content"]  # Takes the latest user question from the history.
                data = {"answer": local_ai_answer(question)}  # Falls back to local answers.
            else:                                 # Runs when the API call succeeded.
                data = extract_json_object(raw_text)  # Parses the reply and checks it is valid JSON.

        if fields_present(data, required_fields):  # Checks the required fields are present and not empty.
            return data                           # Returns the validated reply.

    return None                                   # Returns nothing after the retry also failed.


def format_history(messages):                     # Formats the stored messages as readable conversation text.
    lines = []                                    # Creates a list for the formatted lines.

    for message in messages:                      # Goes through every stored message.
        if message["role"] == "system":           # Skips the system instruction.
            continue                              # Moves to the next message.

        speaker = "User" if message["role"] == "user" else "Advisor"  # Chooses the speaker's label.
        lines.append(f"{speaker}: {message['content']}")  # Formats one conversation line.

    return "\n".join(lines)                       # Joins all lines into one text block.


def save_session(messages, summary):              # Saves the conversation and summary to a dated JSON file.
    date_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Builds the date string for the file name.
    file_path = SESSION_DIR / f"session_{date_string}.json"  # Builds the dated session file path.

    conversation = [                              # Prepares the conversation for saving.
        m for m in messages                       # Goes through every stored message.
        if m["role"] != "system"                 # Skips the system instruction in the saved file.
    ]

    payload = {                                   # Builds the saved session record.
        "tool": "Cachabyt Duka Stock Advisor",    # Records the tool's name.
        "group": "Cachabyt (Charles_1016, Eclare_2545, Caleb_2528)",  # Records the group members.
        "date": date_string,                      # Records the session date and time.
        "turns": len(conversation) // 2,          # Counts the user/advisor turn pairs.
        "conversation": conversation,             # Saves the full conversation with memory.
        "summary": summary                        # Saves the AI-written session summary.
    }

    save_data(file_path, payload)                 # Writes the session record to the dated file.
    return file_path                              # Returns the path so the caller can show it.


def ai_chat():                                    # Runs a full AI conversation session with memory.
    history = [                                   # Creates the message list that acts as conversation memory.
        {"role": "system", "content": SYSTEM_PROMPT + stock_context_block()}  # Stores the system prompt with live data.
    ]

    turns = 0                                     # Counts the completed conversation turns.

    print("\n========== CACHABYT AI STOCK ADVISOR ==========")  # Displays the AI heading.
    print("Ask about stock, prices, ordering or restocking.")  # Explains what the advisor can do.
    print("The advisor remembers this whole session.")  # Explains the memory feature.
    print("Type 'exit' to end the session and save a summary.")  # Explains how to finish.

    while True:                                   # Keeps the conversation running until the user exits.
        try:                                      # Handles the user pressing Ctrl+C or closing the input.
            question = input("\nYou: ").strip()  # Collects the user's question.
        except (EOFError, KeyboardInterrupt):     # Handles interrupted input gracefully.
            print("\nSession ended.")            # Confirms the session is ending.
            break                                 # Leaves the conversation loop.

        if question.lower() == "exit":            # Checks whether the user wants to end the session.
            break                                 # Leaves the conversation loop.

        if not question:                          # Checks for empty user input.
            print("Please type a question first - empty input is not sent.")  # Explains the problem.
            continue                              # Asks for input again without crashing.

        history.append({"role": "user", "content": question})  # Adds the question to the conversation memory.

        reply = get_checked_reply(history, REQUIRED_CHAT_FIELDS)  # Sends the FULL history and checks the JSON reply.

        if reply is None:                         # Checks whether the JSON check failed even after the retry.
            print("Sorry, the AI gave an unreadable answer twice. Please rephrase your question.")  # Shows a clear message.
            history.pop()                         # Removes the unanswered question to keep the memory consistent.
            continue                              # Asks for input again without crashing.

        answer_text = reply["answer"].strip()     # Reads the validated answer from the JSON reply.
        print("\nCachabyt Advisor:", answer_text)  # Displays the AI's answer to the user.

        history.append({"role": "assistant", "content": answer_text})  # Adds the answer to the conversation memory.
        turns += 1                                # Counts one completed turn.

    if turns == 0:                                # Checks whether any conversation actually happened.
        print("No conversation to summarise.")    # Explains why nothing will be saved.
        return                                    # Returns to the menu without an API call.

    print(f"\nTurns completed this session: {turns}")  # Reports how many turns the conversation held.

    summary_messages = [                          # Builds the messages for the final summary API call.
        {"role": "system", "content": SUMMARY_PROMPT},  # Uses the summary prompt as the instruction.
        {"role": "user", "content": "Summarise this conversation:\n" + format_history(history)}  # Sends the full conversation.
    ]

    summary = get_checked_reply(summary_messages, REQUIRED_SUMMARY_FIELDS)  # Calls the AI once for the summary.

    if summary is None:                           # Checks whether the summary call failed twice.
        summary = {"summary": "Summary unavailable - the AI gave unreadable JSON twice.",  # Uses a clear fallback note.
                   "topics": [], "recommended_actions": []}  # Provides empty fields for a valid record.
        print("Could not generate an AI summary after two attempts.")  # Informs the user clearly.

    saved_path = save_session(history, summary)   # Saves the conversation and summary to a dated file.
    print(f"Session saved to: {saved_path}")      # Tells the user where the session was saved.
    print("\n----- SESSION SUMMARY -----")       # Displays the summary heading.
    print(summary["summary"])                     # Shows the AI-written summary.


def view_past_session():                          # Opens and displays a previously saved session file.
    files = sorted(SESSION_DIR.glob("session_*.json"))  # Lists all saved session files by date.

    if not files:                                 # Checks whether any sessions have been saved.
        print("No saved sessions yet. Start a new session first (option 1).")  # Guides the user.
        return                                    # Returns to the menu.

    print("\n========== SAVED SESSIONS ==========")  # Displays the saved-sessions heading.
    for index, file_path in enumerate(files, start=1):  # Numbers each saved session.
        print(f"{index}. {file_path.name}")       # Displays the dated file name.

    choice = input("Enter session number to open (or press Enter to cancel): ").strip()  # Collects the user's choice.

    if not choice:                                # Checks whether the user cancelled.
        return                                    # Returns to the menu quietly.

    try:                                          # Validates the chosen number.
        selected = files[int(choice) - 1]         # Selects the matching session file.
    except (ValueError, IndexError):              # Handles letters or numbers out of range.
        print("Invalid session number.")          # Shows a clear error message.
        return                                    # Returns to the menu without crashing.

    try:                                          # Attempts to open and read the selected file.
        with open(selected, "r", encoding="utf-8") as file:  # Opens the session file for reading.
            payload = json.load(file)             # Converts the saved JSON back into Python data.
    except FileNotFoundError:                     # Handles a session file that cannot be found.
        print("That session file could not be found.")  # Shows a clear error message.
        return                                    # Returns to the menu without crashing.
    except json.JSONDecodeError:                  # Handles a damaged session file.
        print("That session file is damaged and cannot be read.")  # Shows a clear error message.
        return                                    # Returns to the menu without crashing.

    print(f"\n----- {selected.name} -----")      # Displays the opened file's name.
    print(f"Turns: {payload.get('turns', 0)}")    # Displays the number of conversation turns.

    for message in payload.get("conversation", []):  # Displays every stored message.
        speaker = "User" if message["role"] == "user" else "Advisor"  # Chooses the speaker's label.
        print(f"{speaker}: {message['content']}")  # Displays one conversation line.

    print("\n----- SUMMARY -----")               # Displays the summary heading.
    summary = payload.get("summary", {})          # Reads the saved summary safely.
    print(summary.get("summary", "No summary recorded."))  # Displays the summary text.

# ============================================================
# 14. SELLER/OWNER MENU
# Purpose: Give the canteen owner/seller access to management functions.
# ============================================================

def owner_menu():                                 # Starts the owner/Seller dashboard.
    while True:                                   # Keeps the owner menu active.
        print("""
========== DUKA OWNER/SELLER PORTAL ==========
1. View stock and prices
2. Add new product
3. Add received stock
4. Record counter sale
5. View customer orders
6. Verify M-Pesa payment
7. Update collection/delivery status
8. View low-stock report
9. View sales report
10. Ask AI stock advisor
11. Return to main menu
============================================
""")                                              # Displays owner options.

        choice = input("Choose an option: ").strip()  # Collects the owner's selection.

        if choice == "1":                         # Opens the stock display.
            view_stock()                          # Shows all products.

        elif choice == "2":                       # Opens product registration.
            add_new_product()                     # Adds a new product.

        elif choice == "3":                       # Opens stock receiving.
            product = input("Product name: ")     # Collects the product name.
            try:                                  # Validates the received quantity.
                quantity = int(input("Quantity received: "))  # Collects the quantity.
                print(add_stock(product, quantity))  # Adds the stock.
            except ValueError:                    # Handles invalid quantities.
                print("Enter a valid whole number.")  # Displays an error.

        elif choice == "4":                       # Opens counter sales.
            product = input("Product sold: ")     # Collects the product name.
            try:                                  # Validates the quantity sold.
                quantity = int(input("Quantity sold: "))  # Collects the quantity.
                print(record_sale(product, quantity))  # Records the sale.
            except ValueError:                    # Handles invalid quantities.
                print("Enter a valid whole number.")  # Displays an error.

        elif choice == "5":                       # Opens customer orders.
            view_orders()                         # Displays all orders.

        elif choice == "6":                       # Opens payment verification.
            verify_payment()                      # Allows the owner to verify payment.

        elif choice == "7":                       # Opens order collection management.
            update_order_status()                 # Updates collection or delivery status.

        elif choice == "8":                       # Opens the low-stock report.
            print(low_stock_report())             # Displays products requiring restocking.

        elif choice == "9":                       # Opens the sales report.
            sales_report()                        # Displays recorded revenue.

        elif choice == "10":                      # Opens the AI assistant.
            ai_chat()                             # Starts the AI conversation.

        elif choice == "11":                      # Returns to the main menu.
            break                                 # Ends the owner menu.

        else:                                     # Handles invalid menu selections.
            print("Invalid choice. Try again.")   # Displays an error message.


# ============================================================
# 15. CUSTOMER MENU
# Purpose: Give customers access to stock, ordering and payment.
# ============================================================

def customer_menu():                              # Starts the customer dashboard.
    while True:                                   # Keeps the customer menu active.
        print("""
========== CUSTOMER MENU ==========
1. View available products
2. Check a product
3. Place an advance order
4. Submit M-Pesa payment details
5. Ask AI stock advisor
6. Return to main menu
===================================
""")                                              # Displays customer options.

        choice = input("Choose an option: ").strip()  # Collects the customer's selection.

        if choice == "1":                         # Opens available products.
            view_stock()                          # Displays products, prices and quantities.

        elif choice == "2":                       # Opens individual product search.
            product = input("Product name: ")     # Collects the product name.
            print(check_product(product))         # Displays the product details.

        elif choice == "3":                       # Opens advance ordering.
            place_customer_order()                # Allows the customer to place an order.

        elif choice == "4":                       # Opens payment submission.
            submit_payment()                      # Allows the customer to submit a transaction code.

        elif choice == "5":                       # Opens the AI assistant.
            ai_chat()                             # Starts the AI conversation.

        elif choice == "6":                       # Returns to the main menu.
            break                                 # Ends the customer menu.

        else:                                     # Handles invalid choices.
            print("Invalid choice. Try again.")   # Displays an error message.


# ============================================================
# 16. MAIN APPLICATION MENU
# Purpose: Offer the three required choices - start a new AI
# session, open a past session file, and exit - plus the stock
# management menus for the owner and the customer.
# ============================================================

def main():                                       # Defines the main application function.
    print("\n========================================")  # Displays the application heading.
    print("       Cachabyt Duka Stock Advisor")    # Displays the project name.
    print("          Mahanaim Canteen")            # Displays the canteen name.
    print("   WeCan Academy Season 12 Project")    # Displays the course project line.
    print("========================================")  # Closes the heading.

    while True:                                   # Keeps the application running.
        print("""
========== MAIN MENU ==========
1. Start a new AI advisor session
2. Open a past session file
3. Customer self-service centre
4. Duka owner/seller portal
5. Exit application
===============================
""")                                              # Displays the main menu options.

        choice = input("Select an option: ").strip()  # Collects the user's selection.

        if choice == "1":                         # Starts a brand-new AI session.
            ai_chat()                             # Opens the conversation with memory.

        elif choice == "2":                       # Opens a previously saved session.
            view_past_session()                   # Displays the saved conversation and summary.

        elif choice == "3":                       # Checks whether the customer section was selected.
            customer_menu()                       # Opens the customer dashboard.

        elif choice == "4":                       # Checks whether the owner section was selected.
            owner_menu()                         # Opens the owner dashboard.

        elif choice == "5":                       # Checks whether the user wants to exit.
            print("Thank you for using Cachabyt Duka.")  # Displays the closing message.
            break                                 # Ends the application.

        else:                                     # Handles invalid selections.
            print("Invalid choice. Select 1, 2, 3, 4 or 5.")  # Requests a valid selection.


# ============================================================
# 17. APPLICATION START
# Purpose: Run the main menu when this file is executed directly.
# ============================================================

if __name__ == "__main__":                        # Checks that this file is being run directly.
    main()                                        # Starts the Cachabyt Duka application.

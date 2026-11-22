"""
Cachabyt Duka Stock Advisor App
This is user friendly Cachabyt canteen stock and pre-order assistant.

Important:
- Stock, prices, totals and orders are calculated by Python.
- Gemini only helps explain information in a conversational way.
- If no API key is available, the local stock features still work.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Gemini is optional so the app can still run without an API key.
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


# ---------------------------------------------------------
# 1. FOLDER AND FILE SETTINGS
# ---------------------------------------------------------

BASE_FOLDER = Path(__file__).parent
DATA_FOLDER = BASE_FOLDER / "data"
SESSION_FOLDER = BASE_FOLDER / "sessions"
STOCK_FILE = DATA_FOLDER / "stock.json"
ORDERS_FILE = DATA_FOLDER / "orders.json"

DATA_FOLDER.mkdir(exist_ok=True)
SESSION_FOLDER.mkdir(exist_ok=True)


# ---------------------------------------------------------
# 2. CANTEEN MENU AND STARTER STOCK
# Prices are taken from the Mahanaim menu photo and additions.
# Starting quantities are DEMO quantities. Edit them to match
# the real canteen stock before using the app.
# ---------------------------------------------------------

STARTER_STOCK = {
    "samosa": {"price": 10, "quantity": 400},
    "smoki sausage": {"price": 40, "quantity": 300},
    "boiled egg": {"price": 30, "quantity": 250},
    "mandazi": {"price": 10, "quantity": 500},
    "chapati": {"price": 20, "quantity": 350},
    "smocha": {"price": 60, "quantity": 250},
    "tea": {"price": 20, "quantity": 400},
    "soda": {"price": 80, "quantity": 300},
    "biscuits": {"price": 10, "quantity": 500},
    "water": {"price": 50, "quantity": 300}
}

LOW_STOCK_LEVEL = 50


# ---------------------------------------------------------
# 3. R-T-C-C-O SYSTEM PROMPT
# Role, Task, Context, Constraints and Output format.
# ---------------------------------------------------------

SYSTEM_PROMPT = """
ROLE:
You are Cachabyt Duka Stock Advisor, a helpful assistant for Mahanaim Canteen
at IYF WeCan Academy.

TASK:
Help the canteen owner monitor stock, understand sales, identify low-stock
items and help students ask about products and advance orders.

CONTEXT:
The user may be a canteen owner or a student. The conversation history
and the latest stock information are provided with each request.
The canteen sells samosa, smoki sausage, boiled egg, mandazi, chapati,
smocha, tea, soda, biscuits and water.

CONSTRAINTS:
Use only the stock snapshot supplied by the Python application.
Never invent stock quantities, prices, sales or order confirmations.
Python is responsible for stock calculations and order records.
If information is missing, say so clearly.
Do not claim that an order is confirmed unless the application says it is.
Keep answers short, clear and suitable for students and shop staff.

OUTPUT FORMAT:
Return valid JSON only, with these fields:
{
  "reply": "A helpful answer for the user",
  "intent": "stock_check, order_question, sales, restock, general or other",
  "action": "none or a suggested next step"
}
All three fields must be present and non-empty.
"""

SUMMARY_PROMPT = """
ROLE:
You are the session reporting assistant for Cachabyt Duka Stock Advisor.

TASK:
Summarise the canteen stock-advisor conversation for the owner.

CONTEXT:
The full conversation and latest stock snapshot are supplied.
Use the conversation to identify requests, sales/restocking discussions,
student order questions and unresolved issues.

CONSTRAINTS:
Do not invent figures or claim that an order was completed unless recorded.
Clearly identify low-stock items from the supplied stock snapshot.
Use simple language and practical recommendations.

OUTPUT FORMAT:
Return valid JSON only with these non-empty fields:
{
  "session_summary": "Short summary",
  "key_activities": ["activity 1", "activity 2"],
  "restock_priorities": ["item and reason"],
  "follow_up": ["next step"]
}
"""


# ---------------------------------------------------------
# 4. LOAD OR CREATE LOCAL DATA
# This is the app's local memory. No API key is needed to
# remember products, prices, stock quantities or orders.
# ---------------------------------------------------------

def load_json(file_path, default_value):
    """Read a JSON file. Return a default value if it does not exist."""
    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
    except (json.JSONDecodeError, OSError):
        print(f"Warning: Could not read {file_path.name}. Using default data.")
    return default_value


def save_json(file_path, data):
    """Save information in a readable JSON file."""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def load_stock():
    """Create the starter stock file the first time the app runs."""
    if not STOCK_FILE.exists():
        save_json(STOCK_FILE, STARTER_STOCK)
    return load_json(STOCK_FILE, STARTER_STOCK.copy())


stock = load_stock()
orders = load_json(ORDERS_FILE, [])


# ---------------------------------------------------------
# 5. BASIC STOCK FUNCTIONS
# These calculations happen locally in Python, not through AI.
# ---------------------------------------------------------

def show_stock():
    """Display every product, its price and available quantity."""
    print("\n--------- CACHABYT MAHANAIM CANTEEN STOCK ---------")
    print(f"{'PRODUCT':20} {'PRICE (KSH)':12} {'AVAILABLE':10} STATUS")
    for item, details in stock.items():
        quantity = details["quantity"]
        status = "LOW STOCK" if quantity <= LOW_STOCK_LEVEL else "Available"
        print(f"{item.title():20} {details['price']:<12} {quantity:<10} {status}")
    print("------------------------------------------")


def find_product(product_name):
    """Find a product without being affected by capital letters."""
    return product_name.strip().lower()


def check_product(product_name):
    """Return the actual availability and price of one product."""
    name = find_product(product_name)
    if name not in stock:
        return f"I could not find '{product_name}' on the canteen menu."
    item = stock[name]
    if item["quantity"] <= 0:
        return f"{name.title()} is currently out of stock. Price: KSh {item['price']}."
    return (f"{name.title()} costs KSh {item['price']} and "
            f"{item['quantity']} are currently available.")


def record_sale(product_name, quantity_sold):
    """Reduce stock after a sale and save the new quantity."""
    name = find_product(product_name)
    if name not in stock:
        return "Product not found. Check the product name."
    if quantity_sold <= 0:
        return "Quantity must be greater than zero."
    if quantity_sold > stock[name]["quantity"]:
        return f"Not enough stock. Only {stock[name]['quantity']} available."

    stock[name]["quantity"] -= quantity_sold
    save_json(STOCK_FILE, stock)
    total = quantity_sold * stock[name]["price"]
    return (f"Sale recorded: {quantity_sold} {name}(s). "
            f"Total: KSh {total}. Remaining stock: {stock[name]['quantity']}.")


def add_stock(product_name, quantity_added):
    """Add new stock when the canteen receives a delivery."""
    name = find_product(product_name)
    if name not in stock:
        return "Product not found. Add new products through stock.json first."
    if quantity_added <= 0:
        return "Quantity must be greater than zero."

    stock[name]["quantity"] += quantity_added
    save_json(STOCK_FILE, stock)
    return f"Added {quantity_added} {name}(s). New stock: {stock[name]['quantity']}."


def show_low_stock():
    """List products at or below the low-stock level."""
    low_items = [
        f"{name.title()} ({details['quantity']} left)"
        for name, details in stock.items()
        if details["quantity"] <= LOW_STOCK_LEVEL
    ]
    if not low_items:
        return "No products are currently at the low-stock warning level."
    return "Low-stock alert: " + ", ".join(low_items)


def stock_snapshot():
    """Create a short stock summary to give the AI current facts."""
    lines = []
    for name, details in stock.items():
        lines.append(
            f"{name}: KSh {details['price']}, quantity {details['quantity']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------
# 6. STUDENT ORDERS AND PAYMENT VERIFICATION
# Unpaid orders are not confirmed and do not reduce stock.
# Seller checks the real payment account before confirming.
# ---------------------------------------------------------

def next_order_id():
    """Create a unique order number."""
    return max([o.get("order_id", 0) for o in orders], default=0) + 1


def get_order(order_id):
    """Find an order using its order number."""
    for order in orders:
        if order.get("order_id") == order_id:
            return order
    return None


def place_order(student_name, product_name, quantity, phone_number=""):
    """Save a student order as awaiting payment."""
    name = find_product(product_name)
    if not student_name.strip():
        return "Please enter the student's name."
    if name not in stock:
        return "Product not found. Please check the menu."
    if quantity <= 0:
        return "Quantity must be greater than zero."
    if quantity > stock[name]["quantity"]:
        return f"Not enough stock. Available: {stock[name]['quantity']}."

    order = {
        "order_id": next_order_id(),
        "student_name": student_name.strip(),
        "phone_number": phone_number.strip(),
        "product": name,
        "quantity": quantity,
        "unit_price": stock[name]["price"],
        "total": quantity * stock[name]["price"],
        "payment_status": "Awaiting payment",
        "payment_method": "",
        "payment_reference": "",
        "status": "Awaiting payment",
        "created_at": datetime.now().isoformat(timespec="minutes"),
        "reminders": []
    }
    orders.append(order)
    save_json(ORDERS_FILE, orders)
    return (f"Order #{order['order_id']} received. STATUS: AWAITING PAYMENT.\n"
            f"Amount due: KSh {order['total']}.\n"
            "Please pay using the canteen's approved payment instructions. "
            "Your order is not confirmed until the seller verifies payment.")


def show_orders():
    """Display all orders and their payment status."""
    print("\n--------------- STUDENT ORDERS ---------------")
    if not orders:
        print("There are no orders.")
    for order in orders:
        print(f"#{order['order_id']} | {order['student_name']} | "
              f"{order['quantity']} x {order['product']} | KSh {order['total']} | "
              f"Payment: {order.get('payment_status', 'Awaiting payment')} | "
              f"Order: {order['status']}")
    print("----------------------------------------------")


def verify_payment_and_confirm(order_id, payment_method, payment_reference):
    """Seller verifies payment, then stock is deducted and order confirmed."""
    order = get_order(order_id)
    if order is None:
        return "Order number not found."
    if order["status"] != "Awaiting payment":
        return f"Order cannot be confirmed. Current status: {order['status']}."
    if not payment_method.strip() or not payment_reference.strip():
        return "Enter the payment method and payment reference."

    product = order["product"]
    quantity = order["quantity"]
    if stock[product]["quantity"] < quantity:
        return "Not enough stock to fulfil this order. Do not confirm it."

    # This function is called only after the seller confirms payment was checked.
    stock[product]["quantity"] -= quantity
    order["payment_status"] = "Verified"
    order["payment_method"] = payment_method.strip()
    order["payment_reference"] = payment_reference.strip()
    order["payment_verified_at"] = datetime.now().isoformat(timespec="minutes")
    order["status"] = "Confirmed"
    save_json(STOCK_FILE, stock)
    save_json(ORDERS_FILE, orders)
    return (f"Payment verified. Order #{order_id} is CONFIRMED.\n"
            f"Remaining {product.title()} stock: {stock[product]['quantity']}.")


def create_payment_reminder(order_id):
    """Create and save a payment reminder for an unpaid buyer."""
    order = get_order(order_id)
    if order is None:
        return "Order number not found."
    if order.get("payment_status") == "Verified":
        return "Payment is already verified. No reminder is needed."
    if order["status"] != "Awaiting payment":
        return f"Cannot remind buyer. Order status: {order['status']}."

    message = (f"Hello {order['student_name']}, this is Mahanaim Canteen. "
               f"Reminder: your order #{order_id} is awaiting payment of "
               f"KSh {order['total']}. Please pay using the canteen's approved "
               "payment instructions and share the payment reference with the seller. "
               "Your order is not confirmed until payment is verified. Thank you.")
    order.setdefault("reminders", []).append({
        "message": message,
        "created_at": datetime.now().isoformat(timespec="minutes")
    })
    save_json(ORDERS_FILE, orders)
    return ("PAYMENT REMINDER CREATED. Copy this message and send it to the buyer. "
            "SMS/WhatsApp is not automatically sent by this prototype.\n\n" + message)


def update_order_status(order_id, new_status):
    """Mark a paid order ready for collection or collected."""
    order = get_order(order_id)
    if order is None:
        return "Order number not found."
    if order.get("payment_status") != "Verified":
        return "Payment must be verified before collection."
    allowed = {"Confirmed": "Ready for collection",
               "Ready for collection": "Collected"}
    if allowed.get(order["status"]) != new_status:
        return f"Cannot change order from {order['status']} to {new_status}."
    order["status"] = new_status
    order["updated_at"] = datetime.now().isoformat(timespec="minutes")
    save_json(ORDERS_FILE, orders)
    return f"Order #{order_id} updated to {new_status}."


def cancel_unpaid_order(order_id):
    """Cancel an unpaid order without deducting stock."""
    order = get_order(order_id)
    if order is None:
        return "Order number not found."
    if order.get("payment_status") == "Verified":
        return "This order is already paid. Follow the canteen refund process."
    if order["status"] != "Awaiting payment":
        return "Only unpaid orders awaiting payment can be cancelled."
    order["status"] = "Cancelled"
    save_json(ORDERS_FILE, orders)
    return f"Unpaid order #{order_id} cancelled."


def seller_verify_order():
    """Ask seller for payment details after checking the account."""
    try:
        order_id = int(input("Order number: "))
        method = input("Payment method (e.g. M-Pesa): ").strip()
        reference = input("Payment transaction reference: ").strip()
        checked = input("Have you checked the actual account and confirmed receipt? (yes/no): ").strip().lower()
        if checked != "yes":
            print("Order remains unpaid and unconfirmed.")
            return
        print(verify_payment_and_confirm(order_id, method, reference))
    except ValueError:
        print("Please enter a valid order number.")


def seller_send_reminder():
    """Create a reminder for a buyer who has not paid."""
    try:
        print(create_payment_reminder(int(input("Order number: "))))
    except ValueError:
        print("Please enter a valid order number.")


def seller_update_collection():
    """Update a paid order's collection status."""
    try:
        order_id = int(input("Order number: "))
        print("1. Ready for collection\n2. Collected")
        choice = input("Choose: ").strip()
        if choice == "1":
            print(update_order_status(order_id, "Ready for collection"))
        elif choice == "2":
            print(update_order_status(order_id, "Collected"))
        else:
            print("Invalid choice.")
    except ValueError:
        print("Please enter a valid order number.")


def seller_cancel_order():
    """Cancel an unpaid order."""
    try:
        print(cancel_unpaid_order(int(input("Order number: "))))
    except ValueError:
        print("Please enter a valid order number.")


def student_order():
    """Let a student submit an order for payment."""
    student = input("Your name: ").strip()
    phone = input("Phone number (optional): ").strip()
    product = input("Product: ").strip()
    try:
        quantity = int(input("Quantity: "))
        print(place_order(student, product, quantity, phone))
    except ValueError:
        print("Please enter a whole number for quantity.")


# ---------------------------------------------------------
# 7. CONNECT TO GEMINI
# The complete conversation history is sent on every turn.
# If no key is configured, the local assistant still works.
# ---------------------------------------------------------

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

client = None
if API_KEY and genai:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as error:
        print("Gemini could not start. Local mode will be used.")
        print("Details:", error)


def valid_ai_json(text, required_fields):
    """Check that the AI response is valid JSON with required fields."""
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("The AI response is not a JSON object.")
    for field in required_fields:
        if field not in data or data[field] in ("", None, []):
            raise ValueError(f"Missing or empty field: {field}")
    return data


def ask_gemini(history, prompt, required_fields):
    """Send conversation history to Gemini and retry once if JSON is invalid."""
    if client is None:
        return None

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=prompt,
                    response_mime_type="application/json"
                )
            )
            return valid_ai_json(response.text, required_fields)
        except (json.JSONDecodeError, ValueError) as error:
            if attempt == 0:
                # Ask the model again if its JSON did not pass our checks.
                history.append({
                    "role": "user",
                    "parts": [{
                        "text": f"Your last answer failed JSON validation: {error}. "
                                "Return the required valid JSON object."
                    }]
                })
        except Exception as error:
            print("AI request failed. Using local information instead.")
            print("Details:", error)
            return None

    print("The AI response did not pass the JSON check after one retry.")
    return None


# ---------------------------------------------------------
# 8. LOCAL ANSWER BACKUP
# Common stock questions are answered without an API key.
# ---------------------------------------------------------

def local_answer(user_text):
    """Answer common questions using saved local canteen data."""
    message = user_text.lower()

    if "stock" in message or "available" in message or "menu" in message:
        return stock_snapshot()
    if "low" in message or "restock" in message or "running out" in message:
        return show_low_stock()
    if "price" in message or "cost" in message:
        return "Menu prices: " + ", ".join(
            f"{name.title()} KSh {details['price']}"
            for name, details in stock.items()
        )
    return ("I can help with stock, prices, low-stock alerts and orders. "
            "Try asking 'show stock' or use the application menu.")


# ---------------------------------------------------------
# 9. CONVERSATION SESSION WITH MEMORY
# At least four turns are supported. Each answer uses history.
# ---------------------------------------------------------

def run_session():
    """Start a conversation and save the full session at the end."""
    print("\nC2C Duka Stock Advisor session started.")
    print("Ask about stock, prices, sales or restocking.")
    print("Type 'end' to finish and save this session.")

    history = []
    turn_number = 0

    while True:
        user_text = input("\nYou: ").strip()

        if not user_text:
            print("Please enter a question or type 'end'.")
            continue

        if user_text.lower() == "end":
            break

        turn_number += 1

        # Add the latest stock information to the conversation context.
        context_text = (
            f"Current verified canteen stock snapshot:\n{stock_snapshot()}\n"
            f"Low-stock warning level: {LOW_STOCK_LEVEL} units.\n"
            f"Saved student orders: {len(orders)}."
        )

        # Store the user's message in the conversation memory.
        history.append({
            "role": "user",
            "parts": [{"text": context_text + "\nUser message: " + user_text}]
        })

        # Send the full history, not only the latest question.
        ai_result = ask_gemini(
            history,
            SYSTEM_PROMPT,
            ["reply", "intent", "action"]
        )

        if ai_result:
            answer = ai_result["reply"]
            # Save the AI answer so the next turn remembers it.
            history.append({
                "role": "model",
                "parts": [{"text": json.dumps(ai_result)}]
            })
            print("\nC2C Advisor:", answer)
        else:
            answer = local_answer(user_text)
            history.append({
                "role": "model",
                "parts": [{"text": answer}]
            })
            print("\nC2C Advisor (local mode):", answer)

    # Make the final summary call using the whole conversation.
    summary = None
    if history and client is not None:
        summary = ask_gemini(
            history + [{
                "role": "user",
                "parts": [{
                    "text": "Prepare the final session summary. Latest stock:\n"
                            + stock_snapshot()
                }]
            }],
            SUMMARY_PROMPT,
            ["session_summary", "key_activities",
             "restock_priorities", "follow_up"]
        )

    if summary is None:
        summary = {
            "session_summary": "Session completed. Local summary generated.",
            "key_activities": [f"{turn_number} conversation turns recorded."],
            "restock_priorities": [show_low_stock()],
            "follow_up": ["Review pending student orders and update stock."]
        }

    # Save the conversation and summary using today's date and time.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_file = SESSION_FOLDER / f"session_{timestamp}.json"

    saved_session = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "turn_count": turn_number,
        "conversation": history,
        "summary": summary,
        "latest_stock": stock
    }
    save_json(session_file, saved_session)

    print("\nSESSION SUMMARY")
    print(json.dumps(summary, indent=4))
    print(f"\nSession saved to: {session_file}")


# ---------------------------------------------------------
# 10. OPEN A PREVIOUS SESSION
# ---------------------------------------------------------

def open_past_session():
    """List saved sessions and display the selected one."""
    session_files = sorted(SESSION_FOLDER.glob("session_*.json"))

    if not session_files:
        print("No saved sessions were found.")
        return

    print("\nSaved sessions:")
    for number, file_path in enumerate(session_files, start=1):
        print(f"{number}. {file_path.name}")

    choice = input("Enter the session number to open: ").strip()
    try:
        selected = int(choice) - 1
        if selected < 0 or selected >= len(session_files):
            print("That session number does not exist.")
            return
        data = load_json(session_files[selected], {})
        print(json.dumps(data, indent=4))
    except ValueError:
        print("Please enter a valid number.")
    except OSError:
        print("The selected session file could not be opened.")


# ---------------------------------------------------------
# 11. SIMPLE OWNER MENU
# ---------------------------------------------------------

def owner_record_sale():
    """Ask the owner for a sale and update the stock."""
    name = input("Product name: ").strip()
    try:
        quantity = int(input("Quantity sold: "))
        print(record_sale(name, quantity))
    except ValueError:
        print("Please enter a whole number for quantity.")


def owner_add_stock():
    """Ask the owner to record new stock received."""
    name = input("Product name: ").strip()
    try:
        quantity = int(input("Quantity received: "))
        print(add_stock(name, quantity))
    except ValueError:
        print("Please enter a whole number for quantity.")


def student_order():
    """Allow a student to submit a simple advance order request."""
    student = input("Your name: ").strip()
    product = input("Product: ").strip()
    try:
        quantity = int(input("Quantity: "))
        if not student:
            print("Please enter your name.")
            return
        print(place_order(student, product, quantity))
    except ValueError:
        print("Please enter a whole number for quantity.")


def main():
    """Display the main menu until the user chooses to exit."""
    print("\n==========================================")
    print("       C2C DUKA STOCK ADVISOR APP")
    print("          MAHANAIM CANTEEN")
    print("==========================================")

    while True:
        print("\nMAIN MENU")
        print("1. Start AI stock-advisor conversation")
        print("2. Check current stock and prices")
        print("3. Record a sale (owner)")
        print("4. Add new stock (owner)")
        print("5. Place a student advance order")
        print("6. View student orders (owner)")
        print("7. Verify payment and confirm order (owner)")
        print("8. Create payment reminder for unpaid buyer (owner)")
        print("9. Update order to ready / collected (owner)")
        print("10. Cancel an unpaid order (owner)")
        print("11. View low-stock alerts")
        print("12. Open a past session")
        print("13. Exit")

        choice = input("Choose 1-9: ").strip()

        if choice == "1":
            run_session()
        elif choice == "2":
            show_stock()
        elif choice == "3":
            owner_record_sale()
        elif choice == "4":
            owner_add_stock()
        elif choice == "5":
            student_order()
        elif choice == "6":
            show_orders()
        elif choice == "7":
            seller_verify_order()
        elif choice == "8":
            seller_send_reminder()
        elif choice == "9":
            seller_update_collection()
        elif choice == "10":
            seller_cancel_order()
        elif choice == "11":
            print(show_low_stock())
        elif choice == "12":
            open_past_session()
        elif choice == "13":
            print("Thank you for using C2C Duka Stock Advisor.")
            break
        else:
            print("Invalid choice. Please select a number from 1 to 13.")


if __name__ == "__main__":
    main()

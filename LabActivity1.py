import sqlite3

# ----------------------------------------
# DATABASE SETUP
# ----------------------------------------

def init_db():
    conn = sqlite3.connect("hardware_inventory.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hardware (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        status TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


# ----------------------------------------
# DETERMINE STOCK STATUS
# ----------------------------------------

def get_status(quantity):
    if quantity > 5:
        return "In Stock"
    elif 1 <= quantity <= 5:
        return "Low Stock"
    else:
        return "Out of Stock"


# ----------------------------------------
# INSERT ITEM
# ----------------------------------------

def add_item():
    conn = sqlite3.connect("hardware_inventory.db")
    cursor = conn.cursor()

    item_name = input("Enter Item Name: ")
    category = input("Enter Category: ")

    try:
        quantity = int(input("Enter Quantity: "))
        unit_price = float(input("Enter Unit Price: "))
    except ValueError:
        print("\nInvalid input! Please enter valid numbers.\n")
        conn.close()
        return

    status = get_status(quantity)

    cursor.execute("""
    INSERT INTO hardware
    (item_name, category, quantity, unit_price, status)
    VALUES (?, ?, ?, ?, ?)
    """, (item_name, category, quantity, unit_price, status))

    conn.commit()
    conn.close()

    print("\nHardware item added successfully!\n")


# ----------------------------------------
# UPDATE ITEM
# ----------------------------------------

def update_item():
    conn = sqlite3.connect("hardware_inventory.db")
    cursor = conn.cursor()

    try:
        item_id = int(input("Enter Item ID to Update: "))
        quantity = int(input("Enter New Quantity: "))
        unit_price = float(input("Enter New Unit Price: "))
    except ValueError:
        print("\nInvalid input!\n")
        conn.close()
        return

    status = get_status(quantity)

    cursor.execute("""
    UPDATE hardware
    SET quantity = ?,
        unit_price = ?,
        status = ?
    WHERE item_id = ?
    """, (quantity, unit_price, status, item_id))

    if cursor.rowcount == 0:
        print("\nError: Item ID not found!\n")
    else:
        conn.commit()
        print("\nRecord updated successfully!\n")

    conn.close()


# ----------------------------------------
# DELETE ITEM
# ----------------------------------------

def delete_item():
    conn = sqlite3.connect("hardware_inventory.db")
    cursor = conn.cursor()

    try:
        item_id = int(input("Enter Item ID to Delete: "))
    except ValueError:
        print("\nInvalid Item ID!\n")
        conn.close()
        return

    confirm = input("Are you sure you want to delete this item? (y/n): ").lower()

    if confirm == "y":
        cursor.execute("DELETE FROM hardware WHERE item_id = ?", (item_id,))

        if cursor.rowcount == 0:
            print("\nError: Item ID not found!\n")
        else:
            conn.commit()
            print("\nRecord deleted successfully!\n")
    else:
        print("\nDeletion cancelled.\n")

    conn.close()


# ----------------------------------------
# DISPLAY ITEMS
# ----------------------------------------

def display_items():
    conn = sqlite3.connect("hardware_inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM hardware")
    records = cursor.fetchall()

    if not records:
        print("\nNo records found.\n")
    else:
        print("\n" + "=" * 90)
        print(f"{'ID':<5}{'Name':<25}{'Category':<20}{'Qty':<8}{'Unit Price':<15}{'Status'}")
        print("=" * 90)

        for row in records:
            print(f"{row[0]:<5}{row[1]:<25}{row[2]:<20}{row[3]:<8}₱{row[4]:<14.2f}{row[5]}")

        print("=" * 90)

    conn.close()


# ----------------------------------------
# MAIN MENU
# ----------------------------------------

def menu():
    init_db()

    while True:
        print("\n===== CAMPUS HARDWARE INVENTORY SYSTEM =====")
        print("1. Add Hardware Item")
        print("2. Update Hardware Item")
        print("3. Delete Hardware Item")
        print("4. Display Hardware Inventory")
        print("5. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            add_item()

        elif choice == "2":
            update_item()

        elif choice == "3":
            delete_item()

        elif choice == "4":
            display_items()

        elif choice == "5":
            print("\nThank you for using the Campus Hardware Inventory System.")
            break

        else:
            print("\nInvalid choice. Please try again.")


# ----------------------------------------
# START PROGRAM
# ----------------------------------------

if __name__ == "__main__":
    menu()
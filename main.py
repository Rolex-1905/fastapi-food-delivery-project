from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

app = FastAPI()

# -------------------- HOME --------------------

@app.get("/")
def home():
    return {"message": "Welcome to QuickBite Food Delivery"}


# -------------------- MENU DATA --------------------

menu = [
    {"id": 1, "name": "Margherita Pizza", "price": 250, "category": "Pizza", "is_available": True},
    {"id": 2, "name": "Veg Burger", "price": 120, "category": "Burger", "is_available": True},
    {"id": 3, "name": "Chicken Burger", "price": 180, "category": "Burger", "is_available": False},
    {"id": 4, "name": "Coke", "price": 50, "category": "Drink", "is_available": True},
    {"id": 5, "name": "Brownie", "price": 90, "category": "Dessert", "is_available": True},
    {"id": 6, "name": "Pepperoni Pizza", "price": 300, "category": "Pizza", "is_available": False}
]


# -------------------- GET APIs --------------------

@app.get("/menu")
def get_menu():
    return {"total_items": len(menu), "items": menu}


@app.get("/menu/summary")
def menu_summary():
    total = len(menu)
    available = sum(1 for item in menu if item["is_available"])
    categories = list(set(item["category"] for item in menu))

    return {
        "total_items": total,
        "available_items": available,
        "unavailable_items": total - available,
        "categories": categories
    }


def filter_menu_logic(category=None, max_price=None, is_available=None):
    result = menu

    if category is not None:
        result = [i for i in result if i["category"].lower() == category.lower()]

    if max_price is not None:
        result = [i for i in result if i["price"] <= max_price]

    if is_available is not None:
        result = [i for i in result if i["is_available"] == is_available]

    return result


@app.get("/menu/filter")
def filter_menu(
    category: str = Query(None),
    max_price: int = Query(None),
    is_available: bool = Query(None)
):
    result = filter_menu_logic(category, max_price, is_available)
    return {"count": len(result), "items": result}


@app.get("/menu/search")
def search_menu(keyword: str):
    results = [
        item for item in menu
        if keyword.lower() in item["name"].lower()
        or keyword.lower() in item["category"].lower()
    ]

    if not results:
        raise HTTPException(status_code=404, detail="No items found")

    return {"total_found": len(results), "items": results}


@app.get("/menu/sort")
def sort_menu(sort_by: str = "price", order: str = "asc"):
    if sort_by not in ["price", "name", "category"]:
        raise HTTPException(status_code=400, detail="Invalid sort_by field")

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order value")

    sorted_items = sorted(menu, key=lambda x: x[sort_by], reverse=(order == "desc"))

    return {"sort_by": sort_by, "order": order, "items": sorted_items}


@app.get("/menu/page")
def paginate_menu(page: int = 1, limit: int = 3):
    if page < 1 or limit < 1 or limit > 10:
        raise HTTPException(status_code=400, detail="Invalid page or limit")

    start = (page - 1) * limit
    end = start + limit

    return {
        "page": page,
        "limit": limit,
        "total_items": len(menu),
        "total_pages": (len(menu) + limit - 1) // limit,
        "items": menu[start:end]
    }


@app.get("/menu/browse")
def browse_menu(
    keyword: str = None,
    sort_by: str = "price",
    order: str = "asc",
    page: int = 1,
    limit: int = 3
):
    result = menu

    if keyword:
        result = [i for i in result if keyword.lower() in i["name"].lower()]

    if sort_by not in ["price", "name", "category"]:
        raise HTTPException(status_code=400, detail="Invalid sort field")

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order")

    result = sorted(result, key=lambda x: x[sort_by], reverse=(order == "desc"))

    if page < 1 or limit < 1 or limit > 10:
        raise HTTPException(status_code=400, detail="Invalid pagination")

    start = (page - 1) * limit
    end = start + limit

    return {
        "total_results": len(result),
        "page": page,
        "limit": limit,
        "items": result[start:end]
    }


@app.get("/menu/{item_id}")
def get_item(item_id: int):
    for item in menu:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


# -------------------- CRUD --------------------

class NewMenuItem(BaseModel):
    name: str = Field(..., min_length=2)
    price: int = Field(..., gt=0)
    category: str = Field(..., min_length=2)
    is_available: bool = True


@app.post("/menu")
def add_item(item: NewMenuItem, response: Response):
    for m in menu:
        if m["name"].lower() == item.name.lower():
            raise HTTPException(status_code=400, detail="Item exists")

    new_id = max([m["id"] for m in menu], default=0) + 1

    new_item = item.dict()
    new_item["id"] = new_id

    menu.append(new_item)
    response.status_code = 201

    return new_item


@app.put("/menu/{item_id}")
def update_item(item_id: int, price: int = None, is_available: bool = None):
    for item in menu:
        if item["id"] == item_id:
            if price is not None:
                item["price"] = price
            if is_available is not None:
                item["is_available"] = is_available
            return item

    raise HTTPException(status_code=404, detail="Item not found")


@app.delete("/menu/{item_id}")
def delete_item(item_id: int):
    for item in menu:
        if item["id"] == item_id:
            menu.remove(item)
            return {"message": "Deleted"}

    raise HTTPException(status_code=404, detail="Item not found")


# -------------------- ORDERS --------------------

orders = []
order_counter = 1


class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    delivery_address: str = Field(..., min_length=10)
    order_type: str = "delivery"


def find_item(item_id):
    for item in menu:
        if item["id"] == item_id:
            return item
    return None


def calc_bill(price, qty, order_type):
    total = price * qty
    if order_type == "delivery":
        total += 30
    return total


@app.post("/orders")
def create_order(order: OrderRequest):
    global order_counter

    item = find_item(order.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item["is_available"]:
        raise HTTPException(status_code=400, detail="Not available")

    total = calc_bill(item["price"], order.quantity, order.order_type)

    new_order = {
        "order_id": order_counter,
        "customer_name": order.customer_name,
        "item_name": item["name"],
        "quantity": order.quantity,
        "total_price": total,
        "delivery_address": order.delivery_address,
        "order_type": order.order_type
    }

    orders.append(new_order)
    order_counter += 1

    return new_order


@app.get("/orders")
def get_orders():
    return {"total_orders": len(orders), "orders": orders}


@app.get("/orders/summary")
def orders_summary():
    if not orders:
        raise HTTPException(status_code=404, detail="No orders found")

    return {
        "total_orders": len(orders),
        "total_revenue": sum(o["total_price"] for o in orders),
        "orders": orders
    }


# -------------------- CART WORKFLOW --------------------

cart = []


@app.post("/cart/add")
def add_to_cart(item_id: int, quantity: int = 1):
    item = find_item(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item["is_available"]:
        raise HTTPException(status_code=400, detail="Not available")

    for c in cart:
        if c["item_id"] == item_id:
            c["quantity"] += quantity
            return {"message": "Updated", "cart": cart}

    cart.append({
        "item_id": item_id,
        "name": item["name"],
        "price": item["price"],
        "quantity": quantity
    })

    return {"message": "Added", "cart": cart}


@app.get("/cart")
def view_cart():
    total = sum(i["price"] * i["quantity"] for i in cart)
    return {"cart": cart, "total": total}


@app.delete("/cart/{item_id}")
def remove_cart(item_id: int):
    for item in cart:
        if item["item_id"] == item_id:
            cart.remove(item)
            return {"message": "Removed"}

    raise HTTPException(status_code=404, detail="Not in cart")


class Checkout(BaseModel):
    customer_name: str
    delivery_address: str


@app.post("/cart/checkout")
def checkout(data: Checkout, response: Response):
    global order_counter

    if not cart:
        raise HTTPException(status_code=400, detail="Cart empty")

    placed = []
    total = 0

    for item in cart:
        t = item["price"] * item["quantity"]

        order = {
            "order_id": order_counter,
            "customer_name": data.customer_name,
            "item_name": item["name"],
            "quantity": item["quantity"],
            "total_price": t,
            "delivery_address": data.delivery_address,
            "order_type": "delivery"
        }

        orders.append(order)
        placed.append(order)
        total += t
        order_counter += 1

    cart.clear()
    response.status_code = 201

    return {"message": "Order placed", "orders": placed, "total": total}
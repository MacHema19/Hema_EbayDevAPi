import os
import sqlite3
import hashlib
import secrets
import base64
from typing import Optional, List

import httpx
from fastapi import FastAPI, HTTPException, Query, Header
from pydantic import BaseModel


app = FastAPI(title="eBay Product API with Session Login")


# =========================
# EBAY CONFIG
# =========================

EBAY_ENV = os.getenv("EBAY_ENV", "sandbox")
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID", "")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET", "")
EBAY_MARKETPLACE_ID = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")
EBAY_LOCATION_KEY = os.getenv("EBAY_LOCATION_KEY", "default-location")

EBAY_API_BASE = (
    "https://api.ebay.com"
    if EBAY_ENV == "production"
    else "https://api.sandbox.ebay.com"
)


# =========================
# SQLITE DB
# =========================

DB_FILE = "products.db"


def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        active INTEGER DEFAULT 1
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        active INTEGER DEFAULT 1
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        category_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        price REAL,
        quantity INTEGER,
        tags TEXT,
        offer_id TEXT,
        listing_id TEXT
    )
    """)

    conn.commit()
    conn.close()

## simple remark for personal ref - to be deleted later.
## code created for XXX   May6, 2026
## testing and documentation complated on may7,2026
## scripts and technical documentation sent to  XXX
## performed by HemaDaarshiniselvaraju (+XXX)


init_db()


# =========================
# MODELS
# =========================

class AccountRequest(BaseModel):
    username: str
    password: str


class ProductCreate(BaseModel):
    sku: str
    category_id: str
    title: str
    description: str
    price: float
    quantity: int
    tags: Optional[List[str]] = []


# =========================
# AUTH HELPERS
# =========================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)

    conn = db()
    conn.execute("""
    INSERT INTO sessions (token, username, active)
    VALUES (?, ?, 1)
    """, (token, username))
    conn.commit()
    conn.close()

    return token


def get_current_username(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization.replace("Bearer ", "").strip()

    conn = db()
    row = conn.execute("""
    SELECT username
    FROM sessions
    WHERE token = ?
    AND active = 1
    """, (token,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return row["username"]


def register_user(username: str, password: str):
    conn = db()

    existing = conn.execute(
        "SELECT username FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="Username already exists")

    conn.execute("""
    INSERT INTO users (username, password_hash, active)
    VALUES (?, ?, 1)
    """, (username, hash_password(password)))

    conn.commit()
    conn.close()


def validate_user(username: str, password: str) -> bool:
    conn = db()

    row = conn.execute("""
    SELECT username
    FROM users
    WHERE username = ?
    AND password_hash = ?
    AND active = 1
    """, (username, hash_password(password))).fetchone()

    conn.close()
    return row is not None


# =========================
# EBAY HELPERS
# =========================

def get_ebay_app_token() -> Optional[str]:
    if not EBAY_CLIENT_ID or not EBAY_CLIENT_SECRET:
        return None

    raw = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    encoded = base64.b64encode(raw.encode()).decode()

    response = httpx.post(
        f"{EBAY_API_BASE}/identity/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
        timeout=20,
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()["access_token"]


def ebay_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-Language": "en-US",
    }


def create_product_in_ebay(product: ProductCreate):
    token = get_ebay_app_token()

    if not token:
        return {
            "ebay_status": "skipped",
            "reason": "eBay credentials not configured"
        }

    inventory_payload = {
        "product": {
            "title": product.title,
            "description": product.description,
        },
        "condition": "NEW",
        "availability": {
            "shipToLocationAvailability": {
                "quantity": product.quantity
            }
        }
    }

    inventory_response = httpx.put(
        f"{EBAY_API_BASE}/sell/inventory/v1/inventory_item/{product.sku}",
        headers=ebay_headers(token),
        json=inventory_payload,
        timeout=20,
    )

    if inventory_response.status_code not in [200, 201, 204]:
        return {
            "ebay_status": "inventory_failed",
            "status_code": inventory_response.status_code,
            "error": inventory_response.text
        }

    offer_payload = {
        "sku": product.sku,
        "marketplaceId": EBAY_MARKETPLACE_ID,
        "format": "FIXED_PRICE",
        "availableQuantity": product.quantity,
        "categoryId": product.category_id,
        "listingDescription": product.description,
        "pricingSummary": {
            "price": {
                "value": str(product.price),
                "currency": "USD"
            }
        },
        "merchantLocationKey": EBAY_LOCATION_KEY,
    }

    offer_response = httpx.post(
        f"{EBAY_API_BASE}/sell/inventory/v1/offer",
        headers=ebay_headers(token),
        json=offer_payload,
        timeout=20,
    )

    if offer_response.status_code not in [200, 201]:
        return {
            "ebay_status": "offer_failed",
            "status_code": offer_response.status_code,
            "error": offer_response.text
        }

    offer_data = offer_response.json()

    return {
        "ebay_status": "offer_created",
        "offer_id": offer_data.get("offerId")
    }


# =========================
# ACCOUNT ENDPOINTS
# =========================

@app.post("/register")
def register(request: AccountRequest):
    register_user(request.username, request.password)

    token = create_session(request.username)

    return {
        "message": "Account created successfully",
        "username": request.username,
        "access_token": token,
        "token_type": "Bearer"
    }


@app.post("/login")
def login(request: AccountRequest):
    if not validate_user(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_session(request.username)

    return {
        "login": "success",
        "message": "User authenticated successfully",
        "username": request.username,
        "access_token": token,
        "token_type": "Bearer"
    }


@app.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    username = get_current_username(authorization)
    token = authorization.replace("Bearer ", "").strip()

    conn = db()
    conn.execute("""
    UPDATE sessions
    SET active = 0
    WHERE token = ?
    """, (token,))
    conn.commit()
    conn.close()

    return {
        "message": "Logged out successfully",
        "username": username
    }


# =========================
# PRODUCT CRUD ENDPOINTS
# =========================

@app.post("/products")
def create_product(
    product: ProductCreate,
    authorization: Optional[str] = Header(None)
):
    username = get_current_username(authorization)

    ebay_result = create_product_in_ebay(product)

    offer_id = ebay_result.get("offer_id")
    listing_id = ebay_result.get("listing_id")

    conn = db()

    conn.execute("""
    INSERT OR REPLACE INTO products
    (sku, username, category_id, title, description, price, quantity, tags, offer_id, listing_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        product.sku,
        username,
        product.category_id,
        product.title,
        product.description,
        product.price,
        product.quantity,
        ",".join(product.tags or []),
        offer_id,
        listing_id
    ))

    conn.commit()
    conn.close()

    return {
        "message": "Product created successfully",
        "created_by": username,
        "sku": product.sku,
        "local_status": "created",
        "ebay_result": ebay_result
    }


@app.get("/products")
def get_products(
    authorization: Optional[str] = Header(None),
    category_id: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None
):
    username = get_current_username(authorization)

    conn = db()

    query = "SELECT * FROM products WHERE username = ?"
    params = [username]

    if category_id:
        query += " AND category_id = ?"
        params.append(category_id)

    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")

    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.get("/products/{sku}")
def get_product_by_sku(
    sku: str,
    authorization: Optional[str] = Header(None)
):
    username = get_current_username(authorization)

    conn = db()

    row = conn.execute("""
    SELECT *
    FROM products
    WHERE sku = ?
    AND username = ?
    """, (sku, username)).fetchone()

    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    return dict(row)


# @app.delete("/products/{sku}")
# def delete_product_by_sku(
#     sku: str,
#     authorization: Optional[str] = Header(None)
# ):
#     username = get_current_username(authorization)
#
#     conn = db()
#
#     row = conn.execute("""
#     SELECT sku
#     FROM products
#     WHERE sku = ?
#     AND username = ?
#     """, (sku, username)).fetchone()
#
#     if not row:
#         conn.close()
#         raise HTTPException(status_code=404, detail="Product not found")
#
#     conn.execute("""
#     DELETE FROM products
#     WHERE sku = ?
#     AND username = ?
#     """, (sku, username))
#
#     conn.commit()
#     conn.close()
#
#     return {
#         "message": "Product deleted successfully",
#         "sku": sku
#     }
#
#
# @app.delete("/products")
# def delete_products(
#     authorization: Optional[str] = Header(None),
#     category_id: Optional[str] = Query(None),
#     tag: Optional[str] = Query(None),
#     delete_all: bool = Query(False)
# ):
#     username = get_current_username(authorization)
#
#     if not delete_all and not category_id and not tag:
#         raise HTTPException(
#             status_code=400,
#             detail="Provide category_id, tag, or delete_all=true"
#         )
#
#     conn = db()
#
#     select_query = "SELECT sku FROM products WHERE username = ?"
#     delete_query = "DELETE FROM products WHERE username = ?"
#     params = [username]
#
#     if category_id:
#         select_query += " AND category_id = ?"
#         delete_query += " AND category_id = ?"
#         params.append(category_id)
#
#     if tag:
#         select_query += " AND tags LIKE ?"
#         delete_query += " AND tags LIKE ?"
#         params.append(f"%{tag}%")
#
#     rows = conn.execute(select_query, params).fetchall()
#     deleted_skus = [row["sku"] for row in rows]
#
#     conn.execute(delete_query, params)
#     conn.commit()
#     conn.close()
#
#     return {
#         "message": "Products deleted successfully",
#         "deleted_count": len(deleted_skus),
#         "deleted_skus": deleted_skus
#     }
#

# =========================
# PRODUCT DELETE ENDPOINTS
# =========================

@app.delete("/products/all")
def delete_all_products(
    authorization: Optional[str] = Header(None)
):
    username = get_current_username(authorization)

    conn = db()

    rows = conn.execute("""
    SELECT sku
    FROM products
    WHERE username = ?
    """, (username,)).fetchall()

    deleted_skus = [row["sku"] for row in rows]

    conn.execute("""
    DELETE FROM products
    WHERE username = ?
    """, (username,))

    conn.commit()
    conn.close()

    return {
        "message": "All products deleted successfully",
        "deleted_count": len(deleted_skus),
        "deleted_skus": deleted_skus
    }

## simple remark for personal ref - to be deleted later.
## code created for interview ebay_apiconsultant_on May6, 2026
## testing and documentation complated on may7,2026
## scripts and technical documentation sent to adecco recruiter
## performed by HemaDaarshiniselvaraju (+60122919199)

@app.delete("/products/{sku}")
def delete_product_by_sku(
    sku: str,
    authorization: Optional[str] = Header(None)
):
    username = get_current_username(authorization)

    conn = db()

    row = conn.execute("""
    SELECT sku
    FROM products
    WHERE sku = ?
    AND username = ?
    """, (sku, username)).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")

    conn.execute("""
    DELETE FROM products
    WHERE sku = ?
    AND username = ?
    """, (sku, username))

    conn.commit()
    conn.close()

    return {
        "message": "Product deleted successfully",
        "sku": sku
    }


@app.delete("/products/category/{category_id}")
def delete_products_by_category(
    category_id: str,
    authorization: Optional[str] = Header(None)
):
    username = get_current_username(authorization)

    conn = db()

    rows = conn.execute("""
    SELECT sku
    FROM products
    WHERE username = ?
    AND category_id = ?
    """, (username, category_id)).fetchall()

    deleted_skus = [row["sku"] for row in rows]

    conn.execute("""
    DELETE FROM products
    WHERE username = ?
    AND category_id = ?
    """, (username, category_id))

    conn.commit()
    conn.close()

    return {
        "message": "Products deleted by category successfully",
        "category_id": category_id,
        "deleted_count": len(deleted_skus),
        "deleted_skus": deleted_skus
    }


@app.delete("/products/tag/{tag}")
def delete_products_by_tag(
    tag: str,
    authorization: Optional[str] = Header(None)
):
    username = get_current_username(authorization)

    conn = db()

    rows = conn.execute("""
    SELECT sku
    FROM products
    WHERE username = ?
    AND tags LIKE ?
    """, (username, f"%{tag}%")).fetchall()

    deleted_skus = [row["sku"] for row in rows]

    conn.execute("""
    DELETE FROM products
    WHERE username = ?
    AND tags LIKE ?
    """, (username, f"%{tag}%"))

    conn.commit()
    conn.close()

    return {
        "message": "Products deleted by tag successfully",
        "tag": tag,
        "deleted_count": len(deleted_skus),
        "deleted_skus": deleted_skus
    }


# =========================
# DEBUG ENDPOINT
# =========================

@app.get("/debug/users")
def debug_users():
    conn = db()
    rows = conn.execute("""
    SELECT username, active
    FROM users
    """).fetchall()
    conn.close()

    return [dict(row) for row in rows]
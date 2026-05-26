# eBay Product API Developer Program - FastAPI Backend

## Overview

This project is a FastAPI backend application created for an eBay Product API Developer Program reference implementation.

The API allows users to:

- Register a new account
- Log in and receive an access token
- Log out and deactivate the session token
- Create product listings
- View all products created by the logged-in user
- Search and filter products
- View individual products by SKU
- Delete products by SKU, category, tag, or all products

Each product is linked to the logged-in user. This means users can only manage their own products.

The backend uses:

- **FastAPI** for API development
- **SQLite** for local database storage
- **Bearer token authentication** for protected endpoints
- Optional **eBay Sandbox / Production API integration**

If eBay credentials are configured, product creation will also attempt to create an eBay inventory item and offer.  
If eBay credentials are not configured, the product will still be created locally in SQLite and the eBay status will return as skipped.

---

## Base URL

```text
http://127.0.0.1:8000

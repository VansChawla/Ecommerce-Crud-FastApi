from dotenv import load_dotenv
import os
from fastapi import FastAPI, HTTPException, Query, Path, Depends, Request
from fastapi.responses import JSONResponse
from service.products import (
    get_all_products,
    add_product,
    remove_product,
    change_product,
    load_products,
)
from schema.product import Product, ProductUpdate
from uuid import uuid4, UUID
from datetime import datetime
from typing import List, Dict

load_dotenv()
app = FastAPI()


# @app.middleware("http")
# async def lifecycle(request: Request, call_next):
#     print("Before request")
#     response = await call_next(request)
#     print("After request")
#     return response


def common_logic():
    return "Hello There"


@app.get("/", response_model=dict)
def root(dep=Depends(common_logic)):
    DB_PATH = os.getenv("BASE_URL")
    # return {"message": "Welcomne to FastAPI.", "dependency": dep, "data_path": DB_PATH}
    return JSONResponse(
        status_code=200,
        content={
            "message": "Welcomne to FastAPI.",
            "dependency": dep,
            "data_path": DB_PATH,
        },
    )


@app.get("/products", response_model=Dict)
def list_products(
    dep=Depends(load_products),
    name: str = Query(
        default=None,
        min_length=1,
        max_length=50,
        description="Search by product name (case insensitive)",
        example="Energy 3Pcs",
    ),
    sort_by_price: bool = Query(default=False, description="Sort products by price"),
    order: str = Query(
        default="asc", description="Sort order when sort_by_price=true (asc,desc)"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=1000,
        description="Number of items to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Pagination Offset",
    ),
):

    # products = get_all_products()
    products = dep

    if name:
        needle = name.strip().lower()
        products = [p for p in products if needle in p.get("name", "").lower()]

    if not products:
        raise HTTPException(
            status_code=404, detail=f"No product found matching name={name}"
        )

    if sort_by_price:
        reverse = order == "desc"
        products = sorted(products, key=lambda p: p.get("price", 0), reverse=reverse)

    total = len(products)
    products = products[offset : offset + limit]
    return {"total": total, "limit": limit, "items": products}


@app.get("/products/{product_id}", response_model=Dict)
def get_product_by_id(
    product_id: str = Path(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the products",
        example="c47ea2457-c4a9-4bfg-9dd5-6464r0ebe343",
    )
):
    products = get_all_products()
    for product in products:
        if product["id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found!")


@app.post("/products", status_code=201)
def create_product(product: Product):
    product_dict = product.model_dump(mode="json")
    product_dict["id"] = str(uuid4())
    product_dict["created_at"] = datetime.utcnow().isoformat() + "Z"
    try:
        add_product(product_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return product.model_dump(mode="json")


@app.delete("/products/{product_id}")
def delete_product(product_id: UUID = Path(..., description="Product UUID")):
    try:
        res = remove_product(str(product_id))
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/products/{product_id}")
def update_product(
    product_id: UUID = Path(..., description="Product UUID"),
    payload: ProductUpdate = ...,
):
    try:
        update_product = change_product(
            str(product_id), payload.model_dump(mode="json", exclude_unset=True)
        )
        return update_product
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

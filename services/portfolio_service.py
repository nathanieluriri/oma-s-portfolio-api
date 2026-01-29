# ============================================================================
# PORTFOLIO SERVICE
# ============================================================================
# This file was auto-generated on: 2026-01-28 16:50:02 WAT
# It contains  asynchrounous functions that make use of the repo functions 
# 
# ============================================================================

from bson import ObjectId
from fastapi import HTTPException
from typing import Any, Dict, List
from pydantic import ValidationError

from repositories.portfolio import (
    create_portfolio,
    get_portfolio,
    get_portfolio_raw,
    get_portfolios,
    update_portfolio,
    update_portfolio_fields,
    delete_portfolio,
)
from schemas.portfolio import PortfolioCreate, PortfolioUpdate, PortfolioOut
from services.portfolio_normalization import normalize_portfolio_doc


async def add_portfolio(portfolio_data: PortfolioCreate, user_id: str) -> PortfolioOut:
    """adds an entry of PortfolioCreate to the database and returns an object

    Returns:
        _type_: PortfolioOut
    """
    existing = await get_portfolio({"user_id": user_id})
    if existing:
        raise HTTPException(status_code=409, detail="Portfolio already exists for this user")
    return await create_portfolio(portfolio_data)


async def remove_portfolio(portfolio_id: str, user_id: str):
    """deletes a field from the database and removes PortfolioCreateobject 

    Raises:
        HTTPException 400: Invalid portfolio ID format
        HTTPException 404:  Portfolio not found
    """
    if not ObjectId.is_valid(portfolio_id):
        raise HTTPException(status_code=400, detail="Invalid portfolio ID format")

    filter_dict = {"_id": ObjectId(portfolio_id), "user_id": user_id}
    result = await delete_portfolio(filter_dict)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    else: return True

async def remove_portfolio_by_user_id(user_id: str):
    result = await delete_portfolio({"user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return True
    
async def retrieve_portfolio_by_portfolio_id(id: str) -> PortfolioOut:
    """Retrieves portfolio object based specific Id 

    Raises:
        HTTPException 404(not found): if  Portfolio not found in the db
        HTTPException 400(bad request): if  Invalid portfolio ID format

    Returns:
        _type_: PortfolioOut
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid portfolio ID format")

    filter_dict = {"_id": ObjectId(id)}
    result = await get_portfolio_raw(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    try:
        return PortfolioOut(**result)
    except ValidationError:
        updates = normalize_portfolio_doc(result)
        if updates:
            await update_portfolio_fields(filter_dict, updates)
            refreshed = await get_portfolio_raw(filter_dict)
            if refreshed:
                return PortfolioOut(**refreshed)
        raise

async def retrieve_portfolio_by_user_id(user_id: str) -> PortfolioOut:
    """Retrieves portfolio object based on user_id."""
    filter_dict = {"user_id": user_id}
    result = await get_portfolio_raw(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    try:
        return PortfolioOut(**result)
    except ValidationError:
        updates = normalize_portfolio_doc(result)
        if updates:
            await update_portfolio_fields(filter_dict, updates)
            refreshed = await get_portfolio_raw(filter_dict)
            if refreshed:
                return PortfolioOut(**refreshed)
        raise


async def retrieve_portfolios(start=0,stop=100) -> List[PortfolioOut]:
    """Retrieves PortfolioOut Objects in a list

    Returns:
        _type_: PortfolioOut
    """
    return await get_portfolios(start=start,stop=stop)


async def retrieve_portfolio_raw_by_user_id(user_id: str) -> dict:
    result = await get_portfolio_raw({"user_id": user_id})
    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return result


def build_empty_portfolio_schema(user_id: str | None = None) -> Dict[str, Any]:
    return {
        "userId": user_id,
        "navItems": [],
        "footer": {"copyright": "", "tagline": ""},
        "hero": {"name": "", "title": "", "bio": [], "availability": {"label": "", "status": ""}},
        "experience": [],
        "projects": [],
        "skillGroups": [],
        "contacts": [],
        "theme": {
            "text_primary": "",
            "text_secondary": "",
            "text_muted": "",
            "bg_primary": "",
            "bg_surface": "",
            "bg_surface_hover": "",
            "bg_divider": "",
            "accent_primary": "",
            "accent_muted": "",
        },
        "animations": {"staggerChildren": 0, "delayChildren": 0, "duration": 0, "ease": ""},
        "metadata": {"title": "", "description": "", "author": ""},
        "resumeUrl": "",
    }


def build_empty_portfolio_create(user_id: str) -> PortfolioCreate:
    return PortfolioCreate(
        user_id=user_id,
        navItems=[],
        footer={"copyright": "", "tagline": ""},
        hero={"name": "", "title": "", "bio": [], "availability": {"label": "", "status": ""}},
        experience=[],
        projects=[],
        skillGroups=[],
        contacts=[],
        theme={
            "text_primary": "",
            "text_secondary": "",
            "text_muted": "",
            "bg_primary": "",
            "bg_surface": "",
            "bg_surface_hover": "",
            "bg_divider": "",
            "accent_primary": "",
            "accent_muted": "",
        },
        animations={"staggerChildren": 0, "delayChildren": 0, "duration": 0, "ease": ""},
        metadata={"title": "", "description": "", "author": ""},
        resumeUrl="",
    )


async def update_portfolio_by_id(portfolio_id: str, portfolio_data: PortfolioUpdate, user_id: str) -> PortfolioOut:
    """updates an entry of portfolio in the database

    Raises:
        HTTPException 404(not found): if Portfolio not found or update failed
        HTTPException 400(not found): Invalid portfolio ID format

    Returns:
        _type_: PortfolioOut
    """
    if not ObjectId.is_valid(portfolio_id):
        raise HTTPException(status_code=400, detail="Invalid portfolio ID format")

    filter_dict = {"_id": ObjectId(portfolio_id), "user_id": user_id}
    result = await update_portfolio(filter_dict, portfolio_data)

    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found or update failed")

    return result

async def update_portfolio_by_user_id(portfolio_data: PortfolioUpdate, user_id: str) -> PortfolioOut:
    result = await update_portfolio({"user_id": user_id}, portfolio_data)
    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found or update failed")
    return result


async def update_portfolio_fields_by_user_id(
    updates: dict,
    user_id: str,
    push_updates: dict | None = None,
) -> PortfolioOut:
    filter_dict = {"user_id": user_id}
    result = await update_portfolio_fields(filter_dict, updates, push_updates)
    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found or update failed")
    try:
        return PortfolioOut(**result)
    except ValidationError:
        normalized = normalize_portfolio_doc(result)
        if normalized:
            await update_portfolio_fields(filter_dict, normalized)
            refreshed = await get_portfolio_raw(filter_dict)
            if refreshed:
                return PortfolioOut(**refreshed)
        raise

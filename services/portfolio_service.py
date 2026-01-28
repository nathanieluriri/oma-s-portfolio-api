# ============================================================================
# PORTFOLIO SERVICE
# ============================================================================
# This file was auto-generated on: 2026-01-28 16:50:02 WAT
# It contains  asynchrounous functions that make use of the repo functions 
# 
# ============================================================================

from bson import ObjectId
from fastapi import HTTPException
from typing import List

from repositories.portfolio import (
    create_portfolio,
    get_portfolio,
    get_portfolios,
    update_portfolio,
    delete_portfolio,
)
from schemas.portfolio import PortfolioCreate, PortfolioUpdate, PortfolioOut


async def add_portfolio(portfolio_data: PortfolioCreate) -> PortfolioOut:
    """adds an entry of PortfolioCreate to the database and returns an object

    Returns:
        _type_: PortfolioOut
    """
    return await create_portfolio(portfolio_data)


async def remove_portfolio(portfolio_id: str):
    """deletes a field from the database and removes PortfolioCreateobject 

    Raises:
        HTTPException 400: Invalid portfolio ID format
        HTTPException 404:  Portfolio not found
    """
    if not ObjectId.is_valid(portfolio_id):
        raise HTTPException(status_code=400, detail="Invalid portfolio ID format")

    filter_dict = {"_id": ObjectId(portfolio_id)}
    result = await delete_portfolio(filter_dict)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    else: return True
    
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
    result = await get_portfolio(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return result


async def retrieve_portfolios(start=0,stop=100) -> List[PortfolioOut]:
    """Retrieves PortfolioOut Objects in a list

    Returns:
        _type_: PortfolioOut
    """
    return await get_portfolios(start=start,stop=stop)


async def update_portfolio_by_id(portfolio_id: str, portfolio_data: PortfolioUpdate) -> PortfolioOut:
    """updates an entry of portfolio in the database

    Raises:
        HTTPException 404(not found): if Portfolio not found or update failed
        HTTPException 400(not found): Invalid portfolio ID format

    Returns:
        _type_: PortfolioOut
    """
    if not ObjectId.is_valid(portfolio_id):
        raise HTTPException(status_code=400, detail="Invalid portfolio ID format")

    filter_dict = {"_id": ObjectId(portfolio_id)}
    result = await update_portfolio(filter_dict, portfolio_data)

    if not result:
        raise HTTPException(status_code=404, detail="Portfolio not found or update failed")

    return result
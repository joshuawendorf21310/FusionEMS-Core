from datetime import datetime
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.pricing import Price, Product, Module

class PricingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_price(self, product_name: str, module_name: Optional[str] = None) -> Optional[Price]:
        """
        Retrieves the current active versioned price for a product/module.
        """
        stmt = select(Price).join(Product).where(
            Product.name == product_name,
            Price.active == True
        )
        
        if module_name:
            stmt = stmt.join(Module).where(Module.name == module_name)
        else:
            stmt = stmt.where(Price.module_id == None)
            
        # Order by version descending to get latest
        stmt = stmt.order_by(Price.version.desc())
        
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_new_price_version(self, product_id: str, amount_cents: int, module_id: Optional[str] = None):
        """
        Creates a new version of a price, archiving the old one implicitly by version number.
        """
        # Get current version
        stmt = select(Price).where(
            Price.product_id == product_id,
            Price.module_id == module_id,
            Price.active == True
        ).order_by(Price.version.desc())
        current = (await self.db.execute(stmt)).scalars().first()
        
        next_version = (current.version + 1) if current else 1
        
        new_price = Price(
            product_id=product_id,
            module_id=module_id,
            amount_cents=amount_cents,
            version=next_version,
            active=True,
            effective_from=datetime.utcnow()
        )
        self.db.add(new_price)
        
        if current:
            # We keep old prices active for existing subscriptions unless force-migrated?
            # Directive says "Existing subscriptions must update only through controlled flows."
            # So we leave old prices as is, but maybe mark them as 'deprecated' implicitly by not being latest?
            # Model has 'active'. Maybe we set old to active=False if we want to kill it?
            # For now, let's just create the new version.
            pass
            
        await self.db.flush()
        return new_price

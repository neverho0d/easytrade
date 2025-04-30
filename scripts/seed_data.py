# scripts/seed_data.py

import asyncio

# Import necessary components relative to project root if running script from there
# Or adjust paths based on how you run it (e.g., python -m scripts.seed_data)
from marketplace_aggregator.db import AsyncSessionFactory
from marketplace_aggregator.models.product import InventoryProduct, ProductTypeEnum
from marketplace_aggregator.models.promotional_rule import PromotionalRule
from marketplace_aggregator.repositories.inventory_product_repo import InventoryProductRepository
from marketplace_aggregator.repositories.promotional_rule_repo import PromotionalRuleRepository

async def seed():
    print("--- Seeding Initial Data ---")

    # Use the session factory to get a session
    async with AsyncSessionFactory() as session:
        # Create repository instances with the session
        inv_repo = InventoryProductRepository(session=session)
        rule_repo = PromotionalRuleRepository(session=session)

        # --- Create Product ---
        print("Creating sample product...")
        product_sku = "SEED-TSHIRT-01"
        product_title = "Seed Data T-Shirt (Blue, L)"
        # Check if product already exists
        existing_product = await inv_repo.get_one_or_none(sku=product_sku)
        if not existing_product:
            product = InventoryProduct(
                sku=product_sku,
                title=product_title,
                price=22.50,
                attributes={"Color": "Blue", "Size": "L"},
                description="A t-shirt created by the seed script."
            )
            await inv_repo.add(product)
            print(f"Added Product: {product.sku}")
        else:
            product = existing_product # Use existing if already there
            print(f"Product {product.sku} already exists.")


        # --- Create Promotional Rule ---
        print("\nCreating sample promotional rule...")
        marketplace = "Fakemazon" # Match adapter name used in main.py DI
        # Check if rule already exists
        existing_rule = await rule_repo.find_active_rule_for_marketplace(
            product_identifier=product.sku, marketplace_name=marketplace
        )
        if not existing_rule:
            rule = PromotionalRule(
                product_identifier=product.sku, # Link to the product's SKU
                marketplace_name=marketplace,
                product_type=ProductTypeEnum.INVENTORY.value, # Set correct type
                is_active=True,
                rule_name="Seed Rule for Blue T-Shirt on Fakemazon",
                price_override=21.99, # Example override
                marketplace_specific_settings={"category_hint": "apparel/shirt"}
            )
            # Use add, NOT add_or_update unless implemented. AA add handles adding.
            saved_rule = await rule_repo.add(rule) # Add returns the saved obj with ID
            await session.flush() # Commit after adding rule
            print(f"Added Rule ID: {saved_rule.id} for {saved_rule.product_identifier} on {saved_rule.marketplace_name}")
            rule_id_for_test = saved_rule.id
        elif existing_rule.id is not None:
             rule_id_for_test = existing_rule.id
             print(f"Rule for {product.sku} on {marketplace} already exists with ID: {rule_id_for_test}")
        else:
             print("ERROR: Existing rule found but has no ID?")
             rule_id_for_test = None


        await session.commit() # Commit the session to save changes
        print("\n--- Seeding Complete ---")
        if rule_id_for_test:
            print(f"===> Use rule_id: {rule_id_for_test} to test the POST /listings endpoint. <===")


if __name__ == "__main__":
    print("Running seed script...")
    asyncio.run(seed())
    print("Seed script finished.")
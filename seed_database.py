#!/usr/bin/env python
"""
Seed database with sample entities for testing.

This script creates sample entities in the database to populate 
the dashboard with meaningful data.
"""

import json
import sys
from datetime import date
from chronos.models import CorporateEntity, Status
from chronos.portfolio_db import DBPortfolioManager

# Sample entities with different statuses
SAMPLE_ENTITIES = [
    CorporateEntity(
        name="Acme Corporation",
        jurisdiction="DE",
        status=Status.ACTIVE,
        formed=date(2020, 1, 15),
        officers=["John Smith", "Jane Doe"],
        notes="Primary holding company"
    ),
    CorporateEntity(
        name="Widget Industries",
        jurisdiction="NY",
        status=Status.IN_COMPLIANCE,
        formed=date(2019, 6, 22),
        officers=["Robert Johnson"],
        notes="Manufacturing subsidiary"
    ),
    CorporateEntity(
        name="TechStart LLC",
        jurisdiction="CA",
        status=Status.PENDING,
        formed=date(2021, 3, 10),
        officers=["Maria Garcia", "David Kim"],
        notes="Technology R&D division"
    ),
    CorporateEntity(
        name="Global Services Inc",
        jurisdiction="TX",
        status=Status.DELINQUENT,
        formed=date(2018, 11, 5),
        officers=["Thomas Brown"],
        notes="Past due on filing requirements"
    ),
    CorporateEntity(
        name="Legacy Systems",
        jurisdiction="FL",
        status=Status.DISSOLVED,
        formed=date(2015, 8, 30),
        officers=["Patricia White", "Michael Lee"],
        notes="Operations closed in 2022"
    ),
    CorporateEntity(
        name="Sunrise Ventures",
        jurisdiction="WA",
        status=Status.ACTIVE,
        formed=date(2022, 4, 12),
        officers=["Elizabeth Chen"],
        notes="New acquisition"
    ),
    CorporateEntity(
        name="Central Holdings",
        jurisdiction="DE",
        status=Status.IN_COMPLIANCE,
        formed=date(2017, 9, 8),
        officers=["William Davis", "Jennifer Wilson"],
        notes="Financial arm"
    ),
    CorporateEntity(
        name="Atlantic Partners",
        jurisdiction="MA",
        status=Status.ACTIVE,
        formed=date(2020, 7, 19),
        officers=["James Martin"],
        notes="East coast operations"
    ),
    CorporateEntity(
        name="Pacific Group",
        jurisdiction="CA",
        status=Status.PENDING,
        formed=date(2023, 1, 28),
        officers=["Susan Taylor", "Richard Moore"],
        notes="West coast operations"
    ),
]

# Add additional entities from sample_portfolio.json if available
try:
    with open('sample_portfolio.json', 'r') as f:
        sample_data = json.load(f)
        
    for entity_data in sample_data:
        status_str = entity_data.get('status', 'PENDING')
        try:
            status = Status[status_str]
        except KeyError:
            status = Status.PENDING
            
        formed_str = entity_data.get('formed')
        formed = None
        if formed_str:
            year, month, day = map(int, formed_str.split('-'))
            formed = date(year, month, day)
            
        entity = CorporateEntity(
            name=entity_data['name'],
            jurisdiction=entity_data['jurisdiction'],
            status=status,
            formed=formed,
            officers=entity_data.get('officers', []),
            notes=entity_data.get('notes', '')
        )
        SAMPLE_ENTITIES.append(entity)
except (FileNotFoundError, json.JSONDecodeError):
    # Continue with default sample entities
    pass

def seed_database():
    """Add sample entities to the database."""
    pm = DBPortfolioManager()
    
    # Add all sample entities
    for entity in SAMPLE_ENTITIES:
        pm.add(entity)
        print(f"Added: {entity.name} ({entity.status.name})")
    
    print(f"\nAdded {len(SAMPLE_ENTITIES)} entities to the database!")

if __name__ == "__main__":
    # Initialize DB if needed
    from chronos.db import create_all
    print("Ensuring database tables exist...")
    create_all()
    
    # Seed the database
    print("Seeding database with sample entities...")
    seed_database()
    
    print("\nDone! You can now run the API server with:")
    print("uvicorn api.main:app --reload --port 8001")
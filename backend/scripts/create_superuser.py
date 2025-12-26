#!/usr/bin/env python
"""
Script to create a super admin user.

Usage:
    python scripts/create_superuser.py

Or with Docker:
    docker-compose exec api python scripts/create_superuser.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from getpass import getpass


async def create_superuser():
    """Create a super admin user interactively."""
    from app.config.database import Database
    from app.models import User, Institution, OMRTemplate, Test, OMRSheet, UploadBatch
    from app.api.v1.auth.service import AuthService

    print("=" * 50)
    print("OMR Evaluation System - Super Admin Creation")
    print("=" * 50)
    print()

    # Get user input
    email = input("Email: ").strip()
    if not email:
        print("Error: Email is required")
        return

    first_name = input("First Name: ").strip()
    if not first_name:
        print("Error: First name is required")
        return

    last_name = input("Last Name: ").strip()
    if not last_name:
        print("Error: Last name is required")
        return

    password = getpass("Password: ")
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        return

    password_confirm = getpass("Confirm Password: ")
    if password != password_confirm:
        print("Error: Passwords do not match")
        return

    # Connect to database
    print("\nConnecting to database...")
    await Database.connect()
    await Database.init_beanie([
        User, Institution, OMRTemplate, Test, OMRSheet, UploadBatch
    ])

    # Check if super admin already exists
    existing = await User.find_one(User.email == email.lower())
    if existing:
        print(f"Error: User with email '{email}' already exists")
        await Database.disconnect()
        return

    # Create super admin
    try:
        user = await AuthService.create_super_admin(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        print()
        print("=" * 50)
        print("Super Admin created successfully!")
        print("=" * 50)
        print(f"  Email: {user.email}")
        print(f"  Name: {user.full_name}")
        print(f"  Role: {user.role.value}")
        print(f"  ID: {user.id}")
        print()
    except Exception as e:
        print(f"Error creating super admin: {e}")

    await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(create_superuser())

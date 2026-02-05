"""
User Service
============

User management and password synchronization service.
"""

from sqlalchemy import select

from app.config import get_settings
from app.db import get_db_manager
from app.models import User


async def sync_user_passwords() -> None:
    """
    Synchronize user passwords from environment variables.
    
    This function is called on application startup to ensure that
    admin and moderator passwords match the values set in the .env file.
    
    If a user doesn't exist, it will be created.
    If a user exists, their password will be updated.
    
    Environment Variables:
        ADMIN_PASSWORD: Password for the 'admin' user
        MODERATOR_PASSWORD: Password for the 'moderator' user
    """
    settings = get_settings()
    db_manager = get_db_manager()
    
    # Define users to sync: (username, password_from_settings)
    users_to_sync = [
        ("admin", settings.admin_password),
        ("moderator", settings.moderator_password),
    ]
    
    async with db_manager.session() as session:
        for username, password in users_to_sync:
            if password is None:
                # Skip if no password is configured for this user
                print("No password set for user '{username}', skipping...".format(username=username))
                continue
            
            # Check if user exists
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user is None:
                # Create new user
                user = User(username=username)
                user.set_password(password)
                session.add(user)
                print(f"  Created user '{username}' with password from environment")
            else:
                # Update existing user's password
                user.set_password(password)
                print(f"  Updated password for user '{username}' from environment")
        
        await session.commit()

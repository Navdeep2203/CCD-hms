import argparse
from getpass import getpass

from app.core.security import ADMIN, hash_password
from app.database import (
    execute,
    execute_returning_id,
    fetch_one,
    transaction,
)


def create_admin(email: str, name: str, password: str) -> int:
    """Create an administrator account and return its user ID."""

    with transaction() as conn:
        # Prevent creating an account with an existing email.
        existing = fetch_one(
            "SELECT user_id FROM users WHERE LOWER(email) = LOWER(:email)",
            {"email": email},
            conn=conn,
        )

        if existing:
            raise ValueError(f"An account with email {email} already exists.")

        # Confirm that the application role exists.
        role = fetch_one(
            "SELECT role_id FROM roles WHERE role_name = :role",
            {"role": ADMIN},
            conn=conn,
        )

        if not role:
            raise RuntimeError(
                f"{ADMIN} does not exist. Run database migrations first."
            )

        # Create the user.
        user_id = execute_returning_id(
            """
            INSERT INTO users (
                email,
                password_hash,
                name,
                is_active,
                must_change_password
            )
            VALUES (
                :email,
                :password_hash,
                :name,
                TRUE,
                FALSE
            )
            RETURNING user_id
            """,
            {
                "email": email,
                "password_hash": hash_password(password),
                "name": name,
            },
            conn=conn,
        )

        # Assign the administrator role.
        execute(
            """
            INSERT INTO user_roles (user_id, role_id)
            VALUES (:user_id, :role_id)
            """,
            {
                "user_id": user_id,
                "role_id": role["role_id"],
            },
            conn=conn,
        )

    return user_id


def main():
    parser = argparse.ArgumentParser(
        description="Create an administrator account."
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address for the administrator account.",
    )
    args = parser.parse_args()

    email = args.email.strip()
    if not email:
        parser.error("Email cannot be empty.")

    name = input("Admin name: ").strip()
    if not name:
        parser.error("Name cannot be empty.")

    password = getpass("Admin password: ")
    confirmation = getpass("Confirm password: ")

    if not password:
        parser.error("Password cannot be empty.")

    if password != confirmation:
        parser.error("Passwords do not match.")

    try:
        user_id = create_admin(email, name, password)
        print(f"Administrator created successfully (user_id={user_id}).")
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
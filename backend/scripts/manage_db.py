#!/usr/bin/env python3
"""
Database Management Script for AgriProfit Backend

A comprehensive CLI tool for managing database migrations, seeding,
and maintenance operations.

Usage:
    python scripts/manage_db.py <command> [options]

Commands:
    create <message>    Create a new migration
    upgrade             Apply all pending migrations
    downgrade [steps]   Rollback migrations (default: 1)
    current             Show current migration revision
    history             Show migration history
    reset               Drop all tables and recreate (requires confirmation)
    seed                Populate database with sample data
"""

import argparse
import os
import sys
import subprocess
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional
import uuid

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.prompt import Confirm
from rich import print as rprint

# Use ASCII symbols for Windows compatibility
CHECKMARK = "[OK]"
CROSS = "[X]"
BULLET = "*"
WARNING = "[!]"

console = Console(force_terminal=True)

# Environment validation
def validate_environment() -> bool:
    """Validate that the environment is properly configured."""
    errors = []

    # Check for .env file
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        errors.append("Missing .env file - copy from .env.example")

    # Check for alembic.ini
    alembic_ini = PROJECT_ROOT / "alembic.ini"
    if not alembic_ini.exists():
        errors.append("Missing alembic.ini file")

    # Check DATABASE_URL
    from dotenv import load_dotenv
    load_dotenv(env_file)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        errors.append("DATABASE_URL environment variable not set")

    if errors:
        console.print(Panel(
            "\n".join(f"[red]{CROSS}[/red] {e}" for e in errors),
            title="[bold red]Environment Validation Failed[/bold red]",
            border_style="red"
        ))
        return False

    return True


def get_database_url() -> str:
    """Get the database URL with password masked for display."""
    import re
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")

    url = os.getenv("DATABASE_URL", "")
    return re.sub(r'://[^:]+:[^@]+@', '://***:***@', url)


def run_alembic_command(args: list, capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run an alembic command and return the result."""
    cmd = [sys.executable, "-m", "alembic"] + args
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=capture_output,
        text=True
    )


def show_database_info():
    """Display current database connection info."""
    console.print(f"[dim]Database:[/dim] {get_database_url()}")
    console.print()


# ============================================================================
# COMMANDS
# ============================================================================

def cmd_current(verbose: bool = False):
    """Show current migration revision."""
    console.print(Panel("[bold blue]Current Migration Status[/bold blue]"))
    show_database_info()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Checking current revision...", total=None)
        result = run_alembic_command(["current"], capture_output=True)

    if result.returncode != 0:
        console.print(f"[red]Error:[/red] {result.stderr}")
        return False

    # Parse output
    lines = result.stdout.strip().split('\n')
    revision = None
    for line in lines:
        if line and not line.startswith('[') and not line.startswith('INFO'):
            revision = line.strip()
            break

    if revision:
        if "(head)" in revision:
            console.print(f"[green]{CHECKMARK} Current revision:[/green] [bold]{revision}[/bold]")
            console.print("[green]Database is up to date![/green]")
        else:
            console.print(f"[yellow]{WARNING} Current revision:[/yellow] [bold]{revision}[/bold]")
            console.print("[yellow]Pending migrations may exist.[/yellow]")
    else:
        console.print(f"[yellow]{WARNING} No migrations applied yet[/yellow]")

    return True


def cmd_history(verbose: bool = False):
    """Show migration history."""
    console.print(Panel("[bold blue]Migration History[/bold blue]"))
    show_database_info()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Loading migration history...", total=None)
        result = run_alembic_command(["history"], capture_output=True)

    if result.returncode != 0:
        console.print(f"[red]Error:[/red] {result.stderr}")
        return False

    # Create table
    table = Table(title="Migration History")
    table.add_column("Revision", style="cyan")
    table.add_column("Parent", style="dim")
    table.add_column("Description", style="green")
    table.add_column("Status", justify="center")

    lines = result.stdout.strip().split('\n')
    for line in lines:
        if '->' in line:
            # Parse: parent -> revision (head), description
            parts = line.split('->')
            parent = parts[0].strip()
            if parent == '<base>':
                parent = "[dim]base[/dim]"

            rest = parts[1].strip()
            # Check for (head) marker
            is_head = "(head)" in rest
            rest = rest.replace("(head)", "").strip()

            # Split revision and description
            if ',' in rest:
                revision, description = rest.split(',', 1)
                revision = revision.strip()
                description = description.strip()
            else:
                revision = rest
                description = ""

            status = f"[green]{CHECKMARK} HEAD[/green]" if is_head else ""
            table.add_row(revision, parent, description, status)

    console.print(table)
    return True


def cmd_create(message: str, verbose: bool = False):
    """Create a new migration."""
    if not message:
        console.print("[red]Error:[/red] Migration message is required")
        return False

    console.print(Panel(f"[bold blue]Creating Migration[/bold blue]\n[dim]{message}[/dim]"))
    show_database_info()

    # Show current state
    console.print("[bold]Before:[/bold]")
    cmd_current(verbose)
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Generating migration...", total=None)
        result = run_alembic_command(
            ["revision", "--autogenerate", "-m", message],
            capture_output=True
        )

    if result.returncode != 0:
        console.print(f"[red]Error creating migration:[/red]")
        console.print(result.stderr)
        return False

    # Extract generated file path
    output = result.stdout + result.stderr
    for line in output.split('\n'):
        if 'Generating' in line and '.py' in line:
            console.print(f"[green]{CHECKMARK} Migration created:[/green] {line.split('Generating')[-1].strip()}")
            break

    # Show detected changes
    console.print("\n[bold]Detected changes:[/bold]")
    for line in output.split('\n'):
        if 'Detected' in line:
            change = line.split(']')[-1].strip() if ']' in line else line
            console.print(f"  [cyan]{BULLET}[/cyan] {change}")

    return True


def cmd_upgrade(verbose: bool = False):
    """Apply all pending migrations."""
    console.print(Panel("[bold blue]Upgrading Database[/bold blue]"))
    show_database_info()

    # Show before state
    console.print("[bold]Before:[/bold]")
    run_alembic_command(["current"])
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task("Applying migrations...", total=100)

        result = run_alembic_command(["upgrade", "head"], capture_output=True)
        progress.update(task, completed=100)

    if result.returncode != 0:
        console.print(f"[red]Error during upgrade:[/red]")
        console.print(result.stderr)
        return False

    # Show applied migrations
    output = result.stdout + result.stderr
    applied = []
    for line in output.split('\n'):
        if 'Running upgrade' in line:
            applied.append(line.split('Running upgrade')[-1].strip())

    if applied:
        console.print(f"[green]{CHECKMARK} Applied {len(applied)} migration(s):[/green]")
        for migration in applied:
            console.print(f"  [cyan]{BULLET}[/cyan] {migration}")
    else:
        console.print(f"[green]{CHECKMARK} Database already up to date[/green]")

    # Show after state
    console.print("\n[bold]After:[/bold]")
    run_alembic_command(["current"])

    return True


def cmd_downgrade(steps: int = 1, verbose: bool = False):
    """Rollback migrations."""
    console.print(Panel(f"[bold yellow]Rolling Back {steps} Migration(s)[/bold yellow]"))
    show_database_info()

    # Show before state
    console.print("[bold]Before:[/bold]")
    run_alembic_command(["current"])
    console.print()

    # Confirm
    if not Confirm.ask(f"[yellow]Are you sure you want to rollback {steps} migration(s)?[/yellow]"):
        console.print("[dim]Cancelled.[/dim]")
        return False

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        progress.add_task("Rolling back...", total=None)
        result = run_alembic_command([f"downgrade", f"-{steps}"], capture_output=True)

    if result.returncode != 0:
        console.print(f"[red]Error during downgrade:[/red]")
        console.print(result.stderr)
        return False

    # Show rolled back migrations
    output = result.stdout + result.stderr
    rolled_back = []
    for line in output.split('\n'):
        if 'Running downgrade' in line:
            rolled_back.append(line.split('Running downgrade')[-1].strip())

    if rolled_back:
        console.print(f"[yellow]{CHECKMARK} Rolled back {len(rolled_back)} migration(s):[/yellow]")
        for migration in rolled_back:
            console.print(f"  [cyan]{BULLET}[/cyan] {migration}")

    # Show after state
    console.print("\n[bold]After:[/bold]")
    run_alembic_command(["current"])

    return True


def cmd_reset(verbose: bool = False):
    """Drop all tables and recreate from migrations."""
    console.print(Panel("[bold red]DATABASE RESET[/bold red]\n[dim]This will drop ALL tables and data![/dim]"))
    show_database_info()

    # Double confirmation
    console.print("[red]WARNING: This operation is DESTRUCTIVE and IRREVERSIBLE![/red]")
    console.print("[red]All data will be permanently deleted.[/red]")
    console.print()

    if not Confirm.ask("[yellow]Are you sure you want to reset the database?[/yellow]"):
        console.print("[dim]Cancelled.[/dim]")
        return False

    if not Confirm.ask("[red]Type YES to confirm database reset[/red]", default=False):
        console.print("[dim]Cancelled.[/dim]")
        return False

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        # Downgrade to base
        task = progress.add_task("Dropping all tables...", total=None)
        result = run_alembic_command(["downgrade", "base"], capture_output=True)

        if result.returncode != 0:
            console.print(f"[red]Error during downgrade:[/red]")
            console.print(result.stderr)
            return False

        progress.update(task, description="Recreating tables...")

        # Upgrade to head
        result = run_alembic_command(["upgrade", "head"], capture_output=True)

        if result.returncode != 0:
            console.print(f"[red]Error during upgrade:[/red]")
            console.print(result.stderr)
            return False

    console.print(f"[green]{CHECKMARK} Database reset complete![/green]")

    # Show current state
    console.print("\n[bold]Current state:[/bold]")
    run_alembic_command(["current"])

    return True


def cmd_seed(verbose: bool = False):
    """Populate database with sample data."""
    console.print(Panel("[bold blue]Seeding Database[/bold blue]"))
    show_database_info()

    if not Confirm.ask("[yellow]This will add sample data to the database. Continue?[/yellow]"):
        console.print("[dim]Cancelled.[/dim]")
        return False

    try:
        from faker import Faker
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        # Import models and session
        from app.database.session import engine, SessionLocal
        from app.models import (
            User, Commodity, Mandi, PriceHistory, PriceForecast,
            CommunityPost, Notification, AdminAction, OTPRequest
        )

        fake = Faker('en_IN')  # Indian locale

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
        ) as progress:

            db: Session = SessionLocal()

            try:
                # ============================================================
                # USERS (5 sample users)
                # ============================================================
                task = progress.add_task("Creating users...", total=5)
                users = []

                # Create admin user
                admin = User(
                    id=uuid.uuid4(),
                    phone_number="9876543210",
                    role="admin",
                    district="Ernakulam",
                    language="en",
                )
                db.add(admin)
                users.append(admin)
                progress.advance(task)

                # Create farmer users
                districts = ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur"]
                for i, district in enumerate(districts):
                    user = User(
                        id=uuid.uuid4(),
                        phone_number=f"987654321{i+1}",
                        role="farmer",
                        district=district,
                        language="en" if i % 2 == 0 else "ml",
                    )
                    db.add(user)
                    users.append(user)
                    progress.advance(task)

                db.flush()
                console.print(f"  [green]{CHECKMARK}[/green] Created {len(users)} users")

                # ============================================================
                # COMMODITIES (10 commodities)
                # ============================================================
                task = progress.add_task("Creating commodities...", total=10)
                commodities_data = [
                    ("Rice", "Grains", "kg"),
                    ("Wheat", "Grains", "kg"),
                    ("Tomato", "Vegetables", "kg"),
                    ("Onion", "Vegetables", "kg"),
                    ("Potato", "Vegetables", "kg"),
                    ("Banana", "Fruits", "dozen"),
                    ("Coconut", "Fruits", "piece"),
                    ("Cardamom", "Spices", "kg"),
                    ("Pepper", "Spices", "kg"),
                    ("Rubber", "Cash Crops", "kg"),
                ]

                commodities = []
                for name, category, unit in commodities_data:
                    commodity = Commodity(
                        id=uuid.uuid4(),
                        name=name,
                        category=category,
                        unit=unit,
                    )
                    db.add(commodity)
                    commodities.append(commodity)
                    progress.advance(task)

                db.flush()
                console.print(f"  [green]{CHECKMARK}[/green] Created {len(commodities)} commodities")

                # ============================================================
                # MANDIS (15 mandis across Kerala)
                # ============================================================
                task = progress.add_task("Creating mandis...", total=15)
                mandis_data = [
                    ("Thiruvananthapuram Central Market", "Kerala", "Thiruvananthapuram", "TVM001", "8.5241", "76.9366"),
                    ("Chalai Bazaar", "Kerala", "Thiruvananthapuram", "TVM002", "8.4855", "76.9492"),
                    ("Ernakulam Market", "Kerala", "Ernakulam", "EKM001", "9.9312", "76.2673"),
                    ("Broadway Market", "Kerala", "Ernakulam", "EKM002", "9.9680", "76.2870"),
                    ("Kozhikode Mandi", "Kerala", "Kozhikode", "KZD001", "11.2588", "75.7804"),
                    ("SM Street Market", "Kerala", "Kozhikode", "KZD002", "11.2500", "75.7700"),
                    ("Thrissur Round", "Kerala", "Thrissur", "TSR001", "10.5276", "76.2144"),
                    ("Palakkad Market", "Kerala", "Palakkad", "PKD001", "10.7867", "76.6548"),
                    ("Kannur Central", "Kerala", "Kannur", "KNR001", "11.8745", "75.3704"),
                    ("Kollam Market", "Kerala", "Kollam", "KLM001", "8.8932", "76.6141"),
                    ("Alappuzha Mandi", "Kerala", "Alappuzha", "ALP001", "9.4981", "76.3388"),
                    ("Kottayam Market", "Kerala", "Kottayam", "KTM001", "9.5916", "76.5222"),
                    ("Idukki Spice Market", "Kerala", "Idukki", "IDK001", "9.8494", "76.9720"),
                    ("Wayanad Agri Market", "Kerala", "Wayanad", "WYD001", "11.6854", "76.1320"),
                    ("Malappuram Mandi", "Kerala", "Malappuram", "MLP001", "11.0509", "76.0710"),
                ]

                mandis = []
                for name, state, district, market_code, lat, lon in mandis_data:
                    mandi = Mandi(
                        id=uuid.uuid4(),
                        name=name,
                        state=state,
                        district=district,
                        market_code=market_code,
                        address=f"{name}, {district}, {state}",
                        latitude=float(lat),
                        longitude=float(lon),
                    )
                    db.add(mandi)
                    mandis.append(mandi)
                    progress.advance(task)

                db.flush()
                console.print(f"  [green]{CHECKMARK}[/green] Created {len(mandis)} mandis")

                # ============================================================
                # PRICE HISTORY (50 records over last 30 days)
                # ============================================================
                task = progress.add_task("Creating price history...", total=50)

                import random
                base_prices = {
                    "Rice": 45, "Wheat": 35, "Tomato": 40, "Onion": 30,
                    "Potato": 25, "Banana": 60, "Coconut": 25, "Cardamom": 2500,
                    "Pepper": 450, "Rubber": 150
                }

                price_records = []
                seen_combinations = set()
                attempts = 0
                max_attempts = 200

                while len(price_records) < 50 and attempts < max_attempts:
                    attempts += 1
                    commodity = random.choice(commodities)
                    mandi = random.choice(mandis)
                    days_ago = random.randint(0, 30)
                    record_date = datetime.now().date() - timedelta(days=days_ago)

                    # Ensure unique combination
                    key = (commodity.id, mandi.name, record_date)
                    if key in seen_combinations:
                        continue
                    seen_combinations.add(key)

                    base = base_prices.get(commodity.name, 50)
                    variance = base * 0.2  # 20% variance
                    modal = base + random.uniform(-variance, variance)
                    min_price = modal * 0.9
                    max_price = modal * 1.1

                    price = PriceHistory(
                        id=uuid.uuid4(),
                        commodity_id=commodity.id,
                        mandi_id=mandi.id,
                        mandi_name=mandi.name,
                        price_date=record_date,
                        modal_price=Decimal(str(round(modal, 2))),
                        min_price=Decimal(str(round(min_price, 2))),
                        max_price=Decimal(str(round(max_price, 2))),
                    )
                    db.add(price)
                    price_records.append(price)
                    progress.advance(task)

                db.flush()
                console.print(f"  [green]{CHECKMARK}[/green] Created {len(price_records)} price history records")

                # ============================================================
                # PRICE FORECASTS (10 forecasts)
                # ============================================================
                task = progress.add_task("Creating price forecasts...", total=10)

                forecasts = []
                seen_forecast_combinations = set()
                forecast_attempts = 0
                max_forecast_attempts = 50

                while len(forecasts) < 10 and forecast_attempts < max_forecast_attempts:
                    forecast_attempts += 1
                    commodity = random.choice(commodities)
                    mandi = random.choice(mandis)
                    forecast_date = datetime.now().date() + timedelta(days=random.randint(1, 14))

                    # Ensure unique combination
                    key = (commodity.id, mandi.name, forecast_date)
                    if key in seen_forecast_combinations:
                        continue
                    seen_forecast_combinations.add(key)

                    base = base_prices.get(commodity.name, 50)
                    predicted = base * random.uniform(0.9, 1.15)
                    confidence = random.uniform(0.7, 0.95)

                    forecast = PriceForecast(
                        id=uuid.uuid4(),
                        commodity_id=commodity.id,
                        mandi_id=mandi.id,
                        mandi_name=mandi.name,
                        forecast_date=forecast_date,
                        predicted_price=Decimal(str(round(predicted, 2))),
                        confidence_level=Decimal(str(round(confidence, 4))),
                        model_version="v1.0.0",
                    )
                    db.add(forecast)
                    forecasts.append(forecast)
                    progress.advance(task)

                db.flush()
                console.print(f"  [green]{CHECKMARK}[/green] Created {len(forecasts)} price forecasts")

                # ============================================================
                # COMMUNITY POSTS (20 posts)
                # ============================================================
                task = progress.add_task("Creating community posts...", total=20)

                post_titles = [
                    "Best practices for rice cultivation",
                    "How to identify tomato diseases",
                    "Water management tips for summer",
                    "Organic fertilizers that work",
                    "Market prices seem high this week",
                    "Looking for bulk buyers for coconut",
                    "Cardamom harvest season tips",
                    "New irrigation techniques",
                    "Pest control without chemicals",
                    "Weather forecast concerns",
                    "Government subsidy information",
                    "Seed quality discussion",
                    "Transport cost sharing",
                    "Storage solutions for grains",
                    "Crop rotation benefits",
                    "Soil testing results",
                    "Farm equipment rental",
                    "Success with drip irrigation",
                    "Banana cultivation guide",
                    "Pepper price predictions",
                ]

                posts = []
                farmer_users = [u for u in users if u.role == "farmer"]
                for i, title in enumerate(post_titles):
                    user = random.choice(farmer_users)
                    days_ago = random.randint(0, 60)

                    post = CommunityPost(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        title=title,
                        content=fake.paragraph(nb_sentences=5),
                        post_type=random.choice(["normal", "alert"]),
                        district=user.district,
                    )
                    db.add(post)
                    posts.append(post)
                    progress.advance(task)

                db.flush()
                console.print(f"  [green]{CHECKMARK}[/green] Created {len(posts)} community posts")

                # ============================================================
                # NOTIFICATIONS (15 notifications)
                # ============================================================
                task = progress.add_task("Creating notifications...", total=15)

                notification_templates = [
                    ("Price Alert", "price_alert", "Tomato prices increased by 15% in your area"),
                    ("Weather Update", "weather", "Heavy rainfall expected in the next 3 days"),
                    ("Market Update", "market", "New mandi added in your district"),
                    ("Community", "community", "Your post received 10 new likes"),
                    ("System", "system", "App update available with new features"),
                ]

                notifications = []
                for i in range(15):
                    user = random.choice(users)
                    title, ntype, message = random.choice(notification_templates)
                    days_ago = random.randint(0, 14)
                    is_read = random.choice([True, False])

                    notification = Notification(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        title=title,
                        message=message,
                        notification_type=ntype,
                        is_read=is_read,
                        read_at=datetime.now() - timedelta(days=days_ago - 1) if is_read else None,
                    )
                    db.add(notification)
                    notifications.append(notification)
                    progress.advance(task)

                db.flush()
                console.print(f"  [green]{CHECKMARK}[/green] Created {len(notifications)} notifications")

                # ============================================================
                # ADMIN ACTIONS (5 actions)
                # ============================================================
                task = progress.add_task("Creating admin actions...", total=5)

                action_types = [
                    "user_verified",
                    "post_moderated",
                    "price_corrected",
                    "mandi_approved",
                    "report_reviewed",
                ]

                admin_actions = []
                for action_type in action_types:
                    target_user = random.choice(farmer_users)
                    days_ago = random.randint(0, 30)

                    action = AdminAction(
                        id=uuid.uuid4(),
                        admin_id=admin.id,
                        action_type=action_type,
                        target_user_id=target_user.id,
                        description=f"Admin performed {action_type} action",
                        action_metadata={"reason": "routine check", "source": "seed_script"},
                        created_at=datetime.now() - timedelta(days=days_ago),
                    )
                    db.add(action)
                    admin_actions.append(action)
                    progress.advance(task)

                db.flush()
                console.print(f"  [green]{CHECKMARK}[/green] Created {len(admin_actions)} admin actions")

                # Commit all changes
                db.commit()

            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()

        # Summary
        console.print()
        table = Table(title="Seed Data Summary")
        table.add_column("Entity", style="cyan")
        table.add_column("Count", justify="right", style="green")

        table.add_row("Users", "5")
        table.add_row("Commodities", "10")
        table.add_row("Mandis", "15")
        table.add_row("Price History", "50")
        table.add_row("Price Forecasts", "10")
        table.add_row("Community Posts", "20")
        table.add_row("Notifications", "15")
        table.add_row("Admin Actions", "5")
        table.add_row("[bold]Total Records[/bold]", "[bold]130[/bold]")

        console.print(table)
        console.print(f"\n[green]{CHECKMARK} Database seeding complete![/green]")

        return True

    except ImportError as e:
        console.print(f"[red]Import error:[/red] {e}")
        console.print("[dim]Make sure all dependencies are installed.[/dim]")
        return False
    except Exception as e:
        console.print(f"[red]Error during seeding:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        return False


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Database Management Script for AgriProfit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s current                    Show current migration
  %(prog)s history                    Show migration history
  %(prog)s create "Add user roles"    Create a new migration
  %(prog)s upgrade                    Apply pending migrations
  %(prog)s downgrade                  Rollback last migration
  %(prog)s downgrade 3                Rollback last 3 migrations
  %(prog)s reset                      Reset database (destructive!)
  %(prog)s seed                       Add sample data
        """
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # current
    subparsers.add_parser('current', help='Show current migration revision')

    # history
    subparsers.add_parser('history', help='Show migration history')

    # create
    create_parser = subparsers.add_parser('create', help='Create a new migration')
    create_parser.add_argument('message', help='Migration description message')

    # upgrade
    subparsers.add_parser('upgrade', help='Apply all pending migrations')

    # downgrade
    downgrade_parser = subparsers.add_parser('downgrade', help='Rollback migrations')
    downgrade_parser.add_argument(
        'steps',
        nargs='?',
        type=int,
        default=1,
        help='Number of migrations to rollback (default: 1)'
    )

    # reset
    subparsers.add_parser('reset', help='Drop all tables and recreate (destructive!)')

    # seed
    subparsers.add_parser('seed', help='Populate database with sample data')

    args = parser.parse_args()

    # Show banner
    console.print(Panel.fit(
        "[bold blue]AgriProfit Database Manager[/bold blue]\n"
        "[dim]Manage migrations, seeding, and maintenance[/dim]",
        border_style="blue"
    ))
    console.print()

    # No command specified
    if not args.command:
        parser.print_help()
        return 0

    # Validate environment
    if not validate_environment():
        return 1

    # Execute command
    commands = {
        'current': lambda: cmd_current(args.verbose),
        'history': lambda: cmd_history(args.verbose),
        'create': lambda: cmd_create(args.message, args.verbose),
        'upgrade': lambda: cmd_upgrade(args.verbose),
        'downgrade': lambda: cmd_downgrade(args.steps, args.verbose),
        'reset': lambda: cmd_reset(args.verbose),
        'seed': lambda: cmd_seed(args.verbose),
    }

    try:
        success = commands[args.command]()
        return 0 if success else 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        return 130
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())

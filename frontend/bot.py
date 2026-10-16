import os
import sys
import json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps

# Load environment variables from .env
load_dotenv()
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# Configure Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Retrieve configuration
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_PASSWORD = os.environ.get("BOT_ADMIN_PASSWORD", "admin123")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BACKEND_USERNAME = os.environ.get("BACKEND_USERNAME", "admin")
BACKEND_PASSWORD = os.environ.get("BACKEND_PASSWORD", "admin123")

# Your verified live URL
WEB_APP_URL = "https://betel1221.github.io/redhelp-login/?v=6"

if not TOKEN:
    logger.critical("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
    sys.exit(1)

# In-memory database of authorized user IDs → their JWT tokens
AUTHORIZED_USERS: dict[int, str] = {}  # user_id → jwt_token


def _get_backend_token() -> str | None:
    """Get a JWT token from the backend using configured credentials."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={"username": BACKEND_USERNAME, "password": BACKEND_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception as e:
        logger.warning("Backend auth failed: %s", e)
    return None


def _backend_get(path: str, token: str | None = None) -> dict | None:
    """Make an authenticated GET request to the backend."""
    if not token:
        token = _get_backend_token()
    if not token:
        return None
    try:
        resp = requests.get(
            f"{BACKEND_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning("Backend GET %s failed: %s", path, e)
    return None


def _backend_post(path: str, payload: dict, token: str | None = None) -> dict | None:
    """Make an authenticated POST request to the backend."""
    if not token:
        token = _get_backend_token()
    if not token:
        return None
    try:
        resp = requests.post(
            f"{BACKEND_URL}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning("Backend POST %s failed: %s", path, e)
    return None


def _format_database_status() -> str:
    """Fetch real database metrics from backend."""
    data = _backend_get("/api/v1/monitoring/database")
    if not data:
        # Fall back to schema overview
        overview = _backend_get("/api/v1/schema/overview")
        if overview:
            target = overview.get("target_database", {})
            app_db = overview.get("app_database", {})
            return (
                f"🛢️ *Database Status (Live)*\n\n"
                f"*Target DB:* {target.get('status', 'Unknown')}\n"
                f"*Tables:* {target.get('table_count', 'N/A')}\n"
                f"*App DB:* {app_db.get('status', 'Unknown')}\n"
                f"*App Tables:* {app_db.get('table_count', 'N/A')}\n"
                f"\n_Data from: /api/v1/schema/overview_"
            )
        return "❌ *Database:* Backend unavailable — cannot retrieve real metrics."

    status = data.get("connection_status", "unknown")
    status_emoji = "✅" if status == "connected" else "⚠️"
    lines = [f"{status_emoji} *Database Status (Live)*\n"]

    if data.get("database_version"):
        lines.append(f"📌 *Version:* {data['database_version']}")
    if data.get("database_size_human"):
        lines.append(f"💾 *Size:* {data['database_size_human']}")
    if data.get("table_count") is not None:
        lines.append(f"📋 *Tables:* {data['table_count']}")
    if data.get("active_connections") is not None:
        util = f" ({data['connection_utilization_pct']}% utilized)" if data.get("connection_utilization_pct") else ""
        lines.append(f"🔌 *Connections:* {data['active_connections']}{util}")
    if data.get("cache_hit_ratio") is not None:
        lines.append(f"⚡ *Cache Hit:* {data['cache_hit_ratio']}%")
    if data.get("deadlocks") is not None:
        lines.append(f"🔒 *Deadlocks:* {data['deadlocks']}")
    if data.get("slow_query_count") is not None:
        lines.append(f"🐌 *Slow Queries:* {data['slow_query_count']}")

    lines.append(f"\n_Collected: {data.get('collected_at', 'now')}_")
    return "\n".join(lines)


def _format_server_status() -> str:
    """Fetch real server metrics from backend."""
    data = _backend_get("/api/v1/monitoring/server")
    if not data:
        return "❌ *Server:* Backend unavailable — cannot retrieve real metrics."

    status = data.get("status", "unknown")
    status_emoji = "✅" if status == "healthy" else "⚠️"
    lines = [f"{status_emoji} *Server Status (Live)*\n"]

    lines.append(f"🖥️ *Host:* {data.get('hostname', 'N/A')}")
    lines.append(f"💻 *OS:* {data.get('platform', '')} {data.get('platform_version', '')}")

    cpu = data.get("cpu", {})
    if cpu:
        cpu_pct = cpu.get("usage_percent", "N/A")
        cpu_emoji = "🔴" if isinstance(cpu_pct, (int, float)) and cpu_pct > 85 else "🟡" if isinstance(cpu_pct, (int, float)) and cpu_pct > 70 else "🟢"
        lines.append(f"{cpu_emoji} *CPU:* {cpu_pct}% ({cpu.get('core_count', '?')} cores)")

    mem = data.get("memory", {})
    if mem:
        mem_pct = mem.get("usage_percent", "N/A")
        mem_emoji = "🔴" if isinstance(mem_pct, (int, float)) and mem_pct > 85 else "🟡" if isinstance(mem_pct, (int, float)) and mem_pct > 70 else "🟢"
        lines.append(f"{mem_emoji} *RAM:* {mem_pct}% ({mem.get('used_mb', '?')} / {mem.get('total_mb', '?')} MB)")

    disk = data.get("disk", {})
    if disk:
        disk_pct = disk.get("usage_percent", "N/A")
        disk_emoji = "🔴" if isinstance(disk_pct, (int, float)) and disk_pct > 85 else "🟡" if isinstance(disk_pct, (int, float)) and disk_pct > 70 else "🟢"
        lines.append(f"{disk_emoji} *Disk:* {disk_pct}% ({disk.get('used_gb', '?')} / {disk.get('total_gb', '?')} GB)")

    uptime = data.get("uptime_human")
    if uptime:
        lines.append(f"⏱️ *Uptime:* {uptime}")

    proc = data.get("process_count")
    if proc:
        lines.append(f"⚙️ *Processes:* {proc}")

    load = data.get("load_average")
    if load:
        lines.append(f"📊 *Load:* {load.get('1min', '?')} / {load.get('5min', '?')} / {load.get('15min', '?')} (1/5/15m)")

    lines.append(f"\n_Collected: {data.get('collected_at', 'now')}_")
    return "\n".join(lines)


def _format_security_status() -> str:
    """Fetch real security events from backend."""
    data = _backend_get("/api/v1/monitoring/security")
    if not data:
        return "❌ *Security:* Backend unavailable — cannot retrieve real events."

    summary = data.get("summary", {})
    events = data.get("events", [])
    threat = summary.get("threat_level", "UNKNOWN")
    threat_emoji = "🔴" if threat in ("CRITICAL", "HIGH") else "🟡" if threat == "ELEVATED" else "🟢"

    lines = [f"{threat_emoji} *Security Status (Live)*\n"]
    lines.append(f"🛡️ *Threat Level:* {threat}")
    lines.append(f"📊 *Total Events:* {summary.get('total_events', 0)}")
    if summary.get('critical_count', 0) > 0:
        lines.append(f"🔴 *Critical:* {summary['critical_count']}")
    if summary.get('high_count', 0) > 0:
        lines.append(f"🟠 *High:* {summary['high_count']}")
    if summary.get('medium_count', 0) > 0:
        lines.append(f"🟡 *Medium:* {summary['medium_count']}")
    if summary.get('failed_login_attempts_24h', 0) > 0:
        lines.append(f"🔒 *Failed Logins (24h):* {summary['failed_login_attempts_24h']}")
    lines.append(f"🚨 *Active Alerts:* {summary.get('active_alerts', 0)}")

    if events:
        lines.append("\n*Recent Events:*")
        for ev in events[:3]:
            sev = ev.get("severity", "")
            evt = ev.get("event", "")[:60]
            lines.append(f"  • [{sev}] {evt}")
    else:
        lines.append("\n✅ No security events detected.")

    lines.append(f"\n_Collected: {summary.get('collected_at', 'now')}_")
    return "\n".join(lines)


def _format_ai_insights() -> str:
    """Fetch AI analysis from backend."""
    data = _backend_post("/api/v1/chat", {
        "message": "Give me a brief health summary of the database, server, and security status in 3 bullet points.",
        "domain": "database"
    })
    if not data:
        return "❌ *AI:* Backend unavailable — cannot generate real AI insights."

    answer = data.get("answer", "No response from AI.")
    # Truncate for Telegram (max 4096 chars)
    if len(answer) > 800:
        answer = answer[:800] + "\n...(truncated)"
    return f"🤖 *AI Infrastructure Insight (Live)*\n\n{answer}"


# -------------------------------------------------------------
# Keyboards & Navigation
# -------------------------------------------------------------

def get_dashboard_keyboard():
    """Generates the grid of action buttons for logged-in users."""
    keyboard = [
        [
            InlineKeyboardButton("🛢️ Database Health", callback_data="btn_database"),
            InlineKeyboardButton("🖥️ Server Health", callback_data="btn_server"),
        ],
        [
            InlineKeyboardButton("🛡️ Security Score", callback_data="btn_security"),
            InlineKeyboardButton("🤖 AI Insights", callback_data="btn_admin"),
        ],
        [
            InlineKeyboardButton("🔒 Log Out", callback_data="btn_logout")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_login_keyboard():
    """Generates a regular Keyboard Button. 
    Required for window.Telegram.WebApp.sendData() to work."""
    keyboard = [
        [
            KeyboardButton(
                text="🔑 Launch Login Portal", 
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# -------------------------------------------------------------
# Authentication Guard (Decorator)
# -------------------------------------------------------------

def authorized_only(func):
    """Decorator to restrict action button clicks only to verified admins."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = None
        if update.message:
            user_id = update.message.from_user.id
        elif update.callback_query:
            user_id = update.callback_query.from_user.id
            
        if not user_id or user_id not in AUTHORIZED_USERS:
            logger.warning(f"Unauthorized access attempt by user ID: {user_id}")
            return  
        return await func(update, context, *args, **kwargs)
    return wrapper

# -------------------------------------------------------------
# Handlers
# -------------------------------------------------------------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets the user and opens the bottom Keyboard login."""
    user_id = update.message.from_user.id
    
    if user_id in AUTHORIZED_USERS:
        await update.message.reply_text(
            "💻 *Redhelp Infrastructure Dashboard*\nSelect a department below to view real-time mock data:",
            reply_markup=get_dashboard_keyboard(),
            parse_mode="Markdown"
        )
        return

    welcome_text = (
        "👋 *Welcome to Redhelp System Monitor.*\n\n"
        "To view protected system statistics, you must authorize your identity.\n"
        "Tap the keyboard button below to launch the secure login interface:"
    )
    await update.message.reply_text(
        welcome_text, 
        reply_markup=get_login_keyboard(), 
        parse_mode="Markdown"
    )


async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes JSON data transmitted back from the Mini App."""
    user_id = update.message.from_user.id
    raw_data = update.message.web_app_data.data.strip()
    
    import json
    try:
        data = json.loads(raw_data)
        
        if data.get("type") == "system_alert":
            action = data.get("action")
            await update.message.reply_text(f"🚨 *System Alert Received!*\nAction executed: `{action}`", parse_mode="Markdown")
            
        elif data.get("type") == "ai_query":
            query = data.get("query")
            await update.message.reply_text(f"🤖 *AI Intelligence Module*\nI am analyzing your query:\n_{query}_", parse_mode="Markdown")
            
        elif data.get("action") == "login":
            if data.get("status") == "success":
                AUTHORIZED_USERS[user_id] = ""  # token fetched on demand
                await update.message.reply_text("✅ Logged in successfully via Mini App.")
                
    except json.JSONDecodeError:
        # Fallback if it's just a raw password (old behavior)
        if raw_data == ADMIN_PASSWORD:
            AUTHORIZED_USERS[user_id] = ""  # token fetched on demand
            logger.info(f"User {user_id} successfully logged in via Mini App.")
            await update.message.reply_text(
                "🔓 *Access Granted!*\nWelcome back, Administrator:",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="Markdown"
            )
            await update.message.reply_text(
                "Use the control center below to monitor systems:",
                reply_markup=get_dashboard_keyboard()
            )
        else:
            logger.warning(f"Failed login attempt via Mini App by user {user_id}.")
            await update.message.reply_text(
                "❌ *Incorrect Password.*\nAccess remains locked.",
                reply_markup=get_login_keyboard(),
                parse_mode="Markdown"
            )


async def restrict_unauthorized_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ignores or redirects any plain text sent by unauthorized users."""
    user_id = update.message.from_user.id
    
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text(
            "🔒 *Locked:* Unauthorized inputs are ignored.\nUse the login button at the bottom or type `/start`.",
            parse_mode="Markdown"
        )


@authorized_only
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles click events from our dashboard buttons."""
    query = update.callback_query
    await query.answer()
    
    data_key = query.data.replace("btn_", "")
    
    if data_key == "logout":
        AUTHORIZED_USERS.pop(query.from_user.id, None)
        await query.message.reply_text(
            text="🔒 *You have logged out.*\nUse `/start` to log in again.",
            reply_markup=get_login_keyboard(),
            parse_mode="Markdown"
        )
        return

    # Fetch REAL metrics from backend
    await query.edit_message_text(
        text="⏳ *Fetching live data from backend...*",
        reply_markup=None,
        parse_mode="Markdown"
    )

    if data_key == "database":
        metrics_text = _format_database_status()
    elif data_key == "server":
        metrics_text = _format_server_status()
    elif data_key == "security":
        metrics_text = _format_security_status()
    elif data_key == "admin":
        metrics_text = _format_ai_insights()
    else:
        metrics_text = "Unknown metric."

    await query.edit_message_text(
        text=f"💻 *Redhelp Infrastructure Monitor*\n\n{metrics_text}",
        reply_markup=get_dashboard_keyboard(),
        parse_mode="Markdown"
    )

# -------------------------------------------------------------
# Main Loop
# -------------------------------------------------------------

def main():
    logger.info("Initializing Redhelp Telegram Bot...")
    
    # We increase the read and connect timeouts to prevent network "TimedOut" errors
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )

    # Core commands
    app.add_handler(CommandHandler("start", start_handler))
    
    # Mini App callback handler
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    
    # Inline keyboard action handler
    app.add_handler(CallbackQueryHandler(button_callback_handler))
    
    # Block & restrict all non-command text from unauthorized users
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, restrict_unauthorized_messages))

    logger.info("Bot is polling. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
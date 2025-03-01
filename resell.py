import telebot
import os
import random
import string
from datetime import datetime, timedelta
import pytz
import psycopg2
import logging
import time

# Create connection pool
# At the top of the script, modify the connection pool setup
from psycopg2 import pool

import pymongo

# MongoDB configuration
uri = "mongodb+srv://uthayakrishna67:Uthaya$0@cluster0.mlxuz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(uri)
db = client['telegram_bot']

# Collections
resellers = db['resellers']
transactions = db['reseller_transactions']
unused_keys = db['unused_keys']
users = db['users']


# Create connection pool
def setup_database():
    try:
        # Create indexes for better query performance
        resellers.create_index("telegram_id", unique=True)
        transactions.create_index("reseller_id")
        unused_keys.create_index("key", unique=True)
        users.create_index("user_id", unique=True)
    except Exception as e:
        logging.error(f"Database setup error: {e}")

def execute_db_query(collection, operation, query={}, data=None):
    try:
        if operation == "find":
            return collection.find(query)
        elif operation == "find_one":
            return collection.find_one(query)
        elif operation == "insert":
            return collection.insert_one(data)
        elif operation == "update":
            return collection.update_one(query, {"$set": data})
        elif operation == "delete":
            return collection.delete_one(query)
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise


# Bot Configuration 
RESELLER_BOT_TOKEN = '7490965174:AAEucdgSZX5m7txo8_BO1lU8wfvBZ60aqEQ'
ADMIN_IDS = ["7418099890"]
admin_owner = "7418099890"

# Price configuration
PRICES = {
    "2h": 20,
    "1d": 200,
    "3d": 320, 
    "7d": 600,
    "30d": 1100,
    "60d": 1800
}

IST = pytz.timezone('Asia/Kolkata')
bot = telebot.TeleBot(RESELLER_BOT_TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
    user_name = message.from_user.first_name
    response = f"""
🌟𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗠𝗔𝗧𝗥𝗜𝗫 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿 𝗣𝗮𝗻𝗲𝗹🌟

👋 𝗛𝗲𝗹𝗹𝗼 {user_name}!

📝 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀:
• Use /help for all commands
• Use /prices for pricing details
• Use /balance to check balance

🔥Bot: @MatrixCheats_ddos_bot

🔗 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀:
• Channel: @MATRIX_CHEATS

💫 𝗦𝘁𝗮𝗿𝘁 𝗥𝗲𝘀𝗲𝗹𝗹𝗶𝗻𝗴:
Contact @its_MATRIX_King to become a Offical Reseller
"""
    bot.reply_to(message, response)

@bot.message_handler(commands=['help'])
def show_help(message):
    user_id = str(message.from_user.id)
    help_text = """
🎮 𝗠𝗔𝗧𝗥𝗜𝗫 𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦

💎 𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦:
• /balance - Check your wallet balance
• /generatekey - Generate new license key
• /prices - View current key prices
• /mykeys - View your unused keys
• /myusers - View your active users
• /remove - Delete key/user

📊 𝗨𝗦𝗘𝗥 𝗠𝗔𝗡𝗔𝗚𝗘𝗠𝗘𝗡𝗧:
• /myusers - Monitor active users
• /mykeys - Track available keys
• /remove <key> - Remove specific key"""

    # Add admin commands if user is admin
    if user_id in ADMIN_IDS:
        help_text += """

👑 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦:
• /addreseller - Register new reseller
• /addbalance - Add balance to reseller
• /allresellers - View all resellers
• /removecredits - Remove credits from reseller
• /removereseller - Delete reseller account
• /broadcast - Send mass message
"""

    help_text += """

📱 𝗦𝗨𝗣𝗣𝗢𝗥𝗧:
• Channel: @MATRIX_CHEATS
• Owner: @its_MATRiX_King

⚠️ 𝗡𝗢𝗧𝗘:
• Keep your reseller credentials safe
• Contact admin for any issues
• Prices are non-negotiable"""

    bot.reply_to(message, help_text)

@bot.message_handler(commands=['mykeys'])
def show_reseller_keys(message):
    try:
        user_id = str(message.from_user.id)
        
        # Check if user is a reseller
        reseller = db['resellers'].find_one({"telegram_id": user_id})
        if not reseller:
            bot.reply_to(message, "⛔️ Only resellers can use this command")
            return

        # Fetch unused keys for this reseller
        keys = db['unused_keys'].aggregate([
            {
                "$lookup": {
                    "from": "reseller_transactions",
                    "localField": "key",
                    "foreignField": "key_generated",
                    "as": "transaction"
                }
            },
            {
                "$match": {
                    "is_used": False,
                    "transaction.reseller_id": user_id
                }
            },
            {
                "$sort": {"created_at": -1}
            }
        ])

        # Check if there are no keys
        keys_list = list(keys)
        if not keys_list:
            bot.reply_to(message, "📝 You have no unused keys available")
            return

        # Prepare the response
        response = "🔑 Your Unused Keys:\n\n"
        for key in keys_list:
            created_at_ist = key['created_at'].astimezone(IST).strftime('%Y-%m-%d %H:%M:%S')
            response += f"""🔑 Key: `{key['key']}`
⏱️ Duration: {key['duration']}
📅 Generated: {created_at_ist} IST
━━━━━━━━━━━━━━━\n"""

        # Send the response to the reseller
        bot.reply_to(message, response)

    except Exception as e:
        bot.reply_to(message, f"❌ Error fetching keys: {str(e)}")


@bot.message_handler(commands=['myusers'])
def show_reseller_users(message):
    try:
        user_id = str(message.from_user.id)

        # Check if user is a reseller
        reseller = db['resellers'].find_one({"telegram_id": user_id})
        if not reseller:
            bot.reply_to(message, "⛔️ Only resellers can use this command")
            return

        # Get active users for this reseller
        users = db['users'].aggregate([
            {
                "$lookup": {
                    "from": "reseller_transactions",
                    "localField": "key",
                    "foreignField": "key_generated",
                    "as": "transaction"
                }
            },
            {
                "$match": {
                    "expiration": {"$gt": datetime.now(IST)},
                    "transaction.reseller_id": user_id
                }
            },
            {
                "$sort": {"expiration": -1}
            }
        ])

        # Convert cursor to list and check if there are no users
        users_list = list(users)
        if not users_list:
            bot.reply_to(message, "📝 You have no active users")
            return

        # Prepare the response
        response = "📊 Your Active Users:\n\n"
        for user in users_list:
            remaining_time = user['expiration'].astimezone(IST) - datetime.now(IST)
            expiration_ist = user['expiration'].astimezone(IST).strftime('%Y-%m-%d %H:%M:%S')
            response += f"""👤 User: {user.get('username', 'N/A')}
🆔 ID: {user['user_id']}
🔑 Key: {user['key']}
⏳ Remaining: {remaining_time.days}d {remaining_time.seconds // 3600}h
📅 Expires: {expiration_ist} IST
━━━━━━━━━━━━━━━\n"""

        # Send the response to the reseller
        bot.reply_to(message, response)

    except Exception as e:
        bot.reply_to(message, f"❌ Error fetching users: {str(e)}")


@bot.message_handler(commands=['remove'])
def remove_key(message):
    try:
        # Extract user ID and command arguments
        user_id = str(message.from_user.id)
        args = message.text.split()
        
        # Validate command usage
        if len(args) != 2:
            bot.reply_to(message, "📝 Usage: /remove <key>")
            return
        
        key = args[1]
        
        # Check if user is admin
        if user_id in admin_owner:
            # Admins can remove any key
            result_keys = db['unused_keys'].delete_one({"key": key})
            result_users = db['users'].delete_one({"key": key})
            
            if result_keys.deleted_count > 0 or result_users.deleted_count > 0:
                bot.reply_to(message, f"✅ Key {key} has been removed successfully by Admin.")
            else:
                bot.reply_to(message, "❌ Key not found or already removed.")
            return
        
        # Check if user is a registered reseller
        reseller = db['resellers'].find_one({"telegram_id": user_id})
        if not reseller:
            bot.reply_to(message, "⛔️ Only resellers or admins can use this command.")
            return
        
        # Verify that the key belongs to this reseller
        transaction = db['reseller_transactions'].find_one({
            "reseller_id": user_id,
            "key_generated": key
        })
        
        if not transaction:
            bot.reply_to(message, "❌ You can only remove keys generated by you.")
            return
        
        # Remove key from `unused_keys` and `users` collections
        result_keys = db['unused_keys'].delete_one({"key": key})
        result_users = db['users'].delete_one({"key": key})
        
        if result_keys.deleted_count > 0 or result_users.deleted_count > 0:
            bot.reply_to(message, f"✅ Key {key} has been removed successfully.")
        else:
            bot.reply_to(message, "❌ Key not found or already removed.")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Error removing key: {str(e)}")


## All Resellers Command
@bot.message_handler(commands=['allresellers'])
def list_all_resellers(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "⛔️ Only administrators can view all resellers.")
        return
    try:
        # Fetch all resellers sorted by creation date
        resellers = db['resellers'].find().sort("created_at", -1)
        if not resellers:
            bot.reply_to(message, "📝 No resellers found")
            return

        reseller_list = []
        for reseller in resellers:
            # Try to get current username from Telegram API
            try:
                user_info = bot.get_chat(reseller['telegram_id'])
                display_username = user_info.username or user_info.first_name
            except:
                display_username = reseller.get('username', f"ID:{reseller['telegram_id']}")

            # Convert created_at to IST and format it
            created_at_ist = reseller['created_at'].astimezone(IST).strftime('%Y-%m-%d %H:%M:%S')

            # Format reseller details
            reseller_info = f"""👤 Username: @{display_username}
🆔 Telegram ID: {reseller['telegram_id']}
💰 Balance: {reseller['balance']:,} Credits
📅 Added On: {created_at_ist} IST"""
            reseller_list.append(reseller_info)

        # Combine all reseller details into a single response
        response = "📊 All Resellers:\n" + "\n━━━━━━━━━━━━━━━\n".join(reseller_list)
        bot.reply_to(message, response)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


## All Resellers Command
@bot.message_handler(commands=['allresellers'])
def list_all_resellers(message):
    if str(message.from_user.id) not in admin_owner:
        bot.reply_to(message, "⛔️ Only administrators can view all resellers.")
        return
        
    try:
        # Fetch all resellers sorted by creation date
        resellers = db['resellers'].find().sort("created_at", -1)
        
        if not resellers:
            bot.reply_to(message, "📝 No resellers found")
            return
            
        reseller_list = []
        for reseller in resellers:
            # Try to get current username from Telegram API
            try:
                user_info = bot.get_chat(reseller['telegram_id'])
                display_username = user_info.username or user_info.first_name
            except:
                display_username = reseller.get('username', f"ID:{reseller['telegram_id']}")
                
            reseller_info = f"""
👤 Username: @{display_username}
🆔 Telegram ID: {reseller['telegram_id']}
💰 Balance: {reseller['balance']:,} Credits
📅 Added On: {reseller['created_at'].strftime('%Y-%m-%d %H:%M:%S')} IST"""
            reseller_list.append(reseller_info)
            
        response = "📊 All Resellers:\n" + "\n━━━━━━━━━━━━━━━\n".join(reseller_list)
        bot.reply_to(message, response)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.message_handler(commands=['addreseller'])
def add_reseller(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "⛔️ Only administrators can add resellers.")
        return
    
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "📝 Usage: /addreseller <telegram_id> <initial_balance>")
            return

        telegram_id = args[1]
        balance = int(args[2])
        
        resellers.insert_one({
            "telegram_id": telegram_id,
            "balance": balance,
            "added_by": str(message.from_user.id),
            "created_at": datetime.now(IST)
        })

        bot.reply_to(message, f"""
✅ Reseller Added Successfully
👤 Telegram ID: {telegram_id}
💰 Initial Balance: {balance}
""")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.message_handler(commands=['balance'])
def check_balance(message):
    try:
        # Find reseller in MongoDB
        reseller = db['resellers'].find_one({"telegram_id": str(message.from_user.id)})
        
        if not reseller:
            bot.reply_to(message, "⛔️ You are not registered as a reseller")
            return
        
        bot.reply_to(message, f""" 
💰 Your Balance Available: {reseller['balance']:,} Credits
""")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.message_handler(commands=['generatekey'])
def generate_key(message):
    try:
        user_id = str(message.from_user.id)
        reseller = resellers.find_one({"telegram_id": user_id})
        if not reseller:
            bot.reply_to(message, "⛔️ You are not registered as a reseller")
            return

        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "📝 Usage: /generatekey <duration>")
            return

        duration = args[1].lower()
        if duration not in PRICES:
            bot.reply_to(message, "❌ Invalid duration! Use 2h, 1d, 3d, 7d, 30d, or 60d (Example: /generatekey 2h)")
            return

        price = PRICES[duration]
        if reseller["balance"] < price:
            bot.reply_to(message, f"❌ Insufficient balance! Required: {price:,} Credits")
            return

        # Generate unique key
        key = f"MATRIX-{duration.upper()}-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # Update reseller balance
        resellers.update_one({"telegram_id": user_id}, {"$inc": {"balance": -price}})

        # Record transaction
        transactions.insert_one({
            "reseller_id": user_id,
            "type": "KEY_GENERATION",
            "amount": price,
            "key_generated": key,
            "duration": duration,
            "timestamp": datetime.now(IST)
        })

        # Create unused key
        unused_keys.insert_one({
            "key": key,
            "duration": duration,
            "created_at": datetime.now(IST),
            "is_used": False
        })

        # Notify reseller
        bot.reply_to(message, f"""✅ Key Generated Successfully!
🔑 Key: `{key}`
⏱️ Duration: {duration.upper()}
💰 Credits Used: {price:,}
💳 Remaining: {reseller["balance"] - price:,}""")

        # Notify admin(s)
        admin_message = f"""📢 New Key Generated
👤 Reseller: @{message.from_user.username or 'N/A'} (ID: {user_id})
🔑 Key: `{key}`
⏱️ Duration: {duration.upper()}
💰 Credits Used: {price:,}
💳 Remaining Balance: {reseller["balance"] - price:,}
📅 Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST"""

        for admin_id in ADMIN_IDS:
            bot.send_message(admin_id, admin_message)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.message_handler(commands=['removereseller'])
def remove_reseller(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "⛔️ Only administrators can remove resellers.")
        return
        
    try:
        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "📝 Usage: /removereseller <telegram_id>")
            return
            
        telegram_id = args[1]
        
        # Get reseller info before deletion
        reseller = resellers.find_one({"telegram_id": telegram_id})
        if not reseller:
            bot.reply_to(message, "❌ Reseller not found!")
            return
            
        # Try to get current username from Telegram API
        try:
            user_info = bot.get_chat(telegram_id)
            display_username = user_info.username or user_info.first_name
        except:
            display_username = reseller.get('username', f"ID:{telegram_id}")
            
        # Delete reseller and associated transactions
        transactions.delete_many({"reseller_id": telegram_id})
        resellers.delete_one({"telegram_id": telegram_id})
        
        admin_message = f"""
✅ 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿 𝗥𝗲𝗺𝗼𝘃𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆
👤 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: @{display_username}
🆔 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗜𝗗: {telegram_id}
💰 𝗙𝗶𝗻𝗮𝗹 𝗕𝗮𝗹𝗮𝗻𝗰𝗲: {reseller['balance']:,} Credits
📅 𝗥𝗲𝗺𝗼𝘃𝗲𝗱: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST"""
        
        bot.reply_to(message, admin_message)
        
        # Notify other admins
        for admin in ADMIN_IDS:
            if admin != str(message.from_user.id):
                bot.send_message(admin, f"""
🚫 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿 𝗥𝗲𝗺𝗼𝘃𝗲𝗱 𝗔𝗹𝗲𝗿𝘁
👤 𝗥𝗲𝗺𝗼𝘃𝗲𝗱 𝗯𝘆: @{message.from_user.username}
🆔 𝗥𝗲𝗺𝗼𝘃𝗲𝗱 𝗜𝗗: {telegram_id}
👤 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: @{display_username}
📅 𝗧𝗶𝗺𝗲: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST""")
                
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['allresellers'])
def list_all_resellers(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "⛔️ Only administrators can view all resellers.")
        return

    try:
        # Fetch all resellers with their details
        resellers = execute_db_query("""
            SELECT r.telegram_id, r.username, r.balance, r.created_at 
            FROM resellers r
            ORDER BY r.created_at DESC
        """)

        if not resellers:
            bot.reply_to(message, "📝 No resellers found")
            return

        # Format resellers list
        reseller_list = []
        for telegram_id, username, balance, created_at in resellers:
            # Try to get current username from Telegram API
            try:
                user_info = bot.get_chat(telegram_id)
                display_username = user_info.username or user_info.first_name
            except:
                # Fallback to stored username if Telegram API fails
                display_username = username if username else f"ID:{telegram_id}"

            reseller_info = f"""
👤 Username: @{display_username}
🆔 Telegram ID: {telegram_id}
💰 Balance: {balance:,} Credits
📅 Added On: {created_at.astimezone(IST).strftime('%Y-%m-%d %H:%M:%S')} IST
"""
            reseller_list.append(reseller_info)

        # Join all reseller info with a separator
        response = "📊 All Resellers:\n" + "\n━━━━━━━━━━━━━━━\n".join(reseller_list)
        bot.reply_to(message, response)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.message_handler(commands=['addbalance'])
def add_balance_to_reseller(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "⛔️ Only administrators can add balance.")
        return
    
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "📝 Usage: /addbalance <telegram_id> <credits>")
            return
            
        telegram_id = args[1]
        credits = int(args[2])
        
        # Check if reseller exists
        reseller = resellers.find_one({"telegram_id": telegram_id})
        if not reseller:
            bot.reply_to(message, "❌ Reseller not found!")
            return
            
        # Add balance to reseller
        resellers.update_one(
            {"telegram_id": telegram_id},
            {"$inc": {"balance": credits}}
        )
        
        # Get updated reseller info
        updated_reseller = resellers.find_one({"telegram_id": telegram_id})
        
        # Try to get username from Telegram
        try:
            user_info = bot.get_chat(telegram_id)
            display_username = user_info.username or user_info.first_name
        except:
            display_username = updated_reseller.get('username', 'N/A')
            
        bot.reply_to(message, f"""
✅ Balance Added Successfully
👤 Username: @{display_username}
🆔 Telegram ID: {telegram_id}
💰 Added Credits: {credits:,}
💳 New Balance: {updated_reseller['balance']:,}
""")

    except ValueError:
        bot.reply_to(message, "❌ Invalid credit amount. Please enter a valid number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.message_handler(commands=['removecredits'])
def remove_credits_from_reseller(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "⛔️ Only administrators can remove credits.")
        return
        
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "📝 Usage: /removecredits <telegram_id> <credits>")
            return
            
        telegram_id = args[1]
        credits = int(args[2])
        
        # Check if reseller exists
        reseller = resellers.find_one({"telegram_id": telegram_id})
        if not reseller:
            bot.reply_to(message, "❌ Reseller not found!")
            return
            
        # Check if sufficient balance
        if reseller['balance'] < credits:
            bot.reply_to(message, f"""
❌ Insufficient Credits
👤 Username: @{reseller.get('username', 'N/A')}
🆔 Telegram ID: {telegram_id}
💰 Current Balance: {reseller['balance']:,}
❌ Attempted to Remove: {credits:,}
""")
            return
            
        # Remove credits from reseller
        resellers.update_one(
            {"telegram_id": telegram_id},
            {"$inc": {"balance": -credits}}
        )
        
        # Get updated balance
        updated_reseller = resellers.find_one({"telegram_id": telegram_id})
        
        # Try to get username from Telegram
        try:
            user_info = bot.get_chat(telegram_id)
            display_username = user_info.username or user_info.first_name
        except:
            display_username = updated_reseller.get('username', 'N/A')
            
        bot.reply_to(message, f"""
✅ Credits Removed Successfully
👤 Username: @{display_username}
🆔 Telegram ID: {telegram_id}
❌ Removed Credits: {credits:,}
💳 New Balance: {updated_reseller['balance']:,}
""")

    except ValueError:
        bot.reply_to(message, "❌ Invalid credit amount. Please enter a valid number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if str(message.from_user.id) not in ADMIN_IDS:
        bot.reply_to(message, "⛔️ Only administrators can broadcast messages.")
        return

    try:
        args = message.text.split(maxsplit=1)
        if len(args) != 2:
            bot.reply_to(message, "📝 Usage: /broadcast <message>")
            return

        broadcast_text = args[1]
        
        # Get all resellers from MongoDB collection
        all_resellers = resellers.find({})
        
        if not all_resellers:
            bot.reply_to(message, "📝 No resellers found to broadcast to.")
            return

        success_count = 0
        failed_resellers = []

        for reseller in all_resellers:
            try:
                formatted_message = f""" 
📢 𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 
{broadcast_text}
━━━━━━━━━━━━━━━
𝗦𝗲𝗻𝘁 𝗯𝘆: @{message.from_user.username}
𝗧𝗶𝗺𝗲: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST"""

                bot.send_message(reseller['telegram_id'], formatted_message)
                success_count += 1
                time.sleep(0.1)  # Prevent flooding
            except Exception as e:
                failed_resellers.append(f"@{reseller.get('username', 'Unknown')}")

        summary = f"""
✅ 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗦𝘂𝗺𝗺𝗮𝗿𝘆:
📨 𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿𝘀: {success_count + len(failed_resellers)}
✅ 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹: {success_count}
❌ 𝗙𝗮𝗶𝗹𝗲𝗱: {len(failed_resellers)}"""

        if failed_resellers:
            summary += f"\n❌ 𝗙𝗮𝗶𝗹𝗲𝗱 𝗿𝗲𝘀𝗲𝗹𝗹𝗲𝗿𝘀:\n" + "\n".join(failed_resellers)

        bot.reply_to(message, summary)

    except Exception as e:
        bot.reply_to(message, f"❌ Error during broadcast: {str(e)}")


@bot.message_handler(commands=['prices'])
def show_prices(message):
    price_text = """
💎 𝗣𝗔𝗡𝗘𝗟 𝗣𝗥𝗜𝗖𝗘𝗦:
• ₹2,000 ➜ 10000 Credits
• ₹3,000 ➜ 16,000 Credits
• ₹5,000 ➜ 27,000 Credits
• ₹10,000 ➜ 60,000 Credits


💰 𝗞𝗘𝗬 𝗣𝗥𝗜𝗖𝗘𝗦:
• 2 Hours: 20 Credits
• 1 Day: 200 Credits
• 3 Days: 320 Credits
• 7 Days: 600 Credits
• 30 Days: 1,100 Credits
• 60 Days: 1,800 Credits

📌 𝗠𝗜𝗡𝗜𝗠𝗨𝗠 𝗕𝗨𝗬: 2,000₹ (10,000 Credits)"""
    bot.reply_to(message, price_text)

def run_bot():
    setup_database()
    while True:
        try:
            print("Bot is running...")
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Bot error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    run_bot()
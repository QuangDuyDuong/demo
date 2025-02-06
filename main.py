import os
import requests
import logging
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext
from telegram.ext.filters import TEXT
from dotenv import load_dotenv

# Biến global lưu token và thời hạn (time)
CACHED_TOKEN = None
TOKEN_EXPIRY = 0

def get_exness_token():
    global CACHED_TOKEN, TOKEN_EXPIRY
    if time.time() < TOKEN_EXPIRY and CACHED_TOKEN:
        return CACHED_TOKEN  # Token vẫn còn hiệu lực

    try:
        response = requests.post(AUTH_API_URL, json={"username": EXNESS_USERNAME, "password": EXNESS_PASSWORD})
        response.raise_for_status()
        data = response.json()
        CACHED_TOKEN = data.get("token")
        TOKEN_EXPIRY = time.time() + data.get("expires_in", 3600)  # Mặc định 1 giờ
        return CACHED_TOKEN
    except Exception as e:
        logging.error(f"Lỗi refresh token: {e}")
        return None

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),  
        logging.StreamHandler()         
    ]
)

# Thiết lập dotenv
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_TOKEN = os.getenv("EXNESS_API_TOKEN")
EXNESS_USERNAME = os.getenv("EXNESS_USERNAME")
EXNESS_PASSWORD = os.getenv("EXNESS_PASSWORD")
AUTH_API_URL = "https://my.exnessaffiliates.com/api/v2/auth/"

# Lấy API
def get_exness_token():
    """Lấy JWT token từ Exness API bằng tài khoản/password."""
    try:
        logging.info(f"Gửi request đến {AUTH_API_URL} với username: {EXNESS_USERNAME}")
        
        response = requests.post(
            AUTH_API_URL,
            data={
                "login": EXNESS_USERNAME,
                "password": EXNESS_PASSWORD
            },
            timeout=20
        )
        
        logging.info(f"Response status code: {response.status_code}")
        logging.info(f"Response content: {response.text}")
        
        response.raise_for_status()
        token = response.json().get("token")  
        return token
    except Exception as e:
        logging.error(f"Lỗi khi lấy token: {e}")
        return None

if not EXNESS_USERNAME or not EXNESS_PASSWORD or not TELEGRAM_TOKEN:
    logging.error("TELEGRAM_TOKEN hoặc EXNESS_API_TOKEN chưa được cấu hình trong file .env")
    raise ValueError("TELEGRAM_TOKEN hoặc EXNESS_API_TOKEN chưa được cấu hình trong file .env")

# Hàm kiểm tra ID MT4/MT5
async def check_id_mt4(update: Update, context: CallbackContext) -> None:
    user_input = ' '.join(context.args)
    if user_input.isdigit():
        await update.message.reply_text("⏳ Vui lòng đợi trong giây lát...")
        
        # Lấy token tự động
        api_token = get_exness_token()
        if not api_token:
            await update.message.reply_text("⚠️ Lỗi xác thực với Exness. Vui lòng thử lại sau.")
            return

        try:
            # Cấu hình API endpoint và headers
            client_account_id = user_input
            url = f"https://my.exnessaffiliates.com/api/reports/clients/?client_account={client_account_id}"
            
            headers = {
                "Accept": "application/json",
                "Authorization": f"JWT {api_token}"
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()  # Kiểm tra nếu có lỗi HTTP

            data = response.json()
            clients = data.get("data", [])
            if clients:
                for client in clients:
                    client_id = client.get("client_account", "Không xác định")
                    account_type = client.get("client_account_type", "Không xác định")
                    
                    # Kiểm tra loại tài khoản
                    if account_type.lower() in ["standard", "standard plus"]:
                        user = update.message.from_user
                        user_info = f"User ID: {user.id}, Username: {user.username}, First Name: {user.first_name}, Last Name: {user.last_name}, MT4/MT5 ID: {client_id}\n"
                        with open("registered_users.txt", "a", encoding="utf-8") as file:
                            file.write(user_info)
                        
                        await update.message.reply_text(
                            f"✅ *Chúc mừng bạn đã đăng ký thành công.*\n"
                            f"❤️ Tham gia nhóm *Private*:\n"
                            f"[Private | FXNOVA](https://t.me/+Kk8xVUgRAKtkODll)",
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(
                            f"❌ Tài khoản chưa hợp lệ. Vui lòng chuyển sang tài khoản Standard hoặc Standard Plus và đăng ký lại.\n\n"
                            f"Hướng dẫn tạo tài khoản Standard: /create_new"
                        )
                
            else:
                await update.message.reply_text("❌ Không tìm thấy thông tin tài khoản.")
        except requests.exceptions.HTTPError as e:
            logging.error(f"Lỗi API: {e}")
            await update.message.reply_text("⚠️ Hiện tại hệ thống đang bận. Vui lòng thử lại sau.")
        except Exception as e:
            logging.error(f"Lỗi không xác định: {e}")
            await update.message.reply_text("⚠️ Đã xảy ra lỗi. Vui lòng thử lại sau.")
    else:
        await update.message.reply_text(
            f"Vui lòng đăng ký theo cú pháp: /reg <ID MT4/MT5> \n\n"
            f"Ví dụ: ID MT4/MT5 của bạn là 123456789. Hãy gửi cho bot theo cú pháp: /reg 123456789"
        )        
# Hàm hướng dẫn tạo tài khoản
async def guide_create_account(update: Update, context: CallbackContext) -> None:
    guide_message = (
        "✨ *Hướng dẫn tham gia nhóm FXNOVA Private:*\n\n"
        "*1. Đăng ký tài khoản:*\n\n"
        "🌈*https://one.exnesstrack.org/a/bdsgwpgt24*\n"
        "Mã đối tác: `bdsgwpgt24`\n\n"
        "❕*Lưu ý:* Phải sử dụng tài khoản *Standard* hoặc *Standard Plus* (miễn mọi loại phí giao dịch).\n\n"
        "Nếu muốn chuyển đối tác vui lòng chọn: */change_partner*\n\n"
        "*2. Đăng ký theo cú pháp: /reg <ID MT4/MT5>*"
    )
    await update.message.reply_text(guide_message, parse_mode='Markdown')
    
# Hàm hướng dẫn thay đổi đối tác
async def change_partner(update: Update, context: CallbackContext) -> None:
    change_partner_message = (
        "✨ *Hướng dẫn thay đổi đối tác trên sàn Exness:*\n\n"
        "🌈 Link partner: *https://one.exnesstrack.org/a/bdsgwpgt24*\n\n"
        "*Bước 1:* Mở cuộc trò chuyện với Support trên Website hoặc Mobile App.\n\n"
        "*Bước 2:* Chat với Exness BOT nội dung: Thay đổi đối tác.\n\n"
        "*Bước 3:* Exness BOT sẽ gửi cho bạn 1 đường dẫn. Nhấp vào và nhập thông tin như sau:\n\n"
        "- Select reason for partner change: *Trading signals*\n\n"
        "- New partner's link or wallet account number: *( Vui lòng copy đường link trên và dán vào )*\n\n"
        "- Where did you find your new partner: *FXNOVA*\n\n"
        "- Leave a comment: *Thank you Exness.*\n\n"
        "⏳ *Chờ đổi đối tác được chấp thuận (trong vòng 72h làm việc).*\n\n"
        "*Bước 4:* Sau khi đã được chấp thuận, vui lòng tạo mới ID MT4/MT5 Standard/Standard Plus.\n\n"
        "*Bước 5:* Đăng ký theo cú pháp: /reg <ID MT4/MT5>"
    )
    await update.message.reply_text(change_partner_message, parse_mode='Markdown')

# Hàm xử lý lệnh /start
async def start(update: Update, context: CallbackContext) -> None:
    await guide_create_account(update, context)

# Hàm xử lý lệnh không hợp lệ
async def unknown(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Xin lỗi, tôi không hiểu lệnh này. Hãy nhập /help để xem danh sách lệnh.")
    
# Hàm hiển thị danh sách lệnh
async def help_command(update: Update, context: CallbackContext) -> None:
    help_message = (
        "🌟 *Danh sách các lệnh có sẵn* 🌟\n\n"
        "*/start* - Hướng dẫn tạo tài khoản và tham gia nhóm Private\n"
        "*/reg* <ID MT4/MT5> - Kiểm tra và xác nhận tài khoản của bạn\n"
        "*/create_new* - Hướng dẫn tạo tài khoản Standard/Standard Plus\n"
        "*/change_partner* - Hướng dẫn thay đổi đối tác\n"
        "*/help* - Xem danh sách lệnh"
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')

# Khởi tạo bot
def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Cài đặt các lệnh
    application.add_handler(CommandHandler("start", start))  
    application.add_handler(CommandHandler("reg", check_id_mt4))  
    application.add_handler(CommandHandler("create_new", guide_create_account))  
    application.add_handler(CommandHandler("change_partner", change_partner))
    application.add_handler(CommandHandler("help", help_command))  
    application.add_handler(MessageHandler(TEXT, unknown))  

    # Start bot
    application.run_polling()

if __name__ == '__main__':
    main()
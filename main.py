import discord
import os
import requests
from flask import Flask, redirect, request

app = Flask(__name__)

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
GUILD_ID = int(os.getenv("GUILD_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))  # 追加
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(intents=intents)

class AuthButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        auth_url = (
            f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}"
            f"&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20guilds.join"
        )
        self.add_item(discord.ui.Button(label="認証する", url=auth_url))

@bot.command()
async def auth(ctx):
    """認証用のボタンを送信"""
    await ctx.respond("以下のボタンを押して認証してください。", view=AuthButton())

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "認証エラー", 400

    # トークン取得
    token_url = "https://discord.com/api/oauth2/token"
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=data, headers=headers)
    token = response.json().get("access_token")

    if not token:
        return "トークン取得エラー", 400

    # ユーザー情報取得
    user_response = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"},
    )
    user_data = user_response.json()
    user_id = user_data.get("id")
    username = user_data.get("username") + "#" + user_data.get("discriminator")

    # ギルドに追加 & ロール付与
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    member_url = f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}"
    member_data = {"access_token": token}
    
    requests.put(member_url, json=member_data, headers=headers)  # ギルド参加

    role_url = f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}"
    requests.put(role_url, headers=headers)  # ロール付与

    # 認証ログを送信
    send_auth_log(username, user_id)

    return "認証成功！サーバーに追加されました。"

def send_auth_log(username, user_id):
    """認証ログを特定のチャンネルに送信"""
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        bot.loop.create_task(channel.send(f"✅ {username} (ID: {user_id}) が認証しました。"))

bot.run(BOT_TOKEN)

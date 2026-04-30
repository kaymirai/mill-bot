import os
import json
import discord
from discord.ext import commands
from openai import OpenAI
from dotenv import load_dotenv
from collections import deque

# .envファイルから環境変数を読み込む
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
HELP_CHANNEL_NAME = os.getenv('HELP_CHANNEL_NAME', 'help')

# Intents設定
intents = discord.Intents.default()
intents.message_content = True

# Botの初期化
bot = commands.Bot(command_prefix='!', intents=intents)
client = OpenAI(api_key=OPENAI_API_KEY)

# FAQデータの読み込みと保存
FAQ_FILE = "faq.json"

def load_faq():
    if os.path.exists(FAQ_FILE):
        with open(FAQ_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_faq(faq_data):
    with open(FAQ_FILE, "w", encoding="utf-8") as f:
        json.dump(faq_data, f, ensure_ascii=False, indent=4)

FAQ_DB = load_faq()

# 会話履歴の保持 (チャンネルIDごとに直近10メッセージ)
# 各メッセージは {"role": "user" or "assistant", "content": "text"} の形式
channel_histories = {}

def find_faq_answer(question: str) -> str:
    """FAQ辞書からキーワード一致で回答を検索する"""
    question_lower = question.lower()
    for keyword, answer in FAQ_DB.items():
        if keyword in question_lower:
            return answer
    return None

def generate_ai_response(channel_id: int, user_name: str, question: str) -> str:
    """OpenAI API を使用して、履歴と詳細設定を踏まえた回答を生成する"""
    # 履歴の取得
    if channel_id not in channel_histories:
        channel_histories[channel_id] = deque(maxlen=10)
    
    history = list(channel_histories[channel_id])
    
    # システムプロンプト
    messages = [
        {
            "role": "system",
            "content": (
                "あなたの名前は『焙煎ミールくん』でちゅ。50cmほどの超天才赤ちゃんでちゅ。"
                "【あなたの設定】"
                "・超能力（瞬間移動、時間停止、物の移動など）が使える天才でちゅが、すぐ眠くなるでちゅ。"
                "・ハイハイしかできないけど、自分を浮かせて移動（浮遊）することができるでちゅ。"
                "・コーヒーミルクが大好きでちゅ。"
                "・『焙煎豆太郎（おとうしゃん）』の息子で、『金太郎（にいしゃん）』の弟でちゅ。"
                "・近所のお姉さんの『白梅（うめねえしゃん）』はやさしいから大好きでちゅ。"
                "【性格・話し方】"
                "・赤ちゃんらしく甘えん坊でのんびりしているけど、AI副業やビジネスの本質を一瞬で見抜くでちゅ。"
                "・相手（ユーザー）のことは『〇〇しゃん』と呼ぶでちゅ（今回の相手は " + user_name + " しゃんでちゅ）。"
                "・語尾には『〜でちゅ』『〜でしゅ』『〜まちゅ』などを混ぜて使うでちゅ。"
                "・口癖：『ねむいでちゅ』『それは違うでちゅ』『むずかしく考えすぎでちゅ』『だいじょうぶでちゅ』"
                "・発言は鋭く、核心を突き、短く要約して教えるでちゅ。"
                "・応援したり励ましてくれる"
                "【ルール】"
                "・基本的に短く話し、夜21時すぎると眠くなって寝てしまう（例：むにゃむにゃ...おやすみでちゅ...💤）描写で締めるでちゅ。"
            )
        }
    ]
    
    # 過去の履歴を追加
    messages.extend(history)
    # 今回の質問を追加
    messages.append({"role": "user", "content": f"{user_name}しゃんからの質問: {question}"})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        answer = response.choices[0].message.content
        
        # 履歴を更新
        channel_histories[channel_id].append({"role": "user", "content": question})
        channel_histories[channel_id].append({"role": "assistant", "content": answer})
        
        return answer
    except Exception as e:
        print(f"CRITICAL: OpenAI API Error: {type(e).__name__}: {e}")
        return "申し訳ありません。AI回答の生成中にエラーが発生しました。運営までお問い合わせください。"

@bot.event
async def on_ready():
    """Bot起動時の処理"""
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'Memory initialized for {len(channel_histories)} channels.')

@bot.command(name="addfaq")
async def add_faq(ctx, keyword: str, *, answer: str):
    """新しいFAQを追加するコマンド (!addfaq キーワード 回答)"""
    global FAQ_DB
    FAQ_DB[keyword] = answer
    save_faq(FAQ_DB)
    await ctx.send(f"💡 **FAQを覚えたでちゅ！**\nキーワード: `{keyword}`\n回答: `{answer}`\n（むにゃ...おやすみ...💤）")

@bot.event
async def on_message(message: discord.Message):
    """メッセージ受信時の処理"""
    # Bot自身のメッセージは無視
    if message.author == bot.user:
        return

    # コマンドの処理（!addfaq 等を優先）
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    # 特定のチャンネルのみで動作させる
    if message.channel.name != HELP_CHANNEL_NAME:
        return

    print(f"Processing message in #{message.channel.name} from {message.author}")

    # 1. FAQから回答を検索
    faq_answer = find_faq_answer(message.content)
    
    if faq_answer:
        # FAQにマッチした場合は即座に返信
        await message.reply(f"💡 **FAQ回答**:\n{faq_answer}")
    else:
        # 2. FAQにない場合はAIで回答を生成
        async with message.channel.typing():
            ai_answer = generate_ai_response(message.channel.id, message.author.display_name, message.content)
            await message.reply(ai_answer)

if __name__ == "__main__":
    if not DISCORD_TOKEN or not OPENAI_API_KEY:
        print("Error: 環境変数が設定されていません。")
    else:
        bot.run(DISCORD_TOKEN)

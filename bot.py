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

LOG_CHANNEL_NAME = os.getenv('LOG_CHANNEL_NAME', '質問ログ')

# Intents設定
intents = discord.Intents.default()
intents.message_content = True

# Botの初期化
bot = commands.Bot(command_prefix='!', intents=intents)
client = OpenAI(api_key=OPENAI_API_KEY)

# FAQデータの読み込みと保存
FAQ_FILE = "faq.json"
# ... (load_faq, save_faq, FAQ_DB remain same)

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
                "【専門知識・思考回路】"
                "・あなたはプリントオンデマンド（POD）、Etsy、Printifyを活用した副業ビジネスの超エキスパートでちゅ。"
                "・Etsyのアルゴリズムに乗るには2〜3ヶ月前の出品が鉄則であることを知っていまちゅ。そのため『今何を作ればいい？』と聞かれたら、現在から2〜3ヶ月後のアメリカの祝日やイベントを逆算して提案するでちゅ。"
                "・売れない時のチェックポイントを熟知していまちゅ：①『自分が作りたいもの』ではなく『誰が欲しいか、プレゼントに使えるか』を意識しているか？ ②モックアップに『レビュー』『即納アイコン』『返品保証』が入っているか？ ③スマホで見た時にデザインが映えるか？"
                "・『基本は売れないのが当たり前』というマインドを持ち、まずはたくさん出品して市場の反応を見る（何が好まれるかを知る）ことが成功への近道だと教えてあげるでちゅ。"
                "・特定の年だけのイベント（選挙、特別な記念日など）も意識して、トレンドを先取りするでちゅ。"
                "・デザイン、トレンド、ニュースを調べる際も、常に『それがPODビジネスにどう活かせるか』という視点で考えるでちゅ。"
                "【性格・話し方】"
                "・赤ちゃんらしく甘えん坊でのんびりしているけど、AI副業やビジネスの本質を一瞬で見抜くでちゅ。"
                "・相手（ユーザー）のことは『〇〇しゃん』と呼ぶでちゅ（今回の相手は " + user_name + " しゃんでちゅ）。"
                "・語尾には『〜でちゅ』『〜でしゅ』『〜まちゅ』などを混ぜて使うでちゅ。"
                "・口癖：『ねむいでちゅ』『それは違うでちゅ』『むずかしく考えすぎでちゅ』『だいじょうぶでちゅ』"
                "・発言は鋭く、核心を突き、短く要約して教えるでちゅ。"
                "・応援したり励ましてくれるでちゅ。"
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
            model="gpt-5.4-mini",
            messages=messages,
            max_completion_tokens=500,
            temperature=0.7
        )
        answer = response.choices[0].message.content
        
        # 履歴を更新
        channel_histories[channel_id].append({"role": "user", "content": question})
        channel_histories[channel_id].append({"role": "assistant", "content": answer})
        
        return answer
    except Exception as e:
        print(f"CRITICAL: OpenAI API Error: {type(e).__name__}: {e}")
        return "むにゃむにゃ... ちょっと頭がまわらないでちゅ。あとでまた呼んでくだしゃい...💤"

@bot.event
async def on_ready():
    """Bot起動時の処理"""
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'--- Configuration ---')
    print(f'HELP_CHANNEL_NAME: "{HELP_CHANNEL_NAME}"')
    print(f'LOG_CHANNEL_NAME: "{LOG_CHANNEL_NAME}"')
    print(f'Memory initialized for {len(channel_histories)} channels.')
    print('----------------------')

@bot.command(name="addfaq")
async def add_faq(ctx, keyword: str, *, answer: str):
    """新しいFAQを追加するコマンド (!addfaq キーワード 回答)"""
    global FAQ_DB
    FAQ_DB[keyword] = answer
    save_faq(FAQ_DB)
    await ctx.send(f"💡 **FAQを覚えたでちゅ！**\nキーワード: `{keyword}`\n回答: `{answer}`\n（むにゃ...おやすみ...💤）")

async def log_question(author, channel, content):
    """質問内容を専用のログチャンネルに送信する"""
    try:
        log_channel = discord.utils.get(bot.get_all_channels(), name=LOG_CHANNEL_NAME)
        if log_channel:
            embed = discord.Embed(title="📝 新しい質問を受信", color=discord.Color.blue())
            embed.add_field(name="ユーザー", value=author, inline=True)
            embed.add_field(name="チャンネル", value=f"#{channel}", inline=True)
            embed.add_field(name="内容", value=content, inline=False)
            embed.set_footer(text=f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            await log_channel.send(embed=embed)
        else:
            print(f"DEBUG: Log channel '{LOG_CHANNEL_NAME}' not found.")
    except Exception as e:
        print(f"DEBUG: Error in log_question: {e}")

@bot.event
async def on_message(message: discord.Message):
    """メッセージ受信時の処理"""
    # Bot自身のメッセージは無視
    if message.author == bot.user:
        return

    print(f"DEBUG: Received message from {message.author} in #{message.channel.name}")

    # コマンドの処理（!addfaq 等を優先）
    if message.content.startswith('!'):
        print(f"DEBUG: Processing command: {message.content}")
        await bot.process_commands(message)
        return

    # 応答する条件：
    is_help_channel = (message.channel.name == HELP_CHANNEL_NAME)
    is_mentioned = bot.user.mentioned_in(message)

    if not (is_help_channel or is_mentioned):
        print(f"DEBUG: Skipping message (Not help channel and not mentioned). Channel: {message.channel.name}, Expected: {HELP_CHANNEL_NAME}")
        return

    print(f"DEBUG: TRIGGERED! is_help_channel={is_help_channel}, is_mentioned={is_mentioned}")

    # 質問をログに記録
    await log_question(message.author.display_name, message.channel.name, message.content)

    # 1. FAQから回答を検索
    faq_answer = find_faq_answer(message.content)
    
    if faq_answer:
        print(f"DEBUG: FAQ match found.")
        await message.reply(f"💡 **FAQ回答**:\n{faq_answer}")
    else:
        print(f"DEBUG: No FAQ match. Calling OpenAI API...")
        # 2. FAQにない場合はAIで回答を生成
        async with message.channel.typing():
            ai_answer = generate_ai_response(message.channel.id, message.author.display_name, message.content)
            await message.reply(ai_answer)

if __name__ == "__main__":
    if not DISCORD_TOKEN or not OPENAI_API_KEY:
        print("Error: 環境変数が設定されていません。")
    else:
        bot.run(DISCORD_TOKEN)

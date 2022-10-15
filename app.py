from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, ContentType
from aiogram import Bot, Dispatcher, types, executor
import json
import time
import requests

conf = open('config.json')
data = json.load(conf)

API_KEY = data["MODEL"]
users = 0
# supported = [
#     ".8svx",
#     ".3ga",
#     ".aac",
#     ".ac3",
#     ".aif",
#     ".aiff",
#     ".alac",
#     ".amr",
#     ".ape",
#     ".au",
#     ".dss",
#     ".flac",
#     ".flv",
#     ".m4a",
#     ".m4b",
#     ".m4p",
#     ".m4r",
#     ".mp3",
#     ".mpga",
#     ".ogg",
#     ".oga",
#     ".mogg",
#     ".opus",
#     ".qcp",
#     ".tta",
#     ".voc",
#     ".wav",
#     ".wma",
#     ".wv",
#     ".webm",
#     ".MTS",
#     ".M2TS",
#     ".TS",
#     ".mov",
#     ".mp2",
#     ".mp4",
#     ".m4v",
#     ".mxf"
# ]


def start(path):
    users += 1
    print("Okay I started")
    endpoint = "https://api.assemblyai.com/v2/transcript"
    json = {
        "audio_url": f"https://api.telegram.org/file/bot5660455796:AAHQLbAfqcuLrssEyFsdAEr2T9XNKzBGww4/{path}",
        "auto_chapters": True,
        "speaker_labels": True,
        "language_detection": True
    }
    headers = {
        "authorization": API_KEY,
        "content-type": "application/json"
    }
    response = requests.post(endpoint, json=json, headers=headers)
    id = response.json()['id']
    return id


def get_response(id):
    endpoint = f"https://api.assemblyai.com/v2/transcript/{id}"
    headers = {
        "authorization": "91ef75a473094a1da1547257782ee49d",
    }
    response = requests.get(endpoint, headers=headers)
    paragraphs = requests.get(f'{endpoint}/paragraphs', headers=headers)
    return [response, paragraphs]


def polling(id):
    response = get_response(id)
    print("I tried again")
    if response[0].json()['status'] == 'completed':
        print("LETSGOOOOOOO")
        res = {}
        res['transcript'] = response[0].json()['text']
        res['chapters'] = response[0].json()['chapters']
        res['paras'] = response[1].json()['paragraphs']
        return res
    else:
        return {}


API_TOKEN = data["BOT"]
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
kb_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Загрузить аудио"),
            KeyboardButton(text="Загрузить видео"),
        ],
        [
            KeyboardButton(text="Voice message"),
            KeyboardButton(text="Video message"),
        ],
        [
            KeyboardButton(text="Youtube url"),
        ],
    ]
)


@dp.message_handler(text='/help')
async def bot_start(message: Message):
    await bot.send_message(chat_id=message.chat.id, text="Хай! Этот бот поможет получить текст аудио/видео, разбивая его по параграфам, таймстампам и разным спикерам (если их несколько)\n\n Важно понимать, что бот работает на базе ИИ, поэтому возможны неточности. На данный момент есть поддержка только данных языков: English, Spanish, French, German, Italian, Portugese, Dutch, Hindi, Japanese. Русского и казахского нет :(\n\n Для того чтобы получить транскрипт, ты можешь записать аудио/видео сообщение, прикрепить файл, или ссылку на видео (поддерживаются не все сайты, тк не со всех сайтов можно автоматически скачивать видео. Поэтому, если получить транскрипт по ссылке не получается - попробуйте скачать видос в самом худшем качестве и закинуть сюда)\n\n Чтобы прикрепить ссылку, используйте команду /link 'ваша ссылка'")


@dp.message_handler(content_types=[ContentType.VOICE, ContentType.AUDIO, ContentType.DOCUMENT, ContentType.VIDEO, ContentType.VIDEO_NOTE])
async def handle_media(message: Message):
    bot.send_message(chat_id=1257923806,
                     text=f'Еще один написал. Теперь у тебя {users} юзеров')
    content = message.content_type
    await bot.send_message(chat_id=message.chat.id, text=f'You sent {content}')
    if (content == "document"):
        if not (message[content]["mime_type"][:5] == 'audio' or message[content]["mime_type"][:5] == 'video'):
            await bot.send_message(chat_id=message.chat.id, text="Сорян ты кажется приложил неверный файл, или такой формат не поддерживается")
        else:
            file = await message.document.get_file()
    if content == 'voice':
        file = await message.voice.get_file()
    if content == 'audio':
        file = await message.audio.get_file()
    if content == 'video':
        file = await message.video.get_file()
    if content == 'video_note':
        file = await message.video_note.get_file()
    print("okay let's go")
    filepath = file.file_path
    id = start(filepath)
    await bot.send_message(chat_id=message.chat.id, text='Started uploading to the server')
    results = polling(id)
    while len(results) == 0:
        print(":( sleep")
        await bot.send_message(chat_id=message.chat.id, text=f'Waiting for the audio to be transcribed...')
        time.sleep(5)
        results = polling(id)
    msg = 'Содержание:\n\n'
    i = 0
    for item in results['chapters']:
        sStart = item['start'] / 1000
        mStart = 0
        if sStart > 60:
            mStart = sStart // 60
            sStart -= mStart * 60
        sEnd = item['end'] / 1000
        mEnd = 0
        if sEnd > 60:
            mEnd = sEnd // 60
            sEnd -= mEnd * 60
        msg += f"{mStart}:{sStart} --- {mEnd}:{sEnd}\nHeadline: \"{item['headline']}\"\n\nGist: \"{item['gist']}\"\n\nSummary: \"{item['summary']}\"\n\n"
        i += 1
        if i % 3 == 0:
            await bot.send_message(chat_id=message.chat.id, text=msg)
            msg = ''
    if len(msg) > 0:
        await bot.send_message(chat_id=message.chat.id, text=msg)
    msg = '\nПараграфы:\n\n'
    i = 0
    for item in results['paras']:
        sStart = item['start'] / 1000
        mStart = 0
        if sStart > 60:
            mStart = sStart // 60
            sStart -= mStart * 60
        sEnd = item['end'] / 1000
        mEnd = 0
        if sEnd > 60:
            mEnd = sEnd // 60
            sEnd -= mEnd * 60
        msg += f"{mStart}:{sStart} --- {mEnd}:{sEnd}\n: \"{item['text']}\"\n\n"
        i += 1
        if i % 3 == 0:
            await bot.send_message(chat_id=message.chat.id, text=msg)
            msg = ''
    if len(msg) > 0:
        await bot.send_message(chat_id=message.chat.id, text=msg)
    print("Done")


@dp.message_handler(content_types=ContentType.TEXT)
async def get_message(message: Message):
    await bot.send_message(chat_id=message.chat.id, text=f"Айо восап напиши /help")
    # await bot.send_message(chat_id=message.chat.id, text="Hi!\nI'm Transcriber-Summarizer-Timestamper-someCoolStuff-doing Bot!\nMade by Arys.\n\n Чтобы увидеть инструкции, введи команду /help")


# @dp.message_handler(content_types=ContentType.VOICE)
# async def voice_msg(message: Message):
#     print("okay let's go")
#     file = await message.voice.get_file()
#     filepath = file.file_path
#     id = start(filepath)
#     await bot.send_message(chat_id=message.chat.id, text='Started uploading to the server')
#     results = polling(id)
#     while len(results) == 0:
#         print(":( sleep")
#         await bot.send_message(chat_id=message.chat.id, text=f'Waiting for the audio to be transcribed...')
#         time.sleep(5)
#         results = polling(id)
#     await bot.send_message(chat_id=message.chat.id, text=f'{results["transcript"]}')


if __name__ == "__main__":
    print("Bot is ready")
    executor.start_polling(dp)

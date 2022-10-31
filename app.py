from calendar import c
from email import message
from urllib import response
import aiogram
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ContentType
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import logging
import json
import time
import requests

conf = open('config.json')
data = json.load(conf)

API_KEY = data["MODEL"]
API_TOKEN = data["BOT"]

BTN_Youtube = InlineKeyboardButton('YouTube', callback_data='youtube')
BTN_Ted = InlineKeyboardButton('Ted', callback_data='ted')
Standard = InlineKeyboardMarkup().add(BTN_Youtube, BTN_Ted)


def start(path):
    print("Okay I started")
    endpoint = "https://api.assemblyai.com/v2/transcript"
    json = {
        "audio_url": f"https://api.telegram.org/file/bot{API_TOKEN}/{path}",
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
        "authorization": API_KEY,
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


def generate_message(results):
    tempRes = {
        'chapters': [],
        'paras': [],
    }
    msg = '<b>Содержание:</b>\n\n'
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
            tempRes['chapters'].append(msg)
            msg = ''
    if len(msg) > 0:
        tempRes['chapters'].append(msg)
        msg = ''
    msg = '\n<b>Параграфы:</b>\n\n'
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
            tempRes['paras'].append(msg)
            msg = ''
    if len(msg) > 0:
        tempRes['paras'].append(msg)
        msg = ''
    return tempRes


def checklink(url):
    response = requests.get(url)
    if response.status_code == 200:
        return "Good"
    return 'BadLink'


def download_yt():
    pass


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

logging.basicConfig(level=logging.INFO)


class UserForm(StatesGroup):
    name = State()  # Will be represented in storage as 'Form:name'
    url = State()


@dp.message_handler(commands=['help', 'start'])
async def bot_start(message: Message):
    await bot.send_message(chat_id=message.chat.id, text="Хай! Этот бот поможет получить текст аудио/видео, разбивая его по параграфам, таймстампам и разным спикерам (если их несколько)\n\n Важно понимать, что бот работает на базе ИИ, поэтому возможны неточности. На данный момент есть поддержка только данных языков: English, Spanish, French, German, Italian, Portugese, Dutch, Hindi, Japanese. Русского и казахского нет :(\n\n Для того чтобы получить транскрипт, ты можешь записать аудио/видео сообщение, прикрепить файл, или ссылку на видео (поддерживаются не все сайты, тк не со всех сайтов можно автоматически скачивать видео. Поэтому, если получить транскрипт по ссылке не получается - попробуйте скачать видос в самом худшем качестве и закинуть сюда)\n\n ")  # Чтобы прикрепить ссылку, используйте команду /link 'ваша ссылка'


@dp.message_handler(commands=['click'])
async def cmd_start(message: types.Message, state: FSMContext):
    async with state.proxy() as proxy:
        proxy.setdefault('counter', 0)
        proxy['counter'] += 1
    return await message.reply(f"Counter: {proxy['counter']}")


@dp.message_handler(content_types=[ContentType.VOICE, ContentType.AUDIO, ContentType.DOCUMENT, ContentType.VIDEO, ContentType.VIDEO_NOTE])
async def handle_media(message: Message):
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
    ans = generate_message(results)
    for msg in ans['chapters']:
        await bot.send_message(chat_id=message.chat.id, text=msg)
    for msg in ans['paras']:
        await bot.send_message(chat_id=message.chat.id, text=msg)
    # msg = 'Содержание:\n\n'
    # i = 0
    # for item in results['chapters']:
    #     sStart = item['start'] / 1000
    #     mStart = 0
    #     if sStart > 60:
    #         mStart = sStart // 60
    #         sStart -= mStart * 60
    #     sEnd = item['end'] / 1000
    #     mEnd = 0
    #     if sEnd > 60:
    #         mEnd = sEnd // 60
    #         sEnd -= mEnd * 60
    #     msg += f"{mStart}:{sStart} --- {mEnd}:{sEnd}\nHeadline: \"{item['headline']}\"\n\nGist: \"{item['gist']}\"\n\nSummary: \"{item['summary']}\"\n\n"
    #     i += 1
    #     if i % 3 == 0:
    #         await bot.send_message(chat_id=message.chat.id, text=msg)
    #         msg = ''
    # if len(msg) > 0:
    #     await bot.send_message(chat_id=message.chat.id, text=msg)
    # msg = '\nПараграфы:\n\n'
    # i = 0
    # for item in results['paras']:
    #     sStart = item['start'] / 1000
    #     mStart = 0
    #     if sStart > 60:
    #         mStart = sStart // 60
    #         sStart -= mStart * 60
    #     sEnd = item['end'] / 1000
    #     mEnd = 0
    #     if sEnd > 60:
    #         mEnd = sEnd // 60
    #         sEnd -= mEnd * 60
    #     msg += f"{mStart}:{sStart} --- {mEnd}:{sEnd}\n: \"{item['text']}\"\n\n"
    #     i += 1
    #     if i % 3 == 0:
    #         await bot.send_message(chat_id=message.chat.id, text=msg)
    #         msg = ''
    # if len(msg) > 0:
    #     await bot.send_message(chat_id=message.chat.id, text=msg)
    print("Done")


@dp.callback_query_handler(text='youtube')
async def process_callback_weather(callback_query: types.CallbackQuery, state: FSMContext):
    # state = dp.current_state(user=callback_query.from_user.id)
    # await state.set_state(TestStates.all()[0, 'http.youtube.com tuda suda'])
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, text="Ютуб дисн гой")
    async with state.proxy() as proxy:
        await bot.send_message(chat_id=callback_query.from_user.id, text=f'{proxy["name"]} хочет видос по ссылке {proxy["url"]}')


@dp.callback_query_handler(text='ted')
async def process_callback_weather(callback_query: types.CallbackQuery, state: FSMContext):
    # state = dp.current_state(user=callback_query.from_user.id)
    # await state.set_state(TestStates.all()[1, 'http.tedx tuda suda'])
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, text="Тед ток дисн гой")
    async with state.proxy() as proxy:
        await bot.send_message(chat_id=callback_query.from_user.id, text=f'{proxy["name"]} хочет видос по ссылке {proxy["url"]}')


@dp.message_handler(commands=['state'])
async def showState(state: FSMContext):
    async with state.proxy() as proxy:
        await bot.send_message(chat_id=message.chat.id, text=f'Name: {proxy["name"]}\n url: {proxy["url"]}')


@dp.message_handler(content_types=ContentType.ANY)
async def get_message(message: Message, state: FSMContext):
    if message['entities'] and message['entities'][0]['type'] == 'url':
        await bot.send_message(chat_id=message.chat.id, text=f"You sent a link. Checking if it's valid")
        r = checklink(message.text)
        if r == 'BadLink':
            await bot.send_message(chat_id=message.chat.id, text="Ссылка не открывается :(")
        else:
            async with state.proxy() as proxy:
                proxy['name'] = message.from_user.full_name
                proxy['url'] = message.text
            await bot.send_message(chat_id=message.chat.id, text="Ссылка рабочая!")
            await bot.send_message(chat_id=message.chat.id, text="С какого сайта видос? Я еще работаю над другими сервисами. Если сайта, которые тебе нужен нет, напиши мне в личку", reply_markup=Standard)
    else:
        await bot.send_message(chat_id=message.chat.id, text='айоу восап напиши /help')
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

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ContentType, InputFile
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import logging
import time
import requests
from pytube import YouTube, exceptions
import os

# conf = open('config.json')
# data = json.load(conf)

# API_KEY = data["MODEL"]
# API_TOKEN = data["BOT"]
assert (API_KEY := os.environ.get('MODEL'))
assert (API_TOKEN := os.environ.get('BOT'))

BTN_Youtube = InlineKeyboardButton(text='YouTube', callback_data='youtube')
BTN_Ted = InlineKeyboardButton(text='Ted', callback_data='ted')
Standard = InlineKeyboardMarkup().add(BTN_Youtube, BTN_Ted)


def start(url, source):
    if source == 'tg':
        audio_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{url}"
    if source == 'yt':
        audio_url = url
    endpoint = "https://api.assemblyai.com/v2/transcript"
    json = {
        "audio_url": audio_url,
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
        msg += f"<i>{round(mStart, 2)}:{round(sStart, 2)} --- {round(mEnd, 2)}:{round(sEnd, 2)}</i>\n<b>Headline</b>: \"{item['headline']}\"\n\n<b>Gist</b>: \"{item['gist']}\"\n\n<b>Summary</b>: \"{item['summary']}\"\n\n"
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
        msg += f"<i>{round(mStart, 2)}:{round(sStart, 2)} --- {round(mEnd, 2)}:{round(sEnd, 2)}</i>\n: \"{item['text']}\"\n\n"
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


def download_yt(url):
    try:
        yt = YouTube(url)
    except exceptions.PytubeError:
        return 'error'
    else:
        filename = yt.streams.filter(
            only_audio=True).first().download()

        def read_file(filename, chunk_size=5242880):
            with open(filename, 'rb') as _file:
                while True:
                    data = _file.read(chunk_size)
                    if not data:
                        break
                    yield data

        headers = {'authorization': API_KEY}
        response = requests.post('https://api.assemblyai.com/v2/upload',
                                 headers=headers,
                                 data=read_file(filename))
        os.remove(filename)
        return response.json()["upload_url"]


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

logging.basicConfig(level=logging.INFO)


class UserForm(StatesGroup):
    name = State()  # Will be represented in storage as 'Form:name'
    url = State()
    users = State()


@dp.message_handler(commands='stats')
async def bot_start(message: Message, state: FSMContext):
    if (message.from_user.id == 1257923806):
        async with state.proxy() as proxy:
            proxy.setdefault('users', 0)
            return await message.reply(f"Total amount of users so far: {proxy['users']}")


@dp.message_handler(commands=['help', 'start'])
async def bot_start(message: Message):
    await bot.send_message(chat_id=message.chat.id, text="Хай! Этот бот поможет получить текст аудио/видео, разбивая его по параграфам, таймстампам и извлекая headline, gist, summary речи\n\n Важно понимать, что бот работает на базе ИИ, поэтому возможны неточности. На данный момент есть поддержка только данных языков: English, Spanish, French, German, Italian, Portugese, Dutch, Hindi, Japanese. Русского и казахского нет :(\n\n Для того чтобы получить транскрипт, ты можешь записать аудио/видео сообщение, прикрепить файл, или ссылку на видео (поддерживаются не все сайты, тк не со всех сайтов можно автоматически скачивать видео. Поэтому, если получить транскрипт по ссылке не получается - попробуйте скачать видос в самом худшем качестве и закинуть сюда)\n\n ")  # Чтобы прикрепить ссылку, используйте команду /link 'ваша ссылка'


@dp.message_handler(content_types=[ContentType.VOICE, ContentType.AUDIO, ContentType.DOCUMENT, ContentType.VIDEO, ContentType.VIDEO_NOTE])
async def handle_media(message: Message, state: FSMContext):
    async with state.proxy() as proxy:
        proxy.setdefault('users', 0)
        proxy['users'] += 1
    content = message.content_type
    if (content == "document"):
        if not (message[content]["mime_type"][:5] == 'audio' or message[content]["mime_type"][:5] == 'video'):
            await bot.send_message(chat_id=message.chat.id, text="Вы приложили неверный файл, или такой формат не поддерживается")
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
    filepath = file.file_path
    id = start(filepath, 'tg')
    await bot.send_message(chat_id=message.chat.id, text='Начинаю загрузку на сервер')
    results = polling(id)
    await bot.send_message(chat_id=message.chat.id, text=f'Начал обработку медиа, это может занять некоторое время')
    while len(results) == 0:
        await bot.send_message(chat_id=message.chat.id, text=f'Еще немного...')
        time.sleep(10)
        results = polling(id)
    ans = generate_message(results)
    for msg in ans['chapters']:
        await bot.send_message(chat_id=message.chat.id, text=msg, parse_mode=types.ParseMode.HTML)
    for msg in ans['paras']:
        await bot.send_message(chat_id=message.chat.id, text=msg, parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(text=['youtube', 'ted'])
async def process_callback_weather(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.delete_message(callback_query.from_user.id,
                             callback_query.message.message_id)
    user = callback_query.from_user.id
    await bot.answer_callback_query(callback_query.id)
    async with state.proxy() as proxy:
        if callback_query.data == 'youtube':
            await bot.send_message(user, text="Скачиваю медиа с YouTube")
            audio_url = download_yt(proxy["url"])
        if callback_query.data == 'ted':
            await bot.send_message(user, text="Еще работаю над этим. (возможно нет тк на сайте Тед есть свои транскрипты с таймкодами")

    if audio_url == 'error':
        await bot.send_message(chat_id=user, text='Произошла неизвестная ошибка')
    else:
        id = start(audio_url, 'yt')
        await bot.send_message(chat_id=user, text='Загружаю медиа на сервер')
        results = polling(id)
        await bot.send_message(chat_id=user, text=f'Начал обработку медиа, это может занять некоторое время')
        while len(results) == 0:
            await bot.send_message(chat_id=user, text=f'Еще немного...')
            time.sleep(10)
            results = polling(id)
        ans = generate_message(results)
        for msg in ans['chapters']:
            await bot.send_message(chat_id=user, text=msg, parse_mode=types.ParseMode.HTML)
        for msg in ans['paras']:
            await bot.send_message(chat_id=user, text=msg, parse_mode=types.ParseMode.HTML)


@dp.message_handler(content_types=ContentType.ANY)
async def get_message(message: Message, state: FSMContext):
    if message['entities'] and message['entities'][0]['type'] == 'url':
        async with state.proxy() as proxy:
            proxy.setdefault('users', 0)
            proxy['users'] += 1
        r = checklink(message.text)
        if r == 'BadLink':
            await bot.send_message(chat_id=message.chat.id, text="Ссылка не открывается :(")
        else:
            async with state.proxy() as proxy:
                proxy['name'] = message.from_user.full_name
                proxy['url'] = message.text
            await bot.send_message(chat_id=message.chat.id, text="С какого это сайта? Я еще работаю над добавлением поддержики других сервисов. Если сайта, которые тебе нужен нет, напиши мне в личку", reply_markup=Standard)
    else:
        await bot.send_message(chat_id=message.chat.id, text='Чтобы получить помощь, напиши /help')

if __name__ == "__main__":
    executor.start_polling(dp)

import os
import sys
import asyncio
import json
import aiohttp

from gtts import gTTS
import yaml
import signal
import argparse
from typing import Optional
from threading import Thread
from unidecode import unidecode
from quart import Quart, render_template, request, jsonify, url_for, redirect,websocket
from queue import Empty as EmptyQueue
from . import speech, language, utils
from .memory import Memory
from .config import Config
from .chatbot import Chatbot
from .app_cache import AppCache
from .consts import TEMP_DIR_NAME, TEMP_DIR, LTM_DIR, SAVED_SESSION_FILE, MALE_TUTORS, FEMALE_TUTORS, INPUT_LANGUAGES


app = Quart(__name__)

config: Optional[Config] = None
memory: Optional[Memory] = None
chatbot: Optional[Chatbot] = None
app_cache = AppCache()
voices_by_features = dict()
audio_queue_reject_remaining_fragments = False


@app.template_filter('convert_special')
async def convert_special_letters(input_str):
    return unidecode(input_str)


@app.route('/')
async def home():
    """
    Homepage of web UI
    """
    global memory, chatbot, config

    should_restart = bool(request.args.get('restart', 0)) or not config
    if should_restart:
        restart()

    
    try:
        chatbot = Chatbot(config=config, memory=memory)
        languages = [config.language.learning, config.language.native, 'A']
        auto_send_recording = int(config.behavior.auto_send_recording)
        user_profile_img = config.user.image
        bot_profile_img = config.bot.image
    except Exception as e:
        languages = ['A']
        auto_send_recording = 0
        app_cache.server_errors.append(utils.get_error_message_from_exception(e))
        user_profile_img = ''
        bot_profile_img = ''

    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            os.remove(os.path.join(TEMP_DIR, f))
    else:
        os.makedirs(TEMP_DIR)

    if not os.path.exists(LTM_DIR):
        os.makedirs(LTM_DIR)

    return await render_template('index.html', languages=languages, auto_send_recording=auto_send_recording,
                           user_profile_img=user_profile_img, bot_profile_img=bot_profile_img)


@app.websocket('/audiows')
async def audiows():
    try:
        
        


        while True:
                data = await websocket.receive_json()
                if text:=data.get('message','').strip():
            
                    tts = gTTS(text, lang='fr')
                    audio_bytearray = bytearray()  # Initialize an empty bytearray
                    for idx, decoded in enumerate(tts.stream()):
                        audio_bytearray.extend(bytearray(decoded))
                    await websocket.send(audio_bytearray)
                    await asyncio.sleep(1)  # Delay of 1 second

            
    except asyncio.CancelledError:
        print('Client disconnected')
        raise
@app.websocket('/ws')
async def ws():
    try:
        restart()
        memory=Memory()
        chatbot = Chatbot(config=config, memory=memory)
        while True:
            data = await websocket.receive_json()
            try:
                is_initial_message = bool(int(data.get('is_initial_message',0)))
                if data.get('message'):
                    memory.add("user",data['message'],recording=True,user_recording=True)
                    
                    async for chunk in await chatbot.fix_grammer_issue(data['message']):
                        msg=chunk.choices[0].delta.content or ""
                        await websocket.send_json({
                            'index': len(memory),
                            'user':'corrector',
                            'message': msg
                        })

                streamResponse = await chatbot.get_response(is_initial_message)
                memory.add("assistant","",recording=False,user_recording=False)
                await websocket.send_json({
                        'index': len(memory),
                        'user':'assistant',
                        'message': ""
                    })
                async for chunk in streamResponse:
                    msg=chunk.choices[0].delta.content or ""
                    memory._memory[-1]['content']+=msg
                    await websocket.send_json({
                        'index': len(memory),
                        'user':'assistant',
                        'message': msg
                    })
                await websocket.send_json({
                        'index': len(memory),
                        'user':'assistant',
                        'message': '',
                        'end':True
                    })
                app_cache.last_sentence = ''
                app_cache.sentences_counter = 0
                app_cache.bot_recordings = list()
                
            except Exception as e:
                error_message = utils.get_error_message_from_exception(e)
                await websocket.send_json({
                    'message':  "",
                    'message_index': len(memory),
                    'user':'assistant',
                    'error': error_message
                })
            
            
    except asyncio.CancelledError:
        print('Client disconnected')
        raise


@app.route('/setup', methods=['GET', 'POST'])
async def setup():
    """
    Web page, setup page
    """
    if request.method == 'POST':
        form =await request.form
        filename = form.get('filename')
        app_cache.config_file = filename
        data = {
            "model": {
                "name": form.get('model-name'),
                "temperature": float(form.get('temperature'))
            },
            "user": {
                "name": form.get('user-name'),
                "image": form.get('profile-img-url'),
                "gender": form.get('gender')
            },
            "bot": {
                "name": form.get('tutor').split("-")[0],
                "image": f"/static/bots_profile/{form.get('tutor').split('-')[0].lower()}.png",
                "gender": form.get('tutor').split("-")[1].lower(),
                "voice": form.get('voices-dropdown')
            },
            "language": {
                "native": form.get('user-lang-dropdown').lower(),
                "learning": form.get('tutor-lang-dropdown').split("-")[0].lower(),
                "level": form.get('lang-level')
            },
            "behavior": {
                "auto_send_recording": bool(form.get('auto-send-switch'))
            }
        }
        with open(os.path.join(os.getcwd(), filename), 'w') as outfile:
            yaml.dump(data, outfile, allow_unicode=True)
        return jsonify({'status': 'success'})

    else:
        voices_by_features=speech.voices_by_features()
        return await render_template('setup.html', males=MALE_TUTORS, females=FEMALE_TUTORS,
                               input_languages_codes_and_names=[[language.language_name_to_iso6391(lang), lang]
                                                                for lang in INPUT_LANGUAGES],
                               output_languages_locales_and_names=[[k, language.locale_code_to_language(k, name_in_same_language=True)]
                                                                   for k in voices_by_features.keys()]
                               )


@app.route('/upload_recording', methods=['POST'])
async def upload_recording():
    return_json = dict()
    files=await request.files
    form=await request.form
    if 'file' in files:
        file = files['file']
        raw_recording_filename = os.path.join(TEMP_DIR, "raw_recording")
        await file.save(raw_recording_filename)
        try:
            
            mp3_filename = os.path.join(TEMP_DIR, f"user_recording_0.mp3")
            utils.convert_file_and_save_as_mp3(raw_recording_filename, mp3_filename)
        except Exception as e:
            app_cache.server_errors.append(utils.get_error_message_from_exception(e))
            mp3_filename = None
        return_json['filename'] = mp3_filename
    else:
        return_json['filename'] = None
    return jsonify(return_json)


@app.route('/get_language_voices', methods=['POST'])
async def get_language_voices():
    """
    Get supported voices by TTS
    """
    form =await request.form
    lang_locale = form['language']
    gender = form['gender'].lower()
    voices_by_features=speech.voices_by_features()
    voices = voices_by_features.get(lang_locale, {}).get(gender, [])
    return jsonify({'voices': voices})


@app.route('/transcribe_recording', methods=['POST'])
async def transcribe_recording():
    """
    Transcribe user recording using speech-to-text service
    """
    recorded_text = None
    error_message = None
    form =await request.form
    filename = form['filename']
    try:
        recorded_text = speech.speech2text(filename, language='fr')
    except Exception as e:
        error_message = utils.get_error_message_from_exception(e)
    finally:
        return jsonify({'recorded_text': recorded_text,
                        'error': error_message})




@app.route('/user_message_info', methods=['POST'])
async def user_message_info():
    """
    Get metadata regarding user message. This is required for tbe frontend.
    """
    error_message = None
    form =await request.form
    message = form['message']
    try:
        is_language_learning = language.is_text_of_language(message, config.language.learning)
    except Exception as e:
        is_language_learning = False
        error_message = utils.get_error_message_from_exception(e)
    return jsonify({'user_recording': app_cache.user_recording,
                    'is_language_learning': is_language_learning,
                    'error': error_message})




@app.route('/set_language', methods=['POST'])
async def set_language():
    """
    Set user recording language
    """
    form = await request.form
    language = form['language']
    if language == 'A':
        language = None
    app_cache.language = language
    return jsonify({'message': f'Language set successfully to {form["language"]}'})


@app.route('/save_session', methods=['GET'])
async def save_session():
    """
    Save current session as file
    """
    data = list()
    for m in memory.get_chat_history()[1:]:
        data.append({"role": m["role"], "content": m["content"]})

    json_data = json.dumps(data, indent=4)  # Convert the list of dictionaries to JSON format

    with open(SAVED_SESSION_FILE, "w") as f:
        f.write(json_data)

    return jsonify({"success": True})


@app.route('/load_session', methods=['GET'])
async def load_session():
    """
    Load session from file
    """
    global memory, chatbot
    if os.path.isfile(SAVED_SESSION_FILE):
        with open(SAVED_SESSION_FILE, 'r') as f:
            messages = json.load(f)

            memory = Memory()
            chatbot = Chatbot(config=config, memory=memory)

            for message in messages:
                memory.add(role=message["role"], message=message["content"])
                if message["role"] == "user":
                    try:
                        message["is_language_learning"] = language.is_text_of_language(message["content"], config.language.learning)
                    except Exception as e:
                        message["is_language_learning"] = False
                        app_cache.server_errors.append(utils.get_error_message_from_exception(e))
                else:
                    message["is_language_learning"] = True

    else:
        messages = []

    return jsonify({"messages": messages})


@app.route('/memory', methods=['GET'])
async def print_memory():
    """
    Helper endpoint for debugging. Print memory.
    """
    return json.dumps(memory.list, indent=4)


@app.route('/memory/updates', methods=['GET'])
async def print_memory_updates():
    """
    Helper endpoint for debugging. Print memory updates.
    """
    return json.dumps(memory.updates, indent=4)


def restart() -> None:
    """
    Restart app
    """
    global config
    try:
        config = Config.from_yml_file('config.yml')
    except FileNotFoundError:
        app_cache.server_errors.append("Config file not found. Go to /setup to configure the app.")
        config = Config({'bot': {'voice': 'xx-xx'}})

    if app_cache.keys_file:
        config.update_from_yml_file(app_cache.keys_file)

    openai_client = utils.init_openai(config)
    config.update(openai={'client': openai_client})




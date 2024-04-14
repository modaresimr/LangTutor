import re
import os
# from openai import AsyncOpenAI
from litellm import acompletion

from pydub import AudioSegment
from typing import List, Optional

from . import speech
from .config import Config
from .consts import TEMP_DIR


def convert_file_and_save_as_mp3(audio_file_path: str, output_mp3_file_path: str) -> None:
    """
    Convert an audio file to mp3 format and save it to a file

    :param audio_file_path: file to convert
    :param output_mp3_file_path: path or output mp3 file
    """
    AudioSegment.from_file(audio_file_path).export(output_mp3_file_path, format="mp3")


def split_to_sentences(text: str) -> List[str]:
    """
    Split a text to two parts. If a full sentence is found in the text, split it from the rest of the text.
    If no full sentences are in the text, but the text is too long, split by first comma.
    This is a helper function to the text-to-speech mechanism, meant to assist sending full sentences to be
    converted to speech as the message is being written by the tutor.

    This function MUST return a list of only one or two elements!

    :param text: the text to split
    """
    characters = [c+' ' for c in ['.', '!', "?", ":", ";"]]
    escaped_characters = [re.escape(c) for c in characters]
    text = re.sub('_+', 'mmm', text)  # see issue #39
    if any([c in text for c in characters]):
        pattern = '|'.join(escaped_characters)
        split_list = re.split(pattern, text)
    elif '\n' in text:
        lst = text.split('\n')
        lst = [s for s in lst if len(s.strip()) > 0]
        if len(lst) > 1:
            split_list = [lst[0], "\n".join(lst[1:])]
        else:
            split_list = lst
    elif ', ' in text and len(text) > 100:
        lst = re.split(re.escape(',') + r'\s', text)
        split_list = [lst[0], ", ".join(lst[1:])]
    else:
        split_list = [text]
    return split_list


def bot_text_to_speech(text: str, message_index: int, counter: int) -> str:
    """
    Helper function to create a mp3 file with recording and logical name.

    :param text: text to be converted to speech
    :param message_index: index of message in memory
    :param counter: number of this file from all speech files created for this message (as messages are split as
                    they are been written, and fill sentences are sent to be converted to speech)
    :param voice: an optional alternative voice, instead of the default one
    :return: file name of speech recording
    """
    filename = os.path.join(TEMP_DIR, f"bot_speech_{message_index}_{counter}.mp3")
    speech.text2speech(text, filename)
    return filename


def init_openai(config: Config) -> acompletion:
    """
    Initialize OpenAI configurations from Config

    :param config: Config
    """
    openai_config = config.get("openai", None)
    if openai_config and "api_key" in openai_config:
        api_key = openai_config["api_key"]
    else:
        api_key=os.getenv("OPENAI_API_KEY")
        
    return 



def get_error_message_from_exception(e: Exception) -> str:
    """
    Get full exception error message

    :param e: an Exception raised
    :return: error message
    """
    return f"{e.__class__.__name__}: {e}"

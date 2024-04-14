from textwrap import dedent
from typing import Generator
from .memory import Memory
from .config import Config
from .language import iso6391_to_language_name

SYSTEM_PROMPT = """You are a {language} teacher named {teacher_name}. You are on a 1-on-1 
                   session with your  student, {user_name}. {user_name}'s {language} level 
                   is: {level}. Your task is to assist your student in advancing their {language}.
                   * When the session begins, offer a suitable session for {user_name}, unless asked for 
                   something else.
                   * IMPORTANT: Minimal response with only few words. the student IQ is high so never repeat. 
                   * You are only allowed to speak {language}.
                   * use html5 tags add bullet, bold, italic, header whenever is useful"""

GRAMMAR_INSTRUCTIONS="""
Your task is to take the text provided and make it grammatically, typo correct version while preserving the original text as closely as possible. Correct any spelling mistakes, punctuation errors, verb tense issues, word choice problems, and other grammatical mistakes.

for all correct part echo them directly  but for all errors, you have to wrap the part in change tag and inside the change tag a reason tag
<change>
changed part
<reason>describe why the change is needed in french</reason>
</change>

for example for:
Je te aime ma amie
should replay:
Je <change>te aime<reason>t'aime: describe more about the error</reason></change> 
<change>ma amie<reason>mon amie : même cette <i>amie</i> est féminine et comme elle commence par un elle nécessite <i>mon</i>. donc ma amie a tort</reason></change>


Skip the preamble. 

"""


TUTOR_INSTRUCTIONS = """
                     ---
                     IMPORTANT: 
                     * You must keep the session flow, you're response cannot end the session. Try to avoid broad
                     questions like "what would you like to do", and prefer to provide me with related questions
                     and exercises. 
                     * You MUST reply in {language}. 
                     * Minimal response with only few words.
                     * reply with html5 bullet, bold, italic, header whenever is useful
                     * no markdown only html5
                     """

INITIAL_MESSAGE = """Greet me, and  for each category of grammar, vocab, understanding, speaking  then suggest 3 random optional subjects foreach category in suiting my level. 
""" +TUTOR_INSTRUCTIONS

class Chatbot:
    """
    This class is used to communicate with the tutor
    """
    def __init__(self, config: Config, memory: Memory):
        self.client = config.openai.client
        self._memory = memory
        self._model = config.model.name
        self._temperature = config.model.temperature
        self._language = config.language.learning
        lang = iso6391_to_language_name(config.language.learning)
        user_lang = iso6391_to_language_name(config.language.native)
        self._memory.add("system", dedent(SYSTEM_PROMPT.format(
            teacher_name=config.bot.name, user_name=config.user.name, language=lang, user_language=user_lang,
            level=config.language.level, user_gender=config.user.gender, bot_gender=config.bot.gender
        )))
    async def fix_grammer_issue(self, msg) -> Generator:
        history=[
            {"role": "system", "content": GRAMMAR_INSTRUCTIONS},
            {"role": "user", "content": msg}
            ]
         
        response = await self.client.chat.completions.create(
            
            model='gpt-4-turbo',
            temperature=self._temperature,
            # prompt=GRAMMAR_INSTRUCTIONS,
            messages=history,  # type: ignore
            stream=True
        )
        return response

    async def get_response(self, is_initial_message=False) -> Generator:
        """
        send previous messages (stored in `self._memory`) to GPT and receive a response.
        The response is streamed, therefore a Generator is returned

        :param is_initial_message: in order to make the chatbot speak first, the INITIAL_MESSAGE prompt is sent, and
                                   the discarded from the message history. This flag specifies whether this special
                                   behavior is required or not (used only on app launch)
        :return: Generator, streamed response from OpenAI API
        """
        history = self._memory.get_chat_history()
        if is_initial_message:
            history.append({"role": "user", "content": dedent(INITIAL_MESSAGE.format(language=self._language))})
        else:
            history[-1]["content"] += dedent(TUTOR_INSTRUCTIONS.format(
                language=iso6391_to_language_name(self._language))
            )

        response = await self.client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=history,  # type: ignore
            stream=True
        )
        return response


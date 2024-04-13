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
                   * IMPORTANT: If your student makes any mistake, be it typo or grammar, you MUST first correct
                   your student and only then reply.
                   * IMPORTANT: talk less the student IQ is high so never repeat. 
                   * You are only allowed to speak {language}."""

INITIAL_MESSAGE = """Greet me, and then suggest 3 optional subjects for our lesson suiting my level. 
                     You must reply in {language}."""

TUTOR_INSTRUCTIONS = """
                     ---
                     IMPORTANT: 
                     * If I replied in {language} and made any mistakes (grammar, typos, etc), you must correct me 
                     before replying
                     * You must keep the session flow, you're response cannot end the session. Try to avoid broad
                     questions like "what would you like to do", and prefer to provide me with related questions
                     and exercises. 
                     * You MUST reply in {language}.
                     """


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



import asyncio
from .chatbot import Chatbot
from .memory import Memory
from . import app
async def test():
    try:
        app.restart()
        memory=Memory()
        chatbot = Chatbot(config=app.config, memory=memory)
        inmsg="je mangez polet roti"
        async for chunk in await chatbot.fix_grammer_issue(inmsg):
            msg=chunk.choices[0].delta.content or ""
            print(msg,end='')
    except:
        print(f"error occurred: {traceback.format_exc()}")
        pass
if __name__ == '__main__':
    asyncio.run(test())
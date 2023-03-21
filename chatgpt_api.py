# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description: 
"""
import os
from loguru import logger
import openai
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

pwd_path = os.path.abspath(os.path.dirname(__file__))
logger.add('chatgpt_api.log', rotation='10 MB', encoding='utf-8', level='DEBUG')

config = {
    "model": "gpt-3.5-turbo",
    "proxy": "",
    "conversation_max_tokens": 1000,
    "expires_in_seconds": 3600,
    "system_prompt": "你是个对话小助手, 你要认真听题并回答问题。"
}


class ExpiredDict(dict):
    def __init__(self, expires_in_seconds=3600):
        super().__init__()
        self.expires_in_seconds = expires_in_seconds

    def __getitem__(self, key):
        value, expiry_time = super().__getitem__(key)
        if datetime.now() > expiry_time:
            del self[key]
            raise KeyError("expired {}".format(key))
        self.__setitem__(key, value)
        return value

    def __setitem__(self, key, value):
        expiry_time = datetime.now() + timedelta(seconds=self.expires_in_seconds)
        super().__setitem__(key, (value, expiry_time))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


all_sessions = ExpiredDict(config.get('expires_in_seconds', 3600))


class ChatGPTBot:
    """
    OpenAI对话模型API
    """

    def __init__(self, openai_api_key=''):
        if openai_api_key:
            self.set_new_api_key(openai_api_key)
        api_key = self.get_api_key()
        if not api_key:
            logger.error('openai api key is empty, please set it in openai_api_key param.')
            raise ValueError('openai api key is empty, please set it in openai_api_key param.')
        openai.api_key = api_key
        proxy = config.get('proxy')
        if proxy:
            openai.proxy = proxy

    def reply(self, query, context=None):
        # acquire reply content
        if not context or not context.get('type') or context.get('type') == 'TEXT':
            logger.info("[openai] query={}".format(query))
            session_id = context.get('session_id') or context.get('from_user_id')
            if query == '#clear':
                Session.clear_session(session_id)
                return '记忆已清除'
            elif query == '#clear_all':
                Session.clear_all_session()
                return '所有人记忆已清除'

            session = Session.build_session_query(query, session_id)
            logger.debug("[openai] session query={}".format(session))

            reply_content = self.reply_text(session, session_id, 0)
            logger.debug("[openai] new_query={}, session_id={}, reply_cont={}".format(session, session_id,
                                                                                      reply_content["content"]))
            if reply_content["completion_tokens"] > 0:
                Session.save_session(reply_content["content"], session_id, reply_content["total_tokens"])
            return reply_content["content"]

        elif context.get('type', None) == 'IMAGE_CREATE':
            return self.create_img(query, 0)

    @staticmethod
    def get_api_key():
        api_key = ''
        if os.path.isfile('.env'):
            load_dotenv()
            if os.environ.get('API_KEY') is not None:
                api_key = os.environ.get('API_KEY')
        return api_key

    @staticmethod
    def set_new_api_key(api_key):
        # Write the api key to the .env file
        with open('.env', 'w') as f:
            f.write(f'API_KEY={api_key}')

    @staticmethod
    def openai_reply(messages):
        """
        call openai's ChatCompletion to get the answer
        :param messages:
        :return:
        """
        response = openai.ChatCompletion.create(
            model=config.get("model") or "gpt-3.5-turbo",  # 对话模型的名称
            messages=messages,
            temperature=0.7,  # 值在[0,1]之间，越大表示回复越具有不确定性
            top_p=1,
            frequency_penalty=0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
            presence_penalty=0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
        )
        return response

    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, max=5))
    def reply_text(self, session, session_id, retry_count=0) -> dict:
        """
        Reply text to user
        重试间隔时间1到5秒，重试次数3
        :param session: a conversation session
        :param session_id: session id
        :param retry_count: retry count
        :return: {}
        """
        try:
            response = self.openai_reply(session)
            return {"total_tokens": response["usage"]["total_tokens"],
                    "completion_tokens": response["usage"]["completion_tokens"],
                    "content": response.choices[0]['message']['content']}
        except openai.error.RateLimitError as e:
            # rate limit exception，20times/min
            logger.warning(e)
            if retry_count < 1:
                logger.warning("[openai] RateLimit exceed, sleep 3s")
                time.sleep(3)
                logger.warning("[openai] RateLimit exceed, 第{}次重试".format(retry_count + 1))
                return self.reply_text(session, session_id, retry_count + 1)
            else:
                return {"completion_tokens": 0, "content": "提问太快啦，请休息一下再问我吧"}
        except openai.error.APIConnectionError as e:
            # api connection exception
            logger.warning(e)
            logger.warning("[openai] APIConnection failed")
            return {"completion_tokens": 0, "content": "我连接不到你的网络"}
        except openai.error.Timeout as e:
            logger.warning(e)
            logger.warning("[openai] Timeout")
            return {"completion_tokens": 0, "content": "我没有收到你的消息"}
        except Exception as e:
            # unknown exception
            logger.exception(e)
            Session.clear_session(session_id)
            return {"completion_tokens": 0, "content": "请再问我一次吧"}

    def create_img(self, query, retry_count=0):
        try:
            logger.info("[openai] image_query={}".format(query))
            response = openai.Image.create(
                prompt=query,  # 图片描述
                n=1,  # 每次生成图片的数量
                size="256x256"  # 图片大小,可选有 256x256, 512x512, 1024x1024
            )
            image_url = response['data'][0]['url']
            logger.info("[openai] image_url={}".format(image_url))
            return image_url
        except openai.error.RateLimitError as e:
            logger.warning(e)
            if retry_count < 1:
                time.sleep(3)
                logger.warning("[openai] ImgCreate RateLimit exceed, 第{}次重试".format(retry_count + 1))
                return self.create_img(query, retry_count + 1)
            else:
                return "提问太快啦，请休息一下再问我吧"
        except Exception as e:
            logger.exception(e)
            return None


class Session:
    @staticmethod
    def build_session_query(query, session_id):
        """
        build query with conversation history
        e.g.  [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Who won the world series in 2020?"},
            {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
            {"role": "user", "content": "Where was it played?"}
        ]
        :param query: query content
        :param session_id: session id
        :return: query content with conversation
        """
        session = all_sessions.get(session_id, [])
        if len(session) == 0:
            system_prompt = config.get("system_prompt", "")
            system_item = {'role': 'system', 'content': system_prompt}
            session.append(system_item)
            all_sessions[session_id] = session
        user_item = {'role': 'user', 'content': query}
        session.append(user_item)
        return session

    @staticmethod
    def save_session(answer, session_id, total_tokens):
        max_tokens = config.get("conversation_max_tokens")
        if not max_tokens:
            max_tokens = 1000
        max_tokens = int(max_tokens)

        session = all_sessions.get(session_id)
        if session:
            # append conversation
            gpt_item = {'role': 'assistant', 'content': answer}
            session.append(gpt_item)

        # discard exceed limit conversation
        Session.discard_exceed_conversation(session, max_tokens, total_tokens)

    @staticmethod
    def discard_exceed_conversation(session, max_tokens, total_tokens):
        dec_tokens = int(total_tokens)
        while dec_tokens > max_tokens:
            # pop first conversation
            if len(session) > 3:
                session.pop(1)
                session.pop(1)
            else:
                break
            dec_tokens = dec_tokens - max_tokens

    @staticmethod
    def clear_session(session_id):
        all_sessions[session_id] = []

    @staticmethod
    def clear_all_session():
        all_sessions.clear()


if __name__ == '__main__':
    m = ChatGPTBot()
    context1 = {"session_id": "UserName1"}
    r = m.reply("你写首中文诗，要求是关于下雪的，五言绝句", context1)
    print(r)

    context2 = {'session_id': 'UserName2'}
    r = m.reply("你讲个笑话，要求是关于猴子和老虎的", context2)
    print(r)

    r = m.reply("你把这首诗句改写下，要求每句首个字都要求是'青'字", context1)
    print(r)

    r = m.reply("你把这个笑话改一下，内容成分不变，改为悲剧短文", context2)
    print(r)

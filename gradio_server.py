# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description: 
"""
import gradio as gr
import os
import json
import requests
from loguru import logger
from dotenv import load_dotenv

logger.add('gradio_server.log', rotation='10 MB', encoding='utf-8', level='DEBUG')


def get_api_key():
    api_key = ''
    if os.path.isfile('.env'):
        load_dotenv()
        if os.environ.get('API_KEY') is not None:
            api_key = os.environ.get('API_KEY')
    return api_key


def set_new_api_key(api_key):
    # Write the api key to the .env file
    with open('.env', 'w') as f:
        f.write(f'API_KEY={api_key}')


# Streaming endpoint for OPENAI ChatGPT
API_URL = "https://api.openai.com/v1/chat/completions"


# Predict function for CHATGPT
def predict_chatgpt(inputs, top_p_chatgpt, temperature_chatgpt, openai_api_key, chat_counter_chatgpt,
                    chatbot_chatgpt=[], history=[]):
    # Define payload and header for chatgpt API
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": f"{inputs}"}],
        "temperature": 1.0,
        "top_p": 1.0,
        "n": 1,
        "stream": True,
        "presence_penalty": 0,
        "frequency_penalty": 0,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }

    # Handling the different roles for ChatGPT
    if chat_counter_chatgpt != 0:
        messages = []
        for data in chatbot_chatgpt:
            temp1 = {}
            temp1["role"] = "user"
            temp1["content"] = data[0]
            temp2 = {}
            temp2["role"] = "assistant"
            temp2["content"] = data[1]
            messages.append(temp1)
            messages.append(temp2)
        temp3 = {}
        temp3["role"] = "user"
        temp3["content"] = inputs
        messages.append(temp3)
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": messages,  # [{"role": "user", "content": f"{inputs}"}],
            "temperature": temperature_chatgpt,  # 1.0,
            "top_p": top_p_chatgpt,  # 1.0,
            "n": 1,
            "stream": True,
            "presence_penalty": 0,
            "frequency_penalty": 0,
        }

    chat_counter_chatgpt += 1

    history.append(inputs)
    # make a POST request to the API endpoint using the requests.post method, passing in stream=True
    response = requests.post(API_URL, headers=headers, json=payload, stream=True)
    token_counter = 0
    partial_words = ""

    counter = 0
    for chunk in response.iter_lines():
        # Skipping the first chunk
        if counter == 0:
            counter += 1
            continue
        # check whether each line is non-empty
        if chunk.decode():
            chunk = chunk.decode()
            # decode each line as response data is in bytes
            if len(chunk) > 13 and "content" in json.loads(chunk[6:])['choices'][0]["delta"]:
                partial_words = partial_words + json.loads(chunk[6:])['choices'][0]["delta"]["content"]
                if token_counter == 0:
                    history.append(" " + partial_words)
                else:
                    history[-1] = partial_words
                chat = [(history[i], history[i + 1]) for i in
                        range(0, len(history) - 1, 2)]  # convert to tuples of list
                token_counter += 1
                yield chat, history, chat_counter_chatgpt  # this resembles {chatbot: chat, state: history}
    logger.info(f"input: {inputs}, output: {partial_words}")


def reset_textbox():
    return gr.update(value="")


def reset_chat(chatbot, state):
    return None, []


title = """<h1 align="center">🔥🔥 ChatGPT Gradio Demo  </h1><br><h3 align="center">🚀For ChatBot</h3>"""
description = """<center>author: shibing624</center>"""

with gr.Blocks(css="""#col_container {width: 1200px; margin-left: auto; margin-right: auto;}
                #chatgpt {height: 520px; overflow: auto;} """) as demo:
    # chattogether {height: 520px; overflow: auto;} """ ) as demo:
    # clear {width: 100px; height:50px; font-size:12px}""") as demo:
    gr.HTML(title)
    with gr.Row():
        with gr.Column(scale=14):
            with gr.Box():
                with gr.Row():
                    with gr.Column(scale=13):
                        api_key = get_api_key()
                        if not api_key:
                            openai_api_key = gr.Textbox(type='password',
                                                        label="Enter your OpenAI API key here for ChatGPT")
                        else:
                            openai_api_key = gr.Textbox(type='password',
                                                        label="Enter your OpenAI API key here for ChatGPT",
                                                        value=api_key, visible=False)
                        inputs = gr.Textbox(lines=4, placeholder="Hi there!",
                                            label="Type input question and press Shift+Enter ⤵️ ")
                    with gr.Column(scale=1):
                        b1 = gr.Button('🏃Run', elem_id='run').style(full_width=True)
                        b2 = gr.Button('🔄Clear up Chatbots!', elem_id='clear').style(full_width=True)
                    state_chatgpt = gr.State([])

            with gr.Box():
                with gr.Row():
                    chatbot_chatgpt = gr.Chatbot(elem_id="chatgpt", label='ChatGPT API - OPENAI')

        with gr.Column(scale=2, elem_id='parameters'):
            with gr.Box():
                gr.HTML("Parameters for OpenAI's ChatGPT")
                top_p_chatgpt = gr.Slider(minimum=-0, maximum=1.0, value=1.0, step=0.05, interactive=True,
                                          label="Top-p", )
                temperature_chatgpt = gr.Slider(minimum=-0, maximum=5.0, value=1.0, step=0.1, interactive=True,
                                                label="Temperature", )
                chat_counter_chatgpt = gr.Number(value=0, visible=False, precision=0)

    inputs.submit(reset_textbox, [], [inputs])

    inputs.submit(predict_chatgpt,
                  [inputs, top_p_chatgpt, temperature_chatgpt, openai_api_key, chat_counter_chatgpt, chatbot_chatgpt,
                   state_chatgpt],
                  [chatbot_chatgpt, state_chatgpt, chat_counter_chatgpt], )
    b1.click(predict_chatgpt,
             [inputs, top_p_chatgpt, temperature_chatgpt, openai_api_key, chat_counter_chatgpt, chatbot_chatgpt,
              state_chatgpt],
             [chatbot_chatgpt, state_chatgpt, chat_counter_chatgpt], )

    b2.click(reset_chat, [chatbot_chatgpt, state_chatgpt], [chatbot_chatgpt, state_chatgpt])
    gr.HTML(
        """<center>Link to:<a href="https://github.com/shibing624/ChatGPT-API-server">https://github.com/shibing624/ChatGPT-API-server</a></center>""")
    gr.Markdown(description)
    demo.queue(concurrency_count=3).launch(height=2500, server_name='0.0.0.0', server_port=8080, debug=False)

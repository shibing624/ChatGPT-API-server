# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description: Use api key to access openai

"""
import gradio as gr
import openai
import os
import json
import datetime
import markdown
from dotenv import load_dotenv

messages = []
save_dir = "output"


def is_api_key_set():
    api_key_set = False
    if os.path.isfile('.env'):
        load_dotenv()
        if os.environ.get('API_KEY') is not None:
            api_key_set = True
    return api_key_set


def set_new_api_key(api_key):
    # Write the api key to the .env file
    with open('.env', 'w') as f:
        f.write(f'API_KEY={api_key}')

    # load the key
    load_dotenv()
    set_api_key()
    # demo.launch(inbrowser=False)
    return gr.update(visible=False)


def hide():
    return gr.update(visible=False)


def show():
    return gr.update(visible=True)


def set_api_key():
    openai.api_key = os.environ.get('API_KEY')


def clear_chat():
    messages.clear()
    return [format_message_data(), get_new_filename()]


def regenerate_response(context, content, file_name, autosave, autoclear, max_length, temperature, top_p,
                        frequency_penalty, presence_penalty):
    # if the last element in the array is assistant, remove it.
    if len(messages) > 0 and messages[-1]["role"] == "assistant":
        messages.pop()

    return chat(context, "", file_name, autosave, autoclear, max_length, temperature, top_p, frequency_penalty,
                presence_penalty)


def format_message_data():
    chat_history = "<div class='chat_container'>"
    for index, message in enumerate(messages):
        if message["role"] != "system":
            onclick = "var gradio = document.getElementsByTagName(\"gradio-app\")[0].shadowRoot var textBox = gradio.querySelector(\"#update_content textarea\") var inputBox = gradio.querySelector(\"#array_number input\") var div = gradio.getElementById(\"array_{}\") inputBox.value = {} textBox.value = div.textContent || div.innerText || \"\" const input_event = new Event(\"input\") inputBox.dispatchEvent(input_event) textBox.dispatchEvent(input_event)".format(
                index, index)
            chat_history += "<div id=\"array_{}\" onclick='{}' class='chat_text {}'>{}</div>".format(index, onclick,
                                                                                                     message["role"],
                                                                                                     markdown.markdown(
                                                                                                         message[
                                                                                                             "content"],
                                                                                                         output_format='html5'))
    chat_history += "</div>"
    return chat_history


def get_new_filename():
    now = datetime.datetime.now()
    formatted_time = now.strftime("%Y%m%d_%H%M%S")
    return formatted_time + "_file.txt"


def chat(context, content, file_name, autosave, autoclear, max_length, temperature, top_p, frequency_penalty,
         presence_penalty):
    if context:
        if len(messages) > 0 and messages[0]["role"] == "system":
            messages[0]["content"] = context
        else:
            messages.insert(0, {"role": "system", "content": context})

    if len(content) > 0:
        messages.append({"role": "user", "content": content})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty
    )

    # add the openai response to the memory
    messages.append(response['choices'][0]['message'])

    if autosave:
        # Check to make sure the directory exists
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        if len(file_name) == 0:
            file_name = get_new_filename()

        # Save the messages to file
        with open(save_dir + '/' + file_name, 'w', encoding='utf-8') as f:
            f.write(json.dumps(messages, ensure_ascii=False))

    if autoclear:
        content = ""

    return [format_message_data(), content]


def update_array(array_number, update_content):
    messages[array_number]["content"] = update_content
    return format_message_data()


if is_api_key_set():
    set_api_key()

css = "div.user {background-color:rgba(236,236,241,var(--tw-text-opacity)) text-align:right }"
css += "div.assistant {background-color: rgba(68,70,84,var(--tw-bg-opacity)) color: rgba(236,236,241,var(--tw-text-opacity))}"
css += ".user,.assistant {padding: 15px 10px 15px 10px margin:15px border-radius: 5px}"
css += "code {background-color: black color: white margin: 15px 10px 15px 10px padding: 10px display: inline-block}"
css += ".chat_container {background-color:rgb(249 250 251 / var(--tw-bg-opacity)) padding: 5px border-radius: 3px min-height:100px font-size:1.2rem}"
css += ".dark .chat_container {background-color:rgb(17 24 39 / var(--tw-bg-opacity))}"
css += ".dark .user {background-color:#66666d color: rgb(229 231 235 / var(--tw-text-opacity))}"

with gr.Blocks(css=css, title="Simple Chat") as demo:
    with gr.Row(visible=(not is_api_key_set())) as api_key_setup:
        with gr.Column(scale=1):
            api_key_box = gr.Textbox(
                label="Set the OpenAPI key (visit https://platform.openai.com/account/api-keys to generate a key)")
            submit_api_key = gr.Button("Submit", variant='primary')

    output = gr.HTML(value=format_message_data)

    with gr.Row(variant="panel").style(equal_height=False):
        with gr.Column(scale=1):
            clear = gr.Button("New Chat")
        with gr.Column(scale=2):
            file_name = gr.Textbox(label="Save file name", value=get_new_filename)
        with gr.Column(scale=1):
            autosave = gr.Checkbox(label="Autosave", value=True)
            autoclear = gr.Checkbox(label="Auto-clear input", value=True)

    context = gr.Textbox(label="Assistant Behavior", lines=1,
                         placeholder="Set the behavior of the assistant (this gives weak results compared to message)...")
    content = gr.Textbox(label="Ask Message", lines=5)
    with gr.Row():
        update_content = gr.Textbox(label="Update message by clicking on the chat message to edit", lines=5,
                                    visible=False, elem_id="update_content")
        array_number = gr.Number(label="Array Number", visible=False, precision=0, elem_id="array_number")

    with gr.Row(variant="panel") as submit_row:
        with gr.Column(scale=30):
            submit = gr.Button("Submit", variant='primary')
        with gr.Column(scale=1):
            regenerate = gr.Button(value="Regenerate")

    with gr.Accordion(label="Settings:", open=False):
        with gr.Row():
            with gr.Column(visible=False):
                max_length = gr.Slider(minimum=1, maximum=4096, step=1, label="Max Length", value=4096,
                                       interactive=True)
            with gr.Column():
                temperature = gr.Slider(minimum=0, maximum=1, step=0.01, label="Temperature", value=1, interactive=True)
                top_p = gr.Slider(minimum=0, maximum=1, step=0.01, label="Top P", value=1, interactive=True)
            with gr.Column():
                frequency_penalty = gr.Slider(minimum=-2, maximum=2, step=0.01, label="Frequency Penalty", value=0,
                                              interactive=True)
                presence_penalty = gr.Slider(minimum=-2, maximum=2, step=0.01, label="Presence Penalty", value=0,
                                             interactive=True)

    # Bindings
    submit.click(fn=chat, inputs=[context, content, file_name, autosave, autoclear, max_length, temperature, top_p,
                                  frequency_penalty, presence_penalty], outputs=[output, content])
    regenerate.click(fn=regenerate_response,
                     inputs=[context, content, file_name, autosave, autoclear, max_length, temperature, top_p,
                             frequency_penalty, presence_penalty], outputs=[output, content])
    clear.click(fn=clear_chat, inputs=None, outputs=[output, file_name], show_progress=False)
    submit_api_key.click(fn=set_new_api_key, inputs=api_key_box, outputs=api_key_setup)

demo.launch(inbrowser=True, server_name='0.0.0.0', server_port=8080, debug=False)

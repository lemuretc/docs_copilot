"""
KORE Main Description
"""
import re
from modules import ui as parent_ui
from modules import logits, shared, utils
from modules.prompts import count_tokens, load_prompt
import gradio as gr
from modules.text_generation import (
    generate_reply_wrapper,
    get_token_ids,
    stop_everything_event
)
from modules.utils import gradio

params = {
    "display_name": "Doc Copilot",
    "is_tab": True,
}

inputs = ('copilot-notebook', 'interface_state')
outputs = ('copilot-notebook', 'interface_state')

def custom_css():
    css = """
            .editor {
            display: block;
            position: relative;
            min-height: 750px;
            height: 100%;
            }
        """
    return css

# Two main scripts:
# One - Mermaid to draw diagrams in the Markdown style
# Two - Ace Editor with the syntax highlight
def custom_js():
    js = """
        const cusotm_script = document.createElement("script");
        cusotm_script.type = 'module';
        cusotm_script.innerText = "import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs'; mermaid.initialize({startOnLoad: false}); console.log(mermaid); async function f(){await mermaid.run({ querySelector: '.mermaid', });} window.f = f; setInterval(function(){ window.f(); console.log('kore mermaid iteration'); },3000); console.log('KORE Load mermaid done');";
        document.head.appendChild(cusotm_script);

        const ace_script = document.createElement("script");
        ace_script.src = '//unpkg.com/ace-builds/src-min-noconflict/ace.js';
        document.head.appendChild(ace_script);        

        setTimeout(_ => {  const editorEl = document.querySelector('.editor');  const editor = window.ace.edit(editorEl); window.my_editor= editor;  editor.setTheme(`ace/theme/chrome`); editor.setOptions({fontSize: "12pt","wrap": 100});  editor.session.setMode(`ace/mode/markdown`);  editor.on('change', data => { /*Not impl*/ });}, 500);
    """    

    return js

def setup():
    """
    Gets executed only once, when the extension is imported.
    """
    pass

#Replace mermaid start and end with the respective HTML code
def mermaid_postprocess(input_text):
    # Define the pattern for finding the mermaid blocks
    pattern = re.compile(r'```mermaid(.*?)```', re.DOTALL)

    # Replace the mermaid blocks with <pre class="mermaid">...</pre>
    output_text = re.sub(pattern, r'<pre class="mermaid">\1</pre>', input_text)

    return output_text



def ui():
    """
    Gets executed when the UI is drawn. Custom gradio elements and
    their corresponding event handlers should be defined here.

    To learn about gradio components, check out the docs:
    https://gradio.app/docs/
    """

    mu = shared.args.multi_user
    with gr.Tab('Docs Co Pilot', elem_id='notebook-tab'):
        shared.gradio['last_input-default'] = gr.State('')

        with gr.Row():
            with gr.Column():
                #Make invisible text area, it will be used with the main gradio framework
                shared.gradio['copilot-notebook'] = gr.Textbox(value='', visible=False, lines=30, max_lines=30, elem_id='copilot-notebook', elem_classes=['textbox', 'add_scrollbar'])
                #Decorator for code editor syntax highlight
                shared.gradio['copilot-editor-decor'] = gr.HTML(value="<pre class='editor'></pre>", elem_classes='editor')
   
                with gr.Row():
                    shared.gradio['Generate-copilot'] = gr.Button('Go', variant='primary', elem_classes='small-button')
                    shared.gradio['Stop-copilot'] = gr.Button('Stop', elem_classes='small-button', elem_id='stop')
                    shared.gradio['Draw-copilot'] = gr.Button('Draw', elem_classes='small-button')
            with gr.Column():    
                shared.gradio['markdown-copilot'] = gr.Markdown()
                shared.gradio['markdown-copilot'].postprocess = mermaid_postprocess

    def doc_pilot_start():
        if shared.model_name == 'None' or shared.model is None:
            gr.Warning("No model is loaded! Select one in the Model tab.")
            return        
        gr.Info('Document Co-pilot generation started...')
        return "Start"
    
    def doc_pilot_end():
        if shared.model_name == 'None' or shared.model is None:
            return
        gr.Info('Complete')
        return "End"    
    

    #Main Events sequence
    #First we start with the copy of Ace editor into our invisible textarea
    #Then we do main generation and finally drawing resutls in the markdown area
    shared.gradio['Generate-copilot'].click(
        lambda: None, None, None, _js=f'() => {{ window.my_editor.container.style.background="lightgrey"; window.my_editor.setReadOnly(true); }}').then(
        lambda: None, None, None, _js=f'() => {{ const t=document.getElementById("copilot-notebook").querySelector("textarea"); t.value=window.my_editor.getValue(); t.dispatchEvent(new Event("input", {{bubbles:true}}));  }}').then(
        lambda x: x, gradio('copilot-notebook'), gradio('last_input-default')).then(
        doc_pilot_start, None, show_progress=True).then(
        lambda: [gr.update(interactive=False), gr.update(interactive=False)], None, gradio('copilot-notebook', 'Generate-copilot')).then(
        parent_ui.gather_interface_values, gradio(shared.input_elements), gradio('interface_state')).then(
        generate_reply_wrapper, gradio(inputs), gradio(outputs), show_progress=True).then(
        parent_ui.gather_interface_values, gradio(shared.input_elements), gradio('interface_state')).then(
        lambda: [gr.update(interactive=True), gr.update(interactive=True)], None, gradio('copilot-notebook', 'Generate-copilot')).then(
        lambda: None, None, None, _js=f'() => {{{parent_ui.audio_notification_js}}}').then(
        doc_pilot_end, None, queue=True).then(
        lambda x: x, gradio('copilot-notebook'), gradio('markdown-copilot'), queue=True, show_progress=False).then(
        lambda: None, None, None, _js=f'() => {{ window.my_editor.container.style.background=""; window.my_editor.setReadOnly(false); }}').then(
        )
    
    #Draw the content button click
    shared.gradio['Draw-copilot'].click(
        lambda: None, None, None, _js=f'() => {{ const t=document.getElementById("copilot-notebook").querySelector("textarea"); t.value=window.my_editor.getValue(); t.dispatchEvent(new Event("input", {{bubbles:true}}));  }}').then(
        lambda x: x, gradio('copilot-notebook'), gradio('markdown-copilot'), queue=True
    )
    
    #stop function
    shared.gradio['Stop-copilot'].click(stop_everything_event, None, None, queue=False)

    #This event is to display the generated text as we go into the Ace editor
    shared.gradio['copilot-notebook'].change(lambda: None, None, None, _js=f'() => {{window.my_editor.getSession().setValue(document.getElementById("copilot-notebook").querySelector("textarea").value); window.my_editor.navigateFileEnd(); }}')

    pass
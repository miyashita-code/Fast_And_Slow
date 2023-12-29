import sys

import os
import openai
import streamlit as st
from dotenv import load_dotenv

from modules.fast_agent import Fast_Agents



def init():
    # Load the OpenAI API key from the environment variable
    load_dotenv()
    
    # test that the API key exists
    if os.getenv("OPENAI_API_KEY") is None or os.getenv("OPENAI_API_KEY") == "":
        print("OPENAI_API_KEY is not set")
        exit(1)
    else:
        #print("OPENAI_API_KEY is set")
        pass

    # setup streamlit page
    st.set_page_config(
        page_title="Fast & Slow"
    )

    if "instructions" not in st.session_state:
        st.session_state.instructions = ""

    if "prev_option" not in st.session_state:
        st.session_state.prev_option = "gpt4"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agents" not in st.session_state:
        st.session_state.agents = Fast_Agents(st.session_state.instructions)

        # update chat history
        st.session_state.messages = st.session_state.agents.parse_chat_history_into_streamlit_chat_format()




    
    
def main():
    with st.sidebar:
        st.title("Fast & Slow💬")
        
        # model selection
        if option := st.selectbox(
                "Choose Tryal Agent",
                ("fast_and_slow", "gpt4_CoT", "gpt4"),
                index=2,
                placeholder="Select contact method...",
            ):

            if st.session_state.prev_option != option:
                st.session_state.prev_option = option

                # change current chain
                st.session_state.agents.set_chain(option)

                # update chat history
                st.session_state.messages = st.session_state.agents.parse_chat_history_into_streamlit_chat_format()

                st.session_state.instructions = ""

        # show instruction 
        st.subheader("Instructions")

        # ***************************************************************************
        #***************** TODO : MUST FIX HERE *************************************
        # ***************************************************************************

        # update instaruction
        st.session_state.instructions = st.session_state.agents.get_instruction_latest_history()

        st.write(f"{st.session_state.instructions}")



    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Agentにメッセージを送る"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            input = {"input": st.session_state.messages[-1]["content"]}  
            contents = {"input": input["input"], "instruction": st.session_state.instructions} if (st.session_state.agents.current_chain_with_mem_name == "fast_and_slow") else {"input": input["input"]}
                      
            with st.spinner(""):
                # Stream
                for s in st.session_state.agents.current_chain_with_mem["data"]["chain"].stream(contents):        
                    full_response += s
                    message_placeholder.markdown(full_response)

            #message_placeholder.markdown(full_response)
            st.session_state.agents.current_chain_with_mem["data"]["memory"].save_context(input, {"output": full_response})

    
        st.session_state.messages.append({"role": "assistant", "content": full_response})



if __name__ == "__main__":
    init()

    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
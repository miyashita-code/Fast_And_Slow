import sys
import os
import asyncio
import threading
import streamlit as st
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from uot_modules.uot import UoT
from uot_modules.item import Item
from uot_modules.chat_utils import check_open_answer

class UoTManager:
    def __init__(self):
        self.uot = None
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def setup_uot(self):
        item_names = ["腹痛がある", "不明(その他)", "靴下を探している", "服を探している", "不安", 
                      "怒り", "デイサービスの準備", "歯磨きをする", "ごみを捨てに行く", "外に行きたくない"]
        items = [Item(name, "", 1/len(item_names)) for name in item_names]
        self.uot = UoT(
            initial_items=items,
            n_extend_layers=3,
            n_question_candidates=4,
            n_max_pruning=3,
            lambda_=2,
            is_debug=False,
            unknown_reward_prob_ratio=0.1
        )
        self.uot.lock = asyncio.Lock()  # asyncio.Lock()を使用

    def run_coroutine(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    def extend(self):
        return self.run_coroutine(self.uot.extend())

    def get_question(self):
        return self.run_coroutine(self.uot.get_question())

    def answer(self, p_prime_y):
        return self.run_coroutine(self._async_answer(p_prime_y))

    async def _async_answer(self, p_prime_y):
        async with self.uot.lock:
            return await self.uot.answer(p_prime_y)

    def get_current_probabilities(self):
        return self.run_coroutine(self.uot.get_current_probabilities())

def init():
    load_dotenv()
    st.set_page_config(page_title="UoT Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "uot_manager" not in st.session_state:
        st.session_state.uot_manager = UoTManager()
        st.session_state.uot_manager.setup_uot()
        st.session_state.first_question = True
        st.session_state.waiting_for_answer = False
        st.session_state.conversation_ended = False
        st.session_state.current_question = None
        st.session_state.extend_task = st.session_state.uot_manager.extend()

    if "is_p_y_done" not in st.session_state:
        st.session_state.is_p_y_done = False

    if "last_prompt" not in st.session_state:
        st.session_state.last_prompt = None

def main():
    with st.sidebar:
        st.title("UoT Chat")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if st.session_state.first_question:
        message = "状況整理のために、少しだけ質問してもいいですか？"
        st.session_state.messages.append({"role": "assistant", "content": message})
        st.chat_message("assistant").markdown(message)
        st.session_state.first_question = False
        st.session_state.waiting_for_answer = True

    if not st.session_state.conversation_ended:
        prompt = st.chat_input("Agentにメッセージを送る")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.waiting_for_answer = False
            st.session_state.last_prompt = prompt
            st.rerun()

        if not st.session_state.waiting_for_answer:
            with st.spinner("質問を生成中..."):
                if st.session_state.current_question is None:
                    st.session_state.uot_manager.extend()
                    st.session_state.current_question = st.session_state.uot_manager.get_question()

            if st.session_state.current_question:
                st.chat_message("assistant").markdown(f"{st.session_state.current_question}")
                st.session_state.messages.append({"role": "assistant", "content": f"{st.session_state.current_question}"})
                st.session_state.waiting_for_answer = True

            if st.session_state.last_prompt:
                p_y = st.session_state.uot_manager.run_coroutine(check_open_answer(st.session_state.current_question, st.session_state.last_prompt))
                if p_y is not None:
                    st.session_state.is_p_y_done = True
                    st.session_state.last_prompt = None
                else:
                    st.session_state.waiting_for_answer = True
                    st.rerun()

        if st.session_state.is_p_y_done:
            st.session_state.uot_manager.answer(p_y)
            st.session_state.current_question = None

            probabilities = st.session_state.uot_manager.get_current_probabilities()
            max_prob_item = max(probabilities, key=lambda x: x[1])

            if max_prob_item[1] > 0.5:
                message = f"{max_prob_item[0]}、これですね！"
                st.session_state.messages.append({"role": "assistant", "content": message})
                st.chat_message("assistant").markdown(message)
                st.balloons()
                st.session_state.conversation_ended = True
            else:
                st.session_state.waiting_for_answer = False

            # 現在の確率分布を表示
            st.sidebar.write("現在の確率分布:")
            for item, prob in probabilities:
                st.sidebar.write(f"{item}: {prob:.4f}")

            st.session_state.is_p_y_done = False
            st.rerun()

if __name__ == "__main__":
    init()
    main()

import tiktoken

from itertools import zip_longest

from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser, messages_to_dict
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnableLambda, RunnablePassthrough


from operator import itemgetter


from prompts.chat_prompt import fast_and_slow_sys_template, gpt_cot_pander_sys_template, gpt4_cot_response_sys_template, gpt4_sys_template


class Fast_Agents:
    def __init__(self, instructions : str):
        fast_and_slow_chain_with_mem, gpt4_CoT_chain_with_mem, gpt4_chain_with_mem = self.make_chains()
        self.chains_with_mem = {"fast_and_slow": fast_and_slow_chain_with_mem, "gpt4_CoT": gpt4_CoT_chain_with_mem, "gpt4": gpt4_chain_with_mem}
        self.current_chain_with_mem = self.chains_with_mem["gpt4"]
        self.instructions = instructions

        # for debug
        self.current_chain_with_mem_name = "gpt4"

    def make_chains(self):
        """
        make chain instances for fast_and_slow agent system, gpt4_2_gpt4 agent system, gpt4 agent system

        Returns
        -------
        fast_and_slow_chain : dict
            chain for fast_and_slow agent system : pipeline for the cooporation of fast_dialog_agent and Auto-GPT base slow backend agent.

        gpt4_Cot_chain: dict
            chain for gpt4_2_gpt4 simple CoT system : pipeline for simple CoT dialogue agent.

        gpt4_chain: dict
            chain for gpt4 agent system : normal gpt-4 based dialogue agent.
        """

        # make a chain for fast_and_slow agent system
        gpt4_model = ChatOpenAI(model="gpt-4-1106-preview")
        #gpt3_5_turbo_model = ChatOpenAI(model="gpt-3.5-turbo")
        model_paser = gpt4_model | StrOutputParser()
        #model_paser = gpt3_5_turbo_model | StrOutputParser()


        fast_and_slow_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", fast_and_slow_sys_template),
                    MessagesPlaceholder(variable_name="history"),
                    ("user", "{input}"),
                ]
            )
        

        memory_for_fast_and_slow = ConversationBufferMemory(return_messages=True)
        memory_for_fast_and_slow.save_context({"input": ""}, {"output": "こんにちわ。いかがなさいましたか？"})
        
        fast_and_slow_chain = (
            RunnablePassthrough.assign(
                history=RunnableLambda(memory_for_fast_and_slow.load_memory_variables) | itemgetter("history")
            )
            | fast_and_slow_prompt 
            | model_paser
        )

        # make a chain for gpt4_2_gpt4 agent system
        gpt4_CoT_pander_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", gpt_cot_pander_sys_template),
                    MessagesPlaceholder(variable_name="history"),
                    ("user", "{input}"),
                ]
            )


        gpt4_CoT_response_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", gpt4_cot_response_sys_template),
                    MessagesPlaceholder(variable_name="history"),
                    ("user", "{input}"),
                ]
            )

        memory_for_gpt4_CoT_instruction = ConversationBufferMemory(return_messages=True)
        memory_for_gpt4_CoT_main = ConversationBufferMemory(return_messages=True)
        memory_for_gpt4_CoT_main.save_context({"input": ""}, {"output": "こんにちわ。いかがなさいましたか？"})


        def _get_CoT_whole_mem(input):
            mem1 = memory_for_gpt4_CoT_instruction.load_memory_variables(input)["history"]
            mem2 = memory_for_gpt4_CoT_main.load_memory_variables(input)["history"]
            mem = []

            for item1, item2 in zip_longest(mem1, mem2):
                if item1 is not None:
                    mem.append(item1)
                if item2 is not None:
                    mem.append(item2)

            return {"history": mem}

        def _save_instruction(_dict : dict):
            memory_for_gpt4_CoT_instruction.save_context({"input" : _dict["input"]}, {"output": _dict["instruction"]})

            return _dict



        def debug_print(_str : str):
            print("*"*5 +  + _str + "*"*5 + "\n\n")
            return _str

        gpt4_CoT_pander_chain = (
            RunnablePassthrough.assign(
                history=RunnableLambda(_get_CoT_whole_mem) | itemgetter("history")
            )
            | gpt4_CoT_pander_prompt 
            | model_paser
            #| RunnableLambda(debug_print)
        )


        gpt4_CoT_chain = (
            {"instruction" : gpt4_CoT_pander_chain, "input" : itemgetter("input")} 
            | RunnableLambda(_save_instruction)
            | RunnablePassthrough.assign(
                history=RunnableLambda(_get_CoT_whole_mem) | itemgetter("history")
            )
            | gpt4_CoT_response_prompt 
            | model_paser
            #| RunnableLambda(debug_print)
        )

        # make a chain for gpt4 agent system
        gpt4_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", gpt4_sys_template),
                    MessagesPlaceholder(variable_name="history"),
                    ("user", "{input}"),
                ]
            )

        memory_for_gpt4 = ConversationBufferMemory(return_messages=True)
        memory_for_gpt4.save_context({"input": ""}, {"output": "こんにちわ。いかがなさいましたか？"})
        
        gpt4_chain = (
            RunnablePassthrough.assign(
                history=RunnableLambda(memory_for_gpt4.load_memory_variables) | itemgetter("history")
            )
            | gpt4_prompt 
            | model_paser
        )


        return (
            {
                "data" : {
                    "chain": fast_and_slow_chain, 
                    "memory": memory_for_fast_and_slow
                },
                
                "is_multi_mem" : False,
            },
            {
                "data" : {
                    "chain": gpt4_CoT_chain, 
                    "memory": memory_for_gpt4_CoT_main,
                    "memory_instruction" : memory_for_gpt4_CoT_instruction,
                },
                
                "is_multi_mem" : True,
            },
            {
                "data" : {
                    "chain": gpt4_chain, 
                    "memory": memory_for_gpt4
                },
                
                "is_multi_mem" : False,
            }
        )


    def set_chain(self, chain_name : str):
        """
        set current chain

        Parameters
        ----------
        chain_name : str
            name of the chain to set : must be one of "fast_and_slow", "gpt4_CoT", "gpt4"
        """
        try:
            self.current_chain_with_mem = self.chains_with_mem[chain_name]
            self.current_chain_with_mem_name = chain_name

        except KeyError:
            print("chain_name is not valid. temporarily set to gpt4_chain")
            self.current_chain_with_mem = self.chains_with_mem["gpt4"]
            self.current_chain_with_mem_name = "gpt4"
    
    def parse_chat_history_into_streamlit_chat_format(self) -> list:
        """
        parse history of the current chain into the streamlit chat format

        Returns
        -------
        history : list
            list of history of the current chain
        """
        streamlit_chat_history = []

        for history_dict in messages_to_dict(self.current_chain_with_mem["data"]["memory"].load_memory_variables({})["history"]):
            if history_dict["type"] == "human" and history_dict["data"]["content"] != "":
                streamlit_chat_history.append({"role": "user", "content": history_dict["data"]["content"]})
            elif history_dict["type"] == "ai" and history_dict["data"]["content"] != "":
                streamlit_chat_history.append({"role": "assistant", "content": history_dict["data"]["content"]})
            


        return streamlit_chat_history


    def get_instruction_latest_history(self) -> str:
        """
        get instruction of the current chain

        Returns
        -------
        instruction : str
            instruction of the current chain
        """

        if not self.current_chain_with_mem["is_multi_mem"]:
            return ""
        
        instruction_history = messages_to_dict(self.current_chain_with_mem["data"]["memory_instruction"].load_memory_variables({})["history"])

        if len(instruction_history) == 0:
            return ""

        return instruction_history[-1]["data"]["content"]


        



    
from __future__ import annotations

from typing import List, Optional

import langchain.globals

from langchain_openai import ChatOpenAI
from langchain.chains.llm import LLMChain
from langchain_core.language_models import BaseChatModel
from langchain.memory import ChatMessageHistory
from langchain.schema import (
    BaseChatMessageHistory,
    Document,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.vectorstores import VectorStoreRetriever
from langchain.tools.base import BaseTool
from langchain_community.tools.human.tool import HumanInputRun
from langchain.agents import load_tools

from langchain_experimental.autonomous_agents.autogpt.output_parser import (
    AutoGPTOutputParser,
    BaseAutoGPTOutputParser,
)
from langchain_experimental.autonomous_agents.autogpt.prompt import AutoGPTPrompt
from langchain_experimental.autonomous_agents.autogpt.prompt_generator import (
    FINISH_NAME,
)
from langchain_experimental.pydantic_v1 import ValidationError

# Lang chain側のインポート
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from langchain.memory import VectorStoreRetrieverMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate


import faiss

from langchain_community.docstore import InMemoryDocstore
from langchain_community.vectorstores import FAISS

from dotenv import load_dotenv

from autogpt_modules.custom_tools import (
    Pander_Dialog_State,
    Get_Individual_Care_Info_From_DB,
    Updata_Instructions,
    Do_Nothing
)

load_dotenv()




class AutoGPT:
    """Agent class for interacting with Auto-GPT."""

    def __init__(
        self,
        ai_name: str,
        memory: VectorStoreRetriever,
        chain: LLMChain,
        output_parser: BaseAutoGPTOutputParser,
        tools: List[BaseTool],
        feedback_tool: Optional[HumanInputRun] = None,
        chat_history_memory: Optional[BaseChatMessageHistory] = None,
    ):
        self.ai_name = ai_name
        self.memory = memory
        self.next_action_count = 0
        self.chain = chain
        self.output_parser = output_parser
        self.tools = tools
        self.feedback_tool = feedback_tool
        self.chat_history_memory = chat_history_memory or ChatMessageHistory()


    @classmethod
    def from_llm_and_tools(
        cls,
        ai_name: str,
        ai_role: str,
        memory: VectorStoreRetriever,
        tools: List[BaseTool],
        llm: BaseChatModel,
        human_in_the_loop: bool = False,
        output_parser: Optional[BaseAutoGPTOutputParser] = None,
        chat_history_memory: Optional[BaseChatMessageHistory] = None,
    ) -> AutoGPT:
        prompt = AutoGPTPrompt(
            ai_name=ai_name,
            ai_role=ai_role,
            tools=tools,
            input_variables=["memory", "messages", "goals", "user_input"],
            token_counter=llm.get_num_tokens,
        )
        human_feedback_tool = HumanInputRun() if human_in_the_loop else None
        chain = LLMChain(llm=llm, prompt=prompt)

        # for debug turn on verbose
        langchain.globals.set_verbose(True)
        chain.verbose = True 

        return cls(
            ai_name,
            memory,
            chain,
            output_parser or AutoGPTOutputParser(),
            tools,
            feedback_tool=human_feedback_tool,
            chat_history_memory=chat_history_memory,
        )


    def run(self, goals: List[str]) -> str:
        user_input = (
            "Determine which next command to use, "
            "and respond using the format specified above:"
        )
        # Interaction Loop
        loop_count = 0
        while True:
            # Discontinue if continuous limit is reached
            loop_count += 1
            
            # update chat history count
            self.current_size_chat_history = len(self.chat_history_memory.messages)


            # Send message to AI, get response
            input_dict = {
                "goals": goals,
                "messages": self.chat_history_memory.messages,
                "memory": self.memory,
                "user_input": user_input
            }

            # If you have additional configurations, create a RunnableConfig object
            # config = RunnableConfig(callbacks=my_callbacks, tags=["tag1", "tag2"], metadata={"key": "value"})

            # Make the invoke call
            assistant_reply = self.chain.invoke(input=input_dict)["text"]



            # Print Assistant thoughts
            print(assistant_reply)
            self.chat_history_memory.add_message(HumanMessage(content=user_input))
            self.chat_history_memory.add_message(AIMessage(content=assistant_reply))

            # Get command name and arguments
            action = self.output_parser.parse(assistant_reply)
            tools = {t.name: t for t in self.tools}

            if action.name == FINISH_NAME:
                return action.args["response"]

            # give dialog history to Pander_Dialog_State (custom tool : arg that name is dialog_data is just buffer when agent give the arg)
            if action.name == Pander_Dialog_State.get_tool_name():
                action.args["dialog_data"] = self.get_user_dialog_history()

            try:
                # execute wait
                if action.name == Do_Nothing.get_tool_name() and action.args["is_wait_untill_dialog_upadated"]:
                    # wait untill dialog is updated or 5sec passed
                    start_time = datetime.now()

                    while True:
                        if self.current_size_chat_history < len(self.chat_history_memory.messages):
                            break
                        elif (datetime.now() - start_time).seconds > Do_Nothing.TIMEOUT_SEC:
                            break

            except KeyError:
                pass
            
            
            if action.name in tools:
                tool = tools[action.name]
                try:
                    observation = tool.run(action.args)
                except ValidationError as e:
                    observation = (
                        f"Validation Error in args: {str(e)}, args: {action.args}"
                    )
                except Exception as e:
                    observation = (
                        f"Error: {str(e)}, {type(e).__name__}, args: {action.args}"
                    )
                result = f"Command {tool.name} returned: {observation}"
            elif action.name == "ERROR":
                result = f"Error: {action.args}. "
            else:
                result = (
                    f"*** DO NOT VIOLATE THESE RULES ***"
                    f"Unknown command '{action.name}', or illegal null command"
                    f"Please refer to the 'COMMANDS' list for available "
                    f"commands and only respond in the specified JSON format."
                    f"*** *** *** *** *** *** ***"
                )

            memory_to_add = (
                f"Assistant Reply: {assistant_reply} " f"\nResult: {result} "
            )
            if self.feedback_tool is not None:
                feedback = f"\n{self.feedback_tool.run('Input: ')}"
                if feedback in {"q", "stop"}:
                    print("EXITING")
                    return "EXITING"
                memory_to_add += feedback

            self.memory.add_documents([Document(page_content=memory_to_add)])
            self.chat_history_memory.add_message(SystemMessage(content=result))


    def get_user_dialog_history(self) -> str:

        ################################################################################
        ###                  TODO : user dialog history を取得する                    ###
        ################################################################################

        pass

        return "dialog history ..."

def main():

    # Define your embedding model
    embeddings = OpenAIEmbeddings()

    # Initialize the vectorstore as empty
    embedding_size = 1536
    # L2ノルム全探索用
    index = faiss.IndexFlatL2(embedding_size)
    vectorstore = FAISS(embeddings, index, InMemoryDocstore({}), {})

    retriever = vectorstore.as_retriever(search_kwargs=dict(k=5))
    memory = vectorstore.as_retriever()


    # init llm
    llm = ChatOpenAI(temperature=0, model="gpt-4-1106-preview")

    # load google search tool and custom tools
    tools = tools = load_tools(["serpapi"], llm=llm) + [Do_Nothing(), Updata_Instructions(), Pander_Dialog_State()]

    auto_gpt = AutoGPT.from_llm_and_tools(
        ai_name="認知症サポーター",
        ai_role="認知症患者の生活における意思決定支援や不安解消を行う情緒的なケアを行うエージェント",
        memory=memory,
        tools=tools,
        llm=llm,
    )


   
    # Set verbose to be true
    #langchain.globals.set_verbose(True)

    auto_gpt.run(goals=["対話の履歴から、適切な問題を設定する。", "よりよい応答のの方向性の決定を行う。"])





if __name__ == "__main__":
    main()
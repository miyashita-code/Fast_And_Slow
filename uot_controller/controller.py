from typing import Callable



from uot_modules import Item, UoT
from uot_modules import check_is_question_explained, check_is_answered_to_question
from neo4j_modules.care_kg_db import CareKgDB

class UoTController:
    def __init__(self, kg_db : CareKgDB, threshold : float = 0.7, is_debug : bool = False):
        self.kg = kg_db
        self.contexts = []
        self.is_on = False
        self.threshold = threshold
        self.state = None
        self.is_asked_question = False
        self.responses_buffer = []
        self.is_debug = is_debug

    def set_callbacks(self, callback : Callable, direct_prompting_func : Callable):
        self.callback = callback
        self.direct_prompting_func = direct_prompting_func

    def initialize_uot(self):
        kg_nodes = self.kg.get_uot_nodes()
        items = [Item(x['name'], x['description'], 1/len(kg_nodes)) for x in kg_nodes]
        localized_items = self.__localize_probs_with_context(items)

        self.state = UoTControllerState()

        self.uot = UoT(
            initial_items=localized_items,
            n_extend_layers=3,
            n_question_candidates=4,
            n_max_pruning=3,
            lambda_=20,
            is_debug=self.is_debug,
            unknown_reward_prob_ratio=0.3,
            get_grobal_context=self.get_grobal_context_as_str
        )

    def get_grobal_context_as_str(self) -> str:
        return "\n".join(self.contexts)

    def __localize_probs_with_context(self, items : list[Item]) -> list[Item]:
        #TODO: implement this
        # getGrobalContexts
        # estimateProbabilities
        # formatItems
        return items

    def set_contexts(self, contexts : list[str]):
        self.contexts.extend(contexts)

    async def set_context(self, context : str):
        self.contexts.append(context)
        self.debug_print(f"<Set context> : {context}")
        await self.__deal_user_response(context)

    def set_mode(self, mode : bool):
        self.is_on = mode

    def get_mode(self):
        return self.is_on

    async def __deal_user_response(self, response : str):
        self.debug_print(f"<Deal user response> called : {response}")
        if self.state == None:
            self.debug_print(f"<Deal user response> : State is None")
            return
        
        if self.state.state != "wait_answer":
            self.debug_print(f"<Deal user response> : State is not wait_answer")
            return
        
        # 質問がAIによって説明されているかを確認
        if "assistant" in response and not self.is_asked_question:
            self.debug_print(f"<Deal user response> : AI assistant response, {response}")
            # Check if the response by the AI assistant include about the question
            result = await check_is_question_explained(response, self.best_question_candidate)
            self.debug_print(f"<Deal user response> : Check if the response by the AI assistant include about the question : {result}")
            # Store the way of asking the question
            self.real_question_asked = response

            if result:
                self.is_asked_question = True
            else:
                # Prompt the AI assistant to explain the question ASAP
                self.direct_prompting_func(f"次の質問について可能な限り早い段階で伺ってください. ただし対話の文脈を壊さないように少し言い方を変えても構いません. 質問 : {self.best_question_candidate}")
        elif "assistant" in response and self.is_asked_question:
            self.real_question_asked += response
        elif "user" in response and self.is_asked_question:
            self.debug_print(f"<Deal user response> : User response")
            self.responses_buffer.append(response)
            # Check if the response by the user is Answer to the question or not (yet).
            is_answered, answer_label, observed_prob_of_yes = await check_is_answered_to_question(self.responses_buffer, self.best_question_candidate, self.real_question_asked)
            self.debug_print(f"<Deal user response> : Check if the response by the user is Answer to the question or not (yet) : {is_answered}")
            if is_answered:
                self.responses_buffer = []

                # Go to next state
                self.observed_prob_of_yes = observed_prob_of_yes
                self.state.next()
                self.debug_print(f"<Deal user response> : Go to next state")

                self.is_asked_question = False
            else:
                # Prompt the AI assistant to explain the question ASAP
                self.direct_prompting_func(f"次の質問について可能な限り早い段階で伺ってください. すでに聞いている場合は, ゆっくりと傾聴し積極的に回答を引き出してください 質問 : {self.best_question_candidate}")

    def debug_print(self, text : str):
        if self.is_debug == None:
            return
        
        if self.is_debug:
            print(text)

    async def run(self, is_debug : bool = False):
        self.is_debug = is_debug
        self.is_on = True
        self.debug_print("<Run> called")

        # Initialize UoT nodes
        self.initialize_uot()
        self.debug_print("<Run> initialized UoT")

        # Run main loop
        while self.is_on:
            if self.uot.root.current_extended_depth == 0:
                self.debug_print("<Extending first layer>")
                await self.uot.extend()
                self.debug_print("<Extended first layer>")

                self.state.next()
            
            if self.state.state == "send_question":
                self.debug_print("<Sending question>")
                # Best question selection
                question = await self.uot.get_question()

                self.best_question_candidate = question

                # Send question to Client
                self.direct_prompting_func(f"Planing Systemから要請です. 次の質問について可能な限り早い段階で伺ってください. なお、内容が不自然な場合は文脈が壊れないように少し言い方を変えても構いません.** 質問 : {question}**")
                self.direct_prompting_func(question)

                self.debug_print(f"<Sent question> : question : {question}")

                # Update state
                self.state.next()
            #elif self.state.state == "wait_answer":
                # pass
            elif self.state.state == "evaluate_answer":
                self.debug_print("<Evaluating answer>")
                # Tree update
                await self.uot.answer(self.observed_prob_of_yes)

                self.__check_if_done(self.uot.root.get_best_prob_item())

                self.debug_print("<Evaluated answer>")

            # Check if another extension is needed
            if self.uot.root.children:
                await self.uot.extend()


    def __check_if_done(self, item : Item):
        if item.p_s > self.threshold:
            self.is_on = False
        else:
            self.state.next()


class UoTControllerState:
    def __init__(self):
        self.state = "idle"

    def next(self):
        if self.state == "idle" or self.state == "evaluate_answer":
            self.state = "send_question"
        elif self.state == "send_question":
            self.state = "wait_answer"
        elif self.state == "wait_answer":
            self.state = "evaluate_answer"
        else:
            raise ValueError("<UoTControllerState.next> : Invalid state")








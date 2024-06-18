import time
from langchain.tools.base import BaseTool



class DoNothing(BaseTool):
    """Tool that does nothing or just wait 100ms for waiting conversion's procedure."""

    name = "do_nothing_and_wait"
    description = (
        "Do nothing, and if is_wait_untill_dialog_upadated is True, wait untill dialog is updated."
        "Input is_wait_untill_dialog_upadated shold be a boolean value to decide wait or not."
    )


    
    def _do_nothing(self, is_wait_untill_dialog_upadated=False) -> str:
        """
        Do nothing, and if is_wait_untill_dialog_upadated is True, wait untill dialog is upadated uptp 5sec. 
        waiting process is executed in auto_gpt.py itself. 
        
        Args:
            is_delay_100ms (bool): If True, delay 100ms before returning.
        """

        return "No action performed." + ("waited untill dialog is updated." if is_wait_untill_dialog_upadated else "")

    
    def _run(self, is_wait_untill_dialog_upadated=False) -> str:
        return self._do_nothing(is_wait_untill_dialog_upadated)


    async def _arun(self, is_wait_untill_dialog_upadated=False) -> str:
        """Use the do_nothing asynchroneously."""
        return self._do_nothing(is_wait_untill_dialog_upadated)

    @classmethod
    def get_tool_name(cls) -> str:
        return "do_nothing_and_wait"

    @classmethod
    def get_wait_timeout_limit(cls) -> int:
        return 5 #(sec) TIMEOUT_SEC

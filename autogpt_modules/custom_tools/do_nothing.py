import time
from langchain.tools.base import BaseTool

class do_nothing(BaseTool):
    """Tool that does nothing or just wait 100ms for waiting conversion's procedure."""

    name = "do_nothing"
    description = (
        "Do nothing, and if is_delay_100ms is True, delay 100ms before returning."
        "Input shold be a boolean value to decide wait or not."
    )

    
    def _do_nothing(self, is_delay_100ms=False) -> str:
        """
        Do nothing, and if is_delay_100ms is True, delay 100ms before returning.
        
        Args:
            is_delay_100ms (bool): If True, delay 100ms before returning.
        """
        delay_message = ""

        if is_delay_100ms:
            time.sleep(0.1)
            delay_message = " (delayed 100ms)"

        return "No action performed." + delay_message

    
    def _run(self, is_delay_100ms=False) -> str:
        return self._do_nothing(is_delay_100ms)


    async def _arun(self, is_delay_100ms=False) -> str:
        """Use the do_nothing asynchroneously."""
        return self._do_nothing(is_delay_100ms)

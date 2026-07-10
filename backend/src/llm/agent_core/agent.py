import json
from openai import OpenAI
from typing import List, Optional
from openai import AsyncOpenAI
from src.core.config import settings
from src.llm.agent_core.constant import Constants
from src.llm.agent_core.tool import Tool


class Agent:

    def __init__(
        self,
        system_prompt: str,
        model: str = Constants.DEFAULT_MODEL,
        temperature: float = Constants.DEFAULT_TEMPERATURE,
        max_iteration: int = Constants.DEFAULT_MAX_ITERATION,
        max_tool_call: int = Constants.DEFAULT_MAX_TOOL_CALLS,
    ):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.client_async = AsyncOpenAI(api_key=settings.openai_api_key)
        self.system_prompt = system_prompt
        self.model = model
        self.temperature = temperature
        self.max_iteration = max_iteration
        self.max_tool_call = max_tool_call
        self.tools = {}

    def add_tool(self, tool: Tool):
        self.tools[tool.name] = tool

    def on_tool_result(self, tool_name: str, args: dict, result: dict):
        pass

    def _execute_tool(self, name: str, args: Optional[dict]):
        if args:
            return self.tools[name].execute(**args)
        return self.tools[name].execute()

    def _call_llm(self, chat_history: List[dict], stream: bool = False):
        return self.client.responses.create(
            model=self.model,
            temperature=self.temperature,
            input=chat_history,
            tools=[tool.schema() for tool in self.tools.values()],
            tool_choice="auto",
            stream=stream,
        )

    def _format_chat_history(self, chat_history: list[dict]) -> List[dict]:
        history = [
            {"role": "system", "content": self.system_prompt},
        ]
        if isinstance(chat_history, list):
            history.extend(chat_history)
        else:
            history.append(chat_history)

        return history

    def invoke(self, chat_history=None):
        if chat_history is None:
            chat_history = []
        chat_history = self._format_chat_history(chat_history)
        tool_calls = []

        for _ in range(self.max_iteration):
            response = self._call_llm(chat_history)
            assistant_text = ""

            for item in response.output:

                if item.type == "function_call":
                    tool_name = item.name
                    args = json.loads(item.arguments) if item.arguments else {}

                    tool_input = {
                        "type": "function_call",
                        "name": tool_name,
                        "arguments": json.dumps(args),
                        "call_id": item.call_id,
                    }
                    chat_history.append(tool_input)

                    result = self._execute_tool(tool_name, args)

                    self.on_tool_result(tool_name, args, result)

                    tool_output = {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                    chat_history.append(tool_output)
                    tool_calls.append({"input": tool_input, "output": tool_output})

                elif item.type == "message":
                    for part in item.content:
                        if part.type == "output_text":
                            assistant_text += part.text

            if assistant_text:
                return assistant_text, tool_calls

        return Constants.ERROR_GENERIC, tool_calls

    def stream(self, chat_history=None):
        if chat_history is None:
            chat_history = []
        chat_history = self._format_chat_history(chat_history)
        tool_calls = []
        final_text = ""

        for _ in range(self.max_iteration):
            if final_text or len(tool_calls) >= self.max_tool_call:
                break

            current_tool = None
            tool_args_buffer = ""

            with self._call_llm(chat_history=chat_history, stream=True) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        final_text += event.delta
                        yield {"type": "text", "data": event.delta}
                    elif event.type == "response.output_item.added":
                        item = event.item

                        if getattr(item, "type", None) == "function_call":
                            current_tool = {
                                "name": item.name,
                                "call_id": item.call_id,
                            }
                            tool_args_buffer = ""

                    elif event.type == "response.function_call_arguments.delta":
                        tool_args_buffer += event.delta or ""

                    elif event.type == "response.function_call_arguments.done":
                        if current_tool:
                            try:
                                args = (
                                    json.loads(tool_args_buffer)
                                    if tool_args_buffer
                                    else {}
                                )
                            except json.JSONDecodeError:
                                raise

                            result = self._execute_tool(current_tool["name"], args)
                            self.on_tool_result(current_tool["name"], args, result)

                            tool_input = {
                                "type": "function_call",
                                "name": current_tool["name"],
                                "arguments": tool_args_buffer or "{}",
                                "call_id": current_tool["call_id"],
                            }

                            tool_output = {
                                "type": "function_call_output",
                                "call_id": current_tool["call_id"],
                                "output": json.dumps(result),
                            }

                            chat_history.append(tool_input)
                            chat_history.append(tool_output)

                            tool_calls.append(
                                {
                                    "input": tool_input,
                                    "output": tool_output,
                                }
                            )

                            yield {"type": "tool_call", "data": tool_calls[-1]}

                            current_tool = None
                            tool_args_buffer = ""

                    elif event.type == "response.completed":
                        yield {
                            "type": "final",
                            "data": {
                                "assistant_text": final_text,
                                "tool_calls": tool_calls,
                            },
                        }

    async def _call_llm_async(self, chat_history: List[dict], stream: bool = False):
        return await self.client_async.responses.create(
            model=self.model,
            temperature=self.temperature,
            input=chat_history,
            tools=[tool.schema() for tool in self.tools.values()],
            tool_choice="auto",
            stream=stream,
        )

    async def astream(self, chat_history):
        if chat_history is None:
            chat_history = []
        chat_history = self._format_chat_history(chat_history)
        tool_calls = []
        final_text = ""

        for _ in range(self.max_iteration):
            if final_text or len(tool_calls) >= self.max_tool_call:
                break

            current_tool = None
            tool_args_buffer = ""

            async with self._call_llm_async(
                chat_history=chat_history, stream=True
            ) as stream:
                async for event in stream:
                    if event.type == "response.output_text.delta":
                        final_text += event.delta
                        yield {"type": "text", "data": event.delta}

                    elif event.type == "response.output_item.added":
                        if getattr(event.item, "type", None) == "function_call":
                            current_tool = {
                                "name": event.item.name,
                                "call_id": event.item.call_id,
                            }
                            tool_args_buffer = ""

                    elif event.type == "response.function_call_arguments.delta":
                        tool_args_buffer += event.delta or ""

                    elif event.type == "response.function_call_arguments.done":
                        args = json.loads(tool_args_buffer or "{}")
                        result = self._execute_tool(current_tool["name"], args)

                        tool_input = {
                            "type": "function_call",
                            "name": current_tool["name"],
                            "arguments": tool_args_buffer,
                            "call_id": current_tool["call_id"],
                        }

                        tool_output = {
                            "type": "function_call_output",
                            "call_id": current_tool["call_id"],
                            "output": json.dumps(result),
                        }

                        chat_history.append(tool_input)
                        chat_history.append(tool_output)

                        tool_calls.append({"input": tool_input, "output": tool_output})

                        yield {"type": "tool_call", "data": tool_calls[-1]}

                    elif event.type == "response.completed":
                        yield {
                            "type": "final",
                            "data": {
                                "assistant_text": final_text,
                                "tool_calls": tool_calls,
                            },
                        }

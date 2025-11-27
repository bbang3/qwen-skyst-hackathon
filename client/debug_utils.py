"""Debug utilities for printing tool calls and responses."""

import json
import re


def print_debug_info(output):
    """Print debugging information about tool calls and responses to terminal.

    Args:
        output: The RunResult output from Runner.run()
    """
    print("\n" + "=" * 80)
    print("🔍 DEBUG: Tool Calls & Responses")
    print("=" * 80)

    tool_calls_info = extract_tool_calls_info(output)
    if tool_calls_info:
        for i, tool_info in enumerate(tool_calls_info, 1):
            print(f"\n--- Tool Call #{i} ---")
            print(json.dumps(tool_info, indent=2, ensure_ascii=False))
    else:
        print("No tool calls detected in this response.")

    # Also print raw_responses if available
    if hasattr(output, "raw_responses") and output.raw_responses:
        print("\n--- Model Responses ---")
        for i, raw_response in enumerate(output.raw_responses, 1):
            print(f"\nResponse #{i}:")

            # Extract output from raw_response
            output_str = (
                str(raw_response.output)
                if hasattr(raw_response, "output")
                else str(raw_response)
            )

            # Check if it's a tool call
            if "ResponseFunctionToolCall" in output_str:
                print_tool_call(output_str)

            # Check if it's a regular message response
            elif (
                "ResponseOutputMessage" in output_str
                or "ResponseOutputText" in output_str
            ):
                print_text_response(output_str)

            else:
                # Fallback: print usage info if available
                if hasattr(raw_response, "usage"):
                    print(f"Usage: {raw_response.usage}")
                else:
                    print("(Unknown response type)")

    print("\n" + "=" * 80 + "\n")


def print_tool_call(output_str: str):
    """Print tool call information.

    Args:
        output_str: String representation of the tool call response.
    """
    # Extract tool name
    name_match = re.search(r"name='([^']+)'", output_str)
    tool_name = name_match.group(1) if name_match else "Unknown"

    # Extract arguments
    args_match = re.search(r"arguments='([^']+)'", output_str)
    if args_match:
        args_str = args_match.group(1)
        try:
            args_dict = json.loads(args_str)
            print(f"Tool: {tool_name}")
            print("Arguments:")
            print(json.dumps(args_dict, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(f"Tool: {tool_name}")
            print(f"Arguments: {args_str}")
    else:
        print(f"Tool: {tool_name}")
        print("Arguments: (not found)")


def print_text_response(output_str: str):
    """Print text response information.

    Args:
        output_str: String representation of the text response.
    """
    # Try to extract text from ResponseOutputText
    text_match = re.search(r"text='([^']+)'", output_str)
    if text_match:
        text = text_match.group(1)
        print(f"Text: {text}")
    else:
        # Fallback: try to find text in a different format
        text_match = re.search(r'text="([^"]+)"', output_str)
        if text_match:
            text = text_match.group(1)
            print(f"Text: {text}")
        else:
            print("Text: (could not extract)")


def extract_tool_calls_info(output) -> list[dict]:
    """Extract tool call information from the agent output.

    Args:
        output: The RunResult output from Runner.run()

    Returns:
        list[dict]: List of tool call information dictionaries.
    """
    tool_calls_info = []

    if not hasattr(output, "new_items"):
        return tool_calls_info

    for item in output.new_items:
        item_dict = {}

        # Check if this is a tool call item
        if hasattr(item, "type"):
            # Tool call request
            if hasattr(item, "function") or hasattr(item, "tool_call_id"):
                item_dict["type"] = "tool_call"
                item_dict["tool_call_id"] = getattr(item, "tool_call_id", None)

                if hasattr(item, "function"):
                    func = getattr(item, "function", None)
                    if func:
                        item_dict["function_name"] = getattr(func, "name", None)
                        item_dict["function_arguments"] = getattr(
                            func, "arguments", None
                        )
                        # Try to parse arguments as JSON if it's a string
                        if isinstance(item_dict["function_arguments"], str):
                            try:
                                item_dict["function_arguments"] = json.loads(
                                    item_dict["function_arguments"]
                                )
                            except json.JSONDecodeError:
                                pass

            # Tool call response
            elif hasattr(item, "content") and hasattr(item, "tool_call_id"):
                item_dict["type"] = "tool_response"
                item_dict["tool_call_id"] = getattr(item, "tool_call_id", None)
                item_dict["content"] = getattr(item, "content", None)

            # Try to get any other useful attributes
            if item_dict:
                # Convert item to dict if possible
                try:
                    if hasattr(item, "__dict__"):
                        item_dict["raw_item"] = {
                            k: str(v)
                            for k, v in item.__dict__.items()
                            if k not in ["function", "tool_call_id", "content", "type"]
                        }
                except Exception:
                    pass

                tool_calls_info.append(item_dict)

    return tool_calls_info


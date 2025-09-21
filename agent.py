#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p "python3.withPackages(ps: with ps; [ anthropic tenacity ])"
import os
import subprocess
from typing import Optional
import argparse
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import anthropic
from anthropic import RateLimitError, APIError

def main():
    parser = argparse.ArgumentParser(description='LLM Agent with configurable prompt file')
    parser.add_argument('--prompt-file', type=str, default='prompt.md',
                      help='Path to the prompt file (default: prompt.md)')
    parser.add_argument('-e', '--exit', dest='exit_after_response', action='store_true',
                      help='Exit after the first agent turn instead of prompting for input')
    parser.add_argument('-t', '--task', type=str,
                      help='Initial user input/task to start the conversation')
    parser.add_argument('-m', '--model', type=str, default='claude-3-7-sonnet-latest',
                      help='Model to use (default: claude-3-7-sonnet-latest)')
    # validation command 
    parser.add_argument('-v', '--validate', type=str,
                      help='Validate the command', default='! git rev-parse -q --verify REBASE_HEAD >/dev/null')
    args = parser.parse_args()
    
    try:
        print("\n=== LLM Agent Loop with Claude and Bash Tool ===\n")
        print("Type 'exit' to end the conversation.\n")
        loop(
            LLM("claude-3-7-sonnet-latest", args.prompt_file),
            initial_task=args.task,
            exit_after_first=args.exit_after_response,
            validate_command=args.validate,
        )
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")

def loop(llm, initial_task: Optional[str] = None, exit_after_first: bool = False, validate_command: Optional[str] = None):
    def run_validation(cmd: Optional[str]):
        if not cmd:
            return True, ""
        try:
            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            formatted = (
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}\n"
                f"EXIT CODE: {result.returncode}"
            )
            return result.returncode == 0, formatted
        except Exception as e:
            return False, f"Error executing validation command: {str(e)}"

    def build_validation_failure_message(cmd: str, output_text: str) -> list:
        prompt_text = (
            "Validation command failed. You must continue until it succeeds with exit code 0.\n\n"
            f"Command: {cmd}\n\n"
            f"Output:\n{output_text}\n\n"
            "Please diagnose and take further actions (use the bash tool) "
            "to make the validation command succeed."
        )
        return [{"type": "text", "text": prompt_text}]

    awaiting_validation_exit = False

    if initial_task is not None:
        msg = [{"type": "text", "text": initial_task}]
    else:
        if exit_after_first:
            ok, out = run_validation(validate_command)
            if ok:
                print("\nExiting due to -e/--exit flag before prompting for input.")
                return
            print("\nValidation failed; continuing the agent loop.")
            msg = build_validation_failure_message(validate_command or "", out)
            awaiting_validation_exit = True
        else:
            msg, exit_requested = user_input()
            if exit_requested:
                ok, out = run_validation(validate_command)
                if ok:
                    print("\nExiting agent loop. Goodbye!")
                    return
                print("\nValidation failed; continuing the agent loop.")
                msg = build_validation_failure_message(validate_command or "", out)
                awaiting_validation_exit = True

    while True:
        output, tool_calls = llm(msg)
        print("Agent: ", output)
        if tool_calls:
            msg = [ handle_tool_call(tc) for tc in tool_calls ]
            # After tool execution, if we are awaiting validation, re-check now
            if awaiting_validation_exit:
                ok, out = run_validation(validate_command)
                if ok:
                    print("\nValidation succeeded. Exiting.")
                    break
                msg = build_validation_failure_message(validate_command or "", out)
        else:
            if exit_after_first and not awaiting_validation_exit:
                ok, out = run_validation(validate_command)
                if ok:
                    print("\nExiting due to -e/--exit flag.")
                    break
                print("\nValidation failed; continuing the agent loop.")
                msg = build_validation_failure_message(validate_command or "", out)
                awaiting_validation_exit = True
            else:
                if awaiting_validation_exit:
                    ok, out = run_validation(validate_command)
                    if ok:
                        print("\nValidation succeeded. Exiting.")
                        break
                    msg = build_validation_failure_message(validate_command or "", out)
                else:
                    msg, exit_requested = user_input()
                    if exit_requested:
                        ok, out = run_validation(validate_command)
                        if ok:
                            print("\nExiting agent loop. Goodbye!")
                            break
                        print("\nValidation failed; continuing the agent loop.")
                        msg = build_validation_failure_message(validate_command or "", out)
                        awaiting_validation_exit = True


bash_tool = {
    "name": "bash",
    "description": "Execute bash commands and return the output",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute"
            }
        },
        "required": ["command"]
    }
}

# Function to execute bash commands
def execute_bash(command):
    """Execute a bash command and return a formatted string with the results."""
    # If we have a timeout exception, we'll return an error message instead
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nEXIT CODE: {result.returncode}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def user_input():
    x = input("You: ")
    if x.lower() in ["exit", "quit"]:
        return ([{"type": "text", "text": ""}], True)
    return ([{"type": "text", "text": x}], False)

class LLM:
    def __init__(self, model, prompt_file):
        if "ANTHROPIC_API_KEY" not in os.environ:
            raise ValueError("ANTHROPIC_API_KEY environment variable not found.")
        self.client = anthropic.Anthropic()
        self.model = model
        self.messages = []
        # read prompt file from provided path
        with open(prompt_file, 'r') as f:
            prompt = f.read()
        self.system_prompt = """You are a helpful AI assistant with access to bash commands.
        You can help the user by executing commands and interpreting the results.
        Be careful with destructive commands and always explain what you're doing.
        You have access to the bash tool which allows you to run shell commands.\n\n""" + prompt
        self.tools = [bash_tool]

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def _call_anthropic(self):
        return self.client.messages.create(
            model=self.model,
            max_tokens=20_000,
            system=self.system_prompt,
            messages=self.messages,
            tools=self.tools
        )

    def __call__(self, content):
        self.messages.append({"role": "user", "content": content})
        self.messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
        try:
            response = self._call_anthropic()
        except (RateLimitError, APIError) as e:
            print(f"\nRate limit or API error occurred: {str(e)}")
            raise
        finally:
            del self.messages[-1]["content"][-1]["cache_control"]
        assistant_response = {"role": "assistant", "content": []}
        tool_calls = []
        output_text = ""

        for content in response.content:
            if content.type == "text":
                text_content = content.text
                output_text += text_content
                assistant_response["content"].append({"type": "text", "text": text_content})
            elif content.type == "tool_use":
                assistant_response["content"].append(content)
                tool_calls.append({
                    "id": content.id,
                    "name": content.name,
                    "input": content.input
                })

        self.messages.append(assistant_response)
        return output_text, tool_calls

def handle_tool_call(tool_call):
    if tool_call["name"] != "bash":
        raise Exception(f"Unsupported tool: {tool_call['name']}")

    command = tool_call["input"]["command"]
    print(f"Executing bash command: {command}")
    output_text = execute_bash(command)
    print(f"Bash output:\n{output_text}")
    return dict(
        type="tool_result",
        tool_use_id=tool_call["id"],
        content=[dict(
            type="text",
            text=output_text
        )]
    )

if __name__ == "__main__":
    main()
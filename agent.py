#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p "python3.withPackages(ps: with ps; [ anthropic ])"
import os
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Union
import argparse
import difflib
import tempfile
import re

import anthropic

def main():
    parser = argparse.ArgumentParser(description='LLM Agent with configurable prompt file')
    parser.add_argument('--prompt-file', type=str, default='prompt.md',
                      help='Path to the prompt file (default: prompt.md)')
    args = parser.parse_args()
    
    try:
        print("\n=== LLM Agent Loop with Claude and Bash Tool ===\n")
        print("Type 'exit' to end the conversation.\n")
        loop(LLM("claude-3-7-sonnet-latest", args.prompt_file))
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")

def loop(llm):
    msg = user_input()
    while True:
        output, tool_calls = llm(msg)
        print("Agent: ", output)
        if tool_calls:
            msg = [ handle_tool_call(tc) for tc in tool_calls ]
        else:
            msg = user_input()


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

write_diff_tool = {
    "name": "apply_patch",
    "description": "Apply a patch/diff to a file using Python's difflib",
    "input_schema": {
        "type": "object",
        "properties": {
            "target_file": {
                "type": "string",
                "description": "The path of the file to apply the patch to"
            },
            "patch_content": {
                "type": "string",
                "description": "The patch/diff content to apply in unified diff format"
            }
        },
        "required": ["target_file", "patch_content"]
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

def parse_unified_diff(patch_content: str) -> list[tuple[str, str]]:
    """Parse a unified diff into a list of (line_type, content) tuples.
    Line types are: 'context', 'add', 'remove'"""
    changes = []
    current_hunk = []
    in_hunk = False
    
    for line in patch_content.splitlines():
        if line.startswith('@@'):
            if in_hunk:
                changes.extend(current_hunk)
                current_hunk = []
            in_hunk = True
            continue
            
        if in_hunk:
            if line.startswith(' '):
                current_hunk.append(('context', line[1:]))
            elif line.startswith('+'):
                current_hunk.append(('add', line[1:]))
            elif line.startswith('-'):
                current_hunk.append(('remove', line[1:]))
            elif line.startswith('\\'):
                # Handle \ No newline at end of file
                continue
            else:
                # End of hunk
                changes.extend(current_hunk)
                current_hunk = []
                in_hunk = False
    
    if current_hunk:
        changes.extend(current_hunk)
    return changes

def apply_patch_to_file(target_file: str, patch_content: str) -> str:
    """Apply a patch to a file using Python's difflib and return a status message."""
    try:
        # Read the current file content
        with open(target_file, 'r') as f:
            original_lines = f.readlines()
        
        # Parse the patch content
        changes = parse_unified_diff(patch_content)
        
        # Apply the changes
        new_lines = []
        i = 0
        for change_type, content in changes:
            if change_type == 'context':
                if i < len(original_lines) and original_lines[i].rstrip('\n') == content:
                    new_lines.append(original_lines[i])
                    i += 1
                else:
                    return f"Error: Context mismatch at line {i+1}. Expected '{content}', got '{original_lines[i].rstrip() if i < len(original_lines) else 'EOF'}'"
            elif change_type == 'add':
                new_lines.append(content + '\n')
            elif change_type == 'remove':
                if i < len(original_lines) and original_lines[i].rstrip('\n') == content:
                    i += 1
                else:
                    return f"Error: Cannot remove line {i+1}. Expected '{content}', got '{original_lines[i].rstrip() if i < len(original_lines) else 'EOF'}'"
        
        # Add any remaining lines
        new_lines.extend(original_lines[i:])
        
        # Write the modified content back to the file
        with open(target_file, 'w') as f:
            f.writelines(new_lines)
            
        return f"Successfully applied patch to {target_file}"
    except Exception as e:
        return f"Error applying patch: {str(e)}"

def user_input():
    x = input("You: ")
    if x.lower() in ["exit", "quit"]:
        print("\nExiting agent loop. Goodbye!")
        raise SystemExit(0)
    return [{"type": "text", "text": x}]

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
        self.system_prompt = """You are a helpful AI assistant with access to bash commands and can apply patches to files.
        You can help the user by executing commands, applying patches to files, and interpreting the results.
        Be careful with destructive commands and always explain what you're doing.
        You have access to the bash tool which allows you to run shell commands and the apply_patch tool to modify files using patches.\n\n""" + prompt
        self.tools = [bash_tool, write_diff_tool]

    def __call__(self, content):
        self.messages.append({"role": "user", "content": content})
        self.messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
        response = self.client.messages.create(
            model=self.model,
            max_tokens=20_000,
            system=self.system_prompt,
            messages=self.messages,
            tools=self.tools
        )
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
    if tool_call["name"] == "bash":
        command = tool_call["input"]["command"]
        print(f"Executing bash command: {command}")
        output_text = execute_bash(command)
        print(f"Bash output:\n{output_text}")
    elif tool_call["name"] == "apply_patch":
        target_file = tool_call["input"]["target_file"]
        patch_content = tool_call["input"]["patch_content"]
        print(f"Applying patch to file: {target_file}")
        output_text = apply_patch_to_file(target_file, patch_content)
        print(f"Patch application output:\n{output_text}")
    else:
        raise Exception(f"Unsupported tool: {tool_call['name']}")

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
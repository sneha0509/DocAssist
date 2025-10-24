import os
from openai import AzureOpenAI

def analyse_metadata():
    # Environment variables for Azure OpenAI
    endpoint = os.getenv("ENDPOINT_URL")
    deployment = os.getenv("DEPLOYMENT_NAME")
    subscription_key = os.getenv("AZURE_OPENAI_API_KEY")

    # Initialize Azure OpenAI client
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2025-01-01-preview",
    )

    # Read metadata content
    SRC_DIR = r"result\metadata.json"
    with open(SRC_DIR, "r", encoding="utf-8") as file:
        metadata_content = file.read()

    # Read instruction content
    Instr_File = r"instruction.txt"
    with open(Instr_File, "r", encoding="utf-8") as f:
        instr_content = f.read()

    # Prepare chat prompt
    chat_prompt = [
        {"role": "system", "content": instr_content},
        {
            "role": "developer",
            "content": [
                {
                    "type": "text",
                    "text": "Generate comprehensive Markdown documentation from provided metadata of multiple source files, including architecture, APIs, configuration, and usage examples. Ensure accuracy, professional tone, and structured sections based strictly on metadata without speculation."
                }
            ]
        },
        {"role": "user", "content": [{"type": "text", "text": metadata_content}]}
    ]

    # Generate completion
    completion = client.chat.completions.create(
        model=deployment,
        messages=chat_prompt,
        max_completion_tokens=13107,
        stop=None,
        stream=False
    )

    # Write response to TXT file
    output_file = r"result\documentation_output.txt"
    with open(output_file, "w", encoding="utf-8") as out_file:
        for choice in completion.choices:
            print("Response:", choice.message.content)  # Console output
            out_file.write(choice.message.content + "\n\n")  # Save to file

    print(f"Documentation written to: {output_file}")

if __name__ == "__main__":
    analyse_metadata()

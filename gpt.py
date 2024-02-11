from openai import OpenAI

client = OpenAI()

def make_reply(email, context=""):
    system_message = "You are an automatic email replyer. Write a response to the given email conversation. Respond only with the reply email, nothing else."

    if context:
        system_message += "\n\n" + "This is your current knowledge as an assistant. Adhere to these rules when creating your response:\n\n" + context

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": email
            }
        ]
    )

    response_message = response.choices[0].message
    message_content = response_message.content

    return message_content


if __name__ == "__main__":
    reply = make_reply("Hello!\nI would like to book an appointment for a meeting\n\nBest,\nMe")
    print(reply)

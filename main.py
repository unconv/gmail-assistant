from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import pickle
import base64
import email
import time
import sys
import os

import gpt

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid',
]


def get_services():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return {
        "gmail": build('gmail', 'v1', credentials=creds),
        "people": build('people', 'v1', credentials=creds),
    }


def get_user_info(service):
    """
    Fetches the user's name and email address.

    Args:
    service: Authorized People API service instance.

    Returns:
    A dictionary containing the user's name and email address.
    """
    profile = service.people().get(resourceName='people/me', personFields='names,emailAddresses').execute()
    name = profile['names'][0]['displayName']
    email = profile['emailAddresses'][0]['value']
    return {"name": name, "email": email}


def create_message(sender, to, subject, message_text, headers=None):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    if headers:
        for name, value in headers.items():
            message[name] = value
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}


def send_message(service, message):
    message = service.users().messages().send(userId='me', body=message).execute()
    print(f"Sent message: {message['id']}")
    return message


def get_message_body(message):
    msg_raw = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
    msg_str = email.message_from_bytes(msg_raw)

    # If message is multipart, the parts are in .get_payload()
    if msg_str.is_multipart():
        for part in msg_str.walk():
            if part.get_content_type() == 'text/plain':
                # We use get_payload(decode=True) to decode the base64 string
                body = part.get_payload(decode=True).decode()
                return body
    else:
        # If message is not multipart, simply decode
        body = msg_str.get_payload(decode=True).decode()
        return body


def mark_message_as_read(service, msg_id):
    """
    Marks the specified message as read by removing the 'UNREAD' label.

    Args:
    service: Authorized Gmail API service instance.
    msg_id: The ID of the message to mark as read.
    """
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()
    print(f"Message ID {msg_id} marked as read.")


def get_messages(service):
    # Call the Gmail API
    results = service.users().messages().list(userId='me', labelIds=['UNREAD']).execute()
    messages = results.get('messages', [])

    message_list = []

    for message in messages:
        msg_raw = service.users().messages().get(userId='me', id=message['id'], format="raw").execute()
        msg_json = service.users().messages().get(userId='me', id=message['id']).execute()

        headers = msg_json["payload"]["headers"]
        for header in headers:
            if header["name"] == "From":
                sender = header["value"]
                sender_name = sender.split("<")[0].strip()
                sender_email = sender.split("<")[1].strip().removesuffix(">")
                msg_json["sender_name"] = sender_name
                msg_json["sender_email"] = sender_email
            if header["name"] == "Subject":
                msg_json["subject"] = header["value"]
            if header["name"] == "Message-ID":
                msg_json["message_id"] = header["value"]

        message_list.append({
            "raw": msg_raw,
            "json": msg_json,
        })

    return message_list


def reply_to_unread_messages(gmail_service, context, info):
    print("Getting unread messages...")
    messages = get_messages(gmail_service)

    for message in messages:
        raw_email = get_message_body(message["raw"])

        print("Generating GPT reply...")
        reply = gpt.make_reply(raw_email, context)

        current_date = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
        sender_name = message["json"]["sender_name"]
        sender_email = message["json"]["sender_email"]
        subject = message["json"]["subject"]
        message_id = message["json"]["message_id"]

        reply_block = "\n".join(["> " + line for line in raw_email.split("\n")])

        raw_reply = reply + "\n\nOn "+current_date+" "+sender_name+" <"+sender_email+"> wrote:\n\n"+reply_block

        my_info = info["name"] + " <"+info["email"]+">"

        re_subject = "Re: " + subject.removeprefix("Re: ")

        headers = {
            "In-Reply-To": message_id,
            "References": message_id,
        }

        new_message = create_message(my_info, sender_email, re_subject, raw_reply, headers)

        print("Sending reply...")
        send_message(gmail_service, new_message)

        print("Marking message as read...")
        mark_message_as_read(gmail_service, message["json"]["id"])

        print("Done!")

    if len(messages) == 0:
        print("No unread messages found.")
    else:
        print(f"Replied to {len(messages)} messages.")


def main():
    if len(sys.argv) == 2:
        with open(sys.argv[1], "r") as f:
            context = f.read()
    else:
        context = ""

    print( "#######################################" )
    print( "##       Gmail AI Assistant by       ##" )
    print( "##       Unconventional Coding       ##" )
    print( "##                                   ##" )
    print( "##              WARNING:             ##")
    print( "##  This program will fetch unread   ##" )
    print( "##  messages from your Gmail inbox   ##" )
    print( "##  and reply to them using GPT-3.5  ##" )
    print( "##                                   ##" )
    print( "##      Type 'yes' to continue       ##" )
    print( "#######################################" )

    if input() != "yes":
        print("Exiting...")
        sys.exit()

    print("Authenticating...")
    services = get_services()

    gmail_service = services["gmail"]
    people_service = services["people"]

    print("Getting user info...")
    info = get_user_info(people_service)

    while True:
        reply_to_unread_messages(gmail_service, context, info)
        print("Waiting for 10 seconds...")
        time.sleep(10)

if __name__ == '__main__':
    main()

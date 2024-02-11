# Gmail AI Assistant

This is a Python script that will read all your unread emails and reply to them automatically with a ChatGPT generated response.

## Quick start

```bash
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ export OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXX
$ python3 main.py
```

The script will do an OAuth authentication for your Gmail account and then directly read all your unread emails and **automatically respond** to them with a ChatGPT generated response.

You can pass a text file with instructions for how to reply to emails as a command line argument:

```bash
$ python3 main.py context.txt
```

FROM python:3-alpine

WORKDIR /bot

RUN pip3 install discord

CMD [ "python3", "bot.py" ]

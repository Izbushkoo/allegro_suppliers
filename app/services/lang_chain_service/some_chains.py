from click import prompt
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import SimpleJsonOutputParser

from pydantic import BaseModel


llm = ChatOpenAI(
    model="gpt-3.5-turbo"
)


chat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Твоя единственная задача, сравнивать два поступающих на вход описания товара."
               "Если описания одинаковы по своей сути, а именно, одинаковая комплектация, одинаковые ключевые "
               "параметры и названия то ты возвращаешь True. Если же считаешь что предметы разные, то False,"
                "Свой ответ возвращаешь как JSON object с ключом 'decision' и значением в котором только одно слово-решение"),
        ("human", "Первый товар: {good_first}\nВторой товар: {good_second}\n")
    ]
)

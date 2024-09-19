from collections.abc import Callable
from dataclasses import dataclass

import pytest
from bs4 import Tag, BeautifulSoup


class PublishingError(Exception):
    pass


class ConvertTagError(PublishingError):
    def __init__(self, tag_name: str, tag_string_number: int):
        super().__init__(f"При конвертации тега '{tag_name}' в строке {tag_string_number} произошла ошибка")


class HTMLParseError(Exception):
    def __init__(self, message: str):
        super().__init__(f"Ошибка при парсинге HTML документа: {message}")


class TelegraphPage:
    def __init__(self, title: str, html: BeautifulSoup):
        """
        Класс статьи Telegraph
        :param title: Заголовок статьи
        :param html: HTML документ в формате, подходящем для Telegraph API
        """
        self.title = title
        self.html = html
        self.url = None
        self.path = None


@dataclass
class BlockquoteTag:
    source = """<blockquote class="article_decoration_first article_decoration_last">Будут ли разные виды феодализма?</blockquote>"""
    result = """<blockquote >Будут ли разные виды феодализма?</blockquote>"""


@dataclass
class BlockquoteTagWithChildStrong:
    source = """<blockquote class="article_decoration_first">«<strong class="">адАккарийский народ</strong>!</blockquote>"""
    result = """<blockquote >«<strong>адАккарийский народ</strong>!</blockquote>"""


class TelegraphArticleBuilder:
    """
    Строитель статей Телеграф
    """
    @classmethod
    def build(cls, source_html: str, tag_converters: list[Callable]) -> TelegraphPage:
        """
        Метод строителя
        :param source_html:документ html исходной статьи
        :param tag_converters: список функций для парсинга html тегов
        :return: экземпляр класса статьи Telegraph
        """
        soup = BeautifulSoup(source_html, 'html.parser')
        if error_message := soup.find("div", class_='service_msg_error'):
            raise HTMLParseError(error_message.string)
        if restricted_tag := soup.find("div", class_="article_layer_placeholder__text"):
            raise HTMLParseError(restricted_tag.string)
        try:
            title = soup.find("meta", {"property": "og:title"}).get("content", None)
        except Exception as exc:
            raise HTMLParseError(f"""Не найден тег заголовка статьи. Тег {soup.find("meta")}""")
        body = soup.body
        if body is None:
            raise HTMLParseError(f"Не найден тег тела статьи")
        body = cls._convert(body, tag_converters)
        return TelegraphPage(title, body)

    @classmethod
    def _convert(cls, body: BeautifulSoup, tag_converters: list[Callable]) -> BeautifulSoup:
        # TODO перебить ссылки на вк в нижней части статьи
        # TODO кривая ссылка на twitch
        tags_with_position = {}
        new_body = BeautifulSoup("", "html.parser")
        for parser_func in tag_converters:
            if converted_tags := parser_func(body):
                tags_with_position = tags_with_position | converted_tags
        tags_positions = list(tags_with_position)
        tags_positions.sort()
        for position in tags_positions:
            new_body.append(tags_with_position[position])
        return new_body


def test_convert_blockquote():
    tag = BlockquoteTag()
    result = TelegraphArticleBuilder._convert((BeautifulSoup(tag.source, 'html.parser')),
                                              [convert_blockquote])
    assert result == BeautifulSoup(tag.result, 'html.parser')


def test_blockquote_with_child_strong():
    result = TelegraphArticleBuilder._convert((BeautifulSoup(BlockquoteTagWithChildStrong.source,
                                                             'html.parser')),
                                              [convert_blockquote])
    assert result == BeautifulSoup(BlockquoteTagWithChildStrong.result, 'html.parser')


def get_tag_position(line: int, position: int, sequence: int = 1) -> str:
    if sequence is None:
        sequence = 0
    return "".join([str(line).rjust(7, "0") +
                    str(position).rjust(5, "0") +
                    str(sequence).rjust(2, "0")])


def convert_blockquote(source_tag: Tag) -> dict[str, Tag]:
    new_tags = {}
    for tag in source_tag.find_all("blockquote"):
        new_tag = BeautifulSoup(features='html.parser').new_tag("blockquote")
        new_tag.string = tag.string
        # начало неизменяемых блоков
        new_tag.attrs = {key: value for key, value in new_tag.attrs.items()
                         if key not in ["class"]}
        new_tags.update({get_tag_position(tag.sourceline, tag.sourcepos):
                         new_tag})
        # конец неизменяемых блоков
    return new_tags if len(new_tags) > 0 else None


# test_convert_blockquote()
# test_blockquote_with_child_strong()
pytest.main()

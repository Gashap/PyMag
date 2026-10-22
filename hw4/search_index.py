"""Задание 3. Поисковый индекс на инвертированном индексе."""
import heapq
import re
from collections import Counter


def tokenize(text):
    return re.findall(r'\w+', text.lower())


class SearchIndex:
    """Простая поисковая система по текстовым документам.

    Структуры данных:
    - _index: dict[слово -> set[doc_id]] — инвертированный индекс. Множество, потому что важна
      только уникальность id, а пересечение и объединение множеств — это ровно search_all и search_any.
    - _docs: dict[doc_id -> Counter{слово: количество}] — какие слова и сколько раз есть в каждом
      документе. Благодаря ему remove и повторный add проходят только по словам этого документа,
      а не по всему индексу.
    - _totals: Counter{слово: количество по всем документам} — обновляется при add/remove,
      чтобы top_words не пересчитывал частоты с нуля.

    Слово, которое больше не встречается ни в одном документе, удаляется и из _index, и из _totals.
    """

    def __init__(self):
        self._index = {}
        self._docs = {}
        self._totals = Counter()

    def add(self, doc_id, text):
        if doc_id in self._docs:
            self.remove(doc_id)          # повторный add заменяет старый текст
        counts = Counter(tokenize(text))
        self._docs[doc_id] = counts
        for word, n in counts.items():
            self._index.setdefault(word, set()).add(doc_id)
            self._totals[word] += n

    def remove(self, doc_id):
        counts = self._docs.pop(doc_id)  # KeyError, если такого документа нет
        for word, n in counts.items():
            ids = self._index[word]
            ids.discard(doc_id)
            if not ids:
                del self._index[word]
            self._totals[word] -= n
            if self._totals[word] == 0:
                del self._totals[word]

    def _postings(self, words):
        """Множества id для слов запроса (слова нормализуются так же, как текст)."""
        normalized = [w for word in words for w in tokenize(word)]
        return [self._index.get(w, set()) for w in normalized]

    def search_all(self, *words):
        postings = self._postings(words)
        if not postings:
            return set()
        # пересекаем начиная с самого маленького множества: результат не больше него
        postings.sort(key=len)
        result = set(postings[0])        # копия, чтобы не испортить индекс
        for ids in postings[1:]:
            if not result:
                break
            result &= ids
        return result

    def search_any(self, *words):
        result = set()
        for ids in self._postings(words):
            result |= ids
        return result

    def top_words(self, n):
        """n самых частых слов: [(слово, количество)], при равенстве — по алфавиту."""
        if n <= 0:
            return []
        return heapq.nsmallest(n, self._totals.items(), key=lambda item: (-item[1], item[0]))

    def __len__(self):
        return len(self._docs)

    def __contains__(self, doc_id):
        return doc_id in self._docs


if __name__ == '__main__':
    idx = SearchIndex()
    idx.add(1, 'Python is a programming language.')
    idx.add(2, 'A dict is a hash table; a set is a hash table too!')
    idx.add(3, 'Python dict and set are fast.')
    assert idx.search_all('python') == {1, 3}
    assert idx.search_all('dict', 'set') == {2, 3}
    assert idx.search_all('python', 'hash') == set()
    assert idx.search_any('language', 'fast') == {1, 3}
    assert idx.search_all('PYTHON') == {1, 3}
    assert idx.search_all('nothing') == set()
    assert idx.top_words(2) == [('a', 5), ('is', 3)]
    idx.remove(1)
    assert idx.search_all('python') == {3}
    assert idx.search_any('language', 'programming') == set()
    idx.add(3, 'Totally new text')
    assert idx.search_all('python') == set()
    assert idx.search_all('new') == {3}

    # --- граничные случаи ---
    # слова, которых больше нет ни в одном документе, исчезли из индекса полностью
    assert 'python' not in idx._index and 'language' not in idx._index
    assert 'python' not in idx._totals
    assert idx.top_words(100) == [('a', 4), ('hash', 2), ('is', 2), ('table', 2),
                                  ('dict', 1), ('new', 1), ('set', 1), ('text', 1),
                                  ('too', 1), ('totally', 1)]
    assert idx.top_words(0) == [] and idx.top_words(-1) == []

    # пустой запрос
    assert idx.search_all() == set() and idx.search_any() == set()

    # результат поиска — копия: его изменение не портит индекс
    found = idx.search_all('new')
    found.add(999)
    assert idx.search_all('new') == {3}
    found_any = idx.search_any('new')
    found_any.clear()
    assert idx.search_any('new') == {3}

    # слово, встречающееся в документе несколько раз, даёт один id
    assert idx.search_all('a', 'hash', 'table') == {2}

    # удаление несуществующего документа
    try:
        idx.remove(42)
        assert False, 'ожидали KeyError'
    except KeyError:
        pass

    # пустой документ и документ из одной пунктуации — допустимы, просто без слов
    idx.add(4, '')
    idx.add(5, '!!! ... ???')
    assert len(idx) == 4 and 4 in idx and 5 in idx
    idx.remove(4)
    idx.remove(5)

    # кириллица, цифры и подчёркивание входят в \w
    ru = SearchIndex()
    ru.add('a', 'Словарь — это хеш-таблица, Python 3.13!')
    ru.add('b', 'my_var и Словарь')
    assert ru.search_all('словарь') == {'a', 'b'}
    assert ru.search_all('хеш', 'таблица') == {'a'}
    assert ru.search_all('13') == {'a'} and ru.search_all('my_var') == {'b'}
    # запрос со знаками препинания нормализуется так же, как текст
    assert ru.search_all('Словарь!') == {'a', 'b'}

    # удаление последнего документа очищает индекс целиком
    ru.remove('a')
    ru.remove('b')
    assert ru._index == {} and not ru._totals and len(ru) == 0

    # поиск не перебирает документы: 10 000 документов, искомое слово только в одном
    big = SearchIndex()
    for i in range(10_000):
        big.add(i, f'common word number {i}')
    big.add('target', 'common rare')
    assert big.search_all('common', 'rare') == {'target'}
    assert big.search_any('rare', 'number9999') == {'target'}

    print('Все проверки пройдены.')

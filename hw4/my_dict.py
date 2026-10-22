"""Задание 1. Упрощённый словарь на хеш-таблице с цепочками.

Внутри только списки и кортежи: никаких dict и set.
"""


class MyDict:
    def __init__(self, size=8):
        if size < 1:
            raise ValueError('size должен быть положительным')
        self._buckets = [[] for _ in range(size)]
        self._len = 0

    # --- служебное ---

    def _bucket(self, key):
        return self._buckets[hash(key) % len(self._buckets)]

    @staticmethod
    def _find(bucket, key):
        """Индекс пары с ключом key в корзине или -1.

        Сначала сравниваем через is (как настоящий dict: так находится и float('nan')),
        затем через ==.
        """
        for i, (k, _) in enumerate(bucket):
            if k is key or k == key:
                return i
        return -1

    def _resize(self, new_size):
        old_buckets = self._buckets
        self._buckets = [[] for _ in range(new_size)]
        for bucket in old_buckets:
            for key, value in bucket:
                # номер корзины пересчитывается по новой длине таблицы
                self._bucket(key).append((key, value))

    # --- интерфейс словаря ---

    def __setitem__(self, key, value):
        bucket = self._bucket(key)
        i = self._find(bucket, key)
        if i >= 0:
            old_key, _ = bucket[i]
            bucket[i] = (old_key, value)   # как dict: ключ остаётся прежним, меняется значение
            return
        bucket.append((key, value))
        self._len += 1
        # self._len > 2/3 * число корзин, в целых числах без погрешности float
        if self._len * 3 > len(self._buckets) * 2:
            self._resize(len(self._buckets) * 2)

    def __getitem__(self, key):
        bucket = self._bucket(key)
        i = self._find(bucket, key)
        if i < 0:
            raise KeyError(key)
        return bucket[i][1]

    def __delitem__(self, key):
        bucket = self._bucket(key)
        i = self._find(bucket, key)
        if i < 0:
            raise KeyError(key)
        bucket.pop(i)
        self._len -= 1

    def __contains__(self, key):
        return self._find(self._bucket(key), key) >= 0

    def __len__(self):
        return self._len

    def get(self, key, default=None):
        bucket = self._bucket(key)
        i = self._find(bucket, key)
        return bucket[i][1] if i >= 0 else default

    def stats(self):
        """(число корзин, число элементов, длина самой длинной корзины)."""
        return len(self._buckets), self._len, max(len(b) for b in self._buckets)

    def __repr__(self):
        pairs = ', '.join(f'{k!r}: {v!r}' for bucket in self._buckets for k, v in bucket)
        return f'MyDict({{{pairs}}})'


class BadKey:
    """Ключ, у которого хеш всегда 42: все экземпляры попадают в одну корзину."""
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, BadKey):
            return NotImplemented
        return self.value == other.value

    def __hash__(self):
        return 42


class GoodKey(BadKey):
    __slots__ = ()

    def __hash__(self):
        return hash(self.value)


def _time_insert(keys):
    from time import perf_counter
    d = MyDict()
    start = perf_counter()
    for i, k in enumerate(keys):
        d[k] = i
    return perf_counter() - start, d.stats()


if __name__ == '__main__':
    # --- проверки из задания ---
    d = MyDict()
    for i in range(1000):
        d[f'key{i}'] = i
    assert len(d) == 1000
    assert d['key42'] == 42
    assert 'key7' in d and 'nope' not in d
    d['key42'] = -1
    assert d['key42'] == -1 and len(d) == 1000
    del d['key42']
    assert 'key42' not in d and len(d) == 999
    assert d.get('nope') is None and d.get('nope', 0) == 0
    for bad in (lambda: d['nope'], lambda: d.__delitem__('nope')):
        try:
            bad()
            assert False, 'ожидали KeyError'
        except KeyError:
            pass
    buckets, size, longest = d.stats()
    assert size == 999 and size <= buckets * 2 / 3
    print('1000 строковых ключей:', d.stats())

    # --- граничные случаи ---
    e = MyDict()
    assert len(e) == 0 and repr(e) == 'MyDict({})' and e.stats() == (8, 0, 0)
    assert e.get('x', 'def') == 'def'

    e['a'] = 1
    assert repr(e) == "MyDict({'a': 1})"

    # повторное удаление того же ключа -> KeyError, длина не уходит в минус
    del e['a']
    try:
        del e['a']
        assert False, 'ожидали KeyError'
    except KeyError:
        pass
    assert len(e) == 0

    # 1, 1.0 и True — один и тот же ключ, как в настоящем dict
    e[1] = 'int'
    e[1.0] = 'float'
    e[True] = 'bool'
    assert len(e) == 1 and e[1] == 'bool'

    # None и кортеж — тоже допустимые ключи
    e[None] = 'none'
    e[(1, 2)] = 'tuple'
    assert e[None] == 'none' and e[(1, 2)] == 'tuple'

    # нехешируемый ключ -> TypeError, как у dict
    try:
        e[[1, 2]] = 'list'
        assert False, 'ожидали TypeError'
    except TypeError:
        pass

    # значение None отличается от отсутствующего ключа
    e['empty'] = None
    assert 'empty' in e and e.get('empty', 'def') is None

    # NaN не равен сам себе, но найти его можно, потому что сравниваем сначала через is
    nan = float('nan')
    e[nan] = 'nan'
    assert e[nan] == 'nan'

    # таблица растёт ровно на границе 2/3: 5 элементов в 8 корзинах — ещё можно, 6 — уже нет
    g = MyDict(8)
    for i in range(5):
        g[i] = i
    assert g.stats()[0] == 8
    g[5] = 5
    assert g.stats()[0] == 16

    # перезапись не увеличивает len и не вызывает расширение
    for _ in range(100):
        g[0] = 'x'
    assert len(g) == 6 and g.stats()[0] == 16

    # коллизии: все ключи в одной корзине, но поиск, удаление и перезапись работают
    c = MyDict()
    for i in range(50):
        c[BadKey(i)] = i
    assert c.stats()[2] == 50
    assert c[BadKey(25)] == 25
    del c[BadKey(25)]
    assert BadKey(25) not in c and len(c) == 49
    c[BadKey(0)] = 'zero'
    assert c[BadKey(0)] == 'zero' and len(c) == 49

    try:
        MyDict(0)
        assert False, 'ожидали ValueError'
    except ValueError:
        pass

    # --- эксперимент: хороший хеш против хеша-константы ---
    n = 1000
    t_good, s_good = _time_insert([GoodKey(i) for i in range(n)])
    t_bad, s_bad = _time_insert([BadKey(i) for i in range(n)])
    print(f'{n} ключей с нормальным хешем: {t_good * 1000:.2f} мс, stats={s_good}')
    print(f'{n} ключей с hash() == 42:     {t_bad * 1000:.2f} мс, stats={s_bad}')
    print(f'медленнее в {t_bad / t_good:.0f} раз')

    print('Все проверки пройдены.')


# ===== Ответы на вопросы =====
#
# 1. Почему при увеличении таблицы пары нельзя просто скопировать в корзины с теми же номерами?
#    Номер корзины — это hash(key) % len(buckets), и он зависит от длины таблицы. После увеличения
#    в 2 раза поиск считает номер по новой длине: например, ключ с хешем 13 лежал в корзине 13 % 8 = 5,
#    а искать его будут в 13 % 16 = 13. Если оставить пару в старой корзине, ключ станет «невидимым»,
#    хотя физически в таблице есть, поэтому все пары нужно разложить заново.
#
# 2. Что показывает stats() для 1000 строковых ключей и для ключей с __hash__, равным 42?
#    Для строковых ключей stats() даёт (2048, 999, 4–5) (999 — после del d['key42']): ключи
#    разбросаны почти равномерно, самая длинная цепочка — несколько штук, операции работают за O(1).
#    Если хеш всегда 42, все ключи лежат в одной корзине, stats() == (2048, 1000, 1000), и каждая
#    вставка просматривает всю цепочку через ==, так что 1000 вставок стоят O(n²): в моих замерах
#    ~45–60 мс против ~1 мс с нормальным хешем, то есть в 40–60 раз дольше.

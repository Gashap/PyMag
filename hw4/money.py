"""Задание 2. Неизменяемый хешируемый класс-значение Money."""


class Money:
    __slots__ = ('amount', 'currency')   # нет __dict__ -> новые атрибуты не создать

    def __init__(self, amount, currency):
        # bool — подкласс int, но True копеек не бывает
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise TypeError(f'amount должен быть int (копейки), а не {type(amount).__name__}')
        if not isinstance(currency, str) or not currency:
            raise TypeError('currency должна быть непустой строкой')
        # обычное присваивание запрещено нашим __setattr__, поэтому идём в обход через object
        object.__setattr__(self, 'amount', amount)
        object.__setattr__(self, 'currency', currency)

    def __setattr__(self, name, value):
        raise AttributeError(f'Money неизменяем: нельзя установить атрибут {name!r}')

    def __delattr__(self, name):
        raise AttributeError(f'Money неизменяем: нельзя удалить атрибут {name!r}')

    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return (self.amount, self.currency) == (other.amount, other.currency)

    def __hash__(self):
        # хеш от тех же полей, что участвуют в __eq__: a == b  =>  hash(a) == hash(b)
        return hash((self.amount, self.currency))

    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f'нельзя сложить {self.currency} и {other.currency}')
        return Money(self.amount + other.amount, self.currency)   # новый объект

    def __reduce__(self):
        # copy и pickle по умолчанию восстанавливают объект через setattr, а он у нас запрещён;
        # вместо этого говорим им создавать объект заново через конструктор
        return Money, (self.amount, self.currency)

    def __repr__(self):
        return f'Money({self.amount}, {self.currency!r})'


def total_by_currency(payments):
    """Сумма платежей по каждой валюте: {валюта: Money}."""
    totals = {}
    for p in payments:
        # Money неизменяем, поэтому хранить сам объект из входного списка безопасно
        totals[p.currency] = totals[p.currency] + p if p.currency in totals else p
    return totals


if __name__ == '__main__':
    assert len({Money(100, 'RUB'), Money(100, 'RUB'), Money(100, 'USD')}) == 2
    prices = {Money(100, 'RUB'): 'сто рублей'}
    assert prices[Money(100, 'RUB')] == 'сто рублей'
    assert Money(100, 'RUB') + Money(50, 'RUB') == Money(150, 'RUB')
    for action in (lambda m: setattr(m, 'amount', 5), lambda m: setattr(m, 'extra', 1)):
        try:
            action(Money(1, 'RUB'))
            assert False, 'ожидали AttributeError'
        except AttributeError:
            pass
    try:
        Money(1, 'RUB') + Money(1, 'USD')
        assert False, 'ожидали ValueError'
    except ValueError:
        pass
    pays = [Money(100, 'RUB'), Money(5, 'USD'), Money(250, 'RUB')]
    assert total_by_currency(pays) == {'RUB': Money(350, 'RUB'), 'USD': Money(5, 'USD')}

    # --- граничные случаи ---
    m = Money(1500, 'RUB')
    assert repr(m) == "Money(1500, 'RUB')"

    # контракт хеша: равные объекты — равные хеши
    assert hash(Money(7, 'EUR')) == hash(Money(7, 'EUR'))

    # сравнение с другим типом: __eq__ возвращает NotImplemented, итог — False, а не ошибка
    assert m.__eq__(1500) is NotImplemented
    assert m != 1500 and m != (1500, 'RUB') and m != 'Money(1500, RUB)'
    assert m.__add__(5) is NotImplemented
    try:
        m + 5
        assert False, 'ожидали TypeError'
    except TypeError:
        pass

    # сложение создаёт новый объект, слагаемые не меняются
    a, b = Money(10, 'RUB'), Money(20, 'RUB')
    s = a + b
    assert s is not a and s is not b
    assert a == Money(10, 'RUB') and b == Money(20, 'RUB')

    # нельзя удалить поле, нельзя писать в __dict__ — его просто нет
    try:
        del m.amount
        assert False, 'ожидали AttributeError'
    except AttributeError:
        pass
    assert not hasattr(m, '__dict__')

    # отрицательные суммы и ноль допустимы (возвраты, пустой счёт)
    assert Money(100, 'RUB') + Money(-100, 'RUB') == Money(0, 'RUB')

    # некорректные значения отсекаются сразу
    for bad_args in ((10.5, 'RUB'), ('10', 'RUB'), (True, 'RUB'), (10, ''), (10, None)):
        try:
            Money(*bad_args)
            assert False, f'ожидали TypeError для {bad_args}'
        except TypeError:
            pass

    # копирование и pickle работают и дают равный объект
    import copy
    import pickle
    for clone in (copy.copy(m), copy.deepcopy(m), pickle.loads(pickle.dumps(m))):
        assert clone == m and hash(clone) == hash(m)

    # валюты чувствительны к регистру: 'rub' и 'RUB' — разные
    assert Money(1, 'rub') != Money(1, 'RUB')

    # пустой список платежей, одна валюта, входной список не меняется
    assert total_by_currency([]) == {}
    one = [Money(1, 'RUB')] * 3
    assert total_by_currency(one) == {'RUB': Money(3, 'RUB')}
    assert one == [Money(1, 'RUB')] * 3

    print('Все проверки пройдены.')


# ===== Что сломалось бы, если бы поля можно было менять =====
#
# Множество и словарь кладут объект в корзину по hash(), вычисленному в момент добавления, и потом
# ищут его по хешу заново. В примере с Point из лекции: p = Point(1, 2), visited = {p}, затем p.x = 100 —
# и p in visited даёт False, хотя p in list(visited) даёт True. Объект лежит в корзине для хеша (1, 2),
# а поиск идёт в корзину для (100, 2) и ничего не находит, а по старым координатам найти тоже нельзя:
# там лежит объект, который уже не равен Point(1, 2). Поэтому Money неизменяем: его хеш не может
# поменяться, пока объект лежит в множестве или служит ключом словаря.

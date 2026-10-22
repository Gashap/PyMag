"""Задание 4. Кэширование через замыкание."""


def memoize(func):
    cache = {}   # живёт в объемлющей функции и доступен wrapper через замыкание

    def wrapper(*args, **kwargs):
        # f(1, b=2) и f(1, b=3) дают разные ключи; sorted делает ключ независимым от порядка kwargs
        key = (args, tuple(sorted(kwargs.items())))
        try:
            hash(key)
        except TypeError:
            # нехешируемые аргументы (например, список): вызываем без кэша, счётчики не трогаем
            return func(*args, **kwargs)
        if key in cache:
            wrapper.hits += 1
            return cache[key]
        wrapper.misses += 1
        result = func(*args, **kwargs)
        cache[key] = result
        return result

    def cache_clear():
        cache.clear()
        wrapper.hits = 0
        wrapper.misses = 0

    # сохраняем метаданные исходной функции (то же делает functools.wraps)
    wrapper.__name__ = func.__name__
    wrapper.__qualname__ = func.__qualname__
    wrapper.__doc__ = func.__doc__
    wrapper.__module__ = func.__module__
    wrapper.__wrapped__ = func

    # атрибуты функции хранятся в wrapper.__dict__
    wrapper.hits = 0
    wrapper.misses = 0
    wrapper.cache_clear = cache_clear
    return wrapper


if __name__ == '__main__':
    from time import perf_counter

    calls = []

    def slow_square(x, power=2):
        '''Возводит в степень.'''
        calls.append(x)
        return x ** power

    sq = memoize(slow_square)
    assert sq(3) == 9 and sq(3) == 9 and sq(3, power=3) == 27
    assert calls == [3, 3]
    assert (sq.hits, sq.misses) == (1, 2)
    assert sq.__name__ == 'slow_square' and sq.__doc__ == 'Возводит в степень.'
    assert sq.__wrapped__ is slow_square
    total = memoize(sum)
    assert total([1, 2, 3]) == 6 and total([1, 2, 3]) == 6   # нехешируемый аргумент: вызов без кэша
    assert (total.hits, total.misses) == (0, 0)
    sq.cache_clear()
    assert (sq.hits, sq.misses) == (0, 0)
    sq(3)
    assert calls[-1] == 3

    # --- граничные случаи ---
    log = []

    def f(a, b=0, *, c=0):
        log.append((a, b, c))
        return a + b + c

    mf = memoize(f)
    # порядок именованных аргументов не важен
    assert mf(1, b=2, c=3) == mf(1, c=3, b=2) == 6
    assert len(log) == 1 and (mf.hits, mf.misses) == (1, 1)
    # разные значения именованного аргумента кэшируются отдельно
    mf(1, b=2)
    mf(1, b=3)
    assert len(log) == 3
    # f(1, 2) и f(1, b=2) — разные ключи (как и в functools.lru_cache), но результат верный
    assert mf(1, 2) == mf(1, b=2) == 3

    # 1 и 1.0 равны и имеют одинаковый хеш, поэтому делят запись в кэше
    mf.cache_clear()
    log.clear()
    mf(1)
    mf(1.0)
    assert len(log) == 1

    # нехешируемый именованный аргумент тоже не роняет функцию
    mf.cache_clear()
    pick = memoize(lambda items, idx=0: items[idx])
    assert pick([10, 20], idx=1) == 20 and (pick.hits, pick.misses) == (0, 0)
    assert pick((10, 20), idx=1) == 20 and pick.misses == 1

    # функция без аргументов вызывается один раз
    counter = []
    once = memoize(lambda: counter.append(1) or len(counter))
    assert once() == 1 and once() == 1 and counter == [1]

    # None — тоже результат, и он кэшируется (проверка через in, а не через get)
    nones = []
    nothing = memoize(lambda x: nones.append(x))
    assert nothing(5) is None and nothing(5) is None
    assert nones == [5] and nothing.hits == 1

    # исключения не кэшируются: следующий вызов снова доходит до функции
    attempts = []

    def flaky(x):
        attempts.append(x)
        if len(attempts) == 1:
            raise RuntimeError('первый раз не вышло')
        return x

    mflaky = memoize(flaky)
    try:
        mflaky(1)
        assert False, 'ожидали RuntimeError'
    except RuntimeError:
        pass
    assert mflaky(1) == 1 and len(attempts) == 2

    # у двух мемоизированных функций — свои независимые кэши и счётчики
    sq1, sq2 = memoize(slow_square), memoize(slow_square)
    sq1(2)
    sq1(2)
    assert (sq1.hits, sq1.misses) == (1, 1) and (sq2.hits, sq2.misses) == (0, 0)
    sq1.cache_clear()
    sq2(4)
    assert (sq1.hits, sq1.misses) == (0, 0) and sq2.misses == 1

    print('Все проверки пройдены.')

    # --- эксперимент с рекурсией ---
    N = 30

    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    start = perf_counter()
    plain = fib(N)
    t_plain = perf_counter() - start

    fast_fib = memoize(fib)          # вариант A: глобальное имя fib по-прежнему указывает на оригинал
    start = perf_counter()
    res_a = fast_fib(N)
    t_a = perf_counter() - start

    fib = memoize(fib)               # вариант B: глобальное имя fib теперь указывает на обёртку
    start = perf_counter()
    res_b = fib(N)
    t_b = perf_counter() - start

    assert plain == res_a == res_b == 832040
    assert fast_fib.misses == 1      # закэширован только самый внешний вызов
    assert fib.misses == N + 1       # закэшированы все значения fib(0) ... fib(30)

    print(f'\nfib({N}) без кэша:   {t_plain:.4f} с')
    print(f'вариант A: misses={fast_fib.misses}, {t_a:.4f} с')
    print(f'вариант B: misses={fib.misses}, {t_b * 1000:.4f} мс, быстрее варианта A в {t_a / t_b:.0f} раз')


# ===== Почему один вариант ускоряет, а другой нет (LEGB) =====
#
# Внутри fib рекурсивный вызов fib(n - 1) ищет имя fib не в момент определения функции, а в момент
# каждого вызова, по правилу LEGB: в локальной области fib нет, объемлющей функции нет, поэтому имя
# находится в глобальной области модуля (G).
#
# Вариант A: fast_fib = memoize(fib) создаёт обёртку под новым именем, а глобальное fib по-прежнему
# указывает на исходную функцию. Через кэш проходит только самый внешний вызов fast_fib(30), а все
# ~2,7 млн рекурсивных вызовов идут в исходную fib мимо кэша, поэтому misses == 1 и ускорения нет.
#
# Вариант B: fib = memoize(fib) перепривязывает глобальное имя fib к обёртке. Теперь рекурсивный
# fib(n - 1) при поиске в G находит обёртку, и каждое значение fib(k) вычисляется ровно один раз:
# misses == 31, hits == 28: вместо ~2,7 млн вызовов — 59. В моих замерах (Python 3.13) вариант A работает
# ~0,09–0,11 с, как и fib без кэша, а вариант B — ~0,08–0,09 мс, то есть примерно в 1000 раз быстрее.

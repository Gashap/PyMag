# Мини-трекер книг
class BookTracker:
    def __init__(self) -> None:
        # Коллекции создаются внутри __init__, а не как default-аргументы,
        # поэтому у каждого трекера свои, независимые данные.
        self._books: list[tuple[int, str, str, int]] = []       # list: меняющийся набор записей
        self._by_id: dict[int, tuple[int, str, str, int]] = {}  # dict: быстрый поиск по id
        self._authors: set[str] = set()                         # set: только уникальные авторы

    def add_book(self, book_id: int, title: str, author: str, year: int) -> tuple[int, str, str, int]:
        if book_id in self._by_id:
            raise ValueError(f"Книга с id={book_id} уже есть")
        record = (book_id, title, author, year)  # tuple: фиксированная структура записи
        self._books.append(record)
        self._by_id[book_id] = record  # ключ — int (hashable), не список
        self._authors.add(author)
        return record

    def remove_book(self, book_id: int) -> None:
        record = self._by_id.pop(book_id)
        self._books.remove(record)
        # автор остаётся в set, только если у него есть другие книги
        if all(book[2] != record[2] for book in self._books):
            self._authors.discard(record[2])

    def get_book(self, book_id: int) -> tuple[int, str, str, int] | None:
        return self._by_id.get(book_id)

    def get_books(self) -> list[tuple[int, str, str, int]]:
        # Возвращаем копию, чтобы внешний код не изменил внутренний список через alias
        return list(self._books)

    def get_authors(self) -> set[str]:
        return set(self._authors)


if __name__ == "__main__":
    tracker = BookTracker()
    tracker.add_book(1, "Мастер и Маргарита", "Булгаков", 1967)
    tracker.add_book(2, "Собачье сердце", "Булгаков", 1987)
    tracker.add_book(3, "Пикник на обочине", "Стругацкие", 1972)

    print("Все книги:", tracker.get_books())
    print("Книга id=3:", tracker.get_book(3))
    print("Авторы:", tracker.get_authors())

    books = tracker.get_books()
    books.clear()  # чистим копию — данные трекера не трогаются
    print("После очистки копии:", len(tracker.get_books()), "книги")

    tracker.remove_book(3)
    print("После удаления id=3:", tracker.get_books(), tracker.get_authors())
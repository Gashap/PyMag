# Багованный код
students = ["Anna", "Bob", "Kate"]
grades = dict.fromkeys(students, [])

grades["Anna"].append(5)
print(grades)  # {'Anna': [5], 'Bob': [5], 'Kate': [5]} — оценка появилась у всех

# Исправленный код
students = ["Anna", "Bob", "Kate"]
grades = {name: [] for name in students}  # для каждого ключа создаётся свой список
 
grades["Anna"].append(5)
print(grades)  # {'Anna': [5], 'Bob': [], 'Kate': []}
assert grades == {"Anna": [5], "Bob": [], "Kate": []}
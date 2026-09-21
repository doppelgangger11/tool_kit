### 🔧 Полезные мелкие утилиты

1) Clipboard Manager

- хранить последние N скопированных текстов;
- поиск по истории;
- клик → вставить;
- отдельная кнопка очистки.

2) ~~Quick Notes~~

- ~~маленькие заметки прямо из Toolkit;~~
- ~~notes/2026-09-14.txt;~~
- ~~поиск по заметкам.~~

3) File Renamer

- выбрать папку;
- показать файлы;
- шаблон:

  ```
  file_001.xlsx
  file_002.xlsx
  file_003.xlsx
  ```
- замена текста в именах;
- добавление даты.

4) File Organizer

   ```
   Downloads/
   ├── pdf/
   ├── images/
   ├── archives/
   ├── documents/
   └── other/
   ```

Одной кнопкой разложить Downloads.

5) Duplicate Finder

- поиск одинаковых файлов по hash;
- показать размер;
- возможность удалить/переместить дубли.

6) Folder Size Analyzer

   ```
   Downloads       12.4 GB
   Projects         8.1 GB
   Videos           5.7 GB
   ```

Очень простая, но прикольная штука.

---

### 🖥️ Windows-утилиты

7) Process Manager

Не полноценный Task Manager, а просто:

    ``    chrome.exe       12 processes     python.exe        3 processes     Code.exe          5 processes    ``

И кнопки:

- refresh
- kill process
- kill all selected

8) Quick Commands

GUI для часто используемых команд:

    ```
    [ Git status ]
    [ Git pull ]
    [ Git push ]

    [ Open CMD here ]
    [ Open PowerShell here ]
    [ Open VS Code here ]

    [ pip freeze ]
    [ python --version ]
    ```

9) Port Checker

Ввести:

```
localhost:5432
```

→

```
OPEN
```

или

```
CLOSED
```

10) Localhost Manager

Например:

    ``    PostgreSQL      :5432     Django           :8000     Jupyter          :8888     Airflow          :8080    ``

Кнопки запуска/открытия.

### 🐍 Python-штуки

11) JSON Viewer

Вставил:

```
{"name":"Mark","items":[1,2,3]}
```

→ красивое дерево.

Плюс:

- format;
- minify;
- validate;
- copy.

12) CSV/Excel Inspector

Выбираешь файл → Toolkit показывает:

    ```
    File: data.xlsx

    Rows:       124 532
    Columns:         17
    Duplicates:      842
    Empty cells:   1 234

    Columns:
    ID          int
    Name        str
    Price       float
    Date        datetime
    ```

Это уже очень неплохо выглядит как DE/data-tool.

13) SQL Formatter

Вставил ебанутый SQL:

```
select a,b from table where x=1 and y=2
```

→ нормальный:

```
SELECT
    a,
    b
FROM table
WHERE x = 1
  AND y = 2;
```

14) SQL Playground

Маленькая SQLite БД прямо внутри Toolkit.

Можно:

- создать таблицу;
- загрузить CSV;
- выполнять SQL;
- смотреть результат.

Вот это я бы особенно добавил, учитывая твой DE интерес.

### 📊 Data/DE направление

15) CSV → SQLite

Выбираешь:

```
users.csv
```

Toolkit создаёт:

```
database.db
└── users
```

и показывает количество записей.

16) Simple ETL Runner

Сделать свой мини-Airflow:

```
[Extract]
    ↓
[Transform]
    ↓
[Validate]
    ↓
[Load]
```

И GUI:

```
Pipeline: sales_daily

✓ Extract
✓ Transform
✓ Validate
→ Load

Status: SUCCESS
Runtime: 13.4 sec
```

Причём это может быть реально полезным учебным проектом для DE, а не просто игрушкой.

17) Job/Pipeline Logger

Каждый запуск:

```
2026-09-14 14:03:12
pipeline=sales
rows_in=125432
rows_out=124901
rejected=531
runtime=18.3s
status=SUCCESS
```

Потом сделать простую статистику.

---

### 🎮 Раз уж у тебя уже есть games

Можно добавить всякую хуйню для отдыха:

18) 2048
19) Snake
20) Tetris
21) Reaction test
22) Typing speed test
23) Mini Sudoku

И всё это будет запускаться из Toolkit.

---

### 🧠 А ещё можно сделать «хранилище полезных вещей»

Например Snippets:

```
Python
 ├── pandas
 ├── pathlib
 ├── tkinter
 └── logging

SQL
 ├── JOIN
 ├── CTE
 ├── window functions
 └── date functions

Git
 ├── undo commit
 ├── reset
 └── stash
```

Нажал → код скопирован в clipboard.

Это, кстати, одна из тех вещей, которыми реально начинаешь пользоваться постоянно.

---

### И я бы добавил одну большую штуку

### 🚀 Launcher

У тебя уже есть запуск программ. Можно развить его в универсальный launcher:

```
┌─────────────────────────────────────┐
│ 🔍 Search...                        │
├─────────────────────────────────────┤
│ Visual Studio Code                  │
│ Google Chrome                       │
│ Outlook                             │
│ Minesweeper                         │
│ SQL Playground                      │
│ Downloads                           │
│ Git Bash                            │
│ Terminal                            │
└─────────────────────────────────────┘
```

Начал писать:

```
chr
```

→ Chrome

```
min
```

→ Minesweeper

```
sql
```

→ SQL Playground

А потом можно добавить горячую клавишу типа Ctrl+Space, и Toolkit превращается в твой маленький `<b>`PowerToys/Alfred/Everything-подобный launcher.`</b>`

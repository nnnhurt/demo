git clone https://github.com/nnnhurt/demo .

notepad (Get-PSReadLineOption).HistorySavePath

Откроется блокнот, в него жмем Cntrl A, все стираем и Cntlr S. Закрываем терминал через иконку с мусоркой и создаем новый.

Remove-Item -Recurse -Force .git (команда чтобы удалить .git)

Проверить ls -h (должно быть пусто)

—-----------

uv sync (чтобы и венв создать и чтобы зависимости)

git init

git config user.name “user”
git config user.email “nfnfdkfkdj@mail.ru”

активация венва
.\.venv\Scripts\activate.ps1

Идем в DBeaver, открываем подключение к постгресу, выбираем галочку “Показать все базы данных”
Пароль: 123456
У нас там раздел Databases, жмем правой кнопкой мыши и создать БД (Create new Databse). Имя demo. 

Появилась база Demo. 

Идем в наш проект.
python3 manage.py makemigrations ( для вида)
python3 manage.py migrate

python3 manage.py scriptdb 

python3 manage.py runserver

—--------------------------------------------

НЕ ЗАБЫТЬ
сделать коммиты (лучше просто каждую папку отдельно закоммитить)
сделать ворд документ со скринами
сделать диаграмму процесса разработки в пдф (через приложение или сайт draw.io)
удалить этот файл
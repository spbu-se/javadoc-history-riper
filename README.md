# JavaDoc Ripper

Russian ReadMe / Русское описание

## Что этот скрипт делает?

1. Анализирует логи репоитория Git с исходниками на Java на предмт коммитов с изменениями в JavaDoc.
2. Выдаёт электронную таблицу со следующими колонками:
    - Что за коммит (включает изменения в JavaDoc / есть файлы, в которых поменялся только JavaDoc / во всём коммите исключительно изменения в JavaDoc);
    - Ссылку на коммит (чтобы можно было кликнуть и посмотреть коммит на GitHub);
    - Кусочек diff этого коммита, чтобы прямо в Экселе посмотреть.

## Как его инсталлировать?

1. Инсталлировать Python 3.7 (под Windows — см. https://www.python.org/downloads/release/python-375/).
2. Инсталлировать пакеты (под Windows — `pip install -r requirements.txt`).

## Как его запускать и получать электронную таблицу?

1. Сохранить в файл в какой-нибудь каталог, например под Windows `c:\tools\rip-rep-logs.py`
2. Склонировать репозиторий Git, например, `git clone https://github.com/albertogoffi/toradocu.git`
3. Находясь в корневом каталоге репозитория, запустить скрипт с параметром `-cp <префикс URL коммитов на GitHub>`,
   например, под Windows `python c:\tools\rip-rep-logs.py -cp https://github.com/albertogoffi/toradocu/commit/`
4. Если предыдущие пункты выполнены верно, то подождать несколько минут (или часов, зависит от входных данных),
   пока спкрит сканирует историю Git.
5. Получить на выходе файл `__commits.xlsx`

<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/80x15.png" /></a> This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.

Autor: Dmitry V. Luciv

Contributors:

* Maria Dolgopolova

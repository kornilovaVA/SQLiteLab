import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QPushButton, QTableView, QMessageBox, QAction, QFileDialog, QComboBox
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel, QSqlQueryModel

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Библиотека')
        self.setGeometry(100, 100, 800, 600)

        # Инициализация БД
        if not self.initialize_db():
            return

        # Вкладки
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Создание вкладок Книги, Читатель и Учет_книг
        self.setup_tabs()

        # Меню
        main_menu = self.menuBar()
        file_menu = main_menu.addMenu('Файл')

        # Пункты меню
        save_action = QAction('Сохранить БД', self)
        save_action.triggered.connect(self.save_db)
        file_menu.addAction(save_action)

        restore_action = QAction('Восстановить БД', self)
        restore_action.triggered.connect(self.restore_db)
        file_menu.addAction(restore_action)
        
        clear_db_action = QAction('Очистить БД', self)
        clear_db_action.triggered.connect(self.clear_db)
        file_menu.addAction(clear_db_action)
        
        self.tabs.tabBarClicked.connect(self.on_tab_clicked)
        self.books_model.dataChanged.connect(self.update_overdue_books_tab)
        self.readers_model.dataChanged.connect(self.update_readers_report_tab)
    
    def initialize_db(self):
        self.db = QSqlDatabase.addDatabase('QSQLITE')
        self.db.setDatabaseName('example.db')
        if not self.db.open():
            QMessageBox.critical(None, 'Не могу открыть базу данных',
                'Невозможно установить соединение с базой данных.\n', QMessageBox.Cancel)
            return False

        query = QSqlQuery()
        
        query.exec_("""
        DROP TABLE IF EXISTS Книги;
        """)
        
        query.exec_("""
        DROP TABLE IF EXISTS Читатель;
        """)
        
        query.exec_("""
        DROP TABLE IF EXISTS Учет_книг;
        """)
        
        query.exec_("""
        CREATE TABLE IF NOT EXISTS Книги (
        Номер_книги INTEGER PRIMARY KEY,
        Название_книги TEXT NOT NULL,
        Авторы TEXT,
        Издательство TEXT,
        Год_издания INTEGER
        );
        """)

        query.exec_("""
        CREATE TABLE IF NOT EXISTS Читатель (
        Номер_читательского_билета INTEGER PRIMARY KEY,
        Фамилия TEXT NOT NULL,
        Адрес TEXT,
        Год_рождения INTEGER,
        Образование TEXT
        );
        """)

        query.exec_("""
        CREATE TABLE IF NOT EXISTS Учет_книг (
        Номер_книги INTEGER,
        Номер_читательского_билета INTEGER,
        Дата_выдачи TEXT,
        Дата_возврата TEXT,
        Дата_факт_возврата TEXT,
        FOREIGN KEY (Номер_читательского_билета) REFERENCES Читатель (Номер_читательского_билета),
        FOREIGN KEY (Номер_книги) REFERENCES Книги (Номер_книги)
        );
        """)

        query.exec_("""
        INSERT INTO Книги (Номер_книги, Название_книги, Авторы, Издательство, Год_издания) VALUES
        (1, 'Война и мир', 'Л. Н. Толстой', 'Издательство А', 1989),
        (2, 'Преступление и наказание', 'Ф. М. Достоевский', 'Издательство Б', 1976);
        """)

        query.exec_("""
        INSERT INTO Читатель (Номер_читательского_билета, Фамилия, Адрес, Год_рождения, Образование) VALUES
        (1, 'Иванов', 'ул. Ленина, 1', 1990, 'Высшее'),
        (2, 'Петров', 'ул. Пушкина, 2', 1985, 'Среднее специальное');
        """)

        query.exec_("""
        INSERT INTO Учет_книг (Номер_книги, Номер_читательского_билета, Дата_выдачи, Дата_возврата, Дата_факт_возврата) VALUES
        (1, 1, '2024-01-01', '2024-01-15', '2024-01-20'),
        (2, 2, '2024-02-01', '2024-02-15', NULL);
        """)

        return True
    
    def adjust_table_view(self, table_view):
        table_view.resizeColumnsToContents()
        table_view.resizeRowsToContents()

    def setup_tabs(self):
        self.setup_books_tab()
        self.setup_readers_tab()
        self.setup_accounting_tab()
        self.setup_custom_query_tab()
        
        # Вкладка для Запроса №1
        self.overdue_books_tab = QWidget()
        self.overdue_books_layout = QVBoxLayout()
        self.overdue_books_table = QTableView()
        self.overdue_books_model = QSqlQueryModel()
        self.update_overdue_books_tab()
        self.overdue_books_table.setModel(self.overdue_books_model)
        self.overdue_books_layout.addWidget(self.overdue_books_table)
        self.overdue_books_tab.setLayout(self.overdue_books_layout)
        self.tabs.addTab(self.overdue_books_tab, 'Не возвращенные в срок книги')

        # Вкладка для Отчета №1 «Читатели»
        self.readers_report_tab = QWidget()
        self.readers_report_layout = QVBoxLayout()
        self.readers_report_table = QTableView()
        self.readers_report_model = QSqlQueryModel()
        self.update_readers_report_tab()
        self.readers_report_table.setModel(self.readers_report_model)
        self.readers_report_layout.addWidget(self.readers_report_table)
        self.readers_report_tab.setLayout(self.readers_report_layout)
        self.tabs.addTab(self.readers_report_tab, 'Отчет «Читатели»')
        
        self.adjust_table_view(self.books_table)
        self.adjust_table_view(self.readers_table)
        self.adjust_table_view(self.accounting_table)
        self.adjust_table_view(self.overdue_books_table)
        self.adjust_table_view(self.readers_report_table)
        
    def update_overdue_books_tab(self):
        self.overdue_books_model.setQuery("""
        SELECT К.Номер_книги, К.Название_книги, К.Издательство, У.Номер_читательского_билета, Ч.Фамилия, У.Дата_выдачи, У.Дата_возврата
        FROM Учет_книг У
        JOIN Книги К ON У.Номер_книги = К.Номер_книги
        JOIN Читатель Ч ON У.Номер_читательского_билета = Ч.Номер_читательского_билета
        WHERE У.Дата_возврата < У.Дата_факт_возврата OR У.Дата_факт_возврата IS NULL;
        """)
        self.overdue_books_table.resizeColumnsToContents()

    def update_readers_report_tab(self):
        self.readers_report_model.setQuery("""
        SELECT Ч.Номер_читательского_билета, Ч.Фамилия, COUNT(У.Номер_книги) AS Количество_взятых_книг
        FROM Читатель Ч
        LEFT JOIN Учет_книг У ON Ч.Номер_читательского_билета = У.Номер_читательского_билета
        GROUP BY Ч.Номер_читательского_билета;
        """)
        self.readers_report_table.resizeColumnsToContents()
        
    def setup_readers_tab(self):
        self.readers_tab = QWidget()
        self.readers_layout = QVBoxLayout()
        self.readers_table = QTableView()
        self.readers_model = QSqlTableModel()
        self.readers_model.setTable('Читатель')
        self.readers_model.setEditStrategy(QSqlTableModel.OnFieldChange)
        self.readers_model.select()
        self.readers_table.setModel(self.readers_model)
        self.readers_layout.addWidget(self.readers_table)

        # Кнопки для управления данными
        self.add_reader_button = QPushButton('Добавить читателя')
        self.add_reader_button.clicked.connect(self.add_reader)
        self.delete_reader_button = QPushButton('Удалить читателя')
        self.delete_reader_button.clicked.connect(self.delete_reader)

        self.readers_layout.addWidget(self.add_reader_button)
        self.readers_layout.addWidget(self.delete_reader_button)
        self.readers_tab.setLayout(self.readers_layout)
        self.tabs.addTab(self.readers_tab, 'Читатель')

    def add_reader(self):
        # Добавление новой строки в конец модели
        row_count = self.readers_model.rowCount()
        self.readers_model.insertRow(row_count)
        self.readers_model.setData(self.readers_model.index(row_count, 1), 'Введите фамилию')
        self.readers_model.submitAll()

    def delete_reader(self):
        # Удаление выбранной строки
        selected_indices = self.readers_table.selectionModel().selectedRows()
        for index in sorted(selected_indices):
            self.readers_model.removeRow(index.row())
        self.readers_model.submitAll()
        
    def setup_books_tab(self):
        self.books_tab = QWidget()
        self.books_layout = QVBoxLayout()
        self.books_table = QTableView()
        self.books_model = QSqlTableModel()
        self.books_model.setTable('Книги')
        self.books_model.setEditStrategy(QSqlTableModel.OnFieldChange)
        self.books_model.select()
        self.books_table.setModel(self.books_model)
        self.books_layout.addWidget(self.books_table)

        # Кнопки для управления данными
        self.add_book_button = QPushButton('Добавить книгу')
        self.add_book_button.clicked.connect(self.add_book)
        self.delete_book_button = QPushButton('Удалить книгу')
        self.delete_book_button.clicked.connect(self.delete_book)

        self.books_layout.addWidget(self.add_book_button)
        self.books_layout.addWidget(self.delete_book_button)
        self.books_tab.setLayout(self.books_layout)
        self.tabs.addTab(self.books_tab, 'Книги')

    def add_book(self):
        # Добавление новой строки в конец модели
        row_count = self.books_model.rowCount()
        self.books_model.insertRow(row_count)
        self.books_model.setData(self.books_model.index(row_count, 1), 'Введите название книги')
        self.books_model.submitAll()

    def delete_book(self):
        # Удаление выбранной строки
        selected_indices = self.books_table.selectionModel().selectedRows()
        for index in sorted(selected_indices):
            self.books_model.removeRow(index.row())
        self.books_model.submitAll()
        
    def setup_accounting_tab(self):
        self.accounting_tab = QWidget()
        self.accounting_layout = QVBoxLayout()
        self.accounting_table = QTableView()
        self.accounting_model = QSqlTableModel()
        self.accounting_model.setTable('Учет_книг')
        self.accounting_model.setEditStrategy(QSqlTableModel.OnFieldChange)
        self.accounting_model.select()
        self.accounting_table.setModel(self.accounting_model)
        self.accounting_layout.addWidget(self.accounting_table)

        # Кнопки для управления данными
        self.add_accounting_button = QPushButton('Добавить запись')
        self.add_accounting_button.clicked.connect(self.add_accounting_entry)
        self.delete_accounting_button = QPushButton('Удалить запись')
        self.delete_accounting_button.clicked.connect(self.delete_accounting_entry)

        self.accounting_layout.addWidget(self.add_accounting_button)
        self.accounting_layout.addWidget(self.delete_accounting_button)
        self.accounting_tab.setLayout(self.accounting_layout)
        self.tabs.addTab(self.accounting_tab, 'Учет книг')

    def add_accounting_entry(self):
        # Добавление новой строки в конец модели
        row_count = self.accounting_model.rowCount()
        self.accounting_model.insertRow(row_count)
        self.accounting_table.edit(self.accounting_model.index(row_count, 0))

    def delete_accounting_entry(self):
        # Удаление выбранной строки
        selected_indices = self.accounting_table.selectionModel().selectedRows()
        for index in sorted(selected_indices, reverse=True):
            self.accounting_model.removeRow(index.row())
        self.accounting_model.submitAll()
    
    # Функция для сохранения БД
    def save_db(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "",
                                                  "SQLite Database File (*.db);;All Files (*)", options=options)
        if fileName:
            current_db_path = 'example.db' 
            try:
                # Копирование файла базы данных
                with open(current_db_path, 'rb') as f:
                    db_data = f.read()
                with open(fileName, 'wb') as f:
                    f.write(db_data)
                QMessageBox.information(self, "Успех", "База данных успешно сохранена!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при сохранении: {e}")

    def setup_custom_query_tab(self):
        self.custom_query_tab = QWidget()
        self.custom_query_layout = QVBoxLayout()
        self.custom_query_table = QTableView()
        self.custom_query_model = QSqlQueryModel()

        # Создание QComboBox для выбора фамилии читателя
        self.reader_surname_combobox = QComboBox()
        self.load_reader_surnames()
        self.reader_surname_combobox.currentIndexChanged.connect(self.update_custom_query)

        self.custom_query_layout.addWidget(self.reader_surname_combobox)
        self.custom_query_layout.addWidget(self.custom_query_table)
        self.custom_query_tab.setLayout(self.custom_query_layout)
        self.tabs.addTab(self.custom_query_tab, 'Запрос книг по читателю')

    def load_reader_surnames(self):
        self.reader_surname_combobox.clear()
        # Загрузка фамилий читателей из БД в QComboBox
        query = QSqlQuery("SELECT Фамилия FROM Читатель;")
        while query.next():
            surname = query.value(0)
            self.reader_surname_combobox.addItem(surname)

    def update_custom_query(self):
        selected_surname = self.reader_surname_combobox.currentText()
        print(f"Выбранная фамилия: {selected_surname}")
        self.custom_query_model.setQuery(f"""
        SELECT Книги.Название_книги, Книги.Авторы, Книги.Издательство, Книги.Год_издания
        FROM Книги
        JOIN Учет_книг ON Книги.Номер_книги = Учет_книг.Номер_книги
        JOIN Читатель ON Учет_книг.Номер_читательского_билета = Читатель.Номер_читательского_билета
        WHERE Читатель.Фамилия = '{selected_surname}';
        """)
        if self.custom_query_model.lastError().isValid():
            print(f"Ошибка выполнения запроса: {self.custom_query_model.lastError().text()}")
        else:
            self.custom_query_table.setModel(self.custom_query_model)
            self.custom_query_table.resizeColumnsToContents()
        
    def on_tab_clicked(self, index):
        # Проверка, что выбрана вкладка custom_query
        if self.tabs.tabText(index) == 'Запрос книг по читателю':
            self.load_reader_surnames()  # Обновление содержимого QComboBox
            self.update_custom_query()   # Обновление результатов запроса

    # Функция для восстановления БД
    def restore_db(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Открыть файл базы данных", "",
                                                  "SQLite Database File (*.db);;All Files (*)", options=options)
        if fileName:
            current_db_path = 'example.db'
            try:
                with open(fileName, 'rb') as f:
                    db_data = f.read()
                with open(current_db_path, 'wb') as f:
                    f.write(db_data)
                QMessageBox.information(self, "Успех", "База данных успешно восстановлена!")
                self.reload_data_models()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при восстановлении: {e}")
    
    def clear_db(self):
        reply = QMessageBox.question(self, 'Подтверждение',
                                     'Вы уверены, что хотите очистить все данные в БД?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            query = QSqlQuery()
            query.exec_("DELETE FROM Книги;")
            query.exec_("DELETE FROM Читатель;")
            query.exec_("DELETE FROM Учет_книг;")
            self.reload_data_models()
            QMessageBox.information(self, 'Очистка БД', 'Данные успешно удалены.')

    # Функция для перезагрузки моделей данных после восстановления БД
    def reload_data_models(self):
        self.books_model.select()
        self.readers_model.select()
        self.accounting_model.select()
        self.update_overdue_books_tab()
        self.update_readers_report_tab()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec_())
// Генератор тестовых PDF для скила /quiz-from-pdf (macOS: AppKit + PDFKit, без сторонних зависимостей).
//
//   swift tools/quiz-import/fixtures/make_pdfs.swift fixtures [КАТАЛОГ]   — short, sections, scanned, blank, protected
//   swift tools/quiz-import/fixtures/make_pdfs.swift large ФАЙЛ [СТРАНИЦ] — документ больше 100 страниц (по умолчанию 150),
//                                                                       на каждой странице три уникальных синтетических факта
//
// Большой документ не коммитится: его генерируют при проверке сценария «Большой документ без диапазона».

import AppKit
import PDFKit

let pageRect = CGRect(x: 0, y: 0, width: 595, height: 842)  // A4
let margin: CGFloat = 56

struct Page {
    var header: String? = nil
    var title: String? = nil
    var body: [String] = []
    var footer: String? = nil
    var shape = false  // рисунок без текста
}

// ---------- Отрисовка ----------

// Системный шрифт SF при выводе в PDF кладёт в текстовый слой «ĸ» (U+0138) вместо «к», поэтому Helvetica.
func font(_ size: CGFloat, bold: Bool = false) -> NSFont {
    NSFont(name: bold ? "Helvetica-Bold" : "Helvetica", size: size)!
}

func drawText(_ text: String, font: NSFont, color: NSColor = .black, top y: inout CGFloat, spacing: CGFloat) {
    let style = NSMutableParagraphStyle()
    style.lineSpacing = 3
    let string = NSAttributedString(string: text, attributes: [.font: font, .foregroundColor: color, .paragraphStyle: style])
    let width = pageRect.width - 2 * margin
    let height = ceil(string.boundingRect(with: NSSize(width: width, height: 10_000), options: [.usesLineFragmentOrigin]).height)
    string.draw(with: NSRect(x: margin, y: y - height, width: width, height: height), options: [.usesLineFragmentOrigin])
    y -= height + spacing
}

func draw(_ page: Page, in context: CGContext) {
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: context, flipped: false)
    if let header = page.header {
        var y: CGFloat = 812
        drawText(header, font: font(9), color: .darkGray, top: &y, spacing: 0)
    }
    var y: CGFloat = 770
    if let title = page.title {
        drawText(title, font: font(18, bold: true), top: &y, spacing: 16)
    }
    for paragraph in page.body {
        drawText(paragraph, font: font(12), top: &y, spacing: 10)
    }
    if page.shape {
        context.setStrokeColor(gray: 0.3, alpha: 1)
        context.setLineWidth(4)
        context.strokeEllipse(in: CGRect(x: 197, y: 321, width: 200, height: 200))
        context.stroke(CGRect(x: 147, y: 271, width: 300, height: 300))
    }
    if let footer = page.footer {
        var y: CGFloat = 40
        drawText(footer, font: font(9), color: .darkGray, top: &y, spacing: 0)
    }
    NSGraphicsContext.restoreGraphicsState()
}

/// Страница как растровое изображение без текстового слоя — имитация скана.
func rasterize(_ page: Page) -> CGImage {
    let scale: CGFloat = 1.5
    let bitmap = CGContext(data: nil, width: Int(pageRect.width * scale), height: Int(pageRect.height * scale),
                           bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceGray(),
                           bitmapInfo: CGImageAlphaInfo.none.rawValue)!
    bitmap.setFillColor(gray: 1, alpha: 1)
    bitmap.fill(CGRect(x: 0, y: 0, width: bitmap.width, height: bitmap.height))
    bitmap.scaleBy(x: scale, y: scale)
    draw(page, in: bitmap)
    return bitmap.makeImage()!
}

func writePDF(_ pages: [Page], title: String, to path: String, scanned: Bool = false) {
    var box = pageRect
    let info = [kCGPDFContextTitle: title, kCGPDFContextCreator: "make_pdfs.swift"] as CFDictionary
    let context = CGContext(URL(fileURLWithPath: path) as CFURL, mediaBox: &box, info)!
    for page in pages {
        context.beginPDFPage(nil)
        if scanned {
            context.interpolationQuality = .high
            context.draw(rasterize(page), in: pageRect)
        } else {
            draw(page, in: context)
        }
        context.endPDFPage()
    }
    context.closePDF()
}

func protect(_ path: String, password: String) {
    let document = PDFDocument(url: URL(fileURLWithPath: path))!
    let options: [PDFDocumentWriteOption: Any] = [.userPasswordOption: password, .ownerPasswordOption: password + "-owner"]
    guard document.write(to: URL(fileURLWithPath: path), withOptions: options) else {
        fatalError("не удалось зашифровать \(path)")
    }
}

// ---------- Содержимое ----------

func shortDocument() -> [Page] {
    let header = "Биология, 10 класс — конспект урока"
    let texts = [
        ("Фотосинтез", [
            "Фотосинтез — процесс образования органических веществ из углекислого газа и воды на свету при участии фотосинтетических пигментов.",
            "У растений фотосинтез протекает в хлоропластах. Основной пигмент — хлорофилл. Он поглощает главным образом красный и синий свет, а зелёный отражает, поэтому листья кажутся зелёными.",
        ]),
        ("Фазы фотосинтеза", [
            "Световая фаза идёт на мембранах тилакоидов: под действием света происходит фотолиз воды, выделяется кислород, синтезируются АТФ и НАДФ·H.",
            "Темновая фаза идёт в строме хлоропласта: в цикле Кальвина фиксируется углекислый газ и синтезируется глюкоза. Энергию для неё дают АТФ и НАДФ·H световой фазы.",
            "Кислород, выделяемый при фотосинтезе, образуется из молекул воды, а не из углекислого газа.",
        ]),
        ("Значение фотосинтеза", [
            "Суммарное уравнение фотосинтеза: 6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂.",
            "Фотосинтез — источник кислорода атмосферы и органических веществ, с которых начинаются пищевые цепи.",
            "Скорость фотосинтеза зависит от интенсивности света, концентрации углекислого газа и температуры.",
        ]),
    ]
    return texts.enumerated().map { i, item in
        Page(header: header, title: item.0, body: item.1, footer: "— \(i + 1) —")
    }
}

let lectureSections: [(String, [String])] = [
    ("1. Введение в базы данных", [
        "База данных — организованная совокупность данных, которые хранятся и используются в вычислительной системе. Система управления базами данных (СУБД) — комплекс программ для создания баз данных, управления ими и доступа к данным.",
        "До появления СУБД данные хранились в отдельных файлах каждого приложения. Это приводило к дублированию данных и к зависимости программ от формата файлов. СУБД обеспечивает независимость данных: приложения работают с логическим представлением, а не с физическим размещением данных.",
        "Архитектура ANSI/SPARC выделяет три уровня: внешний (представления отдельных пользователей), концептуальный (логическая схема всей базы данных) и внутренний (физическое хранение данных).",
        "По модели данных различают иерархические СУБД (данные образуют дерево, пример — IBM IMS), сетевые (стандарт CODASYL), реляционные и NoSQL-системы: документные, «ключ — значение», колоночные и графовые.",
        "Основные функции СУБД: управление данными во внешней памяти, управление буферами оперативной памяти, управление транзакциями, журналирование и восстановление после сбоев, поддержка языков баз данных.",
        "Язык SQL делится на подмножества: DDL — определение данных (CREATE, ALTER, DROP), DML — манипулирование данными (SELECT, INSERT, UPDATE, DELETE) и DCL — управление доступом (GRANT, REVOKE).",
    ]),
    ("2. Реляционная модель", [
        "Реляционную модель данных предложил сотрудник IBM Эдгар Кодд в 1970 году в статье «A Relational Model of Data for Large Shared Data Banks».",
        "Отношение — множество кортежей с одинаковым набором атрибутов. В таблице отношению соответствует сама таблица, кортежу — строка, атрибуту — столбец. Число атрибутов называют степенью отношения, число кортежей — его мощностью.",
        "Домен — множество допустимых значений атрибута. Значения атрибутов атомарны: в ячейке хранится одно значение, а не список значений.",
        "Потенциальный ключ — минимальный набор атрибутов, однозначно определяющий кортеж. Один из потенциальных ключей выбирают первичным. Первичный ключ не может содержать NULL.",
        "Внешний ключ — атрибут или набор атрибутов, значения которых ссылаются на первичный ключ другого отношения. Ограничение ссылочной целостности запрещает ссылки на несуществующие кортежи.",
        "Основные операции реляционной алгебры: выборка отбирает кортежи по условию, проекция оставляет часть атрибутов, соединение объединяет кортежи двух отношений по условию. Кроме них есть объединение, пересечение, разность и декартово произведение.",
    ]),
    ("3. Язык SQL", [
        "Предложения запроса SELECT логически обрабатываются в порядке FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY. Поэтому псевдоним столбца, заданный в SELECT, нельзя использовать в WHERE.",
        "WHERE фильтрует строки до группировки, а HAVING — группы после неё. Агрегатные функции допустимы в HAVING, но не в WHERE.",
        "Агрегатные функции SQL: COUNT, SUM, AVG, MIN и MAX. COUNT(*) считает все строки, а COUNT(столбец) — только строки, где значение столбца не NULL.",
        "INNER JOIN возвращает только пары строк, удовлетворяющие условию соединения. LEFT JOIN возвращает все строки левой таблицы и дополняет отсутствующие значения правой таблицы NULL. FULL OUTER JOIN возвращает все строки обеих таблиц.",
        "NULL означает отсутствующее или неизвестное значение. Сравнение с NULL через знак равенства даёт UNKNOWN, поэтому для проверки используют IS NULL и IS NOT NULL.",
        "Коррелированный подзапрос ссылается на столбцы внешнего запроса и логически выполняется для каждой его строки. Оператор EXISTS проверяет, возвращает ли подзапрос хотя бы одну строку.",
    ]),
    ("4. Нормализация", [
        "Нормализация — приведение схемы базы данных к нормальным формам, чтобы устранить избыточность и аномалии вставки, обновления и удаления.",
        "Функциональная зависимость A → B означает, что каждому значению атрибута A соответствует ровно одно значение атрибута B.",
        "Отношение находится в первой нормальной форме (1НФ), если все его атрибуты атомарны и в нём нет повторяющихся групп.",
        "Отношение находится во второй нормальной форме (2НФ), если оно в 1НФ и каждый неключевой атрибут зависит от всего первичного ключа, а не от его части. Частичная зависимость возможна только при составном ключе.",
        "Отношение находится в третьей нормальной форме (3НФ), если оно во 2НФ и неключевые атрибуты не зависят от ключа транзитивно. В нормальной форме Бойса — Кодда левая часть любой нетривиальной функциональной зависимости — суперключ.",
        "Денормализация — сознательное введение избыточности ради ускорения чтения, например в хранилищах данных. Её цена — усложнение поддержки согласованности данных.",
    ]),
    ("5. Транзакции", [
        "Транзакция — последовательность операций, выполняемая как единое целое: либо все изменения фиксируются командой COMMIT, либо все отменяются командой ROLLBACK.",
        "Свойства транзакций ACID: атомарность (всё или ничего), согласованность (переход из одного допустимого состояния в другое), изоляция (параллельные транзакции не влияют друг на друга) и долговечность (зафиксированные изменения сохраняются после сбоя).",
        "Аномалии параллельного доступа: грязное чтение — чтение незафиксированных изменений другой транзакции; неповторяемое чтение — повторное чтение строки даёт другое значение; фантомное чтение — повторный запрос возвращает новые строки.",
        "Стандарт SQL определяет уровни изоляции READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ и SERIALIZABLE. Уровень SERIALIZABLE исключает все три аномалии.",
        "Разделяемая блокировка ставится для чтения и совместима с другими разделяемыми; исключительная ставится для записи и несовместима ни с какими. Взаимоблокировка возникает, когда две транзакции ждут ресурсы друг друга; СУБД обнаруживает её и откатывает одну из транзакций.",
        "При журнале упреждающей записи (WAL) изменение сначала записывается в журнал и только потом в файлы данных. После сбоя СУБД повторяет зафиксированные транзакции и отменяет незафиксированные. MVCC хранит несколько версий строки, чтобы читатели не блокировали писателей.",
    ]),
    ("6. Индексы", [
        "Индекс — вспомогательная структура, ускоряющая поиск строк по значениям столбцов. Цена индекса — дополнительная память и замедление вставки и обновления.",
        "B-дерево — сбалансированное дерево и самый распространённый тип индекса. Оно поддерживает поиск по равенству и по диапазону за логарифмическое время.",
        "Хеш-индекс ускоряет только поиск по равенству и не подходит для поиска по диапазону и сортировки.",
        "Составной индекс по столбцам (a, b) используется для условий по a или по a и b, но, как правило, не для условий только по b. Это правило левого префикса.",
        "Кластерный индекс определяет физический порядок строк таблицы, поэтому у таблицы может быть только один кластерный индекс.",
        "План выполнения запроса показывает команда EXPLAIN. Оптимизатор выбирает между последовательным сканированием и индексом по статистике; при низкой селективности условия полное сканирование бывает быстрее индекса.",
    ]),
]

func sectionsDocument() -> [Page] {
    let total = 2 + lectureSections.count * 6 + 2
    let header = "Базы данных. Курс лекций"
    func footer(_ n: Int) -> String { "Страница \(n) из \(total)" }
    var pages = [Page(title: "Базы данных", body: ["Курс лекций", "Учебное пособие для студентов", "2026"])]
    var toc: [String] = []
    var number = 3
    for (title, _) in lectureSections {
        toc.append("\(title) ........ \(number)")
        number += 6
    }
    toc += ["Заключение ........ \(number)", "Список литературы ........ \(number + 1)"]
    pages.append(Page(header: header, title: "Оглавление", body: toc, footer: footer(2)))
    for (title, paragraphs) in lectureSections {
        for (i, paragraph) in paragraphs.enumerated() {
            pages.append(Page(header: "\(header) · \(title)", title: i == 0 ? title : nil, body: [paragraph],
                              footer: footer(pages.count + 1)))
        }
    }
    pages.append(Page(header: header, title: "Заключение", body: [
        "Курс охватывает путь от общих понятий баз данных через реляционную модель и SQL к проектированию схем, транзакциям и индексам. Эти темы составляют основу работы с любой реляционной СУБД.",
    ], footer: footer(pages.count + 1)))
    pages.append(Page(header: header, title: "Список литературы", body: [
        "1. Дейт К. Дж. Введение в системы баз данных.",
        "2. Кузнецов С. Д. Основы баз данных.",
        "3. Codd E. F. A Relational Model of Data for Large Shared Data Banks // Communications of the ACM. 1970.",
    ], footer: footer(pages.count + 1)))
    return pages
}

func scannedDocument() -> [Page] {
    [
        Page(title: "Солнечная система", body: [
            "Солнечная система состоит из Солнца и обращающихся вокруг него объектов: восьми планет, карликовых планет, спутников, астероидов и комет.",
            "Планеты земной группы — Меркурий, Венера, Земля и Марс. Планеты-гиганты — Юпитер, Сатурн, Уран и Нептун.",
        ], footer: "1"),
        Page(title: "Планеты", body: [
            "Самая большая планета Солнечной системы — Юпитер. Ближайшая к Солнцу планета — Меркурий.",
            "Самая горячая планета — Венера: её плотная атмосфера из углекислого газа создаёт сильный парниковый эффект.",
            "В 2006 году Международный астрономический союз отнёс Плутон к карликовым планетам.",
        ], footer: "2"),
    ]
}

func blankDocument() -> [Page] { [Page(), Page(shape: true), Page()] }

func protectedDocument() -> [Page] {
    [Page(title: "Закрытый конспект", body: [
        "Этот документ защищён паролем. Без пароля скил не может прочитать его содержимое и не должен отправлять карточки.",
    ])]
}

/// Большой документ: на каждой странице — три уникальных факта синтетического справочника,
/// чтобы диапазон из 50+ страниц давал больше 150 ключевых положений (сценарий «Большой набор»).
func largeDocument(_ count: Int) -> [Page] {
    let colors = ["бирюзовый", "янтарный", "сиреневый", "оливковый", "пурпурный", "графитовый", "лимонный"]
    return (0..<count).map { i in
        let n = i + 1
        let code = "К-\(100 + n)"
        let hardness = 1 + (n * 7) % 10
        let melting = 600 + (n * 37) % 1400
        let year = 1850 + (n * 13) % 170
        return Page(header: "Условный справочник кристаллов (синтетические тестовые данные) · глава \(i / 10 + 1)",
                    title: "Кристалл \(code)",
                    body: [
                        "Твёрдость кристалла \(code) по шкале Мооса — \(hardness).",
                        "Кристалл \(code) плавится при температуре \(melting) °C.",
                        "Кристалл \(code) впервые описан в \(year) году; его цвет — \(colors[n % colors.count]).",
                    ],
                    footer: "Страница \(n) из \(count)")
    }
}

// ---------- CLI ----------

let args = CommandLine.arguments.dropFirst()
switch args.first {
case "fixtures":
    let dir = args.dropFirst().first ?? "tools/quiz-import/fixtures"
    writePDF(shortDocument(), title: "Фотосинтез", to: "\(dir)/short.pdf")
    writePDF(sectionsDocument(), title: "Базы данных. Курс лекций", to: "\(dir)/sections.pdf")
    writePDF(scannedDocument(), title: "Солнечная система (скан)", to: "\(dir)/scanned.pdf", scanned: true)
    writePDF(blankDocument(), title: "", to: "\(dir)/blank.pdf")
    writePDF(protectedDocument(), title: "Закрытый конспект", to: "\(dir)/protected.pdf")
    protect("\(dir)/protected.pdf", password: "quiz")
    print("Готово: \(dir)/{short,sections,scanned,blank,protected}.pdf")
case "large":
    guard let path = args.dropFirst().first else { fatalError("укажите путь к файлу") }
    let count = args.dropFirst(2).first.flatMap { Int($0) } ?? 150
    writePDF(largeDocument(count), title: "Условный справочник кристаллов", to: path)
    print("Готово: \(path), страниц: \(count)")
default:
    print("Использование: swift make_pdfs.swift fixtures [КАТАЛОГ] | large ФАЙЛ [СТРАНИЦ]")
    exit(1)
}

// Нарезка PDF на части по 10 страниц для скила /quiz-from-pdf (macOS, PDFKit, без сторонних зависимостей).
//
//   swift tools/quiz-import/split_pdf.swift FILE [--pages N|N-M] --count N|auto --out DIR
//
// Read в Claude Code без параметра pages читает PDF только до 10 страниц, а pages требует poppler,
// поэтому выбранный диапазон режется на part-01.pdf, part-02.pdf, … и описывается в DIR/meta.json
// вместе с квотами карточек (сумма квот равна N). С --count auto квоты не считаются (quota: null):
// число карточек определяют ключевые положения.
//
// Коды выхода: 0 — готово, 1 — неверные аргументы или диапазон вне документа, 3 — файл не открывается
// как PDF, 4 — PDF защищён паролем, 5 — больше 100 страниц без диапазона (нужно указать --pages).

import Foundation
import PDFKit

let partPages = 10
let maxPagesWithoutRange = 100
let countRange = 1...50

enum ExitCode: Int32 { case ok = 0, usage = 1, notPDF = 3, locked = 4, tooLarge = 5 }

func fail(_ code: ExitCode, _ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(code.rawValue)
}

// ---------- Аргументы ----------

var file: String?
var pagesArg: String?
var countArg: String?
var outDir: String?
var rest = Array(CommandLine.arguments.dropFirst())
while !rest.isEmpty {
    let arg = rest.removeFirst()
    switch arg {
    case "--pages", "--count", "--out":
        guard !rest.isEmpty else { fail(.usage, "Ошибка: после \(arg) нужно значение") }
        let value = rest.removeFirst()
        if arg == "--pages" { pagesArg = value } else if arg == "--count" { countArg = value } else { outDir = value }
    default:
        if arg.hasPrefix("--") || file != nil { fail(.usage, "Ошибка: неизвестный аргумент \(arg)") }
        file = arg
    }
}
guard let file, let countArg, let outDir else {
    fail(.usage, "Использование: swift split_pdf.swift FILE [--pages N|N-M] --count N|auto --out DIR")
}
/// nil — автоматический режим (--count auto).
let count: Int?
if countArg == "auto" {
    count = nil
} else if let number = Int(countArg), countRange.contains(number) {
    count = number
} else {
    fail(.usage, "Ошибка: количество должно быть целым числом от \(countRange.lowerBound) до \(countRange.upperBound) или auto, получено «\(countArg)»")
}

// ---------- Документ ----------

guard FileManager.default.fileExists(atPath: file) else { fail(.usage, "Ошибка: файл не найден: \(file)") }
guard let document = PDFDocument(url: URL(fileURLWithPath: file)), document.pageCount > 0 else {
    fail(.notPDF, "Не удалось открыть \(file) как PDF: файл повреждён или это не PDF.")
}
if document.isLocked {
    fail(.locked, "Документ \(file) защищён паролем — прочитать его нельзя.")
}
let total = document.pageCount

var first = 1
var last = total
if let pagesArg {
    let bounds = pagesArg.split(separator: "-", omittingEmptySubsequences: false).map { Int($0) }
    guard (1...2).contains(bounds.count), bounds.allSatisfy({ $0 != nil }) else {
        fail(.usage, "Ошибка: диапазон страниц должен быть N или N-M, получено «\(pagesArg)»")
    }
    first = bounds[0]!
    last = bounds.count == 2 ? bounds[1]! : first
    guard first >= 1, first <= last else {
        fail(.usage, "Ошибка: некорректный диапазон «\(pagesArg)»")
    }
    guard last <= total else {
        fail(.usage, "Ошибка: диапазон \(pagesArg) выходит за пределы документа — в нём \(total) стр.")
    }
} else if total > maxPagesWithoutRange {
    fail(.tooLarge, "В документе \(total) стр. — больше \(maxPagesWithoutRange). Укажите диапазон не больше \(maxPagesWithoutRange) страниц, например 1-\(maxPagesWithoutRange).")
}

// ---------- Части и квоты ----------

var parts: [(from: Int, to: Int)] = []
var start = first
while start <= last {
    let end = min(start + partPages - 1, last)
    parts.append((start, end))
    start = end + 1
}

/// Квоты как у fetch_page.py: при count >= частей — каждой 1 и остаток по числу страниц
/// методом наибольших остатков; иначе count частей, равномерно разнесённых по диапазону.
func quotas(weights: [Int], count: Int) -> [Int] {
    let n = weights.count
    if count < n {
        var result = Array(repeating: 0, count: n)
        for i in 0..<count { result[Int(Double(i * n) / Double(count) + 0.5)] = 1 }
        return result
    }
    let extra = count - n
    let sum = Double(weights.reduce(0, +))
    let exact = weights.map { Double(extra) * Double($0) / sum }
    var result = exact.map { Int($0) }
    let order = (0..<n).sorted { (exact[$0] - Double(result[$0]), -$0) > (exact[$1] - Double(result[$1]), -$1) }
    for i in order.prefix(extra - result.reduce(0, +)) { result[i] += 1 }
    return result.map { $0 + 1 }
}

let partQuotas: [Int?] = count.map { quotas(weights: parts.map { $0.to - $0.from + 1 }, count: $0) }
    ?? Array(repeating: nil, count: parts.count)

try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)
var partsMeta: [[String: Any]] = []
for (index, part) in parts.enumerated() {
    let name = String(format: "part-%02d.pdf", index + 1)
    let piece = PDFDocument()
    for number in part.from...part.to {
        piece.insert(document.page(at: number - 1)!.copy() as! PDFPage, at: piece.pageCount)
    }
    guard piece.write(to: URL(fileURLWithPath: outDir).appendingPathComponent(name)) else {
        fail(.notPDF, "Не удалось записать \(name) в \(outDir)")
    }
    partsMeta.append(["file": name, "from": part.from, "to": part.to, "quota": partQuotas[index] ?? NSNull()])
}

let meta: [String: Any] = [
    "file": file,
    "pages": total,
    "range": ["from": first, "to": last],
    "count": count.map { $0 as Any } ?? "auto",
    "parts": partsMeta,
]
let json = try! JSONSerialization.data(withJSONObject: meta, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
try! json.write(to: URL(fileURLWithPath: outDir).appendingPathComponent("meta.json"))
print("Готово: страницы \(first)–\(last) из \(total), частей \(parts.count) → \(outDir)/meta.json")

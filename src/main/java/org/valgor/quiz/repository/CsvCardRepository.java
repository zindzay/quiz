package org.valgor.quiz.repository;

import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVPrinter;
import org.apache.commons.csv.CSVRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.valgor.quiz.config.QuizProperties;
import org.valgor.quiz.model.Card;

/**
 * Хранит карточки в CSV-файле. Все карточки держатся в памяти, при каждом
 * изменении файл перезаписывается целиком через временный файл и атомарную замену.
 * Файл прежнего формата (без колонки review) читается как есть и переводится
 * в новый формат при первой записи.
 */
@Repository
public class CsvCardRepository implements CardRepository {

    private static final Logger log = LoggerFactory.getLogger(CsvCardRepository.class);

    private static final List<String> HEADER = List.of("id", "question", "answer", "review");

    /** Заголовок до появления признака повторения: все карточки читаются с review = false. */
    private static final List<String> LEGACY_HEADER = List.of("id", "question", "answer");

    private static final CSVFormat WRITE_FORMAT = CSVFormat.RFC4180.builder()
            .setHeader(HEADER.toArray(String[]::new))
            .get();

    private static final CSVFormat READ_FORMAT = CSVFormat.RFC4180.builder()
            .setHeader()
            .setSkipHeaderRecord(true)
            .get();

    private final Path file;
    private final ReadWriteLock lock = new ReentrantReadWriteLock();
    private final List<Card> cards;

    @Autowired
    public CsvCardRepository(QuizProperties properties) {
        this(properties.dataFile());
    }

    public CsvCardRepository(Path file) {
        this.file = file;
        if (Files.exists(file)) {
            this.cards = read(file);
        } else {
            this.cards = new ArrayList<>();
            createParentDirectories();
            write(List.of());
        }
        log.info("Файл данных: {}, карточек: {}", file.toAbsolutePath(), cards.size());
    }

    public Path file() {
        return file;
    }

    @Override
    public List<Card> findAll() {
        lock.readLock().lock();
        try {
            return List.copyOf(cards);
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public Optional<Card> findById(String id) {
        lock.readLock().lock();
        try {
            return cards.stream().filter(card -> card.id().equals(id)).findFirst();
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public void save(Card card) {
        lock.writeLock().lock();
        try {
            List<Card> updated = new ArrayList<>(cards);
            updated.add(card);
            write(updated);
            cards.add(card);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public void update(Card card) {
        lock.writeLock().lock();
        try {
            int index = indexOf(card.id());
            if (index < 0) {
                throw new IllegalArgumentException("Карточка не найдена: " + card.id());
            }
            List<Card> updated = new ArrayList<>(cards);
            updated.set(index, card);
            write(updated);
            cards.set(index, card);
        } finally {
            lock.writeLock().unlock();
        }
    }

    private int indexOf(String id) {
        for (int i = 0; i < cards.size(); i++) {
            if (cards.get(i).id().equals(id)) {
                return i;
            }
        }
        return -1;
    }

    private static List<Card> read(Path file) {
        try (Reader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8);
             CSVParser parser = CSVParser.parse(reader, READ_FORMAT)) {
            List<String> header = parser.getHeaderNames();
            if (!HEADER.equals(header) && !LEGACY_HEADER.equals(header)) {
                throw new DataFileException(file, "ожидался заголовок " + String.join(",", HEADER)
                        + " или " + String.join(",", LEGACY_HEADER) + ", найден " + header);
            }
            List<Card> result = new ArrayList<>();
            for (CSVRecord record : parser) {
                if (record.size() != header.size()) {
                    throw new DataFileException(file,
                            "строка " + record.getRecordNumber() + " содержит " + record.size()
                                    + " полей вместо " + header.size());
                }
                boolean review = header.size() == HEADER.size() && parseReview(file, record);
                result.add(new Card(record.get(0), record.get(1), record.get(2), review));
            }
            return result;
        } catch (IOException | UncheckedIOException | IllegalArgumentException | IllegalStateException e) {
            throw new DataFileException(file, "не удалось прочитать: " + e.getMessage(), e);
        }
    }

    private static boolean parseReview(Path file, CSVRecord record) {
        return switch (record.get(3)) {
            case "true" -> true;
            case "false" -> false;
            default -> throw new DataFileException(file, "строка " + record.getRecordNumber()
                    + ": review должно быть true или false, найдено «" + record.get(3) + "»");
        };
    }

    private void createParentDirectories() {
        Path parent = file.toAbsolutePath().getParent();
        try {
            Files.createDirectories(parent);
        } catch (IOException e) {
            throw new DataFileException(file, "не удалось создать директорию " + parent, e);
        }
    }

    private void write(List<Card> toWrite) {
        Path dir = file.toAbsolutePath().getParent();
        Path temp = null;
        try {
            temp = Files.createTempFile(dir, file.getFileName().toString(), ".tmp");
            try (Writer writer = Files.newBufferedWriter(temp, StandardCharsets.UTF_8);
                 CSVPrinter printer = new CSVPrinter(writer, WRITE_FORMAT)) {
                for (Card card : toWrite) {
                    printer.printRecord(card.id(), card.question(), card.answer(), card.review());
                }
            }
            Files.move(temp, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            temp = null;
        } catch (AtomicMoveNotSupportedException e) {
            throw new DataFileException(file, "файловая система не поддерживает атомарную замену файла", e);
        } catch (IOException e) {
            throw new DataFileException(file, "не удалось записать: " + e.getMessage(), e);
        } finally {
            if (temp != null) {
                try {
                    Files.deleteIfExists(temp);
                } catch (IOException ignored) {
                    // временный файл не критичен
                }
            }
        }
    }
}

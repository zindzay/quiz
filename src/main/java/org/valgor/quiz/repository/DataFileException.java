package org.valgor.quiz.repository;

import java.nio.file.Path;

/** Файл данных нельзя прочитать или записать. */
public class DataFileException extends RuntimeException {

    public DataFileException(Path file, String message, Throwable cause) {
        super("Файл данных " + file.toAbsolutePath() + ": " + message, cause);
    }

    public DataFileException(Path file, String message) {
        this(file, message, null);
    }
}

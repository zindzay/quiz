package org.valgor.quiz.config;

import java.nio.file.Path;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("quiz")
public record QuizProperties(Path dataFile) {
}

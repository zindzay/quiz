package org.valgor.quiz;

import java.nio.file.Path;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

@SpringBootTest
class QuizApplicationTests {

    @TempDir
    static Path tempDir;

    @DynamicPropertySource
    static void dataFile(DynamicPropertyRegistry registry) {
        registry.add("quiz.data-file", () -> tempDir.resolve("cards.csv").toString());
    }

    @Test
    void contextLoads() {
    }
}

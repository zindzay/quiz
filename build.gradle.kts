import com.github.gradle.node.npm.task.NpxTask

plugins {
    java
    id("org.springframework.boot") version "4.1.1"
    id("io.spring.dependency-management") version "1.1.7"
    id("com.github.node-gradle.node") version "7.1.0"
}

group = "org.valgor"
version = "1.0-SNAPSHOT"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(27)
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.apache.commons:commons-csv:1.14.1")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}

// UI-тесты (Playwright) — см. ui-tests/ и раздел «Скриншотные тесты» в CLAUDE.md
node {
    download = true
    version = "24.22.0"
    npmInstallCommand = "ci"
    nodeProjectDir = file("ui-tests")
}

val playwrightInstall by tasks.registering(NpxTask::class) {
    group = "verification"
    description = "Скачивает Chromium для Playwright"
    dependsOn(tasks.npmInstall)
    command = "playwright"
    args = listOf("install", "chromium")
}

val uiTestsDir = file("ui-tests")
val bootJarFile = tasks.bootJar.flatMap { it.archiveFile }

/**
 * Запускает Playwright и падает с понятным сообщением. Код выхода npx недоступен,
 * поэтому результат читается из test-results/.last-run.json, который пишет Playwright.
 */
fun NpxTask.runPlaywright(vararg playwrightArgs: String) {
    dependsOn(tasks.bootJar, playwrightInstall)
    command = "playwright"
    args = listOf("test", *playwrightArgs)
    environment.put("QUIZ_JAR", bootJarFile.map { it.asFile.absolutePath })
    ignoreExitValue = true
    val lastRun = uiTestsDir.resolve("test-results/.last-run.json")
    doFirst { lastRun.delete() }
    doLast {
        val status = if (lastRun.exists()) Regex("\"status\":\\s*\"(\\w+)\"").find(lastRun.readText())?.groupValues?.get(1) else null
        if (status != "passed") {
            throw GradleException(
                "UI-тесты не прошли (status=${status ?: "нет результатов: приложение или браузер не запустились"}).\n" +
                    "Отчёт: cd ui-tests && npx playwright show-report\n" +
                    "Diff-изображения: ${uiTestsDir.resolve("test-results")}"
            )
        }
    }
}

val screenshotTest by tasks.registering(NpxTask::class) {
    group = "verification"
    description = "Сравнивает скриншоты веб-интерфейса с эталонами (ui-tests/tests/__screenshots__)"
    runPlaywright()
    inputs.file(bootJarFile)
    inputs.dir("src/main/resources/static")
    inputs.dir("ui-tests/tests")
    inputs.files("ui-tests/playwright.config.ts", "ui-tests/global-teardown.ts", "ui-tests/package-lock.json")
    val marker = layout.buildDirectory.file("ui-tests/screenshot-test.ok")
    outputs.file(marker)
    doLast { marker.get().asFile.writeText("passed\n") }
}

val screenshotUpdate by tasks.registering(NpxTask::class) {
    group = "verification"
    description = "Перезаписывает эталонные скриншоты. Только при намеренном изменении внешнего вида!"
    runPlaywright("--update-snapshots")
}

tasks.check {
    dependsOn(screenshotTest)
}

<?php

require __DIR__ . '/../vendor/autoload.php';

use Core\DB;

$schemaFile = __DIR__ . '/../database/schema/schema.sql';

if (!file_exists($schemaFile)) {
    die("Schema file not found: {$schemaFile}\n");
}

echo "Running migrations...\n";

try {
    $db = DB::getInstance();
    $content = file_get_contents($schemaFile);
    $statements = array_filter(array_map('trim', explode(';', $content)));
    foreach ($statements as $statement) {
        if (!empty($statement) && !str_starts_with($statement, '--')) {
            $db->run($statement);
            echo ".";
        }
    }
    echo "\nMigrations completed successfully!\n";
} catch (\Exception $e) {
    die("Migration failed: " . $e->getMessage() . "\n");
}
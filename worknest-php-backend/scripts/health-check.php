<?php

require __DIR__ . '/../vendor/autoload.php';

use Core\DB;
use Core\App;

echo "=== WorkNest Health Check ===\n\n";

$checks = [];

try {
    $db = DB::getInstance();
    $result = $db->fetch("SELECT 1 as test");
    $checks['database'] = ['status' => 'healthy', 'message' => 'Connected'];
} catch (\Exception $e) {
    $checks['database'] = ['status' => 'unhealthy', 'message' => $e->getMessage()];
}

$storagePath = __DIR__ . '/../storage/uploads';
$checks['storage'] = is_writable($storagePath) 
    ? ['status' => 'healthy', 'message' => 'Writable']
    : ['status' => 'unhealthy', 'message' => 'Not writable'];

$mailConfig = __DIR__ . '/../config/mail.php';
$checks['mail'] = file_exists($mailConfig)
    ? ['status' => 'healthy', 'message' => 'Configured']
    : ['status' => 'unhealthy', 'message' => 'Not configured'];

foreach ($checks as $check => $result) {
    echo "[{$result['status']}] {$check}: {$result['message']}\n";
}

$allHealthy = !in_array('unhealthy', array_column($checks, 'status'));
exit($allHealthy ? 0 : 1);
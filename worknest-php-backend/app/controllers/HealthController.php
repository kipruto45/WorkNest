<?php

namespace App\Controllers;

use Core\Controller;
use Core\DB;

class HealthController extends Controller
{
    public function index(): void
    {
        $checks = [];
        
        try {
            $db = DB::getInstance();
            $db->fetch("SELECT 1");
            $checks['database'] = ['status' => 'healthy'];
        } catch (\Exception $e) {
            $checks['database'] = ['status' => 'unhealthy', 'message' => $e->getMessage()];
        }

        $storagePath = __DIR__ . '/../../storage/uploads';
        $checks['storage'] = is_writable($storagePath)
            ? ['status' => 'healthy']
            : ['status' => 'unhealthy', 'message' => 'Storage not writable'];

        $allHealthy = !in_array('unhealthy', array_column($checks, 'status'));
        
        if ($allHealthy) {
            $this->success(['checks' => $checks], 'All systems operational');
        } else {
            $this->error('Some checks failed', $checks, 503);
        }
    }
}
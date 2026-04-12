<?php

namespace App\Services\Export;

use Dompdf\Dompdf;
use Dompdf\Options;

class PdfExportService
{
    protected string $storagePath;

    public function __construct()
    {
        $this->storagePath = 'storage/uploads/exports';
        if (!is_dir($this->storagePath)) {
            mkdir($this->storagePath, 0755, true);
        }
    }

    public function generateTaskReport(array $tasks, string $teamName): string
    {
        $html = $this->renderTaskReportHtml($tasks, $teamName);
        return $this->generatePdf($html, "task_report_{$teamName}");
    }

    public function generateActivityReport(array $activities, string $teamName): string
    {
        $html = $this->renderActivityReportHtml($activities, $teamName);
        return $this->generatePdf($html, "activity_report_{$teamName}");
    }

    protected function renderTaskReportHtml(array $tasks, string $teamName): string
    {
        $html = '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Task Report - ' . htmlspecialchars($teamName) . '</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        h1 { color: #333; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f5f5f5; }
        .status-todo { color: #6b7280; }
        .status-in_progress { color: #3b82f6; }
        .status-done { color: #10b981; }
    </style>
</head>
<body>
    <h1>Task Report - ' . htmlspecialchars($teamName) . '</h1>
    <p>Generated: ' . date('Y-m-d H:i:s') . '</p>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Due Date</th>
                <th>Created</th>
            </tr>
        </thead>
        <tbody>';
        
        foreach ($tasks as $task) {
            $html .= '<tr>
                <td>' . ($task['id'] ?? '') . '</td>
                <td>' . htmlspecialchars($task['title'] ?? '') . '</td>
                <td class="status-' . ($task['status'] ?? '') . '">' . htmlspecialchars($task['status'] ?? '') . '</td>
                <td>' . htmlspecialchars($task['priority'] ?? '') . '</td>
                <td>' . ($task['due_date'] ?? '-') . '</td>
                <td>' . ($task['created_at'] ?? '') . '</td>
            </tr>';
        }
        
        $html .= '</tbody></table></body></html>';
        return $html;
    }

    protected function renderActivityReportHtml(array $activities, string $teamName): string
    {
        $html = '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Activity Report - ' . htmlspecialchars($teamName) . '</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        h1 { color: #333; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f5f5f5; }
    </style>
</head>
<body>
    <h1>Activity Report - ' . htmlspecialchars($teamName) . '</h1>
    <p>Generated: ' . date('Y-m-d H:i:s') . '</p>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>User</th>
                <th>Action</th>
                <th>Details</th>
            </tr>
        </thead>
        <tbody>';
        
        foreach ($activities as $activity) {
            $html .= '<tr>
                <td>' . ($activity['created_at'] ?? '') . '</td>
                <td>' . htmlspecialchars($activity['user_name'] ?? 'System') . '</td>
                <td>' . htmlspecialchars($activity['action'] ?? '') . '</td>
                <td>' . htmlspecialchars(json_encode($activity['metadata'] ?? [])) . '</td>
            </tr>';
        }
        
        $html .= '</tbody></table></body></html>';
        return $html;
    }

    protected function generatePdf(string $html, string $filename): string
    {
        $options = new Options();
        $options->set('isRemoteEnabled', true);
        
        $dompdf = new Dompdf($options);
        $dompdf->loadHtml($html);
        $dompdf->setPaper('A4', 'landscape');
        $dompdf->render();
        
        $pdfPath = $this->storagePath . '/' . $filename . '_' . date('YmdHis') . '.pdf';
        file_put_contents($pdfPath, $dompdf->output());
        
        return $pdfPath;
    }
}

class CsvExportService
{
    protected string $storagePath;

    public function __construct()
    {
        $this->storagePath = 'storage/uploads/exports';
        if (!is_dir($this->storagePath)) {
            mkdir($this->storagePath, 0755, true);
        }
    }

    public function generateTaskCsv(array $tasks): string
    {
        $filename = 'task_export_' . date('YmdHis') . '.csv';
        $filepath = $this->storagePath . '/' . $filename;
        
        $handle = fopen($filepath, 'w');
        
        fputcsv($handle, ['ID', 'Title', 'Description', 'Status', 'Priority', 'Due Date', 'Created By', 'Created At']);
        
        foreach ($tasks as $task) {
            fputcsv($handle, [
                $task['id'] ?? '',
                $task['title'] ?? '',
                $task['description'] ?? '',
                $task['status'] ?? '',
                $task['priority'] ?? '',
                $task['due_date'] ?? '',
                $task['created_by'] ?? '',
                $task['created_at'] ?? '',
            ]);
        }
        
        fclose($handle);
        return $filepath;
    }

    public function generateMemberWorkloadCsv(array $workload): string
    {
        $filename = 'member_workload_' . date('YmdHis') . '.csv';
        $filepath = $this->storagePath . '/' . $filename;
        
        $handle = fopen($filepath, 'w');
        
        fputcsv($handle, ['Member Name', 'Task Count', 'Completed', 'In Progress', 'Overdue']);
        
        foreach ($workload as $member) {
            fputcsv($handle, [
                $member['name'] ?? '',
                $member['task_count'] ?? 0,
                $member['completed_count'] ?? 0,
                $member['in_progress_count'] ?? 0,
                $member['overdue_count'] ?? 0,
            ]);
        }
        
        fclose($handle);
        return $filepath;
    }
}

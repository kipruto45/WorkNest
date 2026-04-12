<?php

namespace Core;

class Paginator
{
    protected int $currentPage;
    protected int $perPage;
    protected int $total;
    protected int $lastPage;
    protected array $items = [];

    public function __construct(array $items, int $total, int $currentPage, int $perPage)
    {
        $this->items = $items;
        $this->total = $total;
        $this->currentPage = $currentPage;
        $this->perPage = $perPage;
        $this->lastPage = (int) ceil($total / $perPage);
    }

    public static function make(array $items, int $total, int $currentPage, int $perPage = 15): self
    {
        return new self($items, $total, $currentPage, $perPage);
    }

    public function currentPage(): int
    {
        return $this->currentPage;
    }

    public function lastPage(): int
    {
        return $this->lastPage;
    }

    public function perPage(): int
    {
        return $this->perPage;
    }

    public function total(): int
    {
        return $this->total;
    }

    public function hasMore(): bool
    {
        return $this->currentPage < $this->lastPage;
    }

    public function hasPages(): bool
    {
        return $this->lastPage > 1;
    }

    public function items(): array
    {
        return $this->items;
    }

    public function toArray(): array
    {
        return [
            'data' => $this->items,
            'meta' => [
                'current_page' => $this->currentPage,
                'last_page' => $this->lastPage,
                'per_page' => $this->perPage,
                'total' => $this->total,
                'from' => ($this->currentPage - 1) * $this->perPage + 1,
                'to' => min($this->currentPage * $this->perPage, $this->total),
                'has_more' => $this->hasMore(),
            ],
        ];
    }

    public static function calculateOffset(int $page, int $perPage): int
    {
        return ($page - 1) * $perPage;
    }

    public static function getCurrentPage(): int
    {
        $page = Request::capture()->get('page', 1);
        return max(1, (int) $page);
    }

    public static function getPerPage(int $default = 15, int $max = 100): int
    {
        $perPage = Request::capture()->get('per_page', $default);
        return min(max(1, (int) $perPage), $max);
    }
}
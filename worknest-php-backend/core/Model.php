<?php

namespace Core;

use PDO;

abstract class Model
{
    protected string $table = '';
    protected string $primaryKey = 'id';
    protected array $fillable = [];
    protected array $hidden = [];
    protected array $casts = [];
    protected bool $timestamps = true;
    protected string $dateFormat = 'Y-m-d H:i:s';

    public function __construct()
    {
        if (empty($this->table)) {
            $this->table = $this->getTableName();
        }
    }

    protected function getTableName(): string
    {
        $class = basename(str_replace('\\', '/', static::class));
        return strtolower(pluralize($class));
    }

    protected function getDB(): DB
    {
        return DB::getInstance();
    }

    public static function query(): \stdClass
    {
        $model = new static();
        $query = new \stdClass();
        $query->model = $model;
        $query->where = [];
        $query->orderBy = [];
        $query->limit = null;
        $query->offset = null;
        $query->columns = '*';
        return $query;
    }

    public static function find(int $id): ?static
    {
        $model = new static();
        $db = $model->getDB();

        $data = $db->fetch(
            "SELECT * FROM {$model->table} WHERE {$model->primaryKey} = ? AND deleted_at IS NULL",
            [$id]
        );

        if (!$data) {
            return null;
        }

        return static::hydrate($data);
    }

    public static function findOrFail(int $id): static
    {
        $model = static::find($id);
        if (!$model) {
            throw new \RuntimeException('Resource not found');
        }
        return $model;
    }

    public static function first(array $conditions = []): ?static
    {
        $model = new static();
        return $model->where($conditions)->first();
    }

    public function where(array $conditions): self
    {
        $this->queryBuilder['where'] = $conditions;
        return $this;
    }

    public static function all(): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT * FROM {$model->table} WHERE deleted_at IS NULL ORDER BY created_at DESC"
        );
    }

    public static function create(array $data): static
    {
        $model = new static();
        $fillable = array_intersect_key($data, array_flip($model->fillable));
        $fillable = $model->filterFillable($fillable);
        $fillable['created_at'] = date($model->dateFormat);
        $fillable['updated_at'] = date($model->dateFormat);

        $columns = implode(', ', array_keys($fillable));
        $placeholders = implode(', ', array_fill(0, count($fillable), '?'));

        $db = $model->getDB();
        $db->run(
            "INSERT INTO {$model->table} ({$columns}) VALUES ({$placeholders})",
            array_values($fillable)
        );

        $id = $db->lastInsertId();
        return static::find($id);
    }

    public function update(array $data): bool
    {
        $fillable = array_intersect_key($data, array_flip($this->fillable));
        $fillable = $this->filterFillable($fillable);
        $fillable['updated_at'] = date($this->dateFormat);

        $sets = implode(' = ?, ', array_keys($fillable)) . ' = ?';

        $db = $this->getDB();
        $result = $db->run(
            "UPDATE {$this->table} SET {$sets} WHERE {$this->primaryKey} = ?",
            array_merge(array_values($fillable), [$this->{$this->primaryKey}])
        );

        return $result->rowCount() > 0;
    }

    public function delete(): bool
    {
        $db = $this->getDB();
        $result = $db->run(
            "DELETE FROM {$this->table} WHERE {$this->primaryKey} = ?",
            [$this->{$this->primaryKey}]
        );

        return $result->rowCount() > 0;
    }

    public function softDelete(): bool
    {
        $db = $this->getDB();
        $result = $db->run(
            "UPDATE {$this->table} SET deleted_at = ? WHERE {$this->primaryKey} = ?",
            [date($this->dateFormat), $this->{$this->primaryKey}]
        );

        return $result->rowCount() > 0;
    }

    public static function count(): int
    {
        $model = new static();
        $db = $model->getDB();

        $result = $db->fetch(
            "SELECT COUNT(*) as count FROM {$model->table} WHERE deleted_at IS NULL"
        );

        return (int) $result['count'];
    }

    protected function filterFillable(array $data): array
    {
        return array_filter($data, fn($value) => $value !== null);
    }

    public static function hydrate(array $data): static
    {
        $model = new static();
        foreach ($data as $key => $value) {
            if (property_exists($model, $key) || in_array($key, $model->fillable)) {
                $model->{$key} = $value;
            }
        }
        return $model;
    }

    public function toArray(): array
    {
        $data = [];
        $vars = get_object_vars($this);

        foreach ($vars as $key => $value) {
            if (!in_array($key, $this->hidden) && !str_starts_with($key, '_')) {
                if (isset($this->casts[$key])) {
                    $data[$key] = $this->castAttribute($key, $value);
                } else {
                    $data[$key] = $value;
                }
            }
        }

        return $data;
    }

    protected function castAttribute(string $key, $value)
    {
        $cast = $this->casts[$key] ?? null;

        return match ($cast) {
            'int', 'integer' => (int) $value,
            'float' => (float) $value,
            'bool', 'boolean' => (bool) $value,
            'array' => is_array($value) ? $value : json_decode($value, true),
            'json' => json_encode($value),
            'datetime' => $value instanceof \DateTime ? $value->format($this->dateFormat) : $value,
            default => $value,
        };
    }

    public function __get(string $key)
    {
        return null;
    }

    public function __set(string $key, $value)
    {
        $this->{$key} = $value;
    }

    public function __call(string $method, array $args)
    {
        return null;
    }

    public static function __callStatic(string $method, array $args)
    {
        return null;
    }
}

if (!function_exists('pluralize')) {
    function pluralize(string $word): string
    {
        if (preg_match('/(s|x|z|ch|sh)$/', $word)) {
            return $word . 'es';
        }
        if (preg_match('/([^aeiou])y$/', $word, $matches)) {
            return substr($word, 0, -1) . 'ies';
        }
        return $word . 's';
    }
}
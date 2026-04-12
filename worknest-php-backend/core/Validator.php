<?php

namespace Core;

class Validator
{
    protected array $data = [];
    protected array $rules = [];
    protected array $errors = [];

    public function __construct(array $data = [], array $rules = [])
    {
        $this->data = $data;
        $this->rules = $rules;
    }

    public static function make(array $data, array $rules): self
    {
        return new self($data, $rules);
    }

    public function validate(): bool
    {
        $this->errors = [];

        foreach ($this->rules as $field => $rule) {
            $rules = explode('|', $rule);
            $value = $this->data[$field] ?? null;

            foreach ($rules as $r) {
                $this->applyRule($field, $value, $r);
            }
        }

        return empty($this->errors);
    }

    protected function applyRule(string $field, $value, string $rule): void
    {
        $parts = explode(':', $rule);
        $ruleName = $parts[0];
        $ruleParam = $parts[1] ?? null;

        $method = 'validate' . ucfirst($ruleName);
        $param = $ruleParam;
        if (method_exists($this, $method)) {
            if (!$this->$method($value, $param)) {
                $this->addError($field, $this->getMessage($field, $ruleName, $param));
            }
        } else if (is_callable($rule)) {
            if (!$rule($value)) {
                $this->addError($field, "The {$field} is invalid");
            }
        }
    }

    protected function addError(string $field, string $message): void
    {
        if (!isset($this->errors[$field])) {
            $this->errors[$field] = [];
        }
        $this->errors[$field][] = $message;
    }

    protected function getMessage(string $field, string $rule, ?string $param = null): string
    {
        $messages = [
            'required' => "The {$field} is required",
            'email' => "The {$field} must be a valid email",
            'min' => "The {$field} must be at least {$param} characters",
            'max' => "The {$field} must not exceed {$param} characters",
            'unique' => "The {$field} already exists",
            'exists' => "The {$field} does not exist",
            'confirmed' => "The {$field} confirmation does not match",
            'same' => "The {$field} must match {$param}",
            'numeric' => "The {$field} must be a number",
            'integer' => "The {$field} must be an integer",
            'url' => "The {$field} must be a valid URL",
            'date' => "The {$field} must be a valid date",
            'after' => "The {$field} must be after {$param}",
            'before' => "The {$field} must be before {$param}",
            'in' => "The selected {$field} is invalid",
            'array' => "The {$field} must be an array",
            'file' => "The {$field} must be a file",
            'image' => "The {$field} must be an image",
            'mimes' => "The {$field} must be of type: {$param}",
        ];

        return $messages[$rule] ?? "The {$field} is invalid";
    }

    public function fails(): bool
    {
        return !empty($this->errors);
    }

    public function errors(): array
    {
        return $this->errors;
    }

    public function firstError(): ?string
    {
        foreach ($this->errors as $fieldErrors) {
            if (!empty($fieldErrors)) {
                return $fieldErrors[0];
            }
        }
        return null;
    }

    protected function validateRequired($value): bool
    {
        if (is_null($value)) {
            return false;
        }
        if (is_string($value) && trim($value) === '') {
            return false;
        }
        return true;
    }

    protected function validateEmail($value): bool
    {
        return filter_var($value, FILTER_VALIDATE_EMAIL) !== false;
    }

    protected function validateMin($value, $param): bool
    {
        if (is_numeric($value)) {
            return $value >= $param;
        }
        if (is_string($value)) {
            return mb_strlen($value) >= $param;
        }
        if (is_array($value)) {
            return count($value) >= $param;
        }
        return false;
    }

    protected function validateMax($value, $param): bool
    {
        if (is_numeric($value)) {
            return $value <= $param;
        }
        if (is_string($value)) {
            return mb_strlen($value) <= $param;
        }
        if (is_array($value)) {
            return count($value) <= $param;
        }
        return false;
    }

    protected function validateUnique($value, $param): bool
    {
        if (!$value) {
            return true;
        }

        $table = $param ?? 'users';
        $db = DB::getInstance();
        $result = $db->fetch("SELECT id FROM {$table} WHERE email = ?", [$value]);
        return !$result;
    }

    protected function validateExists($value, $param): bool
    {
        if (!$value) {
            return false;
        }

        $parts = explode(',', $param);
        $table = $parts[0];
        $column = $parts[1] ?? 'id';

        $db = DB::getInstance();
        $result = $db->fetch("SELECT id FROM {$table} WHERE {$column} = ?", [$value]);
        return (bool) $result;
    }

    protected function validateNumeric($value): bool
    {
        return is_numeric($value);
    }

    protected function validateInteger($value): bool
    {
        return filter_var($value, FILTER_VALIDATE_INT) !== false;
    }

    protected function validateUrl($value): bool
    {
        return filter_var($value, FILTER_VALIDATE_URL) !== false;
    }

    protected function validateDate($value): bool
    {
        return strtotime($value) !== false;
    }

    protected function validateArray($value): bool
    {
        return is_array($value);
    }

    protected function validateIn($value, $param): bool
    {
        $values = explode(',', $param);
        return in_array($value, $values);
    }

    protected function validateSame($value, $param): bool
    {
        return isset($this->data[$param]) && $value === $this->data[$param];
    }

    protected function validateImage($value): bool
    {
        if (!isset($value['type']) && !isset($value['tmp_name'])) {
            return false;
        }

        $type = $value['type'] ?? '';
        $allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        return in_array($type, $allowed);
    }

    protected function validateFile($value): bool
    {
        return isset($value['tmp_name']) && is_uploaded_file($value['tmp_name']);
    }
}
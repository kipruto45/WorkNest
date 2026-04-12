<?php

namespace Core;

class App
{
    protected static array $config = [];
    protected static array $bindings = [];

    public static function loadConfig(): void
    {
        $configFiles = glob(__DIR__ . '/../config/*.php');
        foreach ($configFiles as $file) {
            $key = basename($file, '.php');
            static::$config[$key] = require $file;
        }
    }

    public static function config(string $key, $default = null)
    {
        $keys = explode('.', $key);
        $value = static::$config;

        foreach ($keys as $k) {
            if (!isset($value[$k])) {
                return $default;
            }
            $value = $value[$k];
        }

        return $value;
    }

    public static function bind(string $abstract, $concrete): void
    {
        static::$bindings[$abstract] = $concrete;
    }

    public static function make(string $abstract)
    {
        if (isset(static::$bindings[$abstract])) {
            $concrete = static::$bindings[$abstract];
            if (is_callable($concrete)) {
                return $concrete();
            }
            return new $concrete();
        }

        if (class_exists($abstract)) {
            return new $abstract();
        }

        throw new \RuntimeException("Unable to resolve: {$abstract}");
    }

    public static function environment(): string
    {
        return static::config('app.env', 'production');
    }

    public static function isLocal(): bool
    {
        return static::environment() === 'local';
    }

    public static function isDebug(): bool
    {
        return (bool) static::config('app.debug', false);
    }
}
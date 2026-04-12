<?php

namespace Core;

class CSRF
{
    public static function token(): string
    {
        return Session::token();
    }

    public static function field(): string
    {
        return '<input type="hidden" name="_token" value="' . static::token() . '">';
    }

    public static function tokenInput(): string
    {
        return static::field();
    }

    public static function verify(string $token): bool
    {
        if (!$token || !Session::has('_token')) {
            return false;
        }

        return hash_equals(Session::get('_token'), $token);
    }

    public static function verifyOrFail(): void
    {
        $token = Request::capture()->input('_token');
        if (!static::verify($token)) {
            throw new \RuntimeException('Invalid CSRF token');
        }
    }
}

class Request
{
    public static function capture(): \Core\Request
    {
        return new \Core\Request();
    }
}
<?php

namespace App\Controllers;

use App\Services\AuthService;
use App\Services\EmailService;
use Core\Controller;
use Core\Request;
use Core\Auth;
use Core\Token;

class AuthController extends Controller
{
    protected AuthService $authService;
    protected EmailService $emailService;

    public function __construct()
    {
        parent::__construct();
        $this->authService = new AuthService();
        $this->emailService = new EmailService();
    }

    public function register(): void
    {
        $data = $this->all();

        $validator = $this->validate($data, [
            'name' => 'required|min:2|max:255',
            'email' => 'required|email|unique:users',
            'password' => 'required|min:8',
            'password_confirm' => 'required|same:password',
        ]);

        if ($validator->fails()) {
            $this->validationError('Registration failed', $validator->errors());
            return;
        }

        try {
            $user = $this->authService->register($data);
            Auth::login($user->id);

            $this->success([
                'user' => $user->toArray(),
                'token' => Token::generateApiToken(),
            ], 'Registration successful');
        } catch (\RuntimeException $e) {
            $this->error($e->getMessage());
        }
    }

    public function login(): void
    {
        $data = $this->all();

        $validator = $this->validate($data, [
            'email' => 'required|email',
            'password' => 'required',
        ]);

        if ($validator->fails()) {
            $this->validationError('Login failed', $validator->errors());
            return;
        }

        try {
            $user = $this->authService->login($data);

            if (!$user) {
                $this->error('Invalid email or password');
                return;
            }

            if ($this->authService->isLocked($user->id)) {
                $this->error('Account is temporarily locked. Please try again later.');
                return;
            }

            $token = Token::generateApiToken();
            Token::storeApiToken($token, $user->id);

            $this->success([
                'user' => $user->toArray(),
                'token' => $token,
            ], 'Login successful');
        } catch (\RuntimeException $e) {
            $this->error($e->getMessage());
        }
    }

    public function logout(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $token = $this->request->bearerToken();
        if ($token) {
            Token::revokeApiToken($token);
        }

        $this->authService->logout($this->user()->id);
        $this->success([], 'Logged out successfully');
    }

    public function forgotPassword(): void
    {
        $data = $this->all();

        $validator = $this->validate($data, [
            'email' => 'required|email',
        ]);

        if ($validator->fails()) {
            $this->validationError('Request failed', $validator->errors());
            return;
        }

        $result = $this->authService->forgotPassword($data['email']);
        $this->success(['sent' => $result], 'If the email exists, a reset link has been sent');
    }

    public function resetPassword(): void
    {
        $data = $this->all();

        $validator = $this->validate($data, [
            'token' => 'required',
            'password' => 'required|min:8',
            'password_confirm' => 'required|same:password',
        ]);

        if ($validator->fails()) {
            $this->validationError('Reset failed', $validator->errors());
            return;
        }

        $result = $this->authService->resetPassword($data['token'], $data['password']);

        if (!$result) {
            $this->error('Invalid or expired reset token');
            return;
        }

        $this->success([], 'Password reset successfully');
    }

    public function changePassword(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();

        $validator = $this->validate($data, [
            'current_password' => 'required',
            'password' => 'required|min:8',
            'password_confirm' => 'required|same:password',
        ]);

        if ($validator->fails()) {
            $this->validationError('Change failed', $validator->errors());
            return;
        }

        $result = $this->authService->changePassword(
            $this->user()->id,
            $data['current_password'],
            $data['password']
        );

        if (!$result) {
            $this->error('Current password is incorrect');
            return;
        }

        $this->success([], 'Password changed successfully');
    }

    public function verifyEmail(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();

        $validator = $this->validate($data, [
            'token' => 'required',
        ]);

        if ($validator->fails()) {
            $this->error('Verification token is required');
            return;
        }

        $result = $this->authService->verifyEmail($this->user()->id, $data['token']);

        if (!$result) {
            $this->error('Invalid or expired verification token');
            return;
        }

        $this->success([], 'Email verified successfully');
    }

    protected function validate(array $data, array $rules)
    {
        $validator = new \Core\Validator($data, $rules);
        $validator->validate();
        return $validator;
    }
}
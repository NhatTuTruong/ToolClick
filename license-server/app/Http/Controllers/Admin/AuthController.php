<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;

class AuthController extends Controller
{
    public function showLogin()
    {
        if (session('admin_ok')) {
            return redirect()->route('keys.index');
        }

        return view('auth.login');
    }

    public function login(Request $request)
    {
        $data = $request->validate([
            'email' => 'required|email',
            'password' => 'required|string',
        ]);

        $ok = hash_equals((string) config('license.admin_email'), $data['email'])
            && hash_equals((string) config('license.admin_password'), $data['password']);

        if (! $ok) {
            return back()->withErrors(['email' => 'Sai email hoặc mật khẩu.'])->onlyInput('email');
        }

        $request->session()->regenerate();
        $request->session()->put('admin_ok', true);
        $request->session()->put('admin_email', $data['email']);

        return redirect()->route('keys.index');
    }

    public function logout(Request $request)
    {
        $request->session()->forget(['admin_ok', 'admin_email']);
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect()->route('login');
    }
}

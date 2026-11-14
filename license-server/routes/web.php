<?php

use App\Http\Controllers\Admin\AuthController;
use App\Http\Controllers\Admin\LicenseKeyController;
use App\Http\Controllers\Admin\StatsController;
use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return redirect()->route('keys.index');
});

Route::get('/login', [AuthController::class, 'showLogin'])->name('login');
Route::post('/login', [AuthController::class, 'login'])->name('login.attempt');
Route::post('/logout', [AuthController::class, 'logout'])->name('logout');

Route::middleware('admin')->group(function () {
    Route::get('/keys', [LicenseKeyController::class, 'index'])->name('keys.index');
    Route::post('/keys', [LicenseKeyController::class, 'upsert'])->name('keys.upsert');
    Route::post('/keys/generate', [LicenseKeyController::class, 'generate'])->name('keys.generate');
    Route::patch('/keys/{license}', [LicenseKeyController::class, 'update'])->name('keys.update');
    Route::delete('/keys/{license}', [LicenseKeyController::class, 'destroy'])->name('keys.destroy');
    Route::delete('/machines/{machine}', [LicenseKeyController::class, 'revokeMachine'])->name('machines.revoke');
    Route::get('/stats', [StatsController::class, 'index'])->name('stats.index');
});

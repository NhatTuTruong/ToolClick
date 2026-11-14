<?php

use App\Http\Controllers\Api\LicenseController;
use App\Http\Controllers\Api\LicenseStatsController;
use Illuminate\Support\Facades\Route;

Route::middleware('license.secret')->group(function () {
    Route::post('/license/activate', [LicenseController::class, 'activate']);
    Route::post('/license/heartbeat', [LicenseController::class, 'heartbeat']);
    Route::post('/license/stats', [LicenseStatsController::class, 'store']);
});

<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class VerifyLicenseSecret
{
    public function handle(Request $request, Closure $next): Response
    {
        $secret = (string) config('license.api_secret');
        if ($secret === '') {
            return $next($request);
        }

        $given = (string) $request->header('X-License-Secret', '');
        if ($given === '' || ! hash_equals($secret, $given)) {
            return response()->json(['ok' => false, 'error' => 'Sai LICENSE_API_SECRET.'], 401);
        }

        return $next($request);
    }
}

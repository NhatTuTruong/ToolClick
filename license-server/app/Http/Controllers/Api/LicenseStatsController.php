<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\LicenseKey;
use App\Models\LicenseRunStat;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Throwable;

class LicenseStatsController extends Controller
{
    public function store(Request $request): JsonResponse
    {
        try {
            $keywords = $this->lines($request->input('keywords'));
            $click = $this->lines($request->input('click_domains'));
            $skip = $this->lines($request->input('skip_domains'));
            $code = LicenseKey::normalizeCode((string) $request->input('key', ''));
            $license = $code !== '' ? LicenseKey::query()->where('code', $code)->first() : null;

            LicenseRunStat::query()->create([
                'license_key_id' => $license?->id,
                'key_code' => $code !== '' ? $code : null,
                'key_note' => $license?->note ?: $this->clip($request->input('key_note'), 255),
                'keywords' => implode("\n", $keywords),
                'keyword_count' => count($keywords),
                'click_domains' => implode("\n", $click),
                'click_domain_count' => count($click),
                'skip_domains' => implode("\n", $skip),
                'skip_domain_count' => count($skip),
                'serp_rounds' => max(1, (int) $request->input('serp_rounds', 1)),
                'ads_found' => max(0, (int) $request->input('ads_found', 0)),
                'clicks_ok' => max(0, (int) $request->input('clicks_ok', 0)),
                'ip' => $this->clip($request->ip() ?: $request->input('ip'), 64),
                'hostname' => $this->clip($request->input('hostname'), 191),
                'machine_id' => $this->clip($request->input('machine_id'), 128),
                'ran_at' => now(),
            ]);

            return response()->json(['ok' => true, 'stored' => true]);
        } catch (Throwable) {
            return response()->json(['ok' => true, 'stored' => false], 200);
        }
    }

    /**
     * @return list<string>
     */
    private function lines(mixed $raw): array
    {
        if (is_array($raw)) {
            $parts = $raw;
        } else {
            $parts = preg_split('/[\r\n,|]+/', (string) $raw) ?: [];
        }
        $out = [];
        foreach ($parts as $p) {
            $s = trim((string) $p);
            if ($s !== '') {
                $out[] = $s;
            }
        }

        return array_values(array_unique($out));
    }

    private function clip(mixed $value, int $max): ?string
    {
        $s = trim((string) $value);
        if ($s === '') {
            return null;
        }

        return mb_substr($s, 0, $max);
    }
}

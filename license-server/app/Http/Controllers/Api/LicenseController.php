<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\LicenseDailyUsage;
use App\Models\LicenseKey;
use App\Models\LicenseMachine;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class LicenseController extends Controller
{
    public function activate(Request $request): JsonResponse
    {
        $data = $this->validatedMachine($request);
        $key = $this->findActiveKey($data['key']);
        if ($key instanceof JsonResponse) {
            return $key;
        }

        $machine = $this->bindMachine($key, $data);
        if ($machine instanceof JsonResponse) {
            return $machine;
        }

        return $this->ok($key, $machine, 'Đã kích hoạt key trên máy này.');
    }

    public function heartbeat(Request $request): JsonResponse
    {
        $data = $this->validatedMachine($request, withUsage: true);
        $key = $this->findActiveKey($data['key']);
        if ($key instanceof JsonResponse) {
            return $key;
        }

        $machine = $this->bindMachine($key, $data);
        if ($machine instanceof JsonResponse) {
            return $machine;
        }

        $delta = max(0, (int) ($data['records_delta'] ?? 0));
        if ($delta > 0) {
            if ($key->todayUsageTotal() + $delta > $key->daily_record_limit) {
                return response()->json([
                    'ok' => false,
                    'error' => 'Hết hạn mức record / ngày ('.$key->daily_record_limit.').',
                    'remaining_today' => $key->remainingToday(),
                ], 429);
            }
            LicenseDailyUsage::addFor($key, $machine->machine_id, $delta);
        }

        return $this->ok($key, $machine, 'Key hợp lệ.');
    }

    private function validatedMachine(Request $request, bool $withUsage = false): array
    {
        $rules = [
            'key' => 'required|string|max:64',
            'machine_id' => 'required|string|max:128',
            'hostname' => 'nullable|string|max:191',
            'os' => 'nullable|string|max:64',
        ];
        if ($withUsage) {
            $rules['records_delta'] = 'nullable|integer|min:0|max:100000';
        }

        $data = $request->validate($rules);
        $data['key'] = LicenseKey::normalizeCode($data['key']);

        return $data;
    }

    private function findActiveKey(string $code): LicenseKey|JsonResponse
    {
        $key = LicenseKey::query()->where('code', $code)->first();
        if (! $key) {
            return response()->json(['ok' => false, 'error' => 'Key không tồn tại.'], 404);
        }
        if ($key->status !== 'active') {
            return response()->json(['ok' => false, 'error' => 'Key đang tạm khóa.'], 403);
        }
        if ($key->expires_at && $key->expires_at->copy()->endOfDay()->isPast()) {
            return response()->json(['ok' => false, 'error' => 'Key đã hết hạn dùng.'], 403);
        }

        return $key;
    }

    private function bindMachine(LicenseKey $key, array $data): LicenseMachine|JsonResponse
    {
        $machine = $key->machines()->where('machine_id', $data['machine_id'])->first();
        $activeCount = $key->activeMachines()->count();

        if ($machine) {
            if ($machine->revoked) {
                if ($activeCount >= $key->max_machines) {
                    return response()->json([
                        'ok' => false,
                        'error' => 'Đã đủ số máy tối đa ('.$key->max_machines.').',
                    ], 403);
                }
                $machine->revoked = false;
                $machine->activated_at = now();
            }
        } else {
            if ($activeCount >= $key->max_machines) {
                return response()->json([
                    'ok' => false,
                    'error' => 'Đã đủ số máy tối đa ('.$key->max_machines.').',
                ], 403);
            }
            $machine = new LicenseMachine([
                'license_key_id' => $key->id,
                'machine_id' => $data['machine_id'],
                'activated_at' => now(),
                'revoked' => false,
            ]);
        }

        $machine->hostname = $data['hostname'] ?? $machine->hostname;
        $machine->os = $data['os'] ?? $machine->os;
        $machine->last_seen_at = now();
        $machine->save();

        return $machine;
    }

    private function ok(LicenseKey $key, LicenseMachine $machine, string $message): JsonResponse
    {
        $key->refresh();

        return response()->json([
            'ok' => true,
            'message' => $message,
            'key' => $key->code,
            'status' => $key->status,
            'expires_at' => optional($key->expires_at)?->toDateString(),
            'max_machines' => $key->max_machines,
            'machines_active' => $key->activeMachines()->count(),
            'daily_record_limit' => $key->daily_record_limit,
            'used_today' => $key->todayUsageTotal(),
            'remaining_today' => $key->remainingToday(),
            'net' => $key->net,
            'note' => $key->note,
            'machine' => [
                'id' => $machine->machine_id,
                'hostname' => $machine->hostname,
                'last_seen_at' => optional($machine->last_seen_at)?->toIso8601String(),
            ],
        ]);
    }
}

<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\LicenseKey;
use App\Models\LicenseMachine;
use Illuminate\Http\Request;

class LicenseKeyController extends Controller
{
    public function index(Request $request)
    {
        $q = trim((string) $request->get('q', ''));
        $keys = LicenseKey::query()
            ->with(['activeMachines'])
            ->withCount(['activeMachines as machines_active_count'])
            ->when($q !== '', function ($query) use ($q) {
                $query->where(function ($inner) use ($q) {
                    $inner->where('code', 'like', '%'.$q.'%')
                        ->orWhere('note', 'like', '%'.$q.'%')
                        ->orWhere('net', 'like', '%'.$q.'%');
                });
            })
            ->latest('id')
            ->paginate(20)
            ->withQueryString();

        return view('keys.index', compact('keys', 'q'));
    }

    public function upsert(Request $request)
    {
        $data = $request->validate([
            'code' => 'nullable|string|max:64',
            'daily_record_limit' => 'required|integer|min:0|max:10000000',
            'max_machines' => 'required|integer|min:1|max:1000',
            'expires_at' => 'nullable|date',
            'note' => 'nullable|string|max:255',
            'net' => 'nullable|string|max:500',
        ]);

        $code = LicenseKey::normalizeCode($data['code'] ?? '');
        if ($code === '') {
            do {
                $code = LicenseKey::generateCode();
            } while (LicenseKey::where('code', $code)->exists());
        }

        $key = LicenseKey::query()->firstOrNew(['code' => $code]);
        $created = ! $key->exists;
        $key->fill([
            'daily_record_limit' => $data['daily_record_limit'],
            'max_machines' => $data['max_machines'],
            'expires_at' => $data['expires_at'] ?: null,
            'note' => $data['note'] ?? null,
            'net' => $data['net'] ?? $key->net,
        ]);
        if ($created) {
            $key->status = 'active';
        }
        $key->save();

        $msg = $created
            ? 'Đã tạo key '.$key->code
            : 'Đã cập nhật key '.$key->code;

        return redirect()->route('keys.index')->with('ok', $msg);
    }

    public function generate()
    {
        do {
            $code = LicenseKey::generateCode();
        } while (LicenseKey::where('code', $code)->exists());

        return response()->json(['code' => $code]);
    }

    public function update(Request $request, LicenseKey $license)
    {
        $data = $request->validate([
            'status' => 'required|in:active,paused',
            'daily_record_limit' => 'required|integer|min:0|max:10000000',
            'max_machines' => 'required|integer|min:1|max:1000',
            'expires_at' => 'nullable|date',
            'note' => 'nullable|string|max:255',
            'net' => 'nullable|string|max:500',
        ]);
        $license->update($data);

        return redirect()->route('keys.index')->with('ok', 'Đã lưu key '.$license->code);
    }

    public function destroy(LicenseKey $license)
    {
        $code = $license->code;
        $license->delete();

        return redirect()->route('keys.index')->with('ok', 'Đã xóa key '.$code);
    }

    public function revokeMachine(LicenseMachine $machine)
    {
        $machine->revoked = true;
        $machine->save();

        return redirect()->route('keys.index')->with('ok', 'Đã gỡ máy '.$machine->machine_id);
    }
}

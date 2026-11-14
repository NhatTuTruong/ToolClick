<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Str;

class LicenseKey extends Model
{
    protected $fillable = [
        'code',
        'status',
        'daily_record_limit',
        'max_machines',
        'expires_at',
        'net',
        'note',
    ];

    protected function casts(): array
    {
        return [
            'expires_at' => 'date',
            'daily_record_limit' => 'integer',
            'max_machines' => 'integer',
        ];
    }

    public function machines(): HasMany
    {
        return $this->hasMany(LicenseMachine::class);
    }

    public function usages(): HasMany
    {
        return $this->hasMany(LicenseDailyUsage::class);
    }

    public function activeMachines(): HasMany
    {
        return $this->machines()->where('revoked', false);
    }

    public function isActive(): bool
    {
        if ($this->status !== 'active') {
            return false;
        }
        if ($this->expires_at && $this->expires_at->copy()->endOfDay()->isPast()) {
            return false;
        }

        return true;
    }

    public static function normalizeCode(?string $code): string
    {
        $code = strtoupper(trim((string) $code));
        $code = preg_replace('/\s+/', '', $code) ?? '';

        return $code;
    }

    public static function generateCode(string $prefix = 'TCL1'): string
    {
        $chunk = static function (): string {
            $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
            $out = '';
            for ($i = 0; $i < 4; $i++) {
                $out .= $chars[random_int(0, strlen($chars) - 1)];
            }

            return $out;
        };

        return strtoupper($prefix).'-'.$chunk().'-'.$chunk().'-'.$chunk();
    }

    public function todayUsageTotal(): int
    {
        return (int) $this->usages()
            ->whereDate('usage_date', now()->toDateString())
            ->sum('records_used');
    }

    public function remainingToday(): int
    {
        return max(0, $this->daily_record_limit - $this->todayUsageTotal());
    }
}

<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\UniqueConstraintViolationException;

class LicenseDailyUsage extends Model
{
    protected $fillable = [
        'license_key_id',
        'machine_id',
        'usage_date',
        'records_used',
    ];

    protected function casts(): array
    {
        return [
            'records_used' => 'integer',
        ];
    }

    public function licenseKey(): BelongsTo
    {
        return $this->belongsTo(LicenseKey::class);
    }

    public static function addFor(LicenseKey $key, string $machineId, int $delta): self
    {
        $day = now()->toDateString();
        $usage = static::query()
            ->where('license_key_id', $key->id)
            ->where('machine_id', $machineId)
            ->whereDate('usage_date', $day)
            ->first();

        if (! $usage) {
            try {
                $usage = static::query()->create([
                    'license_key_id' => $key->id,
                    'machine_id' => $machineId,
                    'usage_date' => $day,
                    'records_used' => 0,
                ]);
            } catch (UniqueConstraintViolationException) {
                $usage = static::query()
                    ->where('license_key_id', $key->id)
                    ->where('machine_id', $machineId)
                    ->whereDate('usage_date', $day)
                    ->firstOrFail();
            }
        }

        if ($delta > 0) {
            $usage->increment('records_used', $delta);
            $usage->refresh();
        }

        return $usage;
    }
}

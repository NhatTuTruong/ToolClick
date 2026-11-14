<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class LicenseMachine extends Model
{
    protected $fillable = [
        'license_key_id',
        'machine_id',
        'hostname',
        'os',
        'activated_at',
        'last_seen_at',
        'revoked',
    ];

    protected function casts(): array
    {
        return [
            'activated_at' => 'datetime',
            'last_seen_at' => 'datetime',
            'revoked' => 'boolean',
        ];
    }

    public function licenseKey(): BelongsTo
    {
        return $this->belongsTo(LicenseKey::class);
    }
}

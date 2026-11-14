<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class LicenseRunStat extends Model
{
    protected $fillable = [
        'license_key_id',
        'key_code',
        'key_note',
        'keywords',
        'keyword_count',
        'click_domains',
        'click_domain_count',
        'skip_domains',
        'skip_domain_count',
        'serp_rounds',
        'ads_found',
        'clicks_ok',
        'ip',
        'hostname',
        'machine_id',
        'ran_at',
    ];

    protected function casts(): array
    {
        return [
            'keyword_count' => 'integer',
            'click_domain_count' => 'integer',
            'skip_domain_count' => 'integer',
            'serp_rounds' => 'integer',
            'ads_found' => 'integer',
            'clicks_ok' => 'integer',
            'ran_at' => 'datetime',
        ];
    }

    public function licenseKey(): BelongsTo
    {
        return $this->belongsTo(LicenseKey::class);
    }
}

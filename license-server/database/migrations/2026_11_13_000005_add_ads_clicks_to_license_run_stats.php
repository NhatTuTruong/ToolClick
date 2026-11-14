<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('license_run_stats', function (Blueprint $table) {
            $table->unsignedInteger('ads_found')->default(0)->after('serp_rounds');
            $table->unsignedInteger('clicks_ok')->default(0)->after('ads_found');
        });
    }

    public function down(): void
    {
        Schema::table('license_run_stats', function (Blueprint $table) {
            $table->dropColumn(['ads_found', 'clicks_ok']);
        });
    }
};

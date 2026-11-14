<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('license_keys', function (Blueprint $table) {
            $table->id();
            $table->string('code', 64)->unique();
            $table->string('status', 20)->default('active'); // active | paused
            $table->unsignedInteger('daily_record_limit')->default(500);
            $table->unsignedInteger('max_machines')->default(1);
            $table->date('expires_at')->nullable();
            $table->string('net', 500)->nullable();
            $table->string('note', 255)->nullable();
            $table->timestamps();
        });

        Schema::create('license_machines', function (Blueprint $table) {
            $table->id();
            $table->foreignId('license_key_id')->constrained('license_keys')->cascadeOnDelete();
            $table->string('machine_id', 128);
            $table->string('hostname', 191)->nullable();
            $table->string('os', 64)->nullable();
            $table->timestamp('activated_at')->nullable();
            $table->timestamp('last_seen_at')->nullable();
            $table->boolean('revoked')->default(false);
            $table->timestamps();
            $table->unique(['license_key_id', 'machine_id']);
        });

        Schema::create('license_daily_usages', function (Blueprint $table) {
            $table->id();
            $table->foreignId('license_key_id')->constrained('license_keys')->cascadeOnDelete();
            $table->string('machine_id', 128);
            $table->date('usage_date');
            $table->unsignedInteger('records_used')->default(0);
            $table->timestamps();
            $table->unique(['license_key_id', 'machine_id', 'usage_date'], 'license_usage_unique');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('license_daily_usages');
        Schema::dropIfExists('license_machines');
        Schema::dropIfExists('license_keys');
    }
};

<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('license_run_stats', function (Blueprint $table) {
            $table->id();
            $table->foreignId('license_key_id')->nullable()->constrained('license_keys')->nullOnDelete();
            $table->string('key_code', 64)->nullable()->index();
            $table->string('key_note', 255)->nullable();
            $table->text('keywords')->nullable();
            $table->unsignedInteger('keyword_count')->default(0);
            $table->text('click_domains')->nullable();
            $table->unsignedInteger('click_domain_count')->default(0);
            $table->text('skip_domains')->nullable();
            $table->unsignedInteger('skip_domain_count')->default(0);
            $table->unsignedInteger('serp_rounds')->default(1);
            $table->string('ip', 64)->nullable()->index();
            $table->string('hostname', 191)->nullable();
            $table->string('machine_id', 128)->nullable();
            $table->timestamp('ran_at')->useCurrent();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('license_run_stats');
    }
};

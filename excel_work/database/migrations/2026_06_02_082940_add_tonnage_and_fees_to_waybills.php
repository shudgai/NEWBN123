<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('waybills', function (Blueprint $table) {
            $table->decimal('tonnage', 10, 2)->nullable();
            $table->integer('truck_fee')->default(0);
            $table->integer('pallet_recovery_fee')->default(0);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('waybills', function (Blueprint $table) {
            $table->dropColumn(['tonnage', 'truck_fee', 'pallet_recovery_fee']);
        });
    }
};

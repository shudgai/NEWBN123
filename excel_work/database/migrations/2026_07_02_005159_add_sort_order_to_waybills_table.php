<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('waybills', function (Blueprint $table) {
            $table->double('sort_order')->nullable()->after('remark');
        });

        // Initialize sort_order with id for existing records
        DB::statement('UPDATE waybills SET sort_order = id WHERE sort_order IS NULL');
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('waybills', function (Blueprint $table) {
            $table->dropColumn('sort_order');
        });
    }
};

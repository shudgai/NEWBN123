<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Waybill extends Model
{
    use HasFactory;

    protected $fillable = [
        'date',
        'bill_no',
        'client_name',
        'amount',
        'pieces',
        'weight',
        'location',
        'remark',
        'is_client_data',
        'client_code',
        'forklift_fee',
        'styles',
        'tonnage',
        'truck_fee',
        'pallet_recovery_fee',
        'sort_order'
    ];

    protected $casts = [
        'weight' => 'integer',
        'amount' => 'integer',
        'pieces' => 'integer',
        'styles' => 'array',
    ];
}

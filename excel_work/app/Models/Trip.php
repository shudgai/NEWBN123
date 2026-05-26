<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Trip extends Model
{
    use HasFactory;

    protected $fillable = ['date', 'price_id', 'trips_count'];

    public function price()
    {
        return $this->belongsTo(Price::class);
    }
}
